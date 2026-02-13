# Authentication System - Railway Production

## Overview

This application uses **cookie-based session authentication** with PostgreSQL for production deployment on Railway.

## Features

✅ **Email + Password Authentication**
- Passwords hashed with `werkzeug.security` (bcrypt-based)
- Email uniqueness enforced at database level
- Minimum 8 character password requirement

✅ **Secure Cookie Sessions**
- HttpOnly cookies (prevents XSS attacks)
- Secure flag enabled in production (HTTPS only)
- SameSite=Lax (CSRF protection)
- 30-day session expiration
- Random 32-byte session tokens

✅ **Database Storage**
- PostgreSQL on Railway (via `DATABASE_URL`)
- Users table with UUID primary keys
- Sessions table with automatic expiration cleanup
- Foreign key constraints for data integrity

## API Endpoints

### `POST /api/auth/signup`
Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201):**
```json
{
  "message": "Account created successfully",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "is_admin": false,
    ...
  }
}
```

**Sets cookie:** `jet_session=<token>`

### `POST /api/auth/login`
Log in with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "user": { ... }
}
```

**Sets cookie:** `jet_session=<token>`

### `POST /api/auth/logout`
Log out current user.

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

**Clears cookie:** `jet_session`

### `GET /api/auth/me`
Get current logged-in user.

**Requires:** Valid session cookie

**Response (200):**
```json
{
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "is_admin": false,
    ...
  }
}
```

**Response (401):** If not logged in

## Running Locally

1. **Install dependencies:**
   ```bash
   cd legacy
   pip install -r requirements_production.txt
   ```

2. **Set environment variables:**
   ```bash
   export DATABASE_URL="sqlite:///instance/jet_finder.db"  # Local SQLite
   export SESSION_SECRET="your-random-secret-key-here"
   export FLASK_ENV="development"
   ```

3. **Initialize database:**
   ```bash
   python -c "from models import init_db; init_db()"
   ```

4. **Run the app:**
   ```bash
   python app_production.py
   ```

5. **Access:**
   - Frontend: http://localhost:5015
   - Signup: http://localhost:5015/signup
   - Login: http://localhost:5015/login

## Railway Deployment

### Required Environment Variables

Set these in Railway dashboard → Variables:

1. **`DATABASE_URL`** (Auto-set by Railway)
   - Railway automatically provides this when you add a PostgreSQL service
   - Format: `postgresql://user:pass@host:port/dbname`

2. **`SESSION_SECRET`** (Required)
   - Generate a random secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Used to sign Flask sessions
   - **Keep this secret!** Never commit to git.

3. **`APP_BASE_URL`** (Optional, but recommended)
   - Your Railway app URL: `https://your-app.up.railway.app`
   - Used for CORS configuration
   - If not set, CORS allows all origins (development mode)

4. **`FLASK_ENV`** or **`NODE_ENV`** (Optional)
   - Set to `production` to enable secure cookies
   - Railway may set this automatically

### Database Setup

1. **Add PostgreSQL service in Railway:**
   - Railway Dashboard → Your Project → New → Database → PostgreSQL
   - Railway automatically sets `DATABASE_URL`

2. **Initialize database tables:**
   - Tables are created automatically on first app startup via `init_db()`
   - Or run migrations manually:
     ```bash
     cd legacy
     python migrations/run_migrations.py
     ```

3. **Create admin user (optional):**
   ```bash
   export ADMIN_EMAIL="admin@example.com"
   export ADMIN_PASSWORD="SecurePassword123!"
   python migrations/run_migrations.py  # Includes admin seeding
   ```

### Deployment Checklist

- [ ] PostgreSQL service added to Railway project
- [ ] `DATABASE_URL` is set (auto-set by Railway)
- [ ] `SESSION_SECRET` is set (generate random value)
- [ ] `APP_BASE_URL` is set to your Railway domain
- [ ] `FLASK_ENV=production` or `NODE_ENV=production` is set
- [ ] Database tables initialized (automatic on startup)
- [ ] Test signup/login flow
- [ ] Verify cookies are set (check browser DevTools → Application → Cookies)
- [ ] Test session persistence (refresh page, should stay logged in)

## Security Notes

1. **Cookies:**
   - `HttpOnly=True` prevents JavaScript access (XSS protection)
   - `Secure=True` in production (HTTPS only)
   - `SameSite=Lax` prevents CSRF attacks
   - 30-day expiration

2. **Passwords:**
   - Never stored in plain text
   - Hashed with `werkzeug.security.generate_password_hash()`
   - Minimum 8 characters required

3. **Sessions:**
   - Random 32-byte tokens (URL-safe)
   - Stored in database with expiration
   - Automatically cleaned up on validation

4. **Database:**
   - Use prepared statements (SQLAlchemy handles this)
   - Foreign key constraints prevent orphaned records
   - UUID primary keys for users (better security)

## Troubleshooting

### "Authentication required" errors
- Check that cookies are being sent: Browser DevTools → Network → Request Headers → Cookie
- Verify `credentials: 'include'` in all fetch calls
- Check cookie domain/path settings

### Cookies not persisting
- Verify `Secure` flag matches your environment (HTTPS in production)
- Check browser console for cookie warnings
- Ensure `SameSite` is set correctly

### Database connection errors
- Verify `DATABASE_URL` is set correctly
- Check Railway PostgreSQL service is running
- Ensure database tables are initialized

### CORS errors
- Set `APP_BASE_URL` to your Railway domain
- Verify frontend and API are on same origin (single origin is best)
- Check CORS configuration in `app_production.py`

## Testing

### Manual Tests

1. **Signup:**
   ```bash
   curl -X POST http://localhost:5015/api/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test1234"}' \
     -c cookies.txt
   ```

2. **Login:**
   ```bash
   curl -X POST http://localhost:5015/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test1234"}' \
     -c cookies.txt
   ```

3. **Get current user:**
   ```bash
   curl http://localhost:5015/api/auth/me \
     -b cookies.txt
   ```

4. **Logout:**
   ```bash
   curl -X POST http://localhost:5015/api/auth/logout \
     -b cookies.txt \
     -c cookies.txt
   ```

### Acceptance Tests

✅ **Signup then login works**
- Create account → Log in → Should succeed

✅ **Refresh page stays logged in**
- Log in → Refresh page → Should still be logged in

✅ **Logout works**
- Log in → Log out → Should not be able to access `/api/auth/me`

✅ **Wrong password fails**
- Try login with wrong password → Should get 401 error

✅ **Two different users have separate sessions**
- User A logs in → User B logs in → Each has separate session
