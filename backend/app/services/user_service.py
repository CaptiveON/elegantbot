from sqlalchemy.orm import Session
from app.crud import crud_user
from app.schema import UserCreate, UserResponse
from app.exceptions.user_exceptions import UserAlreadyExists

class UserService:
    
    def create_new_user(self, db: Session, user: UserCreate) -> UserResponse:
        
        existing_user = crud_user.get_user_by_email(db, user.email)
        
        if existing_user:
            raise UserAlreadyExists()
        
        new_user  = crud_user.create_user(db, user)
        
        return UserResponse.model_validate(new_user)
    
    
user_service = UserService()