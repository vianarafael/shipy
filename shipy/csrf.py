import os, base64, hmac
from .session import get_session, set_session 
from .app import Response

def _nonce(n=16): return base64.urlsafe_b64encode(os.urandom(n)).decode().rstrip("=")

def ensure_token(req, resp: Response | None = None) -> str:
    s = get_session(req)
    tok = s.get("csrf")
    if not tok:
        tok = _nonce()
        if resp is None:
            # caller will see it later 
            s["csrf"] = tok 
        else:
            s["csrf"] = tok
            set_session(resp, s)
    return tok 

def verify(req):
    # ensure request.form is loaded before calling verify
    s = get_session(req)
    sent = req.form.get("csrf")
    print("req", req)
    good = bool(sent) and sent == s.get("csrf")
    if not good:
        from .app import Response
        return Response.text("Forbidden (CSRF)", 403)
    return None 

# <input type="hidden" name="csrf" value="{{ csrf }}">
