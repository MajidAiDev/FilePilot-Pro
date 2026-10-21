from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from filepilot import core


class TestFilePilotCore(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_scan_counts_files_sizes_and_categories(self):
        (self.root / "image.png").write_bytes(b"image-data")
        (self.root / "notes.txt").write_text("hello", encoding="utf-8")
        sub = self.root / "nested"
        sub.mkdir()
        (sub / "script.py").write_text("print('hi')", encoding="utf-8")

        report = core.scan_directory(self.root)

        self.assertEqual(report.file_count, 3)
        self.assertEqual(report.total_bytes, len(b"image-data") + len("hello".encode()) + len("print('hi')".encode()))
        self.assertEqual(report.category_counts["Images"], 1)
        self.assertEqual(report.category_counts["Documents"], 1)
        self.assertEqual(report.category_counts["Code"], 1)

    def test_duplicate_detection_uses_content_not_filename(self):
        first = self.root / "first.dat"
        second = self.root / "renamed.bin"
        different = self.root / "different.dat"
        first.write_bytes(b"identical content")
        second.write_bytes(b"identical content")
        different.write_bytes(b"other content here")

        report = core.scan_directory(self.root)

        self.assertEqual(report.duplicate_group_count, 1)
        self.assertEqual(report.duplicate_groups[0].copies, 2)
        self.assertEqual(report.reclaimable_bytes, len(b"identical content"))
        self.assertEqual(len(report.duplicate_groups[0].sha256), 64)

    def test_scan_is_read_only_and_excludes_filepilot_internal_directory(self):
        user_file = self.root / "keep.txt"
        user_file.write_text("keep", encoding="utf-8")
        hidden = self.root / ".filepilot"
        hidden.mkdir()
        (hidden / "internal.json").write_text("internal", encoding="utf-8")

        report = core.scan_directory(self.root)

        self.assertTrue(user_file.exists())
        self.assertEqual(report.file_count, 1)
        self.assertNotIn(str(hidden / "internal.json"), {f.path for f in report.files})

    def test_scan_rejects_non_directory(self):
        file_path = self.root / "file.txt"
        file_path.write_text("x", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            core.scan_directory(file_path)

    def test_scan_can_be_cancelled(self):
        import threading
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(InterruptedError):
            core.scan_directory(self.root, cancel_event=cancel)

    def test_organize_plan_only_includes_top_level_files(self):
        (self.root / "image.png").write_bytes(b"img")
        (self.root / "document.pdf").write_bytes(b"pdf")
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "nested.txt").write_text("text", encoding="utf-8")

        plan = core.build_organize_plan(self.root)

        self.assertEqual(len(plan), 2)
        by_name = {Path(item.source).name: item for item in plan}
        self.assertEqual(by_name["image.png"].category, "Images")
        self.assertEqual(Path(by_name["image.png"].destination).parent.name, "Images")
        self.assertNotIn("nested.txt", {Path(item.source).name for item in plan})

    def test_apply_and_undo_organization(self):
        (self.root / "image.png").write_bytes(b"img")
        (self.root / "notes.txt").write_bytes(b"notes")
        journal_path = self.root / "journals"
        journal_path.mkdir()
        with patch.object(core, "journal_dir", return_value=journal_path):
            plan = core.build_organize_plan(self.root)
            result = core.apply_organize_plan(plan)
            self.assertEqual(len(result.moved), 2)
            self.assertFalse((self.root / "image.png").exists())
            self.assertTrue((self.root / "Images" / "image.png").exists())
            undo = core.undo_latest_organization()
            self.assertEqual(len(undo["restored"]), 2)
            self.assertTrue((self.root / "image.png").exists())
            self.assertTrue((self.root / "notes.txt").exists())
            self.assertFalse((self.root / "Images" / "image.png").exists())

    def test_move_collision_preserves_existing_destination(self):
        (self.root / "image.png").write_bytes(b"new")
        (self.root / "Images").mkdir()
        (self.root / "Images" / "image.png").write_bytes(b"existing")
        journal_path = self.root / "journals"
        journal_path.mkdir()
        with patch.object(core, "journal_dir", return_value=journal_path):
            result = core.apply_organize_plan(core.build_organize_plan(self.root))
        self.assertEqual(len(result.moved), 1)
        self.assertEqual((self.root / "Images" / "image.png").read_bytes(), b"existing")
        self.assertEqual((self.root / "Images" / "image (1).png").read_bytes(), b"new")

    def test_undo_does_not_overwrite_existing_original_path(self):
        (self.root / "image.png").write_bytes(b"new")
        journal_path = self.root / "journals"
        journal_path.mkdir()
        with patch.object(core, "journal_dir", return_value=journal_path):
            result = core.apply_organize_plan(core.build_organize_plan(self.root))
            (self.root / "image.png").write_bytes(b"new file created later")
            undo = core.undo_latest_organization()
        self.assertEqual(len(undo["restored"]), 0)
        self.assertTrue(undo["errors"])
        self.assertEqual((self.root / "image.png").read_bytes(), b"new file created later")
        self.assertTrue(Path(result.journal_path).exists())

    def test_export_json_csv_and_html(self):
        (self.root / "unsafe&name.txt").write_text("sample", encoding="utf-8")
        report = core.scan_directory(self.root)
        json_path = core.export_json(report, self.root / "exports" / "report.json")
        csv_path = core.export_csv(report, self.root / "exports" / "report.csv")
        html_path = core.export_html(report, self.root / "exports" / "report.html")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["file_count"], 1)
        self.assertIn("unsafe&name.txt", csv_path.read_text(encoding="utf-8-sig"))
        html_content = html_path.read_text(encoding="utf-8")
        self.assertIn("unsafe&amp;name.txt", html_content)
        self.assertNotIn("unsafe&name.txt", html_content)

    def test_csv_export_neutralizes_spreadsheet_formulas(self):
        dangerous = self.root / "=HYPERLINK_example.txt"
        dangerous.write_text("sample", encoding="utf-8")
        report = core.scan_directory(self.root)
        csv_path = core.export_csv(report, self.root / "formula.csv")
        content = csv_path.read_text(encoding="utf-8-sig")
        self.assertIn("'=HYPERLINK", content)

    def test_format_bytes_and_category_fallback(self):
        self.assertEqual(core.format_bytes(0), "0 B")
        self.assertEqual(core.category_for(Path("mystery.qzz")), "Other")
        self.assertEqual(core.category_for(Path("photo.JPG")), "Images")


if __name__ == "__main__":
    unittest.main()
