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

## 3. DB & Auth

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

## 4. CRUD with HTMX

**Create todos template directory:**

```bash
mkdir -p app/views/todos
```

### What's Already Generated vs. What You Need to Add

**✅ Already in scaffold (`app/main.py`):**

- Basic imports including `render_htmx`, `is_htmx_request`, `login_required`
- Middleware setup with `@app.middleware("request")`
- Auth routes (signup, login, logout)
- Basic home route using `render_htmx`

**➕ You need to add:**

**1. Add a helper function for reliable user access:**
```python
# Add this helper function to app/main.py
def get_user_safely(req):
    """Get user from state or fetch directly if not available."""
    if hasattr(req.state, 'user'):
        return req.state.user
    user = current_user(req)
    req.state.user = user  # Cache for future use
    return user
```

**2. Update the home route to include todos:**
```python
# Replace the existing home function in app/main.py
def home(req):
    user = get_user_safely(req)  # Reliable user access
    todos = query("SELECT * FROM todos ORDER BY created_at DESC") if user else []
    return render_htmx(req, "home/index.html", user=user, todos=todos)
```

**3. Add todo CRUD routes:**

````python
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

**4. Add the new routes:**

```python
# Add these route registrations at the end of app/main.py

# HTMX Todo routes
app.get("/todos", todo_list)
app.post("/todos", todo_create)
app.post("/todos/{id}/toggle", todo_toggle)
app.put("/todos/{id}", todo_update)
app.delete("/todos/{id}", todo_delete)
````

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
    />
    <span
      style="flex: 1; {% if todo.done %}text-decoration: line-through; opacity: 0.6;{% endif %}"
      hx-get="/todos/{{ todo.id }}/edit"
      hx-target="this"
      hx-swap="outerHTML"
      style="cursor: pointer;"
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

**3. Add edit functionality (optional):**

```python
# Add this to app/main.py for inline editing

@login_required()
def todo_edit_form(req):
    """Show inline edit form"""
    todo_id = req.path_params.get("id")
    todo = one("SELECT * FROM todos WHERE id = ?", int(todo_id))
    if not todo:
        return Response.text("Todo not found", 404)

    return render_htmx(req, "todos/edit.html", todo=todo)

# Add this route
app.get("/todos/{id}/edit", todo_edit_form)
```

```html
<!-- Create app/views/todos/edit.html -->
<input
  type="text"
  value="{{ todo.title }}"
  hx-put="/todos/{{ todo.id }}"
  hx-trigger="keyup[key=='Enter']"
  hx-target="#todo-list"
  hx-swap="innerHTML"
  style="flex: 1; border: 1px solid #ccc; padding: 4px;"
/>
```

✅ **Result:** Full CRUD with HTMX - add, toggle, delete todos without page reload

## 5. CSRF Protection

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

## 6. Error Handling

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
