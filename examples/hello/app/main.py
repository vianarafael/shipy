from shipy.app import App, Response 
from shipy.render import render 
from shipy.sql import connect, query, exec, tx 

app = App()
connect("db/app.sqlite")

def home(req):
    post = query("SELECT id, title FROM posts ORDER BY id DESC")
    return render("home/index.html", posts=post)

async def create(req):
    await req.load_body()
    with tx():
        exec("INSERT INTO posts(title, body) VALUES(?, ?)", req.form.get("title",""), req.form.get("body", ""))
    return Response.redirect("/")

app.get("/", home)
app.post("/posts", create)
