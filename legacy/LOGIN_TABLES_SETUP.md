# Login Tables Setup for Railway PostgreSQL

## ✅ Status: Ready for Deployment

PostgreSQL tables for login (users and sessions) are configured and will be created automatically on Railway deployment.

## Tables Created

### 1. `users` Table
Stores user accounts with encrypted passwords:
- `id` - UUID primary key
- `email` - Unique, indexed (login identifier)
- `password_hash` - **Encrypted password** (PBKDF2 with SHA-256)
- `is_admin` - Boolean flag
- `first_name`, `last_name`, `company`, `phone` - Optional info
- `created_at`, `updated_at` - Timestamps

### 2. `sessions` Table
Stores active login sessions:
- `id` - UUID primary key
- `user_id` - Foreign key to users (cascade delete)
- `token` - Secure random token (stored in HttpOnly cookie)
- `expires_at` - Session expiration
- `created_at` - Creation timestamp

## Password Encryption

**Security:** Passwords are NEVER stored in plaintext.

**Method:** Werkzeug's PBKDF2
- Algorithm: PBKDF2 with SHA-256
- Iterations: 260,000 (Werkzeug default)
- Salt: Unique per password (auto-generated)
- Format: `pbkdf2:sha256:260000$salt$hash`

**Code:**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Signup - hash password
password_hash = generate_password_hash(password)

# Login - verify password
if check_password_hash(user.password_hash, password):
    # Password correct
```

## Automatic Table Creation

Tables are created automatically when the app starts on Railway:

1. **App starts** → `legacy/app_production.py` loads
2. **Calls `init_db()`** → `legacy/models.py`
3. **Creates tables** → `Base.metadata.create_all(bind=engine)`
4. **Verifies tables** → Checks `users` and `sessions` exist
5. **Logs success** → Railway logs show completion

**No manual SQL needed!**

## Manual Migration (Optional)

If you want to run the SQL migration manually:

```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Run migration
psql $DATABASE_URL -f legacy/migrations/004_login_tables.sql
```

Or use the migration runner:
```bash
python legacy/migrations/run_migrations.py
```

## Verification After Deployment

### Check Railway Logs
You should see:
```
✅ DATABASE INITIALIZATION STARTING
✅ Database connection successful
✅ Database tables created/verified successfully!
✅ Verified tables exist: users, sessions
✅ DATABASE INITIALIZATION COMPLETE
```

### Test Login Flow
1. **Signup:** Visit `/signup` → Creates user in `users` table
2. **Login:** Visit `/login` → Creates session in `sessions` table
3. **Dashboard:** Should redirect to `/dashboard` after login

### Verify in PostgreSQL
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN ('users', 'sessions');

-- Check user was created (after signup)
SELECT id, email, is_admin, created_at FROM users;

-- Check session was created (after login)
SELECT id, user_id, expires_at, created_at FROM sessions;
```

## Security Features

✅ **Password Hashing:** PBKDF2 with SHA-256, 260,000 iterations  
✅ **Unique Salts:** Each password has unique salt  
✅ **Session Tokens:** Cryptographically secure (`secrets.token_urlsafe(32)`)  
✅ **HttpOnly Cookies:** Tokens stored in HttpOnly cookies (XSS protection)  
✅ **Secure Cookies:** HTTPS-only in production  
✅ **Cascade Delete:** Sessions deleted when user deleted  
✅ **Indexed Queries:** Fast email and token lookups  
✅ **Rate Limiting:** Signup/login rate limited (10 per minute)  

## Files

- **`legacy/models.py`** - SQLAlchemy models (User, Session)
- **`legacy/migrations/004_login_tables.sql`** - SQL migration file
- **`legacy/migrations/004_LOGIN_TABLES_README.md`** - Detailed documentation
- **`legacy/auth.py`** - Authentication endpoints (signup, login, logout)

## Next Steps

1. ✅ Tables are defined in code
2. ✅ Migration SQL file created
3. ✅ Committed to GitHub
4. 🔄 **Deploy on Railway** - Tables will be created automatically
5. ✅ Test signup/login flow

**Ready for Railway deployment!**
