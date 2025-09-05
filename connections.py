
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base



DATABASE_URL=("postgresql://summit:1YT0CF5RUqDdmNo0bXaACWwI66j9FMLE@dpg-d2te6495pdvs739fu590-a.oregon-postgres.render.com:5432/summit_6gqd?sslmode=require"
)

engine = create_engine(DATABASE_URL)


Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session


Base = declarative_base()
