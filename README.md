[![PyPI version](https://badge.fury.io/py/wikimcp.svg)](https://pypi.org/project/wikimcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# wikimcp

**Git-backed multi-user wiki MCP server — long-term memory for any AI.**

Your knowledge compounds across conversations instead of resetting every session.
Inspired by [Andrej Karpathy's LLM Wiki pattern](https://x.com/karpathy/status/1876288339308638596).

---

## What it is

`wikimcp` is a Python package that runs an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server backed by a personal, git-versioned wiki.

- Any MCP-compatible AI client (Claude Desktop, LM Studio, Gemini CLI, ChatGPT, claude.ai) can read and write to the wiki during a conversation.
- Every write is auto-committed to git — full history, branching, and remote sync (GitHub, Gitea, any bare repo).
- Users browse their wiki via a read-only web reader or locally in Obsidian.
- Multi-user server mode: each user has their own wiki, isolated by bearer-token auth.

---

## Quick Start (local, single-user)

```bash
pip install wikimcp

# 1. Scaffold the wiki and generate the MCP config snippet
wikimcp init

# 2. Paste the printed JSON into your Claude Desktop config file
#    macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
#    Linux: ~/.config/Claude/claude_desktop_config.json

# 3. Restart Claude Desktop — the wikimcp tools are now available
```

The config snippet looks like:

```json
{
  "mcpServers": {
    "wikimcp": {
      "command": "wikimcp",
      "args": ["serve", "--wiki-dir", "/Users/you/llm-wiki"]
    }
  }
}
```

Then in any Claude conversation, the AI will call `wiki_info` at the start of each session and keep your wiki updated automatically.

---

## CLI Reference

### Local mode

```bash
wikimcp init [--wiki-dir ~/llm-wiki]
```
Scaffold wiki folder, initialise git repo, print MCP config snippet.

```bash
wikimcp serve [--wiki-dir ~/llm-wiki] [--transport stdio|http] [--host 127.0.0.1] [--port 8765]
```
Start the MCP server. `stdio` (default) for Claude Desktop / LM Studio / Gemini CLI. `http` for ChatGPT / claude.ai via ngrok.

---

### Server mode (multi-user, always-on)

```bash
wikimcp server init [--dir /data/wikimcp] [--port 8765]
```
Initialise the server data directory and `wikimcp.conf`.

```bash
wikimcp server start [--dir /data/wikimcp] [--port 8765] [--host 0.0.0.0]
```
Start the multi-user HTTP MCP server + web reader.

- MCP endpoint: `https://host:port/mcp` (bearer-token auth)
- Web reader: `https://host:port/wiki/<username>` (token auth)
- Health check: `https://host:port/health`

```bash
wikimcp server stop
wikimcp server status [--dir /data/wikimcp]
```

---

### User management

```bash
wikimcp add-user <username> [--dir /data/wikimcp]
```
Create a user, scaffold their wiki, generate their bearer token.

Prints:
```
Token:    wikimcp_alice_<random>
MCP URL:  http://yourserver.com/mcp
Wiki URL: http://yourserver.com/wiki/alice
```

```bash
wikimcp remove-user <username> [--dir /data/wikimcp]
```
Delete user folder and config entry. Prompts for confirmation.

```bash
wikimcp list-users [--dir /data/wikimcp]
```
List all users with masked token, page count, and last active timestamp.

```bash
wikimcp rotate-token <username> [--dir /data/wikimcp]
```
Generate a new bearer token. The old token is immediately invalidated.

---

### Git remote management

```bash
wikimcp remote add <username> <remote-name> <git-url> [--dir /data/wikimcp]
# e.g.
wikimcp remote add alice github git@github.com:alice/my-wiki.git
```

```bash
wikimcp remote remove <username> <remote-name> [--dir /data/wikimcp]
wikimcp remote list <username> [--dir /data/wikimcp]
wikimcp remote push <username> [--remote <name>] [--dir /data/wikimcp]
```

---

### Export and service

```bash
wikimcp export <username> [--format zip|tar] [--out ./] [--dir /data/wikimcp]
```
Export a user's wiki as a zip or tar.gz archive.

```bash
wikimcp install-service [--dir /data/wikimcp] [--port 8765]
```
Install wikimcp as a system service (systemd on Linux, launchd on macOS) so the server starts on boot automatically.

---

## MCP Tools Reference

All tools are available in both local and server mode. In server mode, the user is resolved from their bearer token before any tool runs.

| Tool | Arguments | Description |
|------|-----------|-------------|
| `wiki_info` | — | Page count, log entry count, wiki root path. Call at session start. |
| `read_index` | — | Read `wiki/index.md` — the master catalog and starting point for any query. |
| `update_index` | `content` | Overwrite `wiki/index.md` and auto-commit. |
| `write_page` | `path`, `content` | Create or overwrite a wiki page and auto-commit. |
| `read_page` | `path` | Read a wiki page. |
| `list_pages` | `subdirectory?` | List all pages (or a subdirectory). |
| `search_wiki` | `query`, `case_sensitive?` | Full-text search across all pages. |
| `append_log` | `entry`, `operation?` | Append a timestamped entry to `wiki/log.md` and auto-commit. |
| `delete_page` | `path` | Delete a wiki page and auto-commit. |

Every mutating call (`write_page`, `update_index`, `append_log`, `delete_page`) triggers an automatic git commit:

```
wiki: write_page topics/graph-algorithms.md
wiki: append_log chat 2026-04-14T10:30:00Z
wiki: delete_page old-topic.md
```

Commit author: `wikimcp-bot <wikimcp@localhost>`

---

## Wiki Folder Structure

```
~/llm-wiki/                    (wiki root)
  CLAUDE.md                    ← schema and workflow guide (read by AI at session start)
  wiki/
    index.md                   ← master catalog of all pages
    log.md                     ← append-only activity log
    chats/                     ← one page per conversation (chat_YYYY-MM-DD_N.md)
    topics/                    ← concept and topic pages
    entities/                  ← people, tools, projects
  raw/                         ← your source documents (AI never modifies these)
  .git/                        ← full git history
```

---

## Auth

### Local mode
No auth. Server runs on `localhost`, stdio transport.

### Server mode
Bearer token per user. Every request must include:

```
Authorization: Bearer wikimcp_<username>_<random32>
```

Tokens are stored as SHA-256 hashes in `wikimcp.conf` — never plaintext.
Invalid token → 401. Valid token → user resolved → tool runs against that user's wiki.

---

## Server Mode Setup Guide

1. **Provision a VPS** with Python 3.10+ and `git` installed.

2. **Install wikimcp**:
   ```bash
   pip install wikimcp
   ```

3. **Initialise the server**:
   ```bash
   wikimcp server init --dir /data/wikimcp --port 8765
   ```

4. **Add users**:
   ```bash
   wikimcp add-user alice --dir /data/wikimcp
   wikimcp add-user bob   --dir /data/wikimcp
   ```
   Give each user their token and the MCP URL.

5. **Install as a system service**:
   ```bash
   sudo wikimcp install-service --dir /data/wikimcp --port 8765
   ```

6. **Point a reverse proxy** (nginx, Caddy) at port 8765 with TLS.

7. **Users configure their AI client** with the MCP URL and token:
   ```json
   {
     "mcpServers": {
       "wikimcp": {
         "url": "https://yourserver.com/mcp",
         "headers": { "Authorization": "Bearer wikimcp_alice_<token>" }
       }
     }
   }
   ```

---

## Web Reader

Each user has a read-only web UI at `https://yourserver.com/wiki/<username>`.

- Authenticate via `?token=<token>` query param or `Authorization: Bearer` header.
- Pages rendered as HTML from Markdown.
- Search bar, sidebar page tree, responsive layout.
- No editing through the UI — the AI writes, you read.

---

## Git Sync (Obsidian and local editing)

Users can clone their wiki and edit it locally in Obsidian or any editor:

```bash
git clone https://yourserver.com/git/alice my-wiki
cd my-wiki
# open in Obsidian
```

Edit in Obsidian → `git commit` → `git push origin main` → server picks up changes.

Or set up a GitHub mirror:

```bash
wikimcp remote add alice github git@github.com:alice/my-wiki.git --dir /data/wikimcp
wikimcp remote push alice --remote github --dir /data/wikimcp
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP — MCP server framework |
| `fastapi` | Web reader + HTTP MCP transport |
| `uvicorn` | ASGI server for FastAPI |
| `jinja2` | HTML templates for the web reader |
| `click` | CLI framework |
| `gitpython` | Git operations (commit, push, remote management) |
| `rich` | Beautiful CLI output (token display, tables, panels) |
| `markdown` | Markdown-to-HTML rendering in the web reader |

---

## Transport Modes

| Transport | Command | Used by |
|-----------|---------|---------|
| stdio | `wikimcp serve` (default) | Claude Desktop, LM Studio, Gemini CLI, Claude Code |
| HTTP | `wikimcp serve --transport http` | ChatGPT, claude.ai (via ngrok or public server) |
| HTTP | `wikimcp server start` | All clients (always-on multi-user server) |

---

## License

MIT
