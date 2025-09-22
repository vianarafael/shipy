from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path


def _print(s: str) -> None:
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def cmd_dev(args: argparse.Namespace) -> None:
    app_path = args.app or "app.main:app"
    host = args.host
    port = int(args.port)

    if ":" not in app_path:
        sys.stderr.write("--app must be in module:var format, e.g. app.main:app\n")
        sys.exit(2)
    mod_name, var_name = app_path.split(":", 1)
    try:
        mod = importlib.import_module(mod_name)
        app = getattr(mod, var_name)
    except Exception as exc:
        sys.stderr.write(f"Error importing {app_path}: {exc}\n")
        sys.exit(1)

    # Mount /public if directory exists in CWD
    public_dir = Path(os.getcwd()) / "public"
    try:
        from .app import App
    except Exception:
        App = None  # type: ignore
    if public_dir.exists() and hasattr(app, "mount_static"):
        app.mount_static("/public", str(public_dir))

    # Prefer Uvicorn (ASGI) with a WSGI adapter when available
    try:
        from uvicorn import run as uvicorn_run  # type: ignore
        from uvicorn.middleware.wsgi import WSGIMiddleware  # type: ignore

        asgi_app = WSGIMiddleware(app)
        _print(f"Starting uvicorn with autoreload on http://{host}:{port}")
        uvicorn_run(asgi_app, host=host, port=port, reload=True, log_level="info")
        return
    except Exception:
        # Uvicorn not available or failed to import; fall back to WSGI server
        pass

    if hasattr(app, "run"):
        app.run(host=host, port=port)
    else:
        from wsgiref.simple_server import make_server

        with make_server(host, port, app) as httpd:
            _print(f"shipy dev server running on http://{host}:{port}")
            httpd.serve_forever()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cmd_new(args: argparse.Namespace) -> None:
    name = args.name
    root = Path(args.directory or os.getcwd()) / name
    if root.exists() and any(root.iterdir()):
        sys.stderr.write(f"Refusing to scaffold into non-empty directory: {root}\n")
        sys.exit(1)

    # Scaffold structure similar to examples/hello
    app_dir = root / "app"
    views_dir = app_dir / "views" / "home"
    public_dir = root / "public"
    db_dir = root / "db"

    main_py = f"""
from shipy import App, html
from shipy.render import render
import os

app = App()

# Serve ./public as /public
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir, 'public'))
if os.path.isdir(PUBLIC_DIR):
    app.mount_static('/public', PUBLIC_DIR)


def home(req):
    # Simple session-backed visit counter
    visits = int(req.session.get('visits', 0)) + 1
    req.session['visits'] = visits
    return html(render('home/index.html', {{'visits': visits}}, request=req))


app.get('/', home)
""".strip()

    index_html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Shipy • Hello</title>
    <link rel="stylesheet" href="/public/base.css" />
  </head>
  <body>
    <main class="container">
      <h1>👋 Hello from Shipy</h1>
      <p>This page is rendered with Jinja2. It also demonstrates a cookie session.</p>
      <p><strong>Visits this session:</strong> {{ visits }}</p>
      <p>Try refreshing! Edit <code>app/views/home/index.html</code> to change this page.</p>
    </main>
  </body>
</html>
""".lstrip()

    base_css = """
/* Minimal baseline styles */
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; }
.container { max-width: 720px; margin: 3rem auto; padding: 0 1rem; }
h1 { font-size: 2rem; }
code { background: #f3f4f6; padding: .1rem .3rem; border-radius: .25rem; }
""".lstrip()

    schema_sql = """
-- Example schema (optional)
-- Run: shipy db apply --schema db/schema.sql
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    body TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""".lstrip()

    _write(app_dir / "main.py", main_py + "\n")
    _write(views_dir / "index.html", index_html)
    _write(public_dir / "base.css", base_css)
    _write(db_dir / "schema.sql", schema_sql)

    _print(f"Project created at {root}")
    _print("Next:")
    _print(f"  cd {root}")
    _print("  shipy dev")


def cmd_db(args: argparse.Namespace) -> None:
    action = args.action
    db_path = args.db or None
    schema = args.schema or os.path.join("db", "schema.sql")

    from . import sql

    if action == "apply":
        if not os.path.exists(schema):
            sys.stderr.write(f"Schema not found: {schema}\n")
            sys.exit(1)
        script = Path(schema).read_text(encoding="utf-8")
        sql.executescript(script, db_path=db_path)
        _print(f"Applied schema to {db_path or sql._default_db_path()}")
    else:
        sys.stderr.write(f"Unknown db action: {action}\n")
        sys.exit(2)


def cmd_deploy(_args: argparse.Namespace) -> None:
    _print("Deploy helper is a placeholder. Suggested next steps:")
    _print("- Package your app with your preferred process manager")
    _print("- Or create a Dockerfile + run under gunicorn/uvicorn with a WSGI server")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="shipy", description="Shipy CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Scaffold a new Shipy app")
    p_new.add_argument("name", help="Project directory name")
    p_new.add_argument("--directory", "-C", help="Parent directory (default: cwd)")
    p_new.set_defaults(func=cmd_new)

    p_dev = sub.add_parser("dev", help="Run dev server")
    p_dev.add_argument("--app", help="WSGI target in module:var format (default: app.main:app)")
    p_dev.add_argument("--host", default="127.0.0.1")
    p_dev.add_argument("--port", default="5000")
    p_dev.set_defaults(func=cmd_dev)

    p_db = sub.add_parser("db", help="Database helpers")
    p_db_sub = p_db.add_subparsers(dest="action", required=True)
    p_db_apply = p_db_sub.add_parser("apply", help="Apply SQL schema script")
    p_db_apply.add_argument("--db", help="SQLite DB path (default: ./db/app.db)")
    p_db_apply.add_argument("--schema", help="Schema SQL file (default: db/schema.sql)")
    p_db_apply.set_defaults(func=cmd_db)

    p_deploy = sub.add_parser("deploy", help="Deployment helpers (placeholder)")
    p_deploy.set_defaults(func=cmd_deploy)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
