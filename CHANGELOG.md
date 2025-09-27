# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2024-12-26

### Added

- **Routing Documentation**: Complete HTTP methods documentation (GET, POST, PUT, PATCH, DELETE)
- **HTMX Response Helpers**: Added `Response.htmx_redirect()` and `Response.htmx_refresh()` documentation
- **Enhanced CLI Documentation**: All CLI commands now properly documented with descriptions

### Improved

- **Tutorial Formatting**: Fixed code fence structure and formatting issues
- **Edit Functionality**: Enhanced inline editing with proper save-on-enter/blur and escape-to-cancel
- **Technical Accuracy**: Corrected CSRF implementation and HTMX behavior explanations
- **Documentation Clarity**: Improved readability and organization throughout

### Fixed

- **Code Fence Issues**: Resolved nested four-backtick blocks in tutorial
- **HTMX Triggers**: Proper separation of PUT and GET functionality in edit templates
- **Template Structure**: Fixed HTML nesting and structural issues

## [0.3.2] - 2024-12-26

### Fixed

- **Critical HTMX Bug**: Added missing `headers` attribute to Request object
- **HTMX Functionality**: Fixed `is_htmx_request()` function causing 500 errors
- **Request Object**: Headers are now properly parsed and accessible as `req.headers`

## [0.3.1] - 2024-12-26

### Fixed

- **CLI Syntax Error**: Resolved invalid dictionary key syntax in scaffold template
- **Middleware Reliability**: Added `get_user_safely()` helper function for robust user access
- **Tutorial Improvements**: Enhanced virtual environment setup instructions

### Changed

- **Scaffold Template**: Moved main.py content outside dictionary to avoid syntax issues
- **File Writing Logic**: Added support for string paths in file generation
- **Documentation**: Improved tutorial formatting and clarity

## [0.3.0] - 2024-12-26

### Added

- **Database Migration System**: `shipy db run`, `shipy db make-migration`, `shipy db ls`, `shipy db shell` commands
- **Middleware Support**: `@app.middleware("request")` decorator with `req.state` for per-request storage
- **Authentication Decorator**: `@login_required()` decorator for route protection with automatic redirects
- **HTMX Support**: `render_htmx()`, `is_htmx_request()`, HTMX response helpers (`htmx_redirect`, `htmx_refresh`)
- **Additional HTTP Methods**: `app.put()`, `app.patch()`, `app.delete()` route registration
- **Comprehensive Documentation**: Complete API reference (`docs.md`) and step-by-step tutorial (`tutorial.md`)
- **Enhanced CLI**: New database management commands and improved development workflow

### Changed

- **Template Rendering**: Added HTMX-aware rendering with `htmx` context object
- **Request Object**: Added `req.state` for per-request data storage
- **Response Class**: Added HTMX-specific response methods
- **Scaffold Templates**: Updated to include HTMX CDN and modern examples

### Fixed

- **Documentation**: Complete API reference with examples for all functions
- **Tutorial**: Comprehensive guide for building production-ready applications
- **CLI Help**: Updated help text and command descriptions

## [0.2.1] - 2024-12-19

### Added

- `shipy --version` command to display current version
- GitHub Actions workflow for automated releases
- Updated README with auth-first quickstart and current CLI commands

### Fixed

- README now reflects current auth-first scaffold and database defaults
- CLI documentation updated to show correct commands and paths

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
