from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone, timedelta

class ChargingSessionCreate(BaseModel):
    # Frontend field names
    station_id: str
    port_id: Optional[str] = "PORT_A"
    
    # Frontend sends current_soc and target_soc - map to backend naming
    current_soc: Optional[float] = Field(None, ge=0, le=100, alias="current_soc")
    target_soc: Optional[float] = Field(None, ge=0, le=100, alias="target_soc")
    
    # Backend naming (also supported)
    initial_soc_pct: Optional[float] = Field(None, ge=0, le=100)
    target_soc_pct: Optional[float] = Field(None, ge=0, le=100)
    
    battery_capacity_kwh: float = Field(..., gt=0)
    max_charge_power_kw: Optional[float] = Field(None, gt=0, alias="max_charge_power_kw")
    max_charging_power_kw: Optional[float] = Field(None, gt=0)
    
    ready_by: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    
    flexibility: Literal["Low", "Medium", "High"] = "Medium"
    preference: Literal["Fastest", "Cheapest", "Greenest"] = "Greenest"
    
    # Optional contact info
    phone_number: Optional[str] = None
    whatsapp_opt_in: Optional[bool] = False

    model_config = {"populate_by_name": True}
    
    @model_validator(mode="before")
    @classmethod
    def map_frontend_fields(cls, data):
        if isinstance(data, dict):
            # Map frontend field names to backend
            if "current_soc" in data and "initial_soc_pct" not in data:
                data["initial_soc_pct"] = data["current_soc"]
            if "target_soc" in data and "target_soc_pct" not in data:
                data["target_soc_pct"] = data["target_soc"]
            if "max_charge_power_kw" in data and "max_charging_power_kw" not in data:
                data["max_charging_power_kw"] = data["max_charge_power_kw"]
                
        return data
    
    @model_validator(mode="after")
    def validate_soc_and_time(self):
        initial = self.initial_soc_pct if self.initial_soc_pct is not None else self.current_soc
        target = self.target_soc_pct if self.target_soc_pct is not None else self.target_soc
        
        if target is None or initial is None:
            raise ValueError("Both initial and target SOC are required.")
            
        if target <= initial:
            raise ValueError("Target SOC must be greater than initial SOC.")
            
        now = datetime.now(timezone.utc)
        if not self.arrival_time:
            self.arrival_time = now
        elif self.arrival_time.tzinfo is None:
            self.arrival_time = self.arrival_time.replace(tzinfo=timezone.utc)

        if not self.ready_by:
            self.ready_by = self.arrival_time + timedelta(hours=2)
        elif self.ready_by.tzinfo is None:
            self.ready_by = self.ready_by.replace(tzinfo=timezone.utc)
            
        if self.ready_by <= self.arrival_time:
            self.ready_by = self.arrival_time + timedelta(hours=2)
        return self

class ChargingSessionResponse(BaseModel):
    # Include both ID formats for compatibility
    id: Optional[str] = None
    session_id: str
    station_id: str
    station_name: Optional[str] = None
    port_id: Optional[str] = "PORT_A"
    
    arrival_time: datetime
    ready_by: datetime
    initial_soc_pct: float
    target_soc_pct: float
    battery_capacity_kwh: float
    energy_required_kwh: float
    max_charging_power_kw: float
    max_charge_power_kw: Optional[float] = None
    estimated_duration_min: float
    flexibility: str
    preference: str
    
    # Include SOC for frontend display
    current_soc: Optional[float] = None
    target_soc: Optional[float] = None
    
    status: str
    created_at: datetime
    updated_at: datetime
    
    @model_validator(mode="after")
    def populate_computed_fields(self):
        # Add current_soc as initial_soc_pct for frontend compatibility
        if self.current_soc is None:
            self.current_soc = self.initial_soc_pct
        if self.target_soc is None:
            self.target_soc = self.target_soc_pct
        if self.max_charge_power_kw is None:
            self.max_charge_power_kw = self.max_charging_power_kw
        # Add id as alias for session_id
        if self.id is None:
            self.id = self.session_id
        if self.port_id is None:
            self.port_id = "PORT_A"
        return self

    model_config = {"from_attributes": True}

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    station_id: str
    queue_position: int
    current_power_kw: float
    progress_pct: float
    updated_at: datetime
    
class RescheduleRequest(BaseModel):
    ready_by: datetime
    preference: Literal["Fastest", "Cheapest", "Greenest"]
    flexibility: Literal["Low", "Medium", "High"]
    
class ScheduleSegment(BaseModel):
    start_time: datetime
    end_time: datetime
    power_level_kw: Optional[float] = 0.0
    power_kw: Optional[float] = None
    expected_renewable_pct: Optional[float] = 0.0
    expected_cost_inr: Optional[float] = 0.0
    cost_estimate: Optional[float] = None
    expected_co2_g: Optional[float] = 0.0
    carbon_gco2: Optional[float] = None
    segment_reason: Optional[str] = ""

    @model_validator(mode="after")
    def populate_aliases(self):
        if self.power_kw is None:
            self.power_kw = self.power_level_kw
        if self.cost_estimate is None:
            self.cost_estimate = self.expected_cost_inr
        if self.carbon_gco2 is None:
            self.carbon_gco2 = self.expected_co2_g
        return self
    
class ScheduleResponse(BaseModel):
    session_id: str
    summary_line: Optional[str] = ""
    status: str
    segments: List[ScheduleSegment] = []
    schedule_segments: Optional[List[ScheduleSegment]] = None
    agent_outputs: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def populate_schedule_segments(self):
        if self.schedule_segments is None:
            self.schedule_segments = self.segments
        return self

    model_config = {"from_attributes": True}

class AgentDecisionResponse(BaseModel):
    agent: str
    recommendation: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}

class CandidateWindow(BaseModel):
    start_time: datetime
    end_time: datetime
    expected_renewable_pct: float
    expected_cost_inr: float
    expected_co2_g: float
    grid_stress_pct: float
    ranking_reason: str

    model_config = {"from_attributes": True}
