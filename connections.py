"""from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

path= 'mysql+mysqldb://root:2480@localhost/summit_db'


engine = create_engine(path)
SessionLocal = sessionmaker(bind=engine)


Base = declarative_base()"""
'''
connection.py
'''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base


DATABASE_URL = "postgresql://summit_347t_user:ZWXX4Du4KK7KfPlhpyTw2O2SMg4cz2l1@dpg-d2okroq4d50c73a2bghg-a.oregon-postgres.render.com:5432/summit_347t?sslmode=require"


engine = create_engine(DATABASE_URL)


Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session


Base = declarative_base()
