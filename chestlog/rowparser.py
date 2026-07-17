"""Turn raw OCR text boxes into ordered, structured chest-history Rows.

Each real row in the game's list renders as three lines:
    <Chest Type> chest
    From: <Player>
    Source: Level <N> <Location>
To the right of the "From:" and "Source:" lines, the game also renders a
"Time left: ..." countdown and an "Open" button at roughly the same row
height. Line-clustering by y-position pulls those into the same OCR line as
the From/Source text (since it groups purely by vertical position), so this
module explicitly strips that contamination off the end of each line rather
than including it in the player/level fields.
"""
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import median

from chestlog.config import EDGE_MARGIN_PX, LINE_CLUSTER_TOLERANCE_RATIO
from chestlog.models import Row, TextBox

_FROM_RE = re.compile(r"^from\s*:\s*(.+)$", re.IGNORECASE)
_SOURCE_RE = re.compile(r"^source\s*:\s*(.+)$", re.IGNORECASE)
_TIME_LEFT_CONTAMINATION_RE = re.compile(r"\s*time\s*left\s*:?.*$", re.IGNORECASE)
_OPEN_CONTAMINATION_RE = re.compile(r"\s*open\s*$", re.IGNORECASE)
# The small "Clan"/"Guild"/"Personal" badge overlaid on the chest icon sits at
# roughly the same row height as the chest name and to its left, so it lands
# in front of the chest name once boxes are joined left-to-right. OCR
# sometimes tacks on a stray underscore/punctuation after the badge word
# (e.g. "Clan_ Sand Chest"), so allow separator characters, not just a space.
_BADGE_PREFIX_RE = re.compile(r"^(clan|guild|personal|event)[\s_:.\-]+", re.IGNORECASE)
_DEFAULT_LINE_HEIGHT = 20.0
_CHEST_WORD_FUZZ_THRESHOLD = 0.75


@dataclass
class _Line:
    text: str
    y_top: float
    y_bottom: float


@dataclass
class _CandidateRow:
    chest_type: str
    level: str
    player: str
    y_top: float
    y_bottom: float


def _cluster_into_lines(boxes: list[TextBox]) -> list[_Line]:
    if not boxes:
        return []

    ordered = sorted(boxes, key=lambda b: b.y_center)
    heights = [b.height for b in ordered if b.height > 0]
    tolerance = (median(heights) if heights else _DEFAULT_LINE_HEIGHT) * LINE_CLUSTER_TOLERANCE_RATIO

    clusters: list[list[TextBox]] = []
    for box in ordered:
        if clusters:
            cluster_y = sum(b.y_center for b in clusters[-1]) / len(clusters[-1])
            if abs(box.y_center - cluster_y) <= tolerance:
                clusters[-1].append(box)
                continue
        clusters.append([box])

    lines = []
    for cluster in clusters:
        cluster.sort(key=lambda b: b.x_left)
        text = " ".join(b.text for b in cluster).strip()
        if not text:
            continue
        lines.append(_Line(
            text=text,
            y_top=min(b.y_top for b in cluster),
            y_bottom=max(b.y_bottom for b in cluster),
        ))
    return lines


def _looks_like_chest_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    last_word = stripped.split()[-1]
    if last_word.casefold() == "chest":
        return True
    return SequenceMatcher(None, last_word.casefold(), "chest").ratio() >= _CHEST_WORD_FUZZ_THRESHOLD


def _extract_chest_type(chest_line_text: str) -> str:
    return _BADGE_PREFIX_RE.sub("", chest_line_text.strip()).strip()


def _extract_player(from_line_text: str) -> str:
    match = _FROM_RE.match(from_line_text)
    raw = match.group(1)
    return _TIME_LEFT_CONTAMINATION_RE.sub("", raw).strip()


def _extract_level(source_line_text: str) -> str:
    match = _SOURCE_RE.match(source_line_text)
    raw = match.group(1)
    return _OPEN_CONTAMINATION_RE.sub("", raw).strip()


def _pair_lines(lines: list[_Line]) -> list[_CandidateRow]:
    rows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FROM_RE.match(line.text) or _SOURCE_RE.match(line.text):
            # An orphan From:/Source: line with no preceding chest line -- noise, skip it.
            i += 1
            continue
        if _looks_like_chest_line(line.text):
            if i + 2 < len(lines):
                from_match = _FROM_RE.match(lines[i + 1].text)
                source_match = _SOURCE_RE.match(lines[i + 2].text)
                if from_match and source_match:
                    rows.append(_CandidateRow(
                        chest_type=_extract_chest_type(line.text),
                        player=_extract_player(lines[i + 1].text),
                        level=_extract_level(lines[i + 2].text),
                        y_top=line.y_top,
                        y_bottom=lines[i + 2].y_bottom,
                    ))
                    i += 3
                    continue
            # Chest line with no complete From:/Source: pair following -- incomplete, drop it.
            i += 1
            continue
        # Neither a chest line, from line, nor source line -- UI chrome/noise.
        i += 1
    return rows


def _apply_edge_crop_filter(rows: list[_CandidateRow], frame_height: float) -> list[_CandidateRow]:
    if not rows:
        return rows
    filtered = list(rows)
    if filtered and filtered[0].y_top < EDGE_MARGIN_PX:
        filtered = filtered[1:]
    if filtered and filtered[-1].y_bottom > frame_height - EDGE_MARGIN_PX:
        filtered = filtered[:-1]
    return filtered


def parse(boxes: list[TextBox], frame_height: float) -> list[Row]:
    """boxes: OCR detections for one frame, in any order.
    frame_height: pixel height of the captured frame, used for edge cropping.
    Returns ordered, top-to-bottom, edge-filtered list of Row.
    """
    lines = _cluster_into_lines(boxes)
    candidates = _pair_lines(lines)
    candidates = _apply_edge_crop_filter(candidates, frame_height)
    return [Row(chest_type=c.chest_type, level=c.level, player=c.player) for c in candidates]
