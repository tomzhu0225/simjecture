"""Safe inline file viewer, diff tracking, and turn baselines for workspace files.

All file reads enforce strict directory containment, reject symlinks at every path
segment, bound inline payloads, and never execute or unsafely render file contents.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import io
import json
import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from ..research_service import put

MAX_INLINE_BYTES = 512 * 1024
MAX_BASELINE_BYTES = 512 * 1024
MAX_DIFF_LINES = 1500
MAX_CSV_ROWS = 200
MAX_CSV_COLS = 50
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})
MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})
TABLE_SUFFIXES = frozenset({".csv", ".tsv"})
LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".lean": "lean",
    ".tex": "latex",
    ".bib": "bibtex",
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
    ".jsonl": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "ini",
    ".ini": "ini",
    ".cfg": "ini",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".f": "fortran",
    ".f90": "fortran",
    ".f95": "fortran",
    ".rs": "rust",
    ".go": "go",
    ".js": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".css": "css",
    ".html": "xml",
    ".htm": "xml",
    ".xml": "xml",
    ".sql": "sql",
    ".par": "ini",
    ".in": "plaintext",
    ".out": "plaintext",
    ".log": "plaintext",
    ".txt": "plaintext",
    ".csv": "plaintext",
    ".tsv": "plaintext",
}

_DIFF_STAT_CACHE: dict[tuple[str, int, int, str], tuple[int, int]] = {}


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return {} if default is None else default


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _is_binary_bytes(sample: bytes) -> bool:
    if not sample:
        return False
    if b"\x00" in sample[:8192]:
        return True
    try:
        sample.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def file_category(suffix: str) -> str:
    low = suffix.lower()
    if low in IMAGE_SUFFIXES:
        return "image"
    if low in MARKDOWN_SUFFIXES:
        return "markdown"
    if low in TABLE_SUFFIXES:
        return "data"
    if low == ".pdf":
        return "pdf"
    if low in LANGUAGE_BY_SUFFIX:
        return "code"
    return "binary"


def file_language(name: str) -> str:
    low = Path(name).suffix.lower()
    if low in LANGUAGE_BY_SUFFIX:
        return LANGUAGE_BY_SUFFIX[low]
    if Path(name).name.lower() in {"makefile", "dockerfile", "cmakelists.txt"}:
        return "makefile"
    return "plaintext"


def resolve_safe_file(root: Path, requested: str) -> tuple[Path, str]:
    """Validate and resolve a relative path strictly inside ``root`` without symlinks."""
    if not isinstance(requested, str) or not requested.strip() or "\x00" in requested:
        raise ValueError("Specify a valid relative file path")
    cleaned = requested.strip().lstrip("./")
    if not cleaned:
        raise ValueError("Specify a valid relative file path")
    relative = Path(cleaned)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("File path must remain inside the workspace directory")
    if any(part.startswith(".") for part in relative.parts):
        raise ValueError("Hidden workspace files cannot be viewed inline")
    resolved_root = root.resolve()
    if root.is_symlink():
        raise ValueError("Workspace root cannot be a symlink")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlinked workspace files cannot be viewed inline")
    resolved = cursor.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("File path escapes the workspace directory")
    if not resolved.is_file():
        raise ValueError("File is missing")
    return resolved, relative.as_posix()


def capture_file_baseline(project_dir: Path, turn_dir: Path) -> dict[str, Any]:
    """Record content hashes and text snapshots of ``files/`` before a turn begins."""
    files_root = project_dir / "files"
    snapshots_root = project_dir / "file_snapshots"
    snapshots_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, Any]] = {}
    if files_root.is_dir() and not files_root.is_symlink():
        resolved_root = files_root.resolve()
        for path in sorted(files_root.rglob("*")):
            if len(manifest) >= 400:
                break
            rel = path.relative_to(files_root)
            if (
                path.is_symlink()
                or any(part.startswith(".") for part in rel.parts)
                or not path.is_file()
            ):
                continue
            try:
                if not path.resolve().is_relative_to(resolved_root):
                    continue
                stat = path.stat()
                digest = _file_sha256(path)
                entry: dict[str, Any] = {
                    "sha256": digest,
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
                if stat.st_size <= MAX_BASELINE_BYTES:
                    raw = path.read_bytes()
                    if not _is_binary_bytes(raw):
                        snap = snapshots_root / digest
                        if not snap.exists():
                            snap.write_bytes(raw)
                        entry["snapshot"] = digest
                manifest[rel.as_posix()] = entry
            except OSError:
                continue
    payload = {"captured_at": time.time(), "files": manifest}
    put(turn_dir / "file_baseline.json", payload)
    return payload


def _latest_baseline(project_dir: Path) -> tuple[dict[str, dict[str, Any]], float]:
    turns_dir = project_dir / "turns"
    if not turns_dir.is_dir():
        return {}, 0.0
    for turn in sorted(turns_dir.iterdir(), reverse=True):
        baseline_file = turn / "file_baseline.json"
        if baseline_file.is_file() and not baseline_file.is_symlink():
            data = _load_json(baseline_file)
            files = data.get("files") if isinstance(data, dict) else None
            if isinstance(files, dict):
                return files, float(data.get("captured_at") or 0.0)
    return {}, 0.0


def _snapshot_text(project_dir: Path, digest: str | None) -> str | None:
    if not digest or len(digest) != 64:
        return None
    snap = project_dir / "file_snapshots" / digest
    if not snap.is_file() or snap.is_symlink():
        return None
    try:
        return snap.read_bytes()[:MAX_INLINE_BYTES].decode("utf-8", errors="replace")
    except OSError:
        return None


def _compute_diff_stats(old_text: str, new_text: str) -> tuple[int, int]:
    added = removed = 0
    diff_iter = difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(), lineterm="", n=0
    )
    for line in diff_iter:
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def _structured_diff(old_text: str, new_text: str, rel_path: str) -> dict[str, Any]:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    rows: list[dict[str, Any]] = []
    added = removed = 0
    old_no = new_no = 0
    truncated = False
    for raw in difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        lineterm="",
        n=3,
    ):
        if raw.startswith(("--- ", "+++ ")):
            continue
        if len(rows) >= MAX_DIFF_LINES:
            truncated = True
            break
        if raw.startswith("@@"):
            parts = raw.split(" ")
            with_old = parts[1].lstrip("-").split(",")[0] if len(parts) > 1 else "1"
            with_new = parts[2].lstrip("+").split(",")[0] if len(parts) > 2 else "1"
            old_no = int(with_old) if with_old.isdigit() else 1
            new_no = int(with_new) if with_new.isdigit() else 1
            rows.append({"type": "hunk", "old_line": None, "new_line": None, "text": raw})
        elif raw.startswith("+"):
            added += 1
            rows.append({"type": "add", "old_line": None, "new_line": new_no, "text": raw[1:]})
            new_no += 1
        elif raw.startswith("-"):
            removed += 1
            rows.append({"type": "del", "old_line": old_no, "new_line": None, "text": raw[1:]})
            old_no += 1
        else:
            rows.append(
                {
                    "type": "ctx",
                    "old_line": old_no,
                    "new_line": new_no,
                    "text": raw[1:] if raw.startswith(" ") else raw,
                }
            )
            old_no += 1
            new_no += 1
    return {
        "has_diff": bool(rows),
        "added_lines": added,
        "removed_lines": removed,
        "truncated": truncated,
        "lines": rows,
    }


def describe_project_files(project_dir: Path, *, limit: int = 200) -> tuple[list[dict], list[dict]]:
    """Return enriched conversation file entries and a newest-first edited-files summary."""
    files_root = project_dir / "files"
    baseline, _ = _latest_baseline(project_dir)
    has_baseline = bool(baseline) or (
        (project_dir / "turns").is_dir()
        and any((t / "file_baseline.json").is_file() for t in (project_dir / "turns").iterdir())
    )
    entries: list[dict[str, Any]] = []
    edited: list[dict[str, Any]] = []
    if not files_root.is_dir() or files_root.is_symlink():
        return entries, edited
    resolved_root = files_root.resolve()
    for path in sorted(files_root.rglob("*")):
        if len(entries) >= limit:
            break
        rel = path.relative_to(files_root)
        if (
            path.is_symlink()
            or any(part.startswith(".") for part in rel.parts)
            or not path.is_file()
        ):
            continue
        try:
            if not path.resolve().is_relative_to(resolved_root):
                continue
            stat = path.stat()
        except OSError:
            continue
        name = rel.as_posix()
        change = "unchanged"
        added_lines = 0
        removed_lines = 0
        if has_baseline:
            base = baseline.get(name)
            if base is None:
                change = "created"
                if stat.st_size <= MAX_INLINE_BYTES:
                    cache_key = (str(path), stat.st_mtime_ns, stat.st_size, "created")
                    cached = _DIFF_STAT_CACHE.get(cache_key)
                    if cached is None:
                        try:
                            raw = path.read_bytes()
                            if not _is_binary_bytes(raw):
                                line_count = len(raw.decode("utf-8", errors="replace").splitlines())
                                cached = (line_count, 0)
                            else:
                                cached = (0, 0)
                        except OSError:
                            cached = (0, 0)
                        if len(_DIFF_STAT_CACHE) > 2048:
                            _DIFF_STAT_CACHE.clear()
                        _DIFF_STAT_CACHE[cache_key] = cached
                    added_lines, removed_lines = cached
            elif (
                stat.st_size != base.get("bytes")
                or stat.st_mtime_ns != base.get("mtime_ns")
            ):
                try:
                    current_sha = _file_sha256(path)
                except OSError:
                    current_sha = base.get("sha256", "")
                if current_sha != base.get("sha256"):
                    change = "modified"
                    if stat.st_size <= MAX_INLINE_BYTES and base.get("snapshot"):
                        cache_key = (str(path), stat.st_mtime_ns, stat.st_size, base["snapshot"])
                        cached = _DIFF_STAT_CACHE.get(cache_key)
                        if cached is None:
                            old_text = _snapshot_text(project_dir, base.get("snapshot"))
                            try:
                                raw = path.read_bytes()
                                if old_text is not None and not _is_binary_bytes(raw):
                                    new_text = raw.decode("utf-8", errors="replace")
                                    cached = _compute_diff_stats(old_text, new_text)
                                else:
                                    cached = (0, 0)
                            except OSError:
                                cached = (0, 0)
                            if len(_DIFF_STAT_CACHE) > 2048:
                                _DIFF_STAT_CACHE.clear()
                            _DIFF_STAT_CACHE[cache_key] = cached
                        added_lines, removed_lines = cached
        record = {
            "name": name,
            "bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "change": change,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "category": file_category(path.suffix),
            "language": file_language(name),
        }
        entries.append(record)
        if change != "unchanged":
            edited.append(record)
    edited.sort(key=lambda item: (item["mtime"], item["name"]), reverse=True)
    return entries, edited


def _parse_table(text_content: str, delimiter: str) -> dict[str, Any]:
    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    headers: list[str] = []
    rows: list[list[str]] = []
    total_rows = 0
    for idx, row in enumerate(reader):
        if idx == 0:
            headers = [cell[:200] for cell in row[:MAX_CSV_COLS]]
            continue
        total_rows += 1
        if len(rows) < MAX_CSV_ROWS:
            rows.append([cell[:200] for cell in row[:MAX_CSV_COLS]])
    return {
        "headers": headers,
        "rows": rows,
        "total_rows": total_rows,
        "truncated_rows": total_rows > len(rows),
    }


def read_file_view(
    project_dir: Path,
    project_id: str,
    rel_path: str,
    *,
    source: str = "files",
    simulation: str | None = None,
    workspace_space: str | None = None,
) -> dict[str, Any]:
    """Return a safe, structured inline view (content, table, image URL, and diff)."""
    if source == "simulation":
        from .jobs import read as read_job
        from .jobs import resolve as resolve_job

        if not simulation:
            raise ValueError("Specify a simulation or worker identifier")
        job_dir = resolve_job(project_dir, simulation)
        job_req = read_job(job_dir / "request.json")
        root = (
            project_dir / "files"
            if job_req.get("kind") == "command"
            else job_dir / "workspace"
        )
        source_label = job_req.get("name") or simulation
    elif source == "files":
        root = project_dir / "files"
        source_label = "Conversation files"
    else:
        raise ValueError("Unsupported file source")

    resolved, clean_path = resolve_safe_file(root, rel_path)
    stat = resolved.stat()
    suffix = resolved.suffix.lower()
    mime = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    query_params: dict[str, str] = {"id": project_id, "path": clean_path}
    if workspace_space and workspace_space != "personal":
        query_params["workspace"] = workspace_space
    if source == "simulation" and simulation:
        query_params["simulation"] = simulation
        download_url = f"/api/workspace/simulation-file?{urlencode(query_params)}"
        preview_url = f"/api/workspace/simulation-file?{urlencode(query_params | {'preview': '1'})}"
    else:
        download_url = f"/api/workspace/file?{urlencode(query_params)}"
        preview_url = f"/api/workspace/preview?{urlencode(query_params)}"

    base_info: dict[str, Any] = {
        "path": clean_path,
        "name": resolved.name,
        "source": source,
        "source_label": source_label,
        "simulation": simulation,
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "mime_type": mime,
        "language": file_language(clean_path),
        "category": file_category(suffix),
        "download_url": download_url,
        "change": "unchanged",
        "diff": {"has_diff": False, "added_lines": 0, "removed_lines": 0, "lines": []},
    }
    if suffix in IMAGE_SUFFIXES:
        return base_info | {
            "kind": "image",
            "preview_url": preview_url,
            "truncated": False,
        }

    with resolved.open("rb") as stream:
        raw = stream.read(MAX_INLINE_BYTES + 1)
    truncated = len(raw) > MAX_INLINE_BYTES
    payload_bytes = raw[:MAX_INLINE_BYTES]
    if _is_binary_bytes(payload_bytes):
        return base_info | {
            "kind": "binary",
            "sha256": _file_sha256(resolved) if stat.st_size <= 32 * 1024 * 1024 else None,
            "truncated": truncated,
        }

    text_content = payload_bytes.decode("utf-8", errors="replace")
    diff_info = {"has_diff": False, "added_lines": 0, "removed_lines": 0, "lines": []}
    change = "unchanged"
    if source == "files":
        baseline, _ = _latest_baseline(project_dir)
        has_baseline = bool(baseline) or (
            (project_dir / "turns").is_dir()
            and any((t / "file_baseline.json").is_file() for t in (project_dir / "turns").iterdir())
        )
        if has_baseline:
            base_entry = baseline.get(clean_path)
            if base_entry is None:
                change = "created"
                diff_info = _structured_diff("", text_content, clean_path)
            else:
                old_text = _snapshot_text(project_dir, base_entry.get("snapshot"))
                if old_text is not None and old_text != text_content:
                    change = "modified"
                    diff_info = _structured_diff(old_text, text_content, clean_path)

    kind = (
        "markdown"
        if suffix in MARKDOWN_SUFFIXES
        else "table"
        if suffix in TABLE_SUFFIXES
        else "text"
    )
    result = base_info | {
        "kind": kind,
        "content": text_content,
        "line_count": len(text_content.splitlines()),
        "truncated": truncated,
        "change": change,
        "diff": diff_info,
    }
    if kind == "table":
        result["table"] = _parse_table(text_content, "\t" if suffix == ".tsv" else ",")
    return result
