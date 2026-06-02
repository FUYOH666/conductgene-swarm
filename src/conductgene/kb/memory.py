"""In-memory knowledge base loaded from synthetic markdown files."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from conductgene.logutil import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class KbChunk:
    chunk_id: str
    doc_id: str
    section: str | None
    text: str
    language: str = "en"


def _split_sections(content: str) -> list[tuple[str | None, str]]:
    parts = re.split(r"^##\s+", content, flags=re.MULTILINE)
    if len(parts) <= 1:
        return [(None, content.strip())]
    sections: list[tuple[str | None, str]] = []
    for part in parts[1:]:
        lines = part.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if body:
            sections.append((title, body))
    return sections


class MemoryKnowledgeBase:
    """Load markdown KB files into searchable chunks (no external vector DB required)."""

    def __init__(self, kb_dir: Path) -> None:
        self.kb_dir = kb_dir
        self._chunks: list[KbChunk] = []
        self.reload()

    def reload(self) -> int:
        self._chunks.clear()
        if not self.kb_dir.exists():
            logger.warning("kb dir missing", extra={"meta": {"path": str(self.kb_dir)}})
            return 0
        for path in sorted(self.kb_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            doc_id = path.stem
            for section, body in _split_sections(content):
                for para in re.split(r"\n\s*\n", body):
                    text = para.strip()
                    if len(text) < 20:
                        continue
                    self._chunks.append(
                        KbChunk(
                            chunk_id=f"{doc_id}_{uuid.uuid4().hex[:8]}",
                            doc_id=doc_id,
                            section=section,
                            text=text,
                        )
                    )
        logger.info("kb loaded", extra={"meta": {"chunks": len(self._chunks)}})
        return len(self._chunks)

    @property
    def chunks(self) -> list[KbChunk]:
        return list(self._chunks)

    def chunk_count(self) -> int:
        return len(self._chunks)
