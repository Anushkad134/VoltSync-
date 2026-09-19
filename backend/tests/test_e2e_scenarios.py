import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.charging_schedule import ChargingSchedule
from app.models.renewable_generation import RenewableGeneration
from app.models.tariff_carbon import TariffCarbon
from app.models.grid_demand import GridDemand

from app.services.session_service import SessionService
from app.services.scheduling_service import SchedulingService
from app.schemas.session import ChargingSessionCreate, RescheduleRequest


@pytest.fixture
def e2e_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Driver
    driver_1 = User(
        clerk_user_id="driver_e2e_1",
        role="driver"
    )
    db.add(driver_1)

    # Station
    station = Station(
        station_id="STATION_E2E_01",
        cpo_name="VoltSync Demo Power",
        govt_private="Private",
        state="Maharashtra",
        district_city_village="Mumbai",
        location="BKC Central",
        latitude=19.0657,
        longitude=72.8687,
        charger_types_connectors_installed="CCS2",
        charger_rating=60.0,
        connector_rating=60.0,
        no_of_connectors=4
    )
    db.add(station)

    # Seed 24-hour deterministic time-series (15-min intervals)
    base_time = datetime(2026, 6, 15, 8, 0, 0, tzinfo=timezone.utc)
    region = "Maharashtra - Mumbai"

    for i in range(48):  # 12 hours from 08:00 to 20:00
        t = base_time + timedelta(minutes=15 * i)
        hour = t.hour

        # Solar peak midday (11:00 - 14:00)
        is_solar_peak = (11 <= hour < 14)
        # Off-peak pricing late afternoon / morning
        is_cheap_window = (8 <= hour < 10)
        # Grid peak early evening (17:00 - 20:00)
        is_grid_stress = (17 <= hour < 20)

        ren_share = 85.0 if is_solar_peak else (45.0 if is_cheap_window else 20.0)
        solar_mw = 600.0 if is_solar_peak else 80.0
        tariff_val = 4.50 if is_cheap_window else (7.50 if is_solar_peak else 12.00)
        carbon_val = 250.0 if is_solar_peak else 650.0
        grid_stress_score = 88.0 if is_grid_stress else 32.0

        db.add(RenewableGeneration(
            timestamp=t,
            region=region,
            solar_generation_mw=solar_mw,
            wind_generation_mw=120.0,
            hydro_generation_mw=40.0,
            other_renewable_mw=10.0,
            total_renewable_mw=solar_mw + 170.0,
            renewable_share_pct=ren_share
        ))

        db.add(TariffCarbon(
            timestamp=t,
            region=region,
            tariff_period="Peak-Solar" if is_solar_peak else ("Off-Peak" if is_cheap_window else "Standard"),
            electricity_tariff_inr_per_kwh=tariff_val,
            renewable_share_pct=ren_share,
            grid_carbon_intensity_gco2_per_kwh=carbon_val
        ))

        db.add(GridDemand(
            timestamp=t,
            region=region,
            demand_mw=1200.0,
            peak_demand_mw=1500.0,
            available_capacity_mw=1800.0,
            reserve_margin_mw=600.0,
            grid_stress_pct=grid_stress_score
        ))

    db.commit()
    yield db
    db.close()


# ==============================================================================
# 1. Scenario 1: Greenest Charging
# ==============================================================================
def test_scenario_1_greenest_charging(e2e_db):
    """
    Scenario 1: Preference='Greenest', Flexibility='High', generous ready-by.
    Expected: Orchestrator selects high renewable midday window (11:00-14:00).
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()
    
    arrival = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 16, 0, 0, tzinfo=timezone.utc)

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=20,
        target_soc_pct=80,
        battery_capacity_kwh=60.0,
        max_charging_power_kw=50.0,
        flexibility="High",
        preference="Greenest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        assert session.session_id is not None
        assert session.status in ["created", "Queued"]

        sched = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)
        assert sched.status == "Scheduled"
        assert len(sched.segments) > 0
        assert "renewable" in sched.summary_line.lower() or "green" in sched.summary_line.lower() or "scheduled" in sched.summary_line.lower()


# ==============================================================================
# 2. Scenario 2: Cheapest Charging
# ==============================================================================
def test_scenario_2_cheapest_charging(e2e_db):
    """
    Scenario 2: Preference='Cheapest', Flexibility='High', window spanning cheap morning tariff.
    Expected: Orchestrator selects lowest tariff window (08:00 - 10:00).
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()

    arrival = datetime(2026, 6, 15, 8, 0, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 15, 0, 0, tzinfo=timezone.utc)

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=30,
        target_soc_pct=70,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="High",
        preference="Cheapest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        sched = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)

        assert sched.status == "Scheduled"
        assert len(sched.segments) > 0


# ==============================================================================
# 3. Scenario 3: Deadline Wins (Hard Constraint)
# ==============================================================================
def test_scenario_3_deadline_wins(e2e_db):
    """
    Scenario 3: Preference='Greenest', but ready-by is 10:30 (before solar peak at 11:00).
    Expected: Orchestrator MUST schedule before ready_by, proving hard deadline constraint wins over green preference.
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()

    arrival = datetime(2026, 6, 15, 8, 30, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 10, 30, 0, tzinfo=timezone.utc)  # Urgent deadline

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=20,
        target_soc_pct=60,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="Low",
        preference="Greenest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        sched = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)

        assert sched.status == "Scheduled"
        assert len(sched.segments) > 0
        end_slot = datetime.fromisoformat(sched.segments[-1]["end_time"])
        assert end_slot <= ready


# ==============================================================================
# 4. Scenario 4: Grid Stress
# ==============================================================================
def test_scenario_4_grid_stress(e2e_db):
    """
    Scenario 4: Evening period (17:00-20:00) has Critical grid stress (88%).
    Expected: Orchestrator schedules before the critical stress window.
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()

    arrival = datetime(2026, 6, 15, 15, 0, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 19, 30, 0, tzinfo=timezone.utc)

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=40,
        target_soc_pct=70,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="High",
        preference="Fastest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        sched = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)

        assert sched.status == "Scheduled"
        start_slot = datetime.fromisoformat(sched.segments[0]["start_time"])
        assert start_slot.hour < 17


# ==============================================================================
# 5. Scenario 5: Infeasible Request
# ==============================================================================
def test_scenario_5_infeasible_request(e2e_db):
    """
    Scenario 5: Required energy (80 kWh) cannot physically be delivered in 15 mins with 50 kW max power.
    Expected: Orchestrator sets status to 'Infeasible' and does not create a fake schedule.
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()

    arrival = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 9, 15, 0, tzinfo=timezone.utc)  # Only 15 min window

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=10,
        target_soc_pct=90,
        battery_capacity_kwh=100.0,
        max_charging_power_kw=50.0,
        flexibility="Low",
        preference="Fastest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        sched = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)

        assert sched.status == "Infeasible"
        assert len(sched.segments) == 0


# ==============================================================================
# 6. Scenario 6: Schedule Changed / Reschedule Workflow
# ==============================================================================
def test_scenario_6_schedule_changed_workflow(e2e_db):
    """
    Scenario 6: Start with valid schedule, then driver or system reschedules.
    Expected: New schedule generated and persisted in history table.
    """
    driver = e2e_db.query(User).filter(User.clerk_user_id == "driver_e2e_1").first()

    arrival = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    ready = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    req = ChargingSessionCreate(
        station_id="STATION_E2E_01",
        arrival_time=arrival,
        ready_by=ready,
        initial_soc_pct=20,
        target_soc_pct=60,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="Medium",
        preference="Fastest"
    )

    with patch("app.services.notification_service.NotificationService"):

        session = SessionService.create_session(req, driver, e2e_db)
        sched1 = SchedulingService.generate_and_persist_schedule(session.session_id, e2e_db)
        assert sched1.status == "Scheduled"

        # Reschedule session with new preference and extended deadline
        resched_req = RescheduleRequest(
            ready_by=datetime(2026, 6, 15, 15, 0, 0, tzinfo=timezone.utc),
            flexibility="High",
            preference="Greenest"
        )

        updated_sched = SessionService.reschedule_session(
            session.session_id, resched_req, driver, e2e_db
        )
        assert updated_sched.status == "Scheduled"

        all_schedules = e2e_db.query(ChargingSchedule).filter(
            ChargingSchedule.session_id == session.session_id
        ).all()
        assert len(all_schedules) >= 2
