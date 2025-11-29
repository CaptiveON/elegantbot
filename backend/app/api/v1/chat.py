from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schema import MessageCreate, ChatResponse, MessageResponse, ChatSessionResponse
from app.services.chat_service import chat_service
from app.crud import crud_chat
from app.api.deps import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/message", response_model=ChatResponse)
def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    return chat_service.process_message(db, current_user.id, message_data)
