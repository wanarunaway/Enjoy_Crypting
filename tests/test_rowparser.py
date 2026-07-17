from chestlog.models import Row, TextBox
from chestlog.rowparser import parse


def box(text, x_left, y_top, y_bottom):
    return TextBox(text=text, x_left=x_left, y_top=y_top, y_bottom=y_bottom)


def test_basic_three_line_pairing():
    boxes = [
        box("Dark Omens chest", 10, 60, 78),
        box("From: Enjoyer", 10, 80, 98),
        box("Source: Level 10 Crypt", 10, 100, 118),
        box("Gold Chest", 10, 140, 158),
        box("From: Masida", 10, 160, 178),
        box("Source: Level 25 Crypt", 10, 180, 198),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [
        Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer"),
        Row(chest_type="Gold Chest", level="Level 25 Crypt", player="Masida"),
    ]


def test_time_left_contamination_stripped_from_player():
    # "Time left: ... 17 h 45 m" lands on the same OCR line as "From:" because
    # it sits at the same row height in the game's UI (different column).
    boxes = [
        box("Dark Omens chest", 10, 60, 78),
        box("From: Enjoyer", 10, 80, 98),
        box("Time left: 17 h 45 m", 900, 80, 98),  # same y as the From line, far right
        box("Source: Level 10 Crypt", 10, 100, 118),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer")]


def test_open_button_contamination_stripped_from_level():
    # The "Open" button sits at roughly the same row height as the Source line.
    boxes = [
        box("Dark Omens chest", 10, 60, 78),
        box("From: Enjoyer", 10, 80, 98),
        box("Source: Level 10 Crypt", 10, 100, 118),
        box("Open", 900, 100, 118),  # same y as the Source line, far right
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer")]


def test_clan_badge_prefix_stripped_from_chest_name():
    # The "Clan" badge overlaid on the chest icon sits at roughly the same
    # row height as the chest name and to its left, so it gets joined in
    # front of the chest name: "Clan Dark Omens chest".
    boxes = [
        box("Clan", 15, 40, 58),
        box("Dark Omens chest", 220, 42, 60),
        box("From: Enjoyer", 10, 80, 98),
        box("Source: Level 10 Crypt", 10, 100, 118),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer")]


def test_clan_badge_with_stray_underscore_stripped():
    # Real-world OCR variant: the badge reads as "Clan_" (stray underscore)
    # instead of a clean "Clan " space separator.
    boxes = [
        box("Clan_ Sand Chest", 15, 40, 58),
        box("From: Draconan", 10, 80, 98),
        box("Source: Level 15 Crypt", 10, 100, 118),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Sand Chest", level="Level 15 Crypt", player="Draconan")]


def test_split_line_joined_left_to_right():
    boxes = [
        box("Dark", 10, 60, 78),
        box("Omens chest", 90, 61, 79),  # same visual line, second box
        box("From:", 10, 80, 98),
        box("Enjoyer", 60, 81, 99),
        box("Source:", 10, 100, 118),
        box("Level 10 Crypt", 70, 101, 119),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer")]


def test_edge_clipped_rows_dropped():
    boxes = [
        # clipped at top (y_top < EDGE_MARGIN_PX=15)
        box("Dark Omens chest", 10, 2, 20),
        box("From: Enjoyer", 10, 22, 40),
        box("Source: Level 10 Crypt", 10, 42, 60),
        # fully visible
        box("Gold Chest", 10, 120, 138),
        box("From: Masida", 10, 140, 158),
        box("Source: Level 25 Crypt", 10, 160, 178),
        # clipped at bottom (y_bottom > frame_height(400) - 15 = 385)
        box("Iron Chest", 10, 340, 358),
        box("From: Alex", 10, 360, 378),
        box("Source: Level 30 Crypt", 10, 380, 398),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Gold Chest", level="Level 25 Crypt", player="Masida")]


def test_unpaired_chest_line_dropped():
    boxes = [
        box("Dark Omens chest", 10, 60, 78),
        # no From:/Source: lines follow before next chest line
        box("Gold Chest", 10, 120, 138),
        box("From: Masida", 10, 140, 158),
        box("Source: Level 25 Crypt", 10, 160, 178),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Gold Chest", level="Level 25 Crypt", player="Masida")]


def test_noise_lines_ignored():
    boxes = [
        box("Chest History", 10, 5, 23),  # header/title
        box("Dark Omens chest", 10, 60, 78),
        box("From: Enjoyer", 10, 80, 98),
        box("Source: Level 10 Crypt", 10, 100, 118),
        box("Scroll for more", 10, 370, 388),
    ]
    rows = parse(boxes, frame_height=400)
    assert rows == [Row(chest_type="Dark Omens chest", level="Level 10 Crypt", player="Enjoyer")]


def test_empty_input():
    assert parse([], frame_height=400) == []
