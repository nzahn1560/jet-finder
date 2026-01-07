from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.entities import ListingStatus


class PerformanceProfileRead(BaseModel):
    id: int
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

    class Config:
        from_attributes = True


class ListingBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_usd: int = Field(ge=0)
    location: str
    engine_type: str
    contact_email: EmailStr
    payment_plan: str = Field(pattern="^(monthly|semiannual)$")


class ListingCreate(ListingBase):
    performance_profile_id: int


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_usd: Optional[int] = Field(default=None, ge=0)
    location: Optional[str] = None
    engine_type: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    payment_plan: Optional[str] = Field(default=None, pattern="^(monthly|semiannual)$")


class ListingStatusUpdate(BaseModel):
    status: ListingStatus
    reason: Optional[str] = None


class ListingRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price_usd: int
    location: str
    engine_type: str
    contact_email: EmailStr
    status: ListingStatus
    payment_plan: str
    created_at: datetime
    updated_at: datetime
    performance_profile: Optional[PerformanceProfileRead] = None
    pricing_plan: Optional["PricingPlanRead"] = None

    class Config:
        from_attributes = True


class PricingPlanRead(BaseModel):
    id: int
    name: str
    slug: str
    price_usd: int
    billing_cycle_months: int

    class Config:
        from_attributes = True

