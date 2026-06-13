from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "Resume Review Project"
    API_V1_STR: str = "/api"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    USE_GEMINI: bool = False # Changed to False to prioritize groq or local models as per MVP request
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
