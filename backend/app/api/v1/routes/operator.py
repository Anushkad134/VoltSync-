from app.models.user import User
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_operator
from app.schemas.operator import OperatorDashboardResponse
from app.schemas.station import StationResponse
from app.schemas.session import ChargingSessionResponse
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from app.services.dashboard_service import DashboardService
from app.services.station_service import StationService
from app.services.session_service import SessionService
from typing import Optional

router = APIRouter()

@router.get("/dashboard", response_model=DataResponse[OperatorDashboardResponse])
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_operator)
):
    dashboard_data = DashboardService.get_operator_dashboard(user, db)
    return DataResponse(data=dashboard_data)

@router.get("/stations", response_model=PaginatedResponse[StationResponse])
def get_operator_stations(
    availability: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_operator)
):
    stations, total = StationService.list_stations(
        state=state,
        district=city,
        availability_status=availability,
        limit=limit,
        offset=offset,
        db=db
    )
    # If user has linked_station_ids, filter to those
    if user.linked_station_ids:
        stations = [s for s in stations if s["station_id"] in user.linked_station_ids]
        total = len(stations)

    return PaginatedResponse(
        data=[StationResponse.model_validate(s) for s in stations],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/sessions", response_model=PaginatedResponse[ChargingSessionResponse])
def get_operator_sessions(
    status: Optional[str] = None,
    station_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_operator)
):
    sessions, total = SessionService.list_user_sessions(
        user=user,
        status_filter=status,
        limit=limit,
        offset=offset,
        db=db
    )
    if station_id:
        sessions = [s for s in sessions if s.station_id == station_id]
        total = len(sessions)

    return PaginatedResponse(
        data=[ChargingSessionResponse.model_validate(s) for s in sessions],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )
