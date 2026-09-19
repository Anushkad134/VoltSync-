import pytest
from fastapi.testclient import TestClient
from fastapi import Request, HTTPException
from app.main import app
from app.models.user import User
from app.api.deps import get_current_user

# Mock dependency for routes testing
def mock_get_current_user(request: Request) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"error_code": "AUTHENTICATION_REQUIRED", "message": "Valid authentication is required.", "status_code": 401})
    token = auth_header.split(" ")[1]
    if token == "invalid":
        raise HTTPException(status_code=401, detail={"error_code": "INVALID_AUTH_TOKEN", "message": "The authentication token is invalid.", "status_code": 401})
        
    role = request.headers.get("x-mock-role", "driver")
    return User(
        clerk_user_id="mock_user_123",
        role=role,
        region="Ahmedabad" if role == "grid_operator" else None,
        linked_station_ids=["ST-1"] if role == "operator" else []
    )

@pytest.fixture(autouse=True)
def apply_overrides(monkeypatch):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    from app.core.database import SessionLocal, Base, engine
    from app.models.station import Station
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(Station).filter(Station.station_id == "ST-1").first():
        db.add(Station(
            station_id="ST-1",
            cpo_name="Tata Power",
            govt_private="Private",
            state="Gujarat",
            district_city_village="Ahmedabad",
            location="SG Highway",
            latitude=23.0225,
            longitude=72.5714,
            charger_types_connectors_installed="CCS2",
            charger_rating=60.0,
            connector_rating=60.0,
            no_of_connectors=4
        ))
        db.commit()
    db.close()

    def mock_check_session_access(session_id: str, user: User, db):
        if session_id == "invalid_id" or session_id == "S-1":
            class MockSession:
                session_id = "S-1"
                clerk_user_id = "mock_user_123"
                station_id = "ST-1"
                arrival_time = "2026-09-12T10:00:00"
                ready_by = "2026-09-12T14:00:00"
                initial_soc_pct = 20
                target_soc_pct = 80
                battery_capacity_kwh = 60
                energy_required_kwh = 36
                max_charging_power_kw = 50
                estimated_duration_min = 43.2
                flexibility = "High"
                preference = "Greenest"
                status = "Queued"
                created_at = "2026-09-12T09:00:00"
                updated_at = "2026-09-12T09:00:00"
            return MockSession()
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND", "message": "Session not found.", "status_code": 404})
        
    from app.api import deps
    monkeypatch.setattr(deps, "check_session_access", mock_check_session_access)
    
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_auth_me():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "driver"

def test_auth_missing():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTHENTICATION_REQUIRED"

def test_auth_invalid():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_AUTH_TOKEN"

def test_stations_list():
    response = client.get("/api/v1/stations", headers={"Authorization": "Bearer valid_token", "x-mock-role": "driver"})
    assert response.status_code == 200
    assert "pagination" in response.json()

def test_station_get_not_found():
    response = client.get("/api/v1/stations/invalid_id", headers={"Authorization": "Bearer valid_token", "x-mock-role": "driver"})
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

def test_session_create_valid():
    response = client.post("/api/v1/sessions", headers={"Authorization": "Bearer valid", "x-mock-role": "driver"}, json={
        "station_id": "ST-1",
        "arrival_time": "2026-09-12T10:00:00",
        "ready_by": "2026-09-12T14:00:00",
        "initial_soc_pct": 20,
        "target_soc_pct": 80,
        "battery_capacity_kwh": 60,
        "max_charging_power_kw": 50,
        "flexibility": "High",
        "preference": "Greenest"
    })
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "Queued"

def test_session_create_validation_error():
    response = client.post("/api/v1/sessions", headers={"Authorization": "Bearer valid", "x-mock-role": "driver"}, json={
        "station_id": "ST-1",
        "arrival_time": "2026-09-12T10:00:00",
        "ready_by": "2026-09-12T14:00:00",
        "initial_soc_pct": 90, # initial > target
        "target_soc_pct": 80,
        "battery_capacity_kwh": 60,
        "max_charging_power_kw": 50,
        "flexibility": "High",
        "preference": "Greenest"
    })
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert "field_errors" in response.json()

def test_session_role_forbidden():
    response = client.post("/api/v1/sessions", headers={"Authorization": "Bearer valid", "x-mock-role": "operator"}, json={
        "station_id": "ST-1",
        "arrival_time": "2026-09-12T10:00:00",
        "ready_by": "2026-09-12T14:00:00",
        "initial_soc_pct": 20,
        "target_soc_pct": 80,
        "battery_capacity_kwh": 60,
        "max_charging_power_kw": 50,
        "flexibility": "High",
        "preference": "Greenest"
    })
    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"

def test_grid_status_forbidden():
    response = client.get("/api/v1/grid/status", headers={"Authorization": "Bearer valid", "x-mock-role": "driver"})
    assert response.status_code == 403

def test_grid_status_allowed():
    response = client.get("/api/v1/grid/status", headers={"Authorization": "Bearer valid", "x-mock-role": "grid_operator"})
    assert response.status_code == 404 # Stub returns 404

def test_operator_dashboard():
    response = client.get("/api/v1/operator/dashboard", headers={"Authorization": "Bearer valid", "x-mock-role": "operator"})
    assert response.status_code == 200

def test_schedule_unavailable(monkeypatch):
    from app.services.scheduling_service import SchedulingService
    def mock_fail(*args, **kwargs):
        raise HTTPException(
            status_code=503,
            detail={"error_code": "SCHEDULING_SERVICE_UNAVAILABLE", "message": "Charging schedule could not be generated.", "status_code": 503}
        )
    monkeypatch.setattr(SchedulingService, "generate_and_persist_schedule", mock_fail)
    response = client.post("/api/v1/sessions/S-1/schedule", headers={"Authorization": "Bearer valid", "x-mock-role": "driver"})
    assert response.status_code == 503
    assert response.json()["error_code"] == "SCHEDULING_SERVICE_UNAVAILABLE"
