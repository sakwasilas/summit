
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# # ✅ Correct MySQL path format
# DATABASE_URL = "mysql+mysqldb://root:2480@localhost:3306/summit_db"

# engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session = scoped_session(sessionmaker(bind=engine))
# SessionLocal = Session

# Base = declarative_base()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# Database URL
DATABASE_URL = "postgresql://summit_lxsj_user:AwgCE7QG9BGI8UYzT6rNsThjUNDp0fAt@dpg-d2tc8cre5dus73dmuqpg-a.oregon-postgres.render.com:5432/summit_lxsj?sslmode=require"

# Engine
engine = create_engine(DATABASE_URL)

# Session
Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

# Base
Base = declarative_base()



