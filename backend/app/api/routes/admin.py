from datetime import datetime
from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.entities import Listing, ListingStatus
from app.schemas import ListingRead, ListingStatusUpdate
from app.services.auth import get_current_admin

router = APIRouter()
PERFORMANCE_REL: InstrumentedAttribute = cast(InstrumentedAttribute, Listing.performance_profile)
PRICING_REL: InstrumentedAttribute = cast(InstrumentedAttribute, Listing.pricing_plan)
LISTING_RELATIONSHIPS = (
    selectinload(PERFORMANCE_REL),
    selectinload(PRICING_REL),
)


@router.get("/listings", response_model=List[ListingRead])
def list_pending_listings(
    session: Session = Depends(get_session), admin=Depends(get_current_admin)
) -> list[Listing]:
    created_column = Listing.__table__.c.created_at  # type: ignore[attr-defined]
    statement = (
        select(Listing)
        .where(Listing.status == ListingStatus.PENDING)
        .options(*LISTING_RELATIONSHIPS)
        .order_by(desc(created_column))
    )
    return list(session.exec(statement))


@router.post(
    "/listings/{listing_id}/status",
    response_model=ListingRead,
)
def update_listing_status(
    listing_id: int,
    payload: ListingStatusUpdate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),
) -> Listing:
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.status = payload.status
    listing.rejected_reason = payload.reason if payload.status == ListingStatus.REJECTED else None
    if payload.status == ListingStatus.ACTIVE:
        listing.approved_at = datetime.utcnow()
    else:
        listing.approved_at = None
    listing.updated_at = datetime.utcnow()
    session.add(listing)
    session.commit()
    return session.exec(
        select(Listing).where(Listing.id == listing.id).options(*LISTING_RELATIONSHIPS)
    ).one()

