"""
config.py — Config file management for wikimcp.conf (JSON format).
"""

from __future__ import annotations

import json
from pathlib import Path


def default_config(port: int = 8765, host: str = "0.0.0.0") -> dict:
    """Return a default config dict."""
    return {
        "version": "0.1",
        "port": port,
        "host": host,
        "users": {},
    }


def get_config_path(server_dir: Path) -> Path:
    """Return the path to wikimcp.conf inside server_dir."""
    return Path(server_dir) / "wikimcp.conf"


def load_config(config_path: Path) -> dict:
    """Read and parse wikimcp.conf. Return default config if file doesn't exist."""
    config_path = Path(config_path)
    if not config_path.exists():
        return default_config()
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config_path: Path, config: dict) -> None:
    """Write config to wikimcp.conf with pretty-print JSON."""
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def get_user(config: dict, username: str) -> dict | None:
    """Get a user's config entry, or None if not found."""
    return config.get("users", {}).get(username)
