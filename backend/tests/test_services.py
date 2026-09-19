import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.core.database import Base
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.tariff_carbon import TariffCarbon
from app.models.grid_demand import GridDemand
from app.models.renewable_generation import RenewableGeneration
from app.schemas.session import ChargingSessionCreate, RescheduleRequest

from app.services.station_service import StationService
from app.services.queue_service import QueueService
from app.services.pricing_service import PricingService
from app.services.reliability_service import ReliabilityService
from app.services.session_service import SessionService
from app.services.dashboard_service import DashboardService

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
        clerk_user_id="user_driver_100",
        role="driver"
    )
    operator = User(
        clerk_user_id="user_op_100",
        role="operator",
        linked_station_ids=["STATION_SERV_01"]
    )
    grid_op = User(
        clerk_user_id="user_grid_100",
        role="grid_operator",
        region="Maharashtra - Mumbai"
    )
    db.add_all([driver, operator, grid_op])

    # Seed mock station
    station = Station(
        station_id="STATION_SERV_01",
        cpo_name="Tata Power",
        govt_private="Private",
        state="Maharashtra",
        district_city_village="Mumbai",
        location="BKC Central",
        latitude=19.0657,
        longitude=72.8687,
        charger_types_connectors_installed="CCS2",
        charger_rating=60.0,
        connector_rating=60.0,
        no_of_connectors=2
    )
    db.add(station)

    # Seed datasets
    now = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
    region = "Maharashtra - Mumbai"

    db.add(TariffCarbon(
        timestamp=now,
        region=region,
        tariff_period="Peak",
        electricity_tariff_inr_per_kwh=8.5,
        renewable_share_pct=75.0,
        grid_carbon_intensity_gco2_per_kwh=420.0
    ))

    db.add(GridDemand(
        timestamp=now,
        region=region,
        demand_mw=1250.0,
        peak_demand_mw=1500.0,
        available_capacity_mw=1800.0,
        reserve_margin_mw=550.0,
        grid_stress_pct=45.0
    ))

    db.add(RenewableGeneration(
        timestamp=now,
        region=region,
        solar_generation_mw=400.0,
        wind_generation_mw=200.0,
        hydro_generation_mw=100.0,
        other_renewable_mw=20.0,
        total_renewable_mw=720.0,
        renewable_share_pct=75.0
    ))

    db.commit()

    yield db
    db.close()


# ==========================================
# 1. SESSION SERVICE TESTS
# ==========================================

def test_session_service_create_and_energy_calculation(db_session):
    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_100").first()
    
    session_in = ChargingSessionCreate(
        station_id="STATION_SERV_01",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=80.0,
        battery_capacity_kwh=60.0,
        max_charging_power_kw=50.0,
        flexibility="Medium",
        preference="Greenest"
    )

    session = SessionService.create_session(session_in, driver, db_session)
    assert session.session_id.startswith("SES_")
    assert session.clerk_user_id == driver.clerk_user_id
    assert session.status == "Queued"
    
    # 60 kWh * (80 - 20) / 100 = 36 kWh
    assert session.energy_required_kwh == 36.0
    # (36 / 50) * 60 = 43.2 min
    assert session.estimated_duration_min == 43.2


def test_session_service_exceed_station_power_raises(db_session):
    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_100").first()
    
    # Station charger_rating is 60 kW. Requesting 100 kW must fail with 400.
    session_in = ChargingSessionCreate(
        station_id="STATION_SERV_01",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=80.0,
        battery_capacity_kwh=60.0,
        max_charging_power_kw=100.0,
        flexibility="Low",
        preference="Fastest"
    )

    with pytest.raises(HTTPException) as exc_info:
        SessionService.create_session(session_in, driver, db_session)
    assert exc_info.value.status_code == 400


def test_session_service_cancel_and_state_transitions(db_session):
    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_100").first()
    
    session_in = ChargingSessionCreate(
        station_id="STATION_SERV_01",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=60.0,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="Low",
        preference="Fastest"
    )
    session = SessionService.create_session(session_in, driver, db_session)

    # 1. Cancel queued session -> succeeds
    cancelled = SessionService.cancel_session(session.session_id, driver, db_session)
    assert cancelled.status == "Cancelled"

    # 2. Cancelling already cancelled session -> raises 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        SessionService.cancel_session(session.session_id, driver, db_session)
    assert exc_info.value.status_code == 409


# ==========================================
# 2. STATION & RELIABILITY SERVICE TESTS
# ==========================================

def test_station_service_availability_and_reliability(db_session):
    station = StationService.get_station("STATION_SERV_01", db_session)
    assert station.station_id == "STATION_SERV_01"

    # No active sessions -> Available (2/2)
    status_str, avail, total = StationService.get_station_availability(station, db_session)
    assert status_str == "Available"
    assert avail == 2
    assert total == 2

    # Reliability calculation
    rel = ReliabilityService.calculate_station_reliability("STATION_SERV_01", db_session)
    assert rel["reliability_score"] == 100.0
    assert rel["reliability_category"] == "Excellent"


# ==========================================
# 3. QUEUE SERVICE TESTS
# ==========================================

def test_queue_service_ordering_and_load(db_session):
    driver = db_session.query(User).filter(User.clerk_user_id == "user_driver_100").first()

    # Create 2 sessions at different arrival times
    s1_in = ChargingSessionCreate(
        station_id="STATION_SERV_01",
        arrival_time=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=50.0,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="Low",
        preference="Fastest"
    )
    s1 = SessionService.create_session(s1_in, driver, db_session)

    s2_in = ChargingSessionCreate(
        station_id="STATION_SERV_01",
        arrival_time=datetime(2026, 1, 10, 10, 30, tzinfo=timezone.utc),
        ready_by=datetime(2026, 1, 10, 12, 30, tzinfo=timezone.utc),
        initial_soc_pct=20.0,
        target_soc_pct=50.0,
        battery_capacity_kwh=50.0,
        max_charging_power_kw=50.0,
        flexibility="Low",
        preference="Fastest"
    )
    s2 = SessionService.create_session(s2_in, driver, db_session)

    # s1 arrived at 10:00 -> position 1
    pos1 = QueueService.get_queue_position(s1, db_session)
    assert pos1 == 1

    # s2 arrived at 10:30 -> position 2
    pos2 = QueueService.get_queue_position(s2, db_session)
    assert pos2 == 2

    # Transition s1 to Charging
    s1.status = "Charging"
    db_session.commit()

    # Active session has queue position 0
    assert QueueService.get_queue_position(s1, db_session) == 0

    # Station load should reflect s1 charging at 50 kW
    load = QueueService.calculate_station_load("STATION_SERV_01", db_session)
    assert load == 50.0


# ==========================================
# 4. PRICING SERVICE TESTS
# ==========================================

def test_pricing_service_calculations(db_session):
    price_rec = PricingService.get_current_price("Maharashtra - Mumbai", None, db_session)
    assert price_rec is not None
    assert price_rec.electricity_tariff_inr_per_kwh == 8.5

    # 30 kWh at 8.5 INR/kWh = 255.0 INR
    cost = PricingService.calculate_session_cost(30.0, 8.5)
    assert cost == 255.0

    # 30 kWh at 420.0 gCO2/kWh = 12600.0 g
    carbon = PricingService.calculate_carbon_emission(30.0, 420.0)
    assert carbon == 12600.0


# ==========================================
# 5. DASHBOARD SERVICE TESTS
# ==========================================

def test_dashboard_service_operator_and_grid(db_session):
    operator = db_session.query(User).filter(User.clerk_user_id == "user_op_100").first()
    grid_op = db_session.query(User).filter(User.clerk_user_id == "user_grid_100").first()

    op_dash = DashboardService.get_operator_dashboard(operator, db_session)
    assert op_dash.station_count == 1
    assert op_dash.relevant_grid_stress_pct == 45.0

    grid_dash = DashboardService.get_grid_operator_dashboard(grid_op, db_session)
    assert grid_dash.region == "Maharashtra - Mumbai"
    assert grid_dash.current_demand_mw == 1250.0
    assert grid_dash.grid_stress_pct == 45.0
