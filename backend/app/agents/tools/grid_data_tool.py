from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.grid_demand import GridDemand
from datetime import datetime
import json

class GridDataInput(BaseModel):
    region: str = Field(..., description="The geographic region.")
    start_time: str = Field(..., description="Start time in ISO format.")
    end_time: str = Field(..., description="End time in ISO format.")

@tool
def fetch_grid_data(region: str, start_time: str, end_time: str) -> str:
    """Use this tool to fetch grid demand, available capacity, and grid stress for a region and time window."""
    db = SessionLocal()
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = db.query(GridDemand).filter(
            GridDemand.region == region,
            GridDemand.timestamp >= start_dt,
            GridDemand.timestamp <= end_dt
        ).order_by(GridDemand.timestamp.asc()).all()
        
        results = []
        for r in records:
            results.append({
                "timestamp": r.timestamp.isoformat(),
                "demand_mw": r.demand_mw,
                "available_capacity_mw": r.available_capacity_mw,
                "reserve_margin_mw": r.reserve_margin_mw,
                "grid_stress_pct": r.grid_stress_pct
            })
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()
