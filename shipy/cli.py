# shipy/cli.py
from __future__ import annotations

import argparse
import datetime
import os
import secrets
import sqlite3
from pathlib import Path
from textwrap import dedent
from typing import Optional

from shipy.sql import connect as sql_connect  # reuse PRAGMAs/row_factory


# ---------- DB ----------------------------------------------------------------

def cmd_db_init(db_path: str = "data/app.db", schema_path: str = "data/schema.sql") -> int:
    db = Path(db_path)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sql_connect(str(db))
    schema = Path(schema_path)
    if schema.exists():
        con.executescript(schema.read_text(encoding="utf-8"))
        print(f"✅ DB initialized at {db} (schema: {schema})")
    else:
        print(f"✅ DB created at {db} (no schema.sql found)")
    return 0


def cmd_db_backup(db_path: str = "data/app.db", out_dir: str = "data/backups") -> int:
    srcp = Path(db_path)
    if not srcp.exists():
        print(f"DB not found: {srcp}")
        return 2
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = out / f"{srcp.stem}-{ts}.sqlite"
    src = sqlite3.connect(str(srcp))
    dst = sqlite3.connect(str(dest))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    print(f"📦 Backup written: {dest}")
    return 0


# ---------- DEV ----------------------------------------------------------------

def cmd_dev(app_ref: str, host: str, port: int, reload: bool, workers: int, show_info: bool = True) -> int:
    # Ensure the current working directory is importable as top-level (so 'app.*' resolves)
    import sys
    import uvicorn  # type: ignore

    cwd = os.getcwd()
    os.environ.setdefault("SHIPY_BASE", cwd)

    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Ensure the reload subprocess inherits the path too
    os.environ["PYTHONPATH"] = cwd + os.pathsep + os.environ.get("PYTHONPATH", "")

    if show_info:
        print(f"🚀 Shipy dev server starting...")
        print(f"📁 Working directory: {cwd}")
        print(f"🗄️  Database: data/app.db")
        print(f"📋 Schema: data/schema.sql")
        print(f"🌐 URL: http://{host}:{port}")
        print("Press Ctrl+C to stop\n")

    config = uvicorn.Config(
        app_ref,
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        reload_dirs=[cwd],
    )
    server = uvicorn.Server(config)
    return 0 if server.run() else 1


# ---------- NEW ----------------------------------------------------------------

def _write_file(path: Path, content: str, *, force: bool):
    if path.exists() and not force:
        print(f"• skip {path} (exists)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip(), encoding="utf-8")
    print(f"✓ write {path}")


def cmd_new(name: str, *, force: bool = False) -> int:
    root = Path(name).resolve()
    app = root / "app"
    views = app / "views"
    public = root / "public"
    dbdir = root / "data"

    files: dict[Path, str] = {
        root / ".gitignore": """
            __pycache__/
            *.pyc
            .env
            data/*.db*
            .DS_Store
        """,
        # Make 'app' a real package so 'app.main:app' imports everywhere
        app / "__init__.py": "",
        public / "base.css": """
            :root { --bg:#0b0b0b; --fg:#f6f6f6; --muted:#b7b7b7; --card:#151515; --acc:#60a5fa; }
            *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
            .wrap{max-width:720px;margin:40px auto;padding:0 16px}
            a{color:var(--acc);text-decoration:none}
            header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
            .card{background:var(--card);padding:16px;border-radius:12px;margin:12px 0}
            .stack>*+*{margin-top:10px}
            .input, textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #333;background:#111;color:var(--fg)}
            .btn{display:inline-block;border:0;border-radius:10px;padding:10px 14px;background:#2563eb;color:#fff;cursor:pointer}
            .err{color:#f87171;font-size:14px}
            .flash{padding:8px 12px;border-radius:10px;background:#0f172a;color:#e2e8f0}
            nav a{margin-right:10px}
        """,
        app / "main.py": """
            from shipy.app import App, Response
            from shipy.render import render_req
            from shipy.sql import connect, query, one, exec, tx
            from shipy.forms import Form
            from shipy.auth import (
                current_user, require_login,
                hash_password, check_password,
                login, logout,
                too_many_login_attempts, record_login_failure, reset_login_failures
            )

            app = App()
            connect("data/app.db")

            def home(req):
                user = current_user(req)
                return render_req(req, "home/index.html", user=user)

            def signup_form(req): return render_req(req, "users/new.html")

            async def signup(req):
                await req.load_body()
                form = Form(req.form).require("email","password").min("password", 6).email("email")
                if not form.ok: return render_req(req, "users/new.html", form=form)
                if one("SELECT id FROM users WHERE email=?", form["email"]):
                    form.errors.setdefault("email", []).append("already registered")
                    return render_req(req, "users/new.html", form=form)
                with tx():
                    exec("INSERT INTO users(email,password_hash) VALUES(?,?)",
                         form["email"], hash_password(form['password']))
                    u = one("SELECT id,email FROM users WHERE email=?", form["email"])
                resp = Response.redirect("/")
                login(req, resp, u["id"])
                return resp

            def login_form(req): return render_req(req, "sessions/login.html")

            async def login_post(req):
                await req.load_body()
                form = Form(req.form).require("email","password").email("email")
                ip = req.scope.get("client", ("",0))[0] or "unknown"
                if too_many_login_attempts(ip):
                    form.errors.setdefault("email", []).append("too many attempts, try later")
                    return render_req(req, "sessions/login.html", form=form)
                u = one("SELECT id,email,password_hash FROM users WHERE email=?", form["email"])
                if not u or not check_password(form["password"], u["password_hash"]):
                    record_login_failure(ip)
                    form.errors.setdefault("email", []).append("invalid email or password")
                    return render_req(req, "sessions/login.html", form=form)
                reset_login_failures(ip)
                resp = Response.redirect("/")
                login(req, resp, u["id"])
                return resp

            async def logout_post(req):
                resp = Response.redirect("/")
                logout(resp)
                return resp


            def secret(req):
                user = require_login(req)
                if not user: return Response.redirect("/login")
                return render_req(req, "secret.html", user=user)

            app.get("/", home)
            app.get("/signup", signup_form)
            app.post("/signup", signup)
            app.get("/login", login_form)
            app.post("/login", login_post)
            app.post("/logout", logout_post)
            app.get("/secret", secret)
        """,
        views / "home" / "index.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap">
              <header>
                <strong>Shipy</strong>
                <nav>
                  {% if user %}
                    <span>{{ user.email }}</span>
                    <form method="post" action="/logout" style="display:inline">
                      <input type="hidden" name="csrf" value="{{ csrf }}"><button class="btn">Logout</button>
                    </form>
                  {% else %}
                    <a href="/login">Login</a> <a href="/signup">Sign up</a>
                  {% endif %}
                </nav>
              </header>

              {% if flashes %}{% for f in flashes %}<div class="flash">{{ f.msg }}</div>{% endfor %}{% endif %}

              <div class="card">
                <h2>Posts</h2>
                <div class="stack">
                  {% for p in posts %}
                    <div class="card"><strong>#{{ p.id }}</strong> — {{ p.title }}</div>
                  {% else %}
                    <div class="muted">No posts yet.</div>
                  {% endfor %}
                </div>
              </div>

              {% if user %}
              <div class="card">
                <h3>New post</h3>
                <form method="post" action="/posts" class="stack">
                  <input class="input" name="title" placeholder="Title" value="{{ form['title'] if form else '' }}">
                  {% if form %}{% for e in form.errors_for('title') %}<div class="err">title: {{ e }}</div>{% endfor %}{% endif %}
                  <textarea class="input" name="body" placeholder="Body">{{ form['body'] if form else '' }}</textarea>
                  {% if form %}{% for e in form.errors_for('body') %}<div class="err">body: {{ e }}</div>{% endfor %}{% endif %}
                  <input type="hidden" name="csrf" value="{{ csrf }}">
                  <button class="btn">Create</button>
                </form>
              </div>
              {% else %}
                <div class="card">Log in to create posts.</div>
              {% endif %}
            </div>
        """,
        views / "sessions" / "login.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap">
              <h1>Log in</h1>
              <form method="post" action="/login" class="stack">
                <label>Email <input class="input" name="email" value="{{ form['email'] if form else '' }}"></label>
                {% if form %}{% for e in form.errors_for('email') %}<div class="err">email: {{ e }}</div>{% endfor %}{% endif %}
                <label>Password <input class="input" type="password" name="password"></label>
                {% if form %}{% for e in form.errors_for('password') %}<div class="err">password: {{ e }}</div>{% endfor %}{% endif %}
                <input type="hidden" name="csrf" value="{{ csrf }}">
                <button class="btn">Log in</button>
              </form>
              <p>No account? <a href="/signup">Sign up</a></p>
            </div>
        """,
        views / "users" / "new.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap">
              <h1>Sign up</h1>
              <form method="post" action="/signup" class="stack">
                <label>Email <input class="input" name="email" value="{{ form['email'] if form else '' }}"></label>
                {% if form %}{% for e in form.errors_for('email') %}<div class="err">email: {{ e }}</div>{% endfor %}{% endif %}
                <label>Password (min 6) <input class="input" type="password" name="password"></label>
                {% if form %}{% for e in form.errors_for('password') %}<div class="err">password: {{ e }}</div>{% endfor %}{% endif %}
                <input type="hidden" name="csrf" value="{{ csrf }}">
                <button class="btn">Create account</button>
              </form>
              <p>Have an account? <a href="/login">Log in</a></p>
            </div>
        """,
        views / "secret.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap"><h1>Secret</h1><p>Hello {{ user.email }}!</p></div>
        """,
        views / "errors" / "404.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap"><h1>404</h1><p>Page not found.</p></div>
        """,
        views / "errors" / "500.html": """
            <!doctype html><meta charset="utf-8"><link rel="stylesheet" href="/public/base.css">
            <div class="wrap"><h1>Something went wrong</h1><p>Please try again.</p></div>
        """,
        dbdir / "schema.sql": """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """,
    }
    for path, content in files.items():
        _write_file(path, content, force=force)

    print("\nNext steps:")
    print(f"  cd {root}")
    print("  shipy db init")
    print("  shipy dev --app app.main:app")
    return 0


# ---------- DEPLOY ------------------------------------------------------------

def cmd_deploy_emit(path: str, service: str, domain: str, port: int, user: str, workdir: str) -> int:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    workdir = str(Path(workdir).resolve())
    public = str((Path(workdir) / "public").resolve())

    service_file = out / f"{service}.service"
    nginx_file = out / f"{domain}.conf"

    _write_file(service_file, f"""
        [Unit]
        Description=Shipy app {service}
        After=network.target

        [Service]
        Type=simple
        WorkingDirectory={workdir}
        Environment=SHIPY_BASE={workdir}
        Environment=SHIPY_DEBUG=0
        # Replace this with: shipy gensecret
        Environment=SHIPY_SECRET=CHANGE_ME
        ExecStart=/usr/bin/env uvicorn app.main:app --host 127.0.0.1 --port {port} --workers 2
        Restart=always
        User={user}
        Group={user}

        [Install]
        WantedBy=multi-user.target
    """, force=True)

    _write_file(nginx_file, f"""
        server {{
          listen 80;
          server_name {domain};

          root {public};

          location /public/ {{
            try_files $uri =404;
            add_header Cache-Control "public, max-age=31536000, immutable";
          }}

          location / {{
            proxy_pass http://127.0.0.1:{port};
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
          }}
        }}
    """, force=True)

    print(f"\nDeploy files written to: {out}")
    print(f"  • systemd: {service_file.name}")
    print(f"  • nginx  : {nginx_file.name}")
    print("\nServer steps (Ubuntu):")
    print("  sudo cp deploy/*.service /etc/systemd/system/")
    print(f"  sudo systemctl enable --now {service}.service")
    print(f"  sudo cp deploy/{domain}.conf /etc/nginx/sites-available/")
    print(f"  sudo ln -sf /etc/nginx/sites-available/{domain}.conf /etc/nginx/sites-enabled/{domain}.conf")
    print("  sudo nginx -t && sudo systemctl reload nginx")
    print("  curl -s http://YOUR_DOMAIN/health")
    return 0


def cmd_gensecret() -> int:
    print(secrets.token_urlsafe(32))
    return 0


# ---------- MAIN --------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="shipy", description="Shipy CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="Create a new Shipy app skeleton")
    p_new.add_argument("name", help="Directory name (or path)")
    p_new.add_argument("--force", action="store_true", help="Overwrite existing files")

    p_dev = sub.add_parser("dev", help="Run dev server")
    p_dev.add_argument("--app", default="app.main:app", help="ASGI app path, e.g. app.main:app")
    p_dev.add_argument("--host", default="127.0.0.1")
    p_dev.add_argument("--port", type=int, default=8000)
    p_dev.add_argument("--reload", action="store_true", default=True)
    p_dev.add_argument("--no-reload", dest="reload", action="store_false")
    p_dev.add_argument("--workers", type=int, default=1)
    p_dev.add_argument("--show-info", action="store_true", default=True, help="Show boot info")

    p_db = sub.add_parser("db", help="Database utilities")
    p_db_sub = p_db.add_subparsers(dest="db_cmd", required=True)
    p_db_init = p_db_sub.add_parser("init", help="Create SQLite and run schema.sql (if present)")
    p_db_init.add_argument("--db", default="data/app.db")
    p_db_init.add_argument("--schema", default="data/schema.sql")
    p_db_backup = p_db_sub.add_parser("backup", help="Online backup to db/backups/")
    p_db_backup.add_argument("--db", default="data/app.db")
    p_db_backup.add_argument("--out", default="data/backups")

    p_dep = sub.add_parser("deploy", help="Deployment helpers")
    p_dep_sub = p_dep.add_subparsers(dest="dep_cmd", required=True)
    p_emit = p_dep_sub.add_parser("emit", help="Write systemd + nginx files to ./deploy")
    p_emit.add_argument("--path", default="deploy")
    p_emit.add_argument("--service", default=Path(os.getcwd()).name + "-app")
    p_emit.add_argument("--domain", required=True, help="your-domain.com")
    p_emit.add_argument("--port", type=int, default=8000)
    p_emit.add_argument("--user", default="www-data")
    p_emit.add_argument("--workdir", default=os.getcwd())

    p_secret = sub.add_parser("gensecret", help="Generate a random SHIPY_SECRET")

    args = p.parse_args(argv)

    if args.cmd == "new":
        return cmd_new(args.name, force=args.force)
    if args.cmd == "dev":
        return cmd_dev(args.app, args.host, args.port, args.reload, args.workers, args.show_info)
    if args.cmd == "db" and args.db_cmd == "init":
        return cmd_db_init(args.db, args.schema)
    if args.cmd == "db" and args.db_cmd == "backup":
        return cmd_db_backup(args.db, args.out)
    if args.cmd == "deploy" and args.dep_cmd == "emit":
        return cmd_deploy_emit(args.path, args.service, args.domain, args.port, args.user, args.workdir)
    if args.cmd == "gensecret":
        return cmd_gensecret()

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
