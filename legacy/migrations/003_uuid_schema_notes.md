# UUID Schema Migration Notes

## Important Schema Differences

This migration (`003_uuid_schema.sql`) creates a **simplified schema** using PostgreSQL UUID types. However, the current codebase uses:

### Current Models vs. Migration SQL

1. **Listing ID Type**
   - **Current**: `Integer` (autoincrement)
   - **Migration**: `UUID` (gen_random_uuid())
   - **Impact**: Models need to be updated to use UUID for listing IDs

2. **User ID Field Name**
   - **Current**: `owner_user_id` in listings table
   - **Migration**: `user_id` in listings table
   - **Impact**: All code referencing `owner_user_id` needs to be updated to `user_id`

3. **UUID Storage**
   - **Current**: `String(36)` (UUID stored as string)
   - **Migration**: PostgreSQL `UUID` type
   - **Impact**: Models should use SQLAlchemy's `UUID` type for PostgreSQL

4. **Listing Fields**
   - **Current**: Many fields (title, aircraft_type, manufacturer, model, year, price, location, description, interior_year, exterior_paint_year, avionics_value_estimate, airframe_time, engine1_time, engine1_tbo, engine2_time, engine2_tbo, contact_email, contact_phone, admin_notes, rejected_reason, created_at, updated_at)
   - **Migration**: Only basic fields (id, user_id, aircraft_make, aircraft_model, title, status, created_at)
   - **Impact**: Migration creates minimal schema; additional fields need to be added via ALTER TABLE

## Recommended Approach

### Option 1: Expand Migration SQL (Recommended)
Add all missing fields to the migration SQL to match current models:

```sql
CREATE TABLE IF NOT EXISTS listings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Basic info
  title TEXT,
  aircraft_type TEXT,
  manufacturer TEXT,
  model TEXT,
  year INTEGER,
  price DECIMAL(12, 2),
  location TEXT,
  description TEXT,
  
  -- Condition data
  interior_year INTEGER,
  exterior_paint_year INTEGER,
  avionics_value_estimate DECIMAL(12, 2),
  airframe_time DECIMAL(10, 2),
  engine1_time DECIMAL(10, 2),
  engine1_tbo DECIMAL(10, 2),
  engine2_time DECIMAL(10, 2),
  engine2_tbo DECIMAL(10, 2),
  
  -- Contact info
  contact_email TEXT,
  contact_phone TEXT,
  
  -- Admin fields
  admin_notes TEXT,
  rejected_reason TEXT,
  
  -- Status
  status TEXT NOT NULL DEFAULT 'draft',
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Option 2: Update Models to Match Migration
Update models to use:
- PostgreSQL UUID type for IDs
- `user_id` instead of `owner_user_id`
- Match the simplified schema

### Option 3: Hybrid Approach
1. Run this migration to create basic tables
2. Add ALTER TABLE statements to add missing fields
3. Update models to use UUID types

## Running the Migration

For PostgreSQL (Railway):
```bash
psql $DATABASE_URL -f legacy/migrations/003_uuid_schema.sql
```

Or use the migration runner:
```bash
python legacy/migrations/run_migrations.py
```

## Code Updates Needed

If using this migration, update:

1. **`legacy/models.py`**:
   - Change `id = Column(Integer, ...)` to `id = Column(UUID, ...)` for Listing
   - Change `owner_user_id` to `user_id` in Listing model
   - Use SQLAlchemy's UUID type for PostgreSQL

2. **`legacy/listings_api.py`**:
   - Replace all `owner_user_id` references with `user_id`

3. **All other files**:
   - Search and replace `owner_user_id` with `user_id`

## Migration Safety

⚠️ **WARNING**: This migration will create new tables. If tables already exist with different schemas, you may need to:
1. Drop existing tables (⚠️ **DATA LOSS**)
2. Or use ALTER TABLE to migrate existing data
3. Or create a data migration script
