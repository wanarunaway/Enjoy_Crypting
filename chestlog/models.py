from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    """A single chest-history entry: what chest, from which source level, from whom."""
    chest_type: str
    level: str
    player: str


@dataclass(frozen=True)
class CapturedRow:
    """A Row plus the real-world timestamp of when it was first recorded
    during a scan -- kept separate from Row itself so Row's equality (used
    for overlap matching in merge.py) never depends on timing."""
    row: Row
    captured_at: str


@dataclass
class TextBox:
    """One EasyOCR detection: text plus its pixel position."""
    text: str
    x_left: float
    y_top: float
    y_bottom: float

    @property
    def y_center(self) -> float:
        return (self.y_top + self.y_bottom) / 2

    @property
    def height(self) -> float:
        return self.y_bottom - self.y_top
