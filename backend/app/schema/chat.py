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
        
class ChatSessions(BaseModel):
    
    user_id: str
    chat_sessions: ChatSessionResponse

class ChatHistory(BaseModel):
    
    session_id: str
    messages: List[MessageResponse]

class ChatResponse(BaseModel):
    session_id: str
    user_message: MessageResponse
    bot_response: MessageResponse
    