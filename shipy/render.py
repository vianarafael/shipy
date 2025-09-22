# from __future__ import annotations

# import os
# from typing import Any, Dict, Optional

# _ENV = None


# def _load_jinja2():
#     try:
#         from jinja2 import Environment, FileSystemLoader, select_autoescape
#     except Exception as exc:  # pragma: no cover - import-time guard
#         raise RuntimeError(
#             "Jinja2 is required for template rendering. Install with: pip install jinja2"
#         ) from exc
#     return Environment, FileSystemLoader, select_autoescape


# def get_env(views_dir: Optional[str] = None):
#     global _ENV
#     if _ENV is not None:
#         return _ENV
#     Environment, FileSystemLoader, select_autoescape = _load_jinja2()
#     # default to app/views under current working directory
#     base = views_dir or os.path.join(os.getcwd(), "app", "views")
#     loader = FileSystemLoader([base])
#     env = Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))

#     # Common helpful filters/globals can be added here
#     env.globals["shipy_version"] = lambda: __import__("shipy").__version__
#     _ENV = env
#     return env


# def render(template_name: str, context: Optional[Dict[str, Any]] = None, *, request=None, views_dir: Optional[str] = None) -> str:
#     env = get_env(views_dir)
#     ctx: Dict[str, Any] = {}
#     if context:
#         ctx.update(context)
#     if request is not None:
#         # Surface session and flash utilities into templates if present
#         sess = getattr(request, "session", None)
#         if sess is not None:
#             ctx.setdefault("session", sess)
#             try:
#                 ctx.setdefault("get_flashed_messages", sess.get_flashed_messages)
#                 ctx.setdefault("csrf_token", sess.get_csrf_token())
#             except Exception:
#                 pass
#     tmpl = env.get_template(template_name)
#     return tmpl.render(**ctx)

from jinja2 import Environment, FileSystemLoader, select_autoescape 
import os 

class Renderer:
    def __init__(self, views_path="views"):
        self.env = Environment(
            loader=FileSystemLoader(views_path),
            autoescape=select_autoescape(["html", "xml"]),
            enable_async=False,
        )
    
    def render(self, template, **ctx):
        tpl = self.env.get_template(template)
        return tpl.render(**ctx)
    
_renderer = None 
def render(template, **ctx):
    global _renderer
    if _renderer is None:
        # auto-discover views / relative to CWD
        views = os.path.join(os.getcwd(), "app", "views")
        _renderer = Renderer(views)
    
    from .app import Response
    return Response.html(_renderer.render(template, **ctx))

