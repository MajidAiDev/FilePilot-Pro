from __future__ import annotations

import shutil
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from filepilot.app import FilePilotApp
from filepilot import core


def walk_widgets(parent):
    for widget in parent.winfo_children():
        yield widget
        yield from walk_widgets(widget)


class TestOrganizerUIActions(unittest.TestCase):
    """Small Tk smoke tests for the buttons reported as unresponsive."""

    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.temp = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp.name)
        self.files_root = self.temp_root / "files"
        self.files_root.mkdir()
        (self.files_root / "note.txt").write_text("hello", encoding="utf-8")
        (self.files_root / "image.png").write_bytes(b"image")
        self.journals = self.temp_root / "journals"
        self.journals.mkdir()
        self.journal_patch = patch.object(core, "journal_dir", return_value=self.journals)
        self.journal_patch.start()
        self.app = FilePilotApp(self.root)
        self.app.language = "en"
        self.app.selected_root = str(self.files_root)
        self.app.page = "organizer"
        self.app.start_scan = lambda *args, **kwargs: None
        self.app._render()
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        if hasattr(self, "journal_patch"):
            self.journal_patch.stop()
        if hasattr(self, "temp"):
            self.temp.cleanup()

    def _button(self, label: str):
        for widget in walk_widgets(self.root):
            if isinstance(widget, tk.Button) and widget.cget("text") == label:
                return widget
        self.fail(f"Button not found: {label}")

    def _wait_for_event(self, name: str, timeout: float = 4.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(event == name for event, _payload in list(self.app.events.queue)):
                return
            time.sleep(0.01)
        self.fail(f"Timed out waiting for UI worker event: {name}")


    def test_sidebar_path_shortening_keeps_last_folder_readable(self):
        long_path = r"C:\Users\SarayeTel\Downloads\Compressed"
        compact = self.app._compact_sidebar_path(long_path)
        self.assertIn("Downloads\\Compressed", compact)
        self.assertLessEqual(len(compact), 33)

    def test_build_preview_button_creates_plan_and_rows(self):
        self._button("Build preview").invoke()
        self.assertEqual(len(self.app.organize_plan), 2)
        self.assertTrue(self.app.organizer_preview_built)
        self.assertIn("organize_tree", self.app._widget_refs)

    def test_apply_and_undo_buttons_run_worker_operations(self):
        # Avoid blocking the test in modal dialogs; real dialog controls are tested separately.
        self.app._confirm_dialog = lambda *args, **kwargs: True
        self.app._message_dialog = lambda *args, **kwargs: None
        # Apply from the visible button path, not by calling the core function directly.
        self._button("Apply approved moves").invoke()
        self._wait_for_event("organize_done")
        self.app._process_events()
        self.assertFalse(self.app.busy)
        self.assertTrue((self.files_root / "Documents" / "note.txt").exists())
        self.assertTrue((self.files_root / "Images" / "image.png").exists())

        self._button("Undo latest organization").invoke()
        self._wait_for_event("undo_done")
        self.app._process_events()
        self.assertFalse(self.app.busy)
        self.assertTrue((self.files_root / "note.txt").exists())
        self.assertTrue((self.files_root / "image.png").exists())


    def _schedule_confirmation_click(self, label):
        def _click():
            for window in self.root.winfo_children():
                if isinstance(window, tk.Toplevel):
                    for child in walk_widgets(window):
                        if isinstance(child, tk.Button) and child.cget("text") == label:
                            child.invoke()
                            return
            self.fail(f"Confirmation button not found: {label}")
        self.root.after(100, _click)

    def test_confirmation_yes_button_confirms(self):
        self._schedule_confirmation_click("Yes")
        self.assertTrue(self.app._confirm_dialog("Confirm", "Apply these moves?", file_count=1))

    def test_confirmation_no_button_cancels(self):
        self._schedule_confirmation_click("No")
        self.assertFalse(self.app._confirm_dialog("Confirm", "Apply these moves?", file_count=1))

    def test_message_dialog_ok_button_closes_dialog(self):
        def click_ok():
            widgets = list(walk_widgets(self.root))
            for widget in widgets:
                if isinstance(widget, tk.Button) and widget.cget("text") == "OK":
                    widget.invoke()
                    return
            self.fail("Message dialog OK button not found")
        self.root.after(100, click_ok)
        self.app._message_dialog("Info", "Operation finished.")
        self.assertTrue(True)

    def test_organizer_controls_are_disabled_while_busy(self):
        self.app.busy = True
        self.app.busy_kind = "organize"
        self.app._render()
        for label in ("Build preview", "Apply approved moves", "Undo latest organization"):
            self.assertEqual(self._button(label).cget("state"), "disabled")


if __name__ == "__main__":
    unittest.main()
