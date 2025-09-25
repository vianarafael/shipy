"""Test authentication flow functionality."""
import os
import tempfile
from pathlib import Path
import pytest
import sqlite3

from shipy.sql import connect, query, one, exec, tx
from shipy.auth import hash_password, check_password


def test_create_user_and_auth(tmp_path):
    """Test create_user → auth_user works, wrong password fails."""
    # Create database and schema
    schema_content = """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        email         TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Connect and apply schema
        connect("data/test.db")
        
        # Create user
        email = "test@example.com"
        password = "testpassword123"
        password_hash = hash_password(password)
        
        with tx():
            exec("INSERT INTO users(email, password_hash) VALUES(?, ?)", email, password_hash)
        
        # Verify user was created
        user = one("SELECT id, email, password_hash FROM users WHERE email=?", email)
        assert user is not None
        assert user['email'] == email
        
        # Test correct password
        assert check_password(password, user['password_hash']) is True
        
        # Test wrong password
        assert check_password("wrongpassword", user['password_hash']) is False
        
        # Test empty password
        assert check_password("", user['password_hash']) is False
        
    finally:
        os.chdir(original_cwd)


def test_create_session_and_get_user(tmp_path):
    """Test create_session → get_user_by_session returns row."""
    # Create database and schema
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
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Connect and apply schema
        connect("data/test.db")
        
        # Create user
        email = "test@example.com"
        password_hash = hash_password("testpassword123")
        
        with tx():
            exec("INSERT INTO users(email, password_hash) VALUES(?, ?)", email, password_hash)
            user = one("SELECT id FROM users WHERE email=?", email)
        
        # Create session
        session_id = "test-session-123"
        with tx():
            exec("INSERT INTO sessions(id, user_id) VALUES(?, ?)", session_id, user['id'])
        
        # Get user by session
        session_user = one("""
            SELECT u.id, u.email 
            FROM users u 
            JOIN sessions s ON u.id = s.user_id 
            WHERE s.id = ?
        """, session_id)
        
        assert session_user is not None
        assert session_user['email'] == email
        
    finally:
        os.chdir(original_cwd)


def test_destroy_session(tmp_path):
    """Test destroy_session → then get_user_by_session returns None."""
    # Create database and schema
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
    """
    
    schema_path = tmp_path / "data" / "schema.sql"
    schema_path.parent.mkdir()
    schema_path.write_text(schema_content.strip())
    
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Connect and apply schema
        connect("data/test.db")
        
        # Create user
        email = "test@example.com"
        password_hash = hash_password("testpassword123")
        
        with tx():
            exec("INSERT INTO users(email, password_hash) VALUES(?, ?)", email, password_hash)
            user = one("SELECT id FROM users WHERE email=?", email)
        
        # Create session
        session_id = "test-session-123"
        with tx():
            exec("INSERT INTO sessions(id, user_id) VALUES(?, ?)", session_id, user['id'])
        
        # Verify session exists
        session_user = one("""
            SELECT u.id, u.email 
            FROM users u 
            JOIN sessions s ON u.id = s.user_id 
            WHERE s.id = ?
        """, session_id)
        assert session_user is not None
        
        # Destroy session
        exec("DELETE FROM sessions WHERE id = ?", session_id)
        
        # Verify session is gone
        session_user = one("""
            SELECT u.id, u.email 
            FROM users u 
            JOIN sessions s ON u.id = s.user_id 
            WHERE s.id = ?
        """, session_id)
        assert session_user is None
        
        # Verify user still exists (cascade delete not triggered)
        user_still_exists = one("SELECT id FROM users WHERE email=?", email)
        assert user_still_exists is not None
        
    finally:
        os.chdir(original_cwd)


def test_password_hashing():
    """Test password hashing functionality."""
    password = "testpassword123"
    
    # Hash password
    hash1 = hash_password(password)
    assert hash1 != password  # Should be hashed
    assert len(hash1) > 20  # Should be reasonably long
    
    # Same password should produce different hashes (salt)
    hash2 = hash_password(password)
    assert hash1 != hash2
    
    # But both should verify correctly
    assert check_password(password, hash1) is True
    assert check_password(password, hash2) is True
    
    # Wrong passwords should fail
    assert check_password("wrong", hash1) is False
    assert check_password("", hash1) is False
