from sqlalchemy.orm import Session
from app.models import ChatSession, Message
from typing import List

def create_session(db: Session, user_id: str, title: str = "New Chat") -> ChatSession:
    
    db_chat_session = ChatSession(
        user_id = user_id,
        title = title
    )
    
    db.add(db_chat_session)
    db.commit()
    db.refresh(db_chat_session)
    
    return db_chat_session

def get_session(db: Session, session_id: str) -> ChatSession:
    
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()

def get_user_sessions(db: Session, user_id: str) -> List[ChatSession]:

    return db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).all()

def create_message(db:Session, session_id: str, role: str, content: str, ) -> Message:
    
    db_message = Message(
        session_id = session_id,
        role = role,
        content = content
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_message

def get_session_messages(db:Session, session_id: str) -> List[Message]:
    
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    