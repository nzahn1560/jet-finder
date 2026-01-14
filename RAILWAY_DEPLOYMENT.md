# Railway Full Stack Deployment Guide

Deploy your Python Flask backend + React frontend to Railway.

## Step 1: Create Railway Project

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository: `nzahn1560/jet-finder`
6. Railway will detect your project

## Step 2: Deploy Backend (Python Flask)

Railway should auto-detect your Python app. If not:

1. In your Railway project, click "New Service"
2. Select "GitHub Repo" → Choose `nzahn1560/jet-finder`
3. Railway will detect:
   - `Procfile` → Uses it for start command
   - `requirements.txt` → Installs Python dependencies
   - `runtime.txt` → Uses Python 3.10

### Configure Backend Service

1. Click on your service → Settings
2. **Start Command:** Should auto-detect from Procfile:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
   ```
3. **Root Directory:** Leave blank (or `/`)

### Add Environment Variables (Backend)

Go to your service → Variables tab, add:

- `SECRET_KEY` = (generate a random string, e.g., use `openssl rand -hex 32`)
- `FLASK_ENV` = `production`
- `PORT` = (Railway sets this automatically, don't add manually)
- `STRIPE_SECRET_KEY` = (your Stripe secret key if using)
- `STRIPE_PUBLISHABLE_KEY` = (your Stripe publishable key if using)

### Get Your Backend URL

1. Go to your service → Settings → Networking
2. Click "Generate Domain" (or use the auto-generated one)
3. Copy the URL (e.g., `https://your-app.up.railway.app`)
4. This is your backend API URL!

## Step 3: Deploy Frontend (Optional - or keep on Cloudflare Pages)

**Option A: Deploy Frontend to Railway**

1. Add another service in Railway
2. Select the same repo
3. Settings:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm ci && npm run build`
   - **Start Command:** `npx serve -s dist -l $PORT`
4. Add environment variables:
   - `VITE_API_URL` = (your Railway backend URL from Step 2)
   - `VITE_SUPABASE_URL` = `https://thjvacmcpvwxdrfouymp.supabase.co`
   - `VITE_SUPABASE_ANON_KEY` = (your key)

**Option B: Keep Frontend on Cloudflare Pages (Recommended)**

- Your frontend is already on Cloudflare Pages
- Just update `VITE_API_URL` to point to your Railway backend URL
- This is simpler and faster

## Step 4: Update Frontend to Use Railway Backend

If keeping frontend on Cloudflare Pages:

1. Go to Cloudflare Pages → Your project → Settings → Environment Variables
2. Update `VITE_API_URL` to your Railway backend URL:
   ```
   https://your-app.up.railway.app
   ```
3. Trigger a rebuild

## Step 5: Set Up Database (If Needed)

Your Flask app uses SQLite by default. For production:

1. In Railway, add a PostgreSQL database:
   - Click "New" → "Database" → "Add PostgreSQL"
2. Railway will create a database and set `DATABASE_URL` automatically
3. Update your Flask app to use PostgreSQL instead of SQLite (optional, SQLite works for small apps)

## Step 6: Custom Domain (Optional)

1. In Railway → Your service → Settings → Networking
2. Click "Custom Domain"
3. Add your domain (e.g., `api.jetschoolusa.com`)
4. Railway will give you DNS records to add in Cloudflare

## Quick Start Commands

```bash
# Generate a secure SECRET_KEY
openssl rand -hex 32

# Test locally with Railway's PORT
PORT=8080 gunicorn app:app --bind 0.0.0.0:$PORT
```

## Troubleshooting

**Build fails:**
- Check build logs in Railway
- Make sure `requirements.txt` is correct
- Verify Python version in `runtime.txt`

**App won't start:**
- Check logs in Railway dashboard
- Verify `Procfile` is correct
- Make sure `PORT` environment variable is set (Railway does this automatically)

**API calls fail:**
- Check CORS settings in `app.py`
- Verify your Railway backend URL is correct
- Check environment variables are set
