#!/usr/bin/env python3
"""
Database Migration Runner for JetSchool USA
Supports both SQLite (local) and PostgreSQL (Railway production)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_sqlite_migrations():
    """Run migrations on SQLite database (local development)"""
    import sqlite3
    
    db_path = Path(__file__).parent.parent / 'instance' / 'jet_finder.db'
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Running SQLite migrations...")
    
    # Read and adapt PostgreSQL schema for SQLite
    schema_file = Path(__file__).parent / '001_listings_schema.sql'
    with open(schema_file, 'r') as f:
        sql = f.read()
    
    # SQLite adaptations
    sql = sql.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
    sql = sql.replace('DECIMAL(', 'REAL --(')
    sql = sql.replace('TIMESTAMP', 'TEXT')
    sql = sql.replace('BOOLEAN', 'INTEGER')
    sql = sql.replace('JSON', 'TEXT')
    sql = sql.replace('DEFAULT CURRENT_TIMESTAMP', "DEFAULT (datetime('now'))")
    sql = sql.replace('ON CONFLICT (email) DO NOTHING', '')
    
    # Remove PostgreSQL-specific index syntax
    sql = sql.replace(', INDEX', '; CREATE INDEX')
    sql = sql.replace('INDEX idx_', 'idx_')
    
    # Execute each statement separately
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    for i, statement in enumerate(statements):
        if not statement or statement.startswith('--'):
            continue
        try:
            cursor.execute(statement)
            print(f"✅ Executed statement {i+1}/{len(statements)}")
        except sqlite3.Error as e:
            if 'already exists' in str(e):
                print(f"⏭️  Skipped (already exists): {statement[:50]}...")
            else:
                print(f"❌ Error: {e}")
                print(f"Statement: {statement[:100]}...")
    
    conn.commit()
    conn.close()
    print(f"✅ SQLite migrations complete: {db_path}")
    return True

def run_postgres_migrations():
    """Run migrations on PostgreSQL database (Railway production)"""
    import psycopg2
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("🔧 Running PostgreSQL migrations...")
    
    schema_file = Path(__file__).parent / '001_listings_schema.sql'
    with open(schema_file, 'r') as f:
        sql = f.read()
    
    try:
        cursor.execute(sql)
        conn.commit()
        print("✅ PostgreSQL migrations complete")
        return True
    except psycopg2.Error as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def seed_admin_user():
    """Create admin user from environment variables"""
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@jetschoolusa.com')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin123!')
    
    # Hash password
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(admin_password)
    
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # PostgreSQL
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, user_type, is_admin)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                is_admin = TRUE
        """, (admin_email, password_hash, 'Admin', 'User', 'admin', True))
        
        conn.commit()
        cursor.close()
        conn.close()
    else:
        # SQLite
        import sqlite3
        db_path = Path(__file__).parent.parent / 'instance' / 'jet_finder.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users (email, password_hash, first_name, last_name, user_type, is_admin)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (admin_email, password_hash, 'Admin', 'User', 'admin', 1))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    print(f"✅ Admin user created: {admin_email}")
    print(f"   Password: {admin_password}")
    print(f"   ⚠️  Change password after first login!")

def main():
    print("=" * 60)
    print("JetSchool USA - Database Migration Runner")
    print("=" * 60)
    
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print(f"🐘 Detected PostgreSQL: {database_url[:30]}...")
        success = run_postgres_migrations()
    else:
        print("📁 Using SQLite (local development)")
        success = run_sqlite_migrations()
    
    if success:
        print("\n🌱 Seeding admin user...")
        seed_admin_user()
        print("\n✅ All migrations complete!")
        return 0
    else:
        print("\n❌ Migrations failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
