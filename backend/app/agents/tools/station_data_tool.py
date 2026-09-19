from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.station import Station
import json

class StationDataInput(BaseModel):
    station_id: str = Field(..., description="The ID of the charging station.")

@tool
def fetch_station_data(station_id: str) -> str:
    """Use this tool to fetch charging station details like region, total capacity, and location."""
    db = SessionLocal()
    try:
        station = db.query(Station).filter(Station.station_id == station_id).first()
        if not station:
            return json.dumps({"error": "Station not found."})
        return json.dumps({
            "station_id": station.station_id,
            "name": station.name,
            "region": station.region,
            "city": station.city,
            "state": station.state,
            "total_capacity_kw": station.total_capacity_kw,
            "is_active": station.is_active
        })
    finally:
        db.close()
