import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta

from app.models import Base
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.grid_demand import GridDemand

# Use an in-memory SQLite database for testing the schema
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_create_station(db):
    station = Station(
        station_id="ST-001",
        cpo_name="Test CPO",
        govt_private="Private",
        state="Test State",
        district_city_village="Test City",
        location="Test Location",
        latitude=12.34,
        longitude=56.78,
        charger_types_connectors_installed="Type 2",
        charger_rating=22.0,
        connector_rating=22.0,
        no_of_connectors=2
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    assert station.station_id == "ST-001"

def test_station_latitude_constraint(db):
    station = Station(
        station_id="ST-002",
        cpo_name="Test",
        govt_private="Private",
        state="State",
        district_city_village="City",
        location="Location",
        latitude=100.0,  # Invalid latitude
        longitude=56.78,
        charger_types_connectors_installed="Type 2",
        charger_rating=22.0,
        connector_rating=22.0,
        no_of_connectors=2
    )
    db.add(station)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_create_charging_session(db):
    # Need a station and a user first
    station = Station(
        station_id="ST-003", cpo_name="CPO", govt_private="Gov", state="S", 
        district_city_village="D", location="L", latitude=1.0, longitude=1.0, 
        charger_types_connectors_installed="T", charger_rating=50.0, 
        connector_rating=50.0, no_of_connectors=1
    )
    user = User(clerk_user_id="user_123", role="driver")
    db.add_all([station, user])
    db.commit()

    now = datetime.now(timezone.utc)
    session = ChargingSession(
        session_id="SESS-001",
        station_id="ST-003",
        clerk_user_id="user_123",
        arrival_time=now,
        ready_by=now + timedelta(hours=2),
        initial_soc_pct=20.0,
        target_soc_pct=80.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=30.0,
        max_charging_power_kw=11.0,
        estimated_duration_min=180.0,
        flexibility="High",
        preference="Greenest",
        status="Requested"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    assert session.session_id == "SESS-001"
    assert session.station_id == "ST-003"
    assert session.clerk_user_id == "user_123"

def test_charging_session_soc_constraint(db):
    station = Station(
        station_id="ST-004", cpo_name="CPO", govt_private="Gov", state="S", 
        district_city_village="D", location="L", latitude=1.0, longitude=1.0, 
        charger_types_connectors_installed="T", charger_rating=50.0, 
        connector_rating=50.0, no_of_connectors=1
    )
    user = User(clerk_user_id="user_124", role="driver")
    db.add_all([station, user])
    db.commit()

    now = datetime.now(timezone.utc)
    # Target SOC <= Initial SOC (should fail)
    session = ChargingSession(
        session_id="SESS-002",
        station_id="ST-004",
        clerk_user_id="user_124",
        arrival_time=now,
        ready_by=now + timedelta(hours=2),
        initial_soc_pct=80.0,
        target_soc_pct=20.0,
        battery_capacity_kwh=50.0,
        energy_required_kwh=0.0,
        max_charging_power_kw=11.0,
        estimated_duration_min=0.0,
        flexibility="High",
        preference="Greenest",
        status="Requested"
    )
    db.add(session)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_grid_demand_creation(db):
    demand = GridDemand(
        timestamp=datetime.now(timezone.utc),
        region="Test Region",
        demand_mw=150.0,
        peak_demand_mw=200.0,
        available_capacity_mw=50.0,
        reserve_margin_mw=10.0,
        grid_stress_pct=75.0
    )
    db.add(demand)
    db.commit()
    db.refresh(demand)
    assert demand.id is not None
