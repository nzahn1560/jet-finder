# Railway vs Localhost: Complete Setup Guide

## 🏠 Where the App is Stored

### Local Development
- **Location:** `/Users/amyzahn/Downloads/Code/jet-finder/legacy/`
- **Main App File:** `legacy/app_production.py`
- **Database:** SQLite at `legacy/instance/jet_finder.db` (local only)
- **Templates:** `legacy/templates/`
- **Static Files:** `legacy/static/`

### Railway Production
- **Location:** Railway builds from your GitHub repo
- **Root Directory:** Set to `legacy/` in Railway settings
- **Main App File:** `legacy/app_production.py` (same file!)
- **Database:** PostgreSQL (provided by Railway, separate service)
- **Templates/Static:** Same files from GitHub repo

**Key Point:** Railway runs the SAME code from GitHub, just in a different environment.

---

## 🔄 What Needs to Be Running

### Localhost Setup (What You Have Now)

1. **Flask App** (runs on `localhost:5015`)
   ```bash
   cd legacy
   python app_production.py
   # OR
   gunicorn app_production:app --bind 0.0.0.0:5015
   ```

2. **SQLite Database** (automatic)
   - Created automatically at `legacy/instance/jet_finder.db`
   - Tables created via `init_db()` on first run

3. **Environment Variables** (optional for local)
   - `DATABASE_URL` - Not needed (uses SQLite)
   - `SESSION_SECRET` - Optional (has default)

**Total:** Just run the Flask app. Everything else is automatic.

### Railway Setup (What Railway Needs)

1. **Railway Service** (your Flask app)
   - ✅ Automatically starts when deployed
   - Runs: `gunicorn app_production:app --bind 0.0.0.0:$PORT`
   - Port: Railway assigns automatically (via `$PORT` env var)

2. **PostgreSQL Database** (separate Railway service)
   - ✅ Must be created in Railway dashboard
   - ✅ Must be linked to your Flask service
   - ✅ Provides `DATABASE_URL` environment variable automatically
   - Tables created automatically via `init_db()` on first deploy

3. **Environment Variables** (set in Railway dashboard)
   - `DATABASE_URL` - ✅ Auto-provided by PostgreSQL service
   - `SESSION_SECRET` - ⚠️ **YOU MUST SET THIS** (generate a random string)
   - `APP_BASE_URL` - Optional (your Railway domain)
   - `STRIPE_SECRET_KEY` - If using Stripe
   - `STRIPE_WEBHOOK_SECRET` - If using Stripe webhooks

**Total:** Railway service + PostgreSQL service (both in Railway dashboard)

---

## 📋 Railway Configuration Checklist

### Step 1: Create PostgreSQL Service
1. Railway Dashboard → **New** → **Database** → **Add PostgreSQL**
2. Railway automatically creates the database
3. Railway automatically provides `DATABASE_URL` to linked services

### Step 2: Configure Flask Service
1. Railway Dashboard → Your Flask service → **Settings**
2. **Root Directory:** `legacy` ✅
3. **Build Command:** (leave blank - auto-detects)
4. **Start Command:** (leave blank - uses Procfile)
5. **Environment Variables:**
   - `SESSION_SECRET` = (generate random string: `openssl rand -hex 32`)
   - `APP_BASE_URL` = (your Railway domain, optional)
   - `STRIPE_SECRET_KEY` = (if using Stripe)
   - `STRIPE_WEBHOOK_SECRET` = (if using Stripe)

### Step 3: Link Services
1. Railway Dashboard → Flask service → **Settings** → **Variables**
2. Click **Reference Variable** from PostgreSQL service
3. Select `DATABASE_URL` (Railway does this automatically when you add PostgreSQL)

### Step 4: Deploy
- Railway auto-deploys on git push
- OR click **Deploy** → **Deploy Latest** in Railway dashboard

---

## 🔧 Making Changes: Railway vs Localhost

### ✅ Making Useful Changes (Recommended Workflow)

**1. Develop Locally First**
```bash
# Make changes in your local files
cd legacy
python app_production.py  # Test locally on localhost:5015
```

**2. Test Locally**
- Visit `http://localhost:5015`
- Test all functionality
- Fix bugs locally

**3. Commit Only When Ready**
```bash
git add .
git commit -m "Add feature X"
git push origin main
```

**4. Railway Auto-Deploys**
- Railway detects push
- Builds and deploys automatically
- Your changes go live

### ❌ What NOT to Do

**Don't:**
- ❌ Make changes directly in Railway dashboard (they'll be overwritten on next deploy)
- ❌ Commit every tiny change (commit when feature is complete)
- ❌ Deploy broken code (test locally first)
- ❌ Edit files in Railway's file editor (use local editor)

**Do:**
- ✅ Make all changes locally
- ✅ Test locally first
- ✅ Commit when feature is complete and tested
- ✅ Let Railway auto-deploy from GitHub

---

## 🎯 Railway Settings: What to Change vs What Not to Change

### ✅ Safe to Change in Railway Dashboard

**Environment Variables:**
- `SESSION_SECRET` - Change anytime (regenerates sessions)
- `APP_BASE_URL` - Change if domain changes
- `STRIPE_SECRET_KEY` - Change if switching Stripe accounts
- Any other config values

**Service Settings:**
- Root Directory - Set once, don't change
- Build/Start Commands - Set once, don't change
- Resource limits (CPU/RAM) - Can adjust as needed

**Database:**
- Can view data in Railway PostgreSQL dashboard
- Can run SQL queries
- **Don't manually create tables** (app does this automatically)

### ❌ Don't Change in Railway Dashboard

**Code Files:**
- ❌ Don't edit `.py` files in Railway
- ❌ Don't edit templates in Railway
- ❌ Don't edit static files in Railway
- **Why:** These are overwritten on every deploy from GitHub

**Database Schema:**
- ❌ Don't manually create tables
- ❌ Don't manually run migrations
- **Why:** App creates tables automatically via `init_db()`

---

## 🔄 Development Workflow

### Daily Development

1. **Work Locally**
   ```bash
   cd /Users/amyzahn/Downloads/Code/jet-finder/legacy
   python app_production.py
   # Visit http://localhost:5015
   ```

2. **Make Changes**
   - Edit files in your local `legacy/` directory
   - Test on `localhost:5015`
   - Fix bugs

3. **Commit When Ready**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

4. **Railway Auto-Deploys**
   - Wait 2-5 minutes
   - Check Railway logs
   - Visit your Railway URL

### Making Database Changes

**Local:**
- SQLite database at `legacy/instance/jet_finder.db`
- Tables auto-created on first run
- Can use SQLite browser to view data

**Railway:**
- PostgreSQL database (separate service)
- Tables auto-created on first deploy
- Can view in Railway PostgreSQL dashboard
- Can run SQL queries in Railway

**Important:** Database changes (new tables/columns) should be:
1. Added to `legacy/models.py` (SQLAlchemy models)
2. Committed to GitHub
3. Railway will create them on next deploy via `init_db()`

---

## 🚀 Quick Start Checklist

### First Time Railway Setup

- [ ] Create PostgreSQL service in Railway
- [ ] Create Flask service in Railway (or connect GitHub repo)
- [ ] Set Root Directory to `legacy`
- [ ] Set `SESSION_SECRET` environment variable
- [ ] Link PostgreSQL to Flask service (auto-done)
- [ ] Deploy (auto-deploys on git push)

### Daily Development

- [ ] Work locally: `cd legacy && python app_production.py`
- [ ] Test on `localhost:5015`
- [ ] Commit when ready: `git add . && git commit -m "..." && git push`
- [ ] Railway auto-deploys
- [ ] Check Railway logs for errors

---

## 📍 Key Differences: Localhost vs Railway

| Feature | Localhost | Railway |
|---------|-----------|---------|
| **App Location** | `legacy/app_production.py` | Same file from GitHub |
| **Database** | SQLite (`instance/jet_finder.db`) | PostgreSQL (separate service) |
| **Port** | `5015` (hardcoded) | `$PORT` (Railway assigns) |
| **URL** | `http://localhost:5015` | `https://your-app.railway.app` |
| **Start Command** | `python app_production.py` | `gunicorn app_production:app` |
| **Environment** | Local machine | Railway cloud |
| **Auto-Deploy** | Manual start | Auto on git push |
| **Database Init** | Automatic on first run | Automatic on first deploy |

---

## 💡 Pro Tips

1. **Always Test Locally First**
   - Faster feedback loop
   - No deployment wait time
   - Can debug easily

2. **Use Git Branches**
   ```bash
   git checkout -b feature/new-feature
   # Make changes, test locally
   git commit -m "Add new feature"
   git push origin feature/new-feature
   # Test on Railway staging
   # Merge to main when ready
   ```

3. **Check Railway Logs**
   - Railway Dashboard → Your service → **Logs**
   - Shows real-time output
   - Check for errors after deploy

4. **Environment Variables**
   - Keep secrets in Railway (never commit to GitHub)
   - Use `.env` file locally (gitignored)
   - Railway automatically provides `DATABASE_URL`

5. **Database Migrations**
   - Add to `legacy/models.py` (SQLAlchemy models)
   - App creates tables automatically via `init_db()`
   - No manual SQL needed

---

## 🆘 Troubleshooting

### Railway Not Working Like Localhost?

**Check:**
1. ✅ Root Directory set to `legacy`?
2. ✅ PostgreSQL service created and linked?
3. ✅ `DATABASE_URL` environment variable exists?
4. ✅ `SESSION_SECRET` set?
5. ✅ Check Railway logs for errors

### Changes Not Appearing?

**Check:**
1. ✅ Did you commit and push to GitHub?
2. ✅ Did Railway deploy successfully? (check logs)
3. ✅ Are you looking at the right Railway URL?
4. ✅ Did you clear browser cache?

### Database Issues?

**Check:**
1. ✅ PostgreSQL service running?
2. ✅ `DATABASE_URL` correct?
3. ✅ Check Railway logs for `init_db()` messages
4. ✅ Tables should be created automatically

---

## 📚 Summary

**To make Railway work like localhost:**

1. **Same Code:** Railway runs the same `legacy/app_production.py` from GitHub
2. **Same Structure:** Same templates, static files, everything
3. **Different Database:** PostgreSQL instead of SQLite (but same schema)
4. **Different Environment:** Cloud vs local, but same code

**To make useful changes:**

1. ✅ Edit files locally
2. ✅ Test locally first
3. ✅ Commit when ready
4. ✅ Push to GitHub
5. ✅ Railway auto-deploys

**Don't:**
- ❌ Edit code in Railway dashboard
- ❌ Commit every tiny change
- ❌ Deploy without testing locally

**Your app is stored in:** `/Users/amyzahn/Downloads/Code/jet-finder/legacy/`  
**Railway runs from:** Same files, pulled from GitHub on each deploy
