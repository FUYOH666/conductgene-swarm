"""Append-only, hash-chained event log on SQLite.

Each event stores ``hash = sha256(prev_hash + canonical(event))``. SQLite
triggers refuse UPDATE and DELETE, and ``verify()`` recomputes the chain, so a
silent edit made by bypassing the triggers is still detected.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from precedent.hashing import canonical_json, sha256_hex

GENESIS = "0" * 64

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
"""


@dataclass(frozen=True)
class Event:
    seq: int
    ts: str
    actor: str
    type: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    count: int
    head: str
    first_bad_seq: int | None = None
    reason: str = ""


def _event_hash(prev_hash: str, seq: int, ts: str, actor: str, type_: str, payload: str) -> str:
    body = canonical_json({"seq": seq, "ts": ts, "actor": actor, "type": type_, "payload": payload})
    return sha256_hex(prev_hash + "\n" + body)


class EventStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def append(self, actor: str, type_: str, payload: dict[str, Any]) -> Event:
        if not actor.strip():
            raise ValueError("every event needs an actor")
        body = canonical_json(payload)
        ts = datetime.now(tz=UTC).isoformat(timespec="microseconds")
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            row = cur.execute("SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq = (row[0] + 1) if row else 1
            prev = row[1] if row else GENESIS
            digest = _event_hash(prev, seq, ts, actor, type_, body)
            cur.execute(
                "INSERT INTO events (seq, ts, actor, type, payload, prev_hash, hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (seq, ts, actor, type_, body, prev, digest),
            )
            cur.execute("COMMIT")
        except BaseException:
            cur.execute("ROLLBACK")
            raise
        return Event(seq, ts, actor, type_, payload, prev, digest)

    def _rows(self) -> Iterator[tuple[int, str, str, str, str, str, str]]:
        yield from self._conn.execute(
            "SELECT seq, ts, actor, type, payload, prev_hash, hash FROM events ORDER BY seq"
        )

    def events(self) -> list[Event]:
        return [
            Event(seq, ts, actor, type_, json.loads(payload), prev, digest)
            for seq, ts, actor, type_, payload, prev, digest in self._rows()
        ]

    def head(self) -> str:
        row = self._conn.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        return str(row[0]) if row else GENESIS

    def verify(self) -> VerifyResult:
        prev = GENESIS
        count = 0
        expected_seq = 1
        for seq, ts, actor, type_, payload, prev_hash, digest in self._rows():
            count += 1
            if seq != expected_seq:
                return VerifyResult(False, count, prev, seq, f"gap in sequence before {seq}")
            if prev_hash != prev:
                return VerifyResult(False, count, prev, seq, "prev_hash does not link")
            if _event_hash(prev, seq, ts, actor, type_, payload) != digest:
                return VerifyResult(False, count, prev, seq, "content does not match its hash")
            prev = digest
            expected_seq += 1
        return VerifyResult(True, count, prev)
