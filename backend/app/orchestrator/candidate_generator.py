from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.renewable_generation import RenewableGeneration
from app.models.tariff_carbon import TariffCarbon
from app.models.grid_demand import GridDemand

class CandidateSlot:
    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        tariff_inr_per_kwh: float,
        carbon_intensity_gco2_per_kwh: float,
        renewable_share_pct: float,
        grid_stress_pct: float,
        max_power_kw: float
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.tariff_inr_per_kwh = tariff_inr_per_kwh
        self.carbon_intensity_gco2_per_kwh = carbon_intensity_gco2_per_kwh
        self.renewable_share_pct = renewable_share_pct
        self.grid_stress_pct = grid_stress_pct
        self.max_power_kw = max_power_kw
        self.duration_hours = (end_time - start_time).total_seconds() / 3600.0
        self.max_energy_kwh = max_power_kw * self.duration_hours

        # Score fields populated by ScoringEngine
        self.speed_score: float = 0.0
        self.renewable_score: float = 0.0
        self.cost_score: float = 0.0
        self.carbon_score: float = 0.0
        self.grid_score: float = 0.0
        self.total_score: float = 0.0
        self.is_critical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "tariff_inr_per_kwh": self.tariff_inr_per_kwh,
            "carbon_intensity_gco2_per_kwh": self.carbon_intensity_gco2_per_kwh,
            "renewable_share_pct": self.renewable_share_pct,
            "grid_stress_pct": self.grid_stress_pct,
            "max_power_kw": self.max_power_kw,
            "total_score": self.total_score
        }


def generate_candidate_slots(
    arrival_time: datetime,
    ready_by: datetime,
    max_power_kw: float,
    region: str,
    db: Session,
    interval_minutes: int = 15
) -> List[CandidateSlot]:
    """
    Generates 15-minute candidate slots between arrival_time and ready_by,
    enriching each slot with renewable, tariff, carbon, and grid demand metrics.
    """
    if ready_by <= arrival_time or max_power_kw <= 0:
        return []

    # Ensure timezone awareness
    if arrival_time.tzinfo is None:
        arrival_time = arrival_time.replace(tzinfo=timezone.utc)
    if ready_by.tzinfo is None:
        ready_by = ready_by.replace(tzinfo=timezone.utc)

    # Fetch dataset records in bulk for the region and time range
    renewable_records = db.query(RenewableGeneration).filter(
        RenewableGeneration.region == region,
        RenewableGeneration.timestamp >= arrival_time - timedelta(minutes=15),
        RenewableGeneration.timestamp <= ready_by + timedelta(minutes=15)
    ).all()
    renewable_map = {r.timestamp.replace(tzinfo=timezone.utc) if r.timestamp.tzinfo is None else r.timestamp: r for r in renewable_records}

    tariff_records = db.query(TariffCarbon).filter(
        TariffCarbon.region == region,
        TariffCarbon.timestamp >= arrival_time - timedelta(minutes=15),
        TariffCarbon.timestamp <= ready_by + timedelta(minutes=15)
    ).all()
    tariff_map = {r.timestamp.replace(tzinfo=timezone.utc) if r.timestamp.tzinfo is None else r.timestamp: r for r in tariff_records}

    grid_records = db.query(GridDemand).filter(
        GridDemand.region == region,
        GridDemand.timestamp >= arrival_time - timedelta(minutes=15),
        GridDemand.timestamp <= ready_by + timedelta(minutes=15)
    ).all()
    grid_map = {r.timestamp.replace(tzinfo=timezone.utc) if r.timestamp.tzinfo is None else r.timestamp: r for r in grid_records}

    slots: List[CandidateSlot] = []
    current = arrival_time
    delta = timedelta(minutes=interval_minutes)

    while current < ready_by:
        slot_end = min(current + delta, ready_by)
        if slot_end <= current:
            break

        # Look up nearest or exact metrics
        r_rec = _find_nearest(renewable_map, current)
        t_rec = _find_nearest(tariff_map, current)
        g_rec = _find_nearest(grid_map, current)

        hour = current.hour
        solar_boost = 55.0 * max(0.0, 1.0 - abs(hour - 13) / 5.0) if 8 <= hour <= 18 else 0.0
        default_renewable = min(95.0, 30.0 + solar_boost)
        default_tariff = 12.0 if 10 <= hour <= 15 else (18.5 if 18 <= hour <= 22 else 14.0)
        default_carbon = max(120.0, 480.0 - (solar_boost * 3.5))
        default_grid = 72.0 if 18 <= hour <= 22 else (30.0 if 11 <= hour <= 16 else 42.0)

        renewable_pct = r_rec.renewable_share_pct if r_rec else default_renewable
        tariff_inr = t_rec.electricity_tariff_inr_per_kwh if t_rec else default_tariff
        carbon_gco2 = t_rec.grid_carbon_intensity_gco2_per_kwh if t_rec else default_carbon
        grid_stress = g_rec.grid_stress_pct if g_rec else default_grid

        slot = CandidateSlot(
            start_time=current,
            end_time=slot_end,
            tariff_inr_per_kwh=tariff_inr,
            carbon_intensity_gco2_per_kwh=carbon_gco2,
            renewable_share_pct=renewable_pct,
            grid_stress_pct=grid_stress,
            max_power_kw=max_power_kw
        )
        slots.append(slot)
        current = slot_end

    return slots


def _find_nearest(record_map: Dict[datetime, Any], target_time: datetime) -> Optional[Any]:
    if not record_map:
        return None
    if target_time in record_map:
        return record_map[target_time]
    
    # Find closest timestamp
    closest_key = min(record_map.keys(), key=lambda t: abs((t - target_time).total_seconds()))
    return record_map[closest_key]
