"""Overlap detection between consecutive scroll-capture frames.

Scrolling is monotonic and one-directional, so the overlap between frame N-1
and frame N is always "a contiguous suffix of frame N-1's rows equals a
contiguous prefix of frame N's rows." We only ever need to find that boundary
and append what comes after it -- no general sequence alignment required.
"""
import re
from difflib import SequenceMatcher

from chestlog.config import (
    CHEST_FUZZ_THRESHOLD,
    LEVEL_FUZZ_THRESHOLD,
    MIN_OVERLAP_ROWS,
    PLAYER_FUZZ_THRESHOLD,
)
from chestlog.models import Row

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().casefold())


def rows_match(a: Row, b: Row) -> bool:
    chest_ratio = SequenceMatcher(None, normalize(a.chest_type), normalize(b.chest_type)).ratio()
    level_ratio = SequenceMatcher(None, normalize(a.level), normalize(b.level)).ratio()
    player_ratio = SequenceMatcher(None, normalize(a.player), normalize(b.player)).ratio()
    return (chest_ratio >= CHEST_FUZZ_THRESHOLD
            and level_ratio >= LEVEL_FUZZ_THRESHOLD
            and player_ratio >= PLAYER_FUZZ_THRESHOLD)


def find_overlap_length(tail: list[Row], new_rows: list[Row]) -> int:
    """Return the length of the longest suffix of `tail` that fuzzy-matches
    a prefix of `new_rows`, requiring at least MIN_OVERLAP_ROWS consecutive
    matches to accept it as a real overlap (not a coincidental single match).
    Returns 0 if no such overlap is found.
    """
    max_check = min(len(tail), len(new_rows))
    if max_check < MIN_OVERLAP_ROWS:
        return 0

    for suffix_len in range(max_check, MIN_OVERLAP_ROWS - 1, -1):
        tail_suffix = tail[-suffix_len:]
        new_prefix = new_rows[:suffix_len]
        if all(rows_match(t, n) for t, n in zip(tail_suffix, new_prefix)):
            return suffix_len
    return 0


def align_and_append(tail: list[Row], new_rows: list[Row]) -> tuple[list[Row], list[Row], bool]:
    """Align a new frame's rows against the previous frame's row list.

    Returns (rows_to_append, new_tail, gap_detected).

    - rows_to_append: rows from `new_rows` that are genuinely new (append
      these to the session's accumulated result, in order).
    - new_tail: pass this in as `tail` for the next frame.
    - gap_detected: True when no overlap could be found even though both
      frames had enough rows to check -- likely the user scrolled too far
      in one jump (skipped rows) or scrolled backwards. The caller should
      surface this for manual review rather than silently trusting the data.
    """
    if not tail:
        return new_rows, new_rows, False

    if not new_rows:
        return [], tail, False

    overlap_len = find_overlap_length(tail, new_rows)
    gap_detected = overlap_len == 0 and min(len(tail), len(new_rows)) >= MIN_OVERLAP_ROWS

    rows_to_append = new_rows[overlap_len:]
    return rows_to_append, new_rows, gap_detected
