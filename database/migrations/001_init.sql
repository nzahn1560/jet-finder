-- JetSchoolUSA Database Schema
-- Migration: 001_init.sql
-- Description: Initial schema for users, listings, performance profiles, media, and tool usage

-- Users table (synced with Supabase Auth)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  supabase_user_id TEXT UNIQUE NOT NULL,
  is_admin INTEGER DEFAULT 0 CHECK(is_admin IN (0, 1)),
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_supabase_id ON users(supabase_user_id);

-- Performance profiles (aircraft specifications)
CREATE TABLE IF NOT EXISTS performance_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manufacturer TEXT NOT NULL,
  model TEXT NOT NULL,
  specs TEXT NOT NULL, -- JSON string containing performance specs
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_performance_profiles_manufacturer ON performance_profiles(manufacturer);
CREATE INDEX IF NOT EXISTS idx_performance_profiles_model ON performance_profiles(model);

-- Listings table
CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  price REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'denied')),
  pricing_plan TEXT,
  performance_profile_id INTEGER,
  created_at INTEGER DEFAULT (unixepoch()),
  updated_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (performance_profile_id) REFERENCES performance_profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_owner ON listings(owner_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created ON listings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_listings_performance_profile ON listings(performance_profile_id);

-- Listing images stored in R2
CREATE TABLE IF NOT EXISTS listing_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  r2_key TEXT NOT NULL,
  order INTEGER DEFAULT 0,
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listing_images_listing ON listing_images(listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_images_order ON listing_images(listing_id, order);

-- Tool usage tracking
CREATE TABLE IF NOT EXISTS tool_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  meta TEXT, -- JSON string for additional metadata
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_usage_user ON tool_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_created ON tool_usage(created_at DESC);

-- Pricing plans
CREATE TABLE IF NOT EXISTS pricing_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  price_usd REAL NOT NULL,
  billing_cycle_months INTEGER NOT NULL,
  is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
  created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_pricing_plans_slug ON pricing_plans(slug);

-- Admin approvals/rejections log
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id INTEGER NOT NULL,
  admin_id TEXT NOT NULL,
  action TEXT NOT NULL CHECK(action IN ('approved', 'denied')),
  reason TEXT,
  created_at INTEGER DEFAULT (unixepoch()),
  FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
  FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_listing ON approvals(listing_id);
CREATE INDEX IF NOT EXISTS idx_approvals_admin ON approvals(admin_id);
CREATE INDEX IF NOT EXISTS idx_approvals_created ON approvals(created_at DESC);

