"""Tkinter GUI: region select, start/stop scan, live review table, save."""
import queue
import tkinter as tk
from tkinter import messagebox, ttk

from chestlog import capture, dashboard, db
from chestlog.models import CapturedRow, Row
from chestlog.ocr import ReaderHolder
from chestlog.session import ScanSession

_POLL_INTERVAL_MS = 100


class RegionSelector(tk.Toplevel):
    """Fullscreen semi-transparent overlay for drag-to-select a screen region."""

    def __init__(self, master, on_selected):
        super().__init__(master)
        self._on_selected = on_selected

        bounds = capture.virtual_screen_bounds()
        self._offset_left = bounds["left"]
        self._offset_top = bounds["top"]
        self.geometry(f"{bounds['width']}x{bounds['height']}+{bounds['left']}+{bounds['top']}")
        self.overrideredirect(True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")

        self._canvas = tk.Canvas(self, bg="gray", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        self._start_x = None
        self._start_y = None
        self._rect_id = None

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda e: self.destroy())

        label = tk.Label(
            self, text="Drag to select the chest history panel  ·  Esc to cancel",
            bg="black", fg="white", font=("Segoe UI", 11),
        )
        label.place(relx=0.5, y=10, anchor="n")

    def _on_press(self, event):
        self._start_x, self._start_y = event.x, event.y
        self._rect_id = self._canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def _on_drag(self, event):
        self._canvas.coords(self._rect_id, self._start_x, self._start_y, event.x, event.y)

    def _on_release(self, event):
        x0, x1 = sorted((self._start_x, event.x))
        y0, y1 = sorted((self._start_y, event.y))
        self.destroy()
        if x1 - x0 < 20 or y1 - y0 < 20:
            return
        region = {
            "left": self._offset_left + x0,
            "top": self._offset_top + y0,
            "width": x1 - x0,
            "height": y1 - y0,
        }
        self._on_selected(region)


class MainWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master.title("Total Battle Chest History Logger")
        self.master.geometry("640x520")

        self._reader_holder = ReaderHolder()
        self._db_conn = db.get_connection()
        self._region: dict | None = None
        self._session: ScanSession | None = None
        self._scanning = False
        self._saved = False

        self._build_widgets()
        self.pack(fill="both", expand=True)

    # --- widget construction -------------------------------------------------

    def _build_widgets(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        self.select_btn = tk.Button(top, text="Select Region", command=self._on_select_region)
        self.select_btn.pack(side="left")

        self.region_label = tk.Label(top, text="No region selected", fg="gray")
        self.region_label.pack(side="left", padx=8)

        controls = tk.Frame(self)
        controls.pack(fill="x", padx=8, pady=4)

        self.start_btn = tk.Button(controls, text="Start Scan", command=self._on_start, state="disabled")
        self.start_btn.pack(side="left")

        self.stop_btn = tk.Button(controls, text="Stop Scan", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)

        self.save_btn = tk.Button(controls, text="Save to Database", command=self._on_save, state="disabled")
        self.save_btn.pack(side="left", padx=4)

        self.dashboard_btn = tk.Button(controls, text="Open Dashboard", command=self._on_open_dashboard)
        self.dashboard_btn.pack(side="left", padx=4)

        self.status_label = tk.Label(self, text="Select a region to begin.", anchor="w")
        self.status_label.pack(fill="x", padx=8)

        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=8, pady=8)

        columns = ("num", "chest_type", "level", "player", "time")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("num", text="#")
        self.tree.heading("chest_type", text="Chest")
        self.tree.heading("level", text="Level")
        self.tree.heading("player", text="Player")
        self.tree.heading("time", text="Time")
        self.tree.column("num", width=40, anchor="center")
        self.tree.column("chest_type", width=200)
        self.tree.column("level", width=140)
        self.tree.column("player", width=140)
        self.tree.column("time", width=150)
        self.tree.tag_configure("gap", background="#fff3b0")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Button-3>", self._on_right_click)
        self._context_menu = tk.Menu(self.tree, tearoff=0)
        self._context_menu.add_command(label="Delete row", command=self._delete_selected_row)

    # --- region select ---------------------------------------------------

    def _on_select_region(self):
        RegionSelector(self.master, self._on_region_selected)

    def _on_region_selected(self, region: dict):
        self._region = region
        self.region_label.config(
            text=f"Region: {region['width']}x{region['height']} at ({region['left']}, {region['top']})",
            fg="black",
        )
        self.start_btn.config(state="normal")
        self.status_label.config(text="Region selected. Ready to scan.")

    # --- scan lifecycle ----------------------------------------------------

    def _on_start(self):
        if not self._region:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._saved = False
        self._session = ScanSession(self._region, self._reader_holder)
        self._session.start()
        self._scanning = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.save_btn.config(state="disabled")
        self.select_btn.config(state="disabled")
        self.status_label.config(text="Starting...")
        self.after(_POLL_INTERVAL_MS, self._poll_queue)

    def _on_stop(self):
        if self._session:
            self._session.stop()
        self.stop_btn.config(state="disabled")

    def _poll_queue(self):
        if not self._session:
            return
        try:
            while True:
                kind, payload = self._session.out_queue.get_nowait()
                self._handle_message(kind, payload)
        except queue.Empty:
            pass

        if self._scanning:
            self.after(_POLL_INTERVAL_MS, self._poll_queue)

    def _handle_message(self, kind: str, payload):
        if kind == "status":
            self.status_label.config(text=payload)
        elif kind == "cadence":
            self.status_label.config(text=f"Scanning — ~{payload:.1f}s/frame. Scroll slowly, pause after each scroll.")
        elif kind == "rows":
            self._append_rows(payload, gap=False)
        elif kind == "gap_rows":
            self._append_rows(payload, gap=True)
            self.status_label.config(
                text="Possible skipped rows detected — check the highlighted section before saving."
            )
        elif kind == "error":
            messagebox.showerror("Scan error", payload)
        elif kind == "done":
            self._scanning = False
            self.select_btn.config(state="normal")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            has_rows = bool(self._session and self._session.rows)
            self.save_btn.config(state="normal" if has_rows else "disabled")
            self.status_label.config(text=f"Scan stopped. {len(self._session.rows) if self._session else 0} rows captured. Review and save.")

    def _append_rows(self, captured_rows: list[CapturedRow], gap: bool):
        tags = ("gap",) if gap else ()
        for cr in captured_rows:
            n = len(self.tree.get_children()) + 1
            self.tree.insert(
                "", "end",
                values=(n, cr.row.chest_type, cr.row.level, cr.row.player, cr.captured_at),
                tags=tags,
            )

    # --- review / edit -------------------------------------------------------

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._context_menu.post(event.x_root, event.y_root)

    def _delete_selected_row(self):
        for item in self.tree.selection():
            self.tree.delete(item)
        self._renumber_rows()

    def _renumber_rows(self):
        for i, item in enumerate(self.tree.get_children(), start=1):
            values = list(self.tree.item(item, "values"))
            values[0] = i
            self.tree.item(item, values=values)

    # --- save ----------------------------------------------------------------

    def _on_save(self):
        if not self._session:
            return
        captured_rows = [
            CapturedRow(
                row=Row(chest_type=values[1], level=values[2], player=values[3]),
                captured_at=values[4],
            )
            for values in (self.tree.item(item, "values") for item in self.tree.get_children())
        ]
        if not captured_rows:
            messagebox.showinfo("Nothing to save", "There are no rows to save.")
            return
        try:
            db.save_session(self._db_conn, self._session.id, captured_rows)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self._saved = True
        self.save_btn.config(text="Saved ✓", state="disabled")
        self.status_label.config(text=f"Saved {len(captured_rows)} rows to database.")

    # --- dashboard -------------------------------------------------------------

    def _on_open_dashboard(self):
        try:
            path = dashboard.open_dashboard(db.DB_PATH)
        except Exception as exc:
            messagebox.showerror("Dashboard failed", str(exc))
            return
        self.status_label.config(text=f"Dashboard opened in browser ({path.name}).")
