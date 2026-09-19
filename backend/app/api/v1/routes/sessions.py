from app.models.user import User
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_role, require_driver, require_operator, require_grid_operator
from app.schemas.session import (
    ChargingSessionCreate, ChargingSessionResponse, SessionStatusResponse,
    ScheduleResponse, RescheduleRequest, AgentDecisionResponse, CandidateWindow
)
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from typing import Optional, List
from datetime import datetime

router = APIRouter()

@router.post("", response_model=DataResponse[ChargingSessionResponse], status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChargingSessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_driver)
):
    from app.services.session_service import SessionService
    session = SessionService.create_session(session_in, user, db)
    return DataResponse(data=ChargingSessionResponse.model_validate(session))

@router.get("", response_model=PaginatedResponse[ChargingSessionResponse])
def list_my_sessions(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_driver)
):
    from app.services.session_service import SessionService
    sessions, total = SessionService.list_user_sessions(user, status_filter=status, limit=limit, offset=offset, db=db)
    return PaginatedResponse(
        data=[ChargingSessionResponse.model_validate(s) for s in sessions],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/{session_id}", response_model=DataResponse[ChargingSessionResponse])
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    from app.services.session_service import SessionService
    session = SessionService.get_session(session_id, user, db)
    return DataResponse(data=ChargingSessionResponse.model_validate(session))

@router.get("/{session_id}/status", response_model=DataResponse[SessionStatusResponse])
def get_session_status(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    from app.services.session_service import SessionService
    status_data = SessionService.get_session_status(session_id, user, db)
    return DataResponse(data=status_data)

@router.get("/{session_id}/schedule", response_model=DataResponse[ScheduleResponse])
def get_schedule(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    from app.api.deps import check_session_access
    check_session_access(session_id, user, db)
    from app.services.scheduling_service import SchedulingService
    schedule = SchedulingService.get_schedule(session_id, db)
    return DataResponse(data=ScheduleResponse.model_validate(schedule))

@router.post("/{session_id}/schedule", response_model=DataResponse[ScheduleResponse])
def generate_schedule(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator"]))
):
    from app.api.deps import check_session_access
    check_session_access(session_id, user, db)
    from app.services.scheduling_service import SchedulingService
    schedule = SchedulingService.generate_and_persist_schedule(session_id, db)
    return DataResponse(data=ScheduleResponse.model_validate(schedule))

@router.get("/{session_id}/schedule/history", response_model=PaginatedResponse[ScheduleResponse])
def get_schedule_history(
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    from app.api.deps import check_session_access
    check_session_access(session_id, user, db)
    from app.services.scheduling_service import SchedulingService
    schedules, total = SchedulingService.get_schedule_history(session_id, db, limit=limit, offset=offset)
    return PaginatedResponse(
        data=[ScheduleResponse.model_validate(s) for s in schedules],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/{session_id}/charging-windows", response_model=DataResponse[List[CandidateWindow]])
def get_charging_windows(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator"]))
):
    from app.api.deps import check_session_access
    check_session_access(session_id, user, db)
    from app.services.scheduling_service import SchedulingService
    windows = SchedulingService.get_candidate_windows(session_id, db)
    return DataResponse(data=[CandidateWindow.model_validate(w) for w in windows])

@router.get("/{session_id}/agent-decisions", response_model=DataResponse[List[AgentDecisionResponse]])
def get_agent_decisions(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    from app.api.deps import check_session_access
    check_session_access(session_id, user, db)
    from app.services.scheduling_service import SchedulingService
    decisions = SchedulingService.get_agent_decisions(session_id, db)
    return DataResponse(data=[AgentDecisionResponse.model_validate(d) for d in decisions])

@router.post("/{session_id}/cancel", response_model=DataResponse[ChargingSessionResponse])
def cancel_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_driver)
):
    from app.services.session_service import SessionService
    session = SessionService.cancel_session(session_id, user, db)
    return DataResponse(data=ChargingSessionResponse.model_validate(session))

@router.post("/{session_id}/reschedule", response_model=DataResponse[ScheduleResponse])
def reschedule_session(
    session_id: str,
    request: RescheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_driver)
):
    from app.services.session_service import SessionService
    schedule = SessionService.reschedule_session(session_id, request, user, db)
    return DataResponse(data=ScheduleResponse.model_validate(schedule))
