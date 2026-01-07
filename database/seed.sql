-- JetSchoolUSA Seed Data
-- Run this after migrations to populate initial data

-- Insert default pricing plans
INSERT INTO pricing_plans (name, slug, price_usd, billing_cycle_months, is_active, created_at) VALUES
  ('Monthly Listing', 'monthly', 50.00, 1, 1, unixepoch()),
  ('Six Month Listing', 'six-month', 150.00, 6, 1, unixepoch())
ON CONFLICT(slug) DO NOTHING;

-- Insert sample performance profiles (example data)
-- Note: Replace with actual aircraft data
INSERT INTO performance_profiles (manufacturer, model, specs, created_at) VALUES
  ('Cessna', 'Citation CJ3+', 
   '{"range_nm": 2040, "cruise_speed_knots": 417, "max_passengers": 9, "max_altitude_ft": 45000, "engine_type": "Twin Turbofan"}',
   unixepoch()),
  ('Gulfstream', 'G500',
   '{"range_nm": 5100, "cruise_speed_knots": 516, "max_passengers": 13, "max_altitude_ft": 51000, "engine_type": "Twin Turbofan"}',
   unixepoch()),
  ('Dassault', 'Falcon 8X',
   '{"range_nm": 6450, "cruise_speed_knots": 488, "max_passengers": 12, "max_altitude_ft": 51000, "engine_type": "Twin Turbofan"}',
   unixepoch())
ON CONFLICT DO NOTHING;

-- Note: Admin user will be created via Supabase Auth + sync endpoint
-- To create admin, sign up via Supabase, then run:
-- UPDATE users SET is_admin = 1 WHERE email = 'your-admin@email.com';

