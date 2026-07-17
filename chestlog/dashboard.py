"""Generate a self-contained HTML dashboard from the ChestLog database.

No server, no external requests -- one HTML file with the data embedded as
JSON and plain-JS/SVG charts, safe to open directly (file://) or double-click.
"""
import json
import sqlite3
import webbrowser
from datetime import datetime
from pathlib import Path

from chestlog.config import DB_PATH

_TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard_template.html"
_TOP_N = 10


def _top(conn: sqlite3.Connection, column: str, limit: int = _TOP_N) -> list[dict]:
    rows = conn.execute(
        f"SELECT {column} AS label, COUNT(*) AS value FROM ChestLog "
        f"GROUP BY {column} ORDER BY value DESC, label ASC"
    ).fetchall()
    head = [{"label": (r["label"] or "").strip() or "(unknown)", "value": r["value"]} for r in rows[:limit]]
    rest = sum(r["value"] for r in rows[limit:])
    if rest:
        head.append({"label": "Other", "value": rest})
    return head


def build_data(conn: sqlite3.Connection) -> dict:
    conn.row_factory = sqlite3.Row
    total = conn.execute("SELECT COUNT(*) AS c FROM ChestLog").fetchone()["c"]
    if total == 0:
        return {"total": 0}

    unique_players = conn.execute("SELECT COUNT(DISTINCT Player) AS c FROM ChestLog").fetchone()["c"]
    unique_types = conn.execute("SELECT COUNT(DISTINCT ChestType) AS c FROM ChestLog").fetchone()["c"]
    date_row = conn.execute("SELECT MIN(CapturedAt) AS a, MAX(CapturedAt) AS b FROM ChestLog").fetchone()

    activity_rows = conn.execute(
        "SELECT substr(CapturedAt, 1, 10) AS day, COUNT(*) AS value FROM ChestLog "
        "GROUP BY day ORDER BY day"
    ).fetchall()

    session_rows = conn.execute(
        "SELECT ScanSession AS session, COUNT(*) AS count, "
        "MIN(CapturedAt) AS started, MAX(CapturedAt) AS ended "
        "FROM ChestLog GROUP BY ScanSession ORDER BY started DESC"
    ).fetchall()

    raw_rows = conn.execute(
        "SELECT Player AS player, ChestType AS chest_type, Level AS level, "
        "CapturedAt AS captured_at, ScanSession AS session "
        "FROM ChestLog ORDER BY CapturedAt DESC"
    ).fetchall()

    return {
        "total": total,
        "unique_players": unique_players,
        "unique_types": unique_types,
        "date_start": date_row["a"],
        "date_end": date_row["b"],
        "top_players": _top(conn, "Player"),
        "top_chest_types": _top(conn, "ChestType"),
        "top_levels": _top(conn, "Level"),
        "activity": [{"label": r["day"], "value": r["value"]} for r in activity_rows],
        "sessions": [dict(r) for r in session_rows],
        "raw": [dict(r) for r in raw_rows],
    }


def generate_html(conn: sqlite3.Connection) -> str:
    data = build_data(conn)
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template
        .replace("__DATA_JSON__", json.dumps(data))
        .replace("__GENERATED_AT__", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )


def write_dashboard(db_path: Path = DB_PATH, output_path: Path | None = None) -> Path:
    output_path = output_path or Path(db_path).resolve().parent / "chestlog_dashboard.html"
    conn = sqlite3.connect(db_path)
    try:
        html = generate_html(conn)
    finally:
        conn.close()
    Path(output_path).write_text(html, encoding="utf-8")
    return Path(output_path)


def open_dashboard(db_path: Path = DB_PATH) -> Path:
    path = write_dashboard(db_path)
    webbrowser.open(path.as_uri())
    return path
