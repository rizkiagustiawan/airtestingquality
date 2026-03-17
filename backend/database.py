import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Fallback to sqlite if DATABASE_URL is somehow not set locally, 
# although in docker it will be set.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./airqgis.db"
)

# Use SQLite in memory if test environment or explicitly requested
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
