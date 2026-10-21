from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from .core import (
    APP_VERSION,
    OrganizeItem,
    ScanReport,
    apply_organize_plan,
    build_organize_plan,
    export_csv,
    export_html,
    export_json,
    format_bytes,
    scan_directory,
    undo_latest_organization,
)
from .i18n import LANGUAGES, display_text, tr

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as bidi_get_display
    RTL_AVAILABLE = True
except ImportError:
    arabic_reshaper = None
    bidi_get_display = None
    RTL_AVAILABLE = False


BG = "#0A1020"
PANEL = "#121B30"
PANEL_ALT = "#17233B"
BORDER = "#263653"
TEXT = "#EEF4FF"
MUTED = "#9BACCA"
MINT = "#2EE6C4"
BLUE = "#80A0FF"
AMBER = "#FFBE55"
RED = "#FF7088"


class FilePilotApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.language = "fa" if RTL_AVAILABLE else "en"
        self.page = "dashboard"
        self.selected_root = ""
        self.report: ScanReport | None = None
        self.organize_plan: list[OrganizeItem] = []
        self.organizer_preview_built = False
        self.busy = False
        self.busy_kind = "idle"
        self.cancel_event = threading.Event()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.status_key = "status_ready"
        self.status_detail = ""
        self._widget_refs: dict[str, object] = {}
        self._setup_style()
        self.root.title("FilePilot | Smart File Organizer")
        self.root.geometry("1280x800")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG)
        self._render()
        self.root.after(100, self._process_events)

    def t(self, key: str) -> str:
        return tr(self.language, key)

    def _footer_status_text(self, key: str | None = None, detail: str = "") -> str:
        """Avoid mixed Persian/Latin separators in the RTL status line."""
        base = self.t(key or self.status_key)
        if self.language == "fa" or not detail:
            return base
        return f"{base} · {detail}"

    def _display(self, value: object) -> str:
        return display_text(
            self.language, value, RTL_AVAILABLE,
            reshape=arabic_reshaper.reshape if RTL_AVAILABLE else None,
            bidi_display=bidi_get_display if RTL_AVAILABLE else None,
        )

    def _content_anchor(self) -> str:
        return "e" if self.language == "fa" else "w"

    def _content_wrap(self, horizontal_margin: int = 300, minimum: int = 420, maximum: int = 1000) -> int:
        try:
            width = int(self.root.winfo_width())
        except Exception:
            width = 1280
        if width < 100:
            width = 1280
        return max(minimum, min(maximum, width - horizontal_margin))

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("FP.Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=30, borderwidth=0, font=("Segoe UI", 9))
        style.configure("FP.Treeview.Heading", background=PANEL_ALT, foreground=MINT,
                        relief="flat", borderwidth=0, font=("Segoe UI", 9, "bold"), padding=(8, 8))
        style.map("FP.Treeview", background=[("selected", "#21475A")], foreground=[("selected", TEXT)])
        style.configure("FP.Horizontal.TProgressbar", troughcolor=PANEL_ALT, background=MINT,
                        bordercolor=PANEL_ALT, lightcolor=MINT, darkcolor=MINT, thickness=9)
        style.configure("FP.TCombobox", fieldbackground=PANEL_ALT, background=PANEL_ALT,
                        foreground=TEXT, arrowcolor=MINT, bordercolor=BORDER, padding=7)
        style.map("FP.TCombobox", fieldbackground=[("readonly", PANEL_ALT)],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", PANEL_ALT)],
                  selectforeground=[("readonly", TEXT)])

    def _render(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self._widget_refs.clear()
        self.root.title("FilePilot | Smart File Organizer")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self._build_header()
        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        rtl = self.language == "fa"
        if rtl:
            body.grid_columnconfigure(0, weight=1)
            body.grid_columnconfigure(1, weight=0)
            self.workspace = tk.Frame(body, bg=BG)
            self.workspace.grid(row=0, column=0, sticky="nsew", padx=(18, 0), pady=(12, 10))
            self._build_sidebar(body, side_column=1, side_padx=(14, 18))
        else:
            body.grid_columnconfigure(0, weight=0)
            body.grid_columnconfigure(1, weight=1)
            self._build_sidebar(body, side_column=0, side_padx=(18, 14))
            self.workspace = tk.Frame(body, bg=BG)
            self.workspace.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=(12, 10))
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(0, weight=0)
        self._render_page()
        self._build_footer()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=BG, highlightbackground=BORDER, highlightthickness=0)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 5))
        rtl = self.language == "fa"
        header.grid_columnconfigure(1, weight=1, minsize=150)
        logo_col = 2 if rtl else 0
        name_col = 1
        controls_col = 0 if rtl else 2
        logo = tk.Frame(header, bg=MINT, width=54, height=54)
        logo.grid(row=0, column=logo_col, rowspan=2, sticky="e" if rtl else "w",
                  padx=(12, 0) if rtl else (0, 12))
        logo.grid_propagate(False)
        tk.Label(logo, text="F", bg=MINT, fg=BG, font=("Segoe UI", 27, "bold")).place(relx=.5, rely=.48, anchor="center")
        name_row = tk.Frame(header, bg=BG)
        name_row.grid(row=0, column=name_col, sticky="se" if rtl else "sw")
        tk.Label(name_row, text="FILE", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Label(name_row, text="PILOT", bg=BG, fg=MINT, font=("Segoe UI", 22, "bold")).pack(side="left")
        tagline = tk.Label(header, text=self._display(self.t("tagline")), bg=BG, fg=MUTED,
                           font=("Segoe UI", 9), anchor="e" if rtl else "w",
                           justify="right" if rtl else "left", wraplength=360)
        tagline.grid(row=1, column=name_col, sticky="ne" if rtl else "nw", pady=(0, 2))

        controls = tk.Frame(header, bg=BG)
        controls.grid(row=0, column=controls_col, rowspan=2, sticky="w" if rtl else "e")
        tk.Label(controls, text=self._display(self.t("language")), bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(0, 7))
        lang_box = ttk.Combobox(controls, style="FP.TCombobox", state="readonly", width=10,
                                values=[self._display(LANGUAGES[code]) for code in LANGUAGES])
        lang_box.set(self._display(LANGUAGES[self.language]))
        lang_box.pack(side="left", padx=(0, 9))
        lang_box.bind("<<ComboboxSelected>>", self._on_language_change)
        self._widget_refs["language_box"] = lang_box
        folder_button = self._button(controls, self.t("choose_folder"), self.choose_folder, kind="secondary")
        folder_button.pack(side="left", padx=4)
        if self.busy:
            folder_button.configure(state="disabled")
        if self.busy and self.busy_kind == "scan":
            action_text, action_command = self.t("cancel"), self.cancel_scan
        elif self.busy:
            action_text, action_command = self.t("working"), lambda: None
        else:
            action_text, action_command = self.t("scan"), self.start_scan
        action = self._button(controls, action_text, action_command, kind="primary")
        action.pack(side="left", padx=(4, 0))
        if self.busy and self.busy_kind != "scan":
            action.configure(state="disabled", disabledforeground=BG)
        self._widget_refs["header_action"] = action

    def _build_sidebar(self, parent: tk.Frame, side_column: int = 0, side_padx: tuple[int, int] = (18, 14)) -> None:
        side = tk.Frame(parent, bg=PANEL, width=226, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=side_column, sticky="ns", padx=side_padx, pady=(12, 10))
        side.grid_propagate(False)
        anchor = self._content_anchor()
        workspace_label = self._label(side, self.t("workspace").upper(), color=MUTED, size=9, bold=True)
        workspace_label.pack(fill="x", anchor=anchor, padx=18, pady=(22, 12))
        nav_items = [
            ("dashboard", "▦", "dashboard"),
            ("duplicates", "⧉", "duplicates"),
            ("organizer", "⇄", "organizer"),
            ("reports", "▤", "reports"),
        ]
        for page, glyph, label_key in nav_items:
            selected = page == self.page
            btn = tk.Button(
                side, text=self._display(f"  {glyph}    {self.t(label_key)}"),
                command=lambda p=page: self.go_page(p),
                bg="#1D304A" if selected else PANEL, fg=MINT if selected else TEXT,
                activebackground="#1D304A", activeforeground=MINT,
                font=("Segoe UI", 10, "bold" if selected else "normal"),
                relief="flat", bd=0, anchor=anchor, justify="right" if self.language == "fa" else "left",
                padx=8, pady=12, cursor="hand2",
            )
            btn.pack(fill="x", padx=10, pady=3)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(20, 15))
        selected_label = self._label(side, self.t("selected_folder"), color=MUTED, size=9, bold=True)
        selected_label.pack(fill="x", anchor=anchor, padx=18, pady=(0, 7))
        if self.selected_root:
            # Keep real paths in native LTR form so users can read/copy them accurately.
            folder_label = tk.Label(side, text=self.selected_root, bg=PANEL, fg=TEXT,
                                    font=("Segoe UI", 9), anchor="nw", justify="left", wraplength=185)
        else:
            folder_label = tk.Label(side, text=self._display(self.t("no_folder")), bg=PANEL, fg=TEXT,
                                    font=("Segoe UI", 9), anchor="ne" if self.language == "fa" else "nw",
                                    justify="right" if self.language == "fa" else "left", wraplength=185)
        folder_label.pack(fill="x", padx=18)
        self._widget_refs["sidebar_folder"] = folder_label
        hint = self._label(side, self.t("scan_hint"), color=MUTED, size=8, wrap=185)
        hint.pack(fill="x", anchor=anchor, padx=18, pady=(22, 0))
        tk.Label(side, text=f"FILEPILOT  ·  {APP_VERSION}", bg=PANEL, fg=MINT,
                 font=("Segoe UI", 9, "bold")).pack(side="bottom", anchor="w", padx=18, pady=18)

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=BG)
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        footer.grid_columnconfigure(1, weight=1)
        status_text = self._footer_status_text(self.status_key, self.status_detail)
        # Keep the status message separate from decorative glyphs. Passing a
        # prefixed bullet through the RTL bidi algorithm can move it to the
        # opposite visual side in Persian.
        status = tk.Label(
            footer, text=self._display(status_text), bg=BG,
            fg=MINT if not self.busy else AMBER, font=("Segoe UI", 9),
            anchor="e" if self.language == "fa" else "w",
            justify="right" if self.language == "fa" else "left",
        )
        if self.language == "fa":
            status.grid(row=0, column=2, sticky="e")
        else:
            status.grid(row=0, column=0, sticky="w")
        self._widget_refs["footer_status"] = status
        self.progress = ttk.Progressbar(footer, style="FP.Horizontal.TProgressbar", mode="determinate", maximum=100, length=180)
        self.progress.grid(row=0, column=0 if self.language == "fa" else 2,
                           sticky="w" if self.language == "fa" else "e",
                           padx=(0, 14) if self.language == "fa" else (14, 0))
        if self.busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start(9)

    def _render_page(self) -> None:
        for child in self.workspace.winfo_children():
            child.destroy()
        if self.page == "dashboard":
            self._page_dashboard()
        elif self.page == "duplicates":
            self._page_duplicates()
        elif self.page == "organizer":
            self._page_organizer()
        else:
            self._page_reports()

    def _label(self, parent: tk.Widget, text: str, *, color: str = TEXT, size: int = 10,
               bold: bool = False, wrap: int = 0, **kwargs) -> tk.Label:
        raw = kwargs.pop("raw", False)
        default_justify = "right" if self.language == "fa" else "left"
        default_anchor = "e" if self.language == "fa" else "w"
        label = tk.Label(parent, text=str(text) if raw else self._display(text), bg=kwargs.pop("bg", PANEL), fg=color,
                         font=("Segoe UI", size, "bold" if bold else "normal"),
                         justify=kwargs.pop("justify", default_justify), anchor=kwargs.pop("anchor", default_anchor),
                         wraplength=wrap, **kwargs)
        return label

    def _button(self, parent: tk.Widget, text: str, command, kind: str = "secondary", **kwargs) -> tk.Button:
        if kind == "primary":
            bg, fg, active = MINT, BG, "#59F0D7"
        elif kind == "danger":
            bg, fg, active = "#472537", "#FFB6C5", "#5A2A40"
        else:
            bg, fg, active = PANEL_ALT, TEXT, "#20324E"
        return tk.Button(parent, text=self._display(text), command=command, bg=bg, fg=fg,
                         activebackground=active, activeforeground=fg, relief="flat", bd=0,
                         font=("Segoe UI", 9, "bold"), padx=13, pady=9, cursor="hand2", **kwargs)

    def _title_block(self, title_key: str, subtitle_key: str) -> None:
        wrap = self._content_wrap(horizontal_margin=320, minimum=420, maximum=1000)
        self._label(self.workspace, self.t(title_key), bg=BG, size=22, bold=True, wrap=wrap).grid(row=0, column=0, sticky="ew", pady=(5, 2))
        self._label(self.workspace, self.t(subtitle_key), bg=BG, color=MUTED, size=10, wrap=wrap).grid(row=1, column=0, sticky="ew", pady=(0, 15))

    def _card(self, parent: tk.Widget, title: str, value: str, detail: str, accent: str = MINT) -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Frame(card, bg=accent, height=3).pack(fill="x")
        body = tk.Frame(card, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=13)
        anchor = self._content_anchor()
        self._label(body, title, color=MUTED, size=9, bold=True).pack(fill="x", anchor=anchor)
        self._label(body, value, color=accent, size=22, bold=True).pack(fill="x", anchor=anchor, pady=(8, 3))
        self._label(body, detail, color=MUTED, size=8, wrap=300).pack(fill="x", anchor=anchor)
        return card

    def _tree(self, parent: tk.Widget, columns: list[tuple[str, str, int]], height: int = 9) -> ttk.Treeview:
        ids = [item[0] for item in columns]
        tree = ttk.Treeview(parent, columns=ids, show="headings", style="FP.Treeview", height=height)
        # The hidden tree column otherwise contributes a default width and causes needless x-scrolling.
        tree.column("#0", width=0, minwidth=0, stretch=False)
        for col_id, heading, width in columns:
            heading_anchor = "e" if self.language == "fa" else "w"
            tree.heading(col_id, text=self._display(heading), anchor=heading_anchor)
            cell_anchor = "e" if self.language == "fa" and col_id in {"category", "name", "group"} else "w"
            tree.column(col_id, width=width, minwidth=max(55, width // 2), anchor=cell_anchor, stretch=True)
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        return tree

    def _page_dashboard(self) -> None:
        self.workspace.grid_columnconfigure(0, weight=1)
        report = self.report
        self._title_block("welcome_title", "welcome_subtitle")
        scope = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        scope.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        self._label(scope, self.t("selected_folder"), color=MUTED, size=9, bold=True).pack(fill="x", anchor=self._content_anchor(), padx=14, pady=(10, 2))
        self._label(scope, self.selected_root or self.t("choose_first"), color=TEXT, size=10, wrap=self._content_wrap(horizontal_margin=360, minimum=360, maximum=920), raw=bool(self.selected_root)).pack(fill="x", anchor=self._content_anchor(), padx=14, pady=(0, 10))
        self._widget_refs["scope"] = scope

        if not report:
            # Do not display empty statistic cards before the first scan. Give the user a clear next action.
            self.workspace.grid_rowconfigure(3, weight=1)
            empty = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            empty.grid(row=3, column=0, sticky="nsew")
            self._label(empty, self.t("dashboard_empty_title"), size=18, bold=True).pack(
                fill="x", anchor=self._content_anchor(), padx=24, pady=(38, 10))
            self._label(empty, self.t("dashboard_empty_subtitle"), color=MUTED, size=10,
                        wrap=self._content_wrap(horizontal_margin=380, minimum=380, maximum=900)).pack(
                fill="x", anchor=self._content_anchor(), padx=24, pady=(0, 20))
            if self.selected_root:
                self._button(empty, self.t("scan"), self.start_scan, kind="primary").pack(
                    anchor=self._content_anchor(), padx=24, pady=(0, 28))
            else:
                self._button(empty, self.t("choose_folder"), self.choose_folder, kind="primary").pack(
                    anchor=self._content_anchor(), padx=24, pady=(0, 28))
            return

        metric_frame = tk.Frame(self.workspace, bg=BG)
        metric_frame.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        # Two columns prevent the dashboard from expanding beyond smaller/DPI-scaled screens.
        for col in range(2):
            metric_frame.grid_columnconfigure(col, weight=1, uniform="metrics")
        values = [
            ("files", f"{report.file_count:,}" if report else "—", self.t("all_files"), BLUE),
            ("total_size", format_bytes(report.total_bytes) if report else "—", self.t("storage_breakdown"), MINT),
            ("duplicate_groups", f"{report.duplicate_group_count:,}" if report else "—", self.t("duplicate_files") if report else self.t("choose_first"), AMBER),
            ("reclaimable", format_bytes(report.reclaimable_bytes) if report else "—", self.t("reclaimable_note"), RED),
        ]
        for index, (key, value, detail, accent) in enumerate(values):
            row, col = divmod(index, 2)
            if self.language == "fa":
                col = 1 - col
            card = self._card(metric_frame, self.t(key), value, detail, accent)
            padx = ((6, 0) if col == 1 else (0, 6)) if self.language == "fa" else ((0, 6) if col == 0 else (6, 0))
            card.grid(row=row, column=col, sticky="nsew", padx=padx,
                      pady=(0, 8) if row == 0 else (0, 0))

        self.workspace.grid_rowconfigure(4, weight=1)
        lower = tk.Frame(self.workspace, bg=BG)
        lower.grid(row=4, column=0, sticky="nsew")
        lower.grid_columnconfigure(0, weight=1, uniform="lower")
        lower.grid_columnconfigure(1, weight=1, uniform="lower")
        lower.grid_rowconfigure(0, weight=1)
        category_col = 1 if self.language == "fa" else 0
        duplicate_col = 0 if self.language == "fa" else 1
        category_panel = tk.Frame(lower, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        category_panel.grid(row=0, column=category_col, sticky="nsew", padx=(7, 0) if self.language == "fa" else (0, 7))
        self._label(category_panel, self.t("storage_breakdown"), size=12, bold=True).pack(fill="x", anchor=self._content_anchor(), padx=15, pady=(13, 10))
        if report and report.category_counts:
            order = sorted(report.category_counts.items(), key=lambda pair: report.category_bytes.get(pair[0], 0), reverse=True)[:5]
            max_bytes = max((report.category_bytes.get(cat, 0) for cat, _ in order), default=1) or 1
            for cat, count in order:
                row = tk.Frame(category_panel, bg=PANEL)
                row.pack(fill="x", padx=15, pady=5)
                self._label(row, self._category_name(cat), color=TEXT, size=9).pack(side="right" if self.language == "fa" else "left")
                self._label(row, f"{count:,}", color=MUTED, size=9).pack(side="left" if self.language == "fa" else "right")
                bar = ttk.Progressbar(category_panel, style="FP.Horizontal.TProgressbar", maximum=max_bytes,
                                      value=report.category_bytes.get(cat, 0))
                bar.pack(fill="x", padx=15, pady=(0, 2))
                self._label(category_panel, format_bytes(report.category_bytes.get(cat, 0)), color=MUTED, size=8).pack(anchor="w", padx=15)
        else:
            self._label(category_panel, self.t("ready_subtitle"), color=MUTED, wrap=420).pack(fill="x", anchor=self._content_anchor(), padx=15, pady=20)

        dup_panel = tk.Frame(lower, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        dup_panel.grid(row=0, column=duplicate_col, sticky="nsew", padx=(0, 7) if self.language == "fa" else (7, 0))
        self._label(dup_panel, self.t("top_duplicates"), size=12, bold=True).pack(fill="x", anchor=self._content_anchor(), padx=15, pady=(13, 10))
        if report and report.duplicate_groups:
            for number, group in enumerate(report.duplicate_groups[:5], start=1):
                row = tk.Frame(dup_panel, bg=PANEL_ALT)
                row.pack(fill="x", padx=12, pady=4)
                txt = f"{number:02d}  ·  {group.copies} copies  ·  {format_bytes(group.size)}"
                self._label(row, txt, color=TEXT, size=9, bold=True).pack(anchor="w", padx=10, pady=(7, 2))
                self._label(row, format_bytes(group.reclaimable_bytes) + f"  ·  SHA-256 {group.sha256[:12]}…", color=MUTED, size=8).pack(anchor="w", padx=10, pady=(0, 7))
            self._button(dup_panel, self.t("duplicates"), lambda: self.go_page("duplicates"), kind="secondary").pack(anchor="w", padx=12, pady=7)
        else:
            self._label(dup_panel, self.t("no_duplicates") if report else self.t("choose_first"), color=MUTED, wrap=420).pack(fill="x", anchor=self._content_anchor(), padx=15, pady=20)

    def _page_duplicates(self) -> None:
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(3, weight=1)
        self._title_block("duplicates_title", "duplicates_sub")
        if self.report:
            summary = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            summary.grid(row=2, column=0, sticky="ew", pady=(0, 12))
            summary_text = f"{self.t('duplicate_groups')}: {self.report.duplicate_group_count:,}    ·    {self.t('duplicate_files')}: {self.report.duplicate_file_count:,}    ·    {self.t('space_saved')}: {format_bytes(self.report.reclaimable_bytes)}"
            self._label(summary, summary_text, color=MINT, size=10, bold=True, wrap=self._content_wrap(horizontal_margin=360, minimum=400, maximum=1000)).pack(fill="x", anchor=self._content_anchor(), padx=14, pady=12)
        table_wrap = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        table_wrap.grid(row=3, column=0, sticky="nsew")
        duplicate_columns = [("group", self.t("group"), 60), ("name", self.t("name"), 140), ("size", self.t("size"), 85), ("sha", self.t("sha"), 120), ("path", self.t("path"), 280)]
        if self.language == "fa":
            duplicate_columns.reverse()
        tree = self._tree(table_wrap, duplicate_columns, height=14)
        self._widget_refs["duplicate_tree"] = tree
        if self.report:
            row_num = 0
            for group_number, group in enumerate(self.report.duplicate_groups, start=1):
                for path_str in group.paths:
                    path = Path(path_str)
                    row_values = (group_number, self._display(path.name), format_bytes(group.size), group.sha256[:18] + "…", str(path))
                    if self.language == "fa":
                        row_values = tuple(reversed(row_values))
                    tree.insert("", "end", iid=f"dup_{row_num}", values=row_values)
                    row_num += 1
        actions = tk.Frame(self.workspace, bg=BG)
        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self._button(actions, self.t("copy_path"), self.copy_selected_duplicate_path).pack(side="left", padx=(0, 7))
        self._button(actions, self.t("open_location"), self.open_selected_duplicate_location).pack(side="left")
        if not self.report or not self.report.duplicate_groups:
            self._label(self.workspace, self.t("no_duplicates") if self.report else self.t("choose_first"), bg=BG, color=MUTED).grid(row=5, column=0, sticky="e" if self.language == "fa" else "w", pady=8)

    def _page_organizer(self) -> None:
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(4, weight=1)
        self._title_block("organizer_title", "organizer_sub")
        safety = tk.Frame(self.workspace, bg="#172A2C", highlightbackground="#1C6357", highlightthickness=1)
        safety.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        # Render each safety sentence independently. A multi-sentence RTL
        # paragraph plus a leading bullet can reorder punctuation and the icon.
        safety_lines = tk.Frame(safety, bg="#172A2C")
        safety_lines.pack(fill="x", padx=13, pady=9)
        for index, key in enumerate(("safety_note_1", "safety_note_2", "safety_note_3")):
            line = self._label(
                safety_lines, self.t(key), color="#8EEEDD", size=9,
                wrap=self._content_wrap(horizontal_margin=380, minimum=360, maximum=1000),
                bg="#172A2C",
            )
            line.pack(fill="x", anchor=self._content_anchor(), pady=(0, 3 if index < 2 else 0))
        actions = tk.Frame(self.workspace, bg=BG)
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._button(actions, self.t("make_preview"), self.make_organize_preview, kind="secondary").pack(side="left", padx=(0, 7))
        apply_button = self._button(actions, self.t("apply_moves"), self.apply_organization, kind="primary")
        apply_button.pack(side="left", padx=(0, 7))
        self._button(actions, self.t("undo_last"), self.undo_organization, kind="danger").pack(side="left")
        self._label(actions, f"{self.t('plan_count')}: {len(self.organize_plan):,}", bg=BG, color=MINT, size=9, bold=True).pack(side="right")

        if not self.organize_plan:
            empty = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            empty.grid(row=4, column=0, sticky="nsew")
            if not self.selected_root:
                title_key, subtitle_key = "organizer_empty_title", "organizer_empty_subtitle"
                button_key, command = "choose_folder", self.choose_folder
            elif self.organizer_preview_built:
                title_key, subtitle_key = "organizer_no_moves_title", "organizer_no_moves_subtitle"
                button_key, command = "make_preview", self.make_organize_preview
            else:
                title_key, subtitle_key = "organizer_empty_title", "organizer_empty_subtitle"
                button_key, command = "make_preview", self.make_organize_preview
            self._label(empty, self.t(title_key), size=16, bold=True).pack(fill="x", anchor=self._content_anchor(), padx=22, pady=(32, 8))
            self._label(empty, self.t(subtitle_key), color=MUTED, size=10,
                        wrap=self._content_wrap(horizontal_margin=360, minimum=380, maximum=900)).pack(
                            fill="x", anchor=self._content_anchor(), padx=22, pady=(0, 18))
            self._button(empty, self.t(button_key), command, kind="primary").pack(
                anchor=self._content_anchor(), padx=22, pady=(0, 24))
            return

        table_wrap = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        table_wrap.grid(row=4, column=0, sticky="nsew")
        organizer_columns = [
            ("category", self.t("category"), 105), ("name", self.t("name"), 165),
            ("size", self.t("size"), 80), ("source", self.t("source"), 205),
            ("destination", self.t("destination"), 205),
        ]
        if self.language == "fa":
            organizer_columns.reverse()
        tree = self._tree(table_wrap, organizer_columns, height=13)
        self._widget_refs["organize_tree"] = tree
        for i, item in enumerate(self.organize_plan):
            row_values = (self._display(self._category_name(item.category)), self._display(Path(item.source).name),
                          format_bytes(item.size), item.source, item.destination)
            if self.language == "fa":
                row_values = tuple(reversed(row_values))
            tree.insert("", "end", iid=f"org_{i}", values=row_values)

    def _page_reports(self) -> None:
        self.workspace.grid_columnconfigure(0, weight=1)
        self._title_block("reports_title", "reports_sub")
        card = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self._label(card, self.t("report_scope"), color=AMBER, size=10, wrap=self._content_wrap(horizontal_margin=360, minimum=400, maximum=1000)).pack(fill="x", anchor=self._content_anchor(), padx=16, pady=14)
        buttons = tk.Frame(card, bg=PANEL)
        buttons.pack(anchor="w", padx=16, pady=(0, 16))
        self._button(buttons, self.t("export_csv"), lambda: self.export_report("csv"), kind="primary").pack(side="left", padx=(0, 8))
        self._button(buttons, self.t("export_json"), lambda: self.export_report("json")).pack(side="left", padx=(0, 8))
        self._button(buttons, self.t("export_html"), lambda: self.export_report("html")).pack(side="left")
        summary = tk.Frame(self.workspace, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        summary.grid(row=3, column=0, sticky="ew")
        self._label(summary, self.t("file_inventory"), size=12, bold=True).pack(fill="x", anchor=self._content_anchor(), padx=16, pady=(14, 6))
        if self.report:
            lines = [
                f"{self.t('selected_folder')}: {self.report.root}",
                f"{self.t('files')}: {self.report.file_count:,}",
                f"{self.t('total_size')}: {format_bytes(self.report.total_bytes)}",
                f"{self.t('duplicate_groups')}: {self.report.duplicate_group_count:,}",
                f"{self.t('reclaimable')}: {format_bytes(self.report.reclaimable_bytes)}",
                f"{self.t('duration')}: {self.report.duration_seconds:.2f} {self.t('seconds')}",
                f"{self.t('errors')}: {len(self.report.errors):,}",
            ]
            for line in lines:
                self._label(summary, line, color=MUTED, size=9, wrap=self._content_wrap(horizontal_margin=360, minimum=400, maximum=1000)).pack(fill="x", anchor=self._content_anchor(), padx=16, pady=3)
        else:
            self._label(summary, self.t("export_before"), color=MUTED, size=10).pack(fill="x", anchor=self._content_anchor(), padx=16, pady=(6, 16))

    def _category_name(self, category: str) -> str:
        return self.t("cat_" + category)

    def _on_language_change(self, _event=None) -> None:
        combo = self._widget_refs.get("language_box")
        if not combo:
            return
        selected = combo.get()
        for code, label in LANGUAGES.items():
            if self._display(label) == selected:
                if code == "fa" and not RTL_AVAILABLE:
                    messagebox.showwarning("FilePilot", "Persian right-to-left support is missing. Run install_dependencies.bat, then restart FilePilot.", parent=self.root)
                    self.language = "en"
                else:
                    self.language = code
                break
        self._render()

    def go_page(self, page: str) -> None:
        self.page = page
        self._render()

    def choose_folder(self) -> None:
        initial = self.selected_root if self.selected_root and Path(self.selected_root).is_dir() else str(Path.home())
        folder = filedialog.askdirectory(title=self.t("select_folder"), initialdir=initial, mustexist=True)
        if not folder:
            return
        self.selected_root = str(Path(folder).resolve())
        self.report = None
        self.organize_plan = []
        self.organizer_preview_built = False
        self.status_key = "status_ready"
        self.status_detail = ""
        self._render()

    def start_scan(self, silent: bool = False) -> None:
        if self.busy:
            if not silent:
                messagebox.showinfo(self._display(self.t("app_title")), self._display(self.t("scan_running")), parent=self.root)
            return
        if not self.selected_root or not Path(self.selected_root).is_dir():
            if not silent:
                self.choose_folder()
            if not self.selected_root:
                return
        self.busy = True
        self.busy_kind = "scan"
        self.cancel_event = threading.Event()
        self.status_key = "status_scanning"
        self.status_detail = ""
        self._render()

        root_to_scan = self.selected_root
        def worker() -> None:
            try:
                report = scan_directory(root_to_scan, progress=lambda *args: self.events.put(("scan_progress", args)), cancel_event=self.cancel_event)
                self.events.put(("scan_done", report))
            except InterruptedError:
                self.events.put(("scan_cancelled", None))
            except Exception as exc:
                self.events.put(("error", ("scan", str(exc))))
        threading.Thread(target=worker, daemon=True, name="FilePilot-Scan").start()

    def cancel_scan(self) -> None:
        if self.busy and self.busy_kind == "scan":
            self.cancel_event.set()
            self.status_key = "cancelled"
            status = self._widget_refs.get("footer_status")
            if status:
                status.configure(text=self._display(self.t("cancelled")))

    def make_organize_preview(self) -> None:
        if not self.selected_root or not Path(self.selected_root).is_dir():
            self.choose_folder()
            if not self.selected_root:
                return
        try:
            self.organize_plan = build_organize_plan(self.selected_root)
            self.organizer_preview_built = True
            self.status_key = "status_ready"
            self.status_detail = f"{len(self.organize_plan)} moves previewed"
            self._render()
        except Exception as exc:
            messagebox.showerror(self._display(self.t("status_error")), self._display(f"{self.t('scan_error')}\n{exc}"), parent=self.root)

    def _confirm_dialog(
        self,
        title: str,
        message: str,
        *,
        file_count: int | None = None,
        selected_folder: str | None = None,
        safety_lines: tuple[str, ...] = (),
    ) -> bool:
        """Show an application-owned confirmation dialog that renders RTL text reliably.

        Native Windows message boxes do not reliably honor text that was already
        reshaped/reordered for Tk, which caused Persian confirmation messages to
        appear backwards. Keep all user-facing text in normal Tk labels instead.
        The safe/cancel choice is focused by default.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title("FilePilot - Confirmation")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.geometry("640x380")

        result = {"confirmed": False}
        outer = tk.Frame(dialog, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        header = tk.Frame(outer, bg=PANEL_ALT)
        header.pack(fill="x")
        tk.Label(
            header, text="!", bg=AMBER, fg=BG, width=3, height=1,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="right", padx=(14, 10), pady=12)
        self._label(
            header, title, bg=PANEL_ALT, color=TEXT, size=14, bold=True,
            wrap=500,
        ).pack(side="right", fill="x", expand=True, padx=(0, 14), pady=12)

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=18)
        # Keep confirmation copy short and on a single line in RTL mode. Tk's
        # wrapping happens after bidi shaping and can scramble long visual-order
        # strings, so translated sentences are deliberately concise.
        self._label(body, message, bg=BG, color=TEXT, size=10,
                    wrap=0 if self.language == "fa" else 550).pack(
            fill="x", anchor=self._content_anchor(), pady=(0, 14)
        )

        if file_count is not None:
            count_row = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            count_row.pack(fill="x", pady=(0, 10))
            self._label(
                count_row, self.t("confirm_move_count"), bg=PANEL, color=MUTED,
                size=9, wrap=420,
            ).pack(side="right", fill="x", expand=True, padx=12, pady=11)
            tk.Label(
                count_row, text=f"{file_count:,}", bg=PANEL_ALT, fg=MINT,
                font=("Segoe UI", 15, "bold"), padx=14, pady=5,
            ).pack(side="left", padx=10, pady=6)

        if selected_folder:
            self._label(
                body, self.t("confirm_move_folder"), bg=BG, color=MUTED,
                size=9, bold=True,
            ).pack(fill="x", anchor=self._content_anchor(), pady=(3, 5))
            path_box = tk.Text(
                body, height=2, wrap="char", bg=PANEL, fg=TEXT,
                insertbackground=TEXT, relief="flat", bd=0,
                font=("Consolas", 9), padx=9, pady=7,
            )
            path_box.pack(fill="x", pady=(0, 10))
            path_box.insert("1.0", selected_folder)
            path_box.configure(state="disabled")

        for line in safety_lines:
            self._label(body, line, bg=BG, color=MUTED, size=9,
                        wrap=0 if self.language == "fa" else 550).pack(
                fill="x", anchor=self._content_anchor(), pady=2
            )

        buttons = tk.Frame(outer, bg=PANEL_ALT)
        buttons.pack(fill="x", side="bottom")

        def finish(confirmed: bool) -> None:
            result["confirmed"] = confirmed
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        no_button = self._button(buttons, self.t("no"), lambda: finish(False), kind="secondary")
        yes_button = self._button(buttons, self.t("yes"), lambda: finish(True), kind="primary")
        yes_button.pack(side="right", padx=(16, 8), pady=12)
        no_button.pack(side="right", padx=(0, 10), pady=12)
        no_button.focus_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        dialog.bind("<Escape>", lambda _event: finish(False))
        dialog.update_idletasks()
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_width()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_height()) // 2)
            dialog.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass
        dialog.grab_set()
        dialog.wait_window()
        return result["confirmed"]

    def apply_organization(self) -> None:
        if self.busy:
            return
        if not self.organize_plan:
            self.make_organize_preview()
            if not self.organize_plan:
                return
        confirmed = self._confirm_dialog(
            self.t("confirm_title"),
            self.t("confirm_moves_intro"),
            file_count=len(self.organize_plan),
            selected_folder=self.selected_root,
            safety_lines=(self.t("confirm_moves_safety_1"), self.t("confirm_moves_safety_2"), self.t("confirm_moves_safety_3")),
        )
        if not confirmed:
            return
        plan = list(self.organize_plan)
        self.busy = True
        self.busy_kind = "organize"
        self.cancel_event = threading.Event()
        self.status_key = "working"
        self._render()

        def worker() -> None:
            try:
                result = apply_organize_plan(plan, progress=lambda *args: self.events.put(("operation_progress", args)), cancel_event=self.cancel_event)
                self.events.put(("organize_done", result))
            except Exception as exc:
                self.events.put(("error", ("organize", str(exc))))
        threading.Thread(target=worker, daemon=True, name="FilePilot-Organize").start()

    def undo_organization(self) -> None:
        if self.busy:
            return
        if not self._confirm_dialog(
            self.t("confirm_title"), self.t("confirm_undo_message"),
            safety_lines=(self.t("confirm_undo_safety"),),
        ):
            return
        self.busy = True
        self.busy_kind = "undo"
        self.status_key = "working"
        self._render()
        def worker() -> None:
            try:
                result = undo_latest_organization()
                self.events.put(("undo_done", result))
            except Exception as exc:
                self.events.put(("error", ("undo", str(exc))))
        threading.Thread(target=worker, daemon=True, name="FilePilot-Undo").start()

    def export_report(self, kind: str) -> None:
        if not self.report:
            messagebox.showinfo(self._display(self.t("app_title")), self._display(self.t("export_before")), parent=self.root)
            return
        ext_map = {"csv": ".csv", "json": ".json", "html": ".html"}
        function_map = {"csv": export_csv, "json": export_json, "html": export_html}
        default_name = f"filepilot-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext_map[kind]}"
        path = filedialog.asksaveasfilename(title=self.t("choose_report_path"), defaultextension=ext_map[kind],
                                            initialfile=default_name,
                                            filetypes=[(kind.upper() + " files", "*" + ext_map[kind]), ("All files", "*.*")],
                                            parent=self.root)
        if not path:
            return
        try:
            saved = function_map[kind](self.report, path)
            messagebox.showinfo(self._display(self.t("export_success")), self._display(f"{self.t('export_success')}:\n{saved}"), parent=self.root)
        except Exception as exc:
            messagebox.showerror(self._display(self.t("export_failed")), self._display(f"{self.t('export_failed')}:\n{exc}"), parent=self.root)

    def _selected_duplicate_path(self) -> str | None:
        tree = self._widget_refs.get("duplicate_tree")
        if not tree:
            return None
        selected = tree.selection()
        if not selected:
            return None
        values = tree.item(selected[0], "values")
        path_index = 0 if self.language == "fa" else 4
        return str(values[path_index]) if len(values) >= 5 else None

    def copy_selected_duplicate_path(self) -> None:
        path = self._selected_duplicate_path()
        if not path:
            messagebox.showinfo(self._display(self.t("app_title")), self._display(self.t("select_row")), parent=self.root)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.status_detail = "Path copied"
        status = self._widget_refs.get("footer_status")
        if status:
            status.configure(text=self._display(self._footer_status_text("status_ready", "Path copied")))

    def open_selected_duplicate_location(self) -> None:
        path = self._selected_duplicate_path()
        if not path:
            messagebox.showinfo(self._display(self.t("app_title")), self._display(self.t("select_row")), parent=self.root)
            return
        directory = str(Path(path).parent)
        try:
            if os.name == "nt":
                os.startfile(directory)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", directory])
            else:
                subprocess.Popen(["xdg-open", directory])
        except Exception as exc:
            messagebox.showerror(self._display(self.t("status_error")), self._display(str(exc)), parent=self.root)

    def _process_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "scan_progress":
                    phase, current, total, note = payload  # type: ignore[misc]
                    self.status_key = "status_hashing" if phase == "hashing" else "status_scanning"
                    self.status_detail = f"{current:,}/{total:,}" if total else note
                    status = self._widget_refs.get("footer_status")
                    if status:
                        status.configure(text=self._display(self._footer_status_text(self.status_key, self.status_detail)))
                    if total and getattr(self, "progress", None):
                        try:
                            self.progress.stop()
                            self.progress.configure(mode="determinate", maximum=max(total, 1), value=current)
                        except tk.TclError:
                            pass
                elif event == "operation_progress":
                    phase, current, total, note = payload  # type: ignore[misc]
                    status = self._widget_refs.get("footer_status")
                    if status:
                        status.configure(text=self._display(self._footer_status_text("working", f"{current:,}/{total:,} · {note}")))
                elif event == "scan_done":
                    self.report = payload  # type: ignore[assignment]
                    self.busy = False
                    self.busy_kind = "idle"
                    self.status_key = "status_done"
                    self.status_detail = f"{self.report.file_count:,} {self.t('files_in_folder')} · {self.report.duration_seconds:.2f}s"
                    self._render()
                elif event == "scan_cancelled":
                    self.busy = False
                    self.busy_kind = "idle"
                    self.status_key = "status_cancelled"
                    self.status_detail = ""
                    self._render()
                elif event == "organize_done":
                    result = payload
                    self.busy = False
                    self.busy_kind = "idle"
                    self.organize_plan = []
                    self.organizer_preview_built = False
                    moved = len(result.moved)  # type: ignore[attr-defined]
                    errors = len(result.errors)  # type: ignore[attr-defined]
                    self.status_key = "status_done"
                    self.status_detail = self.t("move_partial").format(moved=moved, errors=errors) if errors else self.t("move_done").format(count=moved)
                    self._render()
                    messagebox.showinfo(self._display(self.t("status_done")), self._display(self.status_detail), parent=self.root)
                    if moved:
                        self.start_scan(silent=True)
                elif event == "undo_done":
                    result = payload  # type: ignore[assignment]
                    self.busy = False
                    self.busy_kind = "idle"
                    restored = len(result.get("restored", []))  # type: ignore[union-attr]
                    errors = result.get("errors", [])  # type: ignore[union-attr]
                    self.status_key = "status_done"
                    self.status_detail = f"{self.t('undo_done').format(count=restored)} · {len(errors)} warnings" if result.get("journal_id") else self.t("undo_none")  # type: ignore[union-attr]
                    self._render()
                    messagebox.showinfo(self._display(self.t("status_done")), self._display(self.status_detail), parent=self.root)
                    if restored:
                        self.start_scan(silent=True)
                elif event == "error":
                    kind, detail = payload  # type: ignore[misc]
                    self.busy = False
                    self.busy_kind = "idle"
                    self.status_key = "status_error"
                    self.status_detail = ""
                    self._render()
                    messagebox.showerror(self._display(self.t("status_error")), self._display(f"{self.t('scan_error')}\n{detail}"), parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)


def main() -> None:
    root = tk.Tk()
    FilePilotApp(root)
    root.mainloop()
