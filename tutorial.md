# Build a Production-Ready Todo App with Auth in Shipy

## Prerequisites

Before starting, you should be comfortable with:

- **Python 3.11+** - Basic syntax, functions, and imports
- **SQL basics** - SELECT, INSERT, UPDATE, DELETE statements
- **HTML/CSS** - Basic markup and styling concepts
- **Command line** - Running commands in terminal/command prompt
- **Git** - Basic version control (clone, commit, push)

**Don't worry if you're new to:**

- HTMX (we'll explain it)
- CSRF protection (we'll cover the basics)
- Database migrations (we'll keep it simple)

## Copy-Paste Quickstart

```bash
# 1. Install & scaffold
# Set up virtual environment first (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Shipy in the virtual environment
pip install shipy-web

# Create new project
shipy new todoapp && cd todoapp

shipy db init

# 2. Add todos table to data/schema.sql
# (users table already exists from scaffold)

# 3. Create todos template directory

mkdir -p app/views/todos

# 4. Update app/main.py with todo routes (see step 4 below)

# 5. Update templates (see step 4 below)

# 6. Run & test

shipy dev

# Visit http://localhost:8000 → signup → login → add todo → toggle todo

```

## How HTMX Works

**HTMX** is a library that lets you add dynamic behavior to HTML without writing JavaScript. Instead of building a complex frontend, you send HTML fragments from your server and HTMX swaps them into the page.

When you check/uncheck a todo, HTMX automatically makes a request and updates the page:

```

1. User clicks checkbox → HTMX sends POST request
   POST /todos/1/toggle HTTP/1.1
   HX-Request: true (tells server this is HTMX)
   HX-Target: #todo-list (where to put response)

2. Server responds with updated HTML
   Response: 200 OK
   Content-Type: text/html
   <div class="stack">
     <div class="card">
       <input type="checkbox" checked hx-post="/todos/1/toggle">
       <span style="text-decoration: line-through;">Buy milk</span>
     </div>
   </div>

3. HTMX replaces #todo-list with new HTML
   → Todo appears crossed out without page reload
```

**Note:** For non-GET requests triggered by hx-post/hx-put/hx-delete, HTMX submits with Content-Type: application/x-www-form-urlencoded. Use hx-vals (or hx-include with a hidden `<input name="csrf">`) to include the CSRF token in the request body so the server can read `req.form['csrf']`.

## 1. Outcome First

**A) First Signup & Login:**

```

✅ User Registration Complete
Email: user@example.com
Password: ********
Status: Authenticated

```

**B) HTMX Todo Toggle:**

## 2. Scaffold

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
│   ├── app.db              # SQLite database (after db init)
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

## 3. DB & Auth

**Add todos table to schema:**

```sql
-- Add to data/schema.sql (users table already exists from scaffold)
CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  done BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at DESC);
```

**Apply updated schema:**

```bash
shipy db init
```

**What this does:** `shipy db init` runs the SQL in `data/schema.sql` (CREATE TABLE IF NOT EXISTS, etc.). If you need a clean reset, delete `data/app.db` first, then run `shipy db init`.

✅ **Result:** Both users and todos tables created

**Auth is already implemented in scaffold:**

- Password hashing with bcrypt/PBKDF2
- Session management with signed cookies
- CSRF protection
- Rate limiting on login attempts

## 4. CRUD with HTMX

**Create todos template directory:**

```bash
mkdir -p app/views/todos
```

### What's Already Generated vs. What You Need to Add

**✅ Already in scaffold (`app/main.py`):**

- Basic imports including `render_htmx`, `is_htmx_request`, `login_required`
- **Middleware setup** with `@app.middleware("request")` - runs code before every request
- Auth routes (signup, login, logout)
- Basic home route using `render_htmx`

**What is middleware?** Middleware functions run automatically before your route handlers. The scaffold includes middleware that attaches the current user to `req.state.user`, so you can access user info in any route.

**Note:** The `@login_required()` decorator redirects unauthenticated users to `/login` (it doesn't return a 404).

**➕ You need to add:**

**1. Update the home route to include todos:**

```python
# Replace the existing home function in app/main.py
# (get_user_safely already exists in scaffold)
def home(req):
    user = get_user_safely(req)  # Reliable user access
    todos = query("SELECT * FROM todos ORDER BY created_at DESC") if user else []  # ← ADD THIS LINE
    return render_htmx(req, "home/index.html", user=user, todos=todos)  # ← ADD todos=todos
```

**2. Add todo CRUD routes:**

```python
# Add these new functions to app/main.py

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
async def todo_update(req):
    """HTMX endpoint for updating todo title"""
    todo_id = req.path_params.get("id")
    if not todo_id:
        return Response.text("Todo ID required", 400)

    await req.load_body()
    form = Form(req.form).require("title")
    if not form.ok:
        return Response.text("Title required", 400)

    with tx():
        exec("UPDATE todos SET title = ? WHERE id = ?", form["title"], int(todo_id))

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

@login_required()
def todo_edit_form(req):
    """Show inline edit form"""
    todo_id = req.path_params.get("id")
    todo = one("SELECT * FROM todos WHERE id = ?", int(todo_id))
    if not todo:
        return Response.text("Todo not found", 404)

    return render_htmx(req, "todos/edit.html", todo=todo)
```

**3. Add the new routes:**

```python
# Add these route registrations at the end of app/main.py

# HTMX Todo routes
app.get("/todos", todo_list)
app.post("/todos", todo_create)
app.post("/todos/{id}/toggle", todo_toggle)
app.put("/todos/{id}", todo_update)
app.delete("/todos/{id}", todo_delete)
app.get("/todos/{id}/edit", todo_edit_form)
```

### Template Updates

**✅ Already in scaffold (`app/views/home/index.html`):**

- Basic HTML structure with HTMX CDN
- Header with navigation
- Flash message display
- Basic user authentication UI

**➕ You need to add the todo functionality:**

**1. Update the home template to include todos:**

```html
<!-- Replace the content inside the {% if user %} block in app/views/home/index.html -->
{% if user %}
<div class="card">
  <h2>My Todos</h2>

  <!-- Todo Form -->
  {% include "todos/form.html" %}

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
```

**2. Create the todo list partial:**

```html
<!-- Create new file: app/views/todos/list.html -->
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
      hx-vals='{"csrf":"{{ csrf }}"}'
    />
    <span
      style="flex: 1; cursor: pointer; {% if todo.done %}text-decoration: line-through; opacity: 0.6;{% endif %}"
      hx-get="/todos/{{ todo.id }}/edit"
      hx-target="this"
      hx-swap="outerHTML"
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
      hx-vals='{"csrf":"{{ csrf }}"}'
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

**3. Create the todo form template:**

```html
<!-- Create new file: app/views/todos/form.html -->
<form hx-post="/todos" hx-target="#todo-list" hx-swap="innerHTML" class="stack">
  <input type="hidden" name="csrf" value="{{ csrf }}" />
  <div style="display: flex; gap: 10px;">
    <input
      class="input"
      name="title"
      placeholder="New todo..."
      value="{{ form.title if form else '' }}"
      style="flex: 1;"
    />
    <button class="btn" type="submit">Add</button>
  </div>
  {% if form and form.errors.title %}
  <div class="error">{{ form.errors.title[0] }}</div>
  {% endif %}
</form>
```

**4. Create the edit template:**

```html
<!-- app/views/todos/edit.html -->
<span
  hx-get="/todos"
  hx-target="#todo-list"
  hx-swap="innerHTML"
  hx-trigger="keyup[key=='Escape'] from:body once"
  style="flex: 1; display: flex;"
>
  <input
    type="text"
    name="title"
    value="{{ todo.title }}"
    hx-put="/todos/{{ todo.id }}"
    hx-vals='{"csrf":"{{ csrf }}"}'
    hx-trigger="keyup[key=='Enter'] once, blur changed once"
    hx-target="#todo-list"
    hx-swap="innerHTML"
    style="flex: 1; border: 1px solid #ccc; padding: 4px;"
    autofocus
  />
</span>
```

✅ **Result:** Full CRUD with HTMX - add, toggle, delete todos without page reload

## 5. CSRF Protection

**What is CSRF Protection?**

CSRF (Cross-Site Request Forgery) protection prevents malicious websites from making unauthorized requests to your app. For example, without CSRF protection, a malicious site could trick a logged-in user into deleting all their todos.

**How CSRF works in Shipy:**

- Token automatically generated per session and stored in signed cookie
- Available in templates as `{{ csrf }}`
- Required for all POST/PUT/DELETE requests (unsafe methods)
- Must be included in request body as `name="csrf"` (headers like X-CSRF-Token are ignored)

### Examples

**❌ Failing example (missing CSRF):**

```html
<!-- This will fail with 403 Forbidden -->
<form method="post" action="/todos">
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>
```

**✅ Fixed version:**

```html
<!-- This works -->
<form method="post" action="/todos">
  <input type="hidden" name="csrf" value="{{ csrf }}" />
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>
```

✅ **Result:** CSRF protection prevents unauthorized form submissions

## 6. Error Handling

**Shipy error page shows:**

- Full stack trace (in DEBUG mode)
- Clean error message (in production)
- Proper HTTP status codes

### Test Error Handling

**Add this route to test error handling:**

```python
# Add this route to app/main.py for testing
def error_test(req):
    raise Exception("This is a test error")
    return Response.text("This won't be reached")

app.get("/error", error_test)
```

**Visit http://localhost:8000/error**

✅ **Result:** Professional error handling with debugging info

## Troubleshooting

### Common Issues and Solutions

**🚫 "shipy: command not found"**

```bash
# Make sure you're in your virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Reinstall if needed
pip install shipy-web
```

**🚫 "403 Forbidden" errors**

- **Cause:** Missing CSRF token
- **Solution:** Make sure all forms include `name="csrf" value="{{ csrf }}"` or use `hx-vals='{"csrf":"{{ csrf }}"}'`

**🚫 "404 Not Found" for todo routes**

- **Cause:** Routes not registered
- **Solution:** Make sure you added the route registrations from step 4

**🚫 "Template not found" errors**

- **Cause:** Missing template files
- **Solution:** Create all required templates: `todos/list.html`, `todos/form.html`, `todos/edit.html`

**🚫 Database connection issues**

- **Cause:** Database not initialized
- **Solution:** Run `shipy db init` after adding the todos table to schema

**🚫 "AttributeError: 'types.SimpleNamespace' object has no attribute 'user'"**

- **Cause:** Middleware not running properly
- **Solution:** Use `get_user_safely(req)` instead of `req.state.user` directly

### Debugging Tips

1. **Check the terminal** - Shipy shows detailed error messages in development
2. **Use browser dev tools** - Check the Network tab to see failed requests
3. **Verify file paths** - Make sure all templates are in the correct directories
4. **Test incrementally** - Get basic auth working before adding todos

## 7. Production Deploy

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

## 8. Recap & Next Steps

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

-- Add triggers to keep FTS in sync
CREATE TRIGGER todos_ai AFTER INSERT ON todos BEGIN
  INSERT INTO todos_fts(rowid, title) VALUES (new.id, new.title);
END;

CREATE TRIGGER todos_au AFTER UPDATE ON todos BEGIN
  DELETE FROM todos_fts WHERE rowid = old.id;
  INSERT INTO todos_fts(rowid, title) VALUES (new.id, new.title);
END;

CREATE TRIGGER todos_ad AFTER DELETE ON todos BEGIN
  DELETE FROM todos_fts WHERE rowid = old.id;
END;

-- Search query
SELECT t.* FROM todos t
JOIN todos_fts fts ON t.id = fts.rowid
WHERE todos_fts MATCH ?
ORDER BY bm25(todos_fts);
```

**3. User-Scoped Todos:**

```sql
-- Add user_id column to todos table
ALTER TABLE todos ADD COLUMN user_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_todos_user_created ON todos(user_id, created_at DESC);
```

```python
@login_required()
async def todo_create(req):
    await req.load_body()
    form = Form(req.form).require("title")
    if not form.ok:
        return render_htmx(req, "todos/form.html", form=form)

    user_id = req.state.user["id"]
    with tx():
        exec("INSERT INTO todos(title, done, user_id) VALUES(?, ?, ?)",
             form["title"], False, user_id)

@login_required()
def todo_list(req):
    user_id = req.state.user["id"]
    todos = query("SELECT * FROM todos WHERE user_id = ? ORDER BY created_at DESC", user_id)
    return render_htmx(req, "todos/list.html", todos=todos)

# Update all SELECT/UPDATE/DELETE to add WHERE user_id = ? so users can only change their own todos
```

**Shipy Philosophy Delivered:**

- No build step ✅
- Server-rendered HTML ✅
- Raw SQL with helpers ✅
- Signed-cookie sessions ✅
- HTMX for interactivity ✅
- Production-ready ✅

**You shipped a working todo app in under 30 minutes!**
