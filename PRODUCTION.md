# Shipy Production Checklist

## Environment

- `SHIPY_DEBUG=0`
- `SHIPY_SECRET=$(shipy gensecret)` — rotate periodically
- Optional: `SHIPY_PUBLIC=/srv/myapp/current/public`

## Systemd + Nginx

```bash
cd /srv/myapp/current
shipy deploy emit --domain yourdomain.com --port 8000 --user www-data --workdir /srv/myapp/current
sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl enable --now <your-folder-name>-app.service
sudo cp deploy/yourdomain.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/yourdomain.com.conf /etc/nginx/sites-enabled/yourdomain.com.conf
sudo nginx -t && sudo systemctl reload nginx
curl -s http://yourdomain.com/health
```

## Zero-Build Deploy

- Pull latest code: `git pull` (or `rsync` files)
- DB is SQLite on disk at `db/app.sqlite`
- Static under `public/` is served by Nginx

## Backups

- `shipy db backup` — writes to `db/backups/`

## Security

- Cookies are Secure + HttpOnly (prod)
- CSRF enforced globally for POST/PUT/PATCH/DELETE
- Default headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`

## Scale

- Increase `--workers` in systemd `ExecStart` if CPU allows
- Put a CDN in front if needed (static caching)

## Logs

- `journalctl -u <service> -f`

## Smoke Tests (8 quick checks)

```python
import os
from pathlib import Path
import pytest
import anyio
import httpx

from shipy.app import App, Response, DEBUG as APP_DEBUG
from shipy.session import set_session, get_session
from shipy.sql import connect, exec as sql_exec, one, tx

pytestmark = pytest.mark.anyio

def make_app(tmp_public: Path | None = None):
    # tiny app under test
    app = App()

    def home(req): return Response.html("ok")
    async def setup_csrf(req):
        # seed a session with csrf and return it
        resp = Response.text("seeded")
        s = get_session(req) or {}
        s["csrf"] = "TOK"
        set_session(resp, s)
        return resp

    async def post_echo(req):
        await req.load_body()
        return Response.text(f"posted:{req.form.get('a','')}")

    app.get("/", home)
    app.get("/setup", setup_csrf)
    app.post("/echo", post_echo)
    app.get("/onlyget", lambda req: Response.text("get"))
    app.get("/headme", lambda req: Response.text("body"))
    return app

async def client_for(app):
    return httpx.AsyncClient(app=app, base_url="http://test", follow_redirects=False)

async def test_health_and_404():
    app = make_app()
    async with httpx.AsyncClient(app=app, base_url="http://x") as c:
        r = await c.get("/health"); assert r.status_code == 200 and r.text == "ok"
        r = await c.get("/nope");   assert r.status_code == 404

async def test_405_and_allow():
    app = make_app()
    async with client_for(app) as c:
        r = await c.post("/onlyget")
        assert r.status_code == 405
        assert "GET" in r.headers.get("allow","")
        assert "HEAD" in r.headers.get("allow","")

async def test_head_shim():
    app = make_app()
    async with client_for(app) as c:
        r = await c.head("/headme")
        assert r.status_code == 200
        assert r.text == ""  # empty body for HEAD

async def test_csrf_blocks_without_token():
    app = make_app()
    async with client_for(app) as c:
        r = await c.post("/echo", data={"a":"1"})  # no csrf
        assert r.status_code == 403

async def test_csrf_allows_with_token_and_session_cookie():
    app = make_app()
    async with client_for(app) as c:
        # get a cookie with csrf=TOK
        r = await c.get("/setup")
        assert r.cookies
        # send matching token in form
        r = await c.post("/echo", data={"a":"1","csrf":"TOK"})
        assert r.status_code == 200 and r.text == "posted:1"

async def test_tx_rolls_back(tmp_path: Path):
    db = tmp_path / "app.sqlite"
    connect(str(db))
    sql_exec("CREATE TABLE t(id INTEGER PRIMARY KEY, n INT)")
    try:
        with tx():
            sql_exec("INSERT INTO t(n) VALUES(1)")
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    row = one("SELECT COUNT(*) AS c FROM t")
    assert row["c"] == 0

async def test_security_headers_in_prod(monkeypatch):
    # force prod
    monkeypatch.setenv("SHIPY_DEBUG", "0")
    from importlib import reload
    import shipy.app as appmod
    reload(appmod)  # apply env
    app = appmod.App()
    app.get("/", lambda req: appmod.Response.text("x"))
    async with httpx.AsyncClient(app=app, base_url="http://t") as c:
        r = await c.get("/")
        h = {k.lower(): v for k,v in r.headers.items()}
        assert "x-content-type-options" in h and h["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in h and h["x-frame-options"] == "DENY"
        assert "referrer-policy" in h and h["referrer-policy"] == "no-referrer"
    # restore debug for other tests
    monkeypatch.delenv("SHIPY_DEBUG", raising=False)
```

## Dev Dependencies

- Add to your `pyproject.toml`:

```toml
[project.optional-dependencies]
test = ["pytest>=8.0", "anyio>=4.0", "httpx>=0.27"]
```

- Run tests:

```bash
python -m pip install -e .[test]
pytest -q
```

## Release Checklist (v0.1)

### Docs

- README quickstart uses `shipy new`
- PRODUCTION.md as above

### Version & Tag

- Bump version in `pyproject.toml` to `0.1.0` (if not already)

```bash
git commit -am "docs: add PRODUCTION.md + smoke tests"
git tag v0.1.0
```

### Publish

```bash
python -m pip install build twine
python -m build
twine upload dist/*  # or to TestPyPI first
```

### Sanity

```bash
pipx run pip install -U shipy
shipy new try && cd try && shipy db init && shipy dev --app app.main:app
```

### One-Liner Commits

```text
docs: add PRODUCTION.md
test: add 8 smoke tests
chore: bump to 0.1.0 and tag
```
