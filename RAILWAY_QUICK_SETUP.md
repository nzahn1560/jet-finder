# Railway Quick Setup for app.py (localhost:5015)

## ✅ Files Ready

1. **`Procfile`** - Updated to run `app:app`
2. **`requirements.txt`** - Contains all dependencies
3. **Railway config** - Ready to deploy

---

## 🚀 Railway Dashboard Setup (5 minutes)

### Step 1: Configure Service

1. **Railway Dashboard** → Your Service → **Settings**

2. **Root Directory:** 
   - **Leave BLANK** (uses repo root where `app.py` is)
   - ❌ NOT `legacy/` (that's for app_production.py)

3. **Build Command:**
   - **Leave BLANK** (Railway auto-detects `requirements.txt`)

4. **Start Command:**
   - **Leave BLANK** (Railway uses `Procfile`)

### Step 2: Environment Variables

Railway Dashboard → Your Service → **Variables** → **New Variable**

**Required:**
- `SESSION_SECRET` = (generate: `openssl rand -hex 32`)

**Optional (if using Stripe):**
- `STRIPE_SECRET_KEY` = your Stripe secret key
- `STRIPE_PUBLISHABLE_KEY` = your Stripe publishable key

### Step 3: Deploy

**Option A: Auto-deploy (recommended)**
- Push to GitHub → Railway auto-deploys

**Option B: Manual deploy**
- Railway Dashboard → **Deployments** → **Deploy Latest**

---

## 📋 What Railway Will Do

1. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```
   - Installs Flask, pandas, numpy, stripe, gunicorn, etc.

2. **Start App**
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
   ```
   - Runs your `app.py` (same as localhost:5015)
   - Uses Railway's assigned port

3. **Serve App**
   - Your app is live at: `https://your-app.railway.app`
   - Works exactly like `localhost:5015`

---

## 🔍 Verify Deployment

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

### Test Your App

Visit your Railway URL:
- Home: `https://your-app.railway.app/`
- Marketplace: `https://your-app.railway.app/marketplace/`
- All routes from `app.py` work

---

## ⚠️ Important Notes

### Database (SQLite)

**Current:** `app.py` uses SQLite (`instance/jet_finder.db`)

**On Railway:**
- ✅ SQLite will work
- ⚠️ Data is **ephemeral** (lost on redeploy)
- 💡 For production, consider PostgreSQL

**To keep SQLite:**
- No additional setup needed
- Works immediately

**To use PostgreSQL:**
- Create PostgreSQL service in Railway
- Modify `app.py` to use PostgreSQL
- More complex but production-ready

### Static Files & Templates

- ✅ `static/` directory - Served automatically
- ✅ `templates/` directory - Served automatically
- ✅ `data/` directory - Available to app

### Port Configuration

**Localhost:**
```python
app.run(debug=True, host="0.0.0.0", port=5015)
```

**Railway:**
- Uses `$PORT` environment variable (auto-assigned)
- Gunicorn handles this automatically
- No code changes needed

---

## 🎯 Summary

**To deploy app.py to Railway:**

1. ✅ **Procfile:** `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
2. ✅ **requirements.txt:** All dependencies listed
3. 🔄 **Railway Root Directory:** (blank - repo root)
4. 🔄 **Set SESSION_SECRET** in Railway
5. 🔄 **Commit and push** to GitHub
6. ✅ **Railway auto-deploys**

**Your app will run on Railway exactly like it runs on localhost:5015!**

---

## 📝 Current Files

- ✅ `Procfile` - Updated for `app:app`
- ✅ `requirements.txt` - All dependencies
- ✅ `app.py` - Your main app (runs on localhost:5015)
- ✅ `marketplace.py` - Blueprint
- ✅ `templates/` - HTML templates
- ✅ `static/` - CSS, JS, images

**Everything is ready! Just configure Railway and deploy.**
