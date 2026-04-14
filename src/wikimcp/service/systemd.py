"""
systemd.py — Generate and install a systemd service unit for wikimcp.

The generated unit runs:
  <wikimcp_bin> server start --dir <server_dir> --port <port>

as the `wikimcp` system user and restarts on failure.
"""

from __future__ import annotations

import os
import subprocess


_SERVICE_TEMPLATE = """\
[Unit]
Description=wikimcp MCP server
After=network.target

[Service]
Type=simple
User=wikimcp
ExecStart={wikimcp_bin} server start --dir {server_dir} --port {port}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

_SERVICE_PATH = "/etc/systemd/system/wikimcp.service"


def generate_service_file(
    server_dir: str,
    port: int,
    wikimcp_bin: str = "wikimcp",
) -> str:
    """
    Return the systemd unit file content as a string.

    Parameters
    ----------
    server_dir:
        Absolute path to the wikimcp server data directory.
    port:
        Port number the server will listen on.
    wikimcp_bin:
        Path or name of the wikimcp executable (default: "wikimcp", resolved
        via PATH at runtime).
    """
    return _SERVICE_TEMPLATE.format(
        wikimcp_bin=wikimcp_bin,
        server_dir=server_dir,
        port=port,
    )


def install_service(server_dir: str, port: int) -> None:
    """
    Write the systemd unit file and enable + start the service.

    Must be run as root (UID 0). Raises PermissionError otherwise.

    Steps:
      1. Write /etc/systemd/system/wikimcp.service
      2. systemctl daemon-reload
      3. systemctl enable wikimcp
      4. systemctl start wikimcp
    """
    if os.geteuid() != 0:
        raise PermissionError(
            "install_service must be run as root. "
            "Try: sudo wikimcp install-service"
        )

    content = generate_service_file(server_dir, port)

    with open(_SERVICE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    for cmd in (
        ["systemctl", "daemon-reload"],
        ["systemctl", "enable", "wikimcp"],
        ["systemctl", "start", "wikimcp"],
    ):
        subprocess.run(cmd, check=True)
