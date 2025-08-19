from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

path= 'mysql+mysqldb://root:2480@localhost/summit_db'


engine = create_engine(path)
SessionLocal = sessionmaker(bind=engine)


Base = declarative_base()