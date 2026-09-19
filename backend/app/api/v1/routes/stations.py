from app.models.user import User
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.schemas.station import StationResponse
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from app.schemas.session import SessionStatusResponse
from app.services.station_service import StationService
from app.services.queue_service import QueueService
from app.services.reliability_service import ReliabilityService
from typing import Optional

router = APIRouter()

@router.get("", response_model=PaginatedResponse[StationResponse])
def list_stations(
    state: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    region: Optional[str] = None,  # Accept region as alias for state
    charger_type: Optional[str] = None,
    min_power_kw: Optional[float] = None,
    max_power_kw: Optional[float] = None,
    availability: Optional[str] = None,
    status: Optional[str] = None,  # Accept status as alias for availability
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    # Handle region parameter (frontend sends region, backend uses state)
    state_filter = state or region
    district_filter = district or city
    
    # Handle status parameter (frontend sends status, backend uses availability)
    availability_filter = availability or status
    
    stations, total = StationService.list_stations(
        state=state_filter,
        district=district_filter,
        availability_status=availability_filter,
        limit=limit,
        offset=offset,
        db=db
    )
    return PaginatedResponse(
        data=[StationResponse.model_validate(s) for s in stations],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/{station_id}", response_model=DataResponse[StationResponse])
def get_station(
    station_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    station = StationService.get_station(station_id, db)
    status_str, avail, total = StationService.get_station_availability(station, db)
    queue_len = len(QueueService.get_station_queue(station.station_id, db))
    rel_info = ReliabilityService.calculate_station_reliability(station.station_id, db)
    
    # Parse charger types
    charger_types = []
    if station.charger_types_connectors_installed:
        charger_types = [ct.strip() for ct in station.charger_types_connectors_installed.split(",")]

    resp_data = {
        # Basic identification
        "id": station.station_id,
        "station_id": station.station_id,
        "name": f"{station.cpo_name} - {station.location}" if station.cpo_name else station.location,
        "location": station.location,
        
        # Location details
        "state": station.state,
        "district": station.district_city_village,
        "district_city_village": station.district_city_village,
        
        # Charging capabilities
        "total_ports": station.no_of_connectors or 1,
        "available_ports": avail,
        "max_power_kw": station.charger_rating or 0,
        "charger_types": charger_types,
        
        # Status and availability
        "status": status_str,
        "current_availability_status": status_str,
        
        # Pricing and green score
        "current_tariff": 0.25,
        "green_score": 75,
        
        # Additional metadata
        "cpo_name": station.cpo_name,
        "govt_private": station.govt_private,
        "charger_rating": station.charger_rating,
        "connector_rating": station.connector_rating,
        "no_of_connectors": station.no_of_connectors,
        "live_queue_length": queue_len,
        "reliability_score": rel_info["reliability_score"],
        "latitude": station.latitude,
        "longitude": station.longitude,
        "charger_types_connectors_installed": station.charger_types_connectors_installed,
    }
    return DataResponse(data=StationResponse.model_validate(resp_data))

@router.get("/{station_id}/sessions", response_model=PaginatedResponse[SessionStatusResponse])
def get_station_sessions(
    station_id: str,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["operator", "grid_operator"]))
):
    sessions, total = StationService.get_station_sessions(
        station_id=station_id,
        limit=limit,
        offset=offset,
        db=db
    )
    from app.services.session_service import SessionService
    status_items = [SessionService.get_session_status(s.session_id, user, db) for s in sessions]
    return PaginatedResponse(
        data=status_items,
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )
