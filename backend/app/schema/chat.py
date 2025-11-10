from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageCreate(BaseModel):
    
    content: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    
    id: str
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        
class ChatResponse(BaseModel):
    user_message: MessageResponse
    bot_response: MessageResponse
    session_id: str
    