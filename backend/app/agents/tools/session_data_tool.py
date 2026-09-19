from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.charging_session import ChargingSession
import json

class SessionDataInput(BaseModel):
    session_id: str = Field(..., description="The ID of the charging session to fetch data for.")

@tool
def fetch_session_data(session_id: str) -> str:
    """Use this tool to fetch charging session details like target SOC, battery capacity, arrival time, and driver preference."""
    db = SessionLocal()
    try:
        session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
        if not session:
            return json.dumps({"error": "Session not found."})
        return json.dumps({
            "session_id": session.session_id,
            "arrival_time": session.arrival_time.isoformat(),
            "ready_by": session.ready_by.isoformat(),
            "initial_soc_pct": session.initial_soc_pct,
            "target_soc_pct": session.target_soc_pct,
            "battery_capacity_kwh": session.battery_capacity_kwh,
            "energy_required_kwh": session.energy_required_kwh,
            "max_charging_power_kw": session.max_charging_power_kw,
            "estimated_duration_min": session.estimated_duration_min,
            "flexibility": session.flexibility,
            "preference": session.preference,
            "station_id": session.station_id
        })
    finally:
        db.close()
