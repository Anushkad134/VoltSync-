from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DriverAgentOutput(BaseModel):
    session_id: str
    energy_required_kwh: float
    estimated_duration_min: int
    urgency: str
    flexibility: str
    preference: str
    available_window_start: datetime
    available_window_end: datetime
    reason: str

class GreenWindow(BaseModel):
    start_time: datetime
    end_time: datetime
    renewable_share_pct: float
    confidence: float

class GreenestWindow(BaseModel):
    start_time: datetime
    end_time: datetime
    renewable_share_pct: float

class RenewableAgentOutput(BaseModel):
    session_id: str
    green_windows: List[GreenWindow]
    greenest_window: Optional[GreenestWindow]
    forecast_confidence: float
    reason: str

class GridAgentOutput(BaseModel):
    session_id: str
    grid_stress: str
    grid_stress_pct: float
    station_load_classification: str
    recommended_action: str
    urgency_override: bool
    reason: str

class CandidateWindow(BaseModel):
    start_time: datetime
    end_time: datetime
    cost_inr: float
    carbon_intensity_gco2_per_kwh: float
    co2_g: float

class CandidateWindowSummary(BaseModel):
    start_time: datetime
    end_time: datetime

class CostCarbonAgentOutput(BaseModel):
    session_id: str
    candidate_windows: List[CandidateWindow]
    cheapest_window: Optional[CandidateWindowSummary]
    lowest_carbon_window: Optional[CandidateWindowSummary]
    tradeoff_summary: str
