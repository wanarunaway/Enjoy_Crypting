# Total Battle Chest History Logger

Watches a screen region while you scroll the game's Chest History list, OCRs
each frame, and merges overlapping scroll frames into one deduplicated log —
text only, no image/icon recognition.

## Setup

```
pip install -r requirements.txt
```

This installs EasyOCR, which pulls in PyTorch (a CPU build on Windows by
default). **First install is large (~1-2 GB) and can take several minutes** —
that's expected, not a hang.

The first time you click **Start Scan**, EasyOCR downloads its recognition
model (tens of MB) to `~/.EasyOCR/model`. This happens once per machine; the
GUI shows "Loading OCR model..." while it happens instead of appearing frozen.

## Running

```
python run.py
```

## Workflow

1. Open Total Battle, open Chest History.
2. In the app, click **Select Region** and drag a rectangle over the chest
   history list. Pick a region tall enough to show at least ~5-6 rows at
   once — the overlap-detection algorithm needs a run of a few matching
   rows between frames to confidently identify the scroll overlap, so a
   very short region increases the chance of a "possible skipped rows"
   warning.
3. Click **Start Scan**.
4. Scroll down through the list slowly, pausing briefly after each scroll
   so the OCR pass can keep up (the status bar shows the observed
   seconds-per-frame once scanning starts — match your scroll pace to it).
5. Click **Stop Scan**.
6. Review the table (columns: Chest, Level, Player, Time — Time is the
   real-world moment each row was captured, not the game's own countdown).
   Rows highlighted yellow mean the app couldn't confidently match an overlap
   between two frames (e.g. you scrolled too far in one jump) — double check
   that section for missing or duplicate rows. Right-click any row to delete
   it if OCR misread something.
7. Click **Save to Database** to commit the session to `chestlog.db`
   (SQLite, created in the project folder).
8. Click **Open Dashboard** anytime to generate `chestlog_dashboard.html`
   (top contributors, chest/level breakdowns, activity over time, a
   searchable table of every row) and open it in your browser. It's a
   self-contained static file — regenerated fresh each time you click the
   button, safe to reopen offline, nothing leaves your machine.

## Tests

The core overlap-detection and row-parsing logic is unit tested with
synthetic data (no game or OCR needed):

```
python -m pytest
```

## Project layout

- `chestlog/merge.py` — the scroll-overlap/dedup algorithm (the core logic)
- `chestlog/rowparser.py` — turns raw OCR text boxes into ordered rows
- `chestlog/capture.py` / `chestlog/ocr.py` — screen grab + EasyOCR wrapper
- `chestlog/session.py` — background worker thread tying the pipeline together
- `chestlog/gui.py` / `chestlog/app.py` — Tkinter UI
- `chestlog/db.py` — SQLite storage (`ChestLog` table)
