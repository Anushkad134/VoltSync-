from pydantic import BaseModel
from typing import Optional, List

class StationResponse(BaseModel):
    # Basic identification
    id: str
    station_id: str
    name: str
    location: str
    
    # Location details
    state: str
    district: str
    district_city_village: str
    
    # Charging capabilities
    total_ports: int
    available_ports: int
    max_power_kw: float
    charger_types: List[str]
    
    # Status and availability
    status: str
    current_availability_status: str
    
    # Pricing and green score
    current_tariff: Optional[float] = None
    green_score: Optional[int] = 0
    
    # Additional metadata
    cpo_name: Optional[str] = None
    govt_private: Optional[str] = None
    charger_rating: Optional[float] = None
    connector_rating: Optional[float] = None
    no_of_connectors: Optional[int] = None
    live_queue_length: Optional[int] = 0
    reliability_score: Optional[float] = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    charger_types_connectors_installed: Optional[str] = None

    model_config = {"from_attributes": True}
