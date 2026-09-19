from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.renewable_generation import RenewableGeneration
from datetime import datetime
import json

class RenewableDataInput(BaseModel):
    region: str = Field(..., description="The geographic region (e.g., 'Ahmedabad').")
    start_time: str = Field(..., description="Start time in ISO format (e.g., '2026-01-10T10:00:00').")
    end_time: str = Field(..., description="End time in ISO format (e.g., '2026-01-10T15:00:00').")

@tool
def fetch_renewable_data(region: str, start_time: str, end_time: str) -> str:
    """Use this tool to fetch renewable generation data (solar, wind, hydro) for a region and time window."""
    db = SessionLocal()
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = db.query(RenewableGeneration).filter(
            RenewableGeneration.region == region,
            RenewableGeneration.timestamp >= start_dt,
            RenewableGeneration.timestamp <= end_dt
        ).order_by(RenewableGeneration.timestamp.asc()).all()
        
        results = []
        for r in records:
            results.append({
                "timestamp": r.timestamp.isoformat(),
                "solar_generation_mw": r.solar_generation_mw,
                "wind_generation_mw": r.wind_generation_mw,
                "hydro_generation_mw": r.hydro_generation_mw,
                "other_renewable_mw": r.other_renewable_mw,
                "demand_mw": r.demand_mw,
                "renewable_share_pct": r.renewable_share_pct
            })
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()
