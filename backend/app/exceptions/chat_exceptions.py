from fastapi import status
from .base import AppException

class BotResponseException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Response cannot be generated temporarily."

class MessageStorageException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error accured."
    