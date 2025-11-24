from sqlalchemy.orm import Session
from app.models import User
from app.schema import UserCreate
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")

def get_user_by_id(db:Session, user_id: str) -> User:
    
    return db.query(User).filter(User.id == user_id).one()

def get_user_by_email(db:Session, user_email:str) -> User:
    
    return db.query(User).filter(User.email == user_email).one()

def create_user(db: Session, user: UserCreate) -> User:
    
    hashed_password = pwd_context.hash(user.password)
    
    db_user = User(
        email = user.email,
        hashed_password = hashed_password,
        is_anonymous = False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user) #Includes latest data like User ID
    
    return db_user

def create_anonymous_user(db: Session) -> User:
    
    db_user = User(
        is_anonymous = True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user