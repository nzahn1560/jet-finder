# Railway Root Directory Fix

## Problem
Railway (Railpack) always tries to install `requirements.txt` first. The build was failing because:
- Root `requirements.txt` contains `-r legacy/requirements_production.txt`
- Railway can't find that file in the build context
- App never reaches "start" step

## Solution: Set Railway Root Directory to `legacy/`

### Step 1: Railway Dashboard Settings
1. Go to Railway Dashboard
2. Click on your **Jetschool** service
3. Go to **Settings** tab
4. Set **Root Directory** to: `legacy`
5. Save

### Step 2: Files Created
✅ **`legacy/requirements.txt`** - Copy of `legacy/requirements_production.txt`
   - Railway will run `pip install -r requirements.txt` from `legacy/` directory
   - This installs all production dependencies including Flask-CORS

✅ **`legacy/Procfile`** - Start command for Railway
   - `web: gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
   - Railway will auto-detect this Procfile when root is `legacy/`

### Step 3: Railway Settings (After Setting Root Directory)
- **Root Directory:** `legacy` ✅
- **Build Command:** (leave blank - Railway auto-detects)
- **Start Command:** (leave blank - Railway uses Procfile)

OR manually set:
- **Start Command:** `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

## Why This Works

1. **Root Directory = `legacy/`**
   - Railway builds from `legacy/` directory
   - All file paths are relative to `legacy/`

2. **`legacy/requirements.txt` exists**
   - Railway runs `pip install -r requirements.txt` from `legacy/`
   - Finds `requirements.txt` in current directory
   - Installs all dependencies

3. **`legacy/Procfile` exists**
   - Railway auto-detects Procfile in root directory (`legacy/`)
   - Runs `gunicorn app_production:app` (relative to `legacy/`)
   - All imports work because we're in `legacy/` directory

## Verification

After setting root directory and redeploying, check Railway logs:

```
Collecting Flask==3.0.0
Collecting Flask-CORS==4.0.0
...
Successfully installed Flask-CORS-4.0.0
...
✅ DATABASE INITIALIZATION COMPLETE
✅ API blueprints registered
```

## Files Status

- ✅ `legacy/requirements.txt` - Created (copy of requirements_production.txt)
- ✅ `legacy/Procfile` - Created with correct start command
- ✅ Root `Procfile` - Can be ignored (Railway uses legacy/Procfile when root is legacy/)

## Alternative: Option B (Not Recommended)

If you keep root = repo root:
- Root `requirements.txt` must contain: `-r legacy/requirements_production.txt`
- Start command: `gunicorn legacy.app_production:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`
- Requires updating imports to use `legacy.` prefix

**Option A (root = legacy/) is cleaner and recommended.**
