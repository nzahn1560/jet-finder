"""
Create admin user for Jet Finder
Run this once after deploying to Railway
"""
from models import SessionLocal, User
from werkzeug.security import generate_password_hash
import sys

def create_admin(email, password):
    """Create an admin user"""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            if not existing_user.is_admin:
                print("   Making existing user an admin...")
                existing_user.is_admin = True
                db.commit()
                print("✅ User is now an admin!")
            return
        
        # Create new admin user
        admin = User(
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
            first_name='Admin'
        )
        db.add(admin)
        db.commit()
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   You can now log in at /login")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python create_admin.py <email> <password>")
        print("Example: python create_admin.py admin@jetfinder.com SecurePass123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        sys.exit(1)
    
    create_admin(email, password)
