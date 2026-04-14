"""
schema.py — Wiki scaffolding and CLAUDE.md template.
"""

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def get_claude_md_template() -> str:
    """Return the CLAUDE.md template shipped with the package."""
    template_path = _TEMPLATES_DIR / "CLAUDE.md"
    return template_path.read_text(encoding="utf-8")


def scaffold_wiki(wiki_dir: Path) -> None:
    """
    Create the full wiki folder structure under wiki_dir.

    Creates:
      CLAUDE.md
      wiki/index.md
      wiki/log.md
      wiki/chats/.gitkeep
      wiki/topics/.gitkeep
      wiki/entities/.gitkeep
      raw/.gitkeep

    Does not initialise a git repo — call git_layer.init_repo() separately.
    Does not overwrite files that already exist.
    """
    wiki_dir = Path(wiki_dir)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # CLAUDE.md at the wiki root
    claude_md = wiki_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(get_claude_md_template(), encoding="utf-8")

    # wiki/ subdirectory
    wiki_subdir = wiki_dir / "wiki"
    wiki_subdir.mkdir(exist_ok=True)

    # wiki/index.md
    index_md = wiki_subdir / "index.md"
    if not index_md.exists():
        index_md.write_text(
            "# Wiki Index\n\nThis is the master catalog of all pages in this wiki."
            "\nUpdate it whenever you create or significantly modify a page.\n",
            encoding="utf-8",
        )

    # wiki/log.md
    log_md = wiki_subdir / "log.md"
    if not log_md.exists():
        log_md.write_text("# Activity Log\n\n", encoding="utf-8")

    # Empty directories with .gitkeep
    for subdir_name in ("chats", "topics", "entities"):
        subdir = wiki_subdir / subdir_name
        subdir.mkdir(exist_ok=True)
        gitkeep = subdir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # raw/ directory
    raw_dir = wiki_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    raw_gitkeep = raw_dir / ".gitkeep"
    if not raw_gitkeep.exists():
        raw_gitkeep.touch()
