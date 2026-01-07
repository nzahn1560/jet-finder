from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional

from sqlmodel import Field, Relationship, SQLModel


class ListingStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class User(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    force_password_reset: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    listings: list[Listing] = Relationship(back_populates="owner")


class PerformanceProfile(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    manufacturer: str
    engine_type: str
    range_nm: int
    cruise_speed_knots: int
    max_passengers: int
    max_altitude_ft: int
    cabin_volume_cuft: Optional[float] = None
    baggage_volume_cuft: Optional[float] = None
    runway_requirement_ft: Optional[int] = None
    hourly_cost_usd: Optional[float] = None
    annual_maintenance_usd: Optional[float] = None
    purchase_price_usd: Optional[float] = None
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    listings: list[Listing] = Relationship(back_populates="performance_profile")


class PricingPlan(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    price_usd: int
    billing_cycle_months: int
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    listings: list[Listing] = Relationship(back_populates="pricing_plan")


class Listing(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    price_usd: int
    location: str
    engine_type: str
    contact_email: str
    status: ListingStatus = Field(default=ListingStatus.PENDING)
    payment_plan: str = Field(default="monthly")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None

    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    performance_profile_id: Optional[int] = Field(
        default=None, foreign_key="performance_profiles.id"
    )
    pricing_plan_id: Optional[int] = Field(default=None, foreign_key="pricing_plans.id")

    owner: Optional[User] = Relationship(back_populates="listings")
    performance_profile: Optional[PerformanceProfile] = Relationship(
        back_populates="listings"
    )
    pricing_plan: Optional[PricingPlan] = Relationship(back_populates="listings")

