from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PricingStatusResponse(BaseModel):
    region: str
    timestamp: datetime
    
    # Frontend expected fields
    price_per_kwh: Optional[float] = None
    carbon_intensity_gco2_kwh: Optional[float] = None
    price_tier: Optional[str] = "Medium"
    
    # Backend original fields (also supported)
    tariff_period: Optional[str] = None
    electricity_tariff_inr_per_kwh: Optional[float] = None
    renewable_share_pct: Optional[float] = None
    grid_carbon_intensity_gco2_per_kwh: Optional[float] = None
    
    model_config = {"from_attributes": True}
    
    @property
    def get_price_per_kwh(self) -> float:
        return self.price_per_kwh or self.electricity_tariff_inr_per_kwh or 0.25
    
    @property
    def get_carbon_intensity(self) -> float:
        return self.carbon_intensity_gco2_kwh or self.grid_carbon_intensity_gco2_per_kwh or 350.0
