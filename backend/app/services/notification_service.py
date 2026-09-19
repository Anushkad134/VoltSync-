import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.notification_log import NotificationLog
from app.models.charging_session import ChargingSession
from app.models.user import User
from app.services.message_builder import MessageBuilder, SUPPORTED_EVENT_TYPES
from app.integrations.twilio_client import TwilioWhatsAppClient

logger = logging.getLogger("voltsync.services.notification")

E164_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")

def is_valid_e164(phone: Optional[str]) -> bool:
    if not phone:
        return False
    return bool(E164_REGEX.match(phone.strip()))

class NotificationService:
    @staticmethod
    def resolve_recipient(
        session_id: Optional[str],
        event_type: str,
        db: Session,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Resolves trusted E.164 recipient phone number based on backend user/session data.
        """
        ctx = context or {}

        # If explicit trusted recipient passed (e.g. from authenticated test endpoint)
        if "to_phone" in ctx and is_valid_e164(ctx["to_phone"]):
            return ctx["to_phone"].strip()

        # Session-based recipient resolution
        if session_id:
            session = db.query(ChargingSession).filter(ChargingSession.session_id == session_id).first()
            if session:
                user = db.query(User).filter(User.clerk_user_id == session.clerk_user_id).first()
                if user and hasattr(user, "phone_number") and is_valid_e164(getattr(user, "phone_number", None)):
                    return getattr(user, "phone_number").strip()
                # Default driver E.164 test number if user has no explicit phone stored
                return "+919909059204"

        # Station Alert -> Operator recipient
        if event_type == "StationAlert":
            station_id = ctx.get("station_id")
            if station_id:
                # Find operator assigned to this station
                operator = db.query(User).filter(User.role == "operator").first()
                if operator and hasattr(operator, "phone_number") and is_valid_e164(getattr(operator, "phone_number", None)):
                    return getattr(operator, "phone_number").strip()
            return "+919876543211"

        # Grid Alert -> Grid Operator recipient
        if event_type == "GridAlert":
            region = ctx.get("region")
            if region:
                grid_op = db.query(User).filter(User.role == "grid_operator", User.region == region).first()
                if grid_op and hasattr(grid_op, "phone_number") and is_valid_e164(getattr(grid_op, "phone_number", None)):
                    return getattr(grid_op, "phone_number").strip()
            return "+919876543212"

        return "+919876543210"

    @staticmethod
    def is_duplicate_or_rate_limited(session_id: Optional[str], event_type: str, db: Session) -> bool:
        """
        Checks if the event is a duplicate or rate-limited.
        """
        if not session_id:
            return False

        if event_type == "ProgressUpdate":
            # Check rate limiting
            min_interval = getattr(settings, "PROGRESS_NOTIFICATION_INTERVAL_MINUTES", 15)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=min_interval)
            
            recent_progress = db.query(NotificationLog).filter(
                NotificationLog.session_id == session_id,
                NotificationLog.event_type == "ProgressUpdate",
                NotificationLog.timestamp >= cutoff
            ).first()
            
            if recent_progress:
                logger.info(f"ProgressUpdate for session {session_id} throttled (interval: {min_interval}m).")
                return True
            return False

        # One-time events: avoid duplicates if already successfully queued/sent/delivered
        one_time_events = {
            "SessionCreated",
            "ScheduleGenerated",
            "ChargingCompleted",
            "ReadyEarly",
            "ReadyOnTime"
        }
        if event_type in one_time_events:
            existing = db.query(NotificationLog).filter(
                NotificationLog.session_id == session_id,
                NotificationLog.event_type == event_type,
                NotificationLog.delivery_status.in_(["Pending", "Sent", "Delivered"])
            ).first()
            if existing:
                logger.info(f"Duplicate {event_type} notification for session {session_id} suppressed.")
                return True

        return False

    @staticmethod
    def notify(
        event_type: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Optional[NotificationLog]:
        """
        Main entry point to dispatch notifications.
        Notification failure will never raise an exception or fail caller transactions.
        """
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            ctx = dict(context or {})
            if session_id and "session_id" not in ctx:
                ctx["session_id"] = session_id

            # 1. Check duplicate / rate limit
            if NotificationService.is_duplicate_or_rate_limited(session_id, event_type, db):
                return None

            # 2. Build message
            message_body = MessageBuilder.build_message(event_type, ctx)

            # 3. Resolve recipient
            recipient = NotificationService.resolve_recipient(session_id, event_type, db, ctx)

            # 4. Dispatch via Twilio Client
            twilio_client = TwilioWhatsAppClient()
            result = twilio_client.send_whatsapp_message(to_phone=recipient, message_body=message_body)

            # 5. Persist to notifications_log
            log_entry = NotificationLog(
                session_id=session_id,
                event_type=event_type,
                message_body=message_body,
                twilio_message_sid=result.get("twilio_message_sid"),
                delivery_status=result.get("delivery_status", "Sent"),
                timestamp=datetime.now(timezone.utc)
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry

        except Exception as e:
            logger.error(f"Notification dispatch failed for event {event_type}: {str(e)}")
            try:
                # Attempt to log failed notification
                log_entry = NotificationLog(
                    session_id=session_id,
                    event_type=event_type,
                    message_body=MessageBuilder.build_message(event_type, context),
                    twilio_message_sid=None,
                    delivery_status="Failed",
                    timestamp=datetime.now(timezone.utc)
                )
                db.add(log_entry)
                db.commit()
                return log_entry
            except Exception:
                db.rollback()
                return None
        finally:
            if owns_db:
                db.close()

    @staticmethod
    def send_test_notification(
        to_phone: str,
        message: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Sends a test WhatsApp message for the test endpoint.
        """
        if not is_valid_e164(to_phone):
            raise ValueError(f"Phone number '{to_phone}' is not a valid E.164 format (e.g. +919876543210).")

        test_msg = message or "⚡ VoltSync WhatsApp Integration Test: Twilio WhatsApp sandbox is operational."
        
        twilio_client = TwilioWhatsAppClient()
        result = twilio_client.send_whatsapp_message(to_phone=to_phone, message_body=test_msg)

        # Log test notification
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            log_entry = NotificationLog(
                session_id=None,
                event_type="StationAlert",
                message_body=test_msg,
                twilio_message_sid=result.get("twilio_message_sid"),
                delivery_status=result.get("delivery_status", "Sent"),
                timestamp=datetime.now(timezone.utc)
            )
            db.add(log_entry)
            db.commit()
        finally:
            if owns_db:
                db.close()

        return result
