"""Test database bootstrap and schema application."""
import os
import tempfile
from pathlib import Path
import pytest
import sqlite3

from shipy.sql import connect, query, ensure_schema


def test_schema_applies_on_fresh_db(tmp_path):
    """Ensure schema applies on a tmp dir with fresh DB."""
    # Create a temporary schema file
    schema_content = """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        email         TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id         TEXT PRIMARY KEY,
        user_id    INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    # Change to temp directory so ensure_schema finds the schema file
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Use connect() which will set up the global connection and apply schema
        connect("data/test.db")
        
        # Verify users table exists
        tables = query("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert len(tables) == 1
        assert tables[0]['name'] == 'users'
        
        # Verify sessions table exists
        sessions = query("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        assert len(sessions) == 1
        assert sessions[0]['name'] == 'sessions'
        
        # Verify index exists
        indexes = query("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_email'")
        assert len(indexes) == 1
        assert indexes[0]['name'] == 'idx_users_email'
        
    finally:
        os.chdir(original_cwd)


def test_connect_auto_applies_schema(tmp_path):
    """Test that connect() automatically applies schema."""
    # Create schema file
    schema_content = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    # Change to temp directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Connect should auto-apply schema
        connect("data/test.db")
        
        # Verify table was created
        tables = query("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert len(tables) == 1
        
    finally:
        os.chdir(original_cwd)


def test_schema_idempotent(tmp_path):
    """Test that applying schema multiple times doesn't cause errors."""
    schema_content = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE
    );
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Apply schema multiple times
        ensure_schema()
        ensure_schema()  # Should not error
        ensure_schema()  # Should not error
        
        # Verify table still exists
        tables = query("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert len(tables) == 1
        
    finally:
        os.chdir(original_cwd)
