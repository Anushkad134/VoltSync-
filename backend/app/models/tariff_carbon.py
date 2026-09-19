from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint, Index
from app.core.database import Base

class TariffCarbon(Base):
    __tablename__ = "tariff_carbon"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    region = Column(String, nullable=False)
    tariff_period = Column(String, nullable=False)
    electricity_tariff_inr_per_kwh = Column(Float, nullable=False)
    renewable_share_pct = Column(Float, nullable=False)
    grid_carbon_intensity_gco2_per_kwh = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint('electricity_tariff_inr_per_kwh >= 0', name='check_tariff'),
        CheckConstraint('renewable_share_pct >= 0 AND renewable_share_pct <= 100', name='check_tariff_renewable_share'),
        CheckConstraint('grid_carbon_intensity_gco2_per_kwh >= 0', name='check_carbon_intensity'),
        Index('ix_tariff_carbon_region_timestamp', 'region', 'timestamp'),
    )
