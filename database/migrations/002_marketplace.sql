-- Migration 002: Marketplace listings + payments + audit events

-- Performance profile additions
ALTER TABLE performance_profiles ADD COLUMN category TEXT;
ALTER TABLE performance_profiles ADD COLUMN aircraft_class TEXT;

-- Listing additions
ALTER TABLE listings ADD COLUMN aircraft_model TEXT;
ALTER TABLE listings ADD COLUMN serial_number TEXT;
ALTER TABLE listings ADD COLUMN hours INTEGER;
ALTER TABLE listings ADD COLUMN year INTEGER;
ALTER TABLE listings ADD COLUMN total_time INTEGER;
ALTER TABLE listings ADD COLUMN engine1_time INTEGER;
ALTER TABLE listings ADD COLUMN engine1_tbo INTEGER;
ALTER TABLE listings ADD COLUMN interior_year INTEGER;
ALTER TABLE listings ADD COLUMN paint_year INTEGER;
ALTER TABLE listings ADD COLUMN avionics_value_estimate INTEGER;
ALTER TABLE listings ADD COLUMN needs_review BOOLEAN DEFAULT FALSE;
ALTER TABLE listings ADD COLUMN rejected_reason TEXT;

-- Listing media additions
ALTER TABLE listing_media ADD COLUMN url TEXT;

-- Payments
CREATE TABLE IF NOT EXISTS payments (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  listing_id INTEGER NOT NULL REFERENCES listings(id),
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  stripe_checkout_session_id TEXT,
  plan TEXT NOT NULL,
  status TEXT NOT NULL,
  current_period_end TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit events
CREATE TABLE IF NOT EXISTS audit_events (
  id SERIAL PRIMARY KEY,
  type TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  user_id INTEGER REFERENCES users(id),
  listing_id INTEGER REFERENCES listings(id),
  metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
