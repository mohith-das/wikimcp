"""
wikimcp.user — User management and config for the wikimcp server.
"""

from .config import (
    default_config,
    get_config_path,
    get_user,
    load_config,
    save_config,
)
from .manager import (
    add_remote,
    add_user,
    export_wiki,
    init_server,
    list_remotes,
    list_users,
    push_remote,
    remove_remote,
    remove_user,
    rotate_token,
)

__all__ = [
    # config
    "default_config",
    "get_config_path",
    "get_user",
    "load_config",
    "save_config",
    # manager
    "add_remote",
    "add_user",
    "export_wiki",
    "init_server",
    "list_remotes",
    "list_users",
    "push_remote",
    "remove_remote",
    "remove_user",
    "rotate_token",
]
