from sqlalchemy import Column, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

class ChatSession(Base):
    
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, default= lambda: str(uuid.uuid4()))
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(String, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session")
    
class Message(Base):
    
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("ChatSession", back_populates="messages")