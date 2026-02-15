# Quick Start Reference: Railway vs Localhost

## 📍 Where Your App Lives

**Local:** `/Users/amyzahn/Downloads/Code/jet-finder/legacy/`  
**Railway:** Same files, pulled from GitHub on each deploy

**Main App:** `legacy/app_production.py` (same file for both!)

---

## 🚀 Starting the App

### Localhost (Development)
```bash
cd /Users/amyzahn/Downloads/Code/jet-finder/legacy
python app_production.py
# Visit: http://localhost:5015
```

**What runs:**
- ✅ Flask app (port 5015)
- ✅ SQLite database (auto-created)
- ✅ All templates and static files

### Railway (Production)
**Automatic!** Railway starts when you deploy.

**What runs:**
- ✅ Flask app (via gunicorn)
- ✅ PostgreSQL database (separate Railway service)
- ✅ All templates and static files (from GitHub)

**You need to set up:**
1. Railway service (Flask app)
2. PostgreSQL service (database)
3. Link them together

---

## 🔧 What Needs to Be Running

### Localhost (Simple)
1. **Just the Flask app** - That's it!
   ```bash
   python app_production.py
   ```
   - Database: SQLite (auto-created)
   - Port: 5015
   - URL: http://localhost:5015

### Railway (Two Services)
1. **Flask Service** (your app)
   - Auto-starts on deploy
   - Runs: `gunicorn app_production:app`
   - Port: Railway assigns automatically

2. **PostgreSQL Service** (database)
   - Must create in Railway dashboard
   - Auto-provides `DATABASE_URL`
   - Tables created automatically on first deploy

**Total:** 2 services in Railway dashboard

---

## ⚙️ Railway Configuration (One-Time Setup)

### Step 1: Create PostgreSQL
1. Railway Dashboard → **New** → **Database** → **Add PostgreSQL**
2. Done! Railway creates it automatically.

### Step 2: Configure Flask Service
1. Railway Dashboard → Your Flask service → **Settings**
2. **Root Directory:** `legacy` ✅
3. **Environment Variables:**
   - `SESSION_SECRET` = (generate: `openssl rand -hex 32`)
   - `DATABASE_URL` = (auto-provided by PostgreSQL service)

### Step 3: Deploy
- Push to GitHub → Railway auto-deploys
- OR Railway Dashboard → **Deploy** → **Deploy Latest**

---

## ✏️ Making Changes: Best Practices

### ✅ DO THIS (Recommended)

**1. Work Locally**
```bash
cd legacy
python app_production.py
# Make changes, test on localhost:5015
```

**2. Test Locally First**
- Fix all bugs locally
- Test all features
- Make sure it works

**3. Commit When Feature is Complete**
```bash
git add .
git commit -m "Add feature X - tested and working"
git push origin main
```

**4. Railway Auto-Deploys**
- Wait 2-5 minutes
- Check Railway logs
- Visit Railway URL

### ❌ DON'T DO THIS

**Don't:**
- ❌ Edit code in Railway dashboard (gets overwritten)
- ❌ Commit every tiny change (commit when feature is done)
- ❌ Deploy without testing locally
- ❌ Edit files in Railway's file editor

**Why:** Railway pulls from GitHub. Any changes in Railway get overwritten on next deploy.

---

## 🎯 What to Change in Railway vs What Not to Change

### ✅ Safe to Change in Railway Dashboard

**Environment Variables (Config):**
- `SESSION_SECRET` - Change anytime
- `APP_BASE_URL` - Change if domain changes
- `STRIPE_SECRET_KEY` - Change if switching accounts
- Any config values

**Service Settings:**
- Resource limits (CPU/RAM)
- Scaling settings

**Database:**
- View data
- Run SQL queries
- Export data

### ❌ Don't Change in Railway Dashboard

**Code Files:**
- ❌ `.py` files
- ❌ Templates (`.html`)
- ❌ Static files (`.js`, `.css`)
- ❌ Any code files

**Why:** These come from GitHub. Changes get overwritten.

**Database Schema:**
- ❌ Don't manually create tables
- ❌ Don't manually run migrations

**Why:** App creates tables automatically via `init_db()`

---

## 📋 Daily Workflow

### Morning: Start Development
```bash
cd /Users/amyzahn/Downloads/Code/jet-finder/legacy
python app_production.py
# Visit http://localhost:5015
```

### During Development
1. Edit files in `legacy/` directory
2. Save files
3. Refresh browser (localhost:5015)
4. Test changes
5. Fix bugs

### When Feature is Done
```bash
git add .
git commit -m "Add feature: description"
git push origin main
# Railway auto-deploys in 2-5 minutes
```

### Check Deployment
1. Railway Dashboard → Your service → **Logs**
2. Look for: `✅ DATABASE INITIALIZATION COMPLETE`
3. Visit Railway URL
4. Test the feature

---

## 🔍 Quick Troubleshooting

### "Railway doesn't work like localhost"

**Check:**
1. ✅ Root Directory = `legacy`?
2. ✅ PostgreSQL service created?
3. ✅ `DATABASE_URL` exists?
4. ✅ `SESSION_SECRET` set?
5. ✅ Check Railway logs

### "Changes not appearing"

**Check:**
1. ✅ Committed to GitHub?
2. ✅ Pushed to GitHub?
3. ✅ Railway deployed? (check logs)
4. ✅ Cleared browser cache?

### "Database errors"

**Check:**
1. ✅ PostgreSQL service running?
2. ✅ `DATABASE_URL` correct?
3. ✅ Check logs for `init_db()` messages

---

## 📊 Comparison Table

| Feature | Localhost | Railway |
|---------|-----------|---------|
| **Start Command** | `python app_production.py` | `gunicorn app_production:app` |
| **Port** | `5015` | `$PORT` (auto) |
| **URL** | `http://localhost:5015` | `https://your-app.railway.app` |
| **Database** | SQLite (local file) | PostgreSQL (cloud) |
| **Start** | Manual | Auto on deploy |
| **Code Location** | `legacy/` folder | Same, from GitHub |

---

## 💡 Key Takeaways

1. **Same Code:** Railway runs the exact same `legacy/app_production.py` from GitHub
2. **Different Database:** PostgreSQL (cloud) vs SQLite (local)
3. **Work Locally:** Always develop and test locally first
4. **Commit When Ready:** Don't commit every tiny change
5. **Railway Auto-Deploys:** Just push to GitHub, Railway handles the rest

**Your app:** `/Users/amyzahn/Downloads/Code/jet-finder/legacy/`  
**Railway runs:** Same files from GitHub
