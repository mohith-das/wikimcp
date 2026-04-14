# Changelog

All notable changes to wikimcp will be documented in this file.

## [0.1.1] - 2026-04-14

### Added
- Initial public release of wikimcp (0.1.0 was a name reservation)
- MCP server with 9 wiki tools (wiki_info, read_index, update_index, write_page, read_page, list_pages, search_wiki, append_log, delete_page)
- Git-backed wiki with auto-commit on every write
- Multi-user support with bearer token authentication
- Web reader UI (FastAPI + Jinja2) for browsing wikis
- CLI with full command set: init, serve, server management, user management, remote management, export, install-service
- systemd (Linux) and launchd (macOS) service installation
- CLAUDE.md schema template for AI workflow guidance
- Local mode (stdio/HTTP) and server mode (multi-user HTTP)
