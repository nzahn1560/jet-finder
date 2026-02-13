# Legacy Code - Archived

This folder contains the original Flask monolith and Cloudflare Workers code.

⚠️ **DO NOT USE THIS CODE** ⚠️

The application has been migrated to a modular FastAPI microservice architecture.

## What's Here

- `app.py` - Original 5441-line Flask monolith
- `marketplace.py` - Marketplace logic
- `stripe_integration.py` - Old Stripe integration
- `templates/` - Flask HTML templates
- `static/` - Old static files
- `worker-api/` - Old Cloudflare Workers code
- `workers/` - Duplicate worker code
- `instance/` - Old SQLite databases

## Active Codebase

See the main project for the current architecture:
- **Backend:** `backend/` (FastAPI modular services)
- **Frontend:** `frontend/` (React + Vite)
- **Database:** `database/` (Alembic migrations)
- **Docs:** `MICROSERVICE_ARCHITECTURE.md`

## Why Archived?

The Flask monolith had:
- 5441 lines in a single file
- Mixed concerns (auth, billing, listings, admin, etc.)
- Hard to test, maintain, and scale
- Duplicate functionality with FastAPI backend

The new architecture:
- Modular services (auth, listings, billing, match, media, admin)
- Clear separation of concerns
- Easy to test and extend
- Single Railway deployment
- Railway Postgres (no more SQLite)
