from pathlib import Path

# --- Capture pacing ---
CAPTURE_INTERVAL_SECONDS = 1.5  # floor between frame starts; OCR time is added on top

# --- Merge / overlap detection ---
MIN_OVERLAP_ROWS = 3        # consecutive matching rows required to accept an overlap boundary
CHEST_FUZZ_THRESHOLD = 0.82  # SequenceMatcher ratio threshold for chest-type text
LEVEL_FUZZ_THRESHOLD = 0.82  # SequenceMatcher ratio threshold for source/level text
PLAYER_FUZZ_THRESHOLD = 0.82  # SequenceMatcher ratio threshold for player-name text

# --- Row parsing ---
LINE_CLUSTER_TOLERANCE_RATIO = 0.6  # fraction of median box height used to group boxes into lines
EDGE_MARGIN_PX = 15  # rows with a line inside this margin of the frame top/bottom are dropped

# --- Storage ---
DB_PATH = Path(__file__).resolve().parent.parent / "chestlog.db"
