"""EasyOCR wrapper: PIL frame -> list[TextBox].

The EasyOCR Reader is expensive to construct (loads/downloads model
weights), so callers should build one Reader and reuse it across frames --
never construct one per frame.
"""
import threading

import numpy as np
from PIL import Image

from chestlog.models import TextBox


def create_reader():
    """Lazily import easyocr so the rest of the app can be tested/used
    without the heavy torch/easyocr dependency chain being importable yet."""
    import easyocr
    return easyocr.Reader(["en"])


class ReaderHolder:
    """Caches a single EasyOCR Reader across scan sessions within one app
    run -- constructing it is slow (model load, first-run download), so it
    must happen at most once, lazily, off the GUI thread."""

    def __init__(self):
        self._reader = None
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            if self._reader is None:
                self._reader = create_reader()
            return self._reader


def read(reader, frame: Image.Image) -> list[TextBox]:
    result = reader.readtext(np.array(frame))
    boxes = []
    for bbox, text, _confidence in result:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        boxes.append(TextBox(
            text=text,
            x_left=min(xs),
            y_top=min(ys),
            y_bottom=max(ys),
        ))
    return boxes
