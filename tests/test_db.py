import sqlite3

from chestlog.db import fetch_all, init_schema, save_session
from chestlog.models import CapturedRow, Row


def test_save_and_fetch_roundtrip():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    captured_rows = [
        CapturedRow(Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer"), "2026-07-17T14:32:00"),
        CapturedRow(Row(chest_type="Gold Chest", level="Level 25 Crypt", player="Masida"), "2026-07-17T14:32:05"),
    ]
    save_session(conn, "session_20260717_143200", captured_rows)

    saved = fetch_all(conn)
    assert len(saved) == 2
    assert saved[0]["Player"] == "Enjoyer"
    assert saved[0]["ChestType"] == "Dark Omens chest"
    assert saved[0]["Level"] == "Level 10 Crypt"
    assert saved[0]["ScanSession"] == "session_20260717_143200"
    assert saved[0]["CapturedAt"] == "2026-07-17T14:32:00"
    assert saved[1]["Player"] == "Masida"
    assert saved[1]["CapturedAt"] == "2026-07-17T14:32:05"


def test_init_schema_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # must not raise on repeated calls
    assert fetch_all(conn) == []


def test_multiple_sessions_accumulate():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    save_session(conn, "session_A", [CapturedRow(Row("Chest1", "Level 1", "P1"), "2026-07-17T10:00:00")])
    save_session(conn, "session_B", [CapturedRow(Row("Chest2", "Level 2", "P2"), "2026-07-17T11:00:00")])
    saved = fetch_all(conn)
    assert len(saved) == 2
    assert {r["ScanSession"] for r in saved} == {"session_A", "session_B"}
