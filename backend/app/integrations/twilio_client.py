import logging
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.core.config import settings

logger = logging.getLogger("voltsync.integrations.twilio")

def mask_phone_number(phone: str) -> str:
    """Masks phone numbers for safe logging (e.g. +91******3210)."""
    if not phone or len(phone) < 6:
        return "***"
    prefix = phone[:3]
    suffix = phone[-4:]
    return f"{prefix}******{suffix}"

class TwilioWhatsAppClient:
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_number = from_number or settings.TWILIO_WHATSAPP_FROM_NUMBER
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                raise ValueError("Twilio credentials (ACCOUNT_SID or AUTH_TOKEN) are missing.")
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_whatsapp_message(self, to_phone: str, message_body: str) -> Dict[str, Any]:
        """
        Sends a WhatsApp message using Twilio.
        Returns a dictionary with message SID and delivery status.
        Never lets Twilio exceptions crash the application.
        """
        masked_to = mask_phone_number(to_phone)
        try:
            if not to_phone:
                return {
                    "twilio_message_sid": None,
                    "delivery_status": "Failed",
                    "error": "Recipient phone number is empty."
                }

            # Format WhatsApp URIs
            formatted_to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            from_num = self.from_number or "+14155238886"
            formatted_from = from_num if from_num.startswith("whatsapp:") else f"whatsapp:{from_num}"

            logger.info(f"Dispatching WhatsApp message to {masked_to}")

            message = self.client.messages.create(
                body=message_body,
                from_=formatted_from,
                to=formatted_to
            )

            status_mapping = {
                "queued": "Pending",
                "sending": "Pending",
                "sent": "Sent",
                "delivered": "Delivered",
                "read": "Delivered",
                "failed": "Failed",
                "undelivered": "Failed"
            }
            mapped_status = status_mapping.get(message.status, "Sent")

            return {
                "twilio_message_sid": message.sid,
                "delivery_status": mapped_status,
                "error": None
            }

        except TwilioRestException as e:
            logger.error(f"Twilio REST error sending WhatsApp to {masked_to}: {e.msg}")
            return {
                "twilio_message_sid": None,
                "delivery_status": "Failed",
                "error": str(e.msg)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp to {masked_to}: {str(e)}")
            return {
                "twilio_message_sid": None,
                "delivery_status": "Failed",
                "error": str(e)
            }
