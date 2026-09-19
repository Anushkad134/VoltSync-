from app.models.user import User
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.schemas.pricing import PricingStatusResponse
from app.schemas.common import PaginatedResponse, Pagination, DataResponse
from app.services.pricing_service import PricingService
from datetime import datetime
from typing import Optional, List

router = APIRouter()

@router.get("/current", response_model=DataResponse[List[PricingStatusResponse]])
def get_current_pricing(
    region: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator", "admin"]))
):
    from app.models.tariff_carbon import TariffCarbon
    target_region = region or user.region or "Maharashtra - Mumbai"
    
    # Query 24h pricing data for the region
    history = db.query(TariffCarbon).filter(
        TariffCarbon.region == target_region
    ).order_by(TariffCarbon.timestamp.desc()).limit(24).all()
    
    if not history:
        history = db.query(TariffCarbon).order_by(TariffCarbon.timestamp.desc()).limit(24).all()
        
    if not history:
        now = datetime.now()
        responses = []
        for i in range(24):
            ts = now - timedelta(hours=23-i)
            responses.append(PricingStatusResponse(
                region=target_region,
                timestamp=ts,
                price_per_kwh=0.22 + (0.08 if 8 <= ts.hour <= 20 else 0.0),
                carbon_intensity_gco2_kwh=380.0 - (120.0 if 10 <= ts.hour <= 16 else 0.0),
                price_tier="Medium",
            ))
        return DataResponse(data=responses)
    
    history_asc = sorted(history, key=lambda x: x.timestamp)
    responses = []
    for p in history_asc:
        # Convert INR to USD/kWh equivalent if needed (e.g., /80) or pass INR directly formatted
        price_val = round(p.electricity_tariff_inr_per_kwh / 80.0, 3) if p.electricity_tariff_inr_per_kwh > 2.0 else round(p.electricity_tariff_inr_per_kwh, 3)
        responses.append(PricingStatusResponse(
            region=p.region,
            timestamp=p.timestamp,
            price_per_kwh=price_val,
            carbon_intensity_gco2_kwh=p.grid_carbon_intensity_gco2_per_kwh,
            price_tier="High" if price_val > 0.18 else ("Medium" if price_val > 0.12 else "Low"),
            electricity_tariff_inr_per_kwh=p.electricity_tariff_inr_per_kwh,
            renewable_share_pct=p.renewable_share_pct,
            grid_carbon_intensity_gco2_per_kwh=p.grid_carbon_intensity_gco2_per_kwh,
        ))
        
    return DataResponse(data=responses)

@router.get("/history", response_model=PaginatedResponse[PricingStatusResponse])
def get_pricing_history(
    region: str,
    start_time: datetime,
    end_time: datetime,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["driver", "operator", "grid_operator"]))
):
    records = PricingService.get_price_history(
        region=region,
        start_time=start_time,
        end_time=end_time,
        db=db
    )
    total = len(records)
    paginated = records[offset:offset + limit]

    return PaginatedResponse(
        data=[PricingStatusResponse.model_validate(r) for r in paginated],
        pagination=Pagination(limit=limit, offset=offset, total=total)
    )
