from datetime import datetime
from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.entities import Listing, ListingStatus, PerformanceProfile, PricingPlan
from app.schemas import ListingCreate, ListingRead, ListingUpdate
from app.services.auth import get_current_user

router = APIRouter()
PERFORMANCE_REL: InstrumentedAttribute = cast(InstrumentedAttribute, Listing.performance_profile)
PRICING_REL: InstrumentedAttribute = cast(InstrumentedAttribute, Listing.pricing_plan)
LISTING_RELATIONSHIPS = (
    selectinload(PERFORMANCE_REL),
    selectinload(PRICING_REL),
)


@router.get("/", response_model=List[ListingRead])
def list_public_listings(
    session: Session = Depends(get_session),
) -> list[Listing]:
    created_column = Listing.__table__.c.created_at  # type: ignore[attr-defined]
    statement = (
        select(Listing)
        .where(Listing.status == ListingStatus.ACTIVE)
        .options(*LISTING_RELATIONSHIPS)
        .order_by(desc(created_column))
    )
    listings = session.exec(statement).all()
    return list(listings)


@router.post("/", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing_in: ListingCreate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
) -> Listing:
    profile = session.get(PerformanceProfile, listing_in.performance_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Performance profile not found")

    plan = session.exec(
        select(PricingPlan).where(PricingPlan.slug == listing_in.payment_plan)
    ).first()
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid pricing plan selected")

    db_listing = Listing(
        title=listing_in.title or f"{profile.manufacturer} {profile.name}",
        description=listing_in.description,
        price_usd=listing_in.price_usd,
        location=listing_in.location,
        engine_type=listing_in.engine_type or profile.engine_type,
        contact_email=listing_in.contact_email,
        payment_plan=listing_in.payment_plan,
        performance_profile_id=profile.id,
        owner_id=user.id,
        pricing_plan_id=plan.id,
    )
    session.add(db_listing)
    session.commit()
    session.refresh(db_listing)
    return (
        session.exec(
            select(Listing)
            .where(Listing.id == db_listing.id)
            .options(*LISTING_RELATIONSHIPS)
        ).one()
    )


@router.patch("/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    listing_in: ListingUpdate,
    session: Session = Depends(get_session),
    user=Depends(get_current_user),
) -> Listing:
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update listing")

    update_data = listing_in.dict(exclude_unset=True)

    if "payment_plan" in update_data:
        plan = session.exec(
            select(PricingPlan).where(PricingPlan.slug == update_data["payment_plan"])
        ).first()
        if not plan:
            raise HTTPException(status_code=400, detail="Invalid pricing plan selected")
        listing.pricing_plan_id = plan.id

    for key, value in update_data.items():
        setattr(listing, key, value)

    listing.updated_at = datetime.utcnow()
    session.add(listing)
    session.commit()
    listing = session.exec(
        select(Listing).where(Listing.id == listing.id).options(*LISTING_RELATIONSHIPS)
    ).one()
    return listing

