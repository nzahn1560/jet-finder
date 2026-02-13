-- Migration: Create Login Tables for Railway PostgreSQL
-- This creates users and sessions tables with proper encryption support
-- Run this on Railway PostgreSQL database

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- USERS table - stores user accounts with encrypted passwords
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,  -- Bcrypt/Argon2 hashed password (never store plaintext)
    is_admin BOOLEAN NOT NULL DEFAULT false,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(200),
    phone VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- SESSIONS table - stores active login sessions
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,  -- Secure random token for cookie
    expires_at TIMESTAMPTZ NOT NULL,      -- Session expiration time
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts with encrypted password storage';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt/Argon2 hashed password - never store plaintext';
COMMENT ON TABLE sessions IS 'Active user login sessions with secure tokens';
COMMENT ON COLUMN sessions.token IS 'Cryptographically secure random token stored in HttpOnly cookie';
