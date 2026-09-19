import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.charging_schedule import ChargingSchedule
from app.models.agent_decision import AgentDecision
from app.models.renewable_generation import RenewableGeneration
from app.models.tariff_carbon import TariffCarbon
from app.models.grid_demand import GridDemand

from app.orchestrator.candidate_generator import generate_candidate_slots
from app.orchestrator.constraint_validator import (
    validate_agent_outputs,
    validate_feasibility,
    SchedulingValidationError
)
from app.orchestrator.scoring_engine import score_candidate_slots
from app.orchestrator.schedule_builder import build_schedule_segments
from app.orchestrator.orchestrator import Orchestrator
from app.services.scheduling_service import SchedulingService

from app.main import app
from app.api.deps import get_db, get_current_user

from sqlalchemy.pool import StaticPool

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

    # Seed mock user
    user = User(
        clerk_user_id="user_driver_123",
        role="driver"
    )
    db.add(user)

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

    # Seed region dataset (Renewable, Tariff, Grid)
    now = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
    region = "Maharashtra - Mumbai"

    for i in range(16):  # 4 hours in 15-min intervals
        t = now + timedelta(minutes=15 * i)
        # Solar peak around noon (slots 8-12)
        ren_pct = 85.0 if 6 <= i <= 10 else 25.0
        tariff = 6.0 if 6 <= i <= 10 else 10.0
        carbon = 300.0 if 6 <= i <= 10 else 700.0
        grid_stress = 80.0 if i >= 12 else 35.0

        db.add(RenewableGeneration(
            timestamp=t,
            region=region,
            solar_generation_mw=500.0 if 6 <= i <= 10 else 50.0,
            wind_generation_mw=100.0,
            hydro_generation_mw=50.0,
            other_renewable_mw=10.0,
            total_renewable_mw=660.0 if 6 <= i <= 10 else 210.0,
            renewable_share_pct=ren_pct
        ))
        db.add(TariffCarbon(
            timestamp=t,
            region=region,
            tariff_period="Solar-Peak" if 6 <= i <= 10 else "Normal",
            electricity_tariff_inr_per_kwh=tariff,
            renewable_share_pct=ren_pct,
            grid_carbon_intensity_gco2_per_kwh=carbon
        ))
        db.add(GridDemand(
            timestamp=t,
            region=region,
            demand_mw=1200.0,
            peak_demand_mw=1500.0,
            available_capacity_mw=1800.0,
            reserve_margin_mw=600.0,
            grid_stress_pct=grid_stress
        ))

    db.commit()

    yield db
    db.close()


@pytest.fixture
def mock_agent_outputs():
    return {
        "driver": {
            "session_id": "SESSION_001",
            "energy_required_kwh": 30.0,
            "estimated_duration_min": 60,
            "urgency": "Medium",
            "flexibility": "High",
            "preference": "Greenest",
            "available_window_start": "2026-01-10T10:00:00Z",
            "available_window_end": "2026-01-10T14:00:00Z",
            "reason": "Driver needs 30 kWh before 14:00."
        },
        "renewable": {
            "session_id": "SESSION_001",
            "green_windows": [
                {
                    "start_time": "2026-01-10T11:30:00Z",
                    "end_time": "2026-01-10T12:30:00Z",
                    "renewable_share_pct": 85.0,
                    "confidence": 0.95
                }
            ],
            "greenest_window": {
                "start_time": "2026-01-10T11:30:00Z",
                "end_time": "2026-01-10T12:30:00Z",
                "renewable_share_pct": 85.0
            },
            "forecast_confidence": 0.95,
            "reason": "Solar peak predicted 11:30-12:30."
        },
        "grid": {
            "session_id": "SESSION_001",
            "grid_stress": "Low",
            "grid_stress_pct": 35.0,
            "station_load_classification": "Normal",
            "recommended_action": "Standard charging",
            "urgency_override": False,
            "reason": "Low stress on local grid."
        },
        "cost_carbon": {
            "session_id": "SESSION_001",
            "candidate_windows": [
                {
                    "start_time": "2026-01-10T11:30:00Z",
                    "end_time": "2026-01-10T12:30:00Z",
                    "cost_inr": 180.0,
                    "carbon_intensity_gco2_per_kwh": 300.0,
                    "co2_g": 9000.0
                }
            ],
            "cheapest_window": {
                "start_time": "2026-01-10T11:30:00Z",
                "end_time": "2026-01-10T12:30:00Z"
            },
            "lowest_carbon_window": {
                "start_time": "2026-01-10T11:30:00Z",
                "end_time": "2026-01-10T12:30:00Z"
            },
            "tradeoff_summary": "Lowest cost and carbon coincide at solar peak."
        }
    }


# ==========================================
# 1. HARD CONSTRAINT TESTS
# ==========================================

def test_hard_constraint_infeasible_power_and_time():
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 10, 30, tzinfo=timezone.utc)
    
    # 60 kWh required in 30 mins at 20 kW max power is physically impossible (max possible is 10 kWh)
    is_feasible, reason = validate_feasibility(
        arrival_time=arrival,
        ready_by=ready_by,
        energy_required_kwh=60.0,
        max_power_kw=20.0
    )
    assert not is_feasible
    assert "Requested energy cannot be delivered" in reason


def test_orchestrator_infeasible_session_handling(db_session, mock_agent_outputs):
    session = ChargingSession(
        session_id="SESS_INFEASIBLE",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 10, 30, tzinfo=timezone.utc),
        initial_soc_pct=10.0,
        target_soc_pct=90.0,
        battery_capacity_kwh=100.0,
        energy_required_kwh=80.0,  # Impossible: 80 kWh in 30 mins with 60 kW charger
        max_charging_power_kw=60.0,
        estimated_duration_min=80.0,
        flexibility="Low",
        preference="Fastest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()
    result = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert result.status == "Infeasible"
    assert result.segments == []
    assert "cannot be delivered" in result.summary_line


def test_hard_constraint_charging_boundaries(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    session = ChargingSession(
        session_id="SESS_BOUNDS",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=80.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=50.0,
        estimated_duration_min=36.0,
        flexibility="Low",
        preference="Fastest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()
    result = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert result.status == "Scheduled"
    assert len(result.segments) > 0
    for seg in result.segments:
        start_dt = datetime.fromisoformat(seg["start_time"])
        end_dt = datetime.fromisoformat(seg["end_time"])
        assert start_dt >= arrival
        assert end_dt <= ready_by
        assert seg["power_level_kw"] <= 50.0


# ==========================================
# 2. PREFERENCE TESTS (Fastest, Cheapest, Greenest)
# ==========================================

def test_preference_fastest_starts_immediately(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    session = ChargingSession(
        session_id="SESS_FASTEST",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=60.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=20.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=20.0,
        flexibility="High",
        preference="Fastest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()
    result = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert result.status == "Scheduled"
    first_seg = result.segments[0]
    # Fastest should start at the arrival time
    assert datetime.fromisoformat(first_seg["start_time"]) == arrival


def test_preference_greenest_shifts_to_solar_peak(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    session = ChargingSession(
        session_id="SESS_GREENEST",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=60.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=15.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=15.0,
        flexibility="High",
        preference="Greenest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()
    result = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert result.status == "Scheduled"
    first_seg = result.segments[0]
    # Solar peak in our fixture starts at 11:30 (slot 6: 10:00 + 1.5h = 11:30)
    assert datetime.fromisoformat(first_seg["start_time"]) >= datetime(2026, 1, 10, 11, 30, tzinfo=timezone.utc)
    assert first_seg["expected_renewable_pct"] >= 80.0


# ==========================================
# 3. FLEXIBILITY TESTS (Low vs High)
# ==========================================

def test_low_flexibility_overrides_green_window_if_deadline_urgent(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 11, 0, tzinfo=timezone.utc)  # Ready by 11:00 (before solar peak at 11:30)
    
    session = ChargingSession(
        session_id="SESS_LOW_FLEX",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=60.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=20.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=20.0,
        flexibility="Low",
        preference="Greenest",  # Driver wants greenest, but Low flex + 11:00 deadline
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()
    result = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert result.status == "Scheduled"
    # Charging must start immediately at 10:00 and finish before 11:00
    first_seg = result.segments[0]
    assert datetime.fromisoformat(first_seg["start_time"]) == arrival
    assert datetime.fromisoformat(result.segments[-1]["end_time"]) <= ready_by


# ==========================================
# 4. GRID STRESS & CRITICAL CONDITION TESTS
# ==========================================

def test_critical_grid_stress_heavily_penalized(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    # Modify grid output to critical
    critical_agent_outputs = dict(mock_agent_outputs)
    critical_agent_outputs["grid"] = {
        "session_id": "SESSION_001",
        "grid_stress": "Critical",
        "grid_stress_pct": 95.0,
        "station_load_classification": "Overload",
        "recommended_action": "Avoid charging during critical peak",
        "urgency_override": True,
        "reason": "Critical grid emergency."
    }

    slots = generate_candidate_slots(arrival, ready_by, 50.0, "Maharashtra - Mumbai", db_session)
    scored = score_candidate_slots(slots, preference="Fastest", flexibility="High")
    
    # Critical slots should have severe penalty
    for s in scored:
        if s.grid_stress_pct >= 90.0:
            assert s.total_score < 0.2


# ==========================================
# 5. AGENT OUTPUT VALIDATION TESTS
# ==========================================

def test_validate_agent_outputs_missing_and_invalid():
    # Missing required agent
    is_valid, err = validate_agent_outputs({"driver": {}})
    assert not is_valid
    assert "Missing required agent output" in err

    # Negative energy
    is_valid, err = validate_agent_outputs({
        "driver": {"energy_required_kwh": -5.0, "preference": "Fastest", "flexibility": "Low"},
        "renewable": {"green_windows": []},
        "grid": {"grid_stress_pct": 20.0, "grid_stress": "Low"},
        "cost_carbon": {"candidate_windows": []}
    })
    assert not is_valid
    assert "energy_required_kwh" in err

    # Invalid preference
    is_valid, err = validate_agent_outputs({
        "driver": {"energy_required_kwh": 10.0, "preference": "InvalidPref", "flexibility": "Low"},
        "renewable": {"green_windows": []},
        "grid": {"grid_stress_pct": 20.0, "grid_stress": "Low"},
        "cost_carbon": {"candidate_windows": []}
    })
    assert not is_valid
    assert "Invalid preference" in err


# ==========================================
# 6. DETERMINISM TEST
# ==========================================

def test_orchestrator_is_deterministic(db_session, mock_agent_outputs):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    session = ChargingSession(
        session_id="SESS_DETERMINISTIC",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=70.0,
        battery_capacity_kwh=60.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=30.0,
        flexibility="Medium",
        preference="Cheapest",
        status="Queued"
    )
    station = db_session.query(Station).filter(Station.station_id == "STATION_001").first()
    orchestrator = Orchestrator()

    res1 = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)
    res2 = orchestrator.create_schedule(session, station, mock_agent_outputs, db_session)

    assert res1.status == res2.status
    assert res1.summary_line == res2.summary_line
    assert len(res1.segments) == len(res2.segments)
    for seg1, seg2 in zip(res1.segments, res2.segments):
        assert seg1["start_time"] == seg2["start_time"]
        assert seg1["end_time"] == seg2["end_time"]
        assert seg1["expected_cost_inr"] == seg2["expected_cost_inr"]


# ==========================================
# 7. PERSISTENCE, HISTORY & RESCHEDULING TESTS
# ==========================================

def test_scheduling_service_persistence_and_history(db_session):
    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)
    
    session = ChargingSession(
        session_id="SESS_PERSIST",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=70.0,
        battery_capacity_kwh=60.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=30.0,
        flexibility="High",
        preference="Greenest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    # Generate schedule
    sched1 = SchedulingService.generate_and_persist_schedule("SESS_PERSIST", db_session)
    assert sched1.session_id == "SESS_PERSIST"
    assert sched1.status == "Scheduled"
    assert len(sched1.segments) > 0

    # Query latest schedule
    fetched = SchedulingService.get_schedule("SESS_PERSIST", db_session)
    assert fetched.id == sched1.id

    # Reschedule session (new ready_by and preference)
    new_ready_by = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    sched2 = SchedulingService.reschedule_session(
        session_id="SESS_PERSIST",
        ready_by=new_ready_by,
        preference="Fastest",
        flexibility="Low",
        db=db_session
    )
    assert sched2.id != sched1.id

    # Check history preserves both records
    history, total = SchedulingService.get_schedule_history("SESS_PERSIST", db_session)
    assert total == 2
    assert len(history) == 2
    assert history[0].id == sched2.id
    assert history[1].id == sched1.id


# ==========================================
# 8. API ROUTE INTEGRATION TESTS
# ==========================================

def test_api_schedule_endpoints(db_session):
    client = TestClient(app)
    user = db_session.query(User).filter(User.clerk_user_id == "user_driver_123").first()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user

    arrival = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    ready_by = datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc)

    session = ChargingSession(
        session_id="SESS_API_TEST",
        station_id="STATION_001",
        clerk_user_id="user_driver_123",
        arrival_time=arrival,
        ready_by=ready_by,
        initial_soc_pct=20.0,
        target_soc_pct=70.0,
        battery_capacity_kwh=60.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=60.0,
        estimated_duration_min=30.0,
        flexibility="High",
        preference="Greenest",
        status="Queued"
    )
    db_session.add(session)
    db_session.commit()

    headers = {"Authorization": "Bearer mock_driver_token"}

    # 1. POST /api/v1/sessions/{session_id}/schedule
    res_post = client.post("/api/v1/sessions/SESS_API_TEST/schedule", headers=headers)
    assert res_post.status_code == 200, res_post.text
    data = res_post.json()["data"]
    assert data["session_id"] == "SESS_API_TEST"
    assert data["status"] == "Scheduled"
    assert len(data["segments"]) > 0

    # 2. GET /api/v1/sessions/{session_id}/schedule
    res_get = client.get("/api/v1/sessions/SESS_API_TEST/schedule", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["session_id"] == "SESS_API_TEST"

    # 3. GET /api/v1/sessions/{session_id}/charging-windows
    res_win = client.get("/api/v1/sessions/SESS_API_TEST/charging-windows", headers=headers)
    assert res_win.status_code == 200
    assert len(res_win.json()["data"]) > 0

    # 4. GET /api/v1/sessions/{session_id}/schedule/history
    res_hist = client.get("/api/v1/sessions/SESS_API_TEST/schedule/history", headers=headers)
    assert res_hist.status_code == 200
    assert res_hist.json()["pagination"]["total"] == 1

    # 5. POST /api/v1/sessions/{session_id}/reschedule
    res_resched = client.post(
        "/api/v1/sessions/SESS_API_TEST/reschedule",
        json={
            "ready_by": "2026-01-10T12:00:00Z",
            "preference": "Fastest",
            "flexibility": "Low"
        },
        headers=headers
    )
    assert res_resched.status_code == 200
    assert res_resched.json()["data"]["status"] == "Scheduled"

    # Verify history is now 2
    res_hist2 = client.get("/api/v1/sessions/SESS_API_TEST/schedule/history", headers=headers)
    assert res_hist2.json()["pagination"]["total"] == 2

    app.dependency_overrides.clear()
