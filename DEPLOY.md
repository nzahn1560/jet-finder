# Deploy Jet Finder to Railway (single guide)

**Use only this file for deployment.** Other Railway/README docs in the repo are legacy; this is the source of truth.

---

## Repo layout (only what matters for deploy)

```
jet-finder/
  app.py              ← main Flask app (this runs)
  db.py               ← database layer (Postgres or SQLite)
  marketplace.py      ← marketplace blueprint
  integrations/       ← optional (enhanced_data_manager, avinode)
  Procfile            ← start command for Railway
  requirements.txt    ← Python deps
  static/
    data/
      aircraft_data.csv   ← aircraft list (must be in repo)
      airports.json       ← airports
  templates/          ← HTML
```

For a full map of the repo, see **PROJECT_LAYOUT.md**.

---

## What actually runs in production

| Thing | What it is |
|-------|------------|
| **App** | Flask app in **`app.py`** (project root) |
| **Server** | Gunicorn, started by the **Procfile**: `gunicorn app:app --bind 0.0.0.0:$PORT ...` |
| **Database** | PostgreSQL (Railway Postgres). If `DATABASE_URL` is not set, the app falls back to SQLite, which is **ephemeral** on Railway (data is lost on restart). |
| **Data files** | Aircraft: **`static/data/aircraft_data.csv`**. Airports: **`static/data/airports.json`**. Used to **seed** the DB on first run. Data is then read from **PostgreSQL/SQLite** (same as users/listings). |

So: one app (`app.py`), one start command (Procfile), one database (Postgres), data from the repo.

---

## Steps to deploy (do these in order)

### 1. Add PostgreSQL in Railway

- Open your Railway project.
- Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**.
- After it’s created, open your **web service** (the one that runs the app).
- Go to **Variables**. You should see **`DATABASE_URL`** (Railway often adds it when Postgres is in the same project). If not, add it and paste the Postgres connection URL from the database service.

Without this, the app uses SQLite and you’ll get empty or reset data.

### 2. Set Railway to use the repo root

- In the **web service** → **Settings** (or **Deploy**):
  - **Root Directory**: leave **empty** (so the repo root, where `app.py` and `Procfile` live, is the app root).
  - **Build Command**: leave empty. The repo has **nixpacks.toml** so Railway does a Python-only build (no `npm run build`).
  - **Start Command**: leave empty so Railway uses the **Procfile**:  
    `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### 3. Deploy

- Push your code; Railway will build and deploy.
- Or use **"Deploy"** in the dashboard to redeploy the latest commit.

### 4. Check that it worked

Open in a browser (use your real Railway URL):

- **`https://YOUR-APP.up.railway.app/api/diagnostic`**

You want to see something like:

- `has_database_url: true`
- `database_type: "postgresql"`
- `aircraft_file_found` and `airports_file_found` not `null`
- `db_ok: true`

If something is wrong, the same page shows what’s missing (no DB URL, files not found, etc.).

Then try:

- **`https://YOUR-APP.up.railway.app/api/health`**  
  → `db_ok: true`, and counts &gt; 0 for aircraft/airports if the data files are present.
- **`https://YOUR-APP.up.railway.app/api/airports?q=LA`**  
  → JSON list of airports (not 404, not empty unless no matches).

---

## If something’s wrong

| Diagnostic says | Do this |
|-----------------|--------|
| `has_database_url: false` or `database_type: "sqlite"` | Add/link Postgres and set `DATABASE_URL` (step 1). |
| `aircraft_file_found: null` or `airports_file_found: null` | Ensure **Root Directory** is blank and the repo has `static/data/aircraft_data.csv` and `static/data/airports.json`. Redeploy. |
| `db_ok: false` | Check `DATABASE_URL` and that Postgres is running. Look at Railway logs for connection errors. |

---

## What to ignore for deployment

- **Legacy folders** – if any remain, they are not used; **`app.py`** at the root is the entry point.
- **Multiple Railway *.md files** in the repo – treat this DEPLOY.md as the only deployment guide.
- **README.md** – it describes a different stack (React/FastAPI/Docker); production is the Flask app above.

---

## Summary

1. Add Postgres and set **`DATABASE_URL`**.  
2. Root Directory **blank**; start command from **Procfile**.  
3. Deploy.  
4. Check **`/api/diagnostic`** and **`/api/health`**.

That’s it. If you follow this and something still fails, the `/api/diagnostic` output (with secrets removed) is enough to debug the next step.
