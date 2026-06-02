"""FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException

from conductgene import __version__
from conductgene.audit.gene_events import GeneAuditStore
from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.harness import compute_learn_eval_delta, run_eval_suite
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import (
    CaseAuditRecord,
    EvalRunRequest,
    EvalRunResponse,
    GeneLearnRequest,
    GeneListResponse,
    HealthResponse,
    PolicyGene,
    ReadyResponse,
    RollbackResponse,
    SwarmAnalyzeRequest,
    SwarmAnalyzeResponse,
)

_settings: Settings | None = None
_kb: MemoryKnowledgeBase | None = None
_genes: GeneStore | None = None
_audit: AuditStore | None = None
_gene_audit: GeneAuditStore | None = None
_eval_cache: EvalRunResponse | None = None
_eval_cache_at: datetime | None = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.resolve_paths(_project_root())
    return _settings


def get_kb() -> MemoryKnowledgeBase:
    global _kb
    if _kb is None:
        s = get_settings()
        _kb = MemoryKnowledgeBase(s.kb_dir)
    return _kb


def get_gene_store() -> GeneStore:
    global _genes
    if _genes is None:
        s = get_settings()
        _genes = GeneStore(s.gene_store_path)
    return _genes


def get_audit_store() -> AuditStore:
    global _audit
    if _audit is None:
        s = get_settings()
        _audit = AuditStore(s.audit_store_path)
    return _audit


def get_gene_audit_store() -> GeneAuditStore:
    global _gene_audit
    if _gene_audit is None:
        s = get_settings()
        _gene_audit = GeneAuditStore(s.gene_audit_store_path)
    return _gene_audit


def _cache_eval_result(result: EvalRunResponse) -> None:
    global _eval_cache, _eval_cache_at
    _eval_cache = result
    _eval_cache_at = datetime.now(tz=UTC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()
    get_kb()
    get_gene_store()
    get_audit_store()
    get_gene_audit_store()
    yield


app = FastAPI(
    title="ConductGene Swarm",
    description="Supervisor-approved conduct QA with auditable Policy Genes",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(ok=True, service="conductgene-swarm", version=__version__)


@app.get("/readyz", response_model=ReadyResponse)
async def readyz() -> ReadyResponse:
    s = get_settings()
    kb = get_kb()
    genes = get_gene_store()
    ready = kb.chunk_count() > 0
    return ReadyResponse(
        ready=ready,
        mode=s.mode,
        kb_chunks=kb.chunk_count(),
        active_genes=genes.count_active(),
    )


@app.post("/swarm/analyze", response_model=SwarmAnalyzeResponse)
async def analyze(request: SwarmAnalyzeRequest) -> SwarmAnalyzeResponse:
    try:
        result = await swarm_analyze(
            settings=get_settings(),
            kb=get_kb(),
            gene_store=get_gene_store(),
            request=request,
            audit_store=get_audit_store(),
        )
        return SwarmAnalyzeResponse(ok=True, result=result)
    except Exception as e:
        return SwarmAnalyzeResponse(ok=False, error=str(e))


@app.get("/genes", response_model=GeneListResponse)
async def list_genes(active_only: bool = False) -> GeneListResponse:
    store = get_gene_store()
    genes = store.list_active() if active_only else store.list_all()
    return GeneListResponse(genes=genes, total=len(genes))


@app.post("/genes/learn", response_model=PolicyGene)
async def learn_gene(request: GeneLearnRequest) -> PolicyGene:
    if not request.approved:
        raise HTTPException(status_code=400, detail="Supervisor approval required")
    store = get_gene_store()
    s = get_settings()
    before, after, heldout = await compute_learn_eval_delta(
        settings=s,
        kb=get_kb(),
        scenarios_dir=s.scenarios_dir,
        request=request,
    )
    gene = store.learn_from_correction(
        request,
        eval_before=before,
        eval_after=after,
        heldout_cases=heldout,
    )
    get_gene_audit_store().append_learned(
        gene,
        request,
        eval_before=before,
        eval_after=after,
    )
    return gene


@app.post("/genes/{gene_id}/rollback", response_model=RollbackResponse)
async def rollback_gene(gene_id: str) -> RollbackResponse:
    store = get_gene_store()
    ok = store.rollback(gene_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gene not found or already inactive")
    get_gene_audit_store().append_rollback(gene_id)
    return RollbackResponse(
        gene_id=gene_id,
        rolled_back=True,
        message="Supervisor-approved Policy Gene rolled back",
    )


@app.delete("/genes/{gene_id}")
async def deactivate_gene(gene_id: str) -> dict[str, bool]:
    return (await rollback_gene(gene_id)).model_dump()


@app.post("/eval/run", response_model=EvalRunResponse)
async def eval_run(request: EvalRunRequest) -> EvalRunResponse:
    s = get_settings()
    result = await run_eval_suite(
        settings=s,
        kb=get_kb(),
        gene_store=get_gene_store(),
        scenarios_dir=s.scenarios_dir,
        suite=request.suite,
        apply_genes=request.apply_genes,
    )
    _cache_eval_result(result)
    return result


@app.get("/audit/export")
async def export_audit() -> dict:
    return {
        "cases": get_audit_store().export_all(),
        "gene_events": get_gene_audit_store().export_all(),
    }


@app.get("/audit/{case_id}", response_model=CaseAuditRecord)
async def get_audit(case_id: str) -> CaseAuditRecord:
    record = get_audit_store().get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Case audit not found")
    return record


@app.get("/metrics/evolution")
async def evolution_metrics(refresh: bool = False) -> dict:
    store = get_gene_store()
    metrics = store.compute_evolution_metrics()
    global _eval_cache, _eval_cache_at

    if refresh or _eval_cache is None:
        s = get_settings()
        eval_resp = await run_eval_suite(
            settings=s,
            kb=get_kb(),
            gene_store=store,
            scenarios_dir=s.scenarios_dir,
            suite="all",
            apply_genes=True,
        )
        _cache_eval_result(eval_resp)
    else:
        eval_resp = _eval_cache

    metrics["eval_score"] = eval_resp.score if eval_resp else None
    metrics["citation_coverage"] = eval_resp.citation_coverage if eval_resp else None
    metrics["abstain_rate"] = eval_resp.abstain_rate if eval_resp else None
    metrics["eval_cached_at"] = _eval_cache_at.isoformat() if _eval_cache_at else None
    metrics["gene_learning"] = eval_resp.gene_learning if eval_resp else None
    return metrics
