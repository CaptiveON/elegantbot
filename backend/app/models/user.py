from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.app.database import Base

# Inherited with Base to specify the User class as a Table for DATABSE
# Email and Password attributes are nullable so the user can use the app without making an account first
# Is_anonymous is True by defualt to specify the user is new and the chathistory can be moved once registered
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_anonymous = Column(Boolean,default= True)
    created_at = Column(DateTime, default=datetime.now)
    
    chat_sessions = relationship("ChatSession", back_populates="user")