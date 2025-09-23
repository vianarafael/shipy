from __future__ import annotations
import argparse, os, sqlite3
from pathlib import Path
from typing import Optional
from shipy.sql import connect as sql_connect

def cmd_db_init(db_path: str = "db/app.sqlite", schema_path: str = "db/schema.sql") -> int:
    con = sql_connect(db_path) # <- reuse the same PRAMAs/row_factory logic
    schema = Path(schema_path)
    if schema.exists():
        con.executescript(schema.read_text(encoding="utf-8"))
        print(f"DB initialized at {db_path} (schema: {schema_path})")
    else:
        print(f"DB created at {db_path} (no schema.sql found)")
    return 0

def cmd_dev(app_ref: str, host: str, port: int, reload: bool, workers: int) -> int:
    os.environ.setdefault("SHIPY_BASE", os.getcwd()) # helps you render() find ./app/views
    try:
        import uvicorn
    except Exception as e:
        print("Uvicorn is required. Install with: pip install 'uvicorn[standard]'", e)
        return 2
    # 1 worker while developing (breakpoints etc.)
    uvicorn.run(app_ref, host=host, port=port, reload=reload, workers=workers)
    return 0

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="shipy", description="Shipy CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_dev = sub.add_parser("dev", help="Run dev server")
    p_dev.add_argument("--app", default="app.main:app", help="ASGI app path, e.g. app.main:app")
    p_dev.add_argument("--host", default="127.0.0.1")
    p_dev.add_argument("--port", type=int, default=8000)
    p_dev.add_argument("--reload", action="store_true", default=True)
    p_dev.add_argument("--no-reload", dest="reload", action="store_false")
    p_dev.add_argument("--workers", type=int, default=1)

    p_db = sub.add_parser("db", help="Database utilities")
    p_db_sub = p_db.add_subparsers(dest="db_cmd", required=True)
    p_db_init = p_db_sub.add_parser("init", help="Create SQLite and run schema.sql (if present)")
    p_db_init.add_argument("--db", default="db/app.sqlite")
    p_db_init.add_argument("--schema", default="db/schema.sql")

    args = p.parse_args(argv)

    if args.cmd == "dev":
        return cmd_dev(args.app, args.host, args.port, args.reload, args.workers)
    
    if args.cmd == "db" and args.db_cmd == "init":
        return cmd_db_init(args.db, args.schema)
    
    p.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())