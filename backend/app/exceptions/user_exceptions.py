from fastapi import status
from .base import AppException

class UserAlreadyExists(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "User Already Exists. Try Logging in."