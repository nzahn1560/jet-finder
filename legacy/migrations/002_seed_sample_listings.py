#!/usr/bin/env python3
"""
Seed Sample Listings from CSV Data
Takes the first 10 aircraft from CSV and creates sample listings in the database
"""

import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def seed_sample_listings():
    """Create 10 sample approved listings from CSV data"""
    
    # Load CSV
    csv_path = Path(__file__).parent.parent.parent / 'Aircraft Data - Aircraft Data (1).csv'
    if not csv_path.exists():
        print(f"❌ CSV not found: {csv_path}")
        return False
    
    df = pd.read_csv(csv_path)
    print(f"📄 Loaded {len(df)} aircraft from CSV")
    
    # Take first 10 aircraft
    sample_aircraft = df.head(10)
    
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # PostgreSQL
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Get admin user ID
        cursor.execute("SELECT id FROM users WHERE is_admin = TRUE LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("❌ No admin user found. Run migrations first.")
            return False
        admin_id = result[0]
        
        for idx, aircraft in sample_aircraft.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO listings (
                        user_id, performance_profile_id, aircraft_name, manufacturer, model, category,
                        year, range_nm, speed_kts, passengers, cabin_volume_cuft, baggage_volume_cuft,
                        total_time_hours, engine1_time_hours, engine1_tbo_hours,
                        interior_refurb_year, paint_year, exterior_condition, interior_condition,
                        avionics_value_estimate, asking_price, location, title, description,
                        status, approved_at, approved_by
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s
                    )
                """, (
                    admin_id,
                    int(aircraft.get('id', idx)),
                    aircraft.get('name', 'Unknown Aircraft'),
                    aircraft.get('manufacturer', 'Unknown'),
                    aircraft.get('model', ''),
                    aircraft.get('category', 'Unknown'),
                    int(aircraft.get('year', 2010)) if pd.notna(aircraft.get('year')) else 2010,
                    int(aircraft.get('range', 0)),
                    int(aircraft.get('speed', 0)),
                    int(aircraft.get('passengers', 0)),
                    float(aircraft.get('cabin_volume', 0)),
                    float(aircraft.get('baggage_volume', 0)),
                    5000,  # Sample total time
                    2000,  # Sample engine1 time
                    3500,  # Sample engine1 TBO
                    2020,  # Interior refurb year
                    2019,  # Paint year
                    'Excellent',  # Exterior condition
                    'Good',  # Interior condition
                    250000,  # Avionics value estimate
                    float(aircraft.get('price', 5000000)),
                    'Fort Lauderdale, FL',
                    f"{aircraft.get('manufacturer', 'Aircraft')} {aircraft.get('name', '')} - Excellent Condition",
                    f"Beautiful {aircraft.get('name', 'aircraft')} with low hours and recent upgrades. Ready for immediate delivery.",
                    'approved',
                    admin_id
                ))
                print(f"✅ Created listing: {aircraft.get('name')}")
            except Exception as e:
                print(f"❌ Error creating listing {aircraft.get('name')}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    else:
        # SQLite
        import sqlite3
        db_path = Path(__file__).parent.parent / 'instance' / 'jet_finder.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get admin user ID
        cursor.execute("SELECT id FROM users WHERE is_admin = 1 LIMIT 1")
        result = cursor.fetchone()
        if not result:
            print("❌ No admin user found. Run migrations first.")
            return False
        admin_id = result[0]
        
        for idx, aircraft in sample_aircraft.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO listings (
                        user_id, performance_profile_id, aircraft_name, manufacturer, model, category,
                        year, range_nm, speed_kts, passengers, cabin_volume_cuft, baggage_volume_cuft,
                        total_time_hours, engine1_time_hours, engine1_tbo_hours,
                        interior_refurb_year, paint_year, exterior_condition, interior_condition,
                        avionics_value_estimate, asking_price, location, title, description,
                        status, approved_at, approved_by
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?
                    )
                """, (
                    admin_id,
                    int(aircraft.get('id', idx)),
                    aircraft.get('name', 'Unknown Aircraft'),
                    aircraft.get('manufacturer', 'Unknown'),
                    aircraft.get('model', ''),
                    aircraft.get('category', 'Unknown'),
                    int(aircraft.get('year', 2010)) if pd.notna(aircraft.get('year')) else 2010,
                    int(aircraft.get('range', 0)),
                    int(aircraft.get('speed', 0)),
                    int(aircraft.get('passengers', 0)),
                    float(aircraft.get('cabin_volume', 0)),
                    float(aircraft.get('baggage_volume', 0)),
                    5000,
                    2000,
                    3500,
                    2020,
                    2019,
                    'Excellent',
                    'Good',
                    250000,
                    float(aircraft.get('price', 5000000)),
                    'Fort Lauderdale, FL',
                    f"{aircraft.get('manufacturer', 'Aircraft')} {aircraft.get('name', '')} - Excellent Condition",
                    f"Beautiful {aircraft.get('name', 'aircraft')} with low hours and recent upgrades. Ready for immediate delivery.",
                    'approved',
                    admin_id
                ))
                print(f"✅ Created listing: {aircraft.get('name')}")
            except Exception as e:
                print(f"❌ Error creating listing {aircraft.get('name')}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
    
    print(f"\n✅ Seeded 10 sample listings")
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("JetSchool USA - Seed Sample Listings")
    print("=" * 60)
    
    success = seed_sample_listings()
    sys.exit(0 if success else 1)
