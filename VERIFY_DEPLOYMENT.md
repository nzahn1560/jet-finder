# Cloudflare Pages Deployment Verification Checklist

## ✅ Step 1: Verify Build Settings

Go to: Cloudflare Dashboard → Workers & Pages → Your Pages Project → Settings → Builds & deployments

**Required Settings:**
- **Framework preset:** `Vite` (or `None` if Vite isn't available)
- **Root directory:** `frontend` ⚠️ CRITICAL
- **Build command:** `npm ci && npm run build`
- **Build output directory:** `dist` ⚠️ CRITICAL

## ✅ Step 2: Verify Environment Variables

Go to: Settings → Environment Variables → Production

**Required Variables:**
1. `VITE_API_URL` = `https://jetschoolusa-api.nick-zahn777.workers.dev`
2. `VITE_SUPABASE_URL` = `https://thjvacmcpvwxdrfouymp.supabase.co`
3. `VITE_SUPABASE_ANON_KEY` = (your full Supabase anon key)

**To check if they're set:**
- Go to Environment Variables
- Look for all 3 variables listed
- Make sure they're set for "Production" environment

## ✅ Step 3: Check Latest Deployment

Go to: Deployments tab

**What to look for:**
- Latest deployment should show "Success" (green) or "Building" (yellow)
- If it shows "Failed" (red), click on it to see the error
- Check the build logs for any errors

## ✅ Step 4: Test Your Site

Once deployment is successful:
1. Click on your Pages URL (e.g., `https://your-project.pages.dev`)
2. Open browser console (F12 → Console tab)
3. Check for any errors
4. Try logging in or using a feature

## Common Issues & Fixes

### Issue: Build fails with "Cannot find cwd: /opt/buildhome/repo/frontend"
**Fix:** Set Root directory to `frontend` in build settings

### Issue: Build succeeds but site shows blank page
**Fix:** Check that Build output directory is set to `dist`

### Issue: API calls fail with CORS errors
**Fix:** Verify `VITE_API_URL` is set correctly in environment variables

### Issue: "supabaseUrl is required" error
**Fix:** Make sure `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set

### Issue: Environment variables not working
**Fix:** 
1. Make sure variables start with `VITE_` (required for Vite)
2. Trigger a new build after adding variables
3. Variables must be set BEFORE the build runs

