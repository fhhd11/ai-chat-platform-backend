from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # FastAPI settings
    secret_key: str = "your-secret-key-change-in-production"
    environment: str = "development"
    log_level: str = "INFO"
    
    # Supabase settings
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    
    # Letta settings
    letta_base_url: str = "https://lettalettalatest-production-4de4.up.railway.app"
    letta_api_token: Optional[str] = None  # Empty for self-hosted
    letta_global_api_key: str = "letta-global-proxy-key"  # Global key for proxy requests
    
    # LiteLLM settings
    litellm_base_url: str = "https://litellm-production-1c8b.up.railway.app"
    litellm_master_key: str
    
    # Backend settings
    backend_base_url: str = "http://localhost:8000"  # Our backend URL for proxy endpoints
    
    # JWT settings
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    
    # CORS settings
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    
    def get_allowed_origins(self) -> list[str]:
        """Parse allowed origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()