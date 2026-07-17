import json
import sqlite3

from chestlog.dashboard import build_data, generate_html
from chestlog.db import init_schema, save_session
from chestlog.models import CapturedRow, Row


def _seed(conn):
    init_schema(conn)
    save_session(conn, "session_A", [
        CapturedRow(Row("Dark Omens chest", "Level 10 Crypt", "Enjoyer"), "2026-07-17T14:00:00"),
        CapturedRow(Row("Dark Omens chest", "Level 10 Crypt", "Enjoyer"), "2026-07-17T14:00:05"),
        CapturedRow(Row("Gold Chest", "Level 25 Crypt", "Masida"), "2026-07-17T14:00:10"),
    ])
    save_session(conn, "session_B", [
        CapturedRow(Row("Gold Chest", "Level 25 Crypt", "Masida"), "2026-07-18T09:00:00"),
    ])


def test_build_data_empty_db():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    data = build_data(conn)
    assert data == {"total": 0}


def test_build_data_totals_and_breakdowns():
    conn = sqlite3.connect(":memory:")
    _seed(conn)
    data = build_data(conn)

    assert data["total"] == 4
    assert data["unique_players"] == 2
    assert data["unique_types"] == 2
    assert data["date_start"] == "2026-07-17T14:00:00"
    assert data["date_end"] == "2026-07-18T09:00:00"

    top_players = {row["label"]: row["value"] for row in data["top_players"]}
    assert top_players == {"Enjoyer": 2, "Masida": 2}

    top_types = {row["label"]: row["value"] for row in data["top_chest_types"]}
    assert top_types == {"Dark Omens chest": 2, "Gold Chest": 2}

    activity = {row["label"]: row["value"] for row in data["activity"]}
    assert activity == {"2026-07-17": 3, "2026-07-18": 1}

    session_ids = {row["session"] for row in data["sessions"]}
    assert session_ids == {"session_A", "session_B"}
    assert len(data["raw"]) == 4


def test_build_data_folds_tail_into_other():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = [
        CapturedRow(Row(f"Chest {i}", "Level 1", f"Player{i}"), f"2026-07-17T14:0{i}:00")
        for i in range(12)
    ]
    save_session(conn, "session_A", rows)
    data = build_data(conn)

    assert len(data["top_players"]) == 11  # 10 head + "Other"
    other = [r for r in data["top_players"] if r["label"] == "Other"][0]
    assert other["value"] == 2  # 12 players, top 10 shown, 2 folded


def test_build_data_blank_level_labeled_unknown():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    save_session(conn, "session_A", [
        CapturedRow(Row("Old Chest", "", "LegacyPlayer"), "2026-07-17T14:00:00"),
    ])
    data = build_data(conn)
    assert data["top_levels"] == [{"label": "(unknown)", "value": 1}]


def test_generate_html_embeds_valid_json_and_is_self_contained():
    conn = sqlite3.connect(":memory:")
    _seed(conn)
    html = generate_html(conn)

    assert "<html" in html.lower()
    assert "__DATA_JSON__" not in html  # placeholder was substituted
    assert "__GENERATED_AT__" not in html
    # no external requests -- must not load a CDN script/stylesheet
    # (the SVG namespace URI itself is not a fetch and is fine to contain "http://")
    assert "<script src=" not in html
    assert "<link " not in html

    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\n", start)
    payload = json.loads(html[start:end])
    assert payload["total"] == 4
