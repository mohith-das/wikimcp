"""Tests for wikimcp.wiki.git_layer — init_repo and auto_commit."""
import pytest
from pathlib import Path

import git as gitpython

from wikimcp.wiki.git_layer import init_repo, auto_commit


def test_init_repo_creates_git_dir(tmp_path: Path) -> None:
    init_repo(tmp_path)
    assert (tmp_path / ".git").is_dir()


def test_init_repo_is_idempotent(tmp_path: Path) -> None:
    init_repo(tmp_path)
    # Calling again should not raise
    init_repo(tmp_path)
    assert (tmp_path / ".git").is_dir()


def test_init_repo_makes_initial_commit_when_files_exist(tmp_path: Path) -> None:
    (tmp_path / "hello.md").write_text("hello", encoding="utf-8")
    init_repo(tmp_path)
    repo = gitpython.Repo(str(tmp_path))
    commits = list(repo.iter_commits())
    assert len(commits) >= 1
    assert commits[0].message.startswith("wiki: initial commit")


def test_auto_commit_creates_commit(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "page.md").write_text("content", encoding="utf-8")
    auto_commit(tmp_path, "wiki: test commit")
    repo = gitpython.Repo(str(tmp_path))
    commits = list(repo.iter_commits())
    messages = [c.message.strip() for c in commits]
    assert "wiki: test commit" in messages


def test_auto_commit_noop_when_clean(tmp_path: Path) -> None:
    (tmp_path / "page.md").write_text("content", encoding="utf-8")
    init_repo(tmp_path)
    repo = gitpython.Repo(str(tmp_path))
    commit_count_before = len(list(repo.iter_commits()))
    # Nothing changed — auto_commit should be a no-op
    auto_commit(tmp_path, "wiki: should not commit")
    commit_count_after = len(list(repo.iter_commits()))
    assert commit_count_after == commit_count_before


def test_auto_commit_stages_new_file(tmp_path: Path) -> None:
    init_repo(tmp_path)
    new_file = tmp_path / "wiki" / "notes.md"
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_text("# Notes", encoding="utf-8")
    auto_commit(tmp_path, "wiki: add notes")
    repo = gitpython.Repo(str(tmp_path))
    # commit.stats.files is a dict mapping file path str -> stats dict
    committed_files = {
        file_path
        for commit in repo.iter_commits()
        for file_path in commit.stats.files
    }
    assert any("notes.md" in f for f in committed_files)
