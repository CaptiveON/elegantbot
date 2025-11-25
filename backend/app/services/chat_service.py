from sqlalchemy.orm import Session
from app.crud import crud_chat
from app.models.chat import Message, ChatSession
from app.schema import MessageCreate, MessageResponse, ChatResponse, ChatHistory, ChatSessions, ChatSessionResponse
from app.exceptions.chat_exceptions import BotResponseException, MessageStorageException
class ChatService:
    
    def process_message(self, db: Session, user_id: str, message_data: MessageCreate) -> ChatResponse:
        
        chat_session = None
        if message_data.session_id:
            chat_session = crud_chat.get_session(db, message_data.session_id)
        if not chat_session:
                # raise ValueError("Session not Found!")
            title = (message_data.content[:50] + "...") if len(message_data.content) > 50 else message_data.content
            chat_session = ChatSession(
                title = title,
                user_id = user_id
            )
            chat_session = crud_chat.create_session(db,chat_session)
            
        user_message = Message(
            session_id = chat_session.id,
            role = "user",
            content = message_data.content
        )
        
        user_message = crud_chat.create_message(db, user_message)
        
        bot_response_text = f"I have received your message: {message_data.content}"
        
        if not bot_response_text:
            raise BotResponseException()
        
        bot_message = Message(
            session_id = chat_session.id,
            role = "bot",
            content = bot_response_text
        )
        
        bot_message = crud_chat.create_message(db, bot_message)
        
        return ChatResponse(
            user_message= MessageResponse.model_validate(user_message),
            bot_response= MessageResponse.model_validate(bot_message),
            session_id= chat_session.id
        )
        
    def get_chat_history(self, db: Session, session_id: str):
        
        orm_messages =  crud_chat.get_session_messages(db, session_id)

        return ChatHistory(
            session_id= session_id,
            messages= [MessageResponse.model_validate(m) for m in orm_messages]
        )
    
    def get_chat_sessions(self, db: Session, user_id: str):
        
        orm_sessions = crud_chat.get_user_sessions(db, user_id)
        
        return ChatSessions(
            user_id= user_id,
            session = [ChatSessionResponse.model_validate(s) for s in orm_sessions]
        )

chat_service = ChatService()