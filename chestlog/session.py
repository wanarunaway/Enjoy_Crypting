"""ScanSession: owns the background capture/OCR/merge worker thread and the
running accumulated result for one Start-Scan-to-Stop-Scan scan.

Threading model: one worker thread per session, communicating with the GUI
thread only via a queue.Queue of (kind, payload) messages. The GUI drains
this queue with root.after() polling -- see gui.py.
"""
import queue
import threading
import time
from datetime import datetime

from chestlog import capture, ocr
from chestlog.config import CAPTURE_INTERVAL_SECONDS
from chestlog.merge import align_and_append
from chestlog.models import CapturedRow, Row
from chestlog.rowparser import parse


class ScanSession:
    def __init__(self, region: dict, reader_holder: ocr.ReaderHolder):
        self.id = "session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        self.region = region
        self.rows: list[CapturedRow] = []
        self.out_queue: queue.Queue = queue.Queue()
        self._tail: list[Row] = []
        self._stop_event = threading.Event()
        self._reader_holder = reader_holder
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        try:
            self.out_queue.put(("status", "Loading OCR model (first run may take a minute)..."))
            reader = self._reader_holder.get()
            self.out_queue.put(("status", "Scanning — scroll slowly through the list"))
            while not self._stop_event.is_set():
                t0 = time.monotonic()
                frame = capture.grab(self.region)
                boxes = ocr.read(reader, frame)
                rows = parse(boxes, frame.height)
                appended, self._tail, gap = align_and_append(self._tail, rows)
                if appended:
                    captured_at = datetime.now().isoformat(timespec="seconds")
                    captured_rows = [CapturedRow(row=r, captured_at=captured_at) for r in appended]
                    self.rows.extend(captured_rows)
                    self.out_queue.put(("gap_rows" if gap else "rows", captured_rows))
                elapsed = time.monotonic() - t0
                self.out_queue.put(("cadence", elapsed))
                time.sleep(max(0.0, CAPTURE_INTERVAL_SECONDS - elapsed))
        except Exception as exc:  # surface to GUI instead of dying silently
            self.out_queue.put(("error", str(exc)))
        finally:
            self.out_queue.put(("done", None))
