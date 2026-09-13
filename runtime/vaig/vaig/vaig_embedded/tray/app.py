"""
VAIG Embedded — macOS Menu Bar App (prototype)
Green/Yellow/Red indicator in system tray
"""
from typing import Optional

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - tkinter is not available on headless CI
    tk = None


class VAIGTray:
    """Minimal system tray indicator for VAIG status."""

    def __init__(self):
        if tk is None:
            raise RuntimeError("tkinter is not available; VAIGTray requires a GUI environment")
        self.root = tk.Tk()
        self.root.withdraw()
        self.status_var = tk.StringVar(value="VAIG: INIT")

    def update_status(self, status: str, score: float):
        """Update tray indicator. status: GREEN/YELLOW/RED"""
        emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
        self.status_var.set(f"VAIG: {emoji.get(status, '⚪')} {status} ({score:.2f})")

    def run(self):
        """Start tray app (blocking)."""
        label = tk.Label(self.root, textvariable=self.status_var)
        label.pack()
        self.root.deiconify()
        self.root.mainloop()
