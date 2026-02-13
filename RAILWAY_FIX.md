# Railway Entrypoint Fix

## Problem
Railway was running `gunicorn app:app` instead of the production app `legacy/app_production.py`, causing:
- Database initialization never ran
- Flask-CORS not installed (wrong requirements.txt)
- App breaking on Railway but working locally

## Solution

### 1. Root `requirements.txt`
**Changed to:** `-r legacy/requirements_production.txt`

This ensures Railway installs all production dependencies including Flask-CORS.

### 2. Root `Procfile`
**Changed to:** `web: cd legacy && gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

This ensures:
- Railway runs the correct production app (`legacy/app_production.py`)
- Working directory is `legacy/` so relative imports work (`from security import ...`)
- Database initialization code runs on startup

## Why This Works

1. **`cd legacy`** - Changes working directory to `legacy/` before starting gunicorn
2. **`app_production:app`** - Runs the production Flask app (not `app.py`)
3. **Relative imports work** - Since we're in `legacy/` directory, `from security import ...` finds `legacy/security.py`

## Expected Behavior After Deploy

1. Railway installs dependencies from `legacy/requirements_production.txt` (including Flask-CORS)
2. Railway runs `cd legacy && gunicorn app_production:app ...`
3. `app_production.py` loads and calls `init_db()`
4. Database tables are created automatically
5. App starts successfully

## Verification

After deployment, check Railway logs for:
```
Collecting Flask-CORS==4.0.0
✅ Database initialization complete
✅ API blueprints registered
```
