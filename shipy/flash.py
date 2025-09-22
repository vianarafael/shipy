from .session import get_session, set_session 

def add(req, resp, message, kind="info"):
    s = get_session(req)
    s.setdefault("_flash", []).append({"kind": kind, "msg": message})
    set_session(resp, s)

def pull(req, resp):
    s = get_session(req)
    out = s.get("_flash", [])
    if out:
        s["_flash"] = []
        set_session(resp, s)
    return out 