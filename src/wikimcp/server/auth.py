"""
auth.py — Token-based authentication for wikimcp server mode.

Token format: wikimcp_<username>_<random32hex>
Tokens are stored as SHA-256 hashes in wikimcp.conf — never plaintext.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_token(token: str, config: dict) -> Optional[str]:
    """
    Validate a bearer token against the server config.

    Returns the username if the token is valid, None if invalid.
    Compares the SHA-256 hash of the provided token against the stored
    token_hash for each user in config["users"].
    """
    if not token:
        return None

    token_hash = hash_token(token)
    users = config.get("users", {})

    for username, user_data in users.items():
        stored_hash = user_data.get("token_hash", "")
        if stored_hash and token_hash == stored_hash:
            return username

    return None


def extract_token(request) -> Optional[str]:
    """
    Extract the bearer token from a request.

    Checks (in order):
      1. Authorization: Bearer <token> header
      2. ?token=<token> query parameter

    Works with FastAPI Request objects and generic dict-like objects.
    Returns the token string or None if not found.
    """
    # Try Authorization header first
    # FastAPI Request: request.headers is a Headers mapping
    # Dict-like: request["headers"] or request.get("headers")
    try:
        # FastAPI-style: headers attribute with case-insensitive get
        headers = request.headers
        auth_header = headers.get("authorization") or headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip() or None
    except (AttributeError, TypeError):
        pass

    # Try dict-style headers
    try:
        headers = request.get("headers", {})
        for key, value in (headers.items() if hasattr(headers, "items") else []):
            if key.lower() == "authorization":
                if value.lower().startswith("bearer "):
                    return value[7:].strip() or None
                break
    except (AttributeError, TypeError):
        pass

    # Try query params
    # FastAPI Request: request.query_params is a QueryParams mapping
    try:
        token = request.query_params.get("token")
        if token:
            return token
    except AttributeError:
        pass

    # Dict-style query params
    try:
        params = request.get("query_params", {})
        token = params.get("token") if hasattr(params, "get") else None
        if token:
            return token
    except (AttributeError, TypeError):
        pass

    return None


def update_last_active(
    username: str,
    config: dict,
    config_path: Path,
) -> None:
    """
    Update the user's last_active timestamp in config and persist to disk.

    Modifies config in-place and writes the updated config to config_path.
    """
    config_path = Path(config_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    users = config.setdefault("users", {})
    if username in users:
        users[username]["last_active"] = timestamp

    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
