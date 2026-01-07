# JetSchoolUSA - Cloudflare Project Structure

## ✅ What's Included (Cloudflare-Ready)

### `/frontend/` - React Frontend (Cloudflare Pages)
- React + Vite + Tailwind CSS
- All pages and components
- Environment variables: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- Builds to `frontend/dist/`

### `/worker-api/` - Cloudflare Worker Backend
- TypeScript API routes
- D1 database migrations
- R2 storage for media
- Supabase authentication
- Deployed to: `jetschoolusa-api.nick-zahn777.workers.dev`

### `/infra/` - Infrastructure Scripts
- Database backup scripts
- Smoke tests

### Documentation Files
- `README.md` - Main project documentation
- `CLOUDFLARE_PAGES_SETUP.md` - Frontend deployment guide
- `README_CLOUDFLARE.md` - Architecture details

## ❌ What's Excluded (Not Cloudflare-Compatible)

All Python/Flask files are ignored via `.gitignore`:
- `app.py` - Python Flask app (not used)
- `backend/` - Python FastAPI backend (not used)
- `workers/` - Old worker folder (use `worker-api/` instead)
- `static/` - Old static files (use `frontend/public/` instead)
- `templates/` - Old HTML templates (use React components instead)
- `requirements.txt` - Python dependencies (not needed)
- `*.py` files - All Python scripts

## 🚀 Deployment Flow

1. **Frontend (Cloudflare Pages):**
   - Connected to GitHub
   - Auto-deploys on push to `main`
   - Builds from `frontend/` directory

2. **Backend (Cloudflare Worker):**
   - Deployed via `wrangler deploy`
   - Uses D1 database
   - Uses R2 for storage

## 📝 Notes

- No Python runtime needed
- No Docker needed
- Everything runs on Cloudflare edge network
- Serverless and scalable

