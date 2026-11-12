"""Canonical JSON and content hashes.

Everything that is hashed (events, rules, datasets, clauses) goes through
``canonical_json`` so the same content always produces the same hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_id(*parts: str, length: int = 12) -> str:
    """Stable id derived from content, e.g. for policy clauses."""
    return sha256_hex("|".join(parts))[:length]
