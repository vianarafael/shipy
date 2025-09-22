# Shipy

Tiny Python web toolkit + CLI.

- App, Request, Response, routing (imperative)
- Jinja2 templates via `shipy.render.render()`
- SQLite helpers in `shipy.sql` (`query`, `one`, `execute`, `tx`)
- Signed-cookie sessions with CSRF + flash in `shipy.session`
- CLI: `shipy new`, `shipy dev`, `shipy db apply`, `shipy deploy`

Note: The SQL write helper is named `execute` (not `exec`, since `exec` is a Python keyword).

## Quick start

- Install dependencies: `pip install jinja2 itsdangerous uvicorn watchfiles`
- Scaffold a new app:
  - `shipy new myapp`
  - `cd myapp`
  - `shipy dev`
- Or try the included example:
  - `cd examples/hello`
  - `shipy dev` (uses uvicorn + autoreload if installed)
  - Or: `uvicorn examples.hello.app.main:asgi --reload`

## Example

See `examples/hello/app/main.py:1` and `examples/hello/app/views/home/index.html:1`.

## CLI

- `shipy new <name>` — creates a scaffolded project in `./<name>`
- `shipy dev [--app app.main:app] [--host 127.0.0.1] [--port 5000]`
- `shipy db apply [--db ./db/app.db] [--schema db/schema.sql]`
- `shipy deploy` — placeholder helper

## Templates

Default template root is `app/views`. Use `shipy.render.render('path/to/template.html', ctx, request=req)`.

## Sessions

Session data is stored in a signed cookie using `itsdangerous`. Set `SHIPY_SECRET` in your environment for production.

Flash messages are available via `req.session.flash(message, category)` and `req.session.get_flashed_messages()` in requests. CSRF token via `req.session.get_csrf_token()`.

## Database

SQLite helpers in `shipy/sql.py:1` use `./db/app.db` by default (created as needed).

- `query(sql, params=()) -> list[dict]`
- `one(sql, params=()) -> dict | None`
- `execute(sql, params=()) -> int`
- `with tx() as conn: conn.execute(...)`

Apply schema with `shipy db apply --schema db/schema.sql`.

## License

MIT — see `LICENSE:1`.
