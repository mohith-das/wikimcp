"""
router.py — Routes MCP tool calls to the correct user's wiki.

Bridges authentication (who is calling) with wiki operations (what to do and where).
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def resolve_wiki_dir(username: str, config: dict) -> Path:
    """
    Look up and return the wiki_dir Path for the given user.

    Raises KeyError if the user is not found in config.
    Raises ValueError if the user has no wiki_dir configured.
    """
    users = config.get("users", {})
    if username not in users:
        raise KeyError(f"User '{username}' not found in config.")

    wiki_dir = users[username].get("wiki_dir")
    if not wiki_dir:
        raise ValueError(f"User '{username}' has no wiki_dir configured.")

    return Path(wiki_dir)


def get_auto_push_remotes(username: str, config: dict) -> List[str]:
    """
    Return the list of auto-push remote names for the given user.

    Returns an empty list if the user has no auto_push_remotes configured
    or if the user is not found in config.
    """
    users = config.get("users", {})
    user_data = users.get(username, {})
    return list(user_data.get("auto_push_remotes", []))
