from crewai.tools import tool
from pydantic import BaseModel, Field
from app.core.database import SessionLocal
from app.models.weather import Weather
from datetime import datetime
import json

class WeatherDataInput(BaseModel):
    region: str = Field(..., description="The geographic region.")
    start_time: str = Field(..., description="Start time in ISO format.")
    end_time: str = Field(..., description="End time in ISO format.")

@tool
def fetch_weather_data(region: str, start_time: str, end_time: str) -> str:
    """Use this tool to fetch weather data (temperature, irradiance, wind speed) for a region and time window."""
    db = SessionLocal()
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = db.query(Weather).filter(
            Weather.region == region,
            Weather.timestamp >= start_dt,
            Weather.timestamp <= end_dt
        ).order_by(Weather.timestamp.asc()).all()
        
        results = []
        for r in records:
            results.append({
                "timestamp": r.timestamp.isoformat(),
                "temperature_c": r.temperature_c,
                "irradiance_w_m2": r.irradiance_w_m2,
                "wind_speed_m_s": r.wind_speed_m_s,
                "cloud_cover_pct": r.cloud_cover_pct,
                "precipitation_mm": r.precipitation_mm
            })
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()
