"""Tests for the web reader routes."""

import hashlib
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from wikimcp.server.web_reader import create_web_reader, mount_static
from wikimcp.user.config import save_config
from wikimcp.wiki.git_layer import init_repo
from wikimcp.wiki.operations import write_page
from wikimcp.wiki.schema import scaffold_wiki


@pytest.fixture()
def wiki_env(tmp_path):
    """Set up a server dir with one user and a few wiki pages."""
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    users_dir = server_dir / "users"
    users_dir.mkdir()

    wiki_dir = users_dir / "testuser"
    wiki_dir.mkdir()
    scaffold_wiki(wiki_dir)
    init_repo(wiki_dir)

    token = "wikimcp_testuser_abc123"
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    config = {
        "version": "0.1",
        "port": 8765,
        "host": "0.0.0.0",
        "users": {
            "testuser": {
                "token_hash": token_hash,
                "wiki_dir": str(wiki_dir),
                "created_at": "2026-04-14T10:00:00Z",
                "last_active": None,
                "remotes": {},
                "auto_push_remotes": [],
            }
        },
    }
    config_path = server_dir / "wikimcp.conf"
    save_config(config_path, config)

    # Write a test page
    write_page(wiki_dir, "topics/python.md", "# Python\n\nA programming language.")

    return {
        "server_dir": server_dir,
        "wiki_dir": wiki_dir,
        "config_path": config_path,
        "token": token,
    }


@pytest.fixture()
def client(wiki_env):
    """Create a FastAPI test client with the web reader mounted."""
    app = FastAPI()
    router = create_web_reader(wiki_env["config_path"])
    app.include_router(router)
    mount_static(app)
    return TestClient(app)


def test_home_with_valid_token(client, wiki_env):
    resp = client.get(f"/wiki/testuser?token={wiki_env['token']}")
    assert resp.status_code == 200
    assert "Wiki Index" in resp.text


def test_home_without_token(client):
    resp = client.get("/wiki/testuser")
    assert resp.status_code == 401


def test_home_with_wrong_token(client):
    resp = client.get("/wiki/testuser?token=wrong_token")
    assert resp.status_code == 401


def test_page_renders_markdown(client, wiki_env):
    resp = client.get(f"/wiki/testuser/topics/python.md?token={wiki_env['token']}")
    assert resp.status_code == 200
    assert "Python" in resp.text
    assert "programming language" in resp.text


def test_page_not_found(client, wiki_env):
    resp = client.get(f"/wiki/testuser/topics/nonexistent.md?token={wiki_env['token']}")
    assert resp.status_code == 404


def test_page_without_extension(client, wiki_env):
    """Requesting a path without .md should still resolve."""
    resp = client.get(f"/wiki/testuser/topics/python?token={wiki_env['token']}")
    assert resp.status_code == 200
    assert "Python" in resp.text


def test_search_with_results(client, wiki_env):
    resp = client.get(f"/wiki/testuser/_search?q=Python&token={wiki_env['token']}")
    assert resp.status_code == 200
    assert "Python" in resp.text
    assert "topics/python.md" in resp.text


def test_search_no_results(client, wiki_env):
    resp = client.get(f"/wiki/testuser/_search?q=zzzznotfound&token={wiki_env['token']}")
    assert resp.status_code == 200
    assert "No results" in resp.text or "no results" in resp.text.lower()


def test_search_empty_query(client, wiki_env):
    resp = client.get(f"/wiki/testuser/_search?q=&token={wiki_env['token']}")
    assert resp.status_code == 200


def test_auth_via_bearer_header(client, wiki_env):
    resp = client.get(
        "/wiki/testuser",
        headers={"Authorization": f"Bearer {wiki_env['token']}"},
    )
    assert resp.status_code == 200


def test_wrong_user_token(client, wiki_env):
    """Token for testuser should not grant access to a different username."""
    resp = client.get(f"/wiki/otheruser?token={wiki_env['token']}")
    assert resp.status_code == 401


def test_sidebar_contains_pages(client, wiki_env):
    resp = client.get(f"/wiki/testuser?token={wiki_env['token']}")
    assert resp.status_code == 200
    # Sidebar should list the python page
    assert "python" in resp.text.lower()


def test_static_css_served(client):
    resp = client.get("/static/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers.get("content-type", "")
