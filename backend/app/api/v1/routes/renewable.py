from app.models.user import User
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_role, require_driver, require_operator, require_grid_operator
from app.schemas.renewable import RenewableStatusResponse, WeatherResponse
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from app.models.renewable_generation import RenewableGeneration
from app.models.weather import Weather
from typing import Optional, List
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/status", response_model=DataResponse[List[RenewableStatusResponse]])
def get_renewable_status(
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator", "admin"]))
):
    # Use user's region if not specified
    target_region = region or user.region or "Maharashtra - Mumbai"
    
    # Get 24h renewable generation data for region
    history = db.query(RenewableGeneration).filter(
        RenewableGeneration.region == target_region
    ).order_by(RenewableGeneration.timestamp.desc()).limit(24).all()
    
    if not history:
        history = db.query(RenewableGeneration).order_by(RenewableGeneration.timestamp.desc()).limit(24).all()
        
    if not history:
        now = datetime.now()
        responses = []
        for i in range(24):
            ts = now - timedelta(hours=23-i)
            hour = ts.hour
            solar_factor = max(0.0, 1.0 - abs(hour - 13) / 6.0) if 6 <= hour <= 18 else 0.0
            solar_mw = round(450.0 * solar_factor, 1)
            wind_mw = round(220.0 + (30.0 if hour < 8 or hour > 18 else -20.0), 1)
            total = solar_mw + wind_mw + 80.0
            responses.append(RenewableStatusResponse(
                region=target_region,
                timestamp=ts,
                solar_mw=solar_mw,
                wind_mw=wind_mw,
                hydro_mw=60.0,
                other_mw=20.0,
                total_mw=total,
                renewable_share_pct=round(min(90.0, (total / 1000.0) * 100.0), 1),
            ))
        return DataResponse(data=responses)
    
    history_asc = sorted(history, key=lambda x: x.timestamp)
    responses = [
        RenewableStatusResponse(
            region=r.region,
            timestamp=r.timestamp,
            solar_mw=r.solar_generation_mw,
            wind_mw=r.wind_generation_mw,
            hydro_mw=r.hydro_generation_mw,
            other_mw=r.other_renewable_mw,
            total_mw=r.total_renewable_mw,
            renewable_share_pct=r.renewable_share_pct,
        ) for r in history_asc
    ]
    
    return DataResponse(data=responses)

@router.get("/generation", response_model=PaginatedResponse[RenewableStatusResponse])
def get_renewable_history(
    region: str,
    start_time: datetime,
    end_time: datetime,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    # Query renewable generation data for the time range
    ren_data = db.query(RenewableGeneration).filter(
        RenewableGeneration.region == region,
        RenewableGeneration.timestamp >= start_time,
        RenewableGeneration.timestamp <= end_time
    ).order_by(RenewableGeneration.timestamp.desc()).offset(offset).limit(limit).all()
    
    responses = [RenewableStatusResponse(
        region=r.region,
        timestamp=r.timestamp,
        solar_mw=r.solar_generation_mw,
        wind_mw=r.wind_generation_mw,
        hydro_mw=r.hydro_generation_mw,
        other_mw=r.other_renewable_mw,
        total_mw=r.total_renewable_mw,
        renewable_share_pct=r.renewable_share_pct,
    ) for r in ren_data]
    
    total = db.query(RenewableGeneration).filter(
        RenewableGeneration.region == region,
        RenewableGeneration.timestamp >= start_time,
        RenewableGeneration.timestamp <= end_time
    ).count()
    
    return PaginatedResponse(
        data=responses,
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/weather", response_model=DataResponse[List[WeatherResponse]])
def get_weather(
    region: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    # Default to last 24 hours if not specified
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    weather_data = db.query(Weather).filter(
        Weather.region == region,
        Weather.timestamp >= start_time,
        Weather.timestamp <= end_time
    ).order_by(Weather.timestamp.desc()).limit(50).all()
    
    if not weather_data:
        # Return mock data
        return DataResponse(data=[WeatherResponse(
            region=region,
            timestamp=datetime.now(),
            temperature_c=28.0,
            humidity_pct=65.0,
            cloud_cover_pct=30.0,
            solar_irradiance_wm2=600.0,
            wind_speed_ms=5.0,
            weather_condition="Clear",
        )])
    
    responses = [WeatherResponse(
        region=w.region,
        timestamp=w.timestamp,
        temperature_c=w.temperature_c,
        humidity_pct=w.humidity_pct,
        cloud_cover_pct=w.cloud_cover_pct,
        solar_irradiance_wm2=w.solar_irradiance_wm2,
        wind_speed_ms=w.wind_speed_ms,
        weather_condition=w.weather_condition,
    ) for w in weather_data]
    
    return DataResponse(data=responses)
