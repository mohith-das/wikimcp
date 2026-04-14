"""
schema.py — Wiki scaffolding and CLAUDE.md template.
"""

from pathlib import Path


def get_claude_md_template() -> str:
    """Return the CLAUDE.md template string that is written to every wiki root on init."""
    return """\
# CLAUDE.md — Wiki Schema & Workflow Guide

This file describes the structure and conventions of this wiki. Read it at the
start of every session so you understand how knowledge is organised and how to
maintain it correctly.

---

## Directory Structure

```
<wiki-dir>/
  CLAUDE.md              ← this file — schema and workflow guide
  wiki/
    index.md             ← master catalog (read this first on every query)
    log.md               ← append-only activity log (one entry per session)
    chats/               ← one page per conversation (chat_YYYY-MM-DD_N.md)
    topics/              ← concept and topic pages (e.g. topics/graph-algorithms.md)
    entities/            ← people, tools, projects (e.g. entities/python.md)
  raw/                   ← source documents the user drops in; never modify these
  .git/                  ← git repo — every write is auto-committed
```

---

## Page Frontmatter Conventions

Every wiki page (except log.md) should begin with YAML front matter:

```yaml
---
title: "Page Title"
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

- `title` — human-readable page title
- `tags` — list of relevant tags for cross-referencing
- `created` — ISO date the page was first written
- `updated` — ISO date the page was last modified (update on every write)
- Omit fields you don't have values for rather than leaving them blank

---

## Post-Chat Workflow

At the end of every conversation session, you MUST:

1. **Update relevant pages** — for every topic, entity, or concept discussed,
   update its page under `wiki/topics/` or `wiki/entities/`. Create the page
   if it does not exist.

2. **Write a chat summary** — create a new page under `wiki/chats/` named
   `chat_YYYY-MM-DD_N.md` (where N is a sequence number if there are multiple
   chats on the same day). Include:
   - A 2–5 sentence summary of what was discussed
   - Key decisions or conclusions reached
   - Links to any topic/entity pages that were updated

3. **Append to the log** — call `append_log` with a one-line summary of the
   session and any operation label (e.g. `operation="chat"`).

4. **Update index.md** — if new pages were created or significant changes were
   made, update the master catalog in `wiki/index.md` to reflect them.

---

## Ingest Workflow

When a user asks you to process a document from `raw/`:

1. Read the document from `raw/<filename>`
2. Extract key entities, topics, and facts
3. Create or update pages under `wiki/topics/` and `wiki/entities/`
4. Write a summary page under `wiki/chats/` or a dedicated ingest note
5. Update `wiki/index.md` to include the new pages
6. Append to `wiki/log.md` with `operation="ingest"`

Do NOT modify anything inside `raw/` — it is the user's source material.

---

## Query Workflow

When a user asks a question or wants to explore the wiki:

1. Call `read_index` to load `wiki/index.md` — this is your map
2. Identify relevant sections and follow links to specific pages
3. Call `read_page` for each relevant page
4. If you need to find something not in the index, call `search_wiki`
5. Synthesise and answer — cite the pages you used

Do NOT guess or hallucinate wiki content. Always read first.

---

## index.md Format

`wiki/index.md` is the master catalog. Keep it structured like this:

```markdown
# Wiki Index

_Last updated: YYYY-MM-DD_

## Topics
- [Graph Algorithms](topics/graph-algorithms.md) — shortest paths, MSTs, BFS/DFS
- [Python](topics/python.md) — language notes, libraries, patterns

## Entities
- [Alice Smith](entities/alice-smith.md) — colleague, ML engineer
- [Project Falcon](entities/project-falcon.md) — Q3 2026 initiative

## Recent Activity
- YYYY-MM-DD: [Chat summary](chats/chat_YYYY-MM-DD_1.md)
```

- Keep each section alphabetically sorted
- Each entry is a markdown link followed by a brief one-line description
- Update the "Last updated" date on every modification
- "Recent Activity" shows the last 5–10 chat entries

---

## Tone & Style Guidelines

- **Concise** — prefer bullet points and short paragraphs over prose
- **Factual** — record what was said or decided; no speculation
- **Linked** — always link related pages using relative markdown links
- **Dated** — include dates wherever relevant (decisions, facts, events)
- **Neutral** — write in third person or imperative; no "I" or "we"
- **Evergreen** — write pages so they remain useful weeks or months later;
  avoid phrases like "recently" or "last week" — use explicit dates instead

---

## File Naming Conventions

| Location | Pattern | Example |
|----------|---------|---------|
| `wiki/chats/` | `chat_YYYY-MM-DD_N.md` | `chat_2026-04-14_1.md` |
| `wiki/topics/` | `kebab-case.md` | `graph-algorithms.md` |
| `wiki/entities/` | `kebab-case.md` | `alice-smith.md` |
| `raw/` | any (user's files) | `paper.pdf`, `notes.txt` |

---

## What the AI Must Never Do

- Never modify files inside `raw/`
- Never delete `index.md` or `log.md`
- Never write outside the `wiki/` directory (except CLAUDE.md which is read-only)
- Never use absolute paths when calling wiki tools — always use paths relative
  to the `wiki/` subdirectory (e.g. `topics/python.md`, not `/wiki/topics/python.md`)
"""


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
