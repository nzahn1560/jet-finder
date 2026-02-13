"""
Database models for Jet Finder - Railway Production
Uses SQLAlchemy with PostgreSQL (via DATABASE_URL env var)
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import enum
import os
import secrets
import uuid

# Get DATABASE_URL from environment (Railway provides this)
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/jet_finder.db')

# Fix postgres:// to postgresql:// (SQLAlchemy requirement)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine with connection pooling and error handling
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=300,     # Recycle connections after 5 minutes
    connect_args={"connect_timeout": 10} if DATABASE_URL.startswith('postgresql') else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class ListingStatus(enum.Enum):
    DRAFT = 'draft'
    UNPAID = 'unpaid'
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ACTIVE = 'active'
    ARCHIVED = 'archived'

class MediaType(enum.Enum):
    PHOTO = 'photo'
    VIDEO = 'video'

class PaymentStatus(enum.Enum):
    CREATED = 'created'
    PAID = 'paid'
    FAILED = 'failed'
    REFUNDED = 'refunded'

# Models
class User(Base):
    __tablename__ = 'users'
    
    # Use UUID for better security and distributed systems
    # For PostgreSQL, use UUID type; for SQLite, use String
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship('Session', back_populates='user', cascade='all, delete-orphan')
    listings = relationship('Listing', back_populates='owner', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'is_admin': self.is_admin,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Session(Base):
    __tablename__ = 'sessions'
    
    # Use UUID for better security and distributed systems
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship('User', back_populates='sessions')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_for_user(user_id, days=30):
        """Create a new session for a user"""
        token = Session.generate_token()
        expires_at = datetime.utcnow() + timedelta(days=days)
        return Session(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
    
    def is_valid(self):
        """Check if session is still valid"""
        return datetime.utcnow() < self.expires_at

class Listing(Base):
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(ListingStatus), default=ListingStatus.DRAFT, nullable=False, index=True)
    
    # Basic info
    title = Column(String(255), nullable=False)
    aircraft_type = Column(String(100), nullable=False)
    manufacturer = Column(String(100))
    model = Column(String(100))
    year = Column(Integer)
    price = Column(Float)
    location = Column(String(200))
    description = Column(Text)
    
    # Condition data
    interior_year = Column(Integer)
    exterior_paint_year = Column(Integer)
    avionics_value_estimate = Column(Float)
    airframe_time = Column(Float)
    engine1_time = Column(Float)
    engine1_tbo = Column(Float)
    engine2_time = Column(Float)
    engine2_tbo = Column(Float)
    
    # Contact info
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    
    # Admin fields
    admin_notes = Column(Text)
    rejected_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship('User', back_populates='listings')
    media = relationship('ListingMedia', back_populates='listing', cascade='all, delete-orphan')
    payments = relationship('Payment', back_populates='listing', cascade='all, delete-orphan')
    
    def to_dict(self, include_owner=False):
        data = {
            'id': self.id,
            'owner_user_id': self.owner_user_id,
            'status': self.status.value if self.status else None,
            'title': self.title,
            'aircraft_type': self.aircraft_type,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'year': self.year,
            'price': self.price,
            'location': self.location,
            'description': self.description,
            'interior_year': self.interior_year,
            'exterior_paint_year': self.exterior_paint_year,
            'avionics_value_estimate': self.avionics_value_estimate,
            'airframe_time': self.airframe_time,
            'engine1_time': self.engine1_time,
            'engine1_tbo': self.engine1_tbo,
            'engine2_time': self.engine2_time,
            'engine2_tbo': self.engine2_tbo,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'admin_notes': self.admin_notes,
            'rejected_reason': self.rejected_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'media': [m.to_dict() for m in self.media] if self.media else []
        }
        
        if include_owner and self.owner:
            data['owner'] = self.owner.to_dict()
        
        return data

class ListingMedia(Base):
    __tablename__ = 'listing_media'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    media_type = Column(Enum(MediaType), nullable=False)
    url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    listing = relationship('Listing', back_populates='media')
    
    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'media_type': self.media_type.value if self.media_type else None,
            'url': self.url,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)
    stripe_checkout_session_id = Column(String(255), unique=True)
    stripe_payment_intent_id = Column(String(255))
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default='usd', nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.CREATED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    listing = relationship('Listing', back_populates='payments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'stripe_checkout_session_id': self.stripe_checkout_session_id,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'amount_cents': self.amount_cents,
            'currency': self.currency,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Database utilities
def get_db():
    """Get database session (use in context manager)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables
    Creates all tables defined in Base.metadata
    Safe to call multiple times (won't recreate existing tables)
    """
    import logging
    import sys
    
    # Ensure logging goes to stdout (Railway captures this)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    
    # Also print to stdout for Railway visibility
    print("=" * 60, file=sys.stdout)
    print("🔧 DATABASE INITIALIZATION STARTING", file=sys.stdout)
    print("=" * 60, file=sys.stdout)
    
    try:
        # Test database connection first
        print("🔧 Testing database connection...", file=sys.stdout)
        with engine.connect() as conn:
            # Use text() for SQLAlchemy 2.0+ compatibility
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful", file=sys.stdout)
        logger.info("✅ Database connection successful")
        
        # Create all tables
        print("🔧 Creating database tables...", file=sys.stdout)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified successfully!", file=sys.stdout)
        logger.info("✅ Database tables created/verified successfully!")
        
        # Verify critical tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = ['users', 'sessions']
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            error_msg = f"❌ CRITICAL: Required tables missing: {missing_tables}"
            print(error_msg, file=sys.stdout)
            logger.error(error_msg)
            raise Exception(f"Database initialization incomplete. Missing tables: {missing_tables}")
        
        success_msg = f"✅ Verified tables exist: {', '.join(required_tables)}"
        print(success_msg, file=sys.stdout)
        logger.info(success_msg)
        
        print("=" * 60, file=sys.stdout)
        print("✅ DATABASE INITIALIZATION COMPLETE", file=sys.stdout)
        print("=" * 60, file=sys.stdout)
        return True
        
    except Exception as e:
        error_msg = f"❌ Database initialization failed: {e}"
        print("=" * 60, file=sys.stdout)
        print(error_msg, file=sys.stdout)
        print(f"❌ Error type: {type(e).__name__}", file=sys.stdout)
        print(f"❌ DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "❌ DATABASE_URL: NOT SET", file=sys.stdout)
        import traceback
        print(f"❌ Traceback:\n{traceback.format_exc()}", file=sys.stdout)
        print("=" * 60, file=sys.stdout)
        
        logger.error(error_msg)
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "❌ DATABASE_URL: NOT SET")
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        
        # Re-raise to ensure app startup fails if DB is broken
        raise

def drop_all():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped!")

if __name__ == '__main__':
    # Initialize database when run directly
    init_db()
