from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schema import UserCreate, UserResponse
from app.crud import crud_user

router = APIRouter(prefix="/auth",tags=["authentication"])

@router.post("/anonymous", response_model=UserResponse)
def create_anonymous_user(db: Session = Depends(get_db)):
    user = crud_user.create_anonymous_user(db)
    return user