# Quick Start - Production System

## 🚀 Test Locally (5 minutes)

### 1. Install Dependencies
```bash
cd legacy/
pip install -r requirements_production.txt
```

### 2. Set Environment Variables
```bash
export DATABASE_URL="postgresql://localhost/jet_finder_dev"
export SESSION_SECRET="dev-secret-change-this"
export STRIPE_SECRET_KEY="sk_test_YOUR_KEY"
export STRIPE_PUBLISHABLE_KEY="pk_test_YOUR_KEY"
export STRIPE_WEBHOOK_SECRET="whsec_YOUR_SECRET"
export APP_BASE_URL="http://localhost:5015"
export FLASK_ENV="development"
```

### 3. Initialize Database
```bash
python -c "from models import init_db; init_db()"
```

### 4. Create Admin User
```bash
python create_admin.py admin@test.com AdminPass123
```

### 5. Run App
```bash
python app_production.py
```

Visit: `http://localhost:5015`

---

## 🧪 Test Workflow

### As User:
1. Visit `/signup` - Create account
2. Visit `/dashboard` - Create listing
3. Click "Pay & Submit" - Use test card: `4242 4242 4242 4242`
4. Listing status → PENDING

### As Admin:
1. Visit `/login` - Log in as admin
2. Visit `/admin` - See pending listing
3. Click "Approve" - Listing becomes ACTIVE

### As Public:
1. Visit `/` - See approved listing

---

## 🌐 Deploy to Railway (10 minutes)

### 1. Push to GitHub
```bash
git add .
git commit -m "Production system ready"
git push origin main
```

### 2. Create Railway Project
1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select your repo

### 3. Add PostgreSQL
1. New → Database → PostgreSQL
2. Wait for provisioning

### 4. Set Environment Variables
```
SESSION_SECRET=<generate-random-32-chars>
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
APP_BASE_URL=https://your-app.up.railway.app
FLASK_ENV=production
```

### 5. Configure Build
- Root Directory: `legacy/`
- Build: `pip install -r requirements_production.txt`
- Start: `gunicorn app_production:app --bind 0.0.0.0:$PORT`

### 6. Deploy
Railway will auto-deploy. Check logs for any errors.

### 7. Create Admin
```bash
railway run python create_admin.py admin@yoursite.com SecurePass123
```

### 8. Configure Stripe Webhook
1. Stripe Dashboard → Webhooks
2. Add endpoint: `https://your-app.up.railway.app/api/billing/webhook/stripe`
3. Select: `checkout.session.completed`
4. Copy webhook secret to Railway env vars

---

## ✅ Production Checklist

Before going live:
- [ ] PostgreSQL database created
- [ ] All environment variables set
- [ ] Admin user created
- [ ] Stripe webhook configured
- [ ] Test signup/login works
- [ ] Test listing creation works
- [ ] Test payment works (test mode first!)
- [ ] Test admin approval works
- [ ] Test public listing view works

---

## 📊 Key Endpoints

### Public
- `GET /` - Home page (active listings)
- `GET /listing/:id` - Listing detail

### Auth
- `GET /signup` - Sign up page
- `GET /login` - Login page
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Log in
- `POST /api/auth/logout` - Log out
- `GET /api/auth/me` - Get current user

### User
- `GET /dashboard` - User dashboard
- `GET /api/listings/me/listings` - Get my listings
- `POST /api/listings` - Create listing
- `PATCH /api/listings/:id` - Update listing
- `POST /api/listings/:id/submit` - Submit for review
- `POST /api/billing/listing-checkout` - Pay listing fee

### Admin
- `GET /admin` - Admin panel
- `GET /api/listings/admin/pending` - Get pending listings
- `POST /api/listings/admin/:id/approve` - Approve listing
- `POST /api/listings/admin/:id/reject` - Reject listing

### Webhook
- `POST /api/billing/webhook/stripe` - Stripe webhook

---

## 🐛 Troubleshooting

### "Cannot connect to database"
- Check `DATABASE_URL` is set correctly
- For Railway: Make sure PostgreSQL service is running

### "Session cookie not persisting"
- Check `SESSION_SECRET` is set
- Check `FLASK_ENV=production` in Railway
- Verify `credentials: 'include'` in fetch calls

### "Stripe webhook signature invalid"
- Verify `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
- Check webhook URL in Stripe is correct
- Test with Stripe CLI: `stripe listen --forward-to localhost:5015/api/billing/webhook/stripe`

### "403 Forbidden on admin page"
- Make sure you're logged in as admin user
- Check `is_admin=True` in database for your user

---

## 🎯 Expected Behavior

### Listing Lifecycle
```
1. User creates listing → Status: UNPAID
2. User pays $50 via Stripe → Status: PENDING
3. Admin approves → Status: ACTIVE (public sees it)
   OR Admin rejects → Status: REJECTED (owner sees reason)
```

### User Permissions
- Users can only see/edit their own listings
- Users cannot see other users' private listings
- Admin can see all listings
- Public can only see ACTIVE listings

### Payment Flow
```
User clicks "Pay & Submit"
  → Stripe Checkout opens
  → User enters card (test: 4242 4242 4242 4242)
  → Payment succeeds
  → Stripe webhook fires
  → Backend verifies signature
  → Backend marks payment as PAID
  → Backend moves listing to PENDING
  → User sees "Under Review" in dashboard
```

---

## 📞 Support

Need help?
1. Check Railway logs: `railway logs`
2. Check Stripe dashboard logs
3. Review `README_DEPLOY_RAILWAY.md` for detailed guide
4. Review `PRODUCTION_SYSTEM_SUMMARY.md` for complete documentation

---

**Ready to go!** 🚀

The system is production-ready and follows all best practices for security, scalability, and user experience.
