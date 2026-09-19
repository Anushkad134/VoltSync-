import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.notification_log import NotificationLog
from app.services.message_builder import MessageBuilder, SUPPORTED_EVENT_TYPES
from app.services.notification_service import NotificationService, is_valid_e164
from app.integrations.twilio_client import TwilioWhatsAppClient, mask_phone_number

from app.main import app
from app.api.deps import get_db, get_current_user

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Seed mock users
    driver = User(
        clerk_user_id="user_driver_1",
        role="driver"
    )
    operator = User(
        clerk_user_id="user_operator_1",
        role="operator",
        linked_station_ids=["STATION_001"]
    )
    grid_op = User(
        clerk_user_id="user_grid_1",
        role="grid_operator",
        region="Maharashtra - Mumbai"
    )
    db.add_all([driver, operator, grid_op])

    # Seed mock station
    station = Station(
        station_id="STATION_001",
        cpo_name="Tata Power",
        govt_private="Private",
        state="Maharashtra",
        district_city_village="Mumbai",
        location="Bandra Kurla Complex",
        latitude=19.0657,
        longitude=72.8687,
        charger_types_connectors_installed="CCS2",
        charger_rating=60.0,
        connector_rating=60.0,
        no_of_connectors=4
    )
    db.add(station)

    # Seed mock charging session
    session = ChargingSession(
        session_id="SESS_NOTIF_01",
        station_id="STATION_001",
        clerk_user_id="user_driver_1",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=80.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=50.0,
        estimated_duration_min=36.0,
        flexibility="High",
        preference="Greenest",
        status="Queued"
    )
    db.add(session)
    db.commit()

    yield db
    db.close()


# ==========================================
# 1. MESSAGE BUILDER TESTS (All 11 Events)
# ==========================================

def test_message_builder_all_events():
    events = [
        ("SessionCreated", {"session_id": "S-1", "station_id": "ST-1"}, "created at Station ST-1"),
        ("ScheduleGenerated", {"start_time": "11:00", "end_time": "13:00", "renewable_share_pct": 84.0}, "expected renewable share of 84%"),
        ("ScheduleChanged", {"start_time": "11:30", "reason": "improved renewable availability"}, "Charging now starts at 11:30"),
        ("ChargingStarted", {"station_id": "ST-1", "power_level_kw": 50.0}, "Power: 50 kW"),
        ("ChargingDelayed", {"reason": "high grid demand", "start_time": "12:00", "end_time": "13:30"}, "Charging has been delayed"),
        ("ProgressUpdate", {"progress_pct": 65.0, "remaining_min": 24}, "Charging progress: 65% complete"),
        ("ReadyEarly", {}, "ready earlier than expected"),
        ("ReadyOnTime", {"ready_by": "14:00"}, "on track to be ready by 14:00"),
        ("ChargingCompleted", {"energy_delivered_kwh": 32.5, "renewable_share_pct": 81.0}, "Energy delivered: 32.5 kWh"),
        ("StationAlert", {"station_id": "ST-1", "available_connectors": 2, "total_connectors": 6}, "Available connectors: 2/6"),
        ("GridAlert", {"region": "Gujarat-West", "stress_level": "Critical", "grid_stress_pct": 97.0}, "Critical grid stress at 97%"),
    ]

    for event_type, ctx, expected_snippet in events:
        msg = MessageBuilder.build_message(event_type, ctx)
        assert msg is not None
        assert expected_snippet in msg
        assert event_type in SUPPORTED_EVENT_TYPES


# ==========================================
# 2. E.164 & RECIPIENT RESOLUTION TESTS
# ==========================================

def test_e164_validation():
    assert is_valid_e164("+919876543210") is True
    assert is_valid_e164("+14155238886") is True
    assert is_valid_e164("9876543210") is False
    assert is_valid_e164("invalid_phone") is False
    assert is_valid_e164("") is False
    assert is_valid_e164(None) is False


def test_mask_phone_number():
    assert mask_phone_number("+919876543210") == "+91******3210"
    assert mask_phone_number("123") == "***"


def test_recipient_resolution(db_session):
    # Driver session recipient
    r1 = NotificationService.resolve_recipient("SESS_NOTIF_01", "SessionCreated", db_session)
    assert is_valid_e164(r1)

    # Station alert recipient
    r2 = NotificationService.resolve_recipient(None, "StationAlert", db_session, {"station_id": "STATION_001"})
    assert is_valid_e164(r2)

    # Grid alert recipient
    r3 = NotificationService.resolve_recipient(None, "GridAlert", db_session, {"region": "Maharashtra - Mumbai"})
    assert is_valid_e164(r3)


# ==========================================
# 3. TWILIO CLIENT & MOCK INTEGRATION
# ==========================================

@patch("app.integrations.twilio_client.Client")
def test_twilio_client_success(mock_client_cls):
    mock_messages = MagicMock()
    mock_msg_instance = MagicMock()
    mock_msg_instance.sid = "SM_MOCK_123456"
    mock_msg_instance.status = "sent"
    mock_messages.create.return_value = mock_msg_instance

    mock_client_instance = MagicMock()
    mock_client_instance.messages = mock_messages
    mock_client_cls.return_value = mock_client_instance

    client = TwilioWhatsAppClient(account_sid="AC_TEST", auth_token="AUTH_TEST", from_number="+14155238886")
    res = client.send_whatsapp_message("+919876543210", "Test notification")

    assert res["delivery_status"] == "Sent"
    assert res["twilio_message_sid"] == "SM_MOCK_123456"
    assert res["error"] is None


@patch("app.integrations.twilio_client.Client")
def test_twilio_client_failure_isolation(mock_client_cls):
    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.side_effect = Exception("Twilio API unreachable")
    mock_client_cls.return_value = mock_client_instance

    client = TwilioWhatsAppClient(account_sid="AC_TEST", auth_token="AUTH_TEST")
    res = client.send_whatsapp_message("+919876543210", "Test message")

    assert res["delivery_status"] == "Failed"
    assert res["twilio_message_sid"] is None
    assert "Twilio API unreachable" in res["error"]


# ==========================================
# 4. DUPLICATE PREVENTION & RATE LIMITING
# ==========================================

@patch.object(TwilioWhatsAppClient, "send_whatsapp_message")
def test_duplicate_prevention(mock_send, db_session):
    mock_send.return_value = {"twilio_message_sid": "SM_1", "delivery_status": "Sent", "error": None}

    # 1. First notify call succeeds and creates log
    log1 = NotificationService.notify("SessionCreated", session_id="SESS_NOTIF_01", db=db_session)
    assert log1 is not None
    assert log1.delivery_status == "Sent"

    # 2. Second duplicate call for same session & event is suppressed
    log2 = NotificationService.notify("SessionCreated", session_id="SESS_NOTIF_01", db=db_session)
    assert log2 is None  # Suppressed duplicate


@patch.object(TwilioWhatsAppClient, "send_whatsapp_message")
def test_progress_update_rate_limiting(mock_send, db_session):
    mock_send.return_value = {"twilio_message_sid": "SM_PROG", "delivery_status": "Sent", "error": None}

    # 1. First progress update dispatched
    log1 = NotificationService.notify("ProgressUpdate", session_id="SESS_NOTIF_01", context={"progress_pct": 25.0}, db=db_session)
    assert log1 is not None

    # 2. Immediate second progress update is rate limited (within 15 mins)
    log2 = NotificationService.notify("ProgressUpdate", session_id="SESS_NOTIF_01", context={"progress_pct": 30.0}, db=db_session)
    assert log2 is None  # Throttled


# ==========================================
# 5. FAILURE ISOLATION IN SERVICE
# ==========================================

@patch.object(TwilioWhatsAppClient, "send_whatsapp_message")
def test_notification_failure_does_not_raise(mock_send, db_session):
    mock_send.side_effect = Exception("Fatal network error")

    # Should not raise exception
    log = NotificationService.notify("ChargingStarted", session_id="SESS_NOTIF_01", db=db_session)
    assert log is not None
    assert log.delivery_status == "Failed"


# ==========================================
# 6. API ENDPOINTS & RBAC
# ==========================================

@patch.object(TwilioWhatsAppClient, "send_whatsapp_message")
def test_whatsapp_test_endpoint(mock_send, db_session):
    mock_send.return_value = {"twilio_message_sid": "SM_TEST_API", "delivery_status": "Sent", "error": None}
    client = TestClient(app)

    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_1").first()
    operator = db_session.query(User).filter(User.clerk_user_id == "user_operator_1").first()

    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Driver attempting test endpoint -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: driver
    res_driver = client.post("/api/v1/whatsapp/test", json={"to_phone": "+919876543210"})
    assert res_driver.status_code == 403

    # 2. Operator attempting test endpoint -> 200 OK
    app.dependency_overrides[get_current_user] = lambda: operator
    res_op = client.post("/api/v1/whatsapp/test", json={"to_phone": "+919876543210", "message": "Custom test"})
    assert res_op.status_code == 200
    assert res_op.json()["data"]["status"] == "Sent"
    assert res_op.json()["data"]["twilio_message_sid"] == "SM_TEST_API"

    app.dependency_overrides.clear()


@patch.object(TwilioWhatsAppClient, "send_whatsapp_message")
def test_notifications_history_endpoint(mock_send, db_session):
    mock_send.return_value = {"twilio_message_sid": "SM_HIST", "delivery_status": "Sent", "error": None}
    client = TestClient(app)

    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_1").first()
    operator = db_session.query(User).filter(User.clerk_user_id == "user_operator_1").first()

    # Create notifications
    NotificationService.notify("ChargingStarted", session_id="SESS_NOTIF_01", db=db_session)
    NotificationService.notify("StationAlert", context={"station_id": "STATION_001"}, db=db_session)

    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Driver queries history -> only sees session notification
    app.dependency_overrides[get_current_user] = lambda: driver
    res_d = client.get("/api/v1/notifications")
    assert res_d.status_code == 200
    data_d = res_d.json()["data"]
    assert len(data_d) == 1
    assert data_d[0]["event_type"] == "ChargingStarted"

    # 2. Operator queries history -> sees station notification and station alert
    app.dependency_overrides[get_current_user] = lambda: operator
    res_op = client.get("/api/v1/notifications")
    assert res_op.status_code == 200
    data_op = res_op.json()["data"]
    assert len(data_op) >= 1

    app.dependency_overrides.clear()
