"""Screen region capture via mss."""
import mss
from PIL import Image


def grab(region: dict) -> Image.Image:
    """region: {"left": int, "top": int, "width": int, "height": int} in
    absolute screen coordinates. Returns a PIL RGB image."""
    with mss.mss() as sct:
        shot = sct.grab(region)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def virtual_screen_bounds() -> dict:
    """Bounding box covering all monitors, for the region-select overlay."""
    with mss.mss() as sct:
        return sct.monitors[0]
