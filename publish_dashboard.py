"""Regenerate the dashboard into docs/index.html for GitHub Pages.

Usage: python publish_dashboard.py
Then review the diff and `git add docs/index.html && git commit && git push`
-- publishing is a deliberate, reviewed step, not automatic.
"""
from pathlib import Path

from chestlog import dashboard
from chestlog.config import DB_PATH

if __name__ == "__main__":
    output = Path(__file__).resolve().parent / "docs" / "index.html"
    output.parent.mkdir(exist_ok=True)
    dashboard.write_dashboard(DB_PATH, output)
    print(f"Wrote {output}")
    print("Review it, then: git add docs/index.html && git commit -m 'Update dashboard' && git push")
