from shipy.app import App, Response
from shipy.render import render_req
from shipy.sql import connect, query, one, exec, tx
from shipy.forms import Form
from shipy.auth import (
    current_user, require_login, login_required,
    hash_password, check_password,
    login, logout,
    too_many_login_attempts, record_login_failure, reset_login_failures
)

app = App()
connect("data/app.db")

# Example middleware: attach user to request state for easy access
@app.middleware("request")
def attach_user_to_state(req):
    user = current_user(req)
    req.state.user = user

# Example middleware: add CSRF token to request state
@app.middleware("request")
def add_csrf_token(req):
    from shipy.session import get_session
    session = get_session(req) or {}
    req.state.csrf_token = session.get("csrf", "")

def home(req):
    # User is now available via middleware in req.state.user
    user = req.state.user
    return render_req(req, "home/index.html", user=user)

def signup_form(req):
    return render_req(req, "users/new.html")

async def signup(req):
    await req.load_body()
    form = Form(req.form).require("email","password").min("password", 6).email("email")
    if not form.ok:
        return render_req(req, "users/new.html", form=form)

    existing = one("SELECT id FROM users WHERE email=?", form["email"])
    if existing:
        form.errors.setdefault("email", []).append("already registered")
        return render_req(req, "users/new.html", form=form)

    with tx():
        exec("INSERT INTO users(email, password_hash) VALUES(?, ?)",
             form["email"], hash_password(form["password"]))
        u = one("SELECT id, email FROM users WHERE email=?", form["email"])
    resp = Response.redirect("/")
    login(req, resp, u["id"])
    return resp

def login_form(req):
    return render_req(req, "sessions/login.html")

async def login_post(req):
    await req.load_body()
    form = Form(req.form).require("email","password").email("email")
    ip = req.scope.get("client", ("",0))[0] or "unknown"
    if too_many_login_attempts(ip):
        form.errors.setdefault("email", []).append("too many attempts, try again later")
        return render_req(req, "sessions/login.html", form=form)

    u = one("SELECT id, email, password_hash FROM users WHERE email=?", form["email"])
    if not u or not check_password(form["password"], u["password_hash"]):
        record_login_failure(ip)
        form.errors.setdefault("email", []).append("invalid email or password")
        return render_req(req, "sessions/login.html", form=form)

    reset_login_failures(ip)
    resp = Response.redirect("/")
    login(req, resp, u["id"])
    return resp

async def logout_post(req):
    resp = Response.redirect("/")
    logout(resp)
    return resp

@login_required()
def secret(req):
    # req.state.user is guaranteed to exist here via @login_required
    return render_req(req, "secret.html", user=req.state.user)


# Routes
app.get("/", home)
app.get("/signup", signup_form)
app.post("/signup", signup)

app.get("/login", login_form)
app.post("/login", login_post)
app.post("/logout", logout_post)

app.get("/secret", secret)
