# Cloudflare Pages Setup Instructions

## Build Settings

**Framework preset:** Vite (or "None")

**Root directory:** `frontend`

**Build command:** `npm ci && npm run build`

**Build output directory:** `dist`

## Environment Variables (Production)

Add these in Cloudflare Pages → Settings → Environment Variables:

- `VITE_API_URL` = `https://api.jetschoolusa.com`
- `VITE_SUPABASE_URL` = `https://thjvacmcpvwxdrfouymp.supabase.co`
- `VITE_SUPABASE_ANON_KEY` = (your full anon key)

**Important:** These must be set BEFORE building. If you add them after, trigger a new deploy by making a commit to the main branch.

## Force Redeploy

To trigger a new build with updated environment variables:

1. Make a small change (e.g., add a space to README.md)
2. Commit and push to main branch
3. Cloudflare will automatically rebuild

