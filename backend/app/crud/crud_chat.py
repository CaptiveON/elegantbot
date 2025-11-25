from sqlalchemy.orm import Session
from app.models import ChatSession, Message
from typing import List

def create_session(db: Session, chat_session: ChatSession) -> ChatSession:
    
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    
    return chat_session

def get_session(db: Session, session_id: str) -> ChatSession:
    
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()

def get_user_sessions(db: Session, user_id: str) -> List[ChatSession]:

    return db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).all()

def create_message(db:Session, message: Message) -> Message:
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message

def get_session_messages(db:Session, session_id: str) -> List[Message]:
    
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    