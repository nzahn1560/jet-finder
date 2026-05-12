# Production data safety & backups

This file documents how to keep production user data (accounts + listings) safe.
Production = Railway PostgreSQL attached to the `jetschool` Flask service.

---

## 1. Safety contract (already enforced in code)

| Rule | Where it's enforced |
|---|---|
| User accounts + listings live ONLY in Railway PostgreSQL | `db.py` (SQLAlchemy models), `marketplace.py` (JSON writes refused in prod) |
| `init_db()` is additive only | `db.py::init_db` — `create_all` (CREATE TABLE IF NOT EXISTS) + `ADD COLUMN IF NOT EXISTS` |
| `Base.metadata.drop_all()` is never called in app startup | `db.py::DROP_ALL_TABLES_DANGEROUS()` — only manual entry point, blocked in prod |
| `DELETE FROM user_listings` is never called | No such code path exists; only single-row soft-delete via owner action |
| Bulk DELETEs (cache table) are blocked in prod | `db.py::clear_performance_profiles` → `assert_not_production()` |
| Force-logout (delete all sessions) is blocked in prod | `db.py::wipe_all_user_sessions_DANGEROUS` → `assert_not_production()` |
| JSON file writes for users/listings are blocked in prod | `marketplace.py::save_users`, `save_listings` (no-op in prod with WARN log) |

**Verify after each deploy** — hit:

```
GET https://jetschoolusa.com/api/data-safety
```

You should see:

```json
{
  "is_production": true,
  "destructive_ops_blocked": true,
  "database_type": "postgresql",
  "listings_storage": "postgres",
  "counts": { "users": N, "user_sessions": N, "user_listings": N }
}
```

If `counts.user_listings` ever drops between deploys, **stop deploying and restore from backup** (see §3).

---

## 2. Production environment variables

| Variable | Value | Purpose |
|---|---|---|
| `DATABASE_URL` | (set by Railway when Postgres plugin is attached) | The only source of production data |
| `FLASK_ENV` | `production` | Marks app as production (Secure cookies, safety guards on) |
| `RAILWAY_ENVIRONMENT` | `production` (Railway sets this automatically) | Backup signal that this is prod |
| `ALLOW_DESTRUCTIVE_DB_OPS` | **never set** in regular deploys | Only set temporarily during planned recovery — see §6 |

---

## 3. Manual backup with `pg_dump`

Railway gives you the Postgres connection details. Two ways to run `pg_dump`:

### Option A: Railway CLI (simplest)

```bash
# Install once
npm i -g @railway/cli
railway login
railway link   # pick your project + Postgres service

# Take a backup (writes to local file)
railway run pg_dump --no-owner --no-acl --format=custom \
  --file=jetschool-$(date -u +%Y%m%dT%H%M%SZ).dump
```

### Option B: Use the connection string directly

In Railway → Postgres service → **Variables** → copy `DATABASE_URL`.

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"

pg_dump "$DATABASE_URL" \
  --no-owner --no-acl --format=custom \
  --file=jetschool-$(date -u +%Y%m%dT%H%M%SZ).dump
```

Store the dump somewhere safe (S3, encrypted drive). Treat it as PII.

### Backup just the user data (smaller)

```bash
pg_dump "$DATABASE_URL" \
  --no-owner --no-acl --format=custom \
  --table=users --table=user_listings --table=user_sessions --table=user_subscriptions \
  --file=jetschool-userdata-$(date -u +%Y%m%dT%H%M%SZ).dump
```

---

## 4. Restore from a backup

> Only do this if you're absolutely sure you want to overwrite production data.

```bash
# Full restore (replaces everything)
pg_restore --clean --no-owner --no-acl --dbname="$DATABASE_URL" jetschool-YYYYMMDDTHHMMSSZ.dump

# Or restore just one table to a temp DB and copy rows in manually
pg_restore --no-owner --no-acl --dbname="$DATABASE_URL" \
  --table=user_listings jetschool-YYYYMMDDTHHMMSSZ.dump
```

---

## 5. Railway automatic backups

In Railway → your Postgres service → **Database** tab → **Backups**.

Railway snapshots the database on a schedule and you can restore from any
snapshot directly in the UI. These are the *primary* safety net; the manual
`pg_dump` flow above is for off-platform copies.

---

## 6. Recovery checklist (if you ever NEED a destructive op)

1. Take a fresh `pg_dump` (§3) and store it off Railway.
2. In Railway, **temporarily** set `ALLOW_DESTRUCTIVE_DB_OPS=yes_i_understand`.
3. Run the recovery script you need.
4. **Immediately remove `ALLOW_DESTRUCTIVE_DB_OPS`** from the env.
5. Hit `/api/data-safety` and confirm `destructive_ops_blocked: true` again.
6. Verify `counts.user_listings` matches what you expect.

If the variable is removed, every guarded function in `db.py` will refuse
to run a destructive op even if someone deploys bad code that calls it.

---

## 7. Schema-change checklist (before deploy)

Every schema change must be additive. Before committing:

- [ ] No `DROP TABLE` / `DROP COLUMN` in `db.py` or migration code.
- [ ] No `Base.metadata.drop_all()` outside `DROP_ALL_TABLES_DANGEROUS`.
- [ ] No `s.query(UserListing).delete()` / `query(User).delete()` (bulk).
- [ ] New columns use `ADD COLUMN IF NOT EXISTS` and have a default.
- [ ] Tested locally: existing rows are still readable after applying the change.
- [ ] If renaming a column: add the new column, copy data, leave the old column
      in place until a follow-up deploy.

Then deploy and immediately hit `/api/data-safety` to confirm row counts.
