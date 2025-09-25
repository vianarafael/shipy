Shipy: The opinionated indie-maker Python web framework for shipping MVPs stupid-fast.

    •	The Philosophy behind the framework:
    •	Taste > config. Defaults you’re proud of beat endless options.
    •	A tight scope. One way for routing, rendering, data access, forms/sessions/auth, static assets and deployment.
    •	Convention over configuration. Predictable files, folders, helper names.
    •	A tiny CLI. Scaffolds apps and keeps you on the default (the official way to do ~90% of things).
    •	Server-rendered HTML by default. JSON is an edge can, `json()` is a helper.
    •	SQLite by default. Raw SQL helpers that return dicts, teach the real fundamentals.
    •	No build step. Edit file → reload → see it.

    •	Non-negotiable principles
    1.	HTML-first: `render(“template.html”, ctx) is primary return.
    2.	Simple data: SQLite + `query/one/exec/tx` helpers. Transactions by default. (Migrations optional later.)
    3.	Fast dev loop. `ships dev` runs auto-reload server. Zero build.
    4.	One way to do it: A single templating engine (Jinja2). One router.  One session mechanism (signed cookies). One auth pattern (cookie-session auth with email + password (crypt), plus CSRF).
    5.	Beginner-friendly: APIs read like English. No decorator gymnastics. No Pydantic/type bureaucracy.

Note on decorators: To keep things obvious for first-timers, Ships uses imperative route registration (no decorators).

Defaults that teach fundamentals (and don’t apologize)
• Routing: Explicit, readable, function routes.
• Templates: Jinja2 (tiny subset: variables, if, for, include).
• State: Cookie-based session (signed). Teach what a cookie/session is.
• Data: Plain SQL. Transactions. Add indexes when needed. Students see the DB
• Assets: Vanilla CSS in `/public`. If you need JS, write a `<script>` for the one thing you need. (HTMX via CDN is optional, but recommended - self host it for deployment)
• default shipy dev to read app.main:app so the flag isn’t needed in new projects.
