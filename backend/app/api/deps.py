from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.crud import crud_user
from app.exceptions.auth_exceptions import LoginTimeOut

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    
    token  = credentials.credentials
    
    payload = decode_access_token(token)
    
    if payload is None:
        raise LoginTimeOut()
    
    user_id: str = payload.get("sub")
    
    if user_id is None:
        raise LoginTimeOut()
    
    user  = crud_user.get_user_by_id(db, user_id)
    
    if user is None:
        raise LoginTimeOut()    
    
    return user