from sqlalchemy.orm import Session
from app.crud import crud_user
from app.models import User
from app.schema import UserCreate, UserResponse
from app.schema.token import LoginRequest
from app.exceptions.user_exceptions import UserAlreadyExists
from app.exceptions.auth_exceptions import EmailOrPasswordException
from passlib.context import CryptContext
from app.core.security import verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    
    def create_new_user(self, db: Session, user: UserCreate) -> UserResponse:
        
        existing_user = crud_user.get_user_by_email(db, user.email)
        
        if existing_user:
            raise UserAlreadyExists()
        
        trunkated_pwd = user.password[:72]
        hashed_password = pwd_context.hash(trunkated_pwd)
        
        db_user = User(
            email = user.email,
            hashed_password = hashed_password,
            is_anonymous = False
        )
        
        new_user  = crud_user.create_new_user(db, db_user)
        
        return UserResponse.model_validate(new_user)
    
    def create_anonymous_user(self, db:Session) -> UserResponse:
        
        db_user = User(
            is_anonymous = True
        )
        new_anonymous_user = crud_user.create_anonymous_user(db, db_user)

        return UserResponse.model_validate(new_anonymous_user)
    
    def authenticate_user(self, db:Session, login_data: LoginRequest) -> User:
        
        email = login_data.email
        password = login_data.password
        
        user = crud_user.get_user_by_email(db, email)
        
        if not user:
            raise EmailOrPasswordException()
        
        if not verify_password(password, user.hashed_password):
            raise EmailOrPasswordException()
        
        return user
        
        
    
    
user_service = UserService()