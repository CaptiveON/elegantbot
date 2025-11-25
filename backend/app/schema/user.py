from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    
    email: str
    password: str
    
class UserResponse(BaseModel):
    
    id: str
    email: Optional[str]
    is_anonymous: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True
    }