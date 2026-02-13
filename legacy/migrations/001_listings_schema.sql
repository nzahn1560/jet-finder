-- JetSchool USA - Listings Database Schema
-- Includes all fields needed for Match Tool scoring

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(255),
    phone VARCHAR(20),
    user_type VARCHAR(50) DEFAULT 'buyer',
    is_admin BOOLEAN DEFAULT FALSE,
    is_verified_seller BOOLEAN DEFAULT FALSE,
    verification_status VARCHAR(50) DEFAULT 'unverified',
    seller_score DECIMAL(3,2) DEFAULT 0.0,
    total_listings INTEGER DEFAULT 0,
    successful_transactions INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aircraft Listings table with Match Tool fields
CREATE TABLE IF NOT EXISTS listings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Performance Profile (reference to CSV data)
    performance_profile_id INTEGER NOT NULL,
    aircraft_name VARCHAR(255) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    category VARCHAR(50),
    
    -- Basic Specs (from performance profile)
    year INTEGER,
    range_nm INTEGER,
    speed_kts INTEGER,
    max_altitude_ft INTEGER,
    passengers INTEGER,
    cabin_volume_cuft DECIMAL(10,2),
    baggage_volume_cuft DECIMAL(10,2),
    
    -- Listing-Specific Condition Fields (for Match Tool)
    total_time_hours INTEGER,
    engine1_time_hours INTEGER,
    engine1_tbo_hours INTEGER,
    engine2_time_hours INTEGER,
    engine2_tbo_hours INTEGER,
    
    -- Cosmetic Fields (for Match Tool)
    interior_refurb_year INTEGER,
    paint_year INTEGER,
    exterior_condition VARCHAR(50),  -- Excellent, Good, Fair, Needs Work
    interior_condition VARCHAR(50),   -- Excellent, Good, Fair, Needs Work
    
    -- Avionics Fields (for Match Tool)
    avionics_package TEXT,
    avionics_value_estimate DECIMAL(12,2),
    has_wifi BOOLEAN DEFAULT FALSE,
    
    -- Pricing
    asking_price DECIMAL(15,2) NOT NULL,
    price_negotiable BOOLEAN DEFAULT TRUE,
    
    -- Location & Contact
    location VARCHAR(255),
    airport_code VARCHAR(10),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    
    -- Listing Details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    images JSON,  -- Array of image URLs
    documents JSON,  -- Array of document URLs (logs, maintenance records)
    
    -- Status & Approval
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected, sold
    admin_notes TEXT,
    approved_at TIMESTAMP,
    approved_by INTEGER REFERENCES users(id),
    
    -- Match Score Metadata (cached from last calculation)
    last_match_score DECIMAL(5,2),
    match_score_categories JSON,
    match_score_updated_at TIMESTAMP,
    
    -- Metrics
    views INTEGER DEFAULT 0,
    inquiries INTEGER DEFAULT 0,
    favorites INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_status (status),
    INDEX idx_approved (status, approved_at),
    INDEX idx_manufacturer (manufacturer),
    INDEX idx_category (category),
    INDEX idx_price (asking_price),
    INDEX idx_year (year),
    INDEX idx_match_score (last_match_score)
);

-- Subscriptions table (for Stripe integration)
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id VARCHAR(255),
    plan_type VARCHAR(50) NOT NULL,  -- charter_search, empty_leg, parts
    status VARCHAR(50) DEFAULT 'active',  -- active, cancelled, past_due
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Favorites table
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, listing_id)
);

-- Inquiries table
CREATE TABLE IF NOT EXISTS inquiries (
    id SERIAL PRIMARY KEY,
    listing_id INTEGER REFERENCES listings(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'new',  -- new, contacted, qualified, closed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search history (for analytics)
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    filters JSON,
    match_weights JSON,
    results_count INTEGER,
    top_result_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_listings_user ON listings(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_listing ON favorites(listing_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_listing ON inquiries(listing_id);
CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history(user_id);

-- Insert default admin user (password: Admin123!)
INSERT INTO users (email, password_hash, first_name, last_name, user_type, is_admin)
VALUES (
    'admin@jetschoolusa.com',
    'pbkdf2:sha256:260000$salt$hash',  -- Replace with actual hash
    'Admin',
    'User',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
