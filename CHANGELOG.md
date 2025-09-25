# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-19

### Added

- Auth-first scaffold with users and sessions tables
- Per-project database default (`./data/app.db`) with auto-schema initialization
- `shipy db init` command for database initialization
- `shipy db path` command to show resolved database path
- Environment variable support (`SHIPY_DB`, `SHIPY_APP_ROOT`)
- Boot information logging in `shipy dev` command
- Comprehensive test suite for database bootstrap and auth flow
- Development guide (`DEV.md`) with manual smoke tests

### Changed

- Default database path from `./db/app.sqlite` to `./data/app.db`
- Schema auto-applies on first database connection
- CLI scaffold templates now generate auth-first applications
- Updated README with new quickstart and auth-first messaging

### Removed

- Posts demo functionality from scaffold templates
- Posts-related routes and templates from generated projects
- References to posts in documentation and examples

### Fixed

- Database path resolution respects environment variables
- Schema application is idempotent (safe to run multiple times)
- Improved error handling in database initialization

## [0.1.1] - Previous Release

- Initial release with posts demo scaffold
- Basic CLI commands (`new`, `dev`, `db apply`)
- SQLite helpers and session management
- Jinja2 template rendering
