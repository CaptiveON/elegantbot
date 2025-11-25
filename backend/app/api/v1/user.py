from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schema import UserCreate, UserResponse
from app.services.user_service import user_service

router = APIRouter(prefix="/user",tags=["authentication"])

@router.post("/anonymous", response_model=UserResponse)
def create_anonymous_user(db: Session = Depends(get_db)):
    
    return user_service.create_anonymous_user(db)

@router.post("/registeration", response_model=UserResponse)
def create_new_user(
    user:UserCreate,
    db:Session = Depends(get_db)
    ):
    
    return user_service.create_new_user(db, user) 