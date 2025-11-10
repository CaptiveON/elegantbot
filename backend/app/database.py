# Create Engine
# Make DB Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

# An Engine building a connection with DATABASE using DATABASE URL
engine = create_engine(settings.DATABASE_URL)

# Session for ORM (Object-Relational Mapping) binded with DATABASE Connection (Engine) to perform the DATABASE Operations
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Telling DATABASE that which class is to be the Table. It's a Parent class to create ORM for creating, updating, deleting 
# in Database via sessionmaker/ORM
# Is set as Global to inherit all the Model Classes to be treated as Tables
Base = declarative_base()

def get_db():
    
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()