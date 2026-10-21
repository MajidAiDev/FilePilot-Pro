import unittest
from filepilot.i18n import LANGUAGES, TEXT, contains_rtl_characters, display_text, should_shape_rtl, tr


class TestTranslations(unittest.TestCase):
    def test_english_and_persian_are_available(self):
        self.assertIn("en", LANGUAGES)
        self.assertIn("fa", LANGUAGES)

    def test_languages_have_same_translation_keys(self):
        self.assertEqual(set(TEXT["en"]), set(TEXT["fa"]))

    def test_translation_fallback(self):
        self.assertEqual(tr("unknown", "app_title"), TEXT["en"]["app_title"])

    def test_organizer_safety_copy_exists(self):
        self.assertIn("اسکن هیچ فایلی را حذف نمی‌کند", tr("fa", "safety_note"))
        self.assertIn("never deletes files", tr("en", "scan_hint"))

    def test_dashboard_empty_state_exists_in_both_languages(self):
        self.assertIn("یک پوشه انتخاب کنید", tr("fa", "dashboard_empty_subtitle"))
        self.assertIn("Choose a folder", tr("en", "dashboard_empty_subtitle"))
        self.assertIn("build a preview", tr("en", "organizer_empty_subtitle"))

    def test_pure_ltr_sizes_and_duplicate_summaries_do_not_get_rtl_shaping(self):
        self.assertFalse(contains_rtl_characters("1.7 KB"))
        self.assertFalse(should_shape_rtl("fa", "1.7 KB", True))
        self.assertFalse(should_shape_rtl("fa", "146 B", True))
        self.assertFalse(should_shape_rtl("fa", "01 · 2 copies · 146 B", True))
        self.assertFalse(should_shape_rtl("fa", "SHA-256 5bde40a17106", True))

    def test_rtl_strings_still_get_shaped_when_available(self):
        self.assertTrue(contains_rtl_characters("تعداد فایل‌ها"))
        self.assertTrue(should_shape_rtl("fa", "تعداد فایل‌ها", True))
        self.assertFalse(should_shape_rtl("en", "تعداد فایل‌ها", True))
        self.assertFalse(should_shape_rtl("fa", "تعداد فایل‌ها", False))

    def test_display_text_preserves_pure_ltr_values_in_persian_mode(self):
        def fail_if_called(value):
            raise AssertionError("RTL shaping must not run for pure LTR text")

        self.assertEqual(display_text("fa", "1.7 KB", True, fail_if_called, fail_if_called), "1.7 KB")
        self.assertEqual(display_text("fa", "146 B", True, fail_if_called, fail_if_called), "146 B")
        self.assertEqual(display_text("fa", r"D:\Files\sample.txt", True, fail_if_called, fail_if_called), r"D:\Files\sample.txt")

    def test_display_text_shapes_rtl_strings(self):
        calls = []
        def reshape(value):
            calls.append(("reshape", value))
            return "SHAPED:" + value
        def bidi(value, base_dir=None):
            calls.append(("bidi", value, base_dir))
            return "DISPLAY:" + value

        actual = display_text("fa", "نام فایل", True, reshape, bidi)
        self.assertEqual(actual, "DISPLAY:SHAPED:نام فایل")
        self.assertEqual(calls[0][0], "reshape")
        self.assertEqual(calls[1][0], "bidi")
        self.assertEqual(calls[1][2], "R")

    def test_rtl_organizer_copy_is_split_into_short_independent_lines(self):
        subtitle = tr("fa", "organizer_sub")
        self.assertEqual(subtitle, "اول پیش‌نمایش را بسازید")
        for key in ("safety_note_1", "safety_note_2", "safety_note_3"):
            self.assertTrue(contains_rtl_characters(tr("fa", key)))
            self.assertTrue(tr("en", key))

    def test_confirmation_dialog_translations_exist_for_both_languages(self):
        required = (
            "confirm_title", "confirm_moves_intro", "confirm_move_count",
            "confirm_move_folder", "confirm_moves_safety_1",
            "confirm_moves_safety_2", "confirm_moves_safety_3", "confirm_undo_message",
            "confirm_undo_safety", "yes", "no",
        )
        for key in required:
            self.assertIn(key, TEXT["en"])
            self.assertIn(key, TEXT["fa"])
        self.assertIn("هیچ فایلی حذف نمی‌شود", tr("fa", "confirm_moves_safety_1"))

    def test_ui_version_is_consistent(self):
        from filepilot.core import APP_VERSION
        self.assertEqual(APP_VERSION, "1.0.6")
        self.assertIn("۱.۰.۶", tr("fa", "version"))

    def test_rtl_organizer_and_confirmation_copy_is_short(self):
        keys = (
            "organizer_sub", "safety_note_1", "safety_note_2", "safety_note_3",
            "confirm_moves_intro", "confirm_moves_safety_1", "confirm_moves_safety_2",
            "confirm_moves_safety_3", "confirm_undo_message", "confirm_undo_safety",
        )
        for key in keys:
            value = tr("fa", key)
            self.assertLessEqual(len(value), 44, f"RTL copy too long for {key}: {value}")
            self.assertFalse(value.endswith((".", "؟", ":")), f"Avoid trailing directional punctuation: {key}")


if __name__ == "__main__":
    unittest.main()
