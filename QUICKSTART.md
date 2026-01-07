# Jet Finder - Quick Start Guide

Get your Cloudflare-based aircraft listing platform up and running in 30 minutes.

## Prerequisites Checklist

- [ ] Node.js 18+ installed
- [ ] Cloudflare account created
- [ ] Supabase account created
- [ ] Domain `jetschoolusa.com` ready (or use subdomain)

## Step 1: Clone & Install (5 min)

```bash
# Install backend dependencies
cd workers
npm install

# Install frontend dependencies
cd ../frontend
npm install
```

## Step 2: Set Up Supabase (5 min)

1. Go to [supabase.com](https://supabase.com) and create a project
2. Copy your project URL and API keys:
   - Settings → API → Project URL
   - Settings → API → `anon` key
   - Settings → API → `service_role` key (keep secret!)
3. Configure auth redirect URLs:
   - Authentication → URL Configuration
   - Add: `http://localhost:5173/auth/callback` (dev)
   - Add: `https://jetschoolusa.com/auth/callback` (prod)

## Step 3: Set Up Cloudflare Resources (10 min)

### Create D1 Database

```bash
cd workers
wrangler d1 create jetfinder-db
```

Copy the `database_id` from output and update `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "jetfinder-db"
database_id = "PASTE_ID_HERE"
```

### Create R2 Buckets

```bash
wrangler r2 bucket create jetfinder-images
wrangler r2 bucket create jetfinder-videos
```

### Create KV Namespace

```bash
wrangler kv:namespace create "CACHE"
```

Copy the `id` from output and update `wrangler.toml`.

### Run Database Migrations

```bash
# Local (for testing)
wrangler d1 migrations apply jetfinder-db --local

# Production
wrangler d1 migrations apply jetfinder-db
```

## Step 4: Configure Environment Variables (5 min)

### Backend (Workers)

Create `workers/.dev.vars` for local development:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
FRONTEND_URL=http://localhost:5173
```

For production, set secrets:

```bash
cd workers
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_ANON_KEY
wrangler secret put SUPABASE_SERVICE_KEY
wrangler secret put FRONTEND_URL
```

### Frontend

Create `frontend/.env.local`:

```env
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_URL=http://localhost:8787
```

## Step 5: Run Locally (5 min)

### Terminal 1: Backend Worker

```bash
cd workers
wrangler dev
```

Worker runs at `http://localhost:8787`

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173`

## Step 6: Deploy to Production

### Deploy Backend

```bash
cd workers
npm run deploy
```

Note the Worker URL (e.g., `jetfinder-api.xxxxx.workers.dev`)

Update `frontend/.env.production` with Worker URL:

```env
VITE_API_URL=https://jetfinder-api.xxxxx.workers.dev
```

### Deploy Frontend

**Option A: Cloudflare Pages Dashboard**

1. Push code to GitHub/GitLab
2. Cloudflare Dashboard → Pages → Connect Repository
3. Configure:
   - Build command: `cd frontend && npm install && npm run build`
   - Output directory: `frontend/dist`
   - Root: `/`
4. Add environment variables in Pages dashboard

**Option B: Wrangler CLI**

```bash
cd frontend
npm run build
npx wrangler pages deploy dist --project-name=jetfinder-frontend
```

## Step 7: Connect Domain

1. Cloudflare Dashboard → Pages → Your Project → Custom domains
2. Add `jetschoolusa.com`
3. Cloudflare automatically:
   - Configures DNS
   - Provisions SSL
   - Sets up HTTPS

## Step 8: Create Admin User

1. Sign up via your frontend (creates Supabase user)
2. Get your user ID from Supabase Dashboard → Authentication → Users
3. Mark as admin in D1:

```bash
wrangler d1 execute jetfinder-db --command "UPDATE users SET is_admin = 1 WHERE id = 'USER_UUID_HERE';"
```

## Step 9: Test Workflow

1. ✅ Sign up for account
2. ✅ Create a listing
3. ✅ Log in as admin
4. ✅ Approve listing via `/admin`
5. ✅ View listing publicly on `/`

## Troubleshooting

**Worker not connecting:**
- Check `wrangler.toml` has correct database/bucket IDs
- Verify secrets are set: `wrangler secret list`

**Auth not working:**
- Verify Supabase redirect URLs match your domain
- Check browser console for errors
- Ensure API keys are correct in `.env` files

**Database errors:**
- Run migrations: `wrangler d1 migrations apply jetfinder-db`
- Check D1 console: `wrangler d1 execute jetfinder-db --command "SELECT * FROM users LIMIT 1;"`

**Images not uploading:**
- Verify R2 buckets exist: `wrangler r2 bucket list`
- Check bucket permissions in Cloudflare dashboard

## Next Steps

- [ ] Add seed data (performance profiles, example listings)
- [ ] Configure R2 public access for images
- [ ] Set up monitoring/alerts
- [ ] Configure custom domain for R2 buckets
- [ ] Set up email notifications

## Support

- 📖 Full deployment guide: `DEPLOYMENT.md`
- 📚 Architecture docs: `README_CLOUDFLARE.md`
- 🔧 Cloudflare Docs: https://developers.cloudflare.com/
- 🔐 Supabase Docs: https://supabase.com/docs

