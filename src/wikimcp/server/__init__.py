"""
wikimcp.server — MCP server module.

Exports the factory functions and auth/router utilities for the server.
"""

from .mcp_server import create_local_server, create_server_mode
from .auth import hash_token, validate_token, extract_token, update_last_active
from .router import resolve_wiki_dir, get_auto_push_remotes

__all__ = [
    # Server factories
    "create_local_server",
    "create_server_mode",
    # Auth utilities
    "hash_token",
    "validate_token",
    "extract_token",
    "update_last_active",
    # Router utilities
    "resolve_wiki_dir",
    "get_auto_push_remotes",
]
