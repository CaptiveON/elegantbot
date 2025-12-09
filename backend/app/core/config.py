from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8"
    )
    
    # Database
    DATABASE_URL:str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = ""
    OPENAI_EMBEDDING_MODEL: str = ""
    OPENAI_CLASSIFICATION_MODEL: str = ""
    OPENAI_GENERATION_MODEL: str = ""
    
    # Pinecone - Vector DB
    PINECONE_API_KEY: Optional[str] = ""
    PINECONE_INDEX_NAME: str = ""
    PINECONE_ENVIRONMENT: str = ""
        
settings = Settings()