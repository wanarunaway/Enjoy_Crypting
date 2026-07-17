import sqlite3
from pathlib import Path

from chestlog.config import DB_PATH
from chestlog.models import CapturedRow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ChestLog (
    ID           INTEGER PRIMARY KEY AUTOINCREMENT,
    Player       TEXT NOT NULL,
    ChestType    TEXT NOT NULL,
    Level        TEXT NOT NULL,
    ScanSession  TEXT NOT NULL,
    CapturedAt   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chestlog_session ON ChestLog(ScanSession);
"""


def get_connection(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    _migrate_missing_columns(conn)
    conn.commit()


def _migrate_missing_columns(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a database file already existed, without
    touching existing rows. Existing rows get an empty string for the new
    column since it has no source data to backfill from."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(ChestLog)")}
    if "Level" not in existing:
        conn.execute("ALTER TABLE ChestLog ADD COLUMN Level TEXT NOT NULL DEFAULT ''")


def save_session(conn: sqlite3.Connection, session_id: str, captured_rows: list[CapturedRow]) -> None:
    with conn:
        conn.executemany(
            "INSERT INTO ChestLog (Player, ChestType, Level, ScanSession, CapturedAt) VALUES (?, ?, ?, ?, ?)",
            [(cr.row.player, cr.row.chest_type, cr.row.level, session_id, cr.captured_at) for cr in captured_rows],
        )


def fetch_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM ChestLog ORDER BY ID").fetchall()
