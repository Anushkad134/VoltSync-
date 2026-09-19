from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from app.core.database import Base
from datetime import datetime, timezone

class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("charging_sessions.session_id"), nullable=False, index=True)
    agent_type = Column(String, nullable=False, index=True)
    input_context = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    execution_duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('ix_agent_decisions_session_agent_created', 'session_id', 'agent_type', 'created_at'),
    )
