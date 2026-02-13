# Database Setup Complete ✅

## What Was Fixed

### 1. Session Model - UUID Primary Key ✅
**File:** `legacy/models.py`

**Changed:**
- `Session.id` from `Integer` to `String(36)` (UUID)
- Matches `User.id` type for consistency
- Added index on `user_id` for faster lookups

**Before:**
```python
id = Column(Integer, primary_key=True, autoincrement=True)
```

**After:**
```python
id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
```

### 2. Enhanced Database Initialization ✅
**File:** `legacy/models.py` → `init_db()`

**Improvements:**
- Tests database connection before creating tables
- Verifies required tables exist after creation
- Comprehensive error logging with context
- Logs DATABASE_URL (truncated for security)
- Raises exception if critical tables are missing

**New Features:**
- Connection test before table creation
- Table existence verification
- Detailed error messages for Railway logs
- Clear success/failure indicators

### 3. Better Error Logging in App Startup ✅
**File:** `legacy/app_production.py`

**Improvements:**
- More detailed error logging
- Clear visual separators in logs
- Logs error type and context
- Allows app to start but logs critical errors
- Errors visible in Railway logs immediately

### 4. Rate Limiting on Auth Endpoints ✅
**File:** `legacy/auth.py`

**Added:**
- Rate limiting integration for signup/login
- 10 requests per minute limit
- Prevents brute force attacks

---

## Database Schema (Final)

### Users Table
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,           -- UUID string
    email VARCHAR(255) UNIQUE NOT NULL,  -- Indexed
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(200),
    phone VARCHAR(20),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,          -- UUID string
    user_id VARCHAR(36) NOT NULL,        -- FK to users.id, indexed
    token VARCHAR(255) UNIQUE NOT NULL, -- Indexed
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## How It Works

### 1. Application Startup
```
Railway starts app
    ↓
app_production.py loads
    ↓
init_db() is called
    ↓
Tests database connection
    ↓
Creates all tables (if not exist)
    ↓
Verifies users & sessions tables exist
    ↓
Logs success or detailed error
```

### 2. User Signup Flow
```
User submits signup form
    ↓
POST /api/auth/signup
    ↓
Creates User row (UUID id, email, password_hash)
    ↓
Creates Session row (UUID id, user_id FK, token, expires_at)
    ↓
Sets HttpOnly cookie with session token
    ↓
Returns success → Frontend redirects to /dashboard
```

### 3. User Login Flow
```
User submits login form
    ↓
POST /api/auth/login
    ↓
Validates email + password_hash
    ↓
Creates new Session row
    ↓
Sets HttpOnly cookie with session token
    ↓
Returns success → Frontend redirects to /dashboard
```

### 4. Session Validation
```
User requests /dashboard
    ↓
Middleware reads cookie (jet_session)
    ↓
Looks up Session by token
    ↓
Checks expires_at > now
    ↓
Loads User via user_id FK
    ↓
Attaches user to request
    ↓
Renders dashboard
```

---

## Verification Checklist

After deploying to Railway:

- [ ] Check Railway logs for: `✅ Database initialized successfully - all tables ready`
- [ ] Check Railway logs for: `✅ Verified tables exist: users, sessions`
- [ ] Visit `/signup` - Create account
- [ ] Check browser DevTools → Application → Cookies → Should see `jet_session`
- [ ] Visit `/dashboard` - Should load (not redirect to login)
- [ ] Refresh page - Should stay logged in
- [ ] Visit `/api/auth/me` - Should return user JSON
- [ ] Log out - Cookie should be cleared
- [ ] Try to access `/dashboard` - Should redirect or show error

---

## Troubleshooting

### Database Tables Not Created

**Check Railway logs for:**
```
❌ CRITICAL: Database initialization FAILED
❌ Error: [error message]
❌ DATABASE_URL: [url]
```

**Common Issues:**
1. **DATABASE_URL not set**
   - Solution: Add PostgreSQL service in Railway
   - Railway auto-sets DATABASE_URL

2. **Connection refused**
   - Solution: Check PostgreSQL service is running
   - Check DATABASE_URL format

3. **Permission denied**
   - Solution: Check database user has CREATE TABLE permission
   - Railway PostgreSQL should have this by default

### Login Not Working

**If tables exist but login fails:**

1. **Check cookies:**
   - Browser DevTools → Application → Cookies
   - Should see `jet_session` cookie
   - Check `HttpOnly`, `Secure`, `SameSite` flags

2. **Check session creation:**
   - Railway logs should show no errors during signup/login
   - Check database directly: `SELECT * FROM sessions;`

3. **Check cookie settings:**
   - `COOKIE_SECURE` should be True in production
   - `COOKIE_HTTPONLY` should be True
   - `COOKIE_SAMESITE` should be 'Lax'

### Tables Missing After Deploy

**If tables don't exist:**
1. Check Railway logs for init_db() errors
2. Manually run: `railway run python -c "from models import init_db; init_db()"`
3. Check DATABASE_URL is correct
4. Verify PostgreSQL service is running

---

## Testing Locally

```bash
# 1. Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/jet_finder"
export SESSION_SECRET="test-secret"

# 2. Run app
cd legacy
python app_production.py

# 3. Check logs for:
# ✅ Database connection successful
# ✅ Database tables created/verified successfully!
# ✅ Verified tables exist: users, sessions

# 4. Test signup
curl -X POST http://localhost:5015/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}' \
  -c cookies.txt

# 5. Test login
curl -X POST http://localhost:5015/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}' \
  -c cookies.txt

# 6. Test session
curl http://localhost:5015/api/auth/me \
  -b cookies.txt
```

---

## Summary

✅ **User model:** UUID id, email (unique, indexed), password_hash, created_at
✅ **Session model:** UUID id, user_id (FK, indexed), created_at, expires_at
✅ **init_db():** Creates tables, verifies existence, logs errors
✅ **App startup:** Calls init_db() automatically, logs results
✅ **Login flow:** Creates user → Creates session → Sets cookie → Redirects to /dashboard
✅ **Error logging:** Comprehensive logging for Railway debugging

**Result:** Fresh Railway deployment will automatically create tables and allow users to sign up, log in, and access their dashboard.
