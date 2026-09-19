import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.station import Station
from app.models.charging_session import ChargingSession
from app.models.charging_schedule import ChargingSchedule
from app.schemas.session import ChargingSessionCreate, SessionStatusResponse, RescheduleRequest
from app.services.station_service import StationService
from app.services.queue_service import QueueService
from app.services.scheduling_service import SchedulingService
from app.services.notification_service import NotificationService
from app.api.deps import check_session_access

class SessionService:
    @staticmethod
    def create_session(session_in: ChargingSessionCreate, user: User, db: Session) -> ChargingSession:
        """
        Creates, validates, and persists a new charging session.
        Derives energy requirements and estimated duration automatically.
        Triggers SessionCreated notification.
        """
        # Validate station existence and capacity
        station = db.query(Station).filter(Station.station_id == session_in.station_id).first()
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "STATION_NOT_FOUND", "message": f"Station {session_in.station_id} not found.", "status_code": 404}
            )

        max_power = session_in.max_charging_power_kw or session_in.max_charge_power_kw or (station.charger_rating or 50.0)
        station_max_power = station.charger_rating or station.max_power_kw or 350.0
        if max_power > station_max_power:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "INVALID_CHARGING_POWER", "message": f"Requested power {max_power} kW exceeds station charger capacity {station_max_power} kW.", "status_code": 400}
            )

        initial_soc = session_in.initial_soc_pct if session_in.initial_soc_pct is not None else (session_in.current_soc if session_in.current_soc is not None else 20.0)
        target_soc = session_in.target_soc_pct if session_in.target_soc_pct is not None else (session_in.target_soc if session_in.target_soc is not None else 80.0)

        # Calculate backend-derived energy and duration
        energy_req = max(0.0, session_in.battery_capacity_kwh * (target_soc - initial_soc) / 100.0)
        est_duration = (energy_req / max_power) * 60.0 if max_power > 0 else 0.0

        arrival = session_in.arrival_time or datetime.now(timezone.utc)
        ready_by = session_in.ready_by or arrival
        if arrival.tzinfo is None:
            arrival = arrival.replace(tzinfo=timezone.utc)
        if ready_by.tzinfo is None:
            ready_by = ready_by.replace(tzinfo=timezone.utc)

        session_id = f"SES_{uuid.uuid4().hex[:8].upper()}"

        session = ChargingSession(
            session_id=session_id,
            station_id=station.station_id,
            clerk_user_id=user.clerk_user_id,
            arrival_time=arrival,
            ready_by=ready_by,
            initial_soc_pct=initial_soc,
            target_soc_pct=target_soc,
            battery_capacity_kwh=session_in.battery_capacity_kwh,
            energy_required_kwh=round(energy_req, 2),
            max_charging_power_kw=max_power,
            estimated_duration_min=round(est_duration, 2),
            flexibility=session_in.flexibility,
            preference=session_in.preference,
            status="Queued",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # Generate initial schedule automatically
        try:
            SchedulingService.generate_and_persist_schedule(session.session_id, db)
            db.refresh(session)
        except Exception:
            pass

        # Dispatch SessionCreated notification (failure isolated)
        try:
            NotificationService.notify(
                event_type="SessionCreated",
                session_id=session.session_id,
                context={
                    "station_id": session.station_id,
                    "to_phone": session_in.phone_number
                },
                db=db
            )
        except Exception:
            pass

        return session

    @staticmethod
    def get_session(session_id: str, user: User, db: Session) -> ChargingSession:
        return check_session_access(session_id, user, db)

    @staticmethod
    def list_user_sessions(
        user: User,
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        db: Session = None
    ) -> Tuple[List[ChargingSession], int]:
        query = db.query(ChargingSession)

        if user.role == "driver":
            query = query.filter(ChargingSession.clerk_user_id == user.clerk_user_id)
        elif user.role == "operator":
            linked = user.linked_station_ids or []
            query = query.filter(ChargingSession.station_id.in_(linked))
        elif user.role == "grid_operator":
            if user.region:
                station_ids = [s.station_id for s in db.query(Station).filter(Station.state == user.region).all()]
                query = query.filter(ChargingSession.station_id.in_(station_ids))

        if status_filter:
            query = query.filter(ChargingSession.status == status_filter)

        total = query.count()
        sessions = query.order_by(ChargingSession.created_at.desc()).offset(offset).limit(limit).all()
        return sessions, total

    @staticmethod
    def cancel_session(session_id: str, user: User, db: Session) -> ChargingSession:
        session = check_session_access(session_id, user, db)

        if session.status in ["Completed", "Cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "SESSION_ALREADY_COMPLETED", "message": "The charging session has already completed or been cancelled.", "status_code": 409}
            )

        session.status = "Cancelled"
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session_status(session_id: str, user: User, db: Session) -> SessionStatusResponse:
        session = check_session_access(session_id, user, db)

        queue_pos = QueueService.get_queue_position(session, db)
        
        if session.status == "Completed":
            progress = 100.0
            power = 0.0
        elif session.status in ["Charging", "InProgress"]:
            progress = 50.0
            power = session.max_charging_power_kw
        else:
            progress = 0.0
            power = 0.0

        return SessionStatusResponse(
            session_id=session.session_id,
            status=session.status,
            station_id=session.station_id,
            queue_position=queue_pos,
            current_power_kw=power,
            progress_pct=progress,
            updated_at=session.updated_at or datetime.now(timezone.utc)
        )

    @staticmethod
    def reschedule_session(
        session_id: str,
        request: RescheduleRequest,
        user: User,
        db: Session
    ) -> ChargingSchedule:
        session = check_session_access(session_id, user, db)

        if session.status in ["Completed", "Cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "SESSION_NOT_RESCHEDULABLE", "message": "The charging session cannot be rescheduled in its current state.", "status_code": 409}
            )

        return SchedulingService.reschedule_session(
            session_id=session_id,
            ready_by=request.ready_by,
            preference=request.preference,
            flexibility=request.flexibility,
            db=db
        )
