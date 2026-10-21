from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import shutil
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

APP_DIR_NAME = "FilePilot"
JOURNAL_DIR_NAME = "journals"
APP_VERSION = "1.0.6"

CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".svg", ".heic", ".ico"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v", ".mpeg", ".mpg"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus"},
    "Documents": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex", ".pages"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods", ".tsv"},
    "Presentations": {".ppt", ".pptx", ".odp", ".key"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".java", ".c", ".h", ".cpp", ".cs", ".go", ".rs", ".php", ".rb", ".json", ".xml", ".yaml", ".yml", ".toml", ".sql", ".sh", ".bat", ".ps1"},
    "Installers": {".exe", ".msi", ".msix", ".apk", ".dmg", ".pkg", ".deb", ".rpm"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2"},
}

ProgressCallback = Callable[[str, int, int, str], None]


@dataclass(slots=True)
class FileRecord:
    path: str
    name: str
    extension: str
    size: int
    modified: float
    category: str
    sha256: str = ""


@dataclass(slots=True)
class DuplicateGroup:
    sha256: str
    size: int
    paths: list[str]

    @property
    def copies(self) -> int:
        return len(self.paths)

    @property
    def reclaimable_bytes(self) -> int:
        return max(0, self.copies - 1) * self.size


@dataclass(slots=True)
class ScanReport:
    root: str
    started_at: str
    finished_at: str
    duration_seconds: float
    files: list[FileRecord] = field(default_factory=list)
    total_bytes: int = 0
    category_counts: dict[str, int] = field(default_factory=dict)
    category_bytes: dict[str, int] = field(default_factory=dict)
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def duplicate_file_count(self) -> int:
        return sum(group.copies for group in self.duplicate_groups)

    @property
    def duplicate_group_count(self) -> int:
        return len(self.duplicate_groups)

    @property
    def reclaimable_bytes(self) -> int:
        return sum(group.reclaimable_bytes for group in self.duplicate_groups)


@dataclass(slots=True)
class OrganizeItem:
    source: str
    destination: str
    category: str
    size: int


@dataclass(slots=True)
class OperationResult:
    journal_id: str
    moved: list[dict[str, str]]
    errors: list[dict[str, str]]
    journal_path: str


def app_data_dir() -> Path:
    """Return per-user app data directory, creating it when needed."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / APP_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def journal_dir() -> Path:
    target = app_data_dir() / JOURNAL_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def format_bytes(value: int) -> str:
    if value < 0:
        value = 0
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:,.1f} {unit}" if unit != "B" else f"{int(number):,} B"
        number /= 1024
    return f"{number:,.1f} PB"


def category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, suffixes in CATEGORY_EXTENSIONS.items():
        if suffix in suffixes:
            return category
    return "Other"


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def scan_directory(
    root: str | os.PathLike[str],
    progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> ScanReport:
    """Recursively inspect regular files and hash same-size candidates.

    Symlinks are not followed. The scan is read-only: it never modifies or removes
    user files. Files under .filepilot are excluded from future scans.
    """
    root_path = Path(root).expanduser().resolve(strict=True)
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")
    cancel_event = cancel_event or threading.Event()
    t0 = time.perf_counter()
    started_iso = datetime.now().astimezone().isoformat(timespec="seconds")
    files: list[FileRecord] = []
    errors: list[str] = []
    size_candidates: dict[int, list[int]] = defaultdict(list)

    def emit(phase: str, current: int, total: int, note: str = "") -> None:
        if progress:
            progress(phase, current, total, note)

    emit("walking", 0, 0, str(root_path))
    for current_dir, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
        if cancel_event.is_set():
            break
        current_path = Path(current_dir)
        filtered_dirs: list[str] = []
        for dirname in dirnames:
            child = current_path / dirname
            if dirname.lower() == ".filepilot" or child.is_symlink():
                continue
            filtered_dirs.append(dirname)
        dirnames[:] = filtered_dirs

        for filename in filenames:
            if cancel_event.is_set():
                break
            path = current_path / filename
            try:
                if path.is_symlink() or not path.is_file():
                    continue
                stat = path.stat()
                if stat.st_size < 0:
                    continue
                category = category_for(path)
                record = FileRecord(
                    path=str(path),
                    name=path.name,
                    extension=path.suffix.lower() or "[no extension]",
                    size=stat.st_size,
                    modified=stat.st_mtime,
                    category=category,
                )
                size_candidates[record.size].append(len(files))
                files.append(record)
            except (OSError, PermissionError) as exc:
                errors.append(f"{path}: {exc}")

    if cancel_event.is_set():
        raise InterruptedError("Scan cancelled by user")

    candidates = [index for indices in size_candidates.values() if len(indices) > 1 for index in indices]
    emit("hashing", 0, len(candidates), f"{len(candidates)} candidate files")
    digest_groups: dict[tuple[int, str], list[str]] = defaultdict(list)
    for position, index in enumerate(candidates, start=1):
        if cancel_event.is_set():
            raise InterruptedError("Scan cancelled by user")
        record = files[index]
        try:
            digest = _sha256(Path(record.path))
            record.sha256 = digest
            digest_groups[(record.size, digest)].append(record.path)
        except (OSError, PermissionError) as exc:
            errors.append(f"{record.path}: could not hash file: {exc}")
        emit("hashing", position, len(candidates), record.name)

    duplicate_groups = [
        DuplicateGroup(sha256=digest, size=size, paths=sorted(paths, key=str.casefold))
        for (size, digest), paths in digest_groups.items()
        if len(paths) > 1
    ]
    duplicate_groups.sort(key=lambda group: (-group.reclaimable_bytes, group.sha256))
    category_counts = Counter(record.category for record in files)
    category_bytes: dict[str, int] = defaultdict(int)
    total_bytes = 0
    for record in files:
        total_bytes += record.size
        category_bytes[record.category] += record.size

    finished_iso = datetime.now().astimezone().isoformat(timespec="seconds")
    report = ScanReport(
        root=str(root_path),
        started_at=started_iso,
        finished_at=finished_iso,
        duration_seconds=round(time.perf_counter() - t0, 3),
        files=files,
        total_bytes=total_bytes,
        category_counts=dict(category_counts),
        category_bytes=dict(category_bytes),
        duplicate_groups=duplicate_groups,
        errors=errors,
    )
    emit("complete", len(files), len(files), "done")
    return report


def build_organize_plan(root: str | os.PathLike[str]) -> list[OrganizeItem]:
    """Plan moving only regular files directly inside the selected root.

    The plan does not move files recursively and excludes directories; this avoids
    surprising recursive moves and never deletes any data.
    """
    root_path = Path(root).expanduser().resolve(strict=True)
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")
    plan: list[OrganizeItem] = []
    ignored_dirs = {".filepilot"}
    for child in root_path.iterdir():
        try:
            if child.name.lower() in ignored_dirs or child.is_dir() or child.is_symlink() or not child.is_file():
                continue
            category = category_for(child)
            destination = root_path / category / child.name
            plan.append(OrganizeItem(str(child), str(destination), category, child.stat().st_size))
        except OSError:
            continue
    plan.sort(key=lambda item: (item.category.casefold(), Path(item.source).name.casefold()))
    return plan


def _unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination
    stem, suffix = destination.stem, destination.suffix
    parent = destination.parent
    for number in range(1, 100_000):
        candidate = parent / f"{stem} ({number}){suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not create a unique destination for {destination}")


def apply_organize_plan(
    plan: Iterable[OrganizeItem],
    progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> OperationResult:
    """Apply approved moves and persist a journal for a later undo operation."""
    cancel_event = cancel_event or threading.Event()
    plan_list = list(plan)
    journal_id = f"organize-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    moved: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for index, item in enumerate(plan_list, start=1):
        if cancel_event.is_set():
            break
        source = Path(item.source)
        original_destination = Path(item.destination)
        try:
            if not source.exists() or source.is_symlink() or not source.is_file():
                raise FileNotFoundError("Source file is missing or is not a regular file")
            original_destination.parent.mkdir(parents=True, exist_ok=True)
            destination = _unique_destination(original_destination)
            shutil.move(str(source), str(destination))
            moved.append({"source": str(source), "destination": str(destination)})
        except (OSError, shutil.Error) as exc:
            errors.append({"source": str(source), "error": str(exc)})
        if progress:
            progress("moving", index, len(plan_list), source.name)

    journal = {
        "schema_version": 1,
        "journal_id": journal_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operation": "organize_move",
        "moved": moved,
        "errors": errors,
        "undone": False,
    }
    path = journal_dir() / f"{journal_id}.json"
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return OperationResult(journal_id=journal_id, moved=moved, errors=errors, journal_path=str(path))


def undo_latest_organization() -> dict[str, object]:
    """Undo the newest non-undone organization journal without overwriting files."""
    journals = sorted(journal_dir().glob("organize-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for journal_path in journals:
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if journal.get("undone") or journal.get("operation") != "organize_move":
            continue
        restored: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        for item in reversed(journal.get("moved", [])):
            source = Path(item["source"])
            destination = Path(item["destination"])
            try:
                if not destination.exists() or not destination.is_file():
                    errors.append({"destination": str(destination), "error": "Moved file no longer exists"})
                    continue
                if source.exists():
                    errors.append({"destination": str(destination), "error": "Original path already exists; not overwritten"})
                    continue
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
                restored.append({"source": str(destination), "destination": str(source)})
            except (OSError, shutil.Error) as exc:
                errors.append({"destination": str(destination), "error": str(exc)})
        journal["undone"] = True
        journal["undone_at"] = datetime.now(timezone.utc).isoformat()
        journal["undo_restored"] = restored
        journal["undo_errors"] = errors
        journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"journal_id": journal.get("journal_id", journal_path.stem), "restored": restored, "errors": errors}
    return {"journal_id": "", "restored": [], "errors": [], "message": "No organization operation is available to undo."}


def _csv_safe(value: object) -> str | int | float:
    """Neutralize spreadsheet formula prefixes in untrusted text fields."""
    if not isinstance(value, str):
        return value
    stripped = value.lstrip(" \t\r\n")
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_csv(report: ScanReport, destination: str | os.PathLike[str]) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "extension", "size_bytes", "modified_local", "category", "sha256", "path"])
        writer.writeheader()
        for record in report.files:
            writer.writerow({
                "name": _csv_safe(record.name),
                "extension": _csv_safe(record.extension),
                "size_bytes": record.size,
                "modified_local": datetime.fromtimestamp(record.modified).astimezone().isoformat(timespec="seconds"),
                "category": _csv_safe(record.category),
                "sha256": record.sha256,
                "path": _csv_safe(record.path),
            })
    return path


def export_json(report: ScanReport, destination: str | os.PathLike[str]) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "app": "FilePilot",
        "version": APP_VERSION,
        "root": report.root,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "duration_seconds": report.duration_seconds,
        "summary": {
            "file_count": report.file_count,
            "total_bytes": report.total_bytes,
            "duplicate_groups": report.duplicate_group_count,
            "duplicate_files": report.duplicate_file_count,
            "reclaimable_bytes": report.reclaimable_bytes,
            "scan_errors": len(report.errors),
        },
        "category_counts": report.category_counts,
        "category_bytes": report.category_bytes,
        "duplicates": [asdict(group) for group in report.duplicate_groups],
        "files": [asdict(record) for record in report.files],
        "errors": report.errors,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_html(report: ScanReport, destination: str | os.PathLike[str]) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in report.files:
        rows.append(
            "<tr>"
            f"<td>{html.escape(record.name)}</td>"
            f"<td>{html.escape(record.extension)}</td>"
            f"<td>{html.escape(format_bytes(record.size))}</td>"
            f"<td>{html.escape(record.category)}</td>"
            f"<td><code>{html.escape(record.sha256[:16])}</code></td>"
            f"<td>{html.escape(record.path)}</td>"
            "</tr>"
        )
    dup_html = []
    for group in report.duplicate_groups:
        paths = "<br>".join(html.escape(path) for path in group.paths)
        dup_html.append(
            f"<tr><td>{len(group.paths)}</td><td>{html.escape(format_bytes(group.size))}</td>"
            f"<td>{html.escape(format_bytes(group.reclaimable_bytes))}</td><td>{paths}</td></tr>"
        )
    created_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FilePilot Scan Report</title><style>
:root{{--bg:#0b1020;--panel:#121a2e;--line:#263653;--text:#edf4ff;--muted:#9aabc8;--mint:#2ee6c4;--blue:#7d9cff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 Segoe UI,Arial,sans-serif}}
header{{padding:32px clamp(18px,4vw,56px);background:linear-gradient(125deg,#111b32,#092d3c);border-bottom:1px solid var(--line)}}
header h1{{margin:0;font-size:30px}}header p{{color:var(--muted);margin:8px 0 0}}main{{padding:24px clamp(18px,4vw,56px);max-width:1600px;margin:auto}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}}.card,section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}}
.card span{{display:block;color:var(--muted);font-size:13px}}.card strong{{display:block;color:var(--mint);font-size:25px;margin-top:8px;overflow-wrap:anywhere}}
section{{margin-top:20px;overflow:hidden}}h2{{margin-top:0}}.muted{{color:var(--muted)}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;min-width:700px}}th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--mint);font-size:13px;background:#17233b}}td{{overflow-wrap:anywhere}}code{{color:#9fdcff}}footer{{padding:18px clamp(18px,4vw,56px);color:var(--muted);border-top:1px solid var(--line)}}
</style></head><body><header><h1>FilePilot · Scan Report</h1><p>Read-only file inventory and duplicate analysis</p></header><main>
<div class="metrics"><div class="card"><span>Scanned files</span><strong>{report.file_count:,}</strong></div><div class="card"><span>Total size</span><strong>{html.escape(format_bytes(report.total_bytes))}</strong></div><div class="card"><span>Duplicate groups</span><strong>{report.duplicate_group_count:,}</strong></div><div class="card"><span>Potentially reclaimable</span><strong>{html.escape(format_bytes(report.reclaimable_bytes))}</strong></div><div class="card"><span>Scan duration</span><strong>{report.duration_seconds:.2f}s</strong></div></div>
<section><h2>Scan details</h2><p><b>Root:</b> {html.escape(report.root)}</p><p><b>Started:</b> {html.escape(report.started_at)}<br><b>Finished:</b> {html.escape(report.finished_at)}<br><b>Report generated:</b> {html.escape(created_at)}</p></section>
<section><h2>Category summary</h2><div class="table-wrap"><table><thead><tr><th>Category</th><th>Files</th><th>Total size</th></tr></thead><tbody>{''.join(f'<tr><td>{html.escape(cat)}</td><td>{count:,}</td><td>{html.escape(format_bytes(report.category_bytes.get(cat, 0)))}</td></tr>' for cat, count in sorted(report.category_counts.items()))}</tbody></table></div></section>
<section><h2>Duplicate groups</h2><div class="table-wrap"><table><thead><tr><th>Copies</th><th>One file size</th><th>Potentially reclaimable</th><th>Paths</th></tr></thead><tbody>{''.join(dup_html) or '<tr><td colspan="4">No duplicate groups found.</td></tr>'}</tbody></table></div><p class="muted">This report does not delete files. Duplicate matches are based on SHA-256 content hashes.</p></section>
<section><h2>File inventory</h2><div class="table-wrap"><table><thead><tr><th>Name</th><th>Extension</th><th>Size</th><th>Category</th><th>SHA-256 prefix</th><th>Path</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Scan warnings</h2><ul>{''.join(f'<li>{html.escape(error)}</li>' for error in report.errors) or '<li>No scan warnings were recorded.</li>'}</ul></section>
</main><footer>Generated by FilePilot {APP_VERSION}. Diagnostic report only; no files were removed.</footer></body></html>"""
    path.write_text(content, encoding="utf-8")
    return path
