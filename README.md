# Shipy

The opinionated Indie Maker Python web framework for shipping MVPs stupid-fast.

- App, Request, Response, routing (imperative)
- Jinja2 templates via `shipy.render.render()`
- SQLite helpers in `shipy.sql` (`query`, `one`, `execute`, `tx`)
- Built-in auth with users/sessions
- Signed-cookie sessions with CSRF + flash in `shipy.session`
- CLI: `shipy new`, `shipy dev`, `shipy db init`, `shipy deploy`

Note: The SQL write helper is named `execute` (not `exec`, since `exec` is a Python keyword).

## Quick start

```bash
pip install shipy-web
shipy new myapp && cd myapp
shipy db init
shipy dev
```

Visit http://localhost:8000 and sign up to get started!

## Example

See `examples/hello/app/main.py:1` and `examples/hello/app/views/home/index.html:1`.

## CLI

- `shipy new <name>` — creates an auth-first scaffolded project in `./<name>`
- `shipy dev [--app app.main:app] [--host 127.0.0.1] [--port 8000]`
- `shipy db init [--db ./data/app.db] [--schema data/schema.sql]` — initialize database
- `shipy db path` — show resolved database path
- `shipy deploy` — deployment helpers

## Templates

Default template root is `app/views`. Use `shipy.render.render('path/to/template.html', ctx, request=req)`.

## Sessions

Session data is stored in a signed cookie using `itsdangerous`. Set `SHIPY_SECRET` in your environment for production.

Flash messages are available via `req.session.flash(message, category)` and `req.session.get_flashed_messages()` in requests. CSRF token via `req.session.get_csrf_token()`.

## Database

SQLite helpers in `shipy/sql.py:1` use `./data/app.db` by default (created as needed).

Override the database path with `SHIPY_DB` environment variable:

```bash
SHIPY_DB=/path/to/custom.db shipy dev
```

- `query(sql, params=()) -> list[dict]`
- `one(sql, params=()) -> dict | None`
- `execute(sql, params=()) -> int`
- `with tx() as conn: conn.execute(...)`

Apply schema with `shipy db init --schema data/schema.sql`.

## License

MIT — see `LICENSE:1`.
