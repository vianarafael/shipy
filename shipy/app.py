# shipy/app.py
import re, inspect
from urllib.parse import parse_qs

class App:
    def __init__(self):
        self.routes = []

    def _compile_path(self, path: str) -> re.Pattern:
        # {id:int}  -> (?P<id>\d+)
        def repl_int(m):   return f"(?P<{m.group(1)}>\\d+)"
        # {slug}    -> (?P<slug>[^/]+)
        def repl_str(m):   return f"(?P<{m.group(1)}>[^/]+)"
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
        method = scope["method"].upper()
        path   = scope["path"]

        for m, rx, handler in self.routes:
            if m != method:
                continue
            mobj = rx.match(path)
            if not mobj:
                continue

            # Build Request
            req = Request(scope, receive, mobj.groupdict())

            # Call handler (sync or async)
            result = handler(req)
            if inspect.isawaitable(result):
                result = await result

            # Ensure it's a Response
            if not isinstance(result, Response):
                result = Response.html(str(result))

            return await result(scope, receive, send)

        return await Response.text("Not Found", 404)(scope, receive, send)


class Response:
    def __init__(self, body=b"", status=200, headers=None, content_type="text/html; charset=utf-8"):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = headers or [(b"content-type", content_type.encode())]
    async def __call__(self, scope, receive, send):
        await send({"type": "http.response.start", "status": self.status, "headers": self.headers})
        await send({"type": "http.response.body", "body": self.body})
    @classmethod
    def html(cls, text, status=200):     return cls(text, status)
    @classmethod
    def text(cls, text, status=200):     return cls(text, status, content_type="text/plain; charset=utf-8")
    @classmethod
    def redirect(cls, location, status=303): return cls(b"", status, headers=[(b"location", location.encode())])


class Request:
    def __init__(self, scope, receive, path_params):
        self.scope = scope
        self._receive = receive
        self.method = scope["method"]
        self.path = scope["path"]
        self.query = {k: (v[0] if len(v) == 1 else v)
                      for k, v in parse_qs(scope.get("query_string", b"").decode()).items()}
        self.path_params = path_params
        self._body = None
        self.form = {}

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
            self.form = {k: (v[0] if len(v) == 1 else v)
                         for k, v in parse_qs(self._body.decode()).items()}
