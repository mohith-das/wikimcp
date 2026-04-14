"""
operations.py — Core wiki operations.

All functions are synchronous and stateless: they take wiki_dir (Path) as their
first argument and operate on the filesystem directly, then delegate git work to
git_layer.auto_commit().

Path conventions:
  - wiki_dir          : root of the user's wiki (contains CLAUDE.md, wiki/, raw/, .git/)
  - wiki_dir / "wiki" : the wiki/ subdirectory — all user pages live here
  - path arguments    : relative paths inside wiki/ (e.g. "topics/python.md")
                        Never absolute, never containing ".."
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .git_layer import auto_commit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wiki_subdir(wiki_dir: Path) -> Path:
    """Return the wiki/ subdirectory path."""
    return Path(wiki_dir) / "wiki"


def _validate_path(path: str) -> None:
    """
    Raise ValueError if 'path' is dangerous (absolute or contains ..).

    Accepts POSIX-style relative paths like 'topics/python.md'.
    """
    if not path:
        raise ValueError("Page path must not be empty.")
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Page path must be relative, got: {path!r}")
    # Resolve against a dummy root and check nothing escapes
    for part in p.parts:
        if part == "..":
            raise ValueError(
                f"Page path must not contain '..', got: {path!r}"
            )


def _resolve_page(wiki_dir: Path, path: str) -> Path:
    """
    Return the absolute filesystem path for a page relative to wiki/.

    Validates the path first.
    """
    _validate_path(path)
    return _wiki_subdir(wiki_dir) / path


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

def wiki_info(wiki_dir: Path) -> Dict[str, Any]:
    """
    Return summary information about the wiki.

    Returns a dict with:
      page_count  : int — number of .md files under wiki/ (excluding log.md)
      log_entries : int — number of log entries in wiki/log.md
      wiki_root   : str — absolute path to wiki_dir
    """
    wiki_dir = Path(wiki_dir)
    wiki_sub = _wiki_subdir(wiki_dir)

    # Count .md pages (exclude log.md from the page count so it doesn't inflate it)
    page_count = 0
    if wiki_sub.exists():
        for p in wiki_sub.rglob("*.md"):
            if p.name != "log.md":
                page_count += 1

    # Count log entries — each entry starts with a "## " heading
    log_entries = 0
    log_path = wiki_sub / "log.md"
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
        log_entries = len(re.findall(r"^## ", text, re.MULTILINE))

    return {
        "page_count": page_count,
        "log_entries": log_entries,
        "wiki_root": str(wiki_dir.resolve()),
    }


def read_index(wiki_dir: Path) -> str:
    """
    Return the string content of wiki/index.md.

    Raises FileNotFoundError if the file does not exist.
    """
    wiki_dir = Path(wiki_dir)
    index_path = _wiki_subdir(wiki_dir) / "index.md"
    if not index_path.exists():
        raise FileNotFoundError(
            f"wiki/index.md not found at {index_path}. "
            "Run scaffold_wiki() first."
        )
    return index_path.read_text(encoding="utf-8")


def update_index(wiki_dir: Path, content: str) -> None:
    """
    Overwrite wiki/index.md with content and auto-commit.

    Creates the file (and parent directories) if it does not exist.
    """
    wiki_dir = Path(wiki_dir)
    index_path = _wiki_subdir(wiki_dir) / "index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(content, encoding="utf-8")
    auto_commit(wiki_dir, "wiki: update_index wiki/index.md")


def write_page(wiki_dir: Path, path: str, content: str) -> None:
    """
    Create or overwrite a page at wiki/<path> and auto-commit.

    path must be a relative path (e.g. "topics/python.md").
    Parent directories are created automatically.
    Raises ValueError for invalid paths.
    """
    wiki_dir = Path(wiki_dir)
    page_path = _resolve_page(wiki_dir, path)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(content, encoding="utf-8")
    auto_commit(wiki_dir, f"wiki: write_page wiki/{path}")


def read_page(wiki_dir: Path, path: str) -> str:
    """
    Return the string content of wiki/<path>.

    Raises ValueError for invalid paths.
    Raises FileNotFoundError if the page does not exist.
    """
    wiki_dir = Path(wiki_dir)
    page_path = _resolve_page(wiki_dir, path)
    if not page_path.exists():
        raise FileNotFoundError(f"Page not found: wiki/{path}")
    return page_path.read_text(encoding="utf-8")


def list_pages(
    wiki_dir: Path,
    subdirectory: Optional[str] = None,
) -> List[str]:
    """
    Return a sorted list of page paths relative to wiki/.

    If subdirectory is given (e.g. "topics"), only pages inside that
    subdirectory are returned.

    Hidden files (starting with '.') and non-.md files are excluded.
    """
    wiki_dir = Path(wiki_dir)
    wiki_sub = _wiki_subdir(wiki_dir)

    if subdirectory is not None:
        _validate_path(subdirectory)
        search_root = wiki_sub / subdirectory
    else:
        search_root = wiki_sub

    if not search_root.exists():
        return []

    pages = []
    for p in search_root.rglob("*.md"):
        if not any(part.startswith(".") for part in p.parts):
            rel = p.relative_to(wiki_sub)
            pages.append(str(rel))

    return sorted(pages)


def search_wiki(
    wiki_dir: Path,
    query: str,
    case_sensitive: bool = False,
) -> List[Dict[str, Any]]:
    """
    Full-text search across all .md pages under wiki/.

    Returns a list of dicts, one per matching page:
      {
        "path": "topics/python.md",          # relative to wiki/
        "matches": [
          {"line": "...", "line_number": 12},
          ...
        ]
      }

    Pages with no matching lines are omitted from the result.
    """
    wiki_dir = Path(wiki_dir)
    wiki_sub = _wiki_subdir(wiki_dir)

    if not wiki_sub.exists():
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(re.escape(query), flags)
    except re.error as exc:
        raise ValueError(f"Invalid search query: {exc}") from exc

    results = []
    for page_path in sorted(wiki_sub.rglob("*.md")):
        if any(part.startswith(".") for part in page_path.parts):
            continue
        try:
            text = page_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        matches = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                matches.append({"line": line, "line_number": line_number})

        if matches:
            rel_path = str(page_path.relative_to(wiki_sub))
            results.append({"path": rel_path, "matches": matches})

    return results


def append_log(
    wiki_dir: Path,
    entry: str,
    operation: Optional[str] = None,
) -> None:
    """
    Append a timestamped entry to wiki/log.md and auto-commit.

    Each entry is formatted as a level-2 heading with the UTC timestamp, an
    optional operation label, and the entry text:

        ## 2026-04-14T10:30:00Z [chat]

        Entry text here.

    Creates wiki/log.md if it does not exist.
    """
    wiki_dir = Path(wiki_dir)
    log_path = _wiki_subdir(wiki_dir) / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not log_path.exists():
        log_path.write_text("# Activity Log\n\n", encoding="utf-8")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    heading = f"## {timestamp}"
    if operation:
        heading += f" [{operation}]"

    block = f"\n{heading}\n\n{entry.strip()}\n"

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(block)

    op_label = operation or "log"
    auto_commit(wiki_dir, f"wiki: append_log {op_label} {timestamp}")


def delete_page(wiki_dir: Path, path: str) -> None:
    """
    Delete wiki/<path> and auto-commit.

    Raises ValueError for invalid paths.
    Raises FileNotFoundError if the page does not exist.
    Raises PermissionError if you attempt to delete index.md or log.md.
    """
    wiki_dir = Path(wiki_dir)
    _validate_path(path)

    # Guard the critical files
    if path in ("index.md", "log.md"):
        raise PermissionError(f"'{path}' is a protected file and cannot be deleted.")

    page_path = _resolve_page(wiki_dir, path)
    if not page_path.exists():
        raise FileNotFoundError(f"Page not found: wiki/{path}")

    page_path.unlink()

    # Remove any now-empty parent directories (but never remove wiki/ itself)
    wiki_sub = _wiki_subdir(wiki_dir)
    parent = page_path.parent
    while parent != wiki_sub and parent.exists():
        try:
            parent.rmdir()  # only removes if empty
            parent = parent.parent
        except OSError:
            break  # not empty — stop

    auto_commit(wiki_dir, f"wiki: delete_page wiki/{path}")
