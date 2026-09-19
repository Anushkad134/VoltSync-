from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.tariff_carbon import TariffCarbon
from datetime import datetime
import json

class TariffCarbonInput(BaseModel):
    region: str = Field(..., description="The geographic region.")
    start_time: str = Field(..., description="Start time in ISO format.")
    end_time: str = Field(..., description="End time in ISO format.")

@tool
def fetch_tariff_carbon_data(region: str, start_time: str, end_time: str) -> str:
    """Use this tool to fetch electricity tariff and carbon intensity data for a region and time window."""
    db = SessionLocal()
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = db.query(TariffCarbon).filter(
            TariffCarbon.region == region,
            TariffCarbon.timestamp >= start_dt,
            TariffCarbon.timestamp <= end_dt
        ).order_by(TariffCarbon.timestamp.asc()).all()
        
        results = []
        for r in records:
            results.append({
                "timestamp": r.timestamp.isoformat(),
                "electricity_tariff_inr_per_kwh": r.electricity_tariff_inr_per_kwh,
                "carbon_intensity_gco2_per_kwh": r.carbon_intensity_gco2_per_kwh
            })
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()
