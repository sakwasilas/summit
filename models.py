from sqlalchemy import Column, Integer, String
from connections import Base 

class Admin(Base):
    __tablename__ = 'admins' 

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True) 
    password = Column(String(100)) 

    def __init__(self,username,password) :
        self.username=username
        self.passwrod=password

class User(Base):
    __tablename__ = 'users'  

    id = Column(Integer, primary_key=True, index=True)
    username= Column(String(100), unique=True, index=True)  
    password = Column(String(100))  


    def __init__(self,username,password):
        self.username=username
        self.password=password

  
        