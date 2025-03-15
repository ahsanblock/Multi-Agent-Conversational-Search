from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "gcp-starter"
    
    # Astra DB Settings
    ASTRA_DB_TOKEN: Optional[str] = None
    ASTRA_DB_ENDPOINT: Optional[str] = None
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Application
    APP_SECRET_KEY: str = "dev_secret_key_123"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Vector Search
    VECTOR_DIMENSION: int = 1536
    INDEX_NAME: str = "product-search"
    
    # Performance
    MAX_RETRIES: int = 3
    TIMEOUT_SECONDS: int = 30
    TEMPERATURE: float = 0.7
    
    # Agent Settings
    MOCK_RESPONSES: bool = True  # Use mock responses when APIs are not configured
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Create a global settings instance
settings = get_settings() 