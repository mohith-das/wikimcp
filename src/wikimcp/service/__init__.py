"""
wikimcp.service — System service installation for wikimcp.

Provides helpers for installing wikimcp as a persistent background service
on Linux (systemd) and macOS (launchd).
"""

from .launchd import generate_plist
from .launchd import install_service as install_launchd_service
from .systemd import generate_service_file
from .systemd import install_service as install_systemd_service

__all__ = [
    "generate_plist",
    "generate_service_file",
    "install_launchd_service",
    "install_systemd_service",
]
