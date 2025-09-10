
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base



# DATABASE_URL=("postgresql://summit:1YT0CF5RUqDdmNo0bXaACWwI66j9FMLE@dpg-d2te6495pdvs739fu590-a.oregon-postgres.render.com:5432/summit_6gqd?sslmode=require"
# )

# engine = create_engine(DATABASE_URL)


# Session = scoped_session(sessionmaker(bind=engine))
# SessionLocal = Session


# Base = declarative_base()

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# # MySQL connection string without host/port (defaults to localhost:3306)
# DATABASE_URL = "mysql+mysqldb://root:2480@/summit_db"

# engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session = scoped_session(sessionmaker(bind=engine))
# SessionLocal = Session

# Base = declarative_base()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# Updated database URL
DATABASE_URL = "postgresql://summit_r1g6_user:VQFcCbzmgEnziJTbnX51a0SBgVn81FUB@dpg-d30gcp7fte5s73ecjk3g-a.oregon-postgres.render.com:5432/summit_r1g6?sslmode=require"

engine = create_engine(DATABASE_URL)

Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

Base = declarative_base()

