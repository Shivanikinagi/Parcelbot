"""Operations dashboard + analytics (internal roles only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_principal
from app.core.security import Principal
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["ops"])


@router.get("/ops/dashboard")
def dashboard(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    principal.require("view_ops")
    return AnalyticsService(db, principal).dashboard()


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), principal: Principal = Depends(get_principal)):
    principal.require("view_analytics")
    return AnalyticsService(db, principal).analytics()
