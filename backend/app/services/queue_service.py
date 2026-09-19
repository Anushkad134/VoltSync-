from typing import List
from sqlalchemy.orm import Session
from app.models.charging_session import ChargingSession

class QueueService:
    @staticmethod
    def get_queue_position(session: ChargingSession, db: Session) -> int:
        """
        Calculates the 1-based queue position for a session at its station.
        Active charging sessions return 0.
        Ordering is deterministic: arrival_time ASC, created_at ASC.
        """
        if not session or session.status in ["Completed", "Cancelled", "Infeasible"]:
            return 0

        if session.status in ["Charging", "InProgress"]:
            return 0

        # Fetch queued sessions for the same station ordered deterministically
        queued_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id == session.station_id,
            ChargingSession.status.in_(["Queued", "Created", "Scheduled"])
        ).order_by(
            ChargingSession.arrival_time.asc(),
            ChargingSession.created_at.asc()
        ).all()

        for idx, s in enumerate(queued_sessions, start=1):
            if s.session_id == session.session_id:
                return idx

        return 1

    @staticmethod
    def get_station_queue(station_id: str, db: Session) -> List[ChargingSession]:
        """
        Returns all queued sessions for a station ordered deterministically.
        """
        return db.query(ChargingSession).filter(
            ChargingSession.station_id == station_id,
            ChargingSession.status.in_(["Queued", "Created", "Scheduled"])
        ).order_by(
            ChargingSession.arrival_time.asc(),
            ChargingSession.created_at.asc()
        ).all()

    @staticmethod
    def calculate_station_load(station_id: str, db: Session) -> float:
        """
        Calculates active charging load in kW across currently charging sessions at a station.
        """
        active_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id == station_id,
            ChargingSession.status.in_(["Charging", "InProgress"])
        ).all()

        total_load = sum(s.max_charging_power_kw for s in active_sessions)
        return round(total_load, 2)
