from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.crud import crud_user

def get_current_user(
    user_id: str,
    db: Session = Depends(get_db)
) -> User:
    
    user = crud_user.get_user_by_id(db, user_id=1)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found"
        )
        
    return user