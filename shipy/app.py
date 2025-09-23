# shipy/app.py
import re, inspect, os, mimetypes
from urllib.parse import parse_qs
from http import cookies as http_cookies
from pathlib import Path

# Base/public resolution:
# - If SHIPY_PUBLIC is set, use it as the full path to the public directory.
# - Else, use SHIPY_BASE/public (or CWD/public).
_BASE = Path(os.getenv("SHIPY_BASE", Path.cwd()))
PUBLIC_DIR = Path(os.getenv("SHIPY_PUBLIC", _BASE / "public")).resolve()


async def _serve_static(scope, receive, send):
    """Very small dev-time static file server for /public/*."""
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

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return

        # define BEFORE using
        method = scope["method"].upper()
        path   = scope["path"]

        # Dev static files under /public/
        if path.startswith("/public/") and method in ("GET", "HEAD"):
            return await _serve_static(scope, receive, send)

        # Route matching (imperative registration)
        for m, rx, handler in self.routes:
            if m != method:
                continue
            mobj = rx.match(path)
            if not mobj:
                continue

            req = Request(scope, receive, mobj.groupdict())
            result = handler(req)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, Response):
                result = Response.html(str(result))
            return await result(scope, receive, send)

        return await Response.text("Not Found", 404)(scope, receive, send)


class Response:
    def __init__(self, body=b"", status=200, headers=None, content_type="text/html; charset=utf-8"):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = headers or [(b"content-type", content_type.encode())]
        self._cookies = http_cookies.SimpleCookie()

    def set_cookie(self, name, value, *, http_only=True, samesite="Lax", path="/", max_age=None, secure=False):
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
