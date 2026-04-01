from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2023-12-01-preview"
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    
    # Azure Search
    azure_search_service_name: str
    azure_search_api_key: str
    azure_search_index_name: str = "documents"
    
    # App Config
    app_env: str = "development"
    debug: bool = True
    session_timeout_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
