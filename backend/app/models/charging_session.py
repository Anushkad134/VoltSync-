from sqlalchemy import Column, String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
from sqlalchemy.schema import Index

class ChargingSession(Base):
    __tablename__ = "charging_sessions"

    session_id = Column(String, primary_key=True, index=True)
    station_id = Column(String, ForeignKey("stations.station_id"), nullable=False, index=True)
    clerk_user_id = Column(String, ForeignKey("users.clerk_user_id"), nullable=False, index=True)
    arrival_time = Column(DateTime(timezone=True), nullable=False)
    ready_by = Column(DateTime(timezone=True), nullable=False, index=True)
    initial_soc_pct = Column(Float, nullable=False)
    target_soc_pct = Column(Float, nullable=False)
    battery_capacity_kwh = Column(Float, nullable=False)
    energy_required_kwh = Column(Float, nullable=False)
    max_charging_power_kw = Column(Float, nullable=False)
    estimated_duration_min = Column(Float, nullable=False)
    flexibility = Column(String, nullable=False)
    preference = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint('initial_soc_pct >= 0 AND initial_soc_pct <= 100', name='check_initial_soc_pct'),
        CheckConstraint('target_soc_pct >= 0 AND target_soc_pct <= 100', name='check_target_soc_pct'),
        CheckConstraint('target_soc_pct > initial_soc_pct', name='check_target_soc_greater_than_initial'),
        CheckConstraint('ready_by > arrival_time', name='check_ready_by_after_arrival'),
        CheckConstraint('max_charging_power_kw > 0', name='check_max_charging_power_kw'),
        CheckConstraint("flexibility IN ('Low', 'Medium', 'High')", name='check_flexibility'),
        CheckConstraint("preference IN ('Fastest', 'Cheapest', 'Greenest')", name='check_preference'),
        Index('ix_charging_sessions_station_status', 'station_id', 'status'),
    )
