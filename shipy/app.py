# shipy/app.py
import re, inspect, os, mimetypes, traceback, html
from urllib.parse import parse_qs
from http import cookies as http_cookies
from pathlib import Path

# CSRF needs the session cookie; session.py must NOT import from app.py (no cycles).
from .session import get_session

# ---- Config & paths ---------------------------------------------------------
def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")

DEBUG = _env_bool("SHIPY_DEBUG", True)  # dev default True; set SHIPY_DEBUG=0 in prod

_BASE = Path(os.getenv("SHIPY_BASE", Path.cwd()))
PUBLIC_DIR = Path(os.getenv("SHIPY_PUBLIC", _BASE / "public")).resolve()

# Where to look for error templates
_ERROR_DIRS = [
    (_BASE / "app" / "views" / "errors").resolve(),
    (_BASE / "views" / "errors").resolve(),
]

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


# ---- Helpers ----------------------------------------------------------------
def _read_error_template(name: str) -> str | None:
    """Return the error HTML if found (e.g., '404.html' in views/errors/)."""
    for d in _ERROR_DIRS:
        f = d / f"{name}.html"
        if f.is_file():
            try:
                return f.read_text(encoding="utf-8")
            except Exception:
                pass
    return None


async def _serve_static(scope, receive, send):
    """Tiny dev-time static server for /public/*."""
    path = scope["path"]
    method = scope["method"].upper()

    if not path.startswith("/public/"):
        return await Response.text("Not Found", 404)(scope, receive, send)

    rel = path[len("/public/"):]
    root = PUBLIC_DIR
    file = (root / rel).resolve()

    # prevent traversal and 404 if missing
    if not str(file).startswith(str(root)) or not file.is_file():
        return await Response.text("Not Found", 404)(scope, receive, send)

    data = file.read_bytes()
    ctype = mimetypes.guess_type(str(file))[0] or "application/octet-stream"
    resp = Response(data, 200, headers=[(b"content-type", ctype.encode())])
    if method == "HEAD":
        resp.body = b""
    return await resp(scope, receive, send)


def _pretty_tb_html(exc: BaseException) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    esc = html.escape(tb)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>500 Internal Server Error</title>
<style>
body{{font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:24px;background:#0b0b0b;color:#f6f6f6}}
pre{{background:#111;color:#f6f6f6;padding:16px;border-radius:12px;overflow:auto}}
h1{{margin-top:0}}
a{{color:#60a5fa}}
</style>
</head><body>
<h1>500 Internal Server Error</h1>
<p>DEBUG is on (SHIPY_DEBUG=1). Here’s the traceback:</p>
<pre>{esc}</pre>
</body></html>"""


# ---- Core -------------------------------------------------------------------
class App:
    def __init__(self):
        self.routes = []  # list of (method, compiled_regex, handler)

    def _compile_path(self, path: str) -> re.Pattern:
        # {id:int}  -> (?P<id>\d+)
        def repl_int(m): return f"(?P<{m.group(1)}>\\d+)"
        # {slug}    -> (?P<slug>[^/]+)
        def repl_str(m): return f"(?P<{m.group(1)}>[^/]+)"
        path = re.sub(r"{(\w+):int}", repl_int, path)
        path = re.sub(r"{(\w+)}", repl_str, path)
        return re.compile("^" + path + "$")

    def add(self, method, path, handler):
        self.routes.append((method.upper(), self._compile_path(path), handler))

    def get(self, path, handler):   self.add("GET",  path, handler)
    def post(self, path, handler):  self.add("POST", path, handler)
    # (add put/patch/delete helpers later if needed)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return

        method = scope["method"].upper()
        path   = scope["path"]

        # Health check (always 200 ok)
        if path == "/health":
            body = b"ok" if method != "HEAD" else b""
            return await Response(body, 200, headers=[(b"content-type", b"text/plain; charset=utf-8")])(scope, receive, send)

        # Dev static under /public/
        if path.startswith("/public/") and method in ("GET", "HEAD"):
            return await _serve_static(scope, receive, send)

        # Route matching + method handling (405 + HEAD shim)
        allowed: set[str] = set()
        chosen = None          # (handler, params, head_shim: bool)
        for m, rx, handler in self.routes:
            mobj = rx.match(path)
            if not mobj:
                continue
            allowed.add(m)
            if m == method:
                chosen = (handler, mobj.groupdict(), False)
                break
            # HEAD shim: if method is HEAD and route defines GET
            if method == "HEAD" and m == "GET" and chosen is None:
                chosen = (handler, mobj.groupdict(), True)

        if chosen:
            handler, params, head_shim = chosen
            req = Request(scope, receive, params)

            # Global CSRF guard for unsafe methods (form posts)
            if method in UNSAFE_METHODS:
                await req.load_body()
                s = get_session(req) or {}
                sent = req.form.get("csrf")
                if not sent or sent != s.get("csrf"):
                    return await Response.text("Forbidden (CSRF)", 403)(scope, receive, send)

            # Call handler with error handling
            try:
                result = handler(req)
                if inspect.isawaitable(result):
                    result = await result
            except Exception as exc:
                if DEBUG:
                    html_page = _pretty_tb_html(exc)
                    return await Response.html(html_page, 500)(scope, receive, send)
                tpl = _read_error_template("500")
                return await (Response.html(tpl, 500) if tpl else Response.text("Internal Server Error", 500))(scope, receive, send)

            if not isinstance(result, Response):
                result = Response.html(str(result))
            if head_shim:
                result.body = b""
            return await result(scope, receive, send)

        # If we matched the path but not the method → 405 with Allow
        if allowed:
            allow = set(allowed)
            if "GET" in allow:
                allow.add("HEAD")  # advertise HEAD when GET exists
            allow_hdr = ", ".join(sorted(allow))
            return await Response.text("Method Not Allowed", 405)(
                {**scope, "headers": scope.get("headers", [])},  # pass-through
                receive,
                lambda msg: send({**msg, "headers": (msg.get("headers") or []) + [(b"allow", allow_hdr.encode())]})
            )

        # No route matched → 404 page
        tpl = _read_error_template("404")
        return await (Response.html(tpl, 404) if tpl else Response.text("Not Found", 404))(scope, receive, send)


class Response:
    def __init__(self, body=b"", status=200, headers=None, content_type="text/html; charset=utf-8"):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = headers or [(b"content-type", content_type.encode())]
        self._cookies = http_cookies.SimpleCookie()

    def set_cookie(self, name, value, *, http_only=True, samesite="Lax", path="/", max_age=None, secure=False):
        # In prod, default to Secure cookies unless caller explicitly wants otherwise
        if not DEBUG:
            secure = True
        self._cookies[name] = value
        morsel = self._cookies[name]
        morsel["path"] = path
        morsel["samesite"] = samesite
        if http_only: morsel["httponly"] = True
        if secure: morsel["secure"] = True
        if max_age is not None: morsel["max-age"] = str(max_age)

    def delete_cookie(self, name, path="/"):
        self.set_cookie(name, "", max_age=0, path=path)

    async def __call__(self, scope, receive, send):
        # Default security headers in prod (add if missing)
        if not DEBUG:
            have = {k.lower(): True for (k, _) in ((h[0].decode(), h[1]) for h in self.headers)}
            sec = []
            if "x-content-type-options" not in have:
                sec.append((b"x-content-type-options", b"nosniff"))
            if "referrer-policy" not in have:
                sec.append((b"referrer-policy", b"no-referrer"))
            if "x-frame-options" not in have:
                sec.append((b"x-frame-options", b"DENY"))
            self.headers = list(self.headers) + sec

        headers = list(self.headers)
        for morsel in self._cookies.values():
            headers.append((b"set-cookie", morsel.OutputString().encode()))
        await send({"type": "http.response.start", "status": self.status, "headers": headers})
        await send({"type": "http.response.body", "body": self.body})

    @classmethod
    def html(cls, text, status=200):       return cls(text, status)
    @classmethod
    def text(cls, text, status=200):       return cls(text, status, content_type="text/plain; charset=utf-8")
    @classmethod
    def redirect(cls, location, status=303):
        return cls(b"", status, headers=[(b"location", location.encode())])


class Request:
    def __init__(self, scope, receive, path_params):
        self.scope = scope
        self._receive = receive
        self.method = scope["method"]
        self.path = scope["path"]
        self.query = {
            k: (v[0] if len(v) == 1 else v)
            for k, v in parse_qs(scope.get("query_string", b"").decode()).items()
        }
        self.path_params = path_params
        self._body = None
        self.form = {}
        self.cookies = {}
        for k, v in scope.get("headers", []):
            if k.lower() == b"cookie":
                jar = http_cookies.SimpleCookie()
                jar.load(v.decode())
                self.cookies = {n: morsel.value for n, morsel in jar.items()}
                break

    async def load_body(self):
        if self._body is not None:
            return
        chunks = []
        while True:
            event = await self._receive()
            if event["type"] == "http.request":
                if event.get("body"):
                    chunks.append(event["body"])
                if not event.get("more_body"):
                    break
        self._body = b"".join(chunks)
        headers = {k.decode(): v.decode() for k, v in self.scope.get("headers", [])}
        ctype = headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype:
            self.form = {
                k: (v[0] if len(v) == 1 else v)
                for k, v in parse_qs(self._body.decode()).items()
            }
