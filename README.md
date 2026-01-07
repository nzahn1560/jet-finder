# Jet Finder Full-Stack Platform

Modern aircraft marketplace and ownership analysis stack featuring:

- React (Vite + Tailwind CSS) frontend with React Query
- FastAPI + SQLModel backend with Alembic migrations
- SQLite database (local dev)
- Admin review workflow, seeded performance profiles, pricing plans, and listings
- Docker Compose orchestration & `start.sh` helper script

---

## Directory Layout

```
frontend/      # React client
backend/       # FastAPI server
database/      # Alembic migrations, seeds, SQLite db
docker-compose.yml
start.sh
```

---

## Requirements

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose

---

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

`start.sh` will:

1. Generate `.env` (if missing)
2. Install backend deps & run Alembic migrations
3. Seed performance profiles, pricing plans, admin user, and sample listings
4. Launch frontend + backend via Docker Compose

Services available at:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api

---

## Authentication / Admin

- Seeded admin: `admin@example.com`
- Temporary password: `Passw0rd!` (force reset recommended)
- Admin dashboard lives at `/admin`
- During scaffolding the frontend uses a stub bearer token (`token-1-admin@example.com`) that maps to the seeded admin user; replace with real auth flows in production.

---

## Key Commands

```bash
# Run migrations
cd backend && alembic upgrade head

# Seed database
python database/seed.py

# Run backend locally
cd backend && uvicorn app.main:app --reload

# Run frontend locally
cd frontend && npm install && npm run dev
```

---

## Environment Variables (`.env`)

```
DATABASE_URL=sqlite:///../database/jetfinder.db
FRONTEND_ORIGIN=http://localhost:5173
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Passw0rd!
```

Adjust as needed for production deployments.

---

## Features & Status

- [x] React + Tailwind UI shell & pages
- [x] FastAPI REST API w/ SQLModel models
- [x] Alembic migrations + seed data
- [x] Admin approval workflow
- [x] Pricing plan selection ($50/mo, $150/6mo)
- [x] Docker-based dev environment

Future enhancements can include JWT auth, file uploads, payment processor integration, and production-ready deployment scripts.

<!-- Trigger rebuild -->
