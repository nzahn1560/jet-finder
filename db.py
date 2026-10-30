"""
Database layer for Jet Finder. Uses PostgreSQL when DATABASE_URL is set (Railway),
otherwise SQLite for localhost. Replaces direct sqlite3 for users/listings.

=============================================================================
PRODUCTION DATA SAFETY GUARANTEES
=============================================================================
1. User accounts and user_listings ONLY live in PostgreSQL (Railway).
   No code path in this file writes user data to JSON, CSV, or local files.
2. init_db() is *additive only*:
   - Uses Base.metadata.create_all (creates missing tables, never drops).
   - Uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS (Postgres).
   - Never runs DROP TABLE / TRUNCATE / DELETE FROM user_listings / drop_all.
3. Any function that COULD be destructive (clear caches, drop schema) must
   call assert_not_production() first, which raises in prod unless the
   operator explicitly sets ALLOW_DESTRUCTIVE_DB_OPS=yes_i_understand.
4. See BACKUPS.md for pg_dump / restore steps before doing any destructive op.
=============================================================================
"""
from __future__ import annotations

import json
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, text, UniqueConstraint, or_
from sqlalchemy.types import JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

_log = logging.getLogger(__name__)
Base = declarative_base()


# -----------------------------------------------------------------------------
# Production-safety helpers
# -----------------------------------------------------------------------------
_DESTRUCTIVE_OVERRIDE_VALUE = 'yes_i_understand'


def is_production() -> bool:
    """True when running in production. Any of the following triggers True:
      - FLASK_ENV=production
      - RAILWAY_ENVIRONMENT=production
      - DATABASE_URL starts with postgres (Railway-attached Postgres)
    """
    if (os.environ.get('FLASK_ENV') or '').lower() == 'production':
        return True
    if (os.environ.get('RAILWAY_ENVIRONMENT') or '').lower() == 'production':
        return True
    db_url = os.environ.get('DATABASE_URL') or ''
    if db_url.startswith('postgres'):
        return True
    return False


def assert_not_production(action: str) -> None:
    """Refuse to run a destructive action in production.

    Raises RuntimeError unless ALLOW_DESTRUCTIVE_DB_OPS=yes_i_understand is set.
    That override is intended for ONE-OFF emergency ops AFTER taking a pg_dump
    backup (see BACKUPS.md). Never bake the override into deploy config.
    """
    if not is_production():
        return
    if os.environ.get('ALLOW_DESTRUCTIVE_DB_OPS') == _DESTRUCTIVE_OVERRIDE_VALUE:
        _log.warning("PRODUCTION DESTRUCTIVE OP ALLOWED via env override: %s", action)
        return
    raise RuntimeError(
        f"BLOCKED in production: '{action}'. "
        f"Set ALLOW_DESTRUCTIVE_DB_OPS={_DESTRUCTIVE_OVERRIDE_VALUE} only after a pg_dump backup."
    )


def DROP_ALL_TABLES_DANGEROUS():  # noqa: N802 - intentional SHOUT name
    """Last-resort full schema drop. Refuses in production without override.

    DO NOT call this from app startup. Only for local dev or manual recovery.
    """
    assert_not_production('Base.metadata.drop_all() / DROP_ALL_TABLES')
    Base.metadata.drop_all(bind=engine)
    _log.warning("DROP_ALL_TABLES_DANGEROUS: all tables dropped (non-production).")


def safety_status() -> dict:
    """Return current safety posture for /api/health and ops debugging."""
    return {
        'is_production': is_production(),
        'destructive_ops_override_set': (
            os.environ.get('ALLOW_DESTRUCTIVE_DB_OPS') == _DESTRUCTIVE_OVERRIDE_VALUE
        ),
        'database_type': 'postgresql' if (os.environ.get('DATABASE_URL') or '').startswith('postgres') else (
            'sqlite' if (os.environ.get('DATABASE_URL') or 'sqlite').startswith('sqlite') else 'unknown'
        ),
        'flask_env': os.environ.get('FLASK_ENV'),
        'railway_environment': os.environ.get('RAILWAY_ENVIRONMENT'),
    }

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
    profile_role = Column(String(50), default='other')  # broker, buyer, seller, mechanic, charter_operator, other
    broker_application_status = Column(String(20))  # pending, approved, denied
    roles = Column(String(200), default='')  # extra roles, comma-separated. Never includes admin.
    profile_location = Column(String(255))  # city, region, or business location
    broker_bio = Column(Text)
    broker_specialties = Column(String(500))
    broker_website = Column(String(255))
    broker_years = Column(Integer)
    broker_verified = Column(Boolean, default=False)
    broker_state = Column(String(100))
    broker_country = Column(String(100))
    broker_lat = Column(Float)
    broker_lon = Column(Float)
    broker_image_url = Column(String(500))
    # Profile photo and company-logo background. Values are image data URLs until Cloudflare R2 stores the files.
    profile_photo_url = Column(Text)
    company_logo_url = Column(Text)
    is_admin = Column(Boolean, default=False, nullable=False)  # Admin portal access
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
    stripe_subscription_id = Column(String(255))
    stripe_customer_id = Column(String(255))
    approved_by = Column(Integer, ForeignKey('users.id'))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    engine_type = Column(String(100))
    manufacturer = Column(String(200))
    pricing_plan = Column(String(50), default='monthly')
    # public | broker_only | private. Legacy value off_market means broker_only.
    market = Column(String(20), default='public', nullable=False)
    serial_number = Column(String(80))
    registration = Column(String(20))
    variant = Column(String(120))
    engine_program = Column(String(120))
    engine_hours = Column(Integer)
    engine_cycles = Column(Integer)
    maintenance_status = Column(Text)
    avionics = Column(Text)
    paint_year = Column(Integer)
    interior_year = Column(Integer)
    passenger_config = Column(String(80))
    admin_notes = Column(Text)
    amendment_note = Column(Text)
    review_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    city = Column(String(120))
    state = Column(String(40))
    # sale | wanted. Public listings stay sale. Off-market brokers choose one.
    listing_intent = Column(String(20), default='sale', nullable=False)
    # JSON proposal for an approved listing. Live columns stay put until an admin approves it.
    pending_changes = Column(Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class BrokerTeam(Base):
    """A company on the broker map. The team pays; members do not."""
    __tablename__ = 'broker_teams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    admin_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    city = Column(String(120))
    state = Column(String(40))
    location = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    logo_url = Column(Text)
    bio = Column(Text)
    category = Column(String(40))
    subscription_status = Column(String(20), default='inactive', nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class BrokerTeamMember(Base):
    """An individual broker asking to join a team, or already on it."""
    __tablename__ = 'broker_team_members'
    __table_args__ = (UniqueConstraint('team_id', 'user_id', name='uq_broker_team_member'),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('broker_teams.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    status = Column(String(20), default='pending', nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ContactMessage(Base):
    """A message sent from the public contact card. Admins read these in Alerts."""
    __tablename__ = 'contact_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(40))
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if data.get('created_at') is not None and not isinstance(data['created_at'], str):
            data['created_at'] = data['created_at'].isoformat()
        return data


class UserNotification(Base):
    """An alert a person sees on their profile, and that can also be emailed."""
    __tablename__ = 'user_notifications'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    kind = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text)
    href = Column(String(255))
    read_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for key in ('read_at', 'created_at'):
            if data.get(key) is not None and not isinstance(data[key], str):
                data[key] = data[key].isoformat()
        return data


class CharterInquiry(Base):
    """A charter estimate request. Stored so a coordinator can follow up."""
    __tablename__ = 'charter_inquiries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50))
    departure_airport = Column(String(10), nullable=False)
    arrival_airport = Column(String(10), nullable=False)
    departure_date = Column(String(40))
    passengers = Column(Integer, default=1)
    aircraft_name = Column(String(255))
    estimated_price = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ListingAudit(Base):
    """Who changed a listing, and from which status to which."""
    __tablename__ = 'listing_audits'
    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('user_listings.id'), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(40), nullable=False)
    previous_status = Column(String(50))
    new_status = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class StripeEvent(Base):
    """Processed Stripe event ids so a repeated webhook cannot charge twice."""
    __tablename__ = 'stripe_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class AuthRateHit(Base):
    """Shared login/signup hits so every Gunicorn worker sees the same counter."""
    __tablename__ = 'auth_rate_hits'
    id = Column(Integer, primary_key=True, autoincrement=True)
    bucket_key = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)


class BrokerMessage(Base):
    """A buyer or seller note sent to an approved broker."""
    __tablename__ = 'broker_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    listing_id = Column(Integer, ForeignKey('user_listings.id'))
    kind = Column(String(20), nullable=False)
    aircraft_name = Column(String(200))
    notes = Column(Text)
    contact_email = Column(String(255))
    contact_phone = Column(String(40))
    sender_hidden = Column(Boolean, default=False)
    recipient_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class CharterOperator(Base):
    __tablename__ = 'charter_operators'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    company_name = Column(String(200), nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    status = Column(String(40), default='active')
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class CharterAircraft(Base):
    """An operator's real aircraft. Empty table means nothing is available to book."""
    __tablename__ = 'charter_aircraft'
    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, ForeignKey('charter_operators.id'), nullable=False, index=True)
    profile_id = Column(Integer)
    name = Column(String(200), nullable=False)
    registration = Column(String(20))
    base_airport = Column(String(10))
    seats = Column(Integer)
    hourly_rate = Column(Float)
    range_nm = Column(Integer)
    speed_kts = Column(Integer)
    status = Column(String(40), default='active', index=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class CharterBlock(Base):
    __tablename__ = 'charter_blocks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(Integer, ForeignKey('charter_aircraft.id'), nullable=False, index=True)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    reason = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class CharterBooking(Base):
    """A request to book. Status stays 'requested' until an operator accepts it."""
    __tablename__ = 'charter_bookings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    aircraft_id = Column(Integer, ForeignKey('charter_aircraft.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    contact_name = Column(String(200), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50))
    departure_airport = Column(String(10), nullable=False)
    arrival_airport = Column(String(10), nullable=False)
    departure_date = Column(String(20))
    passengers = Column(Integer, default=1)
    estimated_price = Column(Float)
    notes = Column(Text)
    status = Column(String(40), default='requested', index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SavedAircraft(Base):
    """Aircraft a customer is watching: a catalog model, or a specific listing for sale.

    Stored in Postgres so a profile survives deploys and works on Railway.
    target_id is a string so it can hold a catalog id or a marketplace listing id.
    """
    __tablename__ = 'saved_aircraft'
    __table_args__ = (
        UniqueConstraint('user_id', 'kind', 'target_id', name='uq_saved_aircraft_user_target'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # catalog | listing
    target_id = Column(String(64), nullable=False)
    title = Column(String(255))
    manufacturer = Column(String(200))
    price = Column(Float)
    location = Column(String(255))
    image_url = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class UserSession(Base):
    """Token-based browser session, set as `jet_session` HttpOnly cookie.

    Login/signup inserts a row with a random 128-hex-char token and 30-day expiry.
    Every authenticated request looks up the user by cookie token here.
    Logout deletes the row, invalidating the cookie immediately.
    """
    __tablename__ = 'user_sessions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class ListingMedia(Base):
    """Per-listing photo/video metadata. Files themselves live in Cloudflare R2.

    PostgreSQL only stores the metadata: which listing, what type, the R2 object
    key, the public URL, and a sort order. The bytes never live in Railway's
    disk or Postgres — only in R2 (or, locally for dev, in static/uploads/dev).
    """
    __tablename__ = 'listing_media'
    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey('user_listings.id'), nullable=False, index=True)
    media_type = Column(String(16), nullable=False, default='photo')  # 'photo' | 'video'
    r2_object_key = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=False)
    thumbnail_url = Column(String(1024))
    content_type = Column(String(128))
    size_bytes = Column(Integer)
    sort_order = Column(Integer, default=0, index=True)
    # False while a new photo on an approved listing is waiting for approval.
    published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PasswordResetToken(Base):
    """One-time password reset token, emailed to the user as a link."""
    __tablename__ = 'password_reset_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)

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
    import logging
    _log = logging.getLogger(__name__)
    try:
        from data_loader import load_aircraft_from_csv, load_airports_from_json
    except ImportError as e:
        _log.warning("seed_aircraft_and_airports: data_loader not available: %s", e)
        return
    csv_path, json_path = _find_data_paths()
    if not csv_path or not json_path:
        _log.warning("seed_aircraft_and_airports: CSV or JSON not found (paths: %s, %s)", csv_path, json_path)
        return
    try:
        with get_session() as s:
            if s.query(AircraftProfile).count() == 0:
                aircraft_list = load_aircraft_from_csv(csv_path)
                for ac in aircraft_list:
                    ac_id = ac.get('id', 0)
                    s.add(AircraftProfile(id=ac_id, data=ac))
                _log.info("Seeded %d aircraft from %s", len(aircraft_list), csv_path)
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
                _log.info("Seeded %d airports from %s", len(airports_list), json_path)
    except Exception as e:
        _log.exception("seed_aircraft_and_airports failed: %s", e)


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
    """Create tables if they do not exist. Safe to call on every startup.

    SAFETY GUARANTEE (do not break this contract):
      * Only ever calls Base.metadata.create_all (additive: CREATE TABLE IF NOT EXISTS).
      * Only ever uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS for schema upgrades.
      * Never drops, truncates, deletes from, or recreates user_listings / users.
      * Seeding only inserts when the target table is EMPTY (see seed_aircraft_and_airports).

    If you need to change a column type or remove a column, write a separate
    migration script that takes a backup first (see BACKUPS.md) and never put
    DROP/DELETE/TRUNCATE into this function.

    Two Gunicorn workers can start together. If the other worker already
    created a table, create_all is retried. Existing rows are left in place.
    """
    from sqlalchemy.exc import OperationalError, ProgrammingError
    last_error = None
    for _attempt in range(3):
        try:
            Base.metadata.create_all(bind=engine)
            last_error = None
            break
        except (OperationalError, ProgrammingError) as exc:
            if 'already exists' not in str(exc).lower():
                raise
            last_error = exc
    if last_error is not None:
        raise last_error
    seed_aircraft_and_airports()
    # SQLite: add columns that may be missing in existing DBs (e.g. created by older app)
    if DATABASE_URL.startswith('sqlite'):
        with engine.connect() as conn:
            for col_def in [
                'payment_status TEXT DEFAULT \'pending\'',
                'payment_session_id TEXT',
                'stripe_payment_intent_id TEXT',
                'stripe_subscription_id TEXT',
                'stripe_customer_id TEXT',
                'approved_by INTEGER',
                'approved_at TIMESTAMP',
                'rejection_reason TEXT',
                'documents TEXT',
                'engine_type TEXT',
                'manufacturer TEXT',
                'pricing_plan TEXT DEFAULT \'monthly\'',
                'market TEXT DEFAULT \'public\'',
                'serial_number TEXT',
                'registration TEXT',
                'variant TEXT',
                'engine_program TEXT',
                'engine_hours INTEGER',
                'engine_cycles INTEGER',
                'maintenance_status TEXT',
                'avionics TEXT',
                'paint_year INTEGER',
                'interior_year INTEGER',
                'passenger_config TEXT',
                'admin_notes TEXT',
                'amendment_note TEXT',
                'review_message TEXT',
                'city TEXT',
                'state TEXT',
                'listing_intent TEXT DEFAULT \'sale\'',
                'pending_changes TEXT',
            ]:
                try:
                    conn.execute(text(f'ALTER TABLE user_listings ADD COLUMN {col_def}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    pass  # column already exists
            try:
                conn.execute(text('ALTER TABLE listing_media ADD COLUMN published BOOLEAN DEFAULT 1'))
                conn.commit()
            except Exception:
                conn.rollback()
            for col_def in [
                'profile_role VARCHAR(50) DEFAULT \'other\'',
                'profile_location VARCHAR(255)',
                'is_admin BOOLEAN DEFAULT 0',
                'roles VARCHAR(200)',
                'broker_bio TEXT',
                'broker_specialties VARCHAR(500)',
                'broker_website VARCHAR(255)',
                'broker_years INTEGER',
                'broker_verified BOOLEAN DEFAULT 0',
                'broker_state VARCHAR(100)',
                'broker_country VARCHAR(100)',
                'broker_lat FLOAT',
                'broker_lon FLOAT',
                'broker_image_url VARCHAR(500)',
                'profile_photo_url TEXT',
                'company_logo_url TEXT',
                'broker_application_status VARCHAR(20)',
            ]:
                try:
                    conn.execute(text(f'ALTER TABLE users ADD COLUMN {col_def}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    pass
    elif DATABASE_URL.startswith('postgresql'):
        with engine.connect() as conn:
            for col, typ in [
                ('profile_role', "VARCHAR(50) DEFAULT 'other'"),
                ('profile_location', 'VARCHAR(255)'),
                ('is_admin', 'BOOLEAN DEFAULT FALSE NOT NULL'),
                ('roles', 'VARCHAR(200)'),
                ('broker_bio', 'TEXT'),
                ('broker_specialties', 'VARCHAR(500)'),
                ('broker_website', 'VARCHAR(255)'),
                ('broker_years', 'INTEGER'),
                ('broker_verified', 'BOOLEAN DEFAULT FALSE'),
                ('broker_state', 'VARCHAR(100)'),
                ('broker_country', 'VARCHAR(100)'),
                ('broker_lat', 'DOUBLE PRECISION'),
                ('broker_lon', 'DOUBLE PRECISION'),
                ('broker_image_url', 'VARCHAR(500)'),
                ('profile_photo_url', 'TEXT'),
                ('company_logo_url', 'TEXT'),
                ('broker_application_status', 'VARCHAR(20)'),
            ]:
                try:
                    conn.execute(text(f'ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    pass
            for col, typ in [
                ('market', "VARCHAR(20) DEFAULT 'public'"),
                ('serial_number', 'VARCHAR(80)'),
                ('registration', 'VARCHAR(20)'),
                ('variant', 'VARCHAR(120)'),
                ('engine_program', 'VARCHAR(120)'),
                ('engine_hours', 'INTEGER'),
                ('engine_cycles', 'INTEGER'),
                ('maintenance_status', 'TEXT'),
                ('avionics', 'TEXT'),
                ('paint_year', 'INTEGER'),
                ('interior_year', 'INTEGER'),
                ('passenger_config', 'VARCHAR(80)'),
                ('admin_notes', 'TEXT'),
                ('amendment_note', 'TEXT'),
                ('review_message', 'TEXT'),
                ('city', 'VARCHAR(120)'),
                ('state', 'VARCHAR(40)'),
                ('listing_intent', "VARCHAR(20) DEFAULT 'sale'"),
                ('pending_changes', 'TEXT'),
                ('stripe_subscription_id', 'VARCHAR(255)'),
                ('stripe_customer_id', 'VARCHAR(255)'),
            ]:
                try:
                    conn.execute(text(f'ALTER TABLE user_listings ADD COLUMN IF NOT EXISTS {col} {typ}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    pass
            try:
                conn.execute(text(
                    'ALTER TABLE listing_media ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT TRUE'
                ))
                conn.commit()
            except Exception:
                conn.rollback()
            try:
                conn.execute(text('ALTER TABLE broker_teams ADD COLUMN IF NOT EXISTS category VARCHAR(40)'))
                conn.commit()
            except Exception:
                conn.rollback()
            for col, typ in (
                ('contact_email', 'VARCHAR(255)'),
                ('contact_phone', 'VARCHAR(40)'),
                ('sender_hidden', 'BOOLEAN DEFAULT FALSE'),
                ('recipient_hidden', 'BOOLEAN DEFAULT FALSE'),
            ):
                try:
                    conn.execute(text(f'ALTER TABLE broker_messages ADD COLUMN IF NOT EXISTS {col} {typ}'))
                    conn.commit()
                except Exception:
                    conn.rollback()
    if DATABASE_URL.startswith('sqlite'):
        with engine.connect() as conn:
            try:
                conn.execute(text('ALTER TABLE broker_teams ADD COLUMN category VARCHAR(40)'))
                conn.commit()
            except Exception:
                conn.rollback()
            for col_def in (
                'contact_email VARCHAR(255)',
                'contact_phone VARCHAR(40)',
                'sender_hidden BOOLEAN DEFAULT 0',
                'recipient_hidden BOOLEAN DEFAULT 0',
            ):
                try:
                    conn.execute(text(f'ALTER TABLE broker_messages ADD COLUMN {col_def}'))
                    conn.commit()
                except Exception:
                    conn.rollback()


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
    tables = ['users', 'user_sessions', 'user_listings', 'listing_media', 'saved_aircraft', 'user_subscriptions', 'per_use_purchases', 'airports', 'aircraft_profiles',
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


def create_user(email, password_hash, first_name=None, last_name=None, company=None, phone=None,
                profile_role=None, profile_location=None):
    with get_session() as s:
        u = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            company=company,
            phone=phone,
            profile_role=(profile_role or 'other').lower().strip() if profile_role else 'other',
            profile_location=profile_location.strip() if (profile_location and isinstance(profile_location, str)) else None,
        )
        s.add(u)
        s.flush()
        return u.id


_PROFILE_ROLES = {'broker', 'buyer', 'seller', 'mechanic', 'charter_operator', 'other'}


def stored_image_url(value):
    """Keep a small image preview or a future Cloudflare R2 https URL. Reject anything else."""
    if value in (None, ''):
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.startswith('https://') and len(value) <= 500:
        return value
    if (
        value.startswith('data:image/')
        and ';base64,' in value
        and len(value) <= 1_200_000
        and value.split(',', 1)[0] in ('data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64')
    ):
        return value
    return None


def update_user_profile(user_id, fields):
    """Update the public profile fields a customer can edit themselves."""
    allowed = {
        'first_name', 'last_name', 'company', 'phone', 'profile_role', 'profile_location',
        'roles', 'broker_bio', 'broker_specialties', 'broker_website', 'broker_years',
        'broker_state', 'broker_country', 'broker_image_url',
        'profile_photo_url', 'company_logo_url',
    }
    safe = {}
    for key, value in (fields or {}).items():
        if key not in allowed:
            continue
        if isinstance(value, str):
            value = value.strip()
        safe[key] = value or None
    if 'profile_role' in safe:
        role = (safe['profile_role'] or 'other').lower()
        safe['profile_role'] = role if role in _PROFILE_ROLES else 'other'
    if 'roles' in safe:
        from authz import clean_roles
        safe['roles'] = clean_roles(safe['roles'])
    for image_key in ('profile_photo_url', 'company_logo_url'):
        if image_key not in safe:
            continue
        raw = (fields or {}).get(image_key)
        if raw in (None, ''):
            safe[image_key] = None
        else:
            cleaned = stored_image_url(raw if isinstance(raw, str) else safe[image_key])
            if cleaned is None:
                safe.pop(image_key, None)
            else:
                safe[image_key] = cleaned
    if isinstance(safe.get('broker_bio'), str):
        safe['broker_bio'] = safe['broker_bio'][:1000]
    if 'broker_years' in safe and safe['broker_years'] not in (None, ''):
        try:
            safe['broker_years'] = int(safe['broker_years'])
        except (TypeError, ValueError):
            safe.pop('broker_years', None)
    if not safe:
        return False
    with get_session() as s:
        n = s.query(User).filter(User.id == user_id).update(safe, synchronize_session=False)
        return n > 0


def save_aircraft_for_user(user_id, kind, target_id, snapshot=None):
    """Remember an aircraft on the customer's profile. Idempotent.

    kind is 'catalog' (a model in the search database) or 'listing'
    (a specific aircraft for sale). Returns the saved row id.
    """
    kind = (kind or '').strip().lower()
    if kind not in ('catalog', 'listing'):
        raise ValueError('invalid_kind')
    target_id = str(target_id or '').strip()
    if not target_id:
        raise ValueError('missing_target')
    snap = snapshot or {}
    with get_session() as s:
        existing = (
            s.query(SavedAircraft)
            .filter(
                SavedAircraft.user_id == user_id,
                SavedAircraft.kind == kind,
                SavedAircraft.target_id == target_id,
            )
            .first()
        )
        if existing:
            return int(existing.id)  # type: ignore[arg-type]
        row = SavedAircraft(
            user_id=user_id,
            kind=kind,
            target_id=target_id,
            title=(snap.get('title') or '')[:255] or None,
            manufacturer=(snap.get('manufacturer') or '')[:200] or None,
            price=snap.get('price'),
            location=(snap.get('location') or '')[:255] or None,
            image_url=(snap.get('image_url') or '')[:500] or None,
        )
        s.add(row)
        s.flush()
        saved_id = int(row.id)  # type: ignore[arg-type]
    if kind == 'listing':
        note_listing_watched(user_id, target_id)
    return saved_id


def remove_saved_aircraft(user_id, kind=None, target_id=None, saved_id=None):
    """Remove one saved aircraft. Match by row id, or by kind + target_id."""
    with get_session() as s:
        q = s.query(SavedAircraft).filter(SavedAircraft.user_id == user_id)
        if saved_id:
            q = q.filter(SavedAircraft.id == saved_id)
        elif kind and target_id is not None:
            q = q.filter(SavedAircraft.kind == kind, SavedAircraft.target_id == str(target_id))
        else:
            return False
        return q.delete(synchronize_session=False) > 0


def list_saved_aircraft(user_id):
    """Saved aircraft for a profile, refreshed from the live catalog or listing when possible."""
    with get_session() as s:
        rows = (
            s.query(SavedAircraft)
            .filter(SavedAircraft.user_id == user_id)
            .order_by(SavedAircraft.created_at.desc())
            .all()
        )
        out = []
        for r in rows:
            created = getattr(r, 'created_at', None)
            item = {
                'id': r.id,
                'kind': r.kind,
                'target_id': r.target_id,
                'title': r.title,
                'manufacturer': r.manufacturer,
                'price': r.price,
                'location': r.location,
                'image_url': r.image_url,
                'created_at': created.isoformat() if created is not None else None,
            }
            target = str(r.target_id or '')
            if r.kind == 'catalog' and target.isdigit():
                prof = s.query(AircraftProfile).filter(AircraftProfile.id == int(target)).first()
                if prof is not None:
                    data = prof.to_dict()
                    item['title'] = data.get('aircraft_name') or data.get('name') or item['title']
                    item['manufacturer'] = data.get('manufacturer') or item['manufacturer']
                    if data.get('price') not in (None, ''):
                        item['price'] = data.get('price')
                    item['range'] = data.get('range')
                    item['speed'] = data.get('speed')
            elif r.kind == 'listing' and target.isdigit():
                listing = s.query(UserListing).filter(UserListing.id == int(target)).first()
                if listing is not None:
                    item['title'] = getattr(listing, 'title', None) or item['title']
                    item['price'] = getattr(listing, 'price', None)
                    item['location'] = getattr(listing, 'location', None)
                    item['manufacturer'] = getattr(listing, 'manufacturer', None)
                    item['status'] = getattr(listing, 'status', None)
            out.append(item)
        return out


# --- Session/token helpers (jet_session cookie) ---
def create_user_session(user_id, token, expires_at):
    """Insert a new session row tied to user_id with the given random token."""
    with get_session() as s:
        row = UserSession(user_id=user_id, token=token, expires_at=expires_at)
        s.add(row)
        s.flush()
        return row.id


def get_user_by_session_token(token):
    """Return user dict for a valid (non-expired) session token, else None.

    Caller is the auth layer; never trust a user_id from the client — always
    derive it via this lookup from the HttpOnly `jet_session` cookie.
    """
    if not token:
        return None
    with get_session() as s:
        sess = s.query(UserSession).filter(UserSession.token == token).first()
        if not sess:
            return None
        expires = getattr(sess, 'expires_at', None)
        if expires is not None and expires < datetime.utcnow():
            s.delete(sess)
            return None
        u = s.query(User).filter(User.id == sess.user_id).first()
        return u.to_dict() if u else None


def delete_user_session_token(token):
    """Remove a session row (used on logout). Returns True if deleted."""
    if not token:
        return False
    with get_session() as s:
        n = s.query(UserSession).filter(UserSession.token == token).delete()
        return n > 0


def delete_user_account(user_id):
    """Remove an account and the rows that belong to it. Returns False when the user is missing."""
    with get_session() as s:
        user = s.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            return False
        listing_ids = [
            row.id for row in s.query(UserListing.id).filter(UserListing.user_id == user.id).all()
        ]
        if listing_ids:
            s.query(BrokerMessage).filter(BrokerMessage.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            s.query(ListingMedia).filter(ListingMedia.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            s.query(ListingAudit).filter(ListingAudit.listing_id.in_(listing_ids)).delete(synchronize_session=False)
            s.query(UserListing).filter(UserListing.id.in_(listing_ids)).delete(synchronize_session=False)
        s.query(UserListing).filter(UserListing.approved_by == user.id).update(
            {UserListing.approved_by: None}, synchronize_session=False,
        )
        s.query(ListingAudit).filter(ListingAudit.actor_id == user.id).update(
            {ListingAudit.actor_id: None}, synchronize_session=False,
        )
        s.query(UserSession).filter(UserSession.user_id == user.id).delete(synchronize_session=False)
        s.query(UserNotification).filter(UserNotification.user_id == user.id).delete(synchronize_session=False)
        s.query(SavedAircraft).filter(SavedAircraft.user_id == user.id).delete(synchronize_session=False)
        s.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)
        s.query(UserSubscription).filter(UserSubscription.user_id == user.id).delete(synchronize_session=False)
        s.query(PerUsePurchase).filter(PerUsePurchase.user_id == user.id).delete(synchronize_session=False)
        s.query(BuyerPreference).filter(BuyerPreference.user_id == user.id).delete(synchronize_session=False)
        s.query(BrokerMessage).filter(
            (BrokerMessage.from_user_id == user.id) | (BrokerMessage.to_user_id == user.id)
        ).delete(synchronize_session=False)
        s.query(BrokerTeamMember).filter(BrokerTeamMember.user_id == user.id).delete(synchronize_session=False)
        team_ids = [
            row.id for row in s.query(BrokerTeam.id).filter(BrokerTeam.admin_user_id == user.id).all()
        ]
        if team_ids:
            s.query(BrokerTeamMember).filter(BrokerTeamMember.team_id.in_(team_ids)).delete(synchronize_session=False)
            s.query(BrokerTeam).filter(BrokerTeam.id.in_(team_ids)).delete(synchronize_session=False)
        s.query(CharterInquiry).filter(CharterInquiry.user_id == user.id).update(
            {CharterInquiry.user_id: None}, synchronize_session=False,
        )
        s.query(CharterBooking).filter(CharterBooking.user_id == user.id).update(
            {CharterBooking.user_id: None}, synchronize_session=False,
        )
        operator_ids = [
            row.id for row in s.query(CharterOperator.id).filter(CharterOperator.user_id == user.id).all()
        ]
        if operator_ids:
            aircraft_ids = [
                row.id for row in s.query(CharterAircraft.id).filter(
                    CharterAircraft.operator_id.in_(operator_ids)
                ).all()
            ]
            if aircraft_ids:
                s.query(CharterBlock).filter(CharterBlock.aircraft_id.in_(aircraft_ids)).delete(synchronize_session=False)
                s.query(CharterBooking).filter(CharterBooking.aircraft_id.in_(aircraft_ids)).delete(synchronize_session=False)
                s.query(CharterAircraft).filter(CharterAircraft.id.in_(aircraft_ids)).delete(synchronize_session=False)
            s.query(CharterOperator).filter(CharterOperator.id.in_(operator_ids)).delete(synchronize_session=False)
        s.query(ServiceProviderReview).filter(ServiceProviderReview.reviewer_id == user.id).delete(synchronize_session=False)
        s.query(ServiceProviderContact).filter(ServiceProviderContact.customer_id == user.id).delete(synchronize_session=False)
        s.query(ServiceProvider).filter(ServiceProvider.user_id == user.id).update(
            {ServiceProvider.user_id: None}, synchronize_session=False,
        )
        s.delete(user)
        return True


def purge_expired_user_sessions():
    """Best-effort cleanup of expired session rows. Safe to call periodically."""
    try:
        cutoff = datetime.utcnow()
        with get_session() as s:
            s.query(UserSession).filter(UserSession.expires_at < cutoff).delete()
    except Exception:
        pass


def set_user_admin(user_id, is_admin=True):
    """Grant/revoke admin. Used by a one-off script or psql."""
    with get_session() as s:
        n = s.query(User).filter(User.id == user_id).update({'is_admin': bool(is_admin)}, synchronize_session=False)
        return n > 0


# --- Password reset tokens ---
def create_password_reset_token(user_id, token, expires_at):
    with get_session() as s:
        row = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
        s.add(row)
        s.flush()
        return int(row.id)  # type: ignore[arg-type]


def get_valid_reset_token(token):
    """Return the token row dict if it exists, is unused, and not expired."""
    if not token:
        return None
    with get_session() as s:
        row = s.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
        if not row:
            return None
        if bool(row.used):
            return None
        expires = getattr(row, 'expires_at', None)
        if expires is not None and expires < datetime.utcnow():
            return None
        return row.to_dict()


def use_reset_token_and_set_password(token, new_password_hash):
    """Atomically mark the token used and update the user's password.

    Also deletes all existing sessions for that user (force re-login everywhere).
    Returns the user_id, or None on failure.
    """
    with get_session() as s:
        row = s.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
        if not row or bool(row.used):
            return None
        expires = getattr(row, 'expires_at', None)
        if expires is not None and expires < datetime.utcnow():
            return None
        uid = int(row.user_id)  # type: ignore[arg-type]
        s.query(PasswordResetToken).filter(PasswordResetToken.id == row.id).update(
            {'used': True}, synchronize_session=False)
        s.query(User).filter(User.id == uid).update({'password_hash': new_password_hash}, synchronize_session=False)
        s.query(UserSession).filter(UserSession.user_id == uid).delete(synchronize_session=False)
        return uid


def list_users_by_role(role, limit=500):
    """Public directory fields for one profile role (broker, mechanic, and so on)."""
    with get_session() as s:
        rows = (
            s.query(User)
            .filter(User.profile_role == role, User.is_suspended == False)  # noqa: E712
            .order_by(User.company.asc(), User.last_name.asc())
            .limit(limit)
            .all()
        )
        out = []
        for u in rows:
            out.append({
                'id': u.id,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'company': u.company,
                'phone': u.phone,
                'email': u.email,
                'profile_location': u.profile_location,
            })
        return out


def create_charter_inquiry(data):
    """Save a charter request. Returns the new row id."""
    with get_session() as s:
        row = CharterInquiry(
            user_id=data.get('user_id'),
            name=(data.get('name') or '').strip(),
            email=(data.get('email') or '').strip(),
            phone=(data.get('phone') or '').strip() or None,
            departure_airport=(data.get('departure_airport') or '').strip().upper(),
            arrival_airport=(data.get('arrival_airport') or '').strip().upper(),
            departure_date=(data.get('departure_date') or '').strip() or None,
            passengers=int(data.get('passengers') or 1),
            aircraft_name=(data.get('aircraft_name') or '').strip() or None,
            estimated_price=data.get('estimated_price'),
            notes=(data.get('notes') or '').strip() or None,
        )
        s.add(row)
        s.flush()
        return row.id


def list_all_users_basic(limit=500):
    """Admin: list users with basic account info, no sensitive fields."""
    with get_session() as s:
        rows = s.query(User).order_by(User.created_at.desc()).limit(limit).all()
        out = []
        for u in rows:
            out.append({
                'id': u.id,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'company': u.company,
                'phone': u.phone,
                'profile_role': u.profile_role,
                'profile_location': u.profile_location,
                'is_admin': bool(u.is_admin),
                'created_at': (u.created_at.isoformat() if getattr(u, 'created_at', None) is not None else None),
            })
        return out


# --- User listings helpers ---
def _public_market_clause():
    """Approved listings that belong on the public marketplace."""
    from sqlalchemy import or_
    return or_(
        UserListing.market.is_(None),
        UserListing.market == '',
        UserListing.market == 'public',
    )


def _stored_market(value) -> str:
    raw = str(value or '').strip().lower().replace('-', '_')
    if raw in ('off_market', 'broker_only'):
        return 'broker_only'
    if raw == 'private':
        return 'private'
    return 'public'


def _apply_listing_details(row, details):
    if not details:
        return
    keys = (
        'serial_number', 'registration', 'variant', 'engine_program', 'engine_hours',
        'engine_cycles', 'maintenance_status', 'avionics', 'paint_year', 'interior_year',
        'passenger_config', 'city', 'state', 'listing_intent',
    )
    for key in keys:
        if key not in details or details[key] in (None, ''):
            continue
        value = details[key]
        if key in ('engine_hours', 'engine_cycles', 'paint_year', 'interior_year'):
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
        if key == 'listing_intent':
            value = str(value).strip().lower()
            if value not in ('sale', 'wanted'):
                continue
        setattr(row, key, value)


def get_active_user_listings():
    """Approved public listings. Off-market aircraft stay off this list."""
    with get_session() as s:
        rows = (
            s.query(UserListing)
            .filter(UserListing.status == 'active', _public_market_clause())
            .order_by(UserListing.created_at.desc())
            .all()
        )
        return [row.to_dict() for row in rows]


def get_off_market_listings():
    """Approved listings that are visible only on the off-market page."""
    with get_session() as s:
        rows = (
            s.query(UserListing)
            .filter(UserListing.status == 'active', UserListing.market.in_(('off_market', 'broker_only')))
            .order_by(UserListing.created_at.desc())
            .all()
        )
        return [row.to_dict() for row in rows]


def create_user_listing(profile_id, title, year, price, hours, location, email, description,
                        images_str, documents_str, engine_type, manufacturer, pricing_plan, user_id=None,
                        status='pending', market='public', details=None):
    """Create a listing. Default status='pending' (awaiting admin approval).

    Pass status='unpaid' when payment is required before review.
    Listings only become publicly visible when an admin approves (status='active').
    """
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
            status=status or 'pending',
            payment_status='pending',
            market=_stored_market(market),
        )
        _apply_listing_details(row, details)
        s.add(row)
        s.flush()
        return row.id


def set_listing_payment_session(listing_id, session_id):
    """Store the Stripe Checkout session id on a listing (before redirecting to pay)."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(
            {'payment_session_id': session_id}, synchronize_session=False
        )
        return n > 0


def mark_listing_fee_paid(listing_id, payment_intent_id=None, session_id=None, subscription_id=None, customer_id=None):
    """Mark a listing fee paid and send an unpaid or draft listing to review."""
    if not listing_id:
        return None
    with get_session() as s:
        row = s.query(UserListing).filter(UserListing.id == listing_id).first()
        if not row:
            return None
        lid = int(row.id)  # type: ignore[arg-type]
        updates: dict = {'payment_status': 'paid'}
        if payment_intent_id:
            updates['stripe_payment_intent_id'] = str(payment_intent_id)[:255]
        if session_id:
            updates['payment_session_id'] = str(session_id)[:255]
        if subscription_id:
            updates['stripe_subscription_id'] = str(subscription_id)[:255]
        if customer_id:
            updates['stripe_customer_id'] = str(customer_id)[:255]
        if row.status in ('unpaid', 'draft'):
            updates['status'] = 'pending'
        elif row.status == 'suspended' and row.payment_status == 'canceled':
            updates['status'] = 'pending'
        s.query(UserListing).filter(UserListing.id == lid).update(updates, synchronize_session=False)
        return lid


def mark_listing_paid_by_session(session_id, payment_intent_id=None, subscription_id=None, customer_id=None):
    """Stripe webhook: mark the listing paid and move it to 'pending' review.

    Returns the listing_id, or None if no listing matches the checkout session.
    """
    if not session_id:
        return None
    with get_session() as s:
        row = s.query(UserListing).filter(UserListing.payment_session_id == session_id).first()
        listing_id = int(row.id) if row else None  # type: ignore[arg-type]
    if not listing_id:
        return None
    return mark_listing_fee_paid(listing_id, payment_intent_id, session_id, subscription_id, customer_id)


def find_listing_by_subscription(subscription_id):
    """The listing whose monthly fee is this Stripe subscription."""
    if not subscription_id:
        return None
    with get_session() as s:
        row = s.query(UserListing).filter(
            UserListing.stripe_subscription_id == str(subscription_id)[:255]
        ).first()
        return row.to_dict() if row else None


def listing_stripe_customer(user_id):
    """Stripe customer from a listing fee, so later Checkout and the portal reuse it."""
    with get_session() as s:
        row = (
            s.query(UserListing.stripe_customer_id)
            .filter(UserListing.user_id == int(user_id), UserListing.stripe_customer_id.isnot(None))
            .order_by(UserListing.id.desc())
            .first()
        )
        return row[0] if row and row[0] else None


def listing_subscription_ids(user_id):
    """Listing-fee subscriptions to cancel when the account is deleted."""
    with get_session() as s:
        rows = (
            s.query(UserListing.stripe_subscription_id)
            .filter(UserListing.user_id == int(user_id), UserListing.stripe_subscription_id.isnot(None))
            .all()
        )
        return [row[0] for row in rows if row[0]]


def end_listing_subscription(listing_id):
    """Take a listing off the public page when its monthly fee ends.

    An already-approved listing is suspended. A listing still in review keeps
    its place in the queue but is no longer marked paid. Returns True when
    the row changed.
    """
    if not listing_id:
        return False
    with get_session() as s:
        row = s.query(UserListing).filter(UserListing.id == int(listing_id)).first()
        if not row or row.payment_status == 'canceled':
            return False
        updates = {'payment_status': 'canceled'}
        if row.status == 'active':
            updates['status'] = 'suspended'
        elif row.status == 'pending':
            updates['status'] = 'unpaid'
        s.query(UserListing).filter(UserListing.id == row.id).update(updates, synchronize_session=False)
        return True


def reconcile_listing_refund(payment_intent_id, payment_status):
    """Record a refund Stripe has already settled. Listing visibility stays as it is.

    Returns the listing id, or None when there is no matching paid listing.
    Does not create a Stripe refund and does not decide that a refund is owed.
    """
    if not payment_intent_id or payment_status not in (
        'refunded', 'partially_refunded', 'refund_recorded', 'disputed', 'fraud_review', 'paid',
    ):
        return None
    with get_session() as s:
        row = (
            s.query(UserListing)
            .filter(UserListing.stripe_payment_intent_id == str(payment_intent_id)[:255])
            .first()
        )
        if not row:
            return None
        lid = int(row.id)  # type: ignore[arg-type]
        current = row.payment_status
        if payment_status == 'paid':
            if current != 'disputed':
                return None
        elif payment_status in ('disputed', 'fraud_review'):
            if current not in ('paid', 'partially_refunded', 'refund_recorded', 'disputed', 'fraud_review'):
                return None
        elif current not in ('paid', 'partially_refunded', 'refund_recorded', 'refunded', 'disputed', 'fraud_review'):
            return None
        if current == 'refunded':
            return lid
        if current == 'partially_refunded' and payment_status == 'refund_recorded':
            return lid
        if current == payment_status:
            return lid
        s.query(UserListing).filter(UserListing.id == lid).update(
            {'payment_status': payment_status}, synchronize_session=False
        )
        return lid


def consume_auth_rate(bucket_key: str, limit: int = 10, window_seconds: int = 60) -> bool:
    """True when this key is over the shared limit. The hit is stored for every worker."""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)
    with get_session() as s:
        s.query(AuthRateHit).filter(AuthRateHit.created_at < now - timedelta(hours=6)).delete(
            synchronize_session=False
        )
        count = (
            s.query(AuthRateHit)
            .filter(AuthRateHit.bucket_key == bucket_key, AuthRateHit.created_at >= cutoff)
            .count()
        )
        if count >= limit:
            return True
        s.add(AuthRateHit(bucket_key=bucket_key, created_at=now))
        return False


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
        q = s.query(UserListing).filter(UserListing.status == 'active', _public_market_clause())
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


# --- Ownership-aware listing helpers (used by /api/listings/<id>) ---
def get_listing_with_owner(listing_id):
    """Return listing dict (any status) or None. Caller must check ownership."""
    with get_session() as s:
        row = s.query(UserListing).filter(UserListing.id == listing_id).first()
        return row.to_dict() if row else None


def normalize_listing_fields(fields):
    """Whitelisted listing columns from a form or JSON body. Never includes ownership or status."""
    allowed = {
        'title', 'year', 'price', 'hours', 'location', 'email', 'description',
        'images', 'documents', 'engine_type', 'manufacturer', 'pricing_plan', 'market',
        'serial_number', 'registration', 'variant', 'engine_program', 'engine_hours',
        'engine_cycles', 'maintenance_status', 'avionics', 'paint_year', 'interior_year',
        'passenger_config', 'city', 'state', 'profile_id', 'listing_intent',
    }
    safe = {k: v for k, v in (fields or {}).items() if k in allowed}
    if 'market' in safe:
        safe['market'] = _stored_market(safe['market'])
    if 'listing_intent' in safe:
        intent = str(safe.get('listing_intent') or '').strip().lower()
        if intent in ('sale', 'wanted'):
            safe['listing_intent'] = intent
        else:
            safe.pop('listing_intent', None)
    if 'profile_id' in safe:
        try:
            safe['profile_id'] = int(safe['profile_id'])
        except (TypeError, ValueError):
            safe.pop('profile_id', None)
    for key in ('engine_hours', 'engine_cycles', 'paint_year', 'interior_year', 'year', 'hours'):
        if key in safe and safe[key] not in (None, ''):
            try:
                safe[key] = int(safe[key])
            except (TypeError, ValueError):
                safe.pop(key, None)
    if 'price' in safe and safe['price'] not in (None, ''):
        try:
            safe['price'] = float(safe['price'])
        except (TypeError, ValueError):
            safe.pop('price', None)
    return safe


def update_user_listing_fields(listing_id, fields):
    """Update an existing listing with a whitelisted set of fields. Returns True if updated.

    Only allowed columns can be patched. user_id can never be overwritten via this path.
    """
    safe = normalize_listing_fields(fields)
    if not safe:
        return False
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(safe, synchronize_session=False)
        return n > 0


def parse_listing_pending(raw):
    """Return the staged update for an approved listing, or None when there is nothing waiting."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    fields = data.get('fields') if isinstance(data.get('fields'), dict) else {}

    def _ids(key):
        found = []
        for item in data.get(key) or []:
            try:
                found.append(int(item))
            except (TypeError, ValueError):
                continue
        return found

    media_add = _ids('media_add')
    media_remove = _ids('media_remove')
    if not fields and not media_add and not media_remove:
        return None
    return {'fields': fields, 'media_add': media_add, 'media_remove': media_remove}


def set_listing_pending_changes(listing_id, pending):
    """Store a staged update, or clear it. Clearing also clears the amendment note."""
    raw = None
    if pending:
        fields = pending.get('fields') or {}
        media_add = []
        media_remove = []
        for item in pending.get('media_add') or []:
            try:
                media_add.append(int(item))
            except (TypeError, ValueError):
                continue
        for item in pending.get('media_remove') or []:
            try:
                media_remove.append(int(item))
            except (TypeError, ValueError):
                continue
        if fields or media_add or media_remove:
            raw = json.dumps({'fields': fields, 'media_add': media_add, 'media_remove': media_remove})
    values = {'pending_changes': raw}
    if raw is None:
        values['amendment_note'] = None
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(values, synchronize_session=False)
        return n > 0


def archive_user_listing(listing_id):
    """Soft-archive a listing (status=archived). Returns True if updated."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(
            {'status': 'archived'}, synchronize_session=False
        )
        return n > 0


def admin_list_user_listings(status=None, limit=500):
    """Admin: list all listings, optionally filtered by status."""
    with get_session() as s:
        q = s.query(UserListing)
        if status == 'pending':
            q = q.filter(or_(
                UserListing.status.in_(('pending', 'unpaid')),
                UserListing.pending_changes.isnot(None),
            ))
        elif status:
            q = q.filter(UserListing.status == status)
        rows = q.order_by(UserListing.created_at.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]


def record_listing_audit(listing_id, actor_id, action, previous_status, new_status, notes=None):
    with get_session() as s:
        row = ListingAudit(
            listing_id=listing_id,
            actor_id=actor_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            notes=notes,
        )
        s.add(row)
        s.flush()
        return row.id


def list_listing_audits(listing_id, limit=50):
    with get_session() as s:
        rows = (
            s.query(ListingAudit)
            .filter(ListingAudit.listing_id == listing_id)
            .order_by(ListingAudit.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for row in rows:
            item = row.to_dict()
            if item.get('created_at') is not None:
                item['created_at'] = str(item['created_at'])
            out.append(item)
        return out


def claim_stripe_event(event_id: str) -> bool:
    """True the first time this Stripe event id is seen."""
    if not event_id:
        return True
    from sqlalchemy.exc import IntegrityError
    try:
        with get_session() as s:
            s.add(StripeEvent(event_id=event_id))
            s.flush()
            return True
    except IntegrityError:
        return False


def set_broker_verified(user_id, verified: bool) -> bool:
    with get_session() as s:
        n = s.query(User).filter(User.id == user_id).update(
            {'broker_verified': bool(verified)}, synchronize_session=False
        )
        return n > 0


def set_listing_review_message(listing_id, message: str, keep_status: bool = False) -> bool:
    values = {'review_message': message}
    if not keep_status:
        values['status'] = 'pending'
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(values, synchronize_session=False)
        return n > 0


def set_listing_amendment(listing_id, note: str) -> bool:
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(
            {'amendment_note': note, 'review_message': None}, synchronize_session=False
        )
        return n > 0


def set_listing_admin_notes(listing_id, notes: str) -> bool:
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update(
            {'admin_notes': notes}, synchronize_session=False
        )
        return n > 0


def list_directory_brokers():
    """Accounts that chose the broker role, with public profile fields only."""
    with get_session() as s:
        rows = (
            s.query(User)
            .filter(User.is_suspended == False)  # noqa: E712
            .order_by(User.company.asc(), User.last_name.asc())
            .all()
        )
        out = []
        for user in rows:
            roles = {(user.profile_role or '').lower()}
            roles.update(part.strip().lower() for part in (user.roles or '').split(',') if part.strip())
            if 'broker' not in roles:
                continue
            out.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'company': user.company,
                'phone': user.phone,
                'email': user.email,
                'profile_location': user.profile_location,
                'broker_bio': user.broker_bio,
                'broker_specialties': user.broker_specialties,
                'broker_website': user.broker_website,
                'broker_years': user.broker_years,
                'broker_verified': bool(user.broker_verified),
                'broker_state': user.broker_state,
                'broker_country': user.broker_country,
                'broker_lat': user.broker_lat,
                'broker_lon': user.broker_lon,
                'broker_image_url': user.broker_image_url,
                'profile_photo_url': user.profile_photo_url,
                'company_logo_url': user.company_logo_url,
            })
        return out


def _team_place(city, state):
    city = (city or '').strip()
    state = (state or '').strip()
    if city and state:
        return f'{city}, {state}'
    return city or state or ''


def create_broker_team(admin_user_id, name, city, state, latitude=None, longitude=None, logo_url=None, active=False):
    """Create a company. It appears on the map only after the team subscription is active."""
    with get_session() as s:
        row = BrokerTeam(
            name=(name or '').strip(),
            admin_user_id=admin_user_id,
            city=(city or '').strip() or None,
            state=(state or '').strip() or None,
            location=_team_place(city, state) or None,
            latitude=latitude,
            longitude=longitude,
            logo_url=logo_url,
            subscription_status='active' if active else 'inactive',
        )
        s.add(row)
        s.flush()
        member = BrokerTeamMember(team_id=row.id, user_id=admin_user_id, status='active' if active else 'pending')
        s.add(member)
        return row.id


def set_team_subscription(team_id, status):
    with get_session() as s:
        team = s.query(BrokerTeam).filter(BrokerTeam.id == team_id).first()
        if not team:
            return False
        team.subscription_status = status
        if status == 'active':
            member = s.query(BrokerTeamMember).filter(
                BrokerTeamMember.team_id == team_id,
                BrokerTeamMember.user_id == team.admin_user_id,
            ).first()
            if member:
                member.status = 'active'
            else:
                s.add(BrokerTeamMember(team_id=team_id, user_id=team.admin_user_id, status='active'))
        return True


def list_public_teams():
    with get_session() as s:
        rows = (
            s.query(BrokerTeam)
            .filter(BrokerTeam.subscription_status == 'active')
            .order_by(BrokerTeam.name.asc())
            .all()
        )
        return [row.to_dict() for row in rows]


def get_broker_team(team_id):
    with get_session() as s:
        row = s.query(BrokerTeam).filter(BrokerTeam.id == team_id).first()
        return row.to_dict() if row else None


def user_on_active_team(user_id):
    """True when this person is an approved member of a paid team."""
    with get_session() as s:
        row = (
            s.query(BrokerTeamMember, BrokerTeam)
            .join(BrokerTeam, BrokerTeam.id == BrokerTeamMember.team_id)
            .filter(
                BrokerTeamMember.user_id == user_id,
                BrokerTeamMember.status == 'active',
                BrokerTeam.subscription_status == 'active',
            )
            .first()
        )
        if not row:
            return None
        member, team = row
        data = team.to_dict()
        data['membership_status'] = member.status
        return data


def team_membership(user_id):
    with get_session() as s:
        row = (
            s.query(BrokerTeamMember, BrokerTeam)
            .join(BrokerTeam, BrokerTeam.id == BrokerTeamMember.team_id)
            .filter(BrokerTeamMember.user_id == user_id)
            .order_by(BrokerTeamMember.id.desc())
            .first()
        )
        if not row:
            return None
        member, team = row
        data = team.to_dict()
        data['membership_status'] = member.status
        data['is_admin'] = team.admin_user_id == user_id
        return data


def request_team_join(team_id, user_id):
    with get_session() as s:
        team = s.query(BrokerTeam).filter(BrokerTeam.id == team_id, BrokerTeam.subscription_status == 'active').first()
        if not team:
            return None
        existing = s.query(BrokerTeamMember).filter(
            BrokerTeamMember.team_id == team_id,
            BrokerTeamMember.user_id == user_id,
        ).first()
        if existing:
            return existing.status
        s.add(BrokerTeamMember(team_id=team_id, user_id=user_id, status='pending'))
        return 'pending'


BROKERAGE_CATEGORIES = ('Sales', 'Acquisition', 'Management', 'Charter', 'Service')


def set_broker_application(user_id, status):
    with get_session() as s:
        n = s.query(User).filter(User.id == user_id).update(
            {'broker_application_status': status}, synchronize_session=False
        )
        return n > 0


def list_broker_applications(status='pending'):
    with get_session() as s:
        rows = (
            s.query(User)
            .filter(User.broker_application_status == status)
            .order_by(User.created_at.desc())
            .all()
        )
        return [{
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'company': user.company,
            'phone': user.phone,
            'profile_role': user.profile_role,
            'profile_location': user.profile_location,
            'status': user.broker_application_status,
        } for user in rows]


def list_teams_for_admin():
    with get_session() as s:
        teams = s.query(BrokerTeam).order_by(BrokerTeam.name.asc()).all()
        out = []
        for team in teams:
            leader = s.query(User).filter(User.id == team.admin_user_id).first()
            out.append({
                'id': team.id,
                'name': team.name,
                'city': team.city,
                'state': team.state,
                'location': team.location,
                'category': team.category,
                'subscription_status': team.subscription_status,
                'leader': {
                    'id': leader.id,
                    'name': ' '.join(part for part in [leader.first_name, leader.last_name] if part) or leader.email,
                    'email': leader.email,
                } if leader else None,
            })
    for team in out:
        team['members'] = list_team_members(team['id'])
    return out


def list_pending_memberships():
    with get_session() as s:
        rows = (
            s.query(BrokerTeamMember, BrokerTeam, User)
            .join(BrokerTeam, BrokerTeam.id == BrokerTeamMember.team_id)
            .join(User, User.id == BrokerTeamMember.user_id)
            .filter(BrokerTeamMember.status == 'pending')
            .all()
        )
        return [{
            'team_id': team.id,
            'team_name': team.name,
            'user_id': user.id,
            'name': ' '.join(part for part in [user.first_name, user.last_name] if part) or user.email,
            'email': user.email,
        } for _member, team, user in rows]


def set_team_category(team_id, category):
    category = (category or '').strip()
    if category and category not in BROKERAGE_CATEGORIES:
        return False
    with get_session() as s:
        n = s.query(BrokerTeam).filter(BrokerTeam.id == team_id).update(
            {'category': category or None}, synchronize_session=False
        )
        return n > 0


def set_team_leader(team_id, user_id):
    with get_session() as s:
        team = s.query(BrokerTeam).filter(BrokerTeam.id == team_id).first()
        member = s.query(BrokerTeamMember).filter(
            BrokerTeamMember.team_id == team_id,
            BrokerTeamMember.user_id == user_id,
        ).first()
        if not team or not member:
            return False
        team.admin_user_id = user_id
        member.status = 'active'
        return True


def admin_allow_team_member(team_id, member_user_id):
    with get_session() as s:
        member = s.query(BrokerTeamMember).filter(
            BrokerTeamMember.team_id == team_id,
            BrokerTeamMember.user_id == member_user_id,
        ).first()
        if not member:
            return False
        member.status = 'active'
        return True


def allow_team_member(team_id, admin_user_id, member_user_id):
    with get_session() as s:
        team = s.query(BrokerTeam).filter(BrokerTeam.id == team_id, BrokerTeam.admin_user_id == admin_user_id).first()
        if not team:
            return False
        member = s.query(BrokerTeamMember).filter(
            BrokerTeamMember.team_id == team_id,
            BrokerTeamMember.user_id == member_user_id,
        ).first()
        if not member:
            return False
        member.status = 'active'
        return True


def list_team_members(team_id, status=None):
    with get_session() as s:
        q = (
            s.query(BrokerTeamMember, User)
            .join(User, User.id == BrokerTeamMember.user_id)
            .filter(BrokerTeamMember.team_id == team_id)
        )
        if status:
            q = q.filter(BrokerTeamMember.status == status)
        out = []
        for member, user in q.all():
            out.append({
                'user_id': user.id,
                'status': member.status,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'company': user.company,
                'email': user.email,
                'phone': user.phone,
                'profile_photo_url': user.profile_photo_url,
                'broker_specialties': user.broker_specialties,
                'broker_bio': user.broker_bio,
                'is_admin': user.id == s.query(BrokerTeam.admin_user_id).filter(BrokerTeam.id == team_id).scalar(),
            })
        return out


def create_contact_message(name, email, phone, message):
    with get_session() as s:
        row = ContactMessage(name=name, email=email, phone=phone or None, message=message)
        s.add(row)
        s.flush()
        return row.id


def list_contact_messages(limit=100):
    with get_session() as s:
        rows = (
            s.query(ContactMessage)
            .order_by(ContactMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [row.to_dict() for row in rows]


def list_admin_user_ids():
    with get_session() as s:
        return [int(user.id) for user in s.query(User).filter(User.is_admin.is_(True)).all()]


def create_notification(user_id, kind, title, body=None, href=None):
    with get_session() as s:
        row = UserNotification(user_id=user_id, kind=kind, title=title, body=body, href=href)
        s.add(row)
        s.flush()
        return row.id


def list_notifications(user_id, limit=40):
    with get_session() as s:
        rows = (
            s.query(UserNotification)
            .filter(UserNotification.user_id == user_id)
            .order_by(UserNotification.created_at.desc())
            .limit(limit)
            .all()
        )
        return [row.to_dict() for row in rows]


def unread_notification_count(user_id):
    with get_session() as s:
        return s.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        ).count()


def mark_notifications_read(user_id):
    with get_session() as s:
        s.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        ).update({'read_at': datetime.utcnow()}, synchronize_session=False)
        return True


def delete_notification(user_id, notification_id):
    """Remove one alert from this account."""
    with get_session() as s:
        row = s.query(UserNotification).filter(
            UserNotification.id == int(notification_id),
            UserNotification.user_id == int(user_id),
        ).first()
        if not row:
            return False
        s.delete(row)
        return True


def delete_notifications(user_id):
    """Remove every alert from this account."""
    with get_session() as s:
        s.query(UserNotification).filter(UserNotification.user_id == int(user_id)).delete(synchronize_session=False)
        return True


def _send_notice_email(email, title, body):
    if not email:
        return False
    try:
        import email_service
        if not email_service.is_configured():
            return False
        text = f'{title}\n\n{body or ""}'
        return bool(email_service.send_email(email, title, f'<p>{text.replace(chr(10), "<br>")}</p>', text))
    except Exception:
        return False


def list_approved_brokers():
    """Approved brokers for the map and for buyer or seller messages."""
    with get_session() as s:
        rows = (
            s.query(User)
            .filter(User.broker_application_status == 'approved')
            .order_by(User.first_name.asc(), User.last_name.asc())
            .all()
        )
        out = []
        for user in rows:
            name = ' '.join(part for part in [user.first_name, user.last_name] if part) or 'Broker'
            out.append({
                'id': int(user.id),
                'name': name,
                'company': user.company or '',
                'place': user.profile_location or '',
                'photo': user.profile_photo_url or '',
                'bio': (user.broker_bio or '')[:1000],
                'lat': user.broker_lat,
                'lon': user.broker_lon,
            })
        return out


def create_broker_message(from_user_id, to_user_id, kind, notes='', aircraft_name='', listing_id=None, contact_email='', contact_phone=''):
    kind = (kind or '').strip().lower()
    if kind not in ('request', 'listing', 'message'):
        raise ValueError('invalid_kind')
    notes = (notes or '').strip()[:2000]
    aircraft_name = (aircraft_name or '').strip()[:200]
    if kind == 'request' and not aircraft_name:
        raise ValueError('aircraft_required')
    if kind == 'message' and not notes:
        raise ValueError('notes_required')
    if kind == 'listing' and not listing_id:
        raise ValueError('listing_required')
    with get_session() as s:
        row = BrokerMessage(
            from_user_id=int(from_user_id),
            to_user_id=int(to_user_id),
            listing_id=int(listing_id) if listing_id else None,
            kind=kind,
            aircraft_name=aircraft_name or None,
            notes=notes or None,
            contact_email=(contact_email or '').strip()[:254] or None,
            contact_phone=(contact_phone or '').strip()[:40] or None,
        )
        s.add(row)
        s.flush()
        return int(row.id)


def list_broker_messages(user_id, box='in'):
    with get_session() as s:
        column = BrokerMessage.to_user_id if box == 'in' else BrokerMessage.from_user_id
        hidden = BrokerMessage.recipient_hidden if box == 'in' else BrokerMessage.sender_hidden
        rows = (
            s.query(BrokerMessage)
            .filter(column == int(user_id), or_(hidden.is_(False), hidden.is_(None)))
            .order_by(BrokerMessage.created_at.desc(), BrokerMessage.id.desc())
            .limit(100)
            .all()
        )
        out = []
        for row in rows:
            other_id = row.from_user_id if box == 'in' else row.to_user_id
            other = s.query(User).filter(User.id == other_id).first()
            other_name = ' '.join(part for part in [getattr(other, 'first_name', None), getattr(other, 'last_name', None)] if part) if other else 'Member'
            out.append({
                'id': int(row.id),
                'kind': row.kind,
                'aircraft_name': row.aircraft_name or '',
                'notes': row.notes or '',
                'contact_email': row.contact_email or '',
                'contact_phone': row.contact_phone or '',
                'listing_id': row.listing_id,
                'from_user_id': int(row.from_user_id),
                'to_user_id': int(row.to_user_id),
                'person_name': other_name or 'Member',
                'created_at': str(row.created_at) if row.created_at else None,
            })
        return out


def hide_broker_message(user_id, message_id):
    """Hide one broker message from this account. The other person still has it."""
    with get_session() as s:
        row = s.query(BrokerMessage).filter(BrokerMessage.id == int(message_id)).first()
        if not row:
            return False
        uid = int(user_id)
        if int(row.from_user_id) == uid:
            row.sender_hidden = True
        elif int(row.to_user_id) == uid:
            row.recipient_hidden = True
        else:
            return False
        if row.sender_hidden and row.recipient_hidden:
            s.delete(row)
        return True


def hide_broker_messages(user_id):
    """Hide every broker message this account sent or received."""
    uid = int(user_id)
    with get_session() as s:
        rows = s.query(BrokerMessage).filter(
            or_(BrokerMessage.from_user_id == uid, BrokerMessage.to_user_id == uid)
        ).all()
        for row in rows:
            if int(row.from_user_id) == uid:
                row.sender_hidden = True
            if int(row.to_user_id) == uid:
                row.recipient_hidden = True
            if row.sender_hidden and row.recipient_hidden:
                s.delete(row)
        return True


def notify_user(user_id, kind, title, body=None, href=None, email=None):
    create_notification(user_id, kind, title, body, href)
    _send_notice_email(email, title, body)


def note_listing_watched(watcher_id, listing_id):
    try:
        listing_id = int(listing_id)
    except (TypeError, ValueError):
        return
    listing = get_listing_with_owner(listing_id)
    if not listing:
        return
    owner_id = listing.get('user_id')
    if not owner_id or int(owner_id) == int(watcher_id):
        return
    title = listing.get('title') or 'Your listing'
    notify_user(
        owner_id,
        'watch',
        'Someone is watching your listing',
        f'{title} was added to a watchlist.',
        f'/people/{owner_id}',
        listing.get('email'),
    )


def notify_watchers_of_listing(listing):
    """Tell people watching this model that a listing is on the market."""
    profile_id = str(listing.get('profile_id') or '').strip()
    if not profile_id:
        return
    title = listing.get('title') or 'An aircraft'
    owner_id = listing.get('user_id')
    with get_session() as s:
        rows = (
            s.query(SavedAircraft)
            .filter(SavedAircraft.kind == 'catalog', SavedAircraft.target_id == profile_id)
            .all()
        )
        watchers = [(row.user_id,) for row in rows]
    seen = set()
    for (user_id,) in watchers:
        if user_id in seen or user_id == owner_id:
            continue
        seen.add(user_id)
        person = get_user_by_id(user_id)
        if not person:
            continue
        notify_user(
            user_id,
            'listing',
            'A plane you are watching is for sale',
            f'{title} is on the marketplace.',
            '/',
            person.get('email'),
        )


def listings_for_user(user_id, include_off_market=False):
    with get_session() as s:
        rows = (
            s.query(UserListing)
            .filter(UserListing.user_id == user_id, UserListing.status == 'active')
            .order_by(UserListing.created_at.desc())
            .all()
        )
        out = []
        for row in rows:
            market = (row.market or 'public').lower()
            if market in ('private',):
                continue
            if market in ('off_market', 'broker_only') and not include_off_market:
                continue
            city = row.city or ''
            state = row.state or ''
            place = _team_place(city, state) or row.location or ''
            if place and len(place) <= 4 and place.isalpha():
                place = _team_place(city, state)
            out.append({
                'id': row.id,
                'title': row.title,
                'price': row.price,
                'city': city,
                'state': state,
                'place': place,
                'serial_number': row.serial_number or '',
                'year': row.year,
                'engine_type': row.engine_type or '',
                'manufacturer': row.manufacturer or '',
                'market': market,
            })
        return out


def ensure_charter_operator(user_id, company_name, phone=None, email=None):
    with get_session() as s:
        row = s.query(CharterOperator).filter(CharterOperator.user_id == user_id).first()
        if row:
            return row.id
        row = CharterOperator(
            user_id=user_id,
            company_name=company_name or 'Charter operator',
            phone=phone,
            email=email,
            status='active',
        )
        s.add(row)
        s.flush()
        return row.id


def get_charter_operator_for_user(user_id):
    with get_session() as s:
        row = s.query(CharterOperator).filter(CharterOperator.user_id == user_id).first()
        return row.to_dict() if row else None


def create_charter_aircraft(operator_id, data):
    with get_session() as s:
        row = CharterAircraft(
            operator_id=operator_id,
            profile_id=data.get('profile_id'),
            name=data['name'],
            registration=data.get('registration'),
            base_airport=(data.get('base_airport') or '').upper() or None,
            seats=data.get('seats'),
            hourly_rate=data.get('hourly_rate'),
            range_nm=data.get('range_nm'),
            speed_kts=data.get('speed_kts'),
            notes=data.get('notes'),
            status='active',
        )
        s.add(row)
        s.flush()
        return row.id


def list_charter_aircraft(operator_id=None, active_only=True):
    with get_session() as s:
        q = s.query(CharterAircraft)
        if operator_id is not None:
            q = q.filter(CharterAircraft.operator_id == operator_id)
        if active_only:
            q = q.filter(CharterAircraft.status == 'active')
        return [row.to_dict() for row in q.order_by(CharterAircraft.name.asc()).all()]


def get_charter_aircraft(aircraft_id):
    with get_session() as s:
        row = s.query(CharterAircraft).filter(CharterAircraft.id == aircraft_id).first()
        return row.to_dict() if row else None


def add_charter_block(aircraft_id, start_date, end_date, reason=None):
    with get_session() as s:
        row = CharterBlock(
            aircraft_id=aircraft_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )
        s.add(row)
        s.flush()
        return row.id


def charter_aircraft_blocked(aircraft_id, on_date: str) -> bool:
    if not on_date:
        return False
    with get_session() as s:
        rows = s.query(CharterBlock).filter(CharterBlock.aircraft_id == aircraft_id).all()
        for row in rows:
            if row.start_date <= on_date <= row.end_date:
                return True
        return False


def create_charter_booking(data):
    with get_session() as s:
        row = CharterBooking(
            aircraft_id=data['aircraft_id'],
            user_id=data.get('user_id'),
            contact_name=data['contact_name'],
            contact_email=data['contact_email'],
            contact_phone=data.get('contact_phone'),
            departure_airport=data['departure_airport'],
            arrival_airport=data['arrival_airport'],
            departure_date=data.get('departure_date'),
            passengers=int(data.get('passengers') or 1),
            estimated_price=data.get('estimated_price'),
            notes=data.get('notes'),
            status='requested',
        )
        s.add(row)
        s.flush()
        return row.id


def list_charter_bookings(user_id=None, operator_id=None):
    with get_session() as s:
        q = s.query(CharterBooking)
        if user_id is not None:
            q = q.filter(CharterBooking.user_id == user_id)
        if operator_id is not None:
            aircraft_ids = [
                row.id for row in s.query(CharterAircraft).filter(CharterAircraft.operator_id == operator_id).all()
            ]
            if not aircraft_ids:
                return []
            q = q.filter(CharterBooking.aircraft_id.in_(aircraft_ids))
        rows = q.order_by(CharterBooking.created_at.desc()).all()
        out = []
        for row in rows:
            item = row.to_dict()
            for key in ('created_at', 'updated_at'):
                if item.get(key) is not None:
                    item[key] = str(item[key])
            out.append(item)
        return out


def get_charter_booking(booking_id):
    with get_session() as s:
        row = s.query(CharterBooking).filter(CharterBooking.id == booking_id).first()
        return row.to_dict() if row else None


def set_charter_booking_status(booking_id, status):
    allowed = {
        'requested', 'pending_operator_confirmation', 'confirmed',
        'payment_pending', 'paid', 'cancelled', 'completed',
    }
    if status not in allowed:
        return False
    with get_session() as s:
        n = s.query(CharterBooking).filter(CharterBooking.id == booking_id).update(
            {'status': status}, synchronize_session=False
        )
        return n > 0


def admin_approve_listing_any(listing_id, approved_by_user_id):
    """Admin approve from ANY current status (pending, unpaid, draft). Sets status=active."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update({
            'status': 'active',
            'approved_by': approved_by_user_id,
            'approved_at': datetime.utcnow(),
            'rejection_reason': None,
            'amendment_note': None,
            'review_message': None,
        }, synchronize_session=False)
        return n > 0


def admin_reject_listing_any(listing_id, rejection_reason):
    """Admin reject from ANY current status. Records reason."""
    with get_session() as s:
        n = s.query(UserListing).filter(UserListing.id == listing_id).update({
            'status': 'rejected',
            'rejection_reason': rejection_reason or 'No reason provided',
        }, synchronize_session=False)
        return n > 0


# --- Listing media helpers (Cloudflare R2 backed) ---
def add_listing_media(listing_id: int, media_type: str, r2_object_key: str, url: str,
                      *, thumbnail_url: str | None = None, content_type: str | None = None,
                      size_bytes: int | None = None, sort_order: int = 0, published: bool = True) -> int:
    """Insert a listing_media row. Bytes themselves are in R2; we only store metadata."""
    with get_session() as s:
        row = ListingMedia(
            listing_id=listing_id,
            media_type=(media_type or 'photo').lower(),
            r2_object_key=r2_object_key,
            url=url,
            thumbnail_url=thumbnail_url,
            content_type=content_type,
            size_bytes=size_bytes,
            sort_order=sort_order,
            published=bool(published),
        )
        s.add(row)
        s.flush()
        return int(row.id)  # type: ignore[arg-type]


def list_listing_media(listing_id: int, include_unpublished: bool = False) -> list[dict]:
    """Return ordered media metadata for a listing (used by display endpoints)."""
    with get_session() as s:
        query = s.query(ListingMedia).filter(ListingMedia.listing_id == listing_id)
        if not include_unpublished:
            query = query.filter(or_(ListingMedia.published.is_(True), ListingMedia.published.is_(None)))
        rows = query.order_by(ListingMedia.sort_order.asc(), ListingMedia.id.asc()).all()
        return [r.to_dict() for r in rows]


def list_media_for_listings(listing_ids: list[int], include_unpublished: bool = False) -> dict[int, list[dict]]:
    """Batch lookup: return {listing_id: [media_dict, ...]} for many listings (avoid N+1)."""
    if not listing_ids:
        return {}
    with get_session() as s:
        query = s.query(ListingMedia).filter(ListingMedia.listing_id.in_(listing_ids))
        if not include_unpublished:
            query = query.filter(or_(ListingMedia.published.is_(True), ListingMedia.published.is_(None)))
        rows = query.order_by(ListingMedia.sort_order.asc(), ListingMedia.id.asc()).all()
        out: dict[int, list[dict]] = {}
        for r in rows:
            out.setdefault(int(r.listing_id), []).append(r.to_dict())  # type: ignore[arg-type]
        return out


def get_listing_media_row(media_id: int) -> dict | None:
    with get_session() as s:
        row = s.query(ListingMedia).filter(ListingMedia.id == media_id).first()
        return row.to_dict() if row else None


def set_listing_media_published(media_id: int, published: bool = True) -> bool:
    with get_session() as s:
        n = s.query(ListingMedia).filter(ListingMedia.id == media_id).update(
            {'published': bool(published)}, synchronize_session=False
        )
        return n > 0


def delete_listing_media_row(media_id: int) -> bool:
    """Delete a single media row by id. Caller is responsible for deleting the R2 object."""
    with get_session() as s:
        n = s.query(ListingMedia).filter(ListingMedia.id == media_id).delete()
        return n > 0


def count_listing_media(listing_id: int, media_type: str | None = None) -> int:
    """Count media items for a listing, optionally filtered by media_type (photo/video)."""
    with get_session() as s:
        q = s.query(ListingMedia).filter(ListingMedia.listing_id == listing_id)
        if media_type:
            q = q.filter(ListingMedia.media_type == media_type)
        return int(q.count() or 0)


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


def find_subscription_by_stripe_id(subscription_id):
    """The local broker subscription row for a Stripe subscription id."""
    if not subscription_id:
        return None
    with get_session() as s:
        row = (
            s.query(UserSubscription)
            .filter(UserSubscription.stripe_subscription_id == str(subscription_id)[:255])
            .order_by(UserSubscription.id.desc())
            .first()
        )
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
        lat = provider_data.get('latitude')
        lon = provider_data.get('longitude')
        try:
            lat = float(lat) if lat not in (None, '') else None
            lon = float(lon) if lon not in (None, '') else None
        except (TypeError, ValueError):
            lat = lon = None
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
    """Wipe the performance_profiles cache table.

    This table is a *cache* derived from aircraft CSV — no user data lives here.
    Even so, it's a bulk DELETE so it goes through assert_not_production() to
    prevent accidental bulk operations in prod without explicit override.
    """
    assert_not_production('clear_performance_profiles (DELETE FROM performance_profiles)')
    with get_session() as s:
        s.query(PerformanceProfile).delete()
    return True


def wipe_all_user_sessions_DANGEROUS():  # noqa: N802 - intentional SHOUT name
    """Force-logout every user by deleting all session rows.

    Use only after a credential leak. Production requires explicit override.
    """
    assert_not_production('wipe_all_user_sessions (DELETE FROM user_sessions)')
    with get_session() as s:
        s.query(UserSession).delete()
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
