# Development Guide

## Manual Smoke Test

This test verifies the complete auth-first scaffold works end-to-end.

### Prerequisites

```bash
# Install shipy-web (development version)
pip install -e .

# Or install from PyPI
pip install shipy-web
```

### Smoke Test Steps

1. **Create demo project:**

   ```bash
   mkdir /tmp/shipy-demo && cd /tmp/shipy-demo
   shipy new demo && cd demo
   ```

2. **Initialize database:**

   ```bash
   shipy db init
   ```

   Expected output:

   ```
   🗄️  Database: /tmp/shipy-demo/demo/data/app.db
   📋 Schema: data/schema.sql ✅ found
   ✅ DB initialized successfully
   ```

3. **Start development server:**

   ```bash
   shipy dev
   ```

   Expected output:

   ```
   🚀 Shipy dev server starting...
   📁 App root: /tmp/shipy-demo/demo
   🗄️  Database: data/app.db
   📋 Schema: data/schema.sql ✅ present
   🌐 URL: http://127.0.0.1:8000
   Press Ctrl+C to stop

   INFO:     Started server process [xxxxx]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   ```

4. **Test authentication flow in browser:**

   **Visit http://localhost:8000**

   - Should redirect to `/login` (since not authenticated)
   - Should show login form with link to `/signup`

   **Sign up:**

   - Click "Sign up" link
   - Fill form: email=`test@example.com`, password=`secret`
   - Submit form
   - Should redirect to `/` and show: "Hi, test@example.com! You're successfully logged in."

   **Logout:**

   - Click "Logout" link
   - Should redirect to `/login` page
   - Visit `/` again → redirects back to login (session destroyed)

5. **Test schema auto-application:**

   ```bash
   # Stop server (Ctrl+C)
   # Delete database
   rm data/app.db

   # Start server again
   shipy dev
   ```

   Expected output should show schema auto-applied on startup:

   ```
   🚀 Shipy server starting...
   📁 Project root: /tmp/shipy-demo/demo
   🗄️  Database: data/app.db
   📋 Schema: data/schema.sql ✅ found
   ✅ Schema applied successfully
   ```

   **Verify database recreated:**

   - Visit http://localhost:8000
   - Sign up with same email (`test@example.com`)
   - Should work (user table recreated)

### Environment Variable Testing

Test database path override:

```bash
# In demo directory
SHIPY_DB=/tmp/custom.db shipy dev
```

Expected output:

```
🗄️  Database: /tmp/custom.db
📋 Schema: data/schema.sql ✅ found
✅ Schema applied successfully
```

Verify custom database location:

```bash
ls -la /tmp/custom.db
```

### CLI Commands Testing

```bash
# Show database path
shipy db path

# Backup database
shipy db backup

# Initialize with custom paths
shipy db init --db /tmp/test.db --schema data/schema.sql
```

### Troubleshooting

**Database not found:**

- Ensure you're in the project directory
- Check `data/schema.sql` exists
- Run `shipy db init` first

**Schema not applying:**

- Check `data/schema.sql` syntax
- Verify file permissions
- Check server logs for SQL errors

**Authentication not working:**

- Verify `SHIPY_SECRET` environment variable (optional, has default)
- Check browser cookies are enabled
- Clear browser cookies and try again

**Port already in use:**

```bash
shipy dev --port 8001
```

### Expected File Structure

After successful smoke test:

```
/tmp/shipy-demo/demo/
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── views/
│       ├── home/
│       │   └── index.html
│       ├── sessions/
│       │   └── login.html
│       ├── users/
│       │   └── new.html
│       └── errors/
│           ├── 404.html
│           └── 500.html
├── data/
│   ├── app.db          # SQLite database
│   └── schema.sql      # Database schema
└── public/
    └── base.css        # Default styles
```

### Success Criteria

✅ All smoke test steps complete without errors  
✅ Authentication flow works (signup → login → logout)  
✅ Schema auto-applies on fresh database  
✅ Environment variables override defaults  
✅ CLI commands show correct paths and status  
✅ Server logs show helpful boot information

If all criteria pass, the auth-first scaffold is working correctly.
