from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint, Index
from app.core.database import Base

class GridDemand(Base):
    __tablename__ = "grid_demand"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    region = Column(String, nullable=False)
    demand_mw = Column(Float, nullable=False)
    peak_demand_mw = Column(Float, nullable=False)
    available_capacity_mw = Column(Float, nullable=False)
    reserve_margin_mw = Column(Float, nullable=False)
    grid_stress_pct = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint('demand_mw >= 0', name='check_demand_mw'),
        CheckConstraint('peak_demand_mw >= 0', name='check_peak_demand_mw'),
        CheckConstraint('available_capacity_mw >= 0', name='check_available_capacity_mw'),
        CheckConstraint('reserve_margin_mw >= 0', name='check_reserve_margin_mw'),
        CheckConstraint('grid_stress_pct >= 0 AND grid_stress_pct <= 100', name='check_grid_stress_pct'),
        Index('ix_grid_demand_region_timestamp', 'region', 'timestamp'),
    )
