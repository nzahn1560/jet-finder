# Login Tables Migration - PostgreSQL

## Overview

This migration creates the `users` and `sessions` tables for secure login functionality on Railway PostgreSQL.

## Password Encryption

**Important:** Passwords are NEVER stored in plaintext. They are hashed using:

- **Werkzeug's PBKDF2** (default in Flask)
- Uses `generate_password_hash()` and `check_password_hash()` from `werkzeug.security`
- PBKDF2 with SHA-256, 260,000 iterations (Werkzeug default)
- Salt is automatically generated and stored with the hash

### How It Works

1. **Signup:**
   ```python
   password_hash = generate_password_hash(password)
   # Stores: pbkdf2:sha256:260000$salt$hash
   ```

2. **Login:**
   ```python
   if check_password_hash(user.password_hash, password):
       # Password matches
   ```

3. **Storage:**
   - Password hash format: `pbkdf2:sha256:260000$salt$hash`
   - Salt is unique per password
   - Hash cannot be reversed (one-way function)

## Tables Created

### `users` Table
- `id` - UUID primary key
- `email` - Unique, indexed (login identifier)
- `password_hash` - Encrypted password (PBKDF2)
- `is_admin` - Boolean flag for admin users
- `first_name`, `last_name`, `company`, `phone` - Optional user info
- `created_at`, `updated_at` - Timestamps

### `sessions` Table
- `id` - UUID primary key
- `user_id` - Foreign key to users (cascade delete)
- `token` - Secure random token (stored in HttpOnly cookie)
- `expires_at` - Session expiration timestamp
- `created_at` - Session creation timestamp

## Running the Migration

### Option 1: Automatic (Recommended)
Tables are created automatically when the app starts via `init_db()` in `legacy/models.py`.

### Option 2: Manual SQL
```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Or use psql
psql $DATABASE_URL -f legacy/migrations/004_login_tables.sql
```

### Option 3: Migration Runner
```bash
python legacy/migrations/run_migrations.py
```

## Security Features

✅ **Password Hashing:** PBKDF2 with SHA-256, 260,000 iterations  
✅ **Unique Salts:** Each password has a unique salt  
✅ **Session Tokens:** Cryptographically secure random tokens  
✅ **HttpOnly Cookies:** Session tokens stored in HttpOnly cookies (not accessible via JavaScript)  
✅ **Secure Cookies:** HTTPS-only in production (Railway)  
✅ **Cascade Delete:** Sessions deleted when user is deleted  
✅ **Indexed Queries:** Email and token indexes for fast lookups  

## Verification

After migration, verify tables exist:
```sql
-- Check tables
\dt

-- Check users table structure
\d users

-- Check sessions table structure
\d sessions

-- Verify indexes
\di
```

## Usage in Code

### Create User (Signup)
```python
from werkzeug.security import generate_password_hash
password_hash = generate_password_hash(password)
user = User(email=email, password_hash=password_hash)
```

### Verify Password (Login)
```python
from werkzeug.security import check_password_hash
if check_password_hash(user.password_hash, password):
    # Password correct - create session
```

### Create Session
```python
session = Session.create_for_user(user.id)
# Token is stored in HttpOnly cookie
```

## Notes

- **Never store plaintext passwords** - Always use `generate_password_hash()`
- **Never log passwords** - Even in error messages
- **Session tokens** are generated using `secrets.token_urlsafe(32)` (cryptographically secure)
- **Password requirements:** Minimum 8 characters (enforced in signup endpoint)
