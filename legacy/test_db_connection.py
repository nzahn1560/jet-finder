#!/usr/bin/env python3
"""
Test database connection and table creation
Run this on Railway to diagnose database issues
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("Database Connection Test")
print("=" * 60)

# Check DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ DATABASE_URL is not set!")
    print("   Add PostgreSQL service in Railway to auto-set this")
    sys.exit(1)

print(f"✅ DATABASE_URL is set: {database_url[:50]}...")

# Test import
try:
    from models import engine, Base, User, Session, init_db
    print("✅ Models imported successfully")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test connection
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test table creation
try:
    print("\n🔧 Creating tables...")
    init_db()
    print("✅ Tables created/verified successfully")
except Exception as e:
    print(f"❌ Table creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify tables exist
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"\n📊 Existing tables: {existing_tables}")
    
    required_tables = ['users', 'sessions']
    for table in required_tables:
        if table in existing_tables:
            print(f"✅ Table '{table}' exists")
            
            # Check columns
            columns = [col['name'] for col in inspector.get_columns(table)]
            print(f"   Columns: {', '.join(columns)}")
        else:
            print(f"❌ Table '{table}' is MISSING")
except Exception as e:
    print(f"❌ Table verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All database checks passed!")
print("=" * 60)
