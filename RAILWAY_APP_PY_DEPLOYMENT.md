# Railway Deployment Guide: app.py (localhost:5015)

## Overview

This guide shows how to deploy `app.py` (your main app running on localhost:5015) to Railway.

## Current Setup

**Localhost:**
- App: `app.py` (root directory)
- Port: `5015`
- Database: SQLite (`instance/jet_finder.db`)
- URL: `http://localhost:5015`

**Railway Target:**
- App: `app.py` (root directory)
- Port: `$PORT` (Railway assigns)
- Database: SQLite (can keep SQLite, or migrate to PostgreSQL)
- URL: `https://your-app.railway.app`

---

## Step 1: Update Procfile

**Current Procfile:**
```
web: cd legacy && gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**New Procfile (for app.py):**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**Why:** 
- No `cd legacy` needed (app.py is in root)
- Use `app:app` (module:variable format)
- Railway will run from repo root

---

## Step 2: Check Requirements

`app.py` needs these dependencies (check if in `requirements.txt`):

**Required:**
- Flask
- pandas
- numpy
- stripe
- werkzeug

**Optional but likely needed:**
- openpyxl (for Excel files)
- matplotlib (for charts)
- Pillow (for images)

**Create/Update `requirements.txt` in repo root:**

```txt
Flask==3.0.0
pandas==2.1.0
numpy==1.25.2
stripe==7.8.0
Werkzeug==3.0.1
gunicorn==21.2.0
python-dotenv==1.0.0
openpyxl==3.1.2
matplotlib==3.7.2
Pillow==10.0.0
requests==2.31.0
```

---

## Step 3: Railway Configuration

### Option A: Keep SQLite (Simpler)

**Pros:**
- No database service needed
- Works immediately
- Same as localhost

**Cons:**
- Data lost on redeploy (ephemeral storage)
- Not suitable for production with real users

**Railway Settings:**
- **Root Directory:** (leave blank - uses repo root)
- **Build Command:** (leave blank - auto-detects)
- **Start Command:** (leave blank - uses Procfile)

### Option B: Use PostgreSQL (Recommended for Production)

**Pros:**
- Persistent data
- Production-ready
- Can handle multiple users

**Cons:**
- Need to migrate app.py from SQLite to PostgreSQL
- More setup required

**Railway Settings:**
- **Root Directory:** (leave blank)
- **PostgreSQL Service:** Create and link
- **Environment Variables:**
  - `DATABASE_URL` (auto-provided by PostgreSQL)

**Note:** You'll need to modify `app.py` to use PostgreSQL instead of SQLite.

---

## Step 4: Update app.py for Railway (If Using PostgreSQL)

If you want to use PostgreSQL, modify `app.py`:

**Current (SQLite):**
```python
import sqlite3
conn = sqlite3.connect('instance/jet_finder.db')
```

**Change to (PostgreSQL):**
```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/jet_finder.db')

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
if DATABASE_URL.startswith('postgres'):
    conn = psycopg2.connect(DATABASE_URL)
    conn.row_factory = RealDictCursor
else:
    import sqlite3
    conn = sqlite3.connect('instance/jet_finder.db')
    conn.row_factory = sqlite3.Row
```

**Or use SQLAlchemy** (like legacy/app_production.py does) for better database abstraction.

---

## Step 5: Railway Dashboard Setup

### Create/Configure Service

1. **Railway Dashboard** → **New Project** (or use existing)
2. **Add Service** → **GitHub Repo** → Select `jet-finder`
3. **Settings:**
   - **Root Directory:** (leave blank - uses repo root)
   - **Build Command:** (leave blank)
   - **Start Command:** (leave blank - uses Procfile)

### Environment Variables

Set in Railway Dashboard → Your Service → **Variables**:

**Required:**
- `SESSION_SECRET` = (generate: `openssl rand -hex 32`)

**Optional:**
- `STRIPE_SECRET_KEY` = (if using Stripe)
- `STRIPE_PUBLISHABLE_KEY` = (if using Stripe)
- `DATABASE_URL` = (auto-provided if using PostgreSQL)

---

## Step 6: File Structure

**Repo Root:**
```
jet-finder/
├── app.py              ← Main app (this is what runs)
├── Procfile            ← Railway start command
├── requirements.txt    ← Python dependencies
├── marketplace.py      ← Blueprint
├── enhanced_data_manager.py
├── avinode_integration.py
├── templates/          ← HTML templates
├── static/            ← CSS, JS, images
├── data/               ← JSON data files
└── instance/           ← SQLite DB (local only)
```

**Railway will:**
- Install from `requirements.txt` (repo root)
- Run `gunicorn app:app` from Procfile
- Serve templates and static files
- Create `instance/` directory for SQLite (if using SQLite)

---

## Step 7: Deploy

1. **Commit changes:**
   ```bash
   git add Procfile requirements.txt
   git commit -m "Configure Railway for app.py deployment"
   git push origin main
   ```

2. **Railway auto-deploys:**
   - Railway detects push
   - Builds and installs dependencies
   - Starts app via Procfile

3. **Check logs:**
   - Railway Dashboard → Your Service → **Logs**
   - Should see: `Starting gunicorn app:app`
   - Should see: `Running on http://0.0.0.0:$PORT`

---

## Step 8: Verify Deployment

### Check Railway Logs

You should see:
```
Collecting Flask==3.0.0
Collecting pandas==2.1.0
...
Successfully installed Flask-3.0.0 pandas-2.1.0 ...
Starting gunicorn app:app
[INFO] Booting worker
Running on http://0.0.0.0:XXXX
```

### Test URLs

- Home: `https://your-app.railway.app/`
- Marketplace: `https://your-app.railway.app/marketplace/`
- Other routes from `app.py`

---

## Important Notes

### SQLite on Railway

**⚠️ Warning:** If using SQLite on Railway:
- Data is **ephemeral** (lost on redeploy)
- File system is read-only in some cases
- Not recommended for production

**Better:** Use PostgreSQL for persistent data.

### Database Migration

If `app.py` uses SQLite and you want PostgreSQL:
1. Create PostgreSQL service in Railway
2. Modify `app.py` to use PostgreSQL (see Step 4)
3. Run migration script to move data
4. Test thoroughly

### Static Files

Railway serves static files from `static/` directory automatically if Flask is configured correctly.

### Templates

Templates in `templates/` directory are served automatically by Flask.

---

## Quick Start Checklist

- [ ] Update `Procfile` to: `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- [ ] Update `requirements.txt` with all dependencies
- [ ] Set Railway Root Directory to: (blank/root)
- [ ] Set `SESSION_SECRET` environment variable
- [ ] (Optional) Create PostgreSQL service if migrating from SQLite
- [ ] Commit and push changes
- [ ] Check Railway logs for successful deployment
- [ ] Test Railway URL

---

## Troubleshooting

### "Module not found" errors
- Check `requirements.txt` has all dependencies
- Railway installs from repo root `requirements.txt`

### "Port already in use"
- Railway handles ports automatically via `$PORT`
- Don't hardcode port 5015

### "Database errors"
- If using SQLite: Check `instance/` directory is writable
- If using PostgreSQL: Check `DATABASE_URL` is set
- Check Railway logs for connection errors

### "Templates not found"
- Ensure `templates/` directory is in repo root
- Check Flask template folder configuration

---

## Summary

**To deploy app.py to Railway:**

1. **Procfile:** `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
2. **Root Directory:** (blank - repo root)
3. **Requirements:** All dependencies in `requirements.txt`
4. **Database:** SQLite (simple) or PostgreSQL (production)
5. **Deploy:** Push to GitHub, Railway auto-deploys

**Your app will run on Railway just like it runs on localhost:5015!**
