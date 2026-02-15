# Railway Setup for app.py (localhost:5015)

## Quick Setup Steps

### 1. Files Updated ✅

**`Procfile` (repo root):**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**`requirements.txt` (repo root):**
- Contains all dependencies for `app.py`
- Flask, pandas, numpy, stripe, gunicorn, etc.

### 2. Railway Dashboard Configuration

**Service Settings:**
1. Railway Dashboard → Your Service → **Settings**
2. **Root Directory:** (leave blank - uses repo root) ✅
3. **Build Command:** (leave blank - auto-detects `requirements.txt`)
4. **Start Command:** (leave blank - uses `Procfile`)

**Environment Variables:**
- `SESSION_SECRET` = (generate: `openssl rand -hex 32`)
- `STRIPE_SECRET_KEY` = (if using Stripe)
- `STRIPE_PUBLISHABLE_KEY` = (if using Stripe)

### 3. Database

**Current:** `app.py` uses SQLite (`instance/jet_finder.db`)

**On Railway:**
- SQLite will work but data is **ephemeral** (lost on redeploy)
- For production, consider migrating to PostgreSQL

**To keep SQLite (simple):**
- No additional setup needed
- Railway will create `instance/` directory
- Data persists during service uptime

**To use PostgreSQL (production):**
1. Create PostgreSQL service in Railway
2. Modify `app.py` to use PostgreSQL (see migration guide)
3. Link PostgreSQL to your Flask service

### 4. Deploy

```bash
git add Procfile requirements.txt
git commit -m "Configure Railway for app.py deployment"
git push origin main
```

Railway will automatically:
1. Install dependencies from `requirements.txt`
2. Run `gunicorn app:app` from Procfile
3. Start your app

### 5. Verify

**Check Railway Logs:**
- Should see: `Collecting Flask==3.0.0`
- Should see: `Starting gunicorn app:app`
- Should see: `Running on http://0.0.0.0:$PORT`

**Visit Railway URL:**
- Your app should work just like `localhost:5015`

---

## Key Differences: Localhost vs Railway

| Feature | Localhost (5015) | Railway |
|---------|------------------|---------|
| **Start** | `python app.py` | `gunicorn app:app` (auto) |
| **Port** | `5015` (hardcoded) | `$PORT` (Railway assigns) |
| **Database** | SQLite (persistent) | SQLite (ephemeral) or PostgreSQL |
| **URL** | `http://localhost:5015` | `https://your-app.railway.app` |

---

## Important Notes

1. **Root Directory:** Leave blank (Railway uses repo root)
2. **Procfile:** Must be in repo root
3. **requirements.txt:** Must be in repo root
4. **Static/Templates:** Served from `static/` and `templates/` directories
5. **Database:** SQLite works but data is ephemeral on Railway

---

## Troubleshooting

**"Module not found"**
- Check `requirements.txt` has all dependencies
- Railway installs from repo root

**"App not starting"**
- Check Railway logs for errors
- Verify Procfile is correct
- Check port is using `$PORT` not hardcoded

**"Database errors"**
- SQLite: Ensure `instance/` directory is writable
- PostgreSQL: Check `DATABASE_URL` is set

---

## Next Steps

1. ✅ Procfile updated
2. ✅ requirements.txt created
3. 🔄 **Set Railway Root Directory to: (blank)**
4. 🔄 **Set SESSION_SECRET in Railway**
5. 🔄 **Commit and push**
6. 🔄 **Deploy on Railway**

Your `app.py` will run on Railway just like it runs on `localhost:5015`!
