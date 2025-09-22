from __future__ import annotations

import secrets
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional, Tuple


def _load_signer():
    try:
        from itsdangerous import BadSignature, URLSafeSerializer
    except Exception as exc:  # pragma: no cover - import-time guard
        raise RuntimeError(
            "itsdangerous is required for sessions. Install with: pip install itsdangerous"
        ) from exc
    return URLSafeSerializer, BadSignature


class Session(dict):
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(initial or {})
        self.changed = False

    # mutation hooks
    def __setitem__(self, key, value):  # type: ignore[override]
        self.changed = True
        return super().__setitem__(key, value)

    def __delitem__(self, key):  # type: ignore[override]
        self.changed = True
        return super().__delitem__(key)

    def clear(self) -> None:  # type: ignore[override]
        self.changed = True
        return super().clear()

    def pop(self, k, d=None):  # type: ignore[override]
        self.changed = True
        return super().pop(k, d)

    # flash messages
    def flash(self, message: str, category: str = "info") -> None:
        flashes: List[Tuple[str, str]] = self.get("_flashes", [])  # type: ignore[assignment]
        flashes.append((category, message))
        self["_flashes"] = flashes

    def get_flashed_messages(self, with_categories: bool = False, clear: bool = True):
        flashes: List[Tuple[str, str]] = self.get("_flashes", [])  # type: ignore[assignment]
        if clear and flashes:
            self.pop("_flashes", None)
        if with_categories:
            return list(flashes)
        return [m for (_c, m) in flashes]

    # CSRF
    def get_csrf_token(self) -> str:
        token = self.get("_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            self["_csrf"] = token
        return token

    def validate_csrf(self, value: Optional[str]) -> bool:
        expected = self.get("_csrf")
        return bool(expected) and bool(value) and secrets.compare_digest(str(expected), str(value))


class SessionManager:
    def __init__(
        self,
        secret: str,
        *,
        cookie_name: str = "shipy_session",
        samesite: str = "Lax",
        secure: Optional[bool] = None,
    ) -> None:
        URLSafeSerializer, BadSignature = _load_signer()
        self.serializer = URLSafeSerializer(secret_key=secret, salt="shipy-session-v1")
        self.BadSignature = BadSignature
        self.cookie_name = cookie_name
        self.samesite = samesite
        self.secure_default = secure

    def _load_from_cookie(self, cookie_header: str) -> Session:
        c = SimpleCookie()
        c.load(cookie_header or "")
        morsel = c.get(self.cookie_name)
        if not morsel:
            return Session()
        data = morsel.value
        try:
            obj = self.serializer.loads(data)
        except self.BadSignature:
            return Session()  # invalid signature: start fresh
        if not isinstance(obj, dict):
            return Session()
        return Session(obj)

    def load_from_environ(self, environ: Dict[str, Any]) -> Session:
        cookie_header = environ.get("HTTP_COOKIE", "")
        return self._load_from_cookie(cookie_header)

    def save_to_response(self, environ: Dict[str, Any], response, session: Session) -> None:
        # only set cookie when changed
        if not isinstance(session, Session) or not session.changed:
            return
        value = self.serializer.dumps(dict(session))
        scheme = environ.get("wsgi.url_scheme", "http")
        secure = self.secure_default if self.secure_default is not None else (scheme == "https")
        response.set_cookie(
            self.cookie_name,
            value,
            httponly=True,
            samesite=self.samesite,
            secure=secure,
            path="/",
        )

