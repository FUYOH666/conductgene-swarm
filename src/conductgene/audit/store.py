"""Append-only case audit store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from conductgene.logutil import get_logger
from conductgene.schemas import CaseAuditRecord, SwarmAnalyzeResult

logger = get_logger(__name__)


class AuditStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append(self, *, case_id: str, transcript: str, result: SwarmAnalyzeResult) -> CaseAuditRecord:
        record = CaseAuditRecord(
            case_id=case_id,
            request_id=result.request_id,
            transcript=transcript,
            result=result,
            recorded_at=datetime.now(tz=UTC),
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        logger.info("audit recorded", extra={"meta": {"case_id": case_id}})
        return record

    def get(self, case_id: str) -> CaseAuditRecord | None:
        latest: CaseAuditRecord | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = CaseAuditRecord.model_validate_json(line)
            if rec.case_id == case_id:
                latest = rec
        return latest

    def list_case_ids(self) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = CaseAuditRecord.model_validate_json(line)
            if rec.case_id not in seen:
                seen.add(rec.case_id)
                ids.append(rec.case_id)
        return ids

    def export_all(self) -> list[dict]:
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
