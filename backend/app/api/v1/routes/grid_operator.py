from app.models.user import User
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_grid_operator
from app.schemas.operator import GridOperatorDashboardResponse, ChargingLoadResponse
from app.schemas.common import DataResponse
from app.services.dashboard_service import DashboardService
from app.models.station import Station
from typing import Optional

router = APIRouter()

@router.get("/dashboard", response_model=DataResponse[GridOperatorDashboardResponse])
def get_grid_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_grid_operator)
):
    dashboard_data = DashboardService.get_grid_operator_dashboard(user, db)
    return DataResponse(data=dashboard_data)

@router.get("/charging-load", response_model=DataResponse[list[ChargingLoadResponse]])
def get_charging_load(
    region: Optional[str] = None,
    station_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_grid_operator)
):
    target_region = region or user.region or "Maharashtra - Mumbai"
    
    if station_id:
        load_data = DashboardService.get_charging_load(station_id, db)
        return DataResponse(data=[load_data])

    # Return charging loads for all stations in target region
    stations = db.query(Station).all()
    matching_stations = [
        s for s in stations
        if target_region in f"{s.state} - {s.district_city_village}" or s.state in target_region
    ]

    loads = [DashboardService.get_charging_load(s.station_id, db) for s in matching_stations]
    return DataResponse(data=loads)
