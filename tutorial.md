# Build a Production-Ready Todo App with Auth in Shipy

## Copy-Paste Quickstart

```bash
# 1. Install & scaffold
pip install shipy-web
shipy new todoapp && cd todoapp
shipy db init

# 2. Add todos table (Windows: use type instead of echo)
echo "CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" >> data/schema.sql
shipy db init

# 3. Create todos template directory
mkdir -p app/views/todos

# 4. Update app/main.py with todo routes (see step 5)
# 5. Update templates (see step 5)
# 6. Run & test
shipy dev
# Visit http://localhost:8000 → signup → login → add todo → toggle todo
```

## 1. Outcome First

**A) First Signup & Login:**

```
✅ User Registration Complete
Email: user@example.com
Password: ********
Status: Authenticated
```

**B) HTMX Todo Toggle:**

```
✅ HTMX Request/Response
POST /todos/1/toggle HTTP/1.1
HX-Request: true
HX-Target: #todo-list

Response: 200 OK
Content-Type: text/html
<div class="stack">
  <div class="card">
    <input type="checkbox" checked hx-post="/todos/1/toggle">
    <span style="text-decoration: line-through;">Buy milk</span>
  </div>
</div>
```

## 2. Stack Check

**30-Second Checklist:**

- ✅ Python 3.11+ installed (`python --version`)
- ✅ `pip install shipy-web` works
- ✅ `shipy --version` shows 0.2.2+
- ✅ Port 8000 available
- ✅ Basic terminal/editor skills

**What You'll Build:**

- User authentication (signup/login/logout)
- Protected todo CRUD with HTMX
- CSRF protection
- Production deployment config

## 3. Scaffold

**Generate the app:**

```bash
shipy new todoapp
cd todoapp
```

**Generated tree (pruned):**

```
todoapp/
├── app/
│   ├── main.py              # Your routes
│   └── views/               # Jinja templates
│       ├── home/index.html
│       ├── users/new.html
│       └── sessions/login.html
├── data/
│   ├── app.db              # SQLite database
│   └── schema.sql          # Initial schema
├── public/
│   └── base.css            # Default styles
└── .gitignore
```

**Initialize database:**

```bash
shipy db init
```

✅ **Result:** Database created with users table

## 4. DB & Auth

**Add todos table to schema:**

```sql
-- data/schema.sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  done BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at DESC);
```

**Reinitialize database:**

```bash
shipy db init
```

✅ **Result:** Both users and todos tables created

**Auth is already implemented in scaffold:**

- Password hashing with bcrypt/PBKDF2
- Session management with signed cookies
- CSRF protection
- Rate limiting on login attempts

## 5. CRUD with HTMX

**Create todos template directory:**

```bash
mkdir -p app/views/todos
```

**Update app/main.py:**

```python
# app/main.py
from shipy.app import App, Response
from shipy.render import render_req, render_htmx, is_htmx_request
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

# Middleware: attach user to request state
@app.middleware("request")
def attach_user_to_state(req):
    user = current_user(req)
    req.state.user = user

@app.middleware("request")
def add_csrf_token(req):
    from shipy.session import get_session
    session = get_session(req) or {}
    req.state.csrf_token = session.get("csrf", "")

def home(req):
    user = req.state.user
    todos = query("SELECT * FROM todos ORDER BY created_at DESC") if user else []
    return render_htmx(req, "home/index.html", user=user, todos=todos)

# Auth routes (from scaffold)
def signup_form(req): return render_req(req, "users/new.html")

async def signup(req):
    await req.load_body()
    form = Form(req.form).require("email","password").min("password", 6).email("email")
    if not form.ok: return render_req(req, "users/new.html", form=form)
    if one("SELECT id FROM users WHERE email=?", form["email"]):
        form.errors.setdefault("email", []).append("already registered")
        return render_req(req, "users/new.html", form=form)
    with tx():
        exec("INSERT INTO users(email,password_hash) VALUES(?,?)",
             form["email"], hash_password(form['password']))
        u = one("SELECT id,email FROM users WHERE email=?", form["email"])
    resp = Response.redirect("/")
    login(req, resp, u["id"])
    return resp

def login_form(req): return render_req(req, "sessions/login.html")

async def login_post(req):
    await req.load_body()
    form = Form(req.form).require("email","password").email("email")
    ip = req.scope.get("client", ("",0))[0] or "unknown"
    if too_many_login_attempts(ip):
        form.errors.setdefault("email", []).append("too many attempts, try later")
        return render_req(req, "sessions/login.html", form=form)
    u = one("SELECT id,email,password_hash FROM users WHERE email=?", form["email"])
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

# Todo CRUD routes
@login_required()
def todo_list(req):
    """HTMX endpoint for todo list partial"""
    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@login_required()
async def todo_create(req):
    """HTMX endpoint for creating todos"""
    await req.load_body()
    form = Form(req.form).require("title")
    if not form.ok:
        return render_htmx(req, "todos/form.html", form=form)

    with tx():
        exec("INSERT INTO todos(title, done) VALUES(?, ?)", form["title"], False)

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@login_required()
async def todo_toggle(req):
    """HTMX endpoint for toggling todo done status"""
    todo_id = req.path_params.get("id")
    if not todo_id:
        return Response.text("Todo ID required", 400)

    with tx():
        exec("UPDATE todos SET done = NOT done WHERE id = ?", int(todo_id))

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@login_required()
async def todo_delete(req):
    """HTMX endpoint for deleting todos"""
    todo_id = req.path_params.get("id")
    if not todo_id:
        return Response.text("Todo ID required", 400)

    with tx():
        exec("DELETE FROM todos WHERE id = ?", int(todo_id))

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

# Routes
app.get("/", home)
app.get("/signup", signup_form)
app.post("/signup", signup)
app.get("/login", login_form)
app.post("/login", login_post)
app.post("/logout", logout_post)

# HTMX Todo routes
app.get("/todos", todo_list)
app.post("/todos", todo_create)
app.post("/todos/{id}/toggle", todo_toggle)
app.delete("/todos/{id}", todo_delete)
```

**Update home template:**

```html
<!-- app/views/home/index.html -->
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Shipy Todo App</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <link rel="stylesheet" href="/public/base.css" />
  </head>
  <body>
    <div class="wrap">
      <header>
        <strong>Shipy Todo</strong>
        <nav>
          {% if user %}
          <span>{{ user.email }}</span>
          <form method="post" action="/logout" style="display:inline">
            <input type="hidden" name="csrf" value="{{ csrf }}" />
            <button class="btn">Logout</button>
          </form>
          {% else %}
          <a href="/login">Login</a> <a href="/signup">Sign up</a>
          {% endif %}
        </nav>
      </header>

      {% if flashes %} {% for f in flashes %}
      <div class="flash">{{ f.msg }}</div>
      {% endfor %} {% endif %} {% if user %}
      <div class="card">
        <h2>My Todos</h2>

        <!-- Todo Form -->
        <form
          hx-post="/todos"
          hx-target="#todo-list"
          hx-swap="innerHTML"
          class="stack"
        >
          <input type="hidden" name="csrf" value="{{ csrf }}" />
          <div style="display: flex; gap: 10px;">
            <input
              class="input"
              name="title"
              placeholder="New todo..."
              style="flex: 1;"
            />
            <button class="btn" type="submit">Add</button>
          </div>
        </form>

        <!-- Todo List -->
        <div id="todo-list">{% include "todos/list.html" %}</div>
      </div>
      {% else %}
      <div class="card">
        <h2>Welcome to Shipy Todo</h2>
        <p>
          Please <a href="/signup">sign up</a> or <a href="/login">log in</a> to
          manage your todos.
        </p>
      </div>
      {% endif %}
    </div>
  </body>
</html>
```

**Create todo list partial:**

```html
<!-- app/views/todos/list.html -->
{% if todos %}
<div class="stack">
  {% for todo in todos %}
  <div class="card" style="display: flex; align-items: center; gap: 10px;">
    <input
      type="checkbox"
      {%
      if
      todo.done
      %}checked{%
      endif
      %}
      hx-post="/todos/{{ todo.id }}/toggle"
      hx-target="#todo-list"
      hx-swap="innerHTML"
    />
    <span
      style="flex: 1; {% if todo.done %}text-decoration: line-through; opacity: 0.6;{% endif %}"
    >
      {{ todo.title }}
    </span>
    <button
      class="btn"
      style="background: #dc2626; padding: 4px 8px; font-size: 12px;"
      hx-delete="/todos/{{ todo.id }}"
      hx-target="#todo-list"
      hx-swap="innerHTML"
      hx-confirm="Delete this todo?"
    >
      Delete
    </button>
  </div>
  {% endfor %}
</div>
{% else %}
<div class="muted">No todos yet. Add one above!</div>
{% endif %}
```

✅ **Result:** Full CRUD with HTMX - add, toggle, delete todos without page reload

## 6. CSRF Protection

**How CSRF works in Shipy:**

- Token automatically generated and stored in signed cookie
- Available in templates as `{{ csrf }}`
- Required for all POST/PUT/DELETE requests
- Generated via `shipy gensecret` for production

**Failing example (missing CSRF):**

```html
<!-- This will fail with 403 Forbidden -->
<form method="post" action="/todos">
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>
```

**Fixed version:**

```html
<!-- This works -->
<form method="post" action="/todos">
  <input type="hidden" name="csrf" value="{{ csrf }}" />
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>
```

✅ **Result:** CSRF protection prevents unauthorized form submissions

## 7. Error Handling

**Trigger a server error:**

```python
# Add this route to app/main.py for testing
def error_test(req):
    raise Exception("This is a test error")
    return Response.text("This won't be reached")

app.get("/error", error_test)
```

**Visit http://localhost:8000/error**

**Shipy error page shows:**

- Full stack trace (in DEBUG mode)
- Clean error message (in production)
- Proper HTTP status codes

✅ **Result:** Professional error handling with debugging info

## 8. Production Deploy

**Generate deployment files:**

```bash
shipy deploy emit --domain yourdomain.com
```

**Generate secret key:**

```bash
shipy gensecret
# Copy the output for SHIPY_SECRET
```

**Generated files:**

**deploy/todoapp.service:**

```ini
[Unit]
Description=Shipy app todoapp
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/user/todoapp
Environment=SHIPY_BASE=/home/user/todoapp
Environment=SHIPY_DEBUG=0
Environment=SHIPY_SECRET=your-secret-key-here
ExecStart=/usr/bin/env uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

**deploy/yourdomain.com.conf:**

```nginx
server {
  listen 80;
  server_name yourdomain.com;

  root /home/user/todoapp/public;

  location /public/ {
    try_files $uri =404;
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
  }
}
```

**Deploy commands:**

```bash
# On your server
sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl enable --now todoapp.service
sudo cp deploy/yourdomain.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/yourdomain.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**Environment variables:**

- `SHIPY_DEBUG=0` - Disable debug mode
- `SHIPY_SECRET` - Secret key for cookie signing (use `shipy gensecret`)
- `SHIPY_BASE` - App root directory

✅ **Result:** Production-ready deployment with systemd + nginx

## 9. Recap & Next Steps

**What you built:**

- ✅ User authentication with sessions
- ✅ Protected todo CRUD with HTMX
- ✅ CSRF protection
- ✅ Production deployment config

**3 Extensions:**

**1. Pagination:**

```python
def todos_paginated(req):
    page = int(req.query.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    todos = query("SELECT * FROM todos ORDER BY created_at DESC LIMIT ? OFFSET ?",
                  per_page, offset)
    total = one("SELECT COUNT(*) as count FROM todos")["count"]

    return render_htmx(req, "todos/paginated.html",
                      todos=todos, page=page, total=total, per_page=per_page)
```

**2. Full-Text Search:**

```sql
-- Add FTS table
CREATE VIRTUAL TABLE todos_fts USING fts5(title, content=todos);

-- Search query
SELECT t.* FROM todos t
JOIN todos_fts fts ON t.id = fts.rowid
WHERE todos_fts MATCH ?
ORDER BY rank;
```

**3. User-Scoped Todos:**

```python
@login_required()
async def todo_create(req):
    user_id = req.state.user["id"]
    with tx():
        exec("INSERT INTO todos(title, done, user_id) VALUES(?, ?, ?)",
             form["title"], False, user_id)
```

**Shipy Philosophy Delivered:**

- No build step ✅
- Server-rendered HTML ✅
- Raw SQL with helpers ✅
- Signed-cookie sessions ✅
- HTMX for interactivity ✅
- Production-ready ✅

**You shipped a working todo app in under 30 minutes!**
