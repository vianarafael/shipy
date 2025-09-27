# Shipy Developer API Reference

## Table of Contents

- [Core Application](#core-application)
- [Request & Response](#request--response)
- [Database Layer](#database-layer)
- [Authentication](#authentication)
- [Templates & Rendering](#templates--rendering)
- [Forms & Validation](#forms--validation)
- [Sessions & Cookies](#sessions--cookies)
- [Middleware](#middleware)
- [HTMX Support](#htmx-support)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Coding Standards](#coding-standards)

## Coding Standards

### Code Organization

Shipy follows consistent code organization patterns to improve readability and maintainability.

#### Python Files

Use section comments to organize your code:

```python
# ---- Imports ----
from shipy.app import App, Response
from shipy.render import render_req
from shipy.sql import query, one, exec

# ---- App Setup ----
app = App()
connect("data/app.db")

# ---- Utilities ----
def get_user_safely(req):
    """Helper function for reliable user access."""
    pass

# ---- Middleware ----
@app.middleware("request")
def attach_user_to_state(req):
    """Attach user to request state."""
    pass

# ---- Route Handlers ----
def home(req):
    """Home page handler."""
    pass

def login_form(req):
    """Login form handler."""
    pass

# ---- Routes ----
app.get("/", home)
app.get("/login", login_form)
```

#### HTML Templates

Use HTML comments to organize template sections:

```html
<!DOCTYPE html>
<html>
  <head>
    <!-- ---- Meta & Head ---- -->
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Page Title</title>
    <link rel="stylesheet" href="/public/base.css" />
  </head>
  <body>
    <div class="wrap">
      <!-- ---- Header ---- -->
      <header>
        <h1>App Name</h1>
        <nav>...</nav>
      </header>

      <!-- ---- Flash Messages ---- -->
      {% if flashes %}{% for f in flashes %}
      <div class="flash">{{ f.msg }}</div>
      {% endfor %}{% endif %}

      <!-- ---- Main Content ---- -->
      <main>
        <h2>Page Content</h2>
        <p>...</p>
      </main>

      <!-- ---- Footer ---- -->
      <footer>...</footer>
    </div>
  </body>
</html>
```

#### Benefits

- **Consistency**: All Shipy projects follow the same organization pattern
- **Readability**: Easy to locate specific sections of code
- **Maintainability**: Clear separation of concerns
- **Onboarding**: New developers can quickly understand project structure

## Core Application

### `App` Class

The main application class that handles routing and request processing.

```python
from shipy.app import App

app = App()
```

#### Methods

**`add(method, path, handler)`**

- Register a route with specific HTTP method
- `method`: HTTP method string ("GET", "POST", etc.)
- `path`: URL pattern with optional parameters (`{id}`, `{id:int}`)
- `handler`: Function that takes `Request` and returns `Response`

**`get(path, handler)`**

- Register GET route
- Shorthand for `add("GET", path, handler)`

**`post(path, handler)`**

- Register POST route
- Shorthand for `add("POST", path, handler)`

**`put(path, handler)`**

- Register PUT route
- Shorthand for `add("PUT", path, handler)`

**`patch(path, handler)`**

- Register PATCH route
- Shorthand for `add("PATCH", path, handler)`

**`delete(path, handler)`**

- Register DELETE route
- Shorthand for `add("DELETE", path, handler)`

**`middleware(phase)`**

- Register middleware function
- `phase`: Currently only "request" supported
- Returns decorator function

#### Route Parameters

Path parameters are defined with curly braces:

```python
# String parameter
app.get("/users/{id}", user_detail)

# Integer parameter
app.get("/posts/{id:int}", post_detail)

# Multiple parameters
app.get("/users/{user_id}/posts/{post_id:int}", user_post)
```

Parameters are available in `req.path_params`:

```python
def user_detail(req):
    user_id = req.path_params["id"]  # Always string
    post_id = int(req.path_params["post_id"])  # Convert to int
```

## Request & Response

### `Request` Class

Represents an incoming HTTP request.

#### Properties

**`scope`** - ASGI scope dictionary
**`method`** - HTTP method string ("GET", "POST", etc.)
**`path`** - Request path ("/users/123")
**`query`** - Query parameters as dict (`{"page": "1", "search": "term"}`)
**`path_params`** - Route parameters as dict (`{"id": "123"}`)
**`form`** - Form data (after calling `await req.load_body()`)
**`cookies`** - Request cookies as dict
**`state`** - Per-request storage (`types.SimpleNamespace`)
**`headers`** - Request headers as dict (lowercase keys)

#### Methods

**`await load_body()`**

- Load request body and parse form data
- Must be called before accessing `req.form`
- Idempotent - safe to call multiple times

```python
async def create_user(req):
    await req.load_body()  # Required for form data
    email = req.form["email"]
    password = req.form["password"]
```

### `Response` Class

Represents an HTTP response.

#### Constructor

```python
Response(body=b"", status=200, headers=None, content_type="text/html; charset=utf-8")
```

#### Class Methods

**`Response.html(text, status=200)`**

- Create HTML response
- `text`: HTML string
- `status`: HTTP status code

**`Response.text(text, status=200)`**

- Create plain text response
- `text`: Plain text string
- `status`: HTTP status code

**`Response.redirect(location, status=303)`**

- Create redirect response
- `location`: URL to redirect to
- `status`: HTTP status code (default 303)

**`Response.htmx_redirect(location, target="#main")`**

- HTMX redirect (updates browser URL without full page reload)
- `location`: URL to redirect to
- `target`: HTMX target element

**`Response.htmx_refresh()`**

- HTMX refresh (triggers page refresh)

#### Instance Methods

**`set_cookie(name, value, **kwargs)`\*\*

- Set cookie on response
- `name`: Cookie name
- `value`: Cookie value
- `http_only`: HTTP-only flag (default True)
- `samesite`: SameSite policy (default "Lax")
- `path`: Cookie path (default "/")
- `max_age`: Max age in seconds
- `secure`: Secure flag (auto-enabled in production)

**`delete_cookie(name, path="/")`**

- Delete cookie
- `name`: Cookie name
- `path`: Cookie path

## Database Layer

### Connection

**`connect(path="data/app.db")`**

- Connect to SQLite database
- Auto-creates directory if needed
- Applies schema.sql on first connection
- Returns connection object

```python
from shipy.sql import connect
connect("data/app.db")
```

### Query Functions

**`query(sql, *args)`**

- Execute SELECT query and return all rows
- Returns list of dicts (one per row)
- `sql`: SQL query string
- `args`: Query parameters

```python
from shipy.sql import query
users = query("SELECT * FROM users WHERE active = ?", True)
```

**`one(sql, *args)`**

- Execute SELECT query and return single row
- Returns dict or None
- Raises ValueError if multiple rows found

```python
from shipy.sql import one
user = one("SELECT * FROM users WHERE id = ?", user_id)
```

**`exec(sql, *args)`**

- Execute INSERT/UPDATE/DELETE query
- Returns `ExecResult` with `rowcount` and `last_id`

```python
from shipy.sql import exec
result = exec("INSERT INTO users (email) VALUES (?)", email)
user_id = result.last_id
```

### Transactions

**`tx()`**

- Context manager for database transactions
- Auto-rollback on exception
- Auto-commit on success

```python
from shipy.sql import tx, exec

with tx():
    exec("INSERT INTO users (email) VALUES (?)", email)
    exec("INSERT INTO profiles (user_id) VALUES (?)", user_id)
    # Both succeed or both fail
```

### ExecResult

**`rowcount`** - Number of affected rows
**`last_id`** - ID of last inserted row (for INSERT)

## Authentication

### Password Hashing

**`hash_password(password)`**

- Hash password for storage
- Uses bcrypt if available, falls back to PBKDF2
- Returns hashed string

**`check_password(password, stored)`**

- Verify password against stored hash
- `password`: Plain text password
- `stored`: Stored hash from database
- Returns boolean

```python
from shipy.auth import hash_password, check_password

# Hash password for storage
hashed = hash_password("secret123")

# Verify password
is_valid = check_password("secret123", hashed)
```

### User Management

**`current_user(req)`**

- Get current user from session
- Returns user dict or None
- User dict contains: `id`, `email`, `created_at`

**`login(req, resp, user_id)`**

- Log user in (set session)
- `req`: Request object
- `resp`: Response object
- `user_id`: User ID from database

**`logout(resp)`**

- Log user out (clear session)
- `resp`: Response object

```python
from shipy.auth import current_user, login, logout

# Check if user is logged in
user = current_user(req)
if user:
    print(f"Logged in as {user['email']}")

# Log user in
login(req, resp, user_id)

# Log user out
logout(resp)
```

### Route Protection

**`@login_required(redirect_to="/login")`**

- Decorator to protect routes
- Redirects to login if not authenticated
- Attaches user to `req.state.user`

```python
from shipy.auth import login_required

@app.get("/secret")
@login_required()
def secret(req):
    # req.state.user is guaranteed to exist
    user = req.state.user
    return render_req(req, "secret.html", user=user)
```

### Rate Limiting

**`too_many_login_attempts(ip, window_sec=300, limit=5)`**

- Check if IP has too many login attempts
- `ip`: IP address string
- `window_sec`: Time window in seconds (default 5 minutes)
- `limit`: Max attempts in window (default 5)

**`record_login_failure(ip)`**

- Record failed login attempt
- `ip`: IP address string

**`reset_login_failures(ip)`**

- Reset login attempts for IP
- `ip`: IP address string

```python
from shipy.auth import too_many_login_attempts, record_login_failure, reset_login_failures

ip = req.scope.get("client", ("", 0))[0] or "unknown"

if too_many_login_attempts(ip):
    return render_req(req, "login.html", error="Too many attempts")

# After successful login
reset_login_failures(ip)
```

## Templates & Rendering

### Template Functions

**`render(template, **ctx)`\*\*

- Basic template rendering
- No session/cookie handling
- Good for static pages

**`render_req(req, template, **ctx)`\*\*

- Template rendering with request context
- Includes CSRF token and flash messages
- Template gets: `csrf`, `flashes`, plus your context

**`render_htmx(req, template, **ctx)`\*\*

- HTMX-aware template rendering
- Includes all `render_req` functionality
- Template gets: `csrf`, `flashes`, `htmx`, plus your context

```python
from shipy.render import render, render_req, render_htmx

# Basic rendering
return render("home.html", title="Home")

# With request context
return render_req(req, "users/profile.html", user=user)

# HTMX rendering
return render_htmx(req, "todos/list.html", todos=todos)
```

### HTMX Helpers

**`is_htmx_request(req)`**

- Check if request is from HTMX
- Returns boolean

```python
from shipy.render import is_htmx_request

def my_handler(req):
    if is_htmx_request(req):
        return render_htmx(req, "partial.html")
    else:
        return render_req(req, "full-page.html")
```

### Template Context

When using `render_req` or `render_htmx`, templates get:

**`csrf`** - CSRF token string
**`flashes`** - List of flash messages
**`htmx`** - HTMX context (only with `render_htmx`)

HTMX context object:

- `htmx.request` - Boolean (is HTMX request)
- `htmx.target` - HTMX target element
- `htmx.trigger` - HTMX trigger name
- `htmx.current_url` - Current URL

### Template Example

```html
<!-- app/views/users/profile.html -->
<h1>Profile</h1>

<!-- CSRF token for forms -->
<form method="post" action="/update-profile">
  <input type="hidden" name="csrf" value="{{ csrf }}" />
  <input name="name" value="{{ user.name }}" />
  <button>Update</button>
</form>

<!-- Flash messages -->
{% for flash in flashes %}
<div class="flash flash-{{ flash.kind }}">{{ flash.msg }}</div>
{% endfor %}

<!-- HTMX context (if using render_htmx) -->
{% if htmx.request %}
<p>This is an HTMX request</p>
{% endif %}
```

## Forms & Validation

### `Form` Class

Simple form validation helper.

```python
from shipy.forms import Form

async def create_user(req):
    await req.load_body()
    form = Form(req.form)

    # Chain validators
    form.require("email", "password").min("password", 6).email("email")

    if not form.ok:
        return render_req(req, "users/new.html", form=form)

    # Form is valid
    email = form["email"]
    password = form["password"]
```

#### Methods

**`require(*fields)`**

- Mark fields as required
- Returns self for chaining

**`min(field, n)`**

- Minimum length validation
- `field`: Field name
- `n`: Minimum length
- Returns self for chaining

**`email(field="email")`**

- Email format validation
- `field`: Field name (default "email")
- Returns self for chaining

#### Properties

**`ok`** - Boolean (no validation errors)
**`data`** - Dict of form data
**`errors`** - Dict of field errors

#### Template Usage

```python
# In handler
form = Form(req.form).require("email").email()
return render_req(req, "form.html", form=form)
```

```html
<!-- In template -->
<form method="post">
  <input name="email" value="{{ form['email'] }}" />
  {% for error in form.errors_for('email') %}
  <span class="error">{{ error }}</span>
  {% endfor %}

  <button>Submit</button>
</form>
```

## Sessions & Cookies

### Session Functions

**`get_session(req)`**

- Get session data from request
- Returns dict or empty dict

**`set_session(resp, data)`**

- Set session data on response
- `resp`: Response object
- `data`: Session data dict

**`clear_session(resp)`**

- Clear session data
- `resp`: Response object

```python
from shipy.session import get_session, set_session, clear_session

# Get session
session = get_session(req)
user_id = session.get("user_id")

# Set session
set_session(resp, {"user_id": 123, "theme": "dark"})

# Clear session
clear_session(resp)
```

### Cookie Management

Use Response methods for cookies:

```python
# Set cookie
resp.set_cookie("theme", "dark", max_age=86400)

# Delete cookie
resp.delete_cookie("theme")
```

## Middleware

### Request Middleware

Register middleware that runs on every request:

```python
@app.middleware("request")
def attach_user(req):
    user = current_user(req)
    req.state.user = user
    # Can return Response to short-circuit
    # return Response.redirect("/login")

@app.middleware("request")
def log_requests(req):
    print(f"{req.method} {req.path}")
    # No return = continue processing
```

Middleware functions:

- Receive `Request` object
- Can modify `req.state`
- Can return `Response` to short-circuit
- Run in registration order

## HTMX Support

### HTMX Response Helpers

**`Response.htmx_redirect(location, target="#main")`**

- HTMX redirect (updates URL without reload)

**`Response.htmx_refresh()`**

- HTMX refresh (triggers page refresh)

```python
# HTMX redirect
return Response.htmx_redirect("/dashboard")

# HTMX refresh
return Response.htmx_refresh()
```

### HTMX Template Context

When using `render_htmx`, templates get `htmx` object:

```html
<!-- Check if HTMX request -->
{% if htmx.request %}
<p>This is an HTMX request</p>
{% endif %}

<!-- Use HTMX target -->
<div id="{{ htmx.target }}">Content will be replaced here</div>
```

### HTMX Attributes

Use standard HTMX attributes in templates:

```html
<!-- HTMX form -->
<form hx-post="/todos" hx-target="#todo-list" hx-swap="innerHTML">
  <input name="title" placeholder="New todo" />
  <button>Add</button>
</form>

<!-- HTMX button -->
<button hx-delete="/todos/{{ todo.id }}" hx-target="#todo-list">Delete</button>
```

## CLI Commands

### Application Commands

**`shipy new <name>`**

- Create new Shipy application
- Creates directory structure and basic files

**`shipy dev [--port PORT]`**

- Start development server
- Hot reload on file changes
- Default port: 8000

**`shipy version`**

- Show Shipy version

### Database Commands

**`shipy db init [--db PATH] [--schema PATH]`**

- Initialize database
- Applies schema.sql if present
- Default: `data/app.db`, `data/schema.sql`

**`shipy db run <sql_file> [--db PATH]`**

- Execute SQL script against database
- `sql_file`: Path to .sql file

**`shipy db make-migration <name> [--dir PATH]`**

- Create timestamped migration file
- `name`: Migration name (will be slugified)
- `--dir`: Output directory (default: `data/migrations`)

**`shipy db ls [--dir PATH]`**

- List migration files
- `--dir`: Migrations directory (default: `data/migrations`)

**`shipy db shell [--db PATH]`**

- Open interactive sqlite3 shell
- `--db`: Database path (default: `data/app.db`)

**`shipy db backup [--db PATH] [--out PATH]`**

- Backup database
- `--db`: Source database (default: `data/app.db`)
- `--out`: Output directory (default: `data/backups`)

### Utility Commands

**`shipy gensecret`**

- Generate random secret key
- Use for `SHIPY_SECRET` environment variable

**`shipy deploy emit --domain <domain> [--port PORT] [--user USER] [--workdir PATH]`**

- Generate deployment files
- Creates systemd service and nginx config
- `--domain`: Your domain name
- `--port`: App port (default: 8000)
- `--user`: System user (default: www-data)
- `--workdir`: App directory (default: current)

## Configuration

### Environment Variables

**`SHIPY_DEBUG`**

- Enable debug mode (default: True)
- Set to "0" in production
- Enables detailed error pages

**`SHIPY_SECRET`**

- Secret key for cookie signing
- Generate with `shipy gensecret`
- Default: "dev-secret-change-me"

**`SHIPY_BASE`**

- Application root directory
- Default: current working directory

**`SHIPY_PUBLIC`**

- Public static files directory
- Default: `{SHIPY_BASE}/public`

**`SHIPY_VIEWS`**

- Templates directory
- Default: `{SHIPY_BASE}/app/views`

### Database Configuration

Database path can be set via:

1. `connect("path/to/db")` in code
2. `SHIPY_DB` environment variable
3. Default: `data/app.db`

## Error Handling

### Error Templates

Create custom error pages in `app/views/errors/`:

- `404.html` - Not found
- `500.html` - Server error

### Debug Mode

When `SHIPY_DEBUG=1`:

- Detailed error pages with stack traces
- Auto-reload on file changes
- Less secure (no security headers)

When `SHIPY_DEBUG=0` (production):

- Clean error pages
- Security headers added
- No stack traces exposed

### Error Response

```python
# Custom error response
return Response.text("Not Found", 404)

# HTML error page
return Response.html("<h1>Error</h1>", 500)
```

### Global Error Handling

Shipy automatically handles:

- 404 for unmatched routes
- 405 for wrong HTTP methods
- 403 for CSRF failures
- 500 for unhandled exceptions

## Examples

### Complete CRUD Handler

```python
from shipy.app import App, Response
from shipy.render import render_req, render_htmx
from shipy.sql import query, one, exec, tx
from shipy.forms import Form
from shipy.auth import login_required

app = App()

@app.get("/todos")
@login_required()
def todo_list(req):
    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@app.post("/todos")
@login_required()
async def todo_create(req):
    await req.load_body()
    form = Form(req.form).require("title")

    if not form.ok:
        return render_htmx(req, "todos/form.html", form=form)

    with tx():
        exec("INSERT INTO todos(title, done) VALUES(?, ?)", form["title"], False)

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@app.post("/todos/{id}/toggle")
@login_required()
async def todo_toggle(req):
    todo_id = req.path_params["id"]

    with tx():
        exec("UPDATE todos SET done = NOT done WHERE id = ?", int(todo_id))

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)

@app.delete("/todos/{id}")
@login_required()
async def todo_delete(req):
    todo_id = req.path_params["id"]

    with tx():
        exec("DELETE FROM todos WHERE id = ?", int(todo_id))

    todos = query("SELECT * FROM todos ORDER BY created_at DESC")
    return render_htmx(req, "todos/list.html", todos=todos)
```

### Middleware Example

```python
@app.middleware("request")
def attach_user(req):
    user = current_user(req)
    req.state.user = user

@app.middleware("request")
def log_requests(req):
    print(f"{req.method} {req.path}")

@app.middleware("request")
def maintenance_mode(req):
    if os.getenv("MAINTENANCE_MODE"):
        return Response.html("<h1>Maintenance</h1>", 503)
```

This completes the comprehensive developer API reference for Shipy!
