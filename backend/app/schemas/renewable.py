from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RenewableStatusResponse(BaseModel):
    region: str
    timestamp: datetime
    
    # Frontend expected field names
    solar_mw: Optional[float] = None
    wind_mw: Optional[float] = None
    hydro_mw: Optional[float] = None
    other_mw: Optional[float] = None
    total_mw: Optional[float] = None
    renewable_share_pct: Optional[float] = None
    
    # Backend original fields (also supported)
    solar_generation_mw: Optional[float] = None
    wind_generation_mw: Optional[float] = None
    hydro_generation_mw: Optional[float] = None
    other_renewable_mw: Optional[float] = None
    total_renewable_mw: Optional[float] = None
    
    model_config = {"from_attributes": True}
    
    @property
    def get_solar_mw(self) -> float:
        return self.solar_mw or self.solar_generation_mw or 0.0
    
    @property
    def get_wind_mw(self) -> float:
        return self.wind_mw or self.wind_generation_mw or 0.0

class WeatherResponse(BaseModel):
    timestamp: datetime
    region: str
    
    # Frontend expected field names
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    solar_irradiance_wm2: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    weather_condition: Optional[str] = "Clear"
    
    # Backend original fields
    solar_irradiance_w_m2: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    rainfall_mm: Optional[float] = None
    
    model_config = {"from_attributes": True}
