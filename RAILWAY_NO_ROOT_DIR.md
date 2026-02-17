# Railway: Deploy Without Root Directory (use repo root)

Use these settings when **Root Directory** is **blank** so Railway runs the **full website** (root `app.py` — same as localhost:5015). Do **not** use Root Directory `legacy` if you want the full site; `legacy` runs `app_production`, which only serves a minimal app.

---

## Railway Settings

| Setting | Value |
|--------|--------|
| **Root Directory** | *(leave blank)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

Or leave **Start Command** blank so Railway uses the **Procfile** at the repo root:

```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

---

## Copy-paste

**Build Command**
```bash
pip install -r requirements.txt
```

**Start Command** (optional – only if you want to override the Procfile)
```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

---

## What runs

- **App:** Root `app.py` (same app as localhost:5015).
- **Routes:** Includes `/api/airports`, `/api/user-listings`, and all other root app routes.
- **Database:** SQLite at `instance/jet_finder.db` (ephemeral on Railway unless you add a volume).
- **Data files (must be committed):**
  - `static/data/airports.json` — airports (or fallback list if missing).
  - `Aircraft Data - Aircraft Data (1).csv` — aircraft + performance profiles (allowed via `.gitignore` exception).
- **Entry point:** `gunicorn app:app` loads root `app.py`, which registers `/api/airports`, `/api/aircraft-data`, `/api/performance-profiles`, `/api/user-listings`, `/api/health`.

---

## Environment variables (optional)

- **`APP_BASE_URL`** – Your public URL. **If you use jetschoolusa.com, set:**
  ```bash
  APP_BASE_URL=https://jetschoolusa.com
  ```
  (no trailing slash). Used by Stripe redirects and any URL generation.
- `SESSION_SECRET` – for session security.
- `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` – if using Stripe.
- `FLASK_ENV=production`

No `DATABASE_URL` required when using root app (it uses SQLite by default).

---

## Custom domain: jetschoolusa.com

1. In Railway: **Settings → Domains** → add custom domain **jetschoolusa.com** (and **www.jetschoolusa.com** if needed).
2. In your DNS (e.g. Cloudflare): add a CNAME for **jetschoolusa.com** (and **www** if used) pointing to the host Railway gives you (e.g. `your-app.up.railway.app`).
3. Set **Variables**: `APP_BASE_URL=https://jetschoolusa.com`.
4. Redeploy. The site and APIs will be served at **https://jetschoolusa.com** (and `/api/airports`, `/api/user-listings`, etc.).

---

## Verification tests (jetschoolusa.com)

After deploy, use these URLs to verify:

| Test | URL | Expected |
|------|-----|----------|
| **Health (data loaded)** | https://jetschoolusa.com/api/health | 200, JSON: `{"status":"ok","data_loaded":{"airports":N,"aircraft":N,"performance_profiles":N},"app":"app.py"}` |
| **Debug (which app)** | https://jetschoolusa.com/api/debug | 200, JSON: `{"app": "app.py", ...}` |
| **Airports** | https://jetschoolusa.com/api/airports?q=dfw | 200, JSON array of airport(s) |
| **Aircraft data** | https://jetschoolusa.com/api/aircraft-data | 200, JSON array of aircraft |
| **Performance profiles** | https://jetschoolusa.com/api/performance-profiles | 200, JSON array of profiles |
| **User listings** | https://jetschoolusa.com/api/user-listings | 200 with session cookie, or 401 without |

**Copy-paste:**

```text
https://jetschoolusa.com/api/health
https://jetschoolusa.com/api/debug
https://jetschoolusa.com/api/airports?q=dfw
https://jetschoolusa.com/api/aircraft-data
https://jetschoolusa.com/api/performance-profiles
https://jetschoolusa.com/api/user-listings
```

**To get the full website (jetschoolusa.com like localhost:5015):**

- **Root Directory** = *(leave blank)*
- **Start command** = `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- **Ensure these files are committed** (not ignored):
  - `app.py`, `requirements.txt`
  - `Aircraft Data - Aircraft Data (1).csv` (aircraft + profiles; allowed via `.gitignore` exception)
  - `static/data/airports.json` (already tracked)
  - First time adding the CSV: `git add -f "Aircraft Data - Aircraft Data (1).csv"`
