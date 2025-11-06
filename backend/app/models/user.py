from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

class User(Base):
    __tabelname__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_anonymous = Column(Boolean,default= True)
    created_at = Column(DateTime, default=datetime.now)