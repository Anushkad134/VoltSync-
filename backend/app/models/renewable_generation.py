from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint, Index
from app.core.database import Base

class RenewableGeneration(Base):
    __tablename__ = "renewable_generation"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    region = Column(String, nullable=False)
    solar_generation_mw = Column(Float, nullable=False)
    wind_generation_mw = Column(Float, nullable=False)
    hydro_generation_mw = Column(Float, nullable=False)
    other_renewable_mw = Column(Float, nullable=False)
    total_renewable_mw = Column(Float, nullable=False)
    renewable_share_pct = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint('solar_generation_mw >= 0', name='check_solar_mw'),
        CheckConstraint('wind_generation_mw >= 0', name='check_wind_mw'),
        CheckConstraint('hydro_generation_mw >= 0', name='check_hydro_mw'),
        CheckConstraint('other_renewable_mw >= 0', name='check_other_mw'),
        CheckConstraint('total_renewable_mw >= 0', name='check_total_mw'),
        CheckConstraint('renewable_share_pct >= 0 AND renewable_share_pct <= 100', name='check_renewable_share_pct'),
        Index('ix_renewable_generation_region_timestamp', 'region', 'timestamp'),
    )
