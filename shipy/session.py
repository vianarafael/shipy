# shipy/session.py
from __future__ import annotations
import json, hmac, hashlib, base64, os

SECRET = os.getenv("SHIPY_SECRET", "dev-secret-change-me").encode()
COOKIE_NAME = "shipy"

def _sign(b: bytes) -> bytes:
    return hmac.new(SECRET, b, hashlib.sha256).digest()

def _pack(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    sig = _sign(raw)
    return base64.urlsafe_b64encode(raw + sig).decode()

def _unpack(token: str) -> dict | None:
    if not token:
        return None
    try:
        blob = base64.urlsafe_b64decode(token.encode())
        raw, sig = blob[:-32], blob[-32:]
        if hmac.compare_digest(sig, _sign(raw)):
            return json.loads(raw.decode())
    except Exception:
        pass
    return None

def get_session(req) -> dict:
    """Read & verify the signed cookie from the request; return {} if missing/bad."""
    return _unpack(req.cookies.get(COOKIE_NAME, "")) or {}

def set_session(resp, data: dict):
    """Write session data into a signed cookie on the response."""
    resp.set_cookie(COOKIE_NAME, _pack(data), http_only=True, samesite="Lax")

def clear_session(resp):
    """Clear the session cookie."""
    resp.delete_cookie(COOKIE_NAME)
