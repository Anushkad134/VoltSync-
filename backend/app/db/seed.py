import os
import csv
import logging
from app.core.database import SessionLocal, engine
from app.core.config import settings
from app.models.station import Station
from app.models.user import User
from app.models.charging_session import ChargingSession
from app.models.grid_demand import GridDemand
from app.models.renewable_generation import RenewableGeneration
from app.models.weather import Weather
from app.models.tariff_carbon import TariffCarbon
from app.models.agent_decision import AgentDecision
from app.models.charging_schedule import ChargingSchedule
from app.models.notification_log import NotificationLog
from app.models.alert import Alert

from app.db.generation.config import GenerationContext
from app.db.generation.timeline import generate_timeline
from app.db.generation.weather import generate_weather
from app.db.generation.renewable import generate_renewable
from app.db.generation.grid import generate_grid_and_update_renewable
from app.db.generation.tariff_carbon import generate_tariff_carbon
from app.db.generation.sessions import generate_sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_stations(db, csv_path: str):
    logger.info(f"Loading stations from {csv_path}")
    if not os.path.exists(csv_path):
        logger.error("STATION_DATA_NOT_FOUND")
        raise FileNotFoundError(f"Station dataset not found at {csv_path}")

    stations = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing = db.query(Station).filter_by(station_id=row['station_id']).first()
            if not existing:
                station = Station(
                    station_id=row['station_id'],
                    cpo_name=row['cpo_name'],
                    govt_private=row['govt_private'],
                    state=row['state'],
                    district_city_village=row['district_city_village'],
                    location=row['location'],
                    latitude=float(row['latitude']),
                    longitude=float(row['longitude']),
                    charger_types_connectors_installed=row['charger_types_connectors_installed'],
                    charger_rating=float(row['charger_rating']),
                    connector_rating=float(row['connector_rating']),
                    no_of_connectors=int(row['no_of_connectors'])
                )
                db.add(station)
                stations.append(station)
            else:
                stations.append(existing)
    
    # Needs to flush to make stations available in the same transaction
    db.flush()
    return stations

def clear_synthetic_data(db):
    logger.info("Clearing existing synthetic data...")
    db.query(AgentDecision).delete()
    db.query(ChargingSchedule).delete()
    db.query(NotificationLog).delete()
    db.query(Alert).delete()
    db.query(ChargingSession).delete()
    db.query(GridDemand).delete()
    db.query(RenewableGeneration).delete()
    db.query(Weather).delete()
    db.query(TariffCarbon).delete()
    db.flush()

def ensure_synthetic_user(db):
    user = db.query(User).filter_by(clerk_user_id="synthetic_user").first()
    if not user:
        user = User(clerk_user_id="synthetic_user", role="synthetic_driver")
        db.add(user)
        db.flush()

def validate_data(db):
    # Minimal post generation checks
    # Because we rely on DB constraints, if flush succeeds, most DB constraints hold.
    # The PRD requires we explicitly log if things look correct.
    sessions = db.query(ChargingSession).count()
    if sessions == 0:
        logger.warning("No sessions were generated!")
    grid = db.query(GridDemand).count()
    if grid == 0:
        logger.error("INVALID_GENERATED_DATA")
        raise ValueError("Grid demand is empty")
    logger.info("Validation: PASS")

def seed():
    logger.info("VoltSync seed started")
    logger.info(f"Seed: {settings.RANDOM_SEED}")
    logger.info(f"Simulation days: {settings.SIMULATION_DAYS}")
    
    db = SessionLocal()
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        stations_csv = os.path.join(data_dir, "charging_stations.csv")
        
        # 1. Load Station CSV
        stations = load_stations(db, stations_csv)
        logger.info(f"Stations: {len(stations)}")
        
        if len(stations) == 0:
            raise ValueError("INVALID_STATION_DATA")
            
        # 2. Clear old data and ensure user
        clear_synthetic_data(db)
        ensure_synthetic_user(db)
        
        # 3. Context & Timeline
        context = GenerationContext(stations)
        logger.info(f"Regions: {len(context.regions)}")
        timeline = generate_timeline(context)
        
        # 4. Generate datasets in order
        weather = generate_weather(context, timeline)
        db.add_all(weather)
        db.flush()
        
        renewable = generate_renewable(context, weather)
        grid = generate_grid_and_update_renewable(context, timeline, renewable)
        tariff = generate_tariff_carbon(context, renewable)
        
        db.add_all(renewable)
        db.add_all(grid)
        db.add_all(tariff)
        db.flush()
        
        sessions = generate_sessions(context, timeline)
        db.add_all(sessions)
        db.flush()
        
        # 5. Validation
        validate_data(db)
        
        # 6. Commit
        db.commit()
        
        logger.info("Generated:")
        logger.info(f"  Sessions: {len(sessions)}")
        logger.info(f"  Grid records: {len(grid)}")
        logger.info(f"  Renewable records: {len(renewable)}")
        logger.info(f"  Weather records: {len(weather)}")
        logger.info(f"  Tariff/carbon records: {len(tariff)}")
        logger.info("Seed completed successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"DATABASE_SEED_FAILED: {e}")
        import sys
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
