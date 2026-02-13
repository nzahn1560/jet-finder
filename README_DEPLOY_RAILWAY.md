# Jet Finder - Railway Deployment Guide

Complete production deployment guide for Railway with PostgreSQL.

## 🎯 Architecture Overview

- **Single Origin**: Backend serves both API (`/api/*`) and frontend pages
- **Database**: Railway Postgres (auto-provisioned)
- **Payments**: Stripe Checkout for listing fees
- **Storage**: S3/Cloudflare R2 for photos/videos (URLs stored in DB)
- **Auth**: Cookie-based sessions (HttpOnly, Secure, SameSite)

---

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Stripe Account**: Get API keys at [stripe.com](https://stripe.com)
3. **GitHub Repository**: Push your code to GitHub
4. **S3/R2 Setup** (optional): For photo/video uploads

---

## 🚀 Railway Deployment Steps

### Step 1: Create New Project

1. Log into Railway
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `jet-finder` repository
5. Railway will auto-detect the Flask app

### Step 2: Add PostgreSQL Database

1. In your project, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway automatically sets `DATABASE_URL` env var
4. Wait for database to provision (1-2 minutes)

### Step 3: Configure Environment Variables

Go to your service → **"Variables"** tab and add:

#### Required Variables

```bash
# Session Security
SESSION_SECRET=<generate-random-32-char-string>

# Stripe Payment
STRIPE_SECRET_KEY=sk_live_xxxxx  # or sk_test_xxxxx for testing
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx  # or pk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx  # from Stripe dashboard

# App Configuration
APP_BASE_URL=https://your-app.up.railway.app  # Railway provides this
FLASK_ENV=production
PORT=5015
```

#### Optional Variables

```bash
# If using S3 for media uploads
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# Or Cloudflare R2
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_key
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET_NAME=your-bucket
```

### Step 4: Configure Build Settings

In Railway → **"Settings"**:

- **Root Directory**: `legacy/`
- **Build Command**: `pip install -r requirements_production.txt`
- **Start Command**: `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### Step 5: Deploy

1. Railway will automatically build and deploy
2. Check deployment logs for any errors
3. Get your public URL from Railway dashboard

### Step 6: Initialize Database

Railway will auto-run database migrations on first deploy via `models.py`.

To manually initialize:

```bash
# Using Railway CLI
railway run python -c "from models import init_db; init_db()"
```

### Step 7: Create Admin User

You need at least one admin to approve listings:

```python
# Create a script: create_admin.py
from models import SessionLocal, User
from werkzeug.security import generate_password_hash

db = SessionLocal()
admin = User(
    email='admin@jetfinder.com',
    password_hash=generate_password_hash('your-secure-password'),
    is_admin=True
)
db.add(admin)
db.commit()
print("✅ Admin created!")
```

Run it:

```bash
railway run python create_admin.py
```

### Step 8: Configure Stripe Webhook

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click **"Add endpoint"**
3. Enter URL: `https://your-app.up.railway.app/api/billing/webhook/stripe`
4. Select events: `checkout.session.completed`
5. Copy the webhook secret to Railway env var `STRIPE_WEBHOOK_SECRET`

---

## 🧪 Testing Your Deployment

### Test Locally First

```bash
# In legacy/ directory
export DATABASE_URL="postgresql://localhost/jet_finder_dev"
export SESSION_SECRET="dev-secret"
export STRIPE_SECRET_KEY="sk_test_xxxxx"
export STRIPE_WEBHOOK_SECRET="whsec_xxxxx"
export APP_BASE_URL="http://localhost:5015"

# Install dependencies
pip install -r requirements_production.txt

# Initialize database
python -c "from models import init_db; init_db()"

# Run app
python app_production.py
```

Visit `http://localhost:5015` and test:
- ✅ Sign up / Login
- ✅ Create listing
- ✅ Pay for listing (use Stripe test card: `4242 4242 4242 4242`)
- ✅ Admin review (log in as admin)
- ✅ Public listing view

### Test on Railway

1. **Sign Up**: Visit `/signup` and create account
2. **Create Listing**: Go to `/dashboard` and create a test listing
3. **Pay**: Click "Pay & Submit" (use test card in test mode)
4. **Admin Review**: Log in as admin at `/admin`
5. **Approve**: Approve the listing
6. **Public View**: Visit `/` to see approved listing

---

## 📊 Acceptance Tests Checklist

Run these tests to verify production behavior:

- [ ] **User Auth**
  - [ ] User can sign up with email/password
  - [ ] User can log in
  - [ ] User stays logged in on page refresh
  - [ ] Cookie is HttpOnly and Secure
  
- [ ] **Listings Ownership**
  - [ ] User creates listing → appears in their dashboard only
  - [ ] User cannot edit another user's listing (403 error)
  - [ ] Draft listings not visible publicly
  
- [ ] **Payment Flow**
  - [ ] Unpaid listing shows "Pay & Submit" button
  - [ ] Stripe checkout opens correctly
  - [ ] Successful payment moves listing to "pending"
  - [ ] Webhook updates listing status
  
- [ ] **Admin Review**
  - [ ] Admin sees all pending listings at `/admin`
  - [ ] Admin can approve → listing becomes public
  - [ ] Admin can reject with reason → owner sees reason
  - [ ] Non-admin cannot access `/admin` (403)
  
- [ ] **Public View**
  - [ ] Only approved/active listings visible on `/`
  - [ ] Pending/draft/rejected listings not visible
  - [ ] Listing detail page works for public listings

---

## 🔒 Security Checklist

- [ ] `SESSION_SECRET` is a strong random string
- [ ] `STRIPE_WEBHOOK_SECRET` is configured
- [ ] Cookies set with `Secure` in production
- [ ] Cookies set with `HttpOnly=True`
- [ ] Cookies set with `SameSite=Lax`
- [ ] Database uses PostgreSQL (not SQLite in production)
- [ ] Admin status checked on all admin routes
- [ ] Ownership checked on all edit/delete operations
- [ ] Payment verification done via webhook only (never trust client)

---

## 🐛 Troubleshooting

### Database Connection Errors

```
Error: could not connect to server
```

**Solution**: Railway auto-sets `DATABASE_URL`. Ensure your `models.py` reads it:

```python
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
```

### Stripe Webhook Not Working

```
Error: No signatures found matching the expected signature for payload
```

**Solutions**:
1. Verify `STRIPE_WEBHOOK_SECRET` is set correctly in Railway
2. Check webhook URL in Stripe dashboard matches Railway URL
3. Test webhook using Stripe CLI: `stripe listen --forward-to localhost:5015/api/billing/webhook/stripe`

### 404 on Frontend Pages

```
Error: 404 Not Found
```

**Solution**: Ensure Railway build settings point to correct directory:
- Root Directory: `legacy/`
- Start Command includes `app_production:app`

### Cookie Not Persisting

```
User logged out on refresh
```

**Solutions**:
1. Check `FLASK_ENV=production` is set in Railway
2. Verify `APP_BASE_URL` matches your Railway domain
3. Ensure `credentials: 'include'` in all frontend fetch calls

---

## 📦 Required Files Checklist

Ensure these files exist in your repository:

- [ ] `legacy/models.py` - Database models
- [ ] `legacy/auth.py` - Authentication system
- [ ] `legacy/listings_api.py` - Listings CRUD
- [ ] `legacy/billing_api.py` - Stripe integration
- [ ] `legacy/app_production.py` - Main app file
- [ ] `legacy/requirements_production.txt` - Python dependencies
- [ ] `legacy/templates/auth/signup.html`
- [ ] `legacy/templates/auth/login.html`
- [ ] `legacy/templates/dashboard/index.html`
- [ ] `legacy/templates/admin/index.html`

---

## 🎉 Production Ready!

If all tests pass, your app is ready for production use!

**Next Steps**:
1. Configure custom domain in Railway
2. Set up monitoring/logging
3. Configure backup schedule for PostgreSQL
4. Add rate limiting for API endpoints
5. Set up error tracking (Sentry, etc.)

---

## 📞 Support

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Check Stripe logs: Stripe Dashboard → Developers → Logs
3. Test locally first with test API keys
4. Verify all environment variables are set

---

## 🔄 Updates & Migrations

To deploy updates:

```bash
git push origin main
```

Railway will automatically redeploy.

To run database migrations:

```bash
railway run python -c "from models import init_db; init_db()"
```

---

**Last Updated**: February 2026  
**Version**: 1.0.0  
**Status**: Production Ready ✅
