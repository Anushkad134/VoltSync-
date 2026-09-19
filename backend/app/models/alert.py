from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from app.core.database import Base
from datetime import datetime, timezone

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    region_or_station_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_alerts_type_region_severity_created_resolved', 'type', 'region_or_station_id', 'severity', 'created_at', 'resolved_at'),
    )
