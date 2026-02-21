# Project layout

One-page map of the repo. **What runs the site** vs config vs data.

---

## Run the site

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5015**. For production (Railway), see **[DEPLOY.md](DEPLOY.md)**.

---

## Core (what runs)

| Path | Purpose |
|------|--------|
| **app.py** | Main Flask app: routes, auth, APIs, pages. Entry point. |
| **db.py** | Database layer: Postgres (Railway) or SQLite (local). Users, listings, subscriptions. |
| **marketplace.py** | Marketplace blueprint: charter search, empty legs, parts, listings. |

---

## Optional integrations (`integrations/`)

| Path | Purpose |
|------|--------|
| **integrations/enhanced_data_manager.py** | Loads aircraft records and user preferences; used for recommendations. |
| **integrations/avinode_integration.py** | Avinode API client; used if configured. |
| **integrations/__init__.py** | Exposes `enhanced_data_manager` and `avinode_client`; handles missing deps. |

If the package or a module is missing, the app still runs (with fallbacks).

---

## Data files (read at runtime)

| Path | Purpose |
|------|--------|
| **static/data/aircraft_data.csv** | Aircraft list (primary). Used for profiles and listings. |
| **static/data/airports.json** | Airports (primary). Used for search/autocomplete. |
| **Aircraft Data - Aircraft Data (1).csv** | Fallback aircraft CSV if `static/data/aircraft_data.csv` is missing. |
| **airports.json** (root) | Fallback airports if `static/data/airports.json` is missing. |
| **data/** | Optional JSON (e.g. listings.json, users.json) if used by other tools. |

---

## Frontend (templates + static)

| Path | Purpose |
|------|--------|
| **templates/** | Jinja2 HTML templates. Rendered by Flask. |
| **static/** | CSS, JS, images. Served at `/static/`. `static/data/` holds the CSVs/JSON above. |

---

## Config and deploy

| Path | Purpose |
|------|--------|
| **requirements.txt** | Python dependencies. |
| **Procfile** | Start command for Railway: `gunicorn app:app ...` |
| **runtime.txt** | Python version for Railway. |
| **railway.toml** | Railway project config. |
| **.env** | Local env vars (not committed). Use for `DATABASE_URL`, Stripe keys, etc. |

---

## Generated / runtime (do not edit)

| Path | Purpose |
|------|--------|
| **instance/** | SQLite DB file when using local DB (`instance/jet_finder.db`). |
| **uploads/** | User-uploaded files. |
| **logs/** | Log files. |
| **.venv/** | Python virtualenv. |
| **__pycache__/** | Python bytecode. |

---

## Docs

| Path | Purpose |
|------|--------|
| **README.md** | Overview and how to run. |
| **DEPLOY.md** | How to deploy to Railway (only deployment guide). |
| **PROJECT_LAYOUT.md** | This file. |

---

## Other at root

- **package.json**, **node_modules/**, **vite.config.js**, **tailwind.config.js**, **tsconfig.*.***  
  Leftover from an old frontend build. Not required to run the Flask app. Safe to remove if you don’t use them.
- **.gitignore**, **.vscode/**, **.pylintrc**, **pyrightconfig.json**  
  Editor and tooling config.
- **credentials.json**, **token.json**  
  Secrets (e.g. Google). Usually in `.gitignore`; don’t commit.
