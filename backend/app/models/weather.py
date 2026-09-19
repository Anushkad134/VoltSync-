from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint, Index
from app.core.database import Base

class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    region = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    solar_irradiance_w_m2 = Column(Float, nullable=False)
    cloud_cover_pct = Column(Float, nullable=False)
    wind_speed_kmh = Column(Float, nullable=False)
    humidity_pct = Column(Float, nullable=False)
    rainfall_mm = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint('solar_irradiance_w_m2 >= 0', name='check_solar_irradiance'),
        CheckConstraint('cloud_cover_pct >= 0 AND cloud_cover_pct <= 100', name='check_cloud_cover'),
        CheckConstraint('wind_speed_kmh >= 0', name='check_wind_speed'),
        CheckConstraint('humidity_pct >= 0 AND humidity_pct <= 100', name='check_humidity'),
        CheckConstraint('rainfall_mm >= 0', name='check_rainfall'),
        Index('ix_weather_region_timestamp', 'region', 'timestamp'),
    )
