from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from precedent.events import GENESIS, EventStore


def test_chain_links_and_verifies(store: EventStore) -> None:
    a = store.append("maria", "x.created", {"n": 1})
    b = store.append("alex", "x.updated", {"n": 2})
    assert a.prev_hash == GENESIS
    assert b.prev_hash == a.hash
    result = store.verify()
    assert result.ok and result.count == 2 and result.head == b.hash
    assert [e.payload["n"] for e in store.events()] == [1, 2]


def test_update_and_delete_are_refused(store: EventStore) -> None:
    store.append("maria", "x", {"n": 1})
    conn = sqlite3.connect(store.path)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE events SET actor = 'mallory'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM events")
    conn.close()


def test_tampering_behind_the_triggers_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "events.db"
    with EventStore(path) as store:
        store.append("maria", "rule.proposed", {"rule": "r@1"})
        store.append("alex", "rule.approved", {"rule": "r@1"})
        store.append("alex", "rule.reverted", {"rule": "r@1"})
    conn = sqlite3.connect(path)
    conn.execute("DROP TRIGGER events_no_update")
    conn.execute("UPDATE events SET actor = 'maria' WHERE seq = 2")
    conn.commit()
    conn.close()
    with EventStore(path) as store:
        result = store.verify()
    assert not result.ok
    assert result.first_bad_seq == 2
    assert "hash" in result.reason


def test_deleted_event_breaks_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "events.db"
    with EventStore(path) as store:
        for i in range(3):
            store.append("maria", "x", {"i": i})
    conn = sqlite3.connect(path)
    conn.execute("DROP TRIGGER events_no_delete")
    conn.execute("DELETE FROM events WHERE seq = 2")
    conn.commit()
    conn.close()
    with EventStore(path) as store:
        result = store.verify()
    assert not result.ok and result.first_bad_seq == 3


def test_every_event_needs_an_actor(store: EventStore) -> None:
    with pytest.raises(ValueError):
        store.append("  ", "x", {})


def test_empty_log_verifies(store: EventStore) -> None:
    result = store.verify()
    assert result.ok and result.count == 0 and store.head() == GENESIS
