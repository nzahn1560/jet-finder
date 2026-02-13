# Railway Start Command - Manual Override

## Problem
Railway is still running `gunicorn app:app` instead of the production app, even after Procfile fix.

## Solution: Set Start Command Manually in Railway Dashboard

### Steps:
1. Go to Railway Dashboard
2. Click on your **Jetschool** service
3. Go to **Settings** tab
4. Scroll to **"Start Command"** section
5. Set it to:
   ```
   cd legacy && gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```
6. Click **Save**
7. Railway will automatically redeploy

### Alternative (if cd doesn't work):
If Railway doesn't support `cd` in the start command, use:
```
gunicorn legacy.app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**BUT** this requires updating imports in `legacy/app_production.py` to use `from legacy.security import ...` instead of `from security import ...`

## Verify Deployment

After setting the start command, check Railway logs for:
- ✅ Should see: `Starting gunicorn app_production:app`
- ✅ Should see: `✅ DATABASE INITIALIZATION COMPLETE`
- ❌ Should NOT see: `Starting gunicorn app:app`

## Current Procfile (Repo Root)

```
web: cd legacy && gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

This is committed and pushed, but Railway may be using a cached build or ignoring it.
