"""Append-only audit log for Policy Gene lifecycle events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from conductgene.logutil import get_logger
from conductgene.schemas import GeneAuditEvent, GeneLearnRequest, PolicyGene

logger = get_logger(__name__)


class GeneAuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append_learned(
        self,
        gene: PolicyGene,
        request: GeneLearnRequest,
        *,
        eval_before: float | None,
        eval_after: float | None,
    ) -> GeneAuditEvent:
        event = GeneAuditEvent(
            event_type="gene_learned",
            gene_id=gene.id,
            request_id=request.request_id,
            supervisor_id=request.supervisor_id,
            checklist_id=request.checklist_id,
            eval_before=eval_before,
            eval_after=eval_after,
            trigger_pattern=gene.trigger_pattern,
            recorded_at=datetime.now(tz=UTC),
        )
        self._append(event)
        return event

    def append_rollback(self, gene_id: str, *, request_id: str | None = None) -> GeneAuditEvent:
        event = GeneAuditEvent(
            event_type="gene_rollback",
            gene_id=gene_id,
            request_id=request_id,
            recorded_at=datetime.now(tz=UTC),
        )
        self._append(event)
        return event

    def _append(self, event: GeneAuditEvent) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
        logger.info(
            "gene audit event recorded",
            extra={"meta": {"event_type": event.event_type, "gene_id": event.gene_id}},
        )

    def export_all(self) -> list[dict]:
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def list_for_gene(self, gene_id: str) -> list[GeneAuditEvent]:
        events: list[GeneAuditEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            event = GeneAuditEvent.model_validate_json(line)
            if event.gene_id == gene_id:
                events.append(event)
        return events
