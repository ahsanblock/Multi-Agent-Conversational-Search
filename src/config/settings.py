from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application configuration settings"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    PINECONE_API_KEY: str = os.getenv('PINECONE_API_KEY', '')
    PINECONE_ENVIRONMENT: str = os.getenv('PINECONE_ENVIRONMENT', '')
    
    # Astra DB Settings
    ASTRA_DB_TOKEN: str = os.getenv('ASTRA_DB_TOKEN', '')
    ASTRA_DB_ENDPOINT: str = os.getenv('ASTRA_DB_ENDPOINT', '')
    
    # OpenAI Settings
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default to cheaper model
    
    # Application Settings
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    
    # Vector Search Settings
    VECTOR_DIMENSION: int = int(os.getenv('VECTOR_DIMENSION', '1536'))
    INDEX_NAME: str = os.getenv('INDEX_NAME', 'product-search')
    
    # Agent Settings
    MOCK_RESPONSES: bool = os.getenv('MOCK_RESPONSES', 'false').lower() == 'true'
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    TIMEOUT_SECONDS: int = int(os.getenv('TIMEOUT_SECONDS', '30'))
    TEMPERATURE: float = float(os.getenv('TEMPERATURE', '0.7'))
    
    # Database Settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    APP_SECRET_KEY: str = os.getenv('APP_SECRET_KEY', 'dev_secret_key_123')

    def __init__(self):
        """Initialize settings and validate required values"""
        # Validate required settings
        if not self.ASTRA_DB_TOKEN:
            raise ValueError("ASTRA_DB_TOKEN is required")
        if not self.ASTRA_DB_ENDPOINT:
            raise ValueError("ASTRA_DB_ENDPOINT is required")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")

settings = Settings() 