from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OperatorStationData(BaseModel):
    id: str
    name: str
    location: str
    status: str
    active_sessions: int
    current_power_draw: float
    total_ports: int
    available_ports: int
    max_power_kw: float
    queue_length: int

class OperatorSessionData(BaseModel):
    id: str
    session_id: str
    status: str
    target_soc: float
    estimated_wait_minutes: Optional[float] = None
    created_at: datetime

class OperatorDashboardResponse(BaseModel):
    station_count: int
    available_stations: int
    occupied_stations: int
    offline_stations: int
    total_active_sessions: int
    queued_sessions: int
    average_queue_length: float
    current_charging_load_kw: float
    relevant_grid_stress_pct: float
    renewable_share_pct: float
    
    # Additional frontend expected fields
    stations: List[OperatorStationData] = []
    queued_sessions_list: List[OperatorSessionData] = []  # For queue table
    power_consumption_history: List[dict] = []

class GridOperatorDashboardResponse(BaseModel):
    region: str
    current_demand_mw: float
    peak_demand_mw: float
    available_capacity_mw: float
    reserve_margin_mw: float
    grid_stress_pct: float
    renewable_share_pct: float
    active_charging_load_kw: float
    active_grid_alerts: int

class ChargingLoadResponse(BaseModel):
    station_id: str
    region: str
    active_sessions: int
    charging_load_kw: float
    queue_length: int
