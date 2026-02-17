"""
Database layer for Jet Finder. Uses PostgreSQL when DATABASE_URL is set (Railway),
otherwise SQLite for localhost. Replaces direct sqlite3 for users/listings.
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

# DATABASE_URL from env (Railway Postgres) or SQLite for local
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/jet_finder.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

_connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    _connect_args = {'check_same_thread': False}

_engine_kw = dict(
    connect_args=_connect_args,
    pool_pre_ping=True,
)
if DATABASE_URL.startswith('postgresql'):
    _engine_kw['pool_recycle'] = 300
engine = create_engine(DATABASE_URL, **_engine_kw)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    phone = Column(String(20))
    user_type = Column(String(50), default='free_user')
    is_verified_seller = Column(Boolean, default=False)
    verification_status = Column(String(50), default='unverified')
    verification_documents = Column(Text)
    seller_score = Column(Float, default=0.0)
    total_listings = Column(Integer, default=0)
    successful_transactions = Column(Integer, default=0)
    user_reports = Column(Integer, default=0)
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserListing(Base):
    __tablename__ = 'user_listings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    profile_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    hours = Column(Integer, default=0)
    location = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    description = Column(Text)
    images = Column(Text)
    documents = Column(Text)
    status = Column(String(50), default='pending')
    payment_status = Column(String(50), default='pending')
    payment_session_id = Column(String(255))
    stripe_payment_intent_id = Column(String(255))
    approved_by = Column(Integer, ForeignKey('users.id'))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    engine_type = Column(String(100))
    manufacturer = Column(String(200))
    pricing_plan = Column(String(50), default='monthly')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserSubscription(Base):
    __tablename__ = 'user_subscriptions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subscription_type = Column(String(100), nullable=False)
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    subscription_status = Column(String(50), default='inactive')
    activated_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PerUsePurchase(Base):
    __tablename__ = 'per_use_purchases'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    service_type = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    stripe_payment_intent_id = Column(String(255))
    status = Column(String(50), default='pending')
    used_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def init_db():
    """Create tables if they do not exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    # SQLite: add columns that may be missing in existing DBs (e.g. created by older app)
    if DATABASE_URL.startswith('sqlite'):
        with engine.connect() as conn:
            for col_def in [
                'payment_status TEXT DEFAULT \'pending\'',
                'payment_session_id TEXT',
                'stripe_payment_intent_id TEXT',
                'approved_by INTEGER',
                'approved_at TIMESTAMP',
                'rejection_reason TEXT',
                'documents TEXT',
                'engine_type TEXT',
                'manufacturer TEXT',
                'pricing_plan TEXT DEFAULT \'monthly\'',
            ]:
                try:
                    conn.execute(text(f'ALTER TABLE user_listings ADD COLUMN {col_def}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    pass  # column already exists


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_ok():
    """Return True if database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return True
    except Exception:
        return False


# --- User helpers (replace sqlite3 in app.py) ---
def get_user_by_id(user_id):
    with get_session() as s:
        user = s.query(User).filter(User.id == user_id).first()
        return user.to_dict() if user else None


def get_user_by_email(email):
    with get_session() as s:
        user = s.query(User).filter(User.email == email).first()
        return user.to_dict() if user else None


def create_user(email, password_hash, first_name=None, last_name=None, company=None, phone=None):
    with get_session() as s:
        u = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            company=company,
            phone=phone,
        )
        s.add(u)
        s.flush()
        return u.id


# --- User listings helpers ---
def get_active_user_listings():
    """Return all active user_listings as list of dicts (for /api/user-listings)."""
    with get_session() as s:
        rows = s.query(UserListing).filter(UserListing.status == 'active').order_by(UserListing.created_at.desc()).all()
        return [row.to_dict() for row in rows]


def create_user_listing(profile_id, title, year, price, hours, location, email, description,
                        images_str, documents_str, engine_type, manufacturer, pricing_plan, user_id=None):
    with get_session() as s:
        row = UserListing(
            user_id=user_id,
            profile_id=profile_id,
            title=title,
            year=year,
            price=price,
            hours=hours,
            location=location,
            email=email,
            description=description or '',
            images=images_str or '',
            documents=documents_str or '',
            engine_type=engine_type,
            manufacturer=manufacturer,
            pricing_plan=pricing_plan or 'monthly',
            status='pending',
            payment_status='pending',
        )
        s.add(row)
        s.flush()
        return row.id


def get_user_listing_by_id(listing_id, active_only=True):
    with get_session() as s:
        q = s.query(UserListing).filter(UserListing.id == listing_id)
        if active_only:
            q = q.filter(UserListing.status == 'active')
        row = q.first()
        return row.to_dict() if row else None


def delete_user_listing_soft(listing_id):
    """Set status to 'deleted'. Returns True if a row was updated."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update({'status': 'deleted'}, synchronize_session=False)
        return n > 0


def search_user_listings(search_query=None, category=None, min_price=None, max_price=None, min_year=None, max_year=None, location=None):
    """Return list of active listing dicts matching filters."""
    with get_session() as s:
        q = s.query(UserListing).filter(UserListing.status == 'active')
        # Simple filters (expand as needed)
        if min_price is not None:
            q = q.filter(UserListing.price >= min_price)
        if max_price is not None:
            q = q.filter(UserListing.price <= max_price)
        if min_year is not None:
            q = q.filter(UserListing.year >= min_year)
        if max_year is not None:
            q = q.filter(UserListing.year <= max_year)
        rows = q.order_by(UserListing.created_at.desc()).all()
        return [row.to_dict() for row in rows]


def get_user_listing_status(listing_id):
    with get_session() as s:
        row = s.query(UserListing).filter(UserListing.id == listing_id).first()
        return (row.status, row.payment_status) if row else (None, None)


def set_user_listing_payment_pending(listing_id):
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update({'payment_status': 'pending'}, synchronize_session=False)
        return n > 0


def set_user_listing_status(listing_id, status):
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update({'status': status}, synchronize_session=False)
        return n > 0


def get_pending_user_listings():
    """Return all pending user_listings as list of dicts (for admin)."""
    with get_session() as s:
        rows = s.query(UserListing).filter(UserListing.status == 'pending').order_by(UserListing.created_at.desc()).all()
        return [row.to_dict() for row in rows]


def approve_user_listing(listing_id, approved_by_user_id):
    """Set listing to active and set approved_by/approved_at. Returns True if updated."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id, UserListing.status == 'pending').update({
            'status': 'active',
            'approved_by': approved_by_user_id,
            'approved_at': datetime.utcnow(),
        }, synchronize_session=False)
        return n > 0


def reject_user_listing(listing_id, rejection_reason):
    """Set listing to rejected. Returns True if updated."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id, UserListing.status == 'pending').update({
            'status': 'rejected',
            'rejection_reason': rejection_reason,
        }, synchronize_session=False)
        return n > 0


# --- UserSubscription / PerUsePurchase (used by app.py auth) ---
def get_user_subscription(user_id, subscription_type=None):
    with get_session() as s:
        q = s.query(UserSubscription).filter(UserSubscription.user_id == user_id)
        if subscription_type:
            q = q.filter(UserSubscription.subscription_type == subscription_type)
        else:
            q = q.order_by(UserSubscription.created_at.desc()).limit(1)
        row = q.first()
        return row.to_dict() if row else None


def get_user_subscriptions(user_id):
    with get_session() as s:
        rows = s.query(UserSubscription).filter(UserSubscription.user_id == user_id).all()
        return [row.to_dict() for row in rows]


def update_user_subscription(user_id, subscription_type, stripe_customer_id=None, stripe_subscription_id=None,
                             subscription_status=None, activated_at=None, expires_at=None):
    with get_session() as s:
        existing = s.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.subscription_type == subscription_type,
        ).first()
        if existing:
            if stripe_customer_id is not None: existing.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id is not None: existing.stripe_subscription_id = stripe_subscription_id
            if subscription_status is not None: existing.subscription_status = subscription_status
            if activated_at is not None: existing.activated_at = activated_at
            if expires_at is not None: existing.expires_at = expires_at
        else:
            s.add(UserSubscription(
                user_id=user_id,
                subscription_type=subscription_type,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                subscription_status=subscription_status or 'inactive',
                activated_at=activated_at,
                expires_at=expires_at,
            ))


def record_per_use_purchase(user_id, service_type, amount, stripe_payment_intent_id=None):
    with get_session() as s:
        row = PerUsePurchase(user_id=user_id, service_type=service_type, amount=amount,
                             stripe_payment_intent_id=stripe_payment_intent_id, status='completed')
        s.add(row)
        s.flush()
        return row.id


def use_per_use_purchase(user_id, service_type):
    """Mark one purchase as used. Returns True if found and updated."""
    from sqlalchemy import and_
    with get_session() as s:
        row = s.query(PerUsePurchase).filter(
            and_(
                PerUsePurchase.user_id == user_id,
                PerUsePurchase.service_type == service_type,
                PerUsePurchase.used_at == None,
                PerUsePurchase.status == 'completed',
            )
        ).order_by(PerUsePurchase.created_at).first()
        if not row:
            return False
        setattr(row, 'used_at', datetime.utcnow())
        return True
