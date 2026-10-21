import unicodedata


LANGUAGES = {
    "fa": "فارسی",
    "en": "English",
}

TEXT = {
    "en": {
        "app_title": "FilePilot", "tagline": "Smart file organization & storage insights", "version": "DESKTOP EDITION · v1.0.6",
        "language": "Language", "choose_folder": "Choose folder", "scan": "Scan folder", "cancel": "Cancel scan", "export_quick": "Export report",
        "dashboard": "Dashboard", "duplicates": "Duplicate finder", "organizer": "Safe organizer", "reports": "Reports & exports",
        "workspace": "WORKSPACE", "selected_folder": "Selected folder", "no_folder": "No folder selected", "choose_first": "Choose a folder to start scanning.",
        "welcome_title": "Take control of your files.", "welcome_subtitle": "Inventory, duplicate analysis and safe organization in one place.", "dashboard_empty_title": "Your workspace is ready", "dashboard_empty_subtitle": "Choose a folder to review its files, storage usage, and duplicate content. Scanning is read-only.",
        "scan_hint": "FilePilot scans files read-only. It never deletes files during a scan.", "files": "Files scanned", "total_size": "Total size", "duplicate_groups": "Duplicate groups", "reclaimable": "Potentially reclaimable",
        "storage_breakdown": "Storage breakdown", "category": "Category", "count": "Files", "size": "Size", "top_duplicates": "Largest duplicate groups", "no_duplicates": "No identical files were found in this scan.",
        "file_inventory": "File inventory", "name": "Name", "extension": "Type", "modified": "Modified", "path": "Path", "sha": "SHA-256", "status_ready": "Ready", "status_scanning": "Scanning files…", "status_hashing": "Comparing duplicate candidates…", "status_done": "Scan complete", "status_cancelled": "Scan cancelled", "status_error": "Operation failed",
        "duplicates_title": "Find identical files", "duplicates_sub": "Matches are based on SHA-256 content hashes, not just file names.", "group": "Group", "copies": "Copies", "one_size": "One copy", "space_saved": "Potential saving", "open_location": "Open file location", "copy_path": "Copy path", "select_row": "Select a file row first.",
        "organizer_title": "Organize without surprises", "organizer_sub": "Preview changes before moving files.", "safety_note_1": "Scanning never deletes files.", "safety_note_2": "Duplicate destination names get a new unique name.", "safety_note_3": "Undo does not overwrite an existing file.", "make_preview": "Build preview", "apply_moves": "Apply approved moves", "undo_last": "Undo latest organization", "source": "Current location", "destination": "Proposed location", "safety_note": "No files are deleted. Existing destination names are preserved by choosing a unique name. Undo never overwrites an existing original path.", "no_plan": "Build a preview to see suggested moves.", "organizer_empty_title": "Ready to preview a safe organization", "organizer_empty_subtitle": "Choose a folder, then build a preview. No files will move until you approve the plan.", "organizer_no_moves_title": "No moves suggested", "organizer_no_moves_subtitle": "The selected folder has no top-level files that need organizing by the current rules.", "plan_count": "Suggested moves", "confirm_title": "Confirm organization", "confirm_moves": "Move {count} files? No file will be deleted.", "confirm_moves_intro": "Apply the proposed file moves?", "confirm_move_count": "Files to move", "confirm_move_folder": "Selected folder", "confirm_moves_safety_1": "No files will be deleted.", "confirm_moves_safety_2": "Duplicate destination names get a unique name.", "confirm_moves_safety_3": "Use Undo latest organization to restore moves.", "confirm_undo_message": "Undo the latest organization operation?", "confirm_undo_safety": "Existing files will not be overwritten.", "move_done": "Moved {count} files.", "move_partial": "Moved {moved} files; {errors} could not be moved.", "undo_done": "Restored {count} files.", "undo_none": "No organization operation is available to undo.",
        "reports_title": "Export a portable report", "reports_sub": "Create a file inventory and duplicate summary to review, share or archive.", "export_csv": "Export CSV", "export_json": "Export JSON", "export_html": "Export HTML report", "export_before": "Run a scan before exporting a report.", "export_success": "Report saved", "export_failed": "Could not save report", "report_scope": "Reports may contain local file paths. Review them before sharing.",
        "folder_error": "Please choose an existing folder.", "scan_error": "Could not scan this folder:", "cancelled": "Cancel requested…", "scan_running": "A scan is already running.", "empty_folder": "No files found in the selected folder.", "errors": "Warnings", "duration": "Scan time", "seconds": "seconds", "all_categories": "All categories", "files_in_folder": "files in folder", "browse": "Browse…", "ready_subtitle": "Choose a folder, then scan it to view storage insights.",
        "cat_Images": "Images", "cat_Videos": "Videos", "cat_Audio": "Audio", "cat_Documents": "Documents", "cat_Spreadsheets": "Spreadsheets", "cat_Presentations": "Presentations", "cat_Archives": "Archives", "cat_Code": "Code", "cat_Installers": "Installers", "cat_Fonts": "Fonts", "cat_Other": "Other",
        "confirm": "Confirm", "cancel_btn": "Keep safe", "no": "No", "yes": "Yes", "footer": "Read-only scanning · SHA-256 duplicate detection · No automatic deletion", "choose_report_path": "Save report", "all_files": "All scanned files", "duplicate_files": "Duplicate file entries", "reclaimable_note": "Estimated space if all but one copy per group were removed; FilePilot does not remove them.", "no_matches": "No rows to show.", "working": "Working…", "done": "Done", "open_root": "Open selected folder", "select_folder": "Select folder",
    },
    "fa": {
        "app_title": "FilePilot", "tagline": "مدیریت هوشمند فایل‌ها و تحلیل فضای ذخیره‌سازی", "version": "نسخه دسکتاپ · ۱.۰.۶",
        "language": "زبان", "choose_folder": "انتخاب پوشه", "scan": "بررسی پوشه", "cancel": "لغو بررسی", "export_quick": "خروجی گزارش",
        "dashboard": "نمای کلی", "duplicates": "یافتن فایل‌های تکراری", "organizer": "مرتب‌سازی امن", "reports": "گزارش‌ها و خروجی‌ها",
        "workspace": "محیط کار", "selected_folder": "پوشه انتخاب‌شده", "no_folder": "هنوز پوشه‌ای انتخاب نشده", "choose_first": "برای شروع، یک پوشه انتخاب کنید.",
        "welcome_title": "کنترل فایل‌ها را به دست بگیرید.", "welcome_subtitle": "فهرست فایل‌ها، تحلیل موارد تکراری و مرتب‌سازی امن در یک برنامه.", "dashboard_empty_title": "فضای کار آماده است", "dashboard_empty_subtitle": "برای مشاهده فهرست فایل‌ها، فضای مصرفی و فایل‌های تکراری، یک پوشه انتخاب کنید. بررسی اولیه فقط‌خواندنی است.",
        "scan_hint": "بررسی فایل‌ها فقط‌خواندنی است. هنگام اسکن هیچ فایلی حذف نمی‌شود.", "files": "تعداد فایل‌ها", "total_size": "حجم کل", "duplicate_groups": "گروه‌های تکراری", "reclaimable": "فضای قابل‌بازیابی احتمالی",
        "storage_breakdown": "ترکیب فضای ذخیره‌سازی", "category": "دسته‌بندی", "count": "تعداد", "size": "حجم", "top_duplicates": "بزرگ‌ترین گروه‌های تکراری", "no_duplicates": "فایل یکسانی در این بررسی پیدا نشد.",
        "file_inventory": "فهرست فایل‌ها", "name": "نام", "extension": "نوع", "modified": "آخرین تغییر", "path": "مسیر", "sha": "هش SHA-256", "status_ready": "آماده", "status_scanning": "در حال بررسی فایل‌ها…", "status_hashing": "در حال مقایسه فایل‌های هم‌اندازه…", "status_done": "بررسی کامل شد", "status_cancelled": "بررسی لغو شد", "status_error": "عملیات ناموفق بود",
        "duplicates_title": "پیدا کردن فایل‌های یکسان", "duplicates_sub": "تطبیق بر اساس هش محتوای SHA-256 است، نه فقط نام فایل.", "group": "گروه", "copies": "تعداد نسخه‌ها", "one_size": "حجم یک نسخه", "space_saved": "صرفه‌جویی احتمالی", "open_location": "باز کردن محل فایل", "copy_path": "کپی مسیر", "select_row": "ابتدا یک ردیف فایل را انتخاب کنید.",
        "organizer_title": "مرتب‌سازی امن فایل‌ها", "organizer_sub": "اول پیش‌نمایش را بسازید", "safety_note_1": "اسکن هیچ فایلی را حذف نمی‌کند", "safety_note_2": "نام تکراری، نام یکتا می‌گیرد", "safety_note_3": "بازگردانی، فایل موجود را جایگزین نمی‌کند", "make_preview": "ساخت پیش‌نمایش", "apply_moves": "اجرای جابه‌جایی‌های تأییدشده", "undo_last": "بازگرداندن آخرین مرتب‌سازی", "source": "مسیر فعلی", "destination": "مسیر پیشنهادی", "safety_note": "اسکن هیچ فایلی را حذف نمی‌کند. نام تکراری، نام یکتا می‌گیرد. بازگردانی، فایل موجود را جایگزین نمی‌کند", "no_plan": "برای دیدن پیشنهادها، پیش‌نمایش بسازید.", "organizer_empty_title": "آماده‌سازی پیش‌نمایش مرتب‌سازی امن", "organizer_empty_subtitle": "یک پوشه انتخاب کنید و پیش‌نمایش بسازید. تا پیش از تأیید شما هیچ فایلی جابه‌جا نمی‌شود.", "organizer_no_moves_title": "جابه‌جایی پیشنهادی وجود ندارد", "organizer_no_moves_subtitle": "طبق قواعد فعلی، در سطح اصلی این پوشه فایلی برای مرتب‌سازی پیشنهاد نشده است.", "plan_count": "تعداد جابه‌جایی‌های پیشنهادی", "confirm_title": "تأیید مرتب‌سازی", "confirm_moves": "تعداد {count} فایل جابه‌جا شود؟", "confirm_moves_intro": "جابه‌جایی فایل‌های پیشنهادی انجام شود", "confirm_move_count": "تعداد فایل‌ها", "confirm_move_folder": "پوشه مبدأ", "confirm_moves_safety_1": "هیچ فایلی حذف نمی‌شود", "confirm_moves_safety_2": "نام تکراری، نام یکتا می‌گیرد", "confirm_moves_safety_3": "برای بازگردانی، گزینه بازگردانی را بزنید", "confirm_undo_message": "آخرین جابه‌جایی‌ها بازگردانده شود", "confirm_undo_safety": "فایل موجود بازنویسی نمی‌شود", "move_done": "تعداد {count} فایل جابه‌جا شد.", "move_partial": "تعداد {moved} فایل جابه‌جا شد؛ جابه‌جایی {errors} فایل ناموفق بود.", "undo_done": "تعداد {count} فایل بازگردانده شد.", "undo_none": "عملیات مرتب‌سازی برای بازگردانی وجود ندارد.",
        "reports_title": "گزارش قابل‌انتقال بسازید", "reports_sub": "فهرست فایل‌ها و خلاصه فایل‌های تکراری را برای بررسی، اشتراک یا بایگانی ذخیره کنید.", "export_csv": "خروجی CSV", "export_json": "خروجی JSON", "export_html": "گزارش HTML", "export_before": "برای خروجی گرفتن ابتدا پوشه‌ای را بررسی کنید.", "export_success": "گزارش ذخیره شد", "export_failed": "ذخیره گزارش ممکن نشد", "report_scope": "گزارش ممکن است مسیرهای محلی فایل‌ها را داشته باشد. پیش از اشتراک‌گذاری آن را بررسی کنید.",
        "folder_error": "لطفاً یک پوشه موجود انتخاب کنید.", "scan_error": "بررسی این پوشه ممکن نشد:", "cancelled": "درخواست لغو ثبت شد…", "scan_running": "یک بررسی از قبل در حال اجراست.", "empty_folder": "فایلی در پوشه انتخاب‌شده پیدا نشد.", "errors": "هشدارها", "duration": "زمان بررسی", "seconds": "ثانیه", "all_categories": "همه دسته‌ها", "files_in_folder": "فایل در پوشه", "browse": "انتخاب…", "ready_subtitle": "یک پوشه انتخاب کنید و سپس برای مشاهده اطلاعات آن را بررسی کنید.",
        "cat_Images": "تصاویر", "cat_Videos": "ویدئوها", "cat_Audio": "صوتی", "cat_Documents": "اسناد", "cat_Spreadsheets": "صفحه‌گسترده‌ها", "cat_Presentations": "ارائه‌ها", "cat_Archives": "فشرده‌ها", "cat_Code": "کد و برنامه‌نویسی", "cat_Installers": "نصب‌کننده‌ها", "cat_Fonts": "فونت‌ها", "cat_Other": "سایر",
        "confirm": "تأیید", "cancel_btn": "انصراف", "no": "خیر", "yes": "بله", "footer": "بررسی فقط‌خواندنی · شناسایی فایل‌های یکسان بر اساس محتوا · بدون حذف خودکار", "choose_report_path": "ذخیره گزارش", "all_files": "همه فایل‌های بررسی‌شده", "duplicate_files": "ردیف فایل‌های تکراری", "reclaimable_note": "فضای احتمالی در صورت نگه‌داشتن یک نسخه از هر گروه؛ FilePilot فایل‌ها را حذف نمی‌کند.", "no_matches": "ردیفی برای نمایش وجود ندارد.", "working": "در حال انجام…", "done": "انجام شد", "open_root": "باز کردن پوشه انتخاب‌شده", "select_folder": "انتخاب پوشه",
    },
}


def tr(language: str, key: str) -> str:
    lang = language if language in TEXT else "en"
    return TEXT[lang].get(key, TEXT["en"].get(key, key))


def contains_rtl_characters(value: object) -> bool:
    """Return True only when text contains right-to-left letters.

    Pure Latin strings, paths, hashes, numeric values, and byte units must stay
    in their native left-to-right order even while the Persian UI is selected.
    """
    return any(unicodedata.bidirectional(char) in {"R", "AL"} for char in str(value))


def should_shape_rtl(language: str, value: object, rtl_available: bool) -> bool:
    """Tell the UI whether this particular string needs RTL shaping.

    Applying the bidi algorithm to an ASCII-only value such as ``1.7 KB``
    reverses the visible order of number and unit. Shape only strings that
    actually contain RTL letters.
    """
    return language == "fa" and rtl_available and contains_rtl_characters(value)


def display_text(language: str, value: object, rtl_available: bool, reshape=None, bidi_display=None) -> str:
    """Prepare text for Tk widgets without mangling pure LTR values.

    Paths, hashes, English labels, numbers and byte units must remain unchanged.
    Only strings containing actual RTL letters pass through shaping/bidi.
    """
    text = str(value)
    if language != "fa" or not rtl_available or not contains_rtl_characters(text):
        return text
    if reshape is None or bidi_display is None:
        return text
    try:
        return bidi_display(reshape(text), base_dir="R")
    except Exception:
        return text
