from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from app.core.database import Base

class ChargingSchedule(Base):
    __tablename__ = "charging_schedule"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("charging_sessions.session_id"), nullable=False, index=True)
    segments = Column(JSON, nullable=False)
    summary_line = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    last_updated = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index('ix_charging_schedule_session_status_updated', 'session_id', 'status', 'last_updated'),
    )
