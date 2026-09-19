from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.tariff_carbon import TariffCarbon

class PricingService:
    @staticmethod
    def get_current_price(region: str, timestamp: Optional[datetime], db: Session) -> Optional[TariffCarbon]:
        """
        Retrieves the pricing record for a region and timestamp (or closest available).
        """
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Look for exact or closest prior timestamp
        rec = db.query(TariffCarbon).filter(
            TariffCarbon.region == region,
            TariffCarbon.timestamp <= ts
        ).order_by(TariffCarbon.timestamp.desc()).first()

        if not rec:
            rec = db.query(TariffCarbon).filter(
                TariffCarbon.region == region
            ).order_by(TariffCarbon.timestamp.asc()).first()

        return rec

    @staticmethod
    def get_price_history(
        region: str,
        start_time: datetime,
        end_time: datetime,
        db: Session
    ) -> List[TariffCarbon]:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        return db.query(TariffCarbon).filter(
            TariffCarbon.region == region,
            TariffCarbon.timestamp >= start_time,
            TariffCarbon.timestamp <= end_time
        ).order_by(TariffCarbon.timestamp.asc()).all()

    @staticmethod
    def calculate_session_cost(energy_kwh: float, tariff_inr_per_kwh: float) -> float:
        """
        Calculates session cost in INR: Energy (kWh) * Tariff (INR/kWh).
        """
        return round(max(0.0, energy_kwh) * max(0.0, tariff_inr_per_kwh), 2)

    @staticmethod
    def calculate_carbon_emission(energy_kwh: float, carbon_intensity_gco2_per_kwh: float) -> float:
        """
        Calculates carbon emission in grams CO2: Energy (kWh) * Carbon Intensity (gCO2/kWh).
        """
        return round(max(0.0, energy_kwh) * max(0.0, carbon_intensity_gco2_per_kwh), 2)
