# Shipy

The opinionated Indie Maker Python web framework for shipping MVPs stupid-fast.

- App, Request, Response, routing (imperative)
- Jinja2 templates via `shipy.render.render()`
- HTMX support for interactive UI without complex JavaScript
- SQLite helpers in `shipy.sql` (`query`, `one`, `execute`, `tx`)
- Built-in auth with users/sessions + `@login_required` decorator
- Request middleware for per-request data and short-circuiting
- Signed-cookie sessions with CSRF + flash in `shipy.session`
- CLI: `shipy new`, `shipy dev`, `shipy db init`, `shipy deploy`

Note: The SQL write helper is named `execute` (not `exec`, since `exec` is a Python keyword).

## Quick start

```bash
pip install shipy-web
shipy new myapp && cd myapp
shipy db init
shipy dev
```

Visit http://localhost:8000 and sign up to get started!

## Routing

Shipy supports all standard HTTP methods with imperative routing:

```python
from shipy.app import App

app = App()

# Standard HTTP methods
app.get("/", home)
app.post("/users", create_user)
app.put("/users/{id}", update_user)
app.patch("/users/{id}", partial_update_user)
app.delete("/users/{id}", delete_user)

# Path parameters are available in req.path_params
def update_user(req):
    user_id = req.path_params.get("id")
    # ... update logic ...
    return Response.text(f"Updated user {user_id}")
```

## Coding Standards

### Code Organization

Use section comments to organize your code for better readability:

**Python files (`app/main.py`):**

```python
# ---- Imports ----
from shipy.app import App, Response

# ---- App Setup ----
app = App()

# ---- Utilities ----
def helper_function():
    pass

# ---- Middleware ----
@app.middleware("request")
def my_middleware(req):
    pass

# ---- Route Handlers ----
def home(req):
    pass

# ---- Routes ----
app.get("/", home)
```

**HTML templates:**

```html
<!DOCTYPE html>
<html>
  <head>
    <!-- ---- Meta & Head ---- -->
    <meta charset="utf-8" />
    <title>Page Title</title>
  </head>
  <body>
    <!-- ---- Header ---- -->
    <header>...</header>

    <!-- ---- Main Content ---- -->
    <main>...</main>

    <!-- ---- Footer ---- -->
    <footer>...</footer>
  </body>
</html>
```

This consistent organization makes code easier to navigate and maintain.

## Example

See `examples/hello/app/main.py:1` and `examples/hello/app/views/home/index.html:1`.

## CLI

- `shipy new <name>` — creates an auth-first scaffolded project in `./<name>`
- `shipy dev [--app app.main:app] [--host 127.0.0.1] [--port 8000]` — run development server
- `shipy version` — show current version
- `shipy gensecret` — generate a random SHIPY_SECRET for production
- `shipy db init [--db ./data/app.db] [--schema data/schema.sql]` — initialize database
- `shipy db backup [--db ./data/app.db] [--out data/backups]` — create database backup
- `shipy db run <path.sql> [--db ./data/app.db]` — execute SQL script
- `shipy db make-migration <name> [--dir data/migrations]` — create timestamped migration file
- `shipy db ls [--dir data/migrations]` — list migration files
- `shipy db shell [--db ./data/app.db]` — open interactive sqlite3 shell
- `shipy deploy emit [--path deploy]` — generate systemd + nginx configs

## Templates

Default template root is `app/views`. Use `shipy.render.render('path/to/template.html', ctx, request=req)`.

### HTMX Support

Shipy includes built-in HTMX support for interactive UI without complex JavaScript:

```python
from shipy.render import render_htmx, is_htmx_request

# Use render_htmx for HTMX-enhanced templates
def home(req):
    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "home/index.html", todos=todos)

# Check if request is from HTMX
def todo_create(req):
    if is_htmx_request(req):
        # Return partial for HTMX
        return render_htmx(req, "todos/list.html", todos=todos)
    else:
        # Return full page
        return render_req(req, "home/index.html", todos=todos)
```

HTMX templates have access to `htmx` context:

- `htmx.request` - true if request is from HTMX
- `htmx.target` - HTMX target element
- `htmx.trigger` - HTMX trigger event

```html
<!-- HTMX form with partial updates -->
<form hx-post="/todos" hx-target="#todo-list" hx-swap="innerHTML">
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>

<div id="todo-list">
  {% for todo in todos %}
  <div hx-delete="/todos/{{ todo.id }}" hx-target="this" hx-swap="outerHTML">
    {{ todo.title }}
    <button>Delete</button>
  </div>
  {% endfor %}
</div>
```

HTMX is included by default in scaffolded apps via CDN.

### HTMX Response Helpers

For advanced HTMX interactions, use these response helpers:

```python
from shipy.app import Response

# HTMX redirect to specific target
def update_profile(req):
    # ... update logic ...
    return Response.htmx_redirect("/profile", target="#main")

# HTMX refresh (reload the page)
def reset_form(req):
    return Response.htmx_refresh()
```

## Middleware

Request middleware runs on every request after the Request is constructed but before route handlers. Use `@app.middleware("request")` to register middleware functions.

```python
# Attach commonly used data to req.state
@app.middleware("request")
def attach_user(req):
    req.state.user = current_user(req)
    req.state.csrf_token = get_csrf_token(req)

# Short-circuit with a Response (e.g., maintenance mode)
@app.middleware("request")
def maintenance_mode(req):
    if maintenance_enabled:
        return Response.text("Site under maintenance", 503)

# Use in route handlers
def home(req):
    user = req.state.user  # Available via middleware
    return render_req(req, "home.html", user=user)
```

Middleware can:

- Attach data to `req.state` for easy access in handlers
- Short-circuit requests by returning a Response
- Handle errors and logging
- Add per-request objects (DB connections, etc.)

## Sessions

Session data is stored in a signed cookie using `itsdangerous`. Set `SHIPY_SECRET` in your environment for production.

Flash messages are available via `req.session.flash(message, category)` and `req.session.get_flashed_messages()` in requests. CSRF token via `req.session.get_csrf_token()`.

### Authentication

Shipy includes built-in authentication helpers:

```python
from shipy.auth import current_user, login_required, login, logout

# Check if user is logged in
user = current_user(req)

# Protect routes with @login_required decorator
@login_required()
def secret(req):
    # req.state.user is guaranteed to exist here
    return render_req(req, "secret.html", user=req.state.user)

# Custom redirect for unauthenticated users
@login_required(redirect_to="/custom-login")
def admin(req):
    return render_req(req, "admin.html", user=req.state.user)

# Manual authentication (for custom logic)
def manual_auth(req):
    user = current_user(req)
    if not user:
        return Response.redirect("/login")
    return render_req(req, "page.html", user=user)
```

The `@login_required` decorator:

- Redirects unauthenticated users to `/login` (or custom path)
- Automatically attaches user to `req.state.user`
- Works with middleware for additional per-request data

## Database

SQLite helpers in `shipy/sql.py:1` use `./data/app.db` by default (created as needed).

Override the database path with `SHIPY_DB` environment variable:

```bash
SHIPY_DB=/path/to/custom.db shipy dev
```

- `query(sql, params=()) -> list[dict]`
- `one(sql, params=()) -> dict | None`
- `execute(sql, params=()) -> int`
- `with tx() as conn: conn.execute(...)`

Apply schema with `shipy db init --schema data/schema.sql`.

### Migrations

For one-off database changes, use the simple migration system:

```bash
# Create a migration file
shipy db make-migration "add user profiles"

# Edit the generated file in data/migrations/
# Then apply it
shipy db run data/migrations/20250926185037_add_user_profiles.sql

# List all migrations
shipy db ls

# Open interactive sqlite3 shell for debugging
shipy db shell
```

Migrations are plain SQL files wrapped in transactions for atomicity. No complex migration engine - just timestamped files you can read and understand.

## License

MIT.
