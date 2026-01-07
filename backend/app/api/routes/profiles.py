from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.entities import PerformanceProfile, PricingPlan
from app.schemas import PerformanceProfileRead, PricingPlanRead

router = APIRouter()


@router.get("/", response_model=List[PerformanceProfileRead])
def list_profiles(session: Session = Depends(get_session)) -> list[PerformanceProfile]:
    return list(session.exec(select(PerformanceProfile)))


@router.get("/plans", response_model=List[PricingPlanRead])
def list_pricing_plans(session: Session = Depends(get_session)) -> list[PricingPlan]:
    return list(session.exec(select(PricingPlan)))

