# Import all models to ensure they are registered with the Base metadata
from app.core.database import Base
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

# This allows importing everything from app.models
__all__ = [
    "Base",
    "Station",
    "User",
    "ChargingSession",
    "GridDemand",
    "RenewableGeneration",
    "Weather",
    "TariffCarbon",
    "AgentDecision",
    "ChargingSchedule",
    "NotificationLog",
    "Alert"
]
