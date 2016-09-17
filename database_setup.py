import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    email = Column(String(250))
    picture = Column(String(400))


class Genre(Base):
    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }

class Book(Base):
    __tablename__ = 'book'

    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    price = Column(String(8))
    added_on = Column(DateTime, default=func.now())
    picture = Column(String(250))
    genre_id = Column(Integer,ForeignKey('genre.id'))
    genre = relationship(Genre)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'price': self.price,
        }

engine = create_engine('postgres://aoopfejlrzadwu:dQSSIHcl-P1yTvGu6hHS8JOROU@ec2-54-221-229-37.compute-1.amazonaws.com:5432/d2li04h4kgqsn')
Base.metadata.create_all(engine)