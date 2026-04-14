"""
manager.py — User lifecycle management for wikimcp.

Handles creating, removing, listing users and managing their git remotes.
Token format:   wikimcp_<username>_<32 hex chars>
Token storage:  SHA-256 hash stored as `token_hash` in wikimcp.conf
"""

from __future__ import annotations

import hashlib
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from wikimcp.wiki.git_layer import (
    add_remote as git_add_remote,
    init_repo,
    list_remotes as git_list_remotes,
    push_auto_remotes,
    push_remote as git_push_remote,
    remove_remote as git_remove_remote,
)
from wikimcp.wiki.schema import scaffold_wiki

from .config import (
    get_config_path,
    get_user,
    load_config,
    save_config,
    default_config,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of *token*."""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token(username: str) -> str:
    """Generate a new bearer token for *username*."""
    return f"wikimcp_{username}_{secrets.token_hex(16)}"


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _users_dir(server_dir: Path) -> Path:
    return Path(server_dir) / "users"


def _user_wiki_dir(server_dir: Path, username: str) -> Path:
    return _users_dir(server_dir) / username


def _require_user(config: dict, username: str) -> dict:
    """Return the user's config entry, raising KeyError if not found."""
    user = get_user(config, username)
    if user is None:
        raise KeyError(f"User '{username}' does not exist.")
    return user


def _count_pages(wiki_dir: Path) -> int:
    """Count .md files under <wiki_dir>/wiki/ (excluding .gitkeep)."""
    wiki_subdir = Path(wiki_dir) / "wiki"
    if not wiki_subdir.exists():
        return 0
    return sum(1 for p in wiki_subdir.rglob("*.md"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_server(server_dir: Path, port: int = 8765) -> None:
    """
    Initialise the server data directory.

    Creates:
      <server_dir>/
        users/
        wikimcp.conf   (written only if it does not already exist)
    """
    server_dir = Path(server_dir)
    server_dir.mkdir(parents=True, exist_ok=True)
    _users_dir(server_dir).mkdir(exist_ok=True)

    config_path = get_config_path(server_dir)
    if not config_path.exists():
        save_config(config_path, default_config(port=port))


def add_user(server_dir: Path, username: str) -> dict:
    """
    Create a new user.

    Steps:
      1. Validate username not already taken.
      2. Create directory at users/<username>.
      3. Scaffold wiki structure (CLAUDE.md, wiki/, raw/).
      4. Initialise git repo.
      5. Generate bearer token and store SHA-256 hash in config.

    Returns a dict with keys:
      token, username, wiki_dir, mcp_url, wiki_url
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    if get_user(config, username) is not None:
        raise ValueError(f"User '{username}' already exists.")

    wiki_dir = _user_wiki_dir(server_dir, username)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    scaffold_wiki(wiki_dir)
    init_repo(wiki_dir)

    token = _generate_token(username)
    token_hash = _hash_token(token)

    host = config.get("host", "0.0.0.0")
    port = config.get("port", 8765)

    config["users"][username] = {
        "token_hash": token_hash,
        "wiki_dir": str(wiki_dir),
        "created_at": _now_iso(),
        "last_active": None,
        "remotes": {},
        "auto_push_remotes": [],
    }
    save_config(config_path, config)

    return {
        "token": token,
        "username": username,
        "wiki_dir": str(wiki_dir),
        "mcp_url": f"http://{host}:{port}/mcp",
        "wiki_url": f"http://{host}:{port}/wiki/{username}",
    }


def remove_user(server_dir: Path, username: str) -> None:
    """
    Remove a user's directory and config entry.

    Raises KeyError if the user does not exist.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    _require_user(config, username)

    wiki_dir = _user_wiki_dir(server_dir, username)
    if wiki_dir.exists():
        shutil.rmtree(wiki_dir)

    del config["users"][username]
    save_config(config_path, config)


def list_users(server_dir: Path) -> List[dict]:
    """
    Return a list of user info dicts.

    Each dict contains:
      username, wiki_dir, page_count, last_active, masked_token
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    result = []
    for username, user_data in config.get("users", {}).items():
        wiki_dir = Path(user_data.get("wiki_dir", _user_wiki_dir(server_dir, username)))
        page_count = _count_pages(wiki_dir)

        # Mask the stored hash to produce a safe display string
        token_hash = user_data.get("token_hash", "")
        masked = f"wikimcp_{username}_{'*' * 24}{token_hash[-8:]}" if token_hash else "N/A"

        result.append({
            "username": username,
            "wiki_dir": str(wiki_dir),
            "page_count": page_count,
            "last_active": user_data.get("last_active"),
            "masked_token": masked,
        })
    return result


def rotate_token(server_dir: Path, username: str) -> str:
    """
    Generate a new bearer token for *username*, replacing the old hash.

    Returns the new plaintext token.
    Raises KeyError if the user does not exist.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    _require_user(config, username)

    token = _generate_token(username)
    config["users"][username]["token_hash"] = _hash_token(token)
    save_config(config_path, config)
    return token


def add_remote(
    server_dir: Path,
    username: str,
    remote_name: str,
    git_url: str,
) -> None:
    """
    Add a git remote to a user's wiki repo and persist the URL in config.

    Raises KeyError if the user does not exist.
    Raises ValueError (from git_layer) if the remote name already exists.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    user = _require_user(config, username)
    wiki_dir = Path(user["wiki_dir"])

    git_add_remote(wiki_dir, remote_name, git_url)

    config["users"][username].setdefault("remotes", {})[remote_name] = git_url
    save_config(config_path, config)


def remove_remote(
    server_dir: Path,
    username: str,
    remote_name: str,
) -> None:
    """
    Remove a named git remote from a user's wiki repo and config.

    Raises KeyError if the user does not exist.
    Raises ValueError (from git_layer) if the remote does not exist.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    user = _require_user(config, username)
    wiki_dir = Path(user["wiki_dir"])

    git_remove_remote(wiki_dir, remote_name)

    remotes = config["users"][username].get("remotes", {})
    remotes.pop(remote_name, None)

    # Also remove from auto_push_remotes if present
    auto = config["users"][username].get("auto_push_remotes", [])
    config["users"][username]["auto_push_remotes"] = [r for r in auto if r != remote_name]

    save_config(config_path, config)


def list_remotes(server_dir: Path, username: str) -> List[dict]:
    """
    Return a list of dicts with keys 'name' and 'url' for every configured remote.

    Raises KeyError if the user does not exist.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    user = _require_user(config, username)
    wiki_dir = Path(user["wiki_dir"])

    return git_list_remotes(wiki_dir)


def push_remote(
    server_dir: Path,
    username: str,
    remote_name: str | None = None,
) -> List[str]:
    """
    Push to a named remote, or to all remotes if *remote_name* is None.

    Returns a list of warning strings (empty list means all pushes succeeded).
    Raises KeyError if the user does not exist.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    user = _require_user(config, username)
    wiki_dir = Path(user["wiki_dir"])

    if remote_name is not None:
        warning = git_push_remote(wiki_dir, remote_name)
        return [warning] if warning else []
    else:
        # Push to every configured remote
        all_remotes = list(user.get("remotes", {}).keys())
        return push_auto_remotes(wiki_dir, all_remotes)


def export_wiki(
    server_dir: Path,
    username: str,
    format: str = "zip",
    out_dir: str = "./",
) -> Path:
    """
    Export a user's wiki as a zip or tar.gz archive.

    The archive is written to *out_dir* and named
    ``<username>_wiki.<ext>``.

    Returns the Path to the created archive.
    Raises KeyError if the user does not exist.
    Raises ValueError for unsupported format strings.
    """
    server_dir = Path(server_dir)
    config_path = get_config_path(server_dir)
    config = load_config(config_path)

    user = _require_user(config, username)
    wiki_dir = Path(user["wiki_dir"])

    out_path = Path(out_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    if format == "zip":
        archive_name = out_path / f"{username}_wiki"
        result = shutil.make_archive(str(archive_name), "zip", str(wiki_dir))
    elif format in ("tar", "tar.gz", "tgz"):
        archive_name = out_path / f"{username}_wiki"
        result = shutil.make_archive(str(archive_name), "gztar", str(wiki_dir))
    else:
        raise ValueError(f"Unsupported export format: '{format}'. Use 'zip' or 'tar'.")

    return Path(result)
