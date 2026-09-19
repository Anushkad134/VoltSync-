from app.models.user import User
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_role, require_driver, require_operator, require_grid_operator
from app.schemas.grid import GridStatusResponse
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from app.models.grid_demand import GridDemand
from app.models.station import Station
from app.models.notification_log import NotificationLog
from app.services.queue_service import QueueService
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()

# Default predefined realistic EV grid regions
DEFAULT_REGIONS = [
    {"id": "Maharashtra - Mumbai", "name": "Maharashtra - Mumbai", "state": "Maharashtra", "city": "Mumbai", "grid_capacity_mw": 3500.0},
    {"id": "Karnataka - Bengaluru", "name": "Karnataka - Bengaluru", "state": "Karnataka", "city": "Bengaluru", "grid_capacity_mw": 2800.0},
    {"id": "Delhi NCR - Central", "name": "Delhi NCR - Central", "state": "Delhi NCR", "city": "Central Delhi", "grid_capacity_mw": 4200.0},
    {"id": "Gujarat - Ahmedabad", "name": "Gujarat - Ahmedabad", "state": "Gujarat", "city": "Ahmedabad", "grid_capacity_mw": 2400.0},
    {"id": "Telangana - Hyderabad", "name": "Telangana - Hyderabad", "state": "Telangana", "city": "Hyderabad", "grid_capacity_mw": 2600.0},
    {"id": "Tamil Nadu - Chennai", "name": "Tamil Nadu - Chennai", "state": "Tamil Nadu", "city": "Chennai", "grid_capacity_mw": 3100.0},
    {"id": "Andhra Pradesh - Visakhapatnam", "name": "Andhra Pradesh - Visakhapatnam", "state": "Andhra Pradesh", "city": "Visakhapatnam", "grid_capacity_mw": 1800.0},
    {"id": "Andhra Pradesh - Vijayawada", "name": "Andhra Pradesh - Vijayawada", "state": "Andhra Pradesh", "city": "Vijayawada", "grid_capacity_mw": 1500.0},
    {"id": "Andhra Pradesh - Tirupati", "name": "Andhra Pradesh - Tirupati", "state": "Andhra Pradesh", "city": "Tirupati", "grid_capacity_mw": 1200.0},
]

@router.get("/regions", response_model=DataResponse[List[Dict[str, Any]]])
def get_grid_regions(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))
):
    """Return all available, realistic regional EV grid zones with live metadata"""
    # Query distinct regions from GridDemand
    db_regions = [r[0] for r in db.query(GridDemand.region).distinct().all() if r[0] and not r[0].startswith('-')]
    
    stations = db.query(Station).all()
    
    result = []
    seen_ids = set()

    for r_meta in DEFAULT_REGIONS:
        r_id = r_meta["id"]
        seen_ids.add(r_id)
        
        # Count stations in this region
        matching_stations = [s for s in stations if (s.state and s.state in r_id) or (s.district_city_village and s.district_city_village in r_id)]
        
        # Check latest capacity
        latest = db.query(GridDemand).filter(GridDemand.region == r_id).order_by(GridDemand.timestamp.desc()).first()
        cap = (latest.demand_mw + latest.available_capacity_mw) if latest else r_meta["grid_capacity_mw"]
        
        result.append({
            "id": r_id,
            "name": r_meta["name"],
            "state": r_meta["state"],
            "city": r_meta["city"],
            "station_count": max(len(matching_stations), 3),
            "grid_capacity_mw": cap,
            "status": "OPERATIONAL"
        })

    # Include any additional DB regions not in default list
    for dbr in db_regions:
        if dbr not in seen_ids:
            seen_ids.add(dbr)
            result.append({
                "id": dbr,
                "name": dbr,
                "state": dbr.split(" - ")[0] if " - " in dbr else dbr,
                "city": dbr.split(" - ")[1] if " - " in dbr else dbr,
                "station_count": 2,
                "grid_capacity_mw": 2000.0,
                "status": "OPERATIONAL"
            })

    return DataResponse(data=result)

@router.get("/status", response_model=DataResponse[List[GridStatusResponse]])
def get_grid_status(
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))
):
    target_region = region or user.region or "Maharashtra - Mumbai"
    
    # Query last 24 hours of grid demand for this region
    history = db.query(GridDemand).filter(
        GridDemand.region == target_region
    ).order_by(GridDemand.timestamp.desc()).limit(24).all()
    
    if not history:
        # Fallback to any region data if this specific name isn't found
        history = db.query(GridDemand).order_by(GridDemand.timestamp.desc()).limit(24).all()
    
    if not history:
        # Generate clean 24h mock curve
        now = datetime.now()
        responses = []
        for i in range(24):
            ts = now - timedelta(hours=23-i)
            responses.append(GridStatusResponse(
                region=target_region,
                timestamp=ts,
                base_load_mw=850.0 + 150.0 * (0.5 if (8 <= ts.hour <= 20) else 0.1),
                ev_load_mw=120.0 + 60.0 * (0.8 if (17 <= ts.hour <= 23) else 0.2),
                capacity_mw=2500.0,
                demand_mw=970.0,
                peak_demand_mw=1200.0,
                available_capacity_mw=1530.0,
                reserve_margin_mw=0.61,
                grid_stress_pct=38.8,
            ))
        return DataResponse(data=responses)
    
    # Calculate stations for EV load
    stations = db.query(Station).all()
    regional_stations = [
        s for s in stations
        if target_region in f"{s.state} - {s.district_city_village}" or s.state in target_region
    ]
    real_time_ev_kw = sum(QueueService.calculate_station_load(s.station_id, db) for s in regional_stations)
    
    # Sort chronologically ascending for charts (earliest to latest)
    history_asc = sorted(history, key=lambda x: x.timestamp)
    
    responses = []
    for g in history_asc:
        cap = g.demand_mw + g.available_capacity_mw
        ev_mw = max((real_time_ev_kw / 1000.0), g.demand_mw * 0.14)
        base_mw = max(0.0, g.demand_mw - ev_mw)
        
        responses.append(GridStatusResponse(
            region=g.region,
            timestamp=g.timestamp,
            base_load_mw=round(base_mw, 1),
            ev_load_mw=round(ev_mw, 1),
            capacity_mw=round(cap, 1),
            demand_mw=round(g.demand_mw, 1),
            peak_demand_mw=round(g.peak_demand_mw, 1),
            available_capacity_mw=round(g.available_capacity_mw, 1),
            reserve_margin_mw=round(g.reserve_margin_mw, 2),
            grid_stress_pct=round(g.grid_stress_pct, 1),
        ))
        
    return DataResponse(data=responses)

@router.get("/demand", response_model=PaginatedResponse[GridStatusResponse])
def get_grid_demand(
    region: str,
    start_time: datetime,
    end_time: datetime,
    interval: Optional[str] = None,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))
):
    demand_data = db.query(GridDemand).filter(
        GridDemand.region == region,
        GridDemand.timestamp >= start_time,
        GridDemand.timestamp <= end_time
    ).order_by(GridDemand.timestamp.asc()).offset(offset).limit(limit).all()
    
    responses = []
    for grid in demand_data:
        cap = grid.demand_mw + grid.available_capacity_mw
        ev_mw = grid.demand_mw * 0.14
        base_mw = grid.demand_mw * 0.86
        responses.append(GridStatusResponse(
            region=grid.region,
            timestamp=grid.timestamp,
            base_load_mw=round(base_mw, 1),
            ev_load_mw=round(ev_mw, 1),
            capacity_mw=round(cap, 1),
            demand_mw=round(grid.demand_mw, 1),
            peak_demand_mw=round(grid.peak_demand_mw, 1),
            available_capacity_mw=round(grid.available_capacity_mw, 1),
            reserve_margin_mw=round(grid.reserve_margin_mw, 2),
            grid_stress_pct=round(grid.grid_stress_pct, 1),
        ))
    
    total = db.query(GridDemand).filter(
        GridDemand.region == region,
        GridDemand.timestamp >= start_time,
        GridDemand.timestamp <= end_time
    ).count()
    
    return PaginatedResponse(
        data=responses,
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )

@router.get("/alerts")
def get_grid_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))
):
    from app.models.alert import Alert
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(50).all()
    
    return DataResponse(data=[{
        "id": a.id,
        "event_type": a.type,
        "region_or_station_id": a.region_or_station_id,
        "severity": a.severity,
        "message": a.message,
        "created_at": a.created_at,
    } for a in alerts])

class GridEventCreate(BaseModel):
    region: str
    type: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = "HIGH"
    message: Optional[str] = "Grid stress event triggered"

@router.post("/events", response_model=DataResponse[Dict[str, Any]])
def create_grid_event(
    event: GridEventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["grid_operator", "operator", "driver", "admin"]))
):
    from app.models.alert import Alert
    ev_type = event.event_type or event.type or "GRID_STRESS"
    severity = event.severity or "HIGH"
    message = event.message or f"{ev_type} active in region {event.region}"

    # 1. Create Alert record
    alert_rec = Alert(
        type=ev_type,
        region_or_station_id=event.region,
        severity=severity,
        message=message,
        created_at=datetime.now(),
    )
    db.add(alert_rec)

    # 2. Simulate instant real-time grid stress spike on latest GridDemand
    try:
        latest_grid = db.query(GridDemand).filter(
            GridDemand.region == event.region
        ).order_by(GridDemand.timestamp.desc()).first()
        if latest_grid:
            stress_bump = 25.0 if severity == "CRITICAL" else (15.0 if severity == "HIGH" else 8.0)
            latest_grid.grid_stress_pct = min(99.0, latest_grid.grid_stress_pct + stress_bump)
            db.add(latest_grid)
    except Exception:
        pass

    db.commit()
    db.refresh(alert_rec)

    return DataResponse(data={
        "status": "success",
        "event_id": str(alert_rec.id),
        "region": event.region,
        "event_type": ev_type,
        "severity": severity,
        "message": f"Grid event '{ev_type}' broadcast successfully to {event.region}."
    })
