"""Policy Gene store — supervisor-approved institutional memory."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from conductgene.logutil import get_logger
from conductgene.schemas import GeneCreatedFrom, GeneEval, GeneLearnRequest, PolicyGene

logger = get_logger(__name__)


class GeneStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _read_all(self) -> list[PolicyGene]:
        genes: list[PolicyGene] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            genes.append(PolicyGene.model_validate_json(line))
        return genes

    def list_active(self) -> list[PolicyGene]:
        return [g for g in self._read_all() if g.active]

    def list_all(self) -> list[PolicyGene]:
        return self._read_all()

    def count_active(self) -> int:
        return len(self.list_active())

    def append(self, gene: PolicyGene) -> PolicyGene:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(gene.model_dump_json() + "\n")
        logger.info(
            "supervisor-approved policy gene stored",
            extra={"meta": {"gene_id": gene.id, "name": gene.name}},
        )
        return gene

    def learn_from_correction(
        self,
        request: GeneLearnRequest,
        *,
        eval_before: float | None = None,
        eval_after: float | None = None,
        heldout_cases: int = 0,
    ) -> PolicyGene:
        if not request.approved:
            raise ValueError("Policy Gene requires supervisor approval")

        trigger = request.trigger_pattern or "supervisor"
        name = request.name or f"gene_{request.checklist_id}_{uuid.uuid4().hex[:6]}"
        title = request.title or name.replace("_", " ").title()
        gene_id = f"GENE-{uuid.uuid4().hex[:6].upper()}"

        gene = PolicyGene(
            id=gene_id,
            name=name,
            title=title,
            trigger_pattern=trigger,
            action=f"Apply supervisor-approved override: {request.checklist_id} -> {request.corrected_status}",
            target_checklist_id=request.checklist_id,
            override_status=request.corrected_status,
            provenance="human_correction",
            eval_score_before=eval_before,
            eval_score_after=eval_after,
            active=True,
            created_at=datetime.now(tz=UTC),
            source_request_id=request.request_id,
            rationale=request.rationale,
            supervisor_id=request.supervisor_id,
            created_from=GeneCreatedFrom(
                case_id=request.case_id,
                supervisor_override=True,
                supervisor_id=request.supervisor_id,
                chunk_ids=request.chunk_ids,
            ),
            eval_detail=GeneEval(
                before=eval_before,
                after=eval_after,
                heldout_cases=heldout_cases,
            ),
        )
        return self.append(gene)

    def deactivate(self, gene_id: str) -> bool:
        genes = self._read_all()
        found = False
        updated: list[PolicyGene] = []
        for g in genes:
            if g.id == gene_id and g.active:
                found = True
                updated.append(g.model_copy(update={"active": False}))
            else:
                updated.append(g)
        if found:
            self._rewrite(updated)
            logger.info("policy gene rolled back", extra={"meta": {"gene_id": gene_id}})
        return found

    def rollback(self, gene_id: str) -> bool:
        return self.deactivate(gene_id)

    def _rewrite(self, genes: list[PolicyGene]) -> None:
        lines = [g.model_dump_json() for g in genes]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def compute_evolution_metrics(self) -> dict[str, float | int | None]:
        genes = self._read_all()
        active = [g for g in genes if g.active]
        with_scores = [
            g for g in active if g.eval_score_before is not None and g.eval_score_after is not None
        ]
        avg_delta: float | None = None
        if with_scores:
            deltas = [g.eval_score_after - g.eval_score_before for g in with_scores]  # type: ignore[operator]
            avg_delta = sum(deltas) / len(deltas)
        return {
            "total_genes": len(genes),
            "active_genes": len(active),
            "genes_with_eval": len(with_scores),
            "avg_eval_delta": avg_delta,
        }

    def export_audit_log(self) -> list[dict]:
        return [json.loads(g.model_dump_json()) for g in self._read_all()]
