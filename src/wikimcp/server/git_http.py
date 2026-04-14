"""
git_http.py — Git smart HTTP backend for wikimcp.

Proxies git clone/fetch/push requests to git-http-backend (CGI) so users
can clone their wiki over HTTP:

    git clone https://yourserver.com/git/<username> my-wiki

Auth: same bearer token system as the rest of the server.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response

from wikimcp.server.auth import extract_token, validate_token
from wikimcp.server.router import resolve_wiki_dir
from wikimcp.user.config import load_config


def _find_git_http_backend() -> str:
    """Locate the git-http-backend binary."""
    # Try git --exec-path first (works on all platforms)
    try:
        result = subprocess.run(
            ["git", "--exec-path"],
            capture_output=True,
            text=True,
            check=True,
        )
        candidate = Path(result.stdout.strip()) / "git-http-backend"
        if candidate.exists():
            return str(candidate)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Common fallback paths
    for path in (
        "/usr/lib/git-core/git-http-backend",
        "/usr/libexec/git-core/git-http-backend",
    ):
        if Path(path).exists():
            return path

    raise FileNotFoundError(
        "git-http-backend not found. Ensure git is installed."
    )


def _run_git_http_backend(
    wiki_dir: Path,
    path_info: str,
    query_string: str,
    method: str,
    content_type: str,
    body: bytes,
) -> tuple[int, dict, bytes]:
    """
    Execute git-http-backend as a CGI subprocess.

    Returns (status_code, headers_dict, body_bytes).
    """
    backend = _find_git_http_backend()

    env = {
        "GIT_PROJECT_ROOT": str(wiki_dir),
        "GIT_HTTP_EXPORT_ALL": "1",
        "PATH_INFO": path_info,
        "QUERY_STRING": query_string,
        "REQUEST_METHOD": method,
        "CONTENT_TYPE": content_type or "",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    if body:
        env["CONTENT_LENGTH"] = str(len(body))

    result = subprocess.run(
        [backend],
        input=body,
        capture_output=True,
        env=env,
        timeout=60,
    )

    # Parse CGI output: headers separated from body by \r\n\r\n or \n\n
    raw = result.stdout
    separator = b"\r\n\r\n"
    idx = raw.find(separator)
    if idx == -1:
        separator = b"\n\n"
        idx = raw.find(separator)

    if idx == -1:
        # No header/body separator — treat entire output as body
        return 200, {}, raw

    header_block = raw[:idx].decode("utf-8", errors="replace")
    response_body = raw[idx + len(separator):]

    headers = {}
    status_code = 200
    for line in header_block.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("status:"):
            # e.g. "Status: 404 Not Found"
            parts = line.split(":", 1)[1].strip().split(" ", 1)
            status_code = int(parts[0])
        elif ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()

    return status_code, headers, response_body


def create_git_http_router(config_path: Path) -> APIRouter:
    """
    Create a FastAPI router that serves git repos over HTTP.

    Routes:
        GET/POST /git/{username}/{path:path}

    Users authenticate with the same bearer token used for MCP and the
    web reader (?token= query param or Authorization header).
    Also supports HTTP Basic auth (username + token as password) for
    compatibility with git credential helpers.
    """
    config_path = Path(config_path)
    router = APIRouter()

    def _get_config() -> dict:
        return load_config(config_path)

    def _auth(request: Request, username: str, config: dict) -> Optional[str]:
        """Authenticate via bearer token or HTTP Basic (token as password)."""
        # Try bearer token first
        token = extract_token(request)
        if token:
            validated = validate_token(token, config)
            if validated == username:
                return token

        # Try HTTP Basic auth (git clients send this)
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("basic "):
            import base64
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                basic_user, basic_pass = decoded.split(":", 1)
                validated = validate_token(basic_pass, config)
                if validated == username:
                    return basic_pass
            except (ValueError, UnicodeDecodeError):
                pass

        return None

    async def _handle_git(username: str, path: str, request: Request) -> Response:
        config = _get_config()

        token = _auth(request, username, config)
        if token is None:
            return Response(
                content="Authentication required",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="wikimcp git"'},
            )

        try:
            wiki_dir = resolve_wiki_dir(username, config)
        except (KeyError, ValueError):
            return Response(content="User not found", status_code=404)

        # path_info for git-http-backend: /<repo-path>
        # Since GIT_PROJECT_ROOT points to wiki_dir's parent and the repo
        # is the wiki_dir itself, we use the username as the repo name.
        # We set GIT_PROJECT_ROOT to the parent of wiki_dir so that
        # /username/<path> resolves to wiki_dir/<path>.
        path_info = f"/{wiki_dir.name}/{path}"
        query_string = str(request.url.query) if request.url.query else ""
        body = await request.body()

        try:
            status, headers, resp_body = _run_git_http_backend(
                wiki_dir=wiki_dir.parent,
                path_info=path_info,
                query_string=query_string,
                method=request.method,
                content_type=request.headers.get("content-type", ""),
                body=body,
            )
        except FileNotFoundError as exc:
            return Response(content=str(exc), status_code=500)
        except subprocess.TimeoutExpired:
            return Response(content="Git operation timed out", status_code=504)

        return Response(
            content=resp_body,
            status_code=status,
            headers=headers,
        )

    @router.get("/git/{username}/{path:path}")
    async def git_get(username: str, path: str, request: Request) -> Response:
        return await _handle_git(username, path, request)

    @router.post("/git/{username}/{path:path}")
    async def git_post(username: str, path: str, request: Request) -> Response:
        return await _handle_git(username, path, request)

    return router
