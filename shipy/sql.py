import sqlite3, contextlib
from dataclasses import dataclass 
from pathlib import Path

_con = None 

def connect(path="data/app.db"):
    global _con 
    # Ensure directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _con = sqlite3.connect(path, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
    _con.row_factory = sqlite3.Row 
    _con.execute("PRAGMA foreign_keys=ON;")
    _con.execute("PRAGMA journal_mode=WAL;")
    _con.execute("PRAGMA busy_timeout=3000;")
    # Auto-apply schema on first connection (idempotent)
    ensure_schema()
    return _con

def ensure_schema():
    """Auto-apply schema.sql on first connection (idempotent)"""
    if _con is None:
        return
    schema_path = Path("data/schema.sql")
    if schema_path.exists():
        try:
            _con.executescript(schema_path.read_text(encoding="utf-8"))
        except sqlite3.Error:
            pass  # Already applied or error - continue 

@dataclass 
class ExecResult:
    rowcount: int
    last_id: int | None 

def _cur():
    if _con is None: connect()
    return _con 

def query(sql, *args):
    cur = _cur().execute(sql, args)
    return [dict(r) for r in cur.fetchall()]

def one(sql, *args):
    rows = query(sql, *args)
    if len(rows) > 1: raise ValueError("one() got %d rows" %len(rows))
    return rows[0] if rows else None 

def exec(sql, *args):
    cur = _cur().execute(sql, args)
    return ExecResult(rowcount=cur.rowcount, last_id=cur.lastrowid)

@contextlib.contextmanager 
def tx():
    try:
        _cur().execute("BEGIN")
        yield
        _cur().execute("COMMIT")
    except Exception:
        _cur().execute("ROLLBACK")
        raise 
