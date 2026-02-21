# Jet Finder

Aircraft marketplace and ownership analysis: compare aircraft, list and search listings, charter search, and admin workflow.

**Deploying to Railway?** → **[DEPLOY.md](DEPLOY.md)**  
**Want to understand the repo?** → **[PROJECT_LAYOUT.md](PROJECT_LAYOUT.md)**

---

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5015**.

Uses SQLite by default (`instance/jet_finder.db`). Set `DATABASE_URL` to use Postgres (e.g. for production).

---

## What’s in the repo

- **app.py** – Main Flask app (routes, auth, APIs).
- **db.py** – Database layer (Postgres or SQLite): users, listings, subscriptions.
- **marketplace.py** – Marketplace blueprint (charter, empty legs, parts).
- **integrations/** – Optional: enhanced data manager, Avinode API client.
- **static/data/** – Aircraft CSV and airports JSON (used at runtime).
- **templates/** – Jinja2 HTML; **static/** – CSS, JS, images.

Full map: **[PROJECT_LAYOUT.md](PROJECT_LAYOUT.md)**.

---

## Config

- **.env** – `DATABASE_URL`, Stripe keys, etc. (not committed).
- **requirements.txt** – Python deps.
- **Procfile** – Used by Railway to start the app.

---

## Docs

| File | Purpose |
|------|--------|
| [DEPLOY.md](DEPLOY.md) | Deploy to Railway (only deployment guide). |
| [PROJECT_LAYOUT.md](PROJECT_LAYOUT.md) | Map of every folder and important file. |
