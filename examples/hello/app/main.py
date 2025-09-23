from shipy.app import App, Response 
from shipy.render import render_req, render
from shipy.sql import connect, query, one, exec, tx  
from shipy.session import get_session, set_session, clear_session
from shipy.csrf import verify, ensure_token
from shipy.flash import add as flash 

app = App()
connect("db/app.sqlite")

def home(req):
    post = query("SELECT id, title, body FROM posts ORDER BY id DESC")
    return render_req(req, "home/index.html", posts=post)

def about(req):
    return render("home/about.html")

def login_form(req):
    return render_req(req, "sessions/login.html")

async def login_form(req):
    return render_req(req, "sessions/login.html")

async def login(req):
    await req.load_body()
    # demo-only login: any email logs in as user id 1
    resp = Response.redirect("/")
    set_session(resp, {"uid": 1, "sv": 1}) # add csrf later via render_req
    flash(req, resp, "Logged in!")
    return resp 

def logout(req):
    resp = Response.redirect("/")
    clear_session(resp)
    flash(req, resp, "Logged out.", "ok")
    return resp 


async def create_post(req):
    await req.load_body()
    # forbidden = verify(req)
    # if forbidden: return forbidden
    with tx():
        exec("INSERT INTO posts(title, body) VALUES(?,?)", req.form["title"], req.form["body"])
    return Response.redirect("/")


app.get("/", home)
app.get("/about", about)
app.get("/login", login_form)
app.post("/login", login)
app.post("/posts", create_post)
app.post("/logout", logout)

def not_found(req):
    # Render a friendly 404 page and set status
    resp = render("home/404.html")
    resp.status = 404
    return resp

# Keep these last so they only match if nothing else did
app.get("/.*", not_found)
app.post("/.*", not_found)
