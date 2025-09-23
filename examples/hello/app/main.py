from shipy.app import App, Response
from shipy.render import render_req
from shipy.sql import connect, query, one, exec, tx
from shipy.forms import Form
from shipy.auth import (
    current_user, require_login,
    hash_password, check_password,
    login, logout,
    too_many_login_attempts, record_login_failure, reset_login_failures
)

app = App()
connect("db/app.sqlite")

def home(req):
    posts = query("SELECT id, title FROM posts ORDER BY id DESC")
    user = current_user(req)
    return render_req(req, "home/index.html", posts=posts, user=user)

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

def secret(req):
    user = require_login(req)
    if not user:
        return Response.redirect("/login")
    return render_req(req, "secret.html", user=user)

# existing posts create route (respects global CSRF already)
async def create_post(req):
    await req.load_body()
    form = Form(req.form).require("title","body").min("title", 3)
    if not form.ok:
        posts = query("SELECT id, title FROM posts ORDER BY id DESC")
        return render_req(req, "home/index.html", posts=posts, form=form, user=current_user(req))
    with tx():
        exec("INSERT INTO posts(title, body) VALUES(?,?)", form["title"], form["body"])
    return Response.redirect("/")

# Routes
app.get("/", home)
app.get("/signup", signup_form)
app.post("/signup", signup)

app.get("/login", login_form)
app.post("/login", login_post)
app.post("/logout", logout_post)

app.get("/secret", secret)
app.post("/posts", create_post)
