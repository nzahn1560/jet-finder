# Railway Deployment Checklist

## ✅ Pre-Deployment (Code Ready)

- [x] Flask app exists: `legacy/app_production.py`
- [x] Database models: `legacy/models.py`
- [x] Authentication: `legacy/auth.py`
- [x] API routes: `legacy/listings_api.py`, `legacy/billing_api.py`
- [x] Frontend templates: `legacy/templates/`
- [x] Requirements: `legacy/requirements_production.txt`
- [x] Procfile: `legacy/Procfile` (fixed to use `app_production:app`)
- [x] Authentication fixes applied

## 🚀 Railway Deployment Steps

### 1. Create Railway Project
- [ ] Go to https://railway.app
- [ ] Sign in with GitHub
- [ ] New Project → Deploy from GitHub
- [ ] Select repository: `nzahn1560/jet-finder`

### 2. Configure Service
- [ ] Set Root Directory: `legacy`
- [ ] Railway should auto-detect:
  - Build: `pip install -r requirements_production.txt`
  - Start: Uses `Procfile` → `gunicorn app_production:app ...`

### 3. Add PostgreSQL Database
- [ ] Railway Dashboard → Your Project → New → Database → PostgreSQL
- [ ] Wait for provisioning
- [ ] Railway auto-sets `DATABASE_URL` environment variable

### 4. Set Environment Variables
Go to Railway → Your Service → Variables tab, add:

```
SESSION_SECRET=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
APP_BASE_URL=https://your-app.up.railway.app
FLASK_ENV=production
```

**Note:** `DATABASE_URL` is auto-set by Railway when you add PostgreSQL.

### 5. Deploy
- [ ] Railway will auto-deploy on git push
- [ ] Or click "Deploy" button
- [ ] Check logs for errors

### 6. Get Your URL
- [ ] Railway → Your Service → Settings → Networking
- [ ] Click "Generate Domain" (or use auto-generated)
- [ ] Copy URL: `https://your-app.up.railway.app`
- [ ] Update `APP_BASE_URL` with this URL

### 7. Test
- [ ] Visit your Railway URL
- [ ] Test signup: `/signup`
- [ ] Test login: `/login`
- [ ] Test dashboard: `/dashboard`
- [ ] Check browser DevTools → Application → Cookies (should see `jet_session`)

## 🔧 Troubleshooting

### Database Connection Error
- Check `DATABASE_URL` is set
- Check PostgreSQL service is running
- Check logs for connection errors

### Authentication Not Working
- Check cookies are being set (DevTools → Application → Cookies)
- Check `SESSION_SECRET` is set
- Check `FLASK_ENV=production` is set
- Check CORS configuration

### App Won't Start
- Check `Procfile` is correct: `app_production:app`
- Check `requirements_production.txt` has all dependencies
- Check Railway logs for errors

## 📝 After Deployment

### Create Admin User
```bash
# SSH into Railway or use Railway CLI
railway run python create_admin.py admin@example.com AdminPass123
```

Or set environment variables:
```
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminPass123!
```

Then run migrations (which seeds admin):
```bash
railway run python migrations/run_migrations.py
```

## 🎯 Next: Add R2 (File Storage)

After basic site is working:

1. Create R2 bucket in Cloudflare
2. Get R2 credentials
3. Add to Railway environment variables:
   ```
   R2_ACCOUNT_ID=your-account-id
   R2_ACCESS_KEY_ID=your-access-key
   R2_SECRET_ACCESS_KEY=your-secret-key
   R2_BUCKET_NAME=your-bucket-name
   R2_PUBLIC_URL=https://your-bucket.r2.dev
   ```
4. Install boto3: Add to `requirements_production.txt`
5. Modify upload code to use R2
