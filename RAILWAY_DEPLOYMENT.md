# Railway Deployment Guide

## Quick Deploy (5 minutes)

### Step 1: Create Railway Account & Project

1. Go to https://railway.app
2. Sign up / Log in (use GitHub to connect)
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Authorize Railway to access your GitHub
6. Select repository: `nzahn1560/jet-finder`

### Step 2: Configure Service

Railway will auto-detect:
- ✅ Python (from `runtime.txt`)
- ✅ Start command (from `Procfile`)
- ✅ Dependencies (from `requirements.txt`)

**If it doesn't auto-detect:**
- **Root Directory:** `/` (leave blank)
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120`

### Step 3: Add Environment Variables

Go to your service → Variables tab → Add:

**Required:**
- `SECRET_KEY` = (generate a random string, e.g., use: `openssl rand -hex 32`)
- `FLASK_ENV` = `production`
- `PORT` = (Railway sets this automatically, but you can add it if needed)

**Optional (if using):**
- `STRIPE_SECRET_KEY` = (your Stripe secret key)
- `STRIPE_PUBLISHABLE_KEY` = (your Stripe publishable key)
- `STRIPE_CHARTER_SEARCH_PRICE_ID` = (if using)
- `STRIPE_EMPTY_LEG_PRICE_ID` = (if using)
- `STRIPE_PARTS_PRICE_ID` = (if using)

### Step 4: Get Your Railway URL

1. Go to your service → Settings
2. Find "Public Domain" or "Generate Domain"
3. Copy the URL (e.g., `https://your-app.up.railway.app`)

### Step 5: Connect Custom Domain (Optional)

To use `api.jetschoolusa.com`:

1. In Railway → Your Service → Settings → Networking
2. Add Custom Domain: `api.jetschoolusa.com`
3. Railway will give you DNS instructions
4. Go to Cloudflare DNS and add the CNAME record Railway provides

### Step 6: Update Frontend to Use Railway Backend

**If using Railway backend instead of Cloudflare Worker:**

1. Go to Cloudflare Pages → Settings → Environment Variables
2. Update `VITE_API_URL` to your Railway URL:
   - `https://your-app.up.railway.app`
   - OR `https://api.jetschoolusa.com` (if you set up custom domain)
3. Trigger a rebuild

## Troubleshooting

### Build Fails
- Check build logs in Railway
- Make sure `requirements.txt` has all dependencies
- Verify Python version in `runtime.txt` matches Railway's supported versions

### App Won't Start
- Check logs in Railway dashboard
- Verify `Procfile` is correct
- Make sure `SECRET_KEY` is set

### Database Issues
- Your app uses SQLite (`instance/jet_finder.db`)
- Railway's filesystem is ephemeral - data will be lost on redeploy
- Consider using Railway PostgreSQL addon for persistent storage

### CORS Errors
- Your Flask app already has CORS configured
- Make sure `jetschoolusa.com` and `jetschoolusa.pages.dev` are in allowed origins

## Current Setup Recommendation

**Best approach:**
- ✅ Frontend: Cloudflare Pages (already working)
- ✅ Backend API: Cloudflare Worker (already deployed at `jetschoolusa-api.nick-zahn777.workers.dev`)
- ⚠️ Python Flask: Only deploy to Railway if you need features the Worker doesn't have

**You don't need Railway if:**
- Your Cloudflare Worker handles all API needs
- You're happy with the current setup

**Deploy to Railway if:**
- You need Python-specific features
- You want to use the Flask app's full functionality
- You need persistent SQLite database (though Railway filesystem is ephemeral)
