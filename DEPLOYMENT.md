# JetSchoolUSA - Full Cloud Deployment Guide

Complete step-by-step guide to deploy JetSchoolUSA to Cloudflare production environment.

## Prerequisites

1. **Cloudflare Account**: Sign up at [cloudflare.com](https://www.cloudflare.com)
2. **Supabase Account**: Sign up at [supabase.com](https://supabase.com) for authentication
3. **Domain**: jetschoolusa.com (or your domain) configured in Cloudflare
4. **Node.js**: v18+ installed locally
5. **Git**: Version control repository
6. **Wrangler CLI**: `npm install -g wrangler`

## Step 1: Set Up Supabase Authentication (15 minutes)

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Create a new project (e.g., "jetschoolusa")
3. Note down your credentials:
   - **Project URL**: `https://xxxxx.supabase.co` (Settings → API)
   - **Anon Key**: Public anon key (Settings → API)
   - **Service Role Key**: Secret service key (Settings → API) ⚠️ **Keep this secret!**

4. Configure Supabase Auth:
   - Navigate to: Authentication → URL Configuration
   - Add redirect URLs:
     - Production: `https://jetschoolusa.com/auth/callback`
     - Local dev: `http://localhost:5173/auth/callback`
   - Enable email authentication

5. Create your admin user:
   - Authentication → Users → Add User
   - Email: `admin@example.com` (use your real email)
   - Set temporary password
   - Note the user UUID

## Step 2: Create Cloudflare D1 Database (5 minutes)

```bash
cd worker-api
npm install

# Create D1 database
wrangler d1 create jetschoolusa-db

# Note the database_id from output, e.g.:
# database_id = "abc123def456..."
```

Update `worker-api/wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "jetschoolusa-db"
database_id = "PASTE_YOUR_DATABASE_ID_HERE"  # From previous command
```

## Step 3: Create Cloudflare R2 Buckets (5 minutes)

```bash
# Create images bucket
wrangler r2 bucket create jetschoolusa-images

# Create videos bucket
wrangler r2 bucket create jetschoolusa-videos
```

Configure R2 public access:
1. Go to Cloudflare Dashboard → R2
2. For each bucket (`jetschoolusa-images`, `jetschoolusa-videos`):
   - Click "Manage R2 API Token"
   - Create public bucket (or use custom domain)
   - Note the public URL pattern: `https://pub-xxxxx.r2.dev`

## Step 4: Create Cloudflare KV Namespace (2 minutes)

```bash
# Create KV namespace for caching and rate limiting
wrangler kv:namespace create "CACHE"

# Note the id from output
# For preview:
wrangler kv:namespace create "CACHE" --preview
```

Update `worker-api/wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "CACHE"
id = "PASTE_YOUR_KV_ID_HERE"
preview_id = "PASTE_YOUR_PREVIEW_KV_ID_HERE"
```

## Step 5: Run Database Migrations (5 minutes)

```bash
cd worker-api

# Test migrations locally first
wrangler d1 migrations apply jetschoolusa-db --local

# Run migrations in production
wrangler d1 migrations apply jetschoolusa-db
```

Verify schema:
```bash
wrangler d1 execute jetschoolusa-db --command "SELECT name FROM sqlite_master WHERE type='table';"
```

## Step 6: Seed Initial Data (5 minutes)

```bash
# Run seed script
wrangler d1 execute jetschoolusa-db --file ../database/seed.sql
```

**Important**: Create your admin user:
1. Sign up via Supabase Auth UI with your admin email
2. Get the user UUID from Supabase Dashboard → Authentication → Users
3. Mark as admin in D1:

```bash
wrangler d1 execute jetschoolusa-db --command "UPDATE users SET is_admin = 1 WHERE supabase_user_id = 'YOUR_SUPABASE_USER_UUID';"
```

## Step 7: Configure Environment Variables (5 minutes)

Set secrets for Workers (these are encrypted):

```bash
cd worker-api

# Supabase credentials
wrangler secret put SUPABASE_URL
# Paste: https://xxxxx.supabase.co

wrangler secret put SUPABASE_ANON_KEY
# Paste your Supabase anon key

wrangler secret put SUPABASE_SERVICE_KEY
# Paste your Supabase service role key

# Frontend URL
wrangler secret put FRONTEND_URL
# Paste: https://jetschoolusa.com
```

Or set in Cloudflare Dashboard:
- Workers & Pages → Your Worker → Settings → Variables → Encrypted

## Step 8: Deploy Cloudflare Workers (Backend) (5 minutes)

```bash
cd worker-api
npm run deploy

# Note the Worker URL from output:
# https://jetschoolusa-api.your-subdomain.workers.dev
```

Verify deployment:
```bash
curl https://jetschoolusa-api.your-subdomain.workers.dev/api/health
```

## Step 9: Deploy Frontend to Cloudflare Pages (10 minutes)

### Option A: Via Git Integration (Recommended)

1. Push your code to GitHub/GitLab/Bitbucket

2. Go to Cloudflare Dashboard → Pages → Create a project

3. Connect your repository

4. Configure build settings:
   - **Framework preset**: Vite
   - **Build command**: `cd frontend && npm install && npm run build`
   - **Build output directory**: `frontend/dist`
   - **Root directory**: `/`

5. Add environment variables in Pages dashboard:
   - `VITE_SUPABASE_URL` = Your Supabase project URL
   - `VITE_SUPABASE_ANON_KEY` = Your Supabase anon key
   - `VITE_API_URL` = Your Worker URL (e.g., `https://jetschoolusa-api.xxxxx.workers.dev`)

6. Deploy!

### Option B: Via Wrangler CLI

```bash
cd frontend
npm install
npm run build

# Deploy to Pages
npx wrangler pages deploy dist --project-name=jetschoolusa-frontend
```

## Step 10: Connect Custom Domain (5 minutes)

1. Go to Cloudflare Dashboard → Pages → Your Project → Custom domains

2. Add custom domain: `jetschoolusa.com`

3. Cloudflare will automatically:
   - Create DNS records
   - Provision SSL certificate
   - Configure HTTPS

4. Wait for DNS propagation (5-60 minutes)

5. Verify HTTPS:
   ```bash
   curl -I https://jetschoolusa.com
   ```

## Step 11: Configure R2 Public Access (5 minutes)

For image/video serving:

1. Cloudflare Dashboard → R2 → Your bucket

2. Settings → Public Access:
   - Enable "Public Access" 
   - Or configure custom domain: `images.jetschoolusa.com`

3. Update CORS settings (if needed):
   - Allow origins: `https://jetschoolusa.com`
   - Allow methods: `GET, HEAD`

## Step 12: Run Smoke Tests (5 minutes)

```bash
cd infra
./smoke-tests.sh https://jetschoolusa-api.xxxxx.workers.dev YOUR_ADMIN_TOKEN
```

Expected results:
- ✅ Health check passed
- ✅ Listing creation works
- ✅ Image upload works
- ✅ Public listings endpoint works

## Step 13: Set Up Monitoring (Optional)

1. **Cloudflare Analytics** (built-in):
   - Dashboard → Workers & Pages → Analytics
   - Monitor requests, errors, CPU time

2. **Real-time Logs**:
   ```bash
   wrangler tail
   ```

3. **Error Tracking**:
   - Set up Sentry or similar service
   - Or use Cloudflare Workers Logs

## Verification Checklist

- [ ] Workers deployed and accessible
- [ ] Frontend deployed to Pages
- [ ] Custom domain connected with HTTPS
- [ ] Supabase auth working (sign up/login)
- [ ] D1 database migrations applied
- [ ] R2 buckets created and publicly accessible
- [ ] Admin user created and marked in database
- [ ] Can create listing
- [ ] Can upload images
- [ ] Admin dashboard accessible
- [ ] Listing approval workflow works
- [ ] Public listings display correctly

## Troubleshooting

### Workers not deploying
- Check `wrangler.toml` syntax
- Verify all secrets are set: `wrangler secret list`
- Check Cloudflare account limits
- Review deployment logs in dashboard

### Frontend not loading
- Verify environment variables in Pages dashboard
- Check build output directory is correct
- Verify API URL in frontend `.env`
- Check browser console for errors

### Auth not working
- Verify Supabase redirect URLs match your domain
- Check CORS settings
- Verify tokens in Network tab
- Ensure user exists in both Supabase and D1

### Images not loading
- Check R2 bucket permissions
- Verify public access enabled
- Check R2 URLs in database
- Verify CORS headers on R2

### Database errors
- Run migrations: `wrangler d1 migrations apply jetschoolusa-db`
- Check D1 console: `wrangler d1 execute jetschoolusa-db --command "SELECT * FROM users LIMIT 1;"`
- Verify database_id in wrangler.toml

## Cost Monitoring

Monitor costs in Cloudflare Dashboard:
- Workers: Requests and CPU time
- D1: Database reads/writes
- R2: Storage and operations
- Pages: Bandwidth (included in free tier)

Target: Stay under $250/month at scale (see README_CLOUDFLARE.md for breakdown)

## Support

- 📖 Quick Start: `QUICKSTART.md`
- 📚 Architecture: `README_CLOUDFLARE.md`
- 🔧 [Cloudflare Docs](https://developers.cloudflare.com/)
- 🔐 [Supabase Docs](https://supabase.com/docs)
