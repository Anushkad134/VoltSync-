from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GridStatusResponse(BaseModel):
    region: str
    timestamp: datetime
    
    # Load details
    base_load_mw: Optional[float] = 0.0
    ev_load_mw: Optional[float] = 0.0
    capacity_mw: Optional[float] = 0.0
    demand_mw: Optional[float] = 0.0
    peak_demand_mw: Optional[float] = 0.0
    available_capacity_mw: Optional[float] = 0.0
    reserve_margin_mw: Optional[float] = 0.0
    grid_stress_pct: Optional[float] = 0.0
    
    model_config = {"from_attributes": True}
