"""
Database layer for Jet Finder. Uses PostgreSQL when DATABASE_URL is set (Railway),
otherwise SQLite for localhost. Replaces direct sqlite3 for users/listings.
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, text
from sqlalchemy.types import JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

# DATABASE_URL from env (Railway Postgres) or SQLite for local
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/jet_finder.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

_connect_args: dict = {}
if DATABASE_URL.startswith('sqlite'):
    _connect_args = {'check_same_thread': False}
elif DATABASE_URL.startswith('postgresql'):
    # Railway and most cloud Postgres require SSL
    _connect_args = {'sslmode': 'require'}

_engine_kw: dict = dict(
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


class Airport(Base):
    __tablename__ = 'airports'
    id = Column(Integer, primary_key=True, autoincrement=True)
    iata = Column(String(10))
    icao = Column(String(10))
    name = Column(String(255))
    city = Column(String(100))
    country = Column(String(10))
    lat = Column(Float)
    lon = Column(Float)
    size = Column(String(10))

    def to_dict(self):
        return {
            'iata': self.iata, 'icao': self.icao, 'name': self.name,
            'city': self.city, 'country': self.country,
            'lat': self.lat, 'lon': self.lon, 'size': self.size,
        }


class AircraftProfile(Base):
    """Stores full aircraft dict as JSON for /api/aircraft-data and performance profiles."""
    __tablename__ = 'aircraft_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(JSON, nullable=False)  # full aircraft dict (Postgres JSONB, SQLite TEXT)

    def to_dict(self):
        d = dict(self.data) if isinstance(self.data, dict) else {}
        d['id'] = self.id  # ensure id matches primary key
        return d


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


class ServiceProvider(Base):
    __tablename__ = 'service_providers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    business_name = Column(String(255), nullable=False)
    service_type = Column(String(100), nullable=False)
    service_subcategory = Column(String(100))
    description = Column(Text)
    street_address = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    zip_code = Column(String(20))
    country = Column(String(100), default='US')
    latitude = Column(Float)
    longitude = Column(Float)
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    business_hours = Column(Text)
    certifications = Column(Text)
    price_range = Column(String(50))
    years_in_business = Column(Integer)
    employee_count = Column(Integer)
    service_area_radius = Column(Integer, default=50)
    accepts_insurance = Column(Boolean, default=False)
    emergency_service = Column(Boolean, default=False)
    status = Column(String(50), default='active')
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ServiceProviderReview(Base):
    __tablename__ = 'service_provider_reviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    reviewer_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)
    review_text = Column(Text)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ServiceProviderContact(Base):
    __tablename__ = 'service_provider_contacts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('service_providers.id'))
    customer_id = Column(Integer, ForeignKey('users.id'))
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_phone = Column(String(50))
    service_requested = Column(String(255))
    message = Column(Text, nullable=False)
    urgency = Column(String(50), default='normal')
    preferred_contact_method = Column(String(50), default='email')
    project_timeline = Column(String(255))
    estimated_budget = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class BuyerPreference(Base):
    __tablename__ = 'buyer_preferences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String(255))
    max_total_hours = Column(Integer)
    min_engine_hours_remaining = Column(Integer)
    preferred_avionics = Column(String(255))
    min_interior_rating = Column(Integer)
    max_maintenance_age_months = Column(Integer)
    min_paint_rating = Column(Integer)
    engine_hours_weight = Column(Float, default=0.2)
    interior_weight = Column(Float, default=0.2)
    avionics_weight = Column(Float, default=0.2)
    maintenance_weight = Column(Float, default=0.2)
    paint_weight = Column(Float, default=0.2)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PerformanceProfile(Base):
    """Cache table for performance profiles (admin populate)."""
    __tablename__ = 'performance_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    manufacturer = Column(String(200))
    category = Column(String(100))
    range_nm = Column(Float)
    speed_kts = Column(Float)
    passengers = Column(Integer)
    max_altitude = Column(Float)
    cabin_volume = Column(Float)
    baggage_volume = Column(Float)
    runway_length = Column(Float)
    fuel_capacity = Column(Float)
    empty_weight = Column(Float)
    max_weight = Column(Float)
    image_url = Column(String(500))
    performance_metrics = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def _find_data_paths():
    """Return (aircraft_csv_path, airports_json_path) or (None, None)."""
    from pathlib import Path
    base = Path(__file__).resolve().parent
    candidates = [
        (base / 'static' / 'data' / 'aircraft_data.csv', base / 'static' / 'data' / 'airports.json'),
        (base / 'Aircraft Data - Aircraft Data (1).csv', base / 'airports.json'),
        (base / 'static' / 'data' / 'Aircraft Data - Aircraft Data (1).csv', base / 'static' / 'data' / 'airports.json'),
    ]
    for csv_p, json_p in candidates:
        if csv_p.is_file() and json_p.is_file():
            return (str(csv_p), str(json_p))
    return (None, None)


def seed_aircraft_and_airports():
    """Populate aircraft_profiles and airports from CSV/JSON if tables are empty."""
    try:
        from data_loader import load_aircraft_from_csv, load_airports_from_json
    except ImportError:
        return
    csv_path, json_path = _find_data_paths()
    if not csv_path or not json_path:
        return
    try:
        with get_session() as s:
            # Seed aircraft
            if s.query(AircraftProfile).count() == 0:
                aircraft_list = load_aircraft_from_csv(csv_path)
                for ac in aircraft_list:
                    ac_id = ac.get('id', 0)
                    s.add(AircraftProfile(id=ac_id, data=ac))
            # Seed airports
            if s.query(Airport).count() == 0:
                airports_list = load_airports_from_json(json_path)
                for ap in airports_list:
                    s.add(Airport(
                        iata=ap.get('iata'),
                        icao=ap.get('icao'),
                        name=ap.get('name'),
                        city=ap.get('city'),
                        country=ap.get('country'),
                        lat=float(ap.get('lat', 0) or 0),
                        lon=float(ap.get('lon', 0) or 0),
                        size=ap.get('size'),
                    ))
    except Exception:
        pass


def get_all_aircraft_profiles():
    """Return list of aircraft dicts from DB (for /api/aircraft-data, performance profiles)."""
    with get_session() as s:
        rows = s.query(AircraftProfile).order_by(AircraftProfile.id).all()
        return [r.to_dict() for r in rows]


def get_all_airports():
    """Return list of airport dicts from DB (for /api/airports)."""
    with get_session() as s:
        rows = s.query(Airport).all()
        return [r.to_dict() for r in rows]


def init_db():
    """Create tables if they do not exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    seed_aircraft_and_airports()
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


def get_database_status():
    """
    Return dict with connection status, table counts, and any error.
    Use for /api/health or /api/diagnostic on Railway to verify Postgres is used and has data.
    """
    out = {'db_ok': False, 'table_counts': {}, 'connection_error': None, 'database_type': 'sqlite' if DATABASE_URL.startswith('sqlite') else 'postgresql'}
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        out['db_ok'] = True
    except Exception as e:
        out['connection_error'] = str(e)
        return out
    # Collect row counts for main tables (same names as model __tablename__)
    tables = ['users', 'user_listings', 'user_subscriptions', 'per_use_purchases', 'airports', 'aircraft_profiles',
              'service_providers', 'buyer_preferences', 'performance_profiles']
    for table in tables:
        try:
            with engine.connect() as conn:
                r = conn.execute(text(f'SELECT COUNT(*) FROM {table}'))
                out['table_counts'][table] = r.scalar() or 0
        except Exception as e:
            out['table_counts'][table] = f'error: {e}'
    return out


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
            status='active',
            payment_status='pending',
        )
        s.add(row)
        s.flush()
        return row.id


def get_listings_by_user_id(user_id):
    """Return all listings for a user (any status: active, pending, deleted) for 'My Listings'."""
    with get_session() as s:
        rows = s.query(UserListing).filter(UserListing.user_id == user_id).order_by(UserListing.created_at.desc()).all()
        return [row.to_dict() for row in rows]


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


def has_unused_service_provider_credit(user_id):
    """True if user has at least one unused service_provider_search per-use purchase."""
    from sqlalchemy import and_
    with get_session() as s:
        row = s.query(PerUsePurchase).filter(
            and_(
                PerUsePurchase.user_id == user_id,
                PerUsePurchase.service_type == 'service_provider_search',
                PerUsePurchase.used_at == None,
                PerUsePurchase.status == 'completed',
            )
        ).order_by(PerUsePurchase.created_at.desc()).first()
        return row is not None


# --- Service providers (Railway-compatible: no sqlite3) ---
def create_service_provider(user_id, provider_data):
    with get_session() as s:
        lat = lon = None
        if provider_data.get('street_address') and provider_data.get('city') and provider_data.get('state'):
            try:
                lat, lon = 40.7128, -74.0060
            except Exception:
                pass
        sp = ServiceProvider(
            user_id=user_id,
            business_name=provider_data['business_name'],
            service_type=provider_data['service_type'],
            service_subcategory=provider_data.get('service_subcategory'),
            description=provider_data.get('description'),
            street_address=provider_data.get('street_address'),
            city=provider_data['city'],
            state=provider_data['state'],
            zip_code=provider_data.get('zip_code'),
            country=provider_data.get('country', 'US'),
            latitude=lat,
            longitude=lon,
            phone=provider_data.get('phone'),
            email=provider_data.get('email'),
            website=provider_data.get('website'),
            business_hours=provider_data.get('business_hours'),
            certifications=provider_data.get('certifications'),
            price_range=provider_data.get('price_range'),
            years_in_business=provider_data.get('years_in_business'),
            employee_count=provider_data.get('employee_count'),
            service_area_radius=provider_data.get('service_area_radius', 50),
            accepts_insurance=bool(provider_data.get('accepts_insurance', False)),
            emergency_service=bool(provider_data.get('emergency_service', False)),
        )
        s.add(sp)
        s.flush()
        return sp.id


def search_service_providers(service_type=None, location=None, radius=50, keywords=None,
                             verified_only=False, sort_by='rating', limit=20):
    with get_session() as s:
        q = s.query(ServiceProvider).filter(ServiceProvider.status == 'active')
        if service_type:
            q = q.filter(ServiceProvider.service_type == service_type)
        if verified_only:
            q = q.join(User).filter(User.is_verified_seller == True)
        if keywords:
            k = f'%{keywords}%'
            q = q.filter(
                (ServiceProvider.business_name.ilike(k)) |
                (ServiceProvider.description.ilike(k)) |
                (ServiceProvider.service_subcategory.ilike(k))
            )
        if location:
            loc = f'%{location}%'
            q = q.filter(
                (ServiceProvider.city.ilike(loc)) |
                (ServiceProvider.state.ilike(loc))
            )
        if sort_by == 'name':
            q = q.order_by(ServiceProvider.business_name.asc())
        elif sort_by == 'newest':
            q = q.order_by(ServiceProvider.created_at.desc())
        else:
            q = q.order_by(ServiceProvider.average_rating.desc(), ServiceProvider.total_reviews.desc())
        rows = q.limit(limit).all()
        out = []
        for sp in rows:
            d = sp.to_dict()
            u = s.query(User).filter(User.id == sp.user_id).first()
            d['first_name'] = u.first_name if u else None
            d['last_name'] = u.last_name if u else None
            out.append(d)
        return out


def get_service_provider_details(provider_id):
    with get_session() as s:
        sp = s.query(ServiceProvider).filter(
            ServiceProvider.id == provider_id,
            ServiceProvider.status == 'active',
        ).first()
        if not sp:
            return None
        d = sp.to_dict()
        u = s.query(User).filter(User.id == sp.user_id).first()
        d['user_email'] = u.email if u else None
        d['first_name'] = u.first_name if u else None
        d['last_name'] = u.last_name if u else None
        reviews = s.query(ServiceProviderReview).filter(
            ServiceProviderReview.provider_id == provider_id,
            ServiceProviderReview.status == 'active',
        ).order_by(ServiceProviderReview.created_at.desc()).limit(10).all()
        d['reviews'] = []
        for r in reviews:
            rd = r.to_dict()
            ru = s.query(User).filter(User.id == r.reviewer_id).first()
            rd['first_name'] = ru.first_name if ru else None
            rd['last_name'] = ru.last_name if ru else None
            d['reviews'].append(rd)
        return d


def contact_service_provider(provider_id, customer_data):
    with get_session() as s:
        c = ServiceProviderContact(
            provider_id=provider_id,
            customer_id=customer_data.get('customer_id'),
            customer_name=customer_data['customer_name'],
            customer_email=customer_data['customer_email'],
            customer_phone=customer_data.get('customer_phone'),
            service_requested=customer_data.get('service_requested'),
            message=customer_data['message'],
            urgency=customer_data.get('urgency', 'normal'),
            preferred_contact_method=customer_data.get('preferred_contact_method', 'email'),
            project_timeline=customer_data.get('project_timeline'),
            estimated_budget=customer_data.get('estimated_budget'),
        )
        s.add(c)
        s.flush()
        return c.id


# --- Buyer preferences (Railway-compatible) ---
def save_buyer_preferences(user_id, session_id, data):
    with get_session() as s:
        if user_id:
            s.query(BuyerPreference).filter(BuyerPreference.user_id == user_id).delete()
        else:
            s.query(BuyerPreference).filter(BuyerPreference.session_id == session_id).delete()
        s.add(BuyerPreference(
            user_id=user_id,
            session_id=session_id,
            max_total_hours=data.get('max_total_hours'),
            min_engine_hours_remaining=data.get('min_engine_hours_remaining'),
            preferred_avionics=data.get('preferred_avionics'),
            min_interior_rating=data.get('min_interior_rating'),
            max_maintenance_age_months=data.get('max_maintenance_age_months'),
            min_paint_rating=data.get('min_paint_rating'),
            engine_hours_weight=float(data.get('engine_hours_weight', 0.2)),
            interior_weight=float(data.get('interior_weight', 0.2)),
            avionics_weight=float(data.get('avionics_weight', 0.2)),
            maintenance_weight=float(data.get('maintenance_weight', 0.2)),
            paint_weight=float(data.get('paint_weight', 0.2)),
        ))
    return True


def get_buyer_preferences(user_id, session_id):
    with get_session() as s:
        if user_id:
            row = s.query(BuyerPreference).filter(
                BuyerPreference.user_id == user_id
            ).order_by(BuyerPreference.created_at.desc()).first()
        else:
            row = s.query(BuyerPreference).filter(
                BuyerPreference.session_id == session_id
            ).order_by(BuyerPreference.created_at.desc()).first()
        return row.to_dict() if row else None


# --- Performance profiles cache (admin populate) ---
def clear_performance_profiles():
    with get_session() as s:
        s.query(PerformanceProfile).delete()
    return True


def add_performance_profiles(aircraft_list):
    """Insert performance profile rows. Uses DB-generated ids (Railway/Postgres safe)."""
    with get_session() as s:
        for ac in aircraft_list:
            metrics = "Speed: {}, Range: {}, Performance: {}".format(
                ac.get('best_speed_dollar', 0),
                ac.get('best_range_dollar', 0),
                ac.get('best_performance_dollar', 0),
            )
            row = PerformanceProfile(
                name=ac.get('aircraft_name', 'Unknown Aircraft'),
                manufacturer=ac.get('manufacturer', 'Unknown'),
                category=ac.get('category', 'Unknown'),
                range_nm=float(ac.get('range', 0) or 0),
                speed_kts=float(ac.get('speed', 0) or 0),
                passengers=int(ac.get('passengers', 0) or 0),
                max_altitude=float(ac.get('max_altitude', 0) or 0),
                cabin_volume=float(ac.get('cabin_volume', 0) or 0),
                baggage_volume=float(ac.get('baggage_volume', 0) or 0),
                runway_length=float(ac.get('runway_length', 0) or 0),
                fuel_capacity=float(ac.get('fuel_capacity', 0) or 0),
                empty_weight=float(ac.get('empty_weight', 0) or 0),
                max_weight=float(ac.get('max_weight', 0) or 0),
                image_url=ac.get('image', '/static/images/aircraft_placeholder.jpg'),
                performance_metrics=metrics,
            )
            s.add(row)
    return True
