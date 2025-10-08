from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# ✅ NEW DATABASE CONNECTION URL
DATABASE_URL = "postgresql://summit_ch14_user:cEImWayFx7yKyraqNjWZd5KPDRCrn7bD@dpg-d3j5b8re5dus739iiti0-a.oregon-postgres.render.com:5432/summit_ch14?sslmode=require"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a scoped session
Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

# Base class for ORM models
Base = declarative_base()
