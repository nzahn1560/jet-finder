# Database Migrations

## Migration Files

1. **`001_listings_schema.sql`** - Original listings schema (comprehensive)
2. **`002_seed_sample_listings.py`** - Seed script for sample data
3. **`003_uuid_schema.sql`** - Simplified UUID schema (PostgreSQL only)

## Running Migrations

### Automatic (Recommended)
```bash
python legacy/migrations/run_migrations.py
```

This script:
- Detects PostgreSQL (via `DATABASE_URL`) or SQLite
- Runs appropriate migrations
- Seeds admin user

### Manual PostgreSQL
```bash
# Set DATABASE_URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Run migration
psql $DATABASE_URL -f legacy/migrations/003_uuid_schema.sql
```

### Manual SQLite
```bash
sqlite3 instance/jet_finder.db < legacy/migrations/001_listings_schema.sql
```

## Migration 003: UUID Schema

This migration creates a simplified schema using PostgreSQL UUID types:

- **Users**: UUID primary key, email, password_hash, is_admin
- **Sessions**: UUID primary key, user_id (UUID FK), token, expires_at
- **Listings**: UUID primary key, user_id (UUID FK), basic fields

⚠️ **Note**: This is a simplified schema. The current models have more fields. See `003_uuid_schema_notes.md` for details.

## Schema Differences

The UUID schema (`003_uuid_schema.sql`) differs from current models:

1. Uses `user_id` instead of `owner_user_id` in listings
2. Uses UUID for listing IDs (not Integer)
3. Has fewer fields than current Listing model

If you need all fields, either:
- Expand `003_uuid_schema.sql` to include all fields
- Or use `001_listings_schema.sql` and manually convert to UUIDs

## Environment Variables

For admin user seeding:
- `ADMIN_EMAIL` - Admin email (default: admin@jetschoolusa.com)
- `ADMIN_PASSWORD` - Admin password (default: Admin123!)

## Railway Deployment

Railway automatically provides `DATABASE_URL`. The migration runner will detect it and run PostgreSQL migrations.
