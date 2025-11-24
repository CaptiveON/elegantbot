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
    user_id: str,
    db: Session = Depends(get_db)
):
    
    try:
        response = chat_service.process_message(db, user_id, message_data)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= str(e)
        )