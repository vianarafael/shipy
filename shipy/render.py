from __future__ import annotations
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .app import Response
from .csrf import ensure_token
from .flash import pull

_jinja_env = None
_views_path = None

def _resolve_views_path() -> Path:
    """Prefer ./app/views, then ./views. Allow override via SHIPY_VIEWS."""
    if os.getenv("SHIPY_VIEWS"):
        return Path(os.getenv("SHIPY_VIEWS")).resolve()
    base = Path(os.getenv("SHIPY_BASE", Path.cwd()))
    for candidate in (base / "app" / "views", base / "views"):
        if candidate.exists():
            return candidate.resolve()
    # default fallback even if missing (Jinja will error on missing template)
    return (base / "app" / "views").resolve()

def _env() -> Environment:
    global _jinja_env, _views_path
    if _jinja_env is None:
        _views_path = _resolve_views_path()
        _jinja_env = Environment(
            loader=FileSystemLoader(str(_views_path)),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=True,  # fine for dev; Jinja caches in prod anyway
            enable_async=False,
        )
    return _jinja_env

def render(template: str, **ctx) -> Response:
    """Plain render: does NOT touch session/cookies. Good for static pages."""
    html = _env().get_template(template).render(**ctx)
    return Response.html(html)

def render_req(req, template: str, **ctx) -> Response:
    """
    Render with request context:
    - Ensures a CSRF token exists (and sets it in a cookie-backed session)
    - Pulls flash messages (consumes them)
    Exposes `csrf` and `flashes` to the template.
    """
    resp = Response.html("")                 # we need a Response to set cookies
    csrf = ensure_token(req, resp)           # may update session cookie
    flashes = pull(req, resp)                # consumes flash from session
    html = _env().get_template(template).render(csrf=csrf, flashes=flashes, **ctx)
    resp.body = html.encode()
    return resp
