# 🚀 Deploy to Railway - Step by Step

## ✅ Code is on GitHub
Your code has been pushed to: `https://github.com/nzahn1560/jet-finder`

---

## Step 1: Create Railway Project

1. Go to https://railway.app
2. Sign in (use GitHub to connect)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose repository: **`nzahn1560/jet-finder`**
6. Railway will detect your project

---

## Step 2: Configure Service

### Set Root Directory
1. Click on your service
2. Go to **Settings** tab
3. Scroll to **"Root Directory"**
4. Set to: **`legacy`**
5. Click **"Save"**

### Verify Build & Start Commands
Railway should auto-detect:
- **Build Command:** `pip install -r requirements_production.txt`
- **Start Command:** Uses `Procfile` → `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

If not set, add manually:
- **Start Command:** `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

---

## Step 3: Add PostgreSQL Database

1. In Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Wait for provisioning (30-60 seconds)
4. Railway automatically sets `DATABASE_URL` environment variable

**✅ No manual configuration needed!**

---

## Step 4: Set Environment Variables

Go to your service → **Variables** tab, add:

### Required Variables

```
SESSION_SECRET=<generate-random-32-chars>
```

**Generate SESSION_SECRET:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Or use Railway CLI:
```bash
railway variables set SESSION_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### Recommended Variables

```
APP_BASE_URL=https://your-app.up.railway.app
FLASK_ENV=production
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

---

## Step 5: Deploy

1. Railway will **auto-deploy** when you push to GitHub
2. Or click **"Deploy"** button manually
3. Watch the **Deploy Logs** tab

### What to Look For in Logs:

**✅ Success:**
```
🔧 Initializing database...
✅ Database connection successful
✅ Database tables created/verified successfully!
✅ Verified tables exist: users, sessions
✅ Database initialized successfully - all tables ready
✅ API blueprints registered
```

**❌ If you see errors:**
- Check `DATABASE_URL` is set (should be auto-set)
- Check PostgreSQL service is running
- Check logs for specific error messages

---

## Step 6: Get Your URL

1. Go to your service → **Settings** → **Networking**
2. Click **"Generate Domain"** (or use auto-generated)
3. Copy the URL: `https://your-app.up.railway.app`
4. Update `APP_BASE_URL` variable with this URL

---

## Step 7: Test Deployment

### 1. Health Check
Visit: `https://your-app.up.railway.app/health`
Should return: `{"status": "healthy"}`

### 2. Test Signup
1. Visit: `https://your-app.up.railway.app/signup`
2. Fill out form
3. Submit
4. Should redirect to `/dashboard`

### 3. Test Login
1. Visit: `https://your-app.up.railway.app/login`
2. Enter credentials
3. Submit
4. Should redirect to `/dashboard`

### 4. Verify Cookies
1. Open browser DevTools (F12)
2. Go to **Application** → **Cookies**
3. Should see `jet_session` cookie
4. Check flags: `HttpOnly`, `Secure`, `SameSite=Lax`

### 5. Test Session Persistence
1. After logging in, refresh page
2. Should stay logged in (not redirect to login)

---

## Step 8: Create Admin User (Optional)

### Option A: Using Railway CLI
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run admin creation script
railway run python create_admin.py admin@example.com AdminPass123!
```

### Option B: Using Environment Variables
Set in Railway Variables:
```
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminPass123!
```

Then run migrations (which seeds admin):
```bash
railway run python migrations/run_migrations.py
```

### Option C: Direct Database Access
1. Railway → PostgreSQL service → **Data** tab
2. Use Railway's database UI
3. Insert admin user manually

---

## Troubleshooting

### Database Connection Error

**Symptoms:**
```
❌ Database initialization failed: [error]
❌ DATABASE_URL: NOT SET
```

**Fix:**
1. Ensure PostgreSQL service is added
2. Check `DATABASE_URL` is in Variables (should be auto-set)
3. Restart service

### Tables Not Created

**Symptoms:**
- App starts but login fails
- No tables in database

**Fix:**
1. Check Railway logs for init_db() errors
2. Manually run:
   ```bash
   railway run python -c "from models import init_db; init_db()"
   ```

### Login Not Working

**If tables exist but login fails:**

1. **Check cookies:**
   - DevTools → Application → Cookies
   - Should see `jet_session`
   - Check `Secure` flag (should be True in production)

2. **Check cookie settings:**
   - `FLASK_ENV=production` must be set
   - Or `NODE_ENV=production`
   - This enables `Secure` cookies

3. **Check CORS:**
   - `APP_BASE_URL` should match your Railway domain
   - Frontend and API should be same origin

### App Won't Start

**Check:**
1. Root Directory is set to `legacy`
2. Start command is correct: `gunicorn app_production:app ...`
3. `requirements_production.txt` exists
4. `Procfile` exists in `legacy/` folder

---

## Quick Reference

### Railway Dashboard URLs
- **Project:** https://railway.app/project/[project-id]
- **Service:** https://railway.app/project/[project-id]/service/[service-id]
- **Variables:** https://railway.app/project/[project-id]/variables
- **Logs:** https://railway.app/project/[project-id]/deployments/[deployment-id]/logs

### Important Files
- **Main App:** `legacy/app_production.py`
- **Database Models:** `legacy/models.py`
- **Auth Routes:** `legacy/auth.py`
- **Procfile:** `legacy/Procfile`
- **Requirements:** `legacy/requirements_production.txt`

### Environment Variables Checklist
- [ ] `DATABASE_URL` (auto-set by Railway)
- [ ] `SESSION_SECRET` (generate random)
- [ ] `APP_BASE_URL` (your Railway domain)
- [ ] `FLASK_ENV=production` (optional but recommended)

---

## Next Steps After Deployment

1. ✅ Test signup/login flow
2. ✅ Verify database tables created
3. ✅ Test session persistence
4. ✅ Create admin user
5. ⏭️ Add Cloudflare (optional - see `CLOUDFLARE_SETUP.md`)
6. ⏭️ Configure R2 for file storage (optional)

---

## Support

If deployment fails:
1. Check Railway logs (most detailed)
2. Check Railway → Service → Metrics (resource usage)
3. Verify all environment variables are set
4. Ensure PostgreSQL service is running
5. Check `legacy/DATABASE_SETUP_COMPLETE.md` for database troubleshooting
