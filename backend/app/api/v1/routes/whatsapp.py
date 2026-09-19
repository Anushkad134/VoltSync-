from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, require_operator
from app.schemas.notification import WhatsAppTestRequest, WhatsAppTestResponse
from app.schemas.common import DataResponse
from app.services.notification_service import NotificationService

router = APIRouter()

@router.post("/test", response_model=DataResponse[WhatsAppTestResponse])
def test_whatsapp(
    payload: Optional[WhatsAppTestRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator)
):
    to_phone = payload.to_phone if payload and payload.to_phone else "+919876543210"
    custom_msg = payload.message if payload and payload.message else None

    try:
        result = NotificationService.send_test_notification(to_phone=to_phone, message=custom_msg, db=db)
        return DataResponse(data=WhatsAppTestResponse(
            status=result.get("delivery_status", "Sent"),
            twilio_message_sid=result.get("twilio_message_sid"),
            delivery_status=result.get("delivery_status", "Sent"),
            message="Test WhatsApp notification dispatched successfully."
        ))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_PHONE_NUMBER", "message": str(e), "status_code": 400}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "NOTIFICATION_SERVICE_ERROR", "message": str(e), "status_code": 503}
        )

@router.post("/webhook")
async def whatsapp_webhook():
    """Handles incoming WhatsApp messages from Twilio Sandbox."""
    return {"status": "success", "message": "Webhook received"}

@router.post("/status")
async def whatsapp_status_callback():
    """Handles message delivery status updates from Twilio."""
    return {"status": "success", "message": "Status callback received"}
