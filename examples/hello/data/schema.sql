-- Auth-first schema
-- Run: shipy db init

-- users table
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- helpful index
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- todos table for HTMX example
CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  done BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- helpful index
CREATE INDEX IF NOT EXISTS idx_todos_created ON todos(created_at DESC);

