"""
launchd.py — Generate and install a macOS launchd plist for wikimcp.

The generated plist runs:
  <wikimcp_bin> server start --dir <server_dir> --port <port>

under the current user's LaunchAgents at startup, logging to
~/Library/Logs/wikimcp.log.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wikimcp.server</string>

    <key>ProgramArguments</key>
    <array>
        <string>{wikimcp_bin}</string>
        <string>server</string>
        <string>start</string>
        <string>--dir</string>
        <string>{server_dir}</string>
        <string>--port</string>
        <string>{port}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{log_path}</string>

    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>
"""

_PLIST_LABEL = "com.wikimcp.server"
_PLIST_FILENAME = f"{_PLIST_LABEL}.plist"


def _launch_agents_dir() -> Path:
    """Return ~/Library/LaunchAgents, creating it if necessary."""
    path = Path.home() / "Library" / "LaunchAgents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_path() -> Path:
    """Return the path used for wikimcp log output."""
    log_dir = Path.home() / "Library" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "wikimcp.log"


def generate_plist(
    server_dir: str,
    port: int,
    wikimcp_bin: str = "wikimcp",
) -> str:
    """
    Return the launchd plist XML content as a string.

    Parameters
    ----------
    server_dir:
        Absolute path to the wikimcp server data directory.
    port:
        Port number the server will listen on.
    wikimcp_bin:
        Path or name of the wikimcp executable (default: "wikimcp", resolved
        via PATH at runtime by launchd).
    """
    return _PLIST_TEMPLATE.format(
        wikimcp_bin=wikimcp_bin,
        server_dir=server_dir,
        port=port,
        log_path=str(_log_path()),
    )


def install_service(server_dir: str, port: int) -> None:
    """
    Write the launchd plist and load it with launchctl.

    Steps:
      1. Write ~/Library/LaunchAgents/com.wikimcp.server.plist
      2. launchctl load -w <plist_path>

    The service will start immediately and on every login.
    If a previous version is already loaded, it is unloaded first.
    """
    plist_path = _launch_agents_dir() / _PLIST_FILENAME
    content = generate_plist(server_dir, port)

    # Unload any existing instance (ignore errors if not loaded)
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", "-w", str(plist_path)],
            check=False,
            capture_output=True,
        )

    plist_path.write_text(content, encoding="utf-8")

    subprocess.run(
        ["launchctl", "load", "-w", str(plist_path)],
        check=True,
    )
