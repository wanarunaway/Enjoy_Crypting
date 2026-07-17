from chestlog.merge import align_and_append
from chestlog.models import Row


def R(chest, player, level="Level 10 Crypt"):
    return Row(chest_type=chest, level=level, player=player)


def test_first_frame_all_new():
    new_rows = [R("Dark Omens chest", "Enjoyer"), R("Dark Omens chest", "Masida")]
    appended, tail, gap = align_and_append([], new_rows)
    assert appended == new_rows
    assert tail == new_rows
    assert gap is False


def test_basic_overlap_from_example():
    frame1 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Masida"),
    ]
    frame2 = [
        R("Dark Omens chest", "Masida"),
        R("Dark Omens chest", "Alex"),
        R("Dark Omens chest", "Sarah"),
    ]
    # Only 1 overlapping row here, below MIN_OVERLAP_ROWS(3) -> treated as a gap,
    # not silently merged. This documents that a single-row overlap is NOT
    # trusted; see test_realistic_overlap_with_enough_rows for the real case.
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is True


def test_realistic_overlap_with_enough_rows():
    frame1 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Small Chest", "Bob"),
        R("Dark Omens chest", "Masida"),
        R("Gold Chest", "Wendy"),
        R("Iron Chest", "Zed"),
    ]
    frame2 = [
        R("Dark Omens chest", "Masida"),
        R("Gold Chest", "Wendy"),
        R("Iron Chest", "Zed"),
        R("Silver Chest", "Alex"),
        R("Bronze Chest", "Sarah"),
    ]
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is False
    assert appended == [R("Silver Chest", "Alex"), R("Bronze Chest", "Sarah")]
    assert tail == frame2


def test_repeated_identical_rows_not_collapsed():
    """Five identical (chest, level, player) rows are five distinct real entries.
    The algorithm must never use set/membership semantics -- only position."""
    frame1 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
    ]
    frame2 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Dark Omens chest", "Enjoyer"),
        R("Gold Chest", "Newguy"),
    ]
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is False
    # Overlap boundary lands at the longest matching run (5, capped by len(frame1)),
    # so only the genuinely new row is appended.
    assert appended == [R("Gold Chest", "Newguy")]


def test_same_chest_and_player_different_level_not_merged():
    """Same chest type and player but a different source level is a distinct
    row -- level participates in the identity/overlap match too."""
    frame1 = [
        R("Dark Omens chest", "Enjoyer", level="Level 10 Crypt"),
        R("Small Chest", "Bob", level="Level 10 Crypt"),
        R("Gold Chest", "Wendy", level="Level 10 Crypt"),
        R("Iron Chest", "Zed", level="Level 10 Crypt"),
    ]
    frame2 = [
        R("Small Chest", "Bob", level="Level 10 Crypt"),
        R("Gold Chest", "Wendy", level="Level 10 Crypt"),
        R("Iron Chest", "Zed", level="Level 10 Crypt"),
        R("Dark Omens chest", "Enjoyer", level="Level 25 Crypt"),  # different level -> new row
    ]
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is False
    assert appended == [R("Dark Omens chest", "Enjoyer", level="Level 25 Crypt")]


def test_fuzzy_ocr_noise_tolerated():
    frame1 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Gold Chest", "Wendy"),
        R("Iron Chest", "Zed"),
    ]
    # OCR misread "Enjoyer" as "En joyer" and "chest" is fine elsewhere
    frame2 = [
        R("Dark 0mens chest", "En joyer"),
        R("Gold Chest", "Wendy"),
        R("Iron Chest", "Zed"),
        R("New Chest", "Newcomer"),
    ]
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is False
    assert appended == [R("New Chest", "Newcomer")]


def test_no_overlap_is_flagged_as_gap_not_silently_merged():
    frame1 = [
        R("Dark Omens chest", "Enjoyer"),
        R("Gold Chest", "Wendy"),
        R("Iron Chest", "Zed"),
    ]
    frame2 = [
        R("Totally Different", "StrangerA"),
        R("Totally Different", "StrangerB"),
        R("Totally Different", "StrangerC"),
    ]
    appended, tail, gap = align_and_append(frame1, frame2)
    assert gap is True
    # On a gap we still don't silently drop or duplicate -- append everything
    # from the new frame since we can't tell what's already been recorded,
    # and let the GUI flag it for manual review.
    assert appended == frame2
    assert tail == frame2


def test_empty_new_frame():
    frame1 = [R("Dark Omens chest", "Enjoyer")]
    appended, tail, gap = align_and_append(frame1, [])
    assert appended == []
    assert tail == frame1
    assert gap is False
