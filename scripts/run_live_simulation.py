#!/usr/bin/env python3
"""End-to-end live simulation: CASE-002 → gene → CASE-005 held-out re-eval."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.harness import compute_learn_eval_delta
from conductgene.eval.scenarios import load_all_scenarios
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.logutil import setup_logging
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import GeneLearnRequest, SwarmAnalyzeRequest
from conductgene.services.discovery import discover_services, format_service_table

OUTPUT_DIR = ROOT / "outputs" / "demo"
REPORT_PATH = OUTPUT_DIR / "live_simulation_report.md"


def _status(result, checklist_id: str) -> str:
    for c in result.checklist:
        if c.id == checklist_id:
            return c.status
    return "n/a"


def _preflight_live(settings: Settings, probes: list) -> None:
    from conductgene.providers.llm import resolve_llm_config

    if settings.llm_provider != "mock":
        if settings.mode != "live":
            print(
                f"WARNING: llm_provider={settings.llm_provider} but mode={settings.mode} "
                "— agents will use mock rules. Set CONDUCTGENE_MODE=live.",
                file=sys.stderr,
            )
        else:
            resolve_llm_config(settings)
            print(f"Live LLM: provider={settings.llm_provider}")
    else:
        print("Agents: deterministic mock (CONDUCTGENE_LLM_PROVIDER=mock)")

    if settings.retrieval_mode != "memory":
        required = {"embedding", "reranker", "qdrant"}
        bad = {p.service for p in probes if p.service in required and p.status == "error"}
        if bad:
            print(f"WARNING: retrieval services down {bad} — may fallback to memory", file=sys.stderr)


async def run() -> int:
    setup_logging()
    settings = Settings()
    settings.resolve_paths(ROOT)

    print("=== Preflight: service discovery ===")
    probes = discover_services(settings)
    print(format_service_table(probes))
    _preflight_live(settings, probes)

    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)
    audit = AuditStore(settings.audit_store_path)
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    case2 = scenarios["CASE-002"]
    case5 = scenarios["CASE-005"]

    print("\n=== Step 1: CASE-002 live swarm analyze ===")
    r1 = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=genes,
        audit_store=audit,
        request=SwarmAnalyzeRequest(
            transcript=case2.transcript,
            case_id=case2.id,
            apply_genes=False,
            abstain_when_low_evidence=False,
        ),
    )
    print(
        f"Case: {r1.case_id} | threat: {_status(r1, 'threat_language')} | "
        f"escalation: {_status(r1, 'escalation_offered')} | "
        f"evidence_chunks: {len(r1.evidence)}"
    )

    gl = case2.gene_learning
    assert gl is not None
    print("\n=== Step 2: Supervisor Policy Gene ===")
    learn_req = GeneLearnRequest(
        request_id=r1.request_id,
        checklist_id=gl.checklist_id,
        corrected_status=gl.corrected_status,
        rationale=gl.rationale,
        trigger_pattern=gl.trigger_pattern,
        name="implicit_repayment_escalation",
        title="Implicit repayment escalation detection",
        supervisor_id="live-sim-supervisor",
        case_id=case2.id,
    )
    before, after, heldout = await compute_learn_eval_delta(
        settings=settings,
        kb=kb,
        scenarios_dir=settings.scenarios_dir,
        request=learn_req,
    )
    gene = genes.learn_from_correction(
        learn_req,
        eval_before=before,
        eval_after=after,
        heldout_cases=heldout,
    )
    print(f"Stored: {gene.id} (held-out eval {before:.2f} → {after:.2f})")

    print("\n=== Step 3: CASE-005 held-out with genes ===")
    r2 = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=genes,
        audit_store=audit,
        request=SwarmAnalyzeRequest(
            transcript=case5.transcript,
            case_id=case5.id,
            apply_genes=True,
            abstain_when_low_evidence=False,
        ),
    )
    esc = _status(r2, "escalation_offered")
    print(f"Genes applied: {r2.genes_applied}")
    print(f"Escalation: {esc} (target: pass via gene)")
    print(f"Metrics: {r2.evolution_metrics}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_export = ROOT / "reports" / "audit_export.json"
    audit_export.parent.mkdir(parents=True, exist_ok=True)
    payload = {"cases": audit.export_all(), "gene_id": gene.id}
    audit_export.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = f"""# Live Simulation Report

Generated: {datetime.now(UTC).isoformat()}

## Configuration

| Setting | Value |
|---------|-------|
| mode | {settings.mode} |
| llm_provider | {settings.llm_provider} |
| retrieval_mode | {settings.retrieval_mode} |

## Service discovery

```
{format_service_table(probes)}
```

## CASE-002 analyze

- threat_language: {_status(r1, "threat_language")}
- escalation_offered: {_status(r1, "escalation_offered")}
- evidence chunks: {len(r1.evidence)}

## Policy Gene

- id: {gene.id}
- held-out eval: {before:.2f} → {after:.2f}

## CASE-005 held-out

- escalation_offered: {esc}
- genes_applied: {r2.genes_applied}
- improved: {esc == "pass"}

## Artifacts

- `{audit_export.relative_to(ROOT)}`
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written: {REPORT_PATH}")
    return 0


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
