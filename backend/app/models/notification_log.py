from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from app.core.database import Base

class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("charging_sessions.session_id"), nullable=True, index=True)
    event_type = Column(String, nullable=False)
    message_body = Column(Text, nullable=False)
    twilio_message_sid = Column(String, nullable=True)
    delivery_status = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('ix_notifications_log_session_time_event', 'session_id', 'timestamp', 'event_type'),
    )
