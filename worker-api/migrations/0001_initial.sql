-- Users table (Supabase handles auth, but we store user metadata)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, -- Supabase user ID (UUID)
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  is_admin INTEGER DEFAULT 0,
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch())
);

-- Performance profiles (aircraft specifications)
CREATE TABLE IF NOT EXISTS performance_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  manufacturer TEXT NOT NULL,
  engine_type TEXT NOT NULL,
  range_nm INTEGER NOT NULL,
  cruise_speed_knots INTEGER NOT NULL,
  max_passengers INTEGER NOT NULL,
  max_altitude_ft INTEGER NOT NULL,
  cabin_volume_cuft REAL,
  baggage_volume_cuft REAL,
  runway_requirement_ft INTEGER,
  hourly_cost_usd REAL,
  annual_maintenance_usd REAL,
  purchase_price_usd REAL,
  image_url TEXT,
  created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_performance_profiles_manufacturer ON performance_profiles(manufacturer);

-- Pricing plans for listings
CREATE TABLE IF NOT EXISTS pricing_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  price_usd INTEGER NOT NULL,
  billing_cycle_months INTEGER NOT NULL,
  is_active INTEGER DEFAULT 1,
  created_at INTEGER DEFAULT (unixepoch())
);

-- Listings table
CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  price_usd INTEGER NOT NULL,
  location TEXT NOT NULL,
  engine_type TEXT NOT NULL,
  contact_email TEXT NOT NULL,
  serial_number TEXT,
  hours INTEGER,
  year INTEGER,
  status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'rejected')),
  payment_plan TEXT DEFAULT 'monthly' CHECK(payment_plan IN ('monthly', 'six_month')),
  owner_id TEXT,
  performance_profile_id INTEGER,
  pricing_plan_id INTEGER,
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch()),
  approved_at INTEGER,
  rejected_reason TEXT,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (performance_profile_id) REFERENCES performance_profiles(id) ON DELETE SET NULL,
  FOREIGN KEY (pricing_plan_id) REFERENCES pricing_plans(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_owner ON listings(owner_id);
CREATE INDEX IF NOT EXISTS idx_listings_profile ON listings(performance_profile_id);
CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC);

-- Listing images stored in R2, URLs in DB
CREATE TABLE IF NOT EXISTS listing_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  image_url TEXT NOT NULL,
  r2_key TEXT NOT NULL, -- R2 object key
  display_order INTEGER DEFAULT 0,
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listing_images_listing ON listing_images(listing_id);

-- Admin approvals/rejections log
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  admin_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK(action IN ('approved', 'rejected')),
  reason TEXT,
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
  FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_listing ON approvals(listing_id);

-- Messages/inquiries about listings
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  sender_id TEXT NOT NULL,
  recipient_id TEXT NOT NULL,
  subject TEXT,
  body TEXT NOT NULL,
  read INTEGER DEFAULT 0,
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
  FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_listing ON messages(listing_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);

-- Usage tracking for internal tool
CREATE TABLE IF NOT EXISTS usage_tracking (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  action TEXT NOT NULL,
  metadata TEXT, -- JSON string for additional data
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_tool ON usage_tracking(tool_name);
CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_tracking(created_at DESC);

-- User dashboard preferences
CREATE TABLE IF NOT EXISTS user_preferences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT UNIQUE NOT NULL,
  preferences TEXT, -- JSON string for user settings
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_prefs_user ON user_preferences(user_id);

