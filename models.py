from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from connections import Base


class Admin(Base):
    __tablename__ = 'admins' 

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password = Column(String(100))  

    def __init__(self, username, password):
        self.username = username
        self.password = password 

class User(Base):
    __tablename__ = 'users'  

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password = Column(String(100))

    def __init__(self, username, password):
        self.username = username
        self.password = password


class Course(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    level = Column(String(255))

 
    subjects = relationship('Subject', back_populates='course', cascade='all, delete-orphan')

    def __init__(self, name, level):
        self.name = name
        self.level = level

class Subject(Base):
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    course_id = Column(Integer, ForeignKey('courses.id'))

    
    course = relationship('Course', back_populates='subjects')

    def __init__(self, name, course_id):
        self.name = name
        self.course_id = course_id
