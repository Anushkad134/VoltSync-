from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    session_id: Optional[str] = None
    event_type: str
    message_body: str
    twilio_message_sid: Optional[str] = None
    delivery_status: str
    timestamp: datetime

    model_config = {"from_attributes": True}

class WhatsAppTestRequest(BaseModel):
    to_phone: str = Field(..., description="Recipient phone number in E.164 format (e.g. +919876543210)")
    message: Optional[str] = Field(None, description="Optional custom test message")

class WhatsAppTestResponse(BaseModel):
    status: str
    twilio_message_sid: Optional[str] = None
    delivery_status: str
    message: str
