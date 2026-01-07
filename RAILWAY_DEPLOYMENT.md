# Railway Full-Stack Deployment Guide

Deploy your entire Jet Finder app to Railway (Python backend + React frontend).

## Step 1: Create Railway Account & Project

1. Go to https://railway.app
2. Sign up/Login (use GitHub login for easiest setup)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your repository: `nzahn1560/jet-finder`
6. Railway will auto-detect it's a Python project

## Step 2: Configure Backend Service (Flask API)

Railway should automatically:
- Detect `Procfile` (uses gunicorn to run Flask)
- Detect `requirements.txt` (installs Python dependencies)
- Detect `runtime.txt` (uses Python 3.10)

### If Railway doesn't auto-detect:

1. In your Railway project → **Settings**
2. Under **"Build & Deploy"**:
   - **Root Directory:** `/` (root)
   - **Build Command:** (leave blank - Railway handles it)
   - **Start Command:** Railway will use your `Procfile` automatically

## Step 3: Add Environment Variables

Go to Railway Project → **Variables** tab and add:

### Required Variables:

```
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=production
PORT=5000
```

**Generate SECRET_KEY:**
```bash
# Run this locally to generate a secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Optional Variables (if you use them):

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_CHARTER_SEARCH_PRICE_ID=price_...
STRIPE_EMPTY_LEG_PRICE_ID=price_...
STRIPE_PARTS_PRICE_ID=price_...
```

## Step 4: Deploy Backend

1. Railway will automatically start deploying when you connect the repo
2. Check the **Deployments** tab to watch the build
3. Once deployed, Railway will give you a URL like:
   - `https://jet-finder-production-xxxx.up.railway.app`

## Step 5: Deploy Frontend (Optional - on Railway)

### Option A: Deploy Frontend on Railway Too

1. In your Railway project, click **"+ New"** → **"GitHub Repo"**
2. Select the same repo: `nzahn1560/jet-finder`
3. Railway will detect a second service
4. Configure it:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm ci && npm run build`
   - **Start Command:** `npx serve dist -s -l $PORT`
   - **Output Directory:** `dist`

5. Add Environment Variables to Frontend service:
   ```
   VITE_API_URL=https://your-backend-service-url.up.railway.app
   VITE_SUPABASE_URL=https://thjvacmcpvwxdrfouymp.supabase.co
   VITE_SUPABASE_ANON_KEY=your-supabase-key
   ```

### Option B: Keep Frontend on Cloudflare Pages (Recommended)

This is actually better - keep your frontend on Cloudflare Pages (fast CDN) and only deploy the backend to Railway.

1. Keep Cloudflare Pages for frontend
2. Set `VITE_API_URL` in Cloudflare Pages to your Railway backend URL
3. You get: Fast frontend (Cloudflare) + Full-featured backend (Railway)

## Step 6: Get Your Railway Backend URL

1. After deployment, go to your backend service
2. Click **"Settings"** → **"Generate Domain"** (if needed)
3. Copy the public URL (e.g., `https://jet-finder-production.up.railway.app`)

## Step 7: Update Frontend API URL

### If using Cloudflare Pages:
Update `VITE_API_URL` in Cloudflare Pages to your Railway backend URL.

### If using Railway for frontend:
The environment variables you set will be used.

## Step 8: Connect Custom Domain (api.jetschoolusa.com)

1. In Railway → Your backend service → **Settings** → **Domains**
2. Click **"Custom Domain"**
3. Enter: `api.jetschoolusa.com`
4. Railway will show you DNS records to add
5. Go to Cloudflare DNS and add the CNAME record Railway provides
6. Wait for DNS propagation (5-10 minutes)

## Troubleshooting

### Build Fails
- Check build logs in Railway
- Verify `requirements.txt` is correct
- Make sure `Procfile` exists and is correct

### App Crashes on Start
- Check logs in Railway → Deployments → Logs
- Verify environment variables are set
- Make sure `SECRET_KEY` is set

### API Not Working
- Check backend logs in Railway
- Verify CORS is configured (already done in app.py)
- Make sure the Railway URL is accessible

## Quick Check Commands (in Railway)

Railway provides a terminal - you can SSH in and check:
- `python --version` (should be 3.10)
- `gunicorn --version` (should be installed)
- `ls -la` (see your files)

