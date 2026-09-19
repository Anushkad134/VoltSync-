from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.user import User
from app.models.notification_log import NotificationLog
from app.models.charging_session import ChargingSession
from app.schemas.notification import NotificationResponse
from app.schemas.common import PaginatedResponse, Pagination
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("", response_model=PaginatedResponse[NotificationResponse])
def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = db.query(NotificationLog)

    if user.role == "driver":
        driver_sessions = db.query(ChargingSession.session_id).filter(
            ChargingSession.clerk_user_id == user.clerk_user_id
        ).all()
        session_ids = [s[0] for s in driver_sessions]
        query = query.filter(NotificationLog.session_id.in_(session_ids))

    elif user.role == "operator":
        linked_stations = user.linked_station_ids or []
        op_sessions = db.query(ChargingSession.session_id).filter(
            ChargingSession.station_id.in_(linked_stations)
        ).all()
        session_ids = [s[0] for s in op_sessions]
        
        # Operator sees notifications for their stations' sessions plus station alerts
        query = query.filter(
            (NotificationLog.session_id.in_(session_ids)) |
            (NotificationLog.event_type == "StationAlert")
        )

    elif user.role == "grid_operator":
        query = query.filter(NotificationLog.event_type == "GridAlert")

    total = query.count()
    items = query.order_by(NotificationLog.timestamp.desc(), NotificationLog.id.desc()).offset(offset).limit(limit).all()

    return PaginatedResponse(
        data=[NotificationResponse.model_validate(n) for n in items],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )
