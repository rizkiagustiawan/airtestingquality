"""Optional SQLAlchemy/PostGIS schema scaffold for future persistence expansion."""

import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    city = Column(String)
    # PostGIS Point (Longitude, Latitude)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))
    latitude = Column(Float)  # duplicated for easy API JSON serialization
    longitude = Column(Float)

    # Relationship to historical readings
    readings = relationship("SensorReading", back_populates="station", cascade="all, delete-orphan")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    # Pollutants
    pm10 = Column(Float, nullable=True)
    pm25 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)

    station = relationship("Station", back_populates="readings")


class EmissionSource(Base):
    __tablename__ = "emission_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # POINT, AREA, VOLUME
    geom = Column(Geometry(geometry_type="POINT", srid=4326))

    # Emission rates (g/s)
    rate_pm10 = Column(Float, default=0.0)
    rate_so2 = Column(Float, default=0.0)
    rate_no2 = Column(Float, default=0.0)

    # Physical pars
    stack_height = Column(Float, nullable=True)
    stack_diameter = Column(Float, nullable=True)
    exit_velocity = Column(Float, nullable=True)
    exit_temp = Column(Float, nullable=True)
