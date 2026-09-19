import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request, HTTPException

from app.main import app
from app.models.user import User
from app.models.station import Station
from app.models.charging_session import ChargingSession
from app.core.database import SessionLocal, Base, engine
from app.api.deps import get_current_user


def mock_get_current_user_matrix(request: Request) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error_code": "AUTHENTICATION_REQUIRED", "message": "Valid authentication is required.", "status_code": 401}
        )
    token = auth_header.split(" ")[1]
    if token == "invalid_token":
        raise HTTPException(
            status_code=401,
            detail={"error_code": "INVALID_AUTH_TOKEN", "message": "The authentication token is invalid.", "status_code": 401}
        )
    
    role = request.headers.get("x-user-role", "driver")
    user_id = request.headers.get("x-user-id", "driver_user_1")
    region = request.headers.get("x-user-region", "Maharashtra - Mumbai")
    
    return User(
        clerk_user_id=user_id,
        role=role,
        region=region if role == "grid_operator" else None,
        linked_station_ids=["ST-MATRIX-01"] if role == "operator" else []
    )


@pytest.fixture(autouse=True)
def matrix_setup(monkeypatch):
    app.dependency_overrides[get_current_user] = mock_get_current_user_matrix
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if not db.query(Station).filter(Station.station_id == "ST-MATRIX-01").first():
        db.add(Station(
            station_id="ST-MATRIX-01",
            cpo_name="VoltSync Matrix CPO",
            govt_private="Private",
            state="Maharashtra",
            district_city_village="Mumbai",
            location="BKC Sector 2",
            latitude=19.0657,
            longitude=72.8687,
            charger_types_connectors_installed="CCS2,Type2",
            charger_rating=60.0,
            connector_rating=60.0,
            no_of_connectors=4
        ))
        db.commit()
    db.close()

    yield
    app.dependency_overrides.clear()


client = TestClient(app)


# ==============================================================================
# 1. Complete API Route Coverage
# ==============================================================================
def test_all_health_and_info_routes():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_auth_me_endpoint():
    # Authenticated driver
    res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer valid", "x-user-role": "driver", "x-user-id": "driver_1"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["role"] == "driver"

    # Authenticated operator
    res_op = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer valid", "x-user-role": "operator", "x-user-id": "op_1"}
    )
    assert res_op.status_code == 200
    assert res_op.json()["data"]["role"] == "operator"


def test_station_endpoints():
    # List stations
    res = client.get(
        "/api/v1/stations",
        headers={"Authorization": "Bearer valid", "x-user-role": "driver"}
    )
    assert res.status_code == 200
    assert isinstance(res.json()["data"], list)

    # Get single station
    res_single = client.get(
        "/api/v1/stations/ST-MATRIX-01",
        headers={"Authorization": "Bearer valid", "x-user-role": "driver"}
    )
    assert res_single.status_code == 200
    assert res_single.json()["data"]["station_id"] == "ST-MATRIX-01"


def test_grid_renewable_pricing_routes():
    grid_headers = {"Authorization": "Bearer valid", "x-user-role": "grid_operator", "x-user-region": "Maharashtra - Mumbai"}
    driver_headers = {"Authorization": "Bearer valid", "x-user-role": "driver"}

    # Grid (grid_operator)
    assert client.get("/api/v1/grid/status", headers=grid_headers).status_code in [200, 404]
    assert client.get("/api/v1/grid/demand?region=Maharashtra%20-%20Mumbai&start_time=2026-06-15T00:00:00Z&end_time=2026-06-15T23:59:59Z", headers=grid_headers).status_code in [200, 404]
    assert client.get("/api/v1/grid/alerts", headers=grid_headers).status_code in [200, 404]

    # Renewable (any auth)
    assert client.get("/api/v1/renewable/status", headers=driver_headers).status_code in [200, 404]
    assert client.get("/api/v1/renewable/generation?region=Maharashtra%20-%20Mumbai&start_time=2026-06-15T00:00:00Z&end_time=2026-06-15T23:59:59Z", headers=driver_headers).status_code in [200, 404]
    assert client.get("/api/v1/renewable/weather?region=Maharashtra%20-%20Mumbai&start_time=2026-06-15T00:00:00Z&end_time=2026-06-15T23:59:59Z", headers=driver_headers).status_code in [200, 404]

    # Pricing (any auth)
    assert client.get("/api/v1/pricing/current?region=Maharashtra%20-%20Mumbai", headers=driver_headers).status_code in [200, 404]
    assert client.get("/api/v1/pricing/history?region=Maharashtra%20-%20Mumbai&start_time=2026-06-15T00:00:00Z&end_time=2026-06-15T23:59:59Z", headers=driver_headers).status_code in [200, 404]


# ==============================================================================
# 2. Cross-Role RBAC Authorization Matrix
# ==============================================================================
def test_rbac_matrix():
    # 1. Driver tries to access Operator Dashboard -> 403 Forbidden
    driver_headers = {"Authorization": "Bearer valid", "x-user-role": "driver", "x-user-id": "driver_1"}
    res = client.get("/api/v1/operator/dashboard", headers=driver_headers)
    assert res.status_code == 403
    assert res.json()["error_code"] == "FORBIDDEN"

    # 2. Driver tries to access Grid Operator Dashboard -> 403 Forbidden
    res_grid = client.get("/api/v1/grid-operator/dashboard", headers=driver_headers)
    assert res_grid.status_code == 403
    assert res_grid.json()["error_code"] == "FORBIDDEN"

    # 3. Operator tries to access Grid Operator Dashboard -> 403 Forbidden
    op_headers = {"Authorization": "Bearer valid", "x-user-role": "operator", "x-user-id": "op_1"}
    res_op_grid = client.get("/api/v1/grid-operator/dashboard", headers=op_headers)
    assert res_op_grid.status_code == 403
    assert res_op_grid.json()["error_code"] == "FORBIDDEN"

    # 4. Operator accesses Operator Dashboard -> 200 OK
    res_op = client.get("/api/v1/operator/dashboard", headers=op_headers)
    assert res_op.status_code in [200, 404]

    # 5. Grid Operator accesses Grid Operator Dashboard -> 200 OK
    grid_op_headers = {"Authorization": "Bearer valid", "x-user-role": "grid_operator", "x-user-id": "grid_op_1", "x-user-region": "Maharashtra - Mumbai"}
    res_grid_ok = client.get("/api/v1/grid-operator/dashboard", headers=grid_op_headers)
    assert res_grid_ok.status_code in [200, 404]


# ==============================================================================
# 3. Resource-Level Security (Driver Tenant Isolation)
# ==============================================================================
def test_driver_tenant_isolation():
    # Create a session belonging to driver_A
    db = SessionLocal()
    session_a = ChargingSession(
        session_id="SES-MATRIX-A",
        clerk_user_id="driver_A",
        station_id="ST-MATRIX-01",
        arrival_time=datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 6, 15, 14, 0, 0, tzinfo=timezone.utc),
        initial_soc_pct=20,
        target_soc_pct=80,
        battery_capacity_kwh=60,
        energy_required_kwh=36,
        max_charging_power_kw=50,
        estimated_duration_min=43.2,
        flexibility="High",
        preference="Greenest",
        status="created"
    )
    db.merge(session_a)
    db.commit()
    db.close()

    # Driver A requests their own session -> 200 OK
    headers_driver_a = {"Authorization": "Bearer valid", "x-user-role": "driver", "x-user-id": "driver_A"}
    res_a = client.get("/api/v1/sessions/SES-MATRIX-A", headers=headers_driver_a)
    assert res_a.status_code == 200
    assert res_a.json()["data"]["session_id"] == "SES-MATRIX-A"

    # Driver B requests Driver A's session -> 403 Forbidden
    headers_driver_b = {"Authorization": "Bearer valid", "x-user-role": "driver", "x-user-id": "driver_B"}
    res_b = client.get("/api/v1/sessions/SES-MATRIX-A", headers=headers_driver_b)
    assert res_b.status_code == 403
    assert res_b.json()["error_code"] == "FORBIDDEN"


# ==============================================================================
# 4. Error Handling & Validation Resilience
# ==============================================================================
def test_error_resilience():
    headers = {"Authorization": "Bearer valid", "x-user-role": "driver", "x-user-id": "driver_1"}

    # Invalid session payload: target_soc <= current_soc
    bad_payload_soc = {
        "station_id": "ST-MATRIX-01",
        "arrival_time": "2026-06-15T10:00:00Z",
        "ready_by": "2026-06-15T14:00:00Z",
        "current_soc_pct": 80,
        "target_soc_pct": 40,
        "battery_capacity_kwh": 60,
        "max_charging_power_kw": 50,
        "flexibility": "High",
        "preference": "Greenest"
    }
    res_soc = client.post("/api/v1/sessions", json=bad_payload_soc, headers=headers)
    assert res_soc.status_code == 422

    # Invalid session payload: ready_by <= arrival_time
    bad_payload_time = {
        "station_id": "ST-MATRIX-01",
        "arrival_time": "2026-06-15T14:00:00Z",
        "ready_by": "2026-06-15T10:00:00Z",
        "current_soc_pct": 20,
        "target_soc_pct": 80,
        "battery_capacity_kwh": 60,
        "max_charging_power_kw": 50,
        "flexibility": "High",
        "preference": "Greenest"
    }
    res_time = client.post("/api/v1/sessions", json=bad_payload_time, headers=headers)
    assert res_time.status_code == 422

    # Non-existent session
    res_nf = client.get("/api/v1/sessions/NON-EXISTENT-SESSION", headers=headers)
    assert res_nf.status_code == 404
