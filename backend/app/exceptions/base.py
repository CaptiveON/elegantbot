from fastapi import status

class AppException(Exception):
    
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An internal error occured."
    
    def __init__(self, detail:str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)