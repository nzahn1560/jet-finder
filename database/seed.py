from __future__ import annotations

import sys
from pathlib import Path

from sqlmodel import Session, select

BACKEND_PATH = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.core.config import get_settings  # type: ignore  # noqa: E402
from app.core.database import engine  # type: ignore  # noqa: E402
from app.models.entities import (  # type: ignore  # noqa: E402
    Listing,
    ListingStatus,
    PerformanceProfile,
    PricingPlan,
    User,
)
from app.services.auth import get_password_hash  # type: ignore  # noqa: E402

settings = get_settings()


def ensure_admin(session: Session) -> User:
    admin = session.exec(select(User).where(User.email == settings.admin_email)).first()
    if admin:
        return admin

    admin = User(
        email=settings.admin_email,
        hashed_password=get_password_hash(settings.admin_password),
        is_admin=True,
        force_password_reset=settings.force_password_reset,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def ensure_pricing_plans(session: Session) -> list[PricingPlan]:
    seed_plans = [
        dict(name="Monthly", slug="monthly", price_usd=50, billing_cycle_months=1),
        dict(
            name="Six-Month",
            slug="semiannual",
            price_usd=150,
            billing_cycle_months=6,
        ),
    ]
    plans: list[PricingPlan] = []
    for payload in seed_plans:
        plan = session.exec(
            select(PricingPlan).where(PricingPlan.slug == payload["slug"])
        ).first()
        if not plan:
            plan = PricingPlan(**payload)
            session.add(plan)
            session.commit()
            session.refresh(plan)
        plans.append(plan)
    return plans


def ensure_profiles(session: Session) -> list[PerformanceProfile]:
    profile_payloads = [
        {
            "name": "Piper M600",
            "manufacturer": "Piper",
            "engine_type": "Turboprop",
            "range_nm": 1400,
            "cruise_speed_knots": 274,
            "max_passengers": 5,
            "max_altitude_ft": 30000,
            "cabin_volume_cuft": 165.3,
            "baggage_volume_cuft": 45.0,
            "purchase_price_usd": 3200000,
        },
        {
            "name": "Cessna Citation CJ3+",
            "manufacturer": "Cessna",
            "engine_type": "Jet",
            "range_nm": 2040,
            "cruise_speed_knots": 416,
            "max_passengers": 7,
            "max_altitude_ft": 45000,
            "cabin_volume_cuft": 286.2,
            "baggage_volume_cuft": 65.0,
            "purchase_price_usd": 9500000,
        },
    ]
    profiles: list[PerformanceProfile] = []
    for payload in profile_payloads:
        profile = session.exec(
            select(PerformanceProfile).where(
                PerformanceProfile.name == payload["name"],
                PerformanceProfile.manufacturer == payload["manufacturer"],
            )
        ).first()
        if not profile:
            profile = PerformanceProfile(**payload)
            session.add(profile)
            session.commit()
            session.refresh(profile)
        profiles.append(profile)
    return profiles


def ensure_sample_listing(
    session: Session,
    admin: User,
    profile: PerformanceProfile,
    pricing_plan: PricingPlan,
) -> None:
    existing = session.exec(
        select(Listing).where(Listing.performance_profile_id == profile.id)
    ).first()
    if existing:
        return

    listing = Listing(
        title=f"{profile.manufacturer} {profile.name}",
        description="Beautifully maintained aircraft with recent avionics upgrade.",
        price_usd=int(profile.purchase_price_usd or 0),
        location="KDAL",
        engine_type=profile.engine_type,
        contact_email="sales@example.com",
        status=ListingStatus.ACTIVE,
        owner_id=admin.id,
        performance_profile_id=profile.id,
        pricing_plan_id=pricing_plan.id,
    )
    session.add(listing)
    session.commit()


def seed() -> None:
    with Session(engine) as session:
        admin = ensure_admin(session)
        plans = ensure_pricing_plans(session)
        profiles = ensure_profiles(session)

        monthly_plan = next(plan for plan in plans if plan.slug == "monthly")
        if profiles:
            ensure_sample_listing(session, admin, profiles[0], monthly_plan)


if __name__ == "__main__":
    seed()

