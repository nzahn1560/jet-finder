# Fix: API URL Not Resolving

## Problem
Your frontend is trying to use `api.jetschoolusa.com` but the DNS isn't set up yet, so it fails with `ERR_NAME_NOT_RESOLVED`.

## Solution: Use Worker URL Directly

**In Cloudflare Pages → Settings → Environment Variables → Production:**

Change:
- `VITE_API_URL` = `https://api.jetschoolusa.com` ❌ (doesn't exist yet)

To:
- `VITE_API_URL` = `https://jetschoolusa-api.nick-zahn777.workers.dev` ✅ (works now)

## After Updating

1. Go to Deployments tab
2. Click "Retry deployment" on the latest build
3. Wait for rebuild to complete
4. Your site should work!

## Optional: Set Up Custom Domain Later

Once you want to use `api.jetschoolusa.com`:

1. Go to Cloudflare Dashboard → Workers & Pages → Your Worker
2. Go to Settings → Triggers → Custom Domains
3. Add `api.jetschoolusa.com`
4. Cloudflare will tell you which DNS record to add
5. Add the DNS record in Cloudflare DNS
6. Then update `VITE_API_URL` back to `https://api.jetschoolusa.com`

