from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.charging_session import ChargingSession

RELIABILITY_THRESHOLDS = {
    "Excellent": 90.0,
    "Good": 75.0,
    "Fair": 60.0
}

class ReliabilityService:
    @staticmethod
    def calculate_station_reliability(station_id: str, db: Session) -> Dict[str, Any]:
        """
        Calculates a deterministic reliability score (0-100) and category for a station.
        Score = (successful_completed_sessions / total_sessions) * 100.
        """
        total_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id == station_id
        ).count()

        completed_sessions = db.query(ChargingSession).filter(
            ChargingSession.station_id == station_id,
            ChargingSession.status == "Completed"
        ).count()

        if total_sessions == 0:
            score = 100.0
        else:
            score = round((completed_sessions / total_sessions) * 100.0, 2)

        if score >= RELIABILITY_THRESHOLDS["Excellent"]:
            category = "Excellent"
        elif score >= RELIABILITY_THRESHOLDS["Good"]:
            category = "Good"
        elif score >= RELIABILITY_THRESHOLDS["Fair"]:
            category = "Fair"
        else:
            category = "Poor"

        return {
            "station_id": station_id,
            "reliability_score": score,
            "reliability_category": category,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions
        }
