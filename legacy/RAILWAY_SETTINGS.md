# Railway Settings (Root Directory = `legacy`)

Use these in your Railway service **Settings** and **Variables**.

---

## Build & Start

| Setting | Value |
|--------|--------|
| **Root Directory** | `legacy` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| **Watch Paths** | *(leave blank)* |

- **Build Command:** Installs deps from `legacy/requirements.txt`. Railway runs this from repo root then uses Root Directory, so the build context is `legacy/` and `requirements.txt` is `legacy/requirements.txt`.
- **Start Command:** Override the Procfile so the **full app** (`app.py`) runs. That gives you `/api/airports`, `/api/user-listings`, and all other routes.  
  If you prefer the minimal production app only, use:  
  `gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`  
  (then `/api/airports` and `/api/user-listings` will not exist unless you add them back to `app_production.py`.)

---

## Optional: Pre-deploy / Release command

Railway doesn’t have a separate “pre-deploy” field. You can use a **Release Command** if your project has one (e.g. in `railway.toml` or Nixpacks):

```bash
python -c "from models import init_db; init_db()"
```

Only needed if you want to run DB init before the app starts. The app already runs `init_db()` on startup when using `app_production`, and `app.py` has its own DB setup.

---

## Environment variables

In **Variables** (or **Settings → Variables**), set:

| Variable | Example | Notes |
|----------|---------|--------|
| `DATABASE_URL` | *(auto from Postgres)* | From Railway Postgres plugin. |
| `SESSION_SECRET` | `openssl rand -hex 32` | Required for auth cookies. |
| `APP_BASE_URL` | `https://your-app.up.railway.app` | Your public URL (no trailing slash). |
| `FLASK_ENV` | `production` | Optional. |
| `STRIPE_SECRET_KEY` | `sk_live_...` or `sk_test_...` | If using Stripe. |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` or `pk_test_...` | If using Stripe. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | For Stripe webhooks. |

---

## Summary (copy-paste)

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command (full app – recommended so `/api/airports` and `/api/user-listings` work)**

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**Start Command (minimal production app only)**

```bash
gunicorn app_production:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

**Release / pre-start (optional)**

```bash
python -c "from models import init_db; init_db()"
```

---

**Note:** `legacy/requirements.txt` includes deps for both `app.py` and `app_production.py`, so one build works for either start command.
