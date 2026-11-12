"""Append-only, hash-chained event log on SQLite.

Each event stores ``hash = sha256(prev_hash + canonical(event))``. SQLite
triggers refuse UPDATE and DELETE, and ``verify()`` recomputes the chain, so a
silent edit made by bypassing the triggers is still detected.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from precedent.hashing import canonical_json, sha256_hex

GENESIS = "0" * 64
#: Bumped when the on-disk format changes; stored as SQLite PRAGMA user_version.
LOG_FORMAT = 1

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
    def __init__(self, path: Path | str, *, timeout: float = 10.0) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None, timeout=timeout)
        self._conn.execute("PRAGMA journal_mode=WAL")
        found = int(self._conn.execute("PRAGMA user_version").fetchone()[0])
        if found > LOG_FORMAT:
            raise RuntimeError(
                f"{self.path} uses log format {found}; this version of precedent reads {LOG_FORMAT}"
            )
        self._conn.executescript(_SCHEMA)
        if found == 0:
            self._conn.execute(f"PRAGMA user_version = {LOG_FORMAT}")
        self._depth = 0

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Hold the write lock: read state, check it and append as one transaction.

        Two processes cannot both validate against the same state and then
        both write; the second waits, then sees the first one's event.
        """
        if self._depth:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        self._conn.execute("BEGIN IMMEDIATE")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")
        finally:
            self._depth = 0

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
        with self.locked():
            row = self._conn.execute(
                "SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq = (row[0] + 1) if row else 1
            prev = row[1] if row else GENESIS
            digest = _event_hash(prev, seq, ts, actor, type_, body)
            self._conn.execute(
                "INSERT INTO events (seq, ts, actor, type, payload, prev_hash, hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (seq, ts, actor, type_, body, prev, digest),
            )
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

    def verify(self, anchor: str | None = None) -> VerifyResult:
        """Recompute the chain. ``anchor`` is a head hash recorded elsewhere earlier;
        if it is no longer in the chain, events were rewritten or cut off."""
        prev = GENESIS
        count = 0
        expected_seq = 1
        seen_anchor = anchor is None
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
            seen_anchor = seen_anchor or digest == anchor
        if not seen_anchor:
            return VerifyResult(
                False, count, prev, None, "anchor not found: log was cut or rewritten"
            )
        return VerifyResult(True, count, prev)
