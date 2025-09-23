# shipy/auth.py
from __future__ import annotations
import os, time, secrets, hashlib, hmac, binascii
from typing import Optional

from .session import get_session, set_session, clear_session
from .sql import one, exec as sql_exec, tx

# --- Password hashing ---------------------------------------------------------
# Optional bcrypt; falls back to PBKDF2-HMAC if not installed.
try:
    import bcrypt  # type: ignore
    _HAS_BCRYPT = True
except Exception:
    _HAS_BCRYPT = False

def hash_password(password: str) -> str:
    pw = password.encode()
    if _HAS_BCRYPT:
        return "bcrypt$" + bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    # PBKDF2-HMAC-SHA256 with 200k iters
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw, salt, 200_000)
    return "pbkdf2$200000$" + binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()

def check_password(password: str, stored: str) -> bool:
    if stored.startswith("bcrypt$"):
        if not _HAS_BCRYPT: return False
        return bcrypt.checkpw(password.encode(), stored[len("bcrypt$"):].encode())
    if stored.startswith("pbkdf2$"):
        _, iters_s, salt_hex, hash_hex = stored.split("$", 3)
        iters = int(iters_s)
        salt = binascii.unhexlify(salt_hex)
        want = binascii.unhexlify(hash_hex)
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
        return hmac.compare_digest(got, want)
    return False

# --- Current user / session helpers -------------------------------------------
def current_user(req) -> Optional[dict]:
    s = get_session(req)
    if not s or "uid" not in s: return None
    return one("SELECT id, email, created_at FROM users WHERE id=?", s["uid"])

def login(req, resp, user_id: int):
    s = get_session(req) or {}
    s["uid"] = int(user_id)
    s["sv"] = 1  # session version; bump to force logout all
    set_session(resp, s)

def logout(resp):
    clear_session(resp)

def require_login(req):
    """Return user dict or None. Handlers can branch or redirect."""
    return current_user(req)

# --- Simple rate limit for login attempts -------------------------------------
# 5 failures per 5 minutes per IP.
def too_many_login_attempts(ip: str, window_sec=300, limit=5) -> bool:
    now = int(time.time())
    with tx():
        sql_exec("""CREATE TABLE IF NOT EXISTS login_attempts(
            ip TEXT, ts INTEGER
        )""")
        sql_exec("DELETE FROM login_attempts WHERE ts < ?", now - window_sec)
        row = one("SELECT COUNT(*) AS c FROM login_attempts WHERE ip=? AND ts>=?", ip, now - window_sec)
    return (row["c"] if row else 0) >= limit

def record_login_failure(ip: str):
    now = int(time.time())
    with tx():
        sql_exec("INSERT INTO login_attempts(ip, ts) VALUES(?,?)", ip, now)

def reset_login_failures(ip: str):
    with tx():
        sql_exec("DELETE FROM login_attempts WHERE ip=?", ip)
