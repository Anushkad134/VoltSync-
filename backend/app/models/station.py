from sqlalchemy import Column, String, Float, Integer, CheckConstraint
from app.core.database import Base

class Station(Base):
    __tablename__ = "stations"

    station_id = Column(String, primary_key=True, index=True)
    cpo_name = Column(String, nullable=False)
    govt_private = Column(String, nullable=False)
    state = Column(String, nullable=False, index=True)
    district_city_village = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    charger_types_connectors_installed = Column(String, nullable=False)
    charger_rating = Column(Float, nullable=False)
    connector_rating = Column(Float, nullable=False)
    no_of_connectors = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint('latitude BETWEEN -90 AND 90', name='check_latitude'),
        CheckConstraint('longitude BETWEEN -180 AND 180', name='check_longitude'),
        CheckConstraint('no_of_connectors > 0', name='check_no_of_connectors'),
        CheckConstraint('charger_rating > 0', name='check_charger_rating'),
        CheckConstraint('connector_rating > 0', name='check_connector_rating'),
    )
