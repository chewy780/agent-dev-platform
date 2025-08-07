from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./agents.db"
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    jwt_secret: str = "your-jwt-secret-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://51.81.187.172:3000"
    ]
    
    # File Storage
    agents_dir: str = "./agents"
    logs_dir: str = "./logs"
    uploads_dir: str = "./uploads"
    
    # OpenHands Integration
    openhands_runtime_url: str = "http://localhost:3000"
    openhands_api_key: Optional[str] = None
    
    # Redis (for WebSocket and caching)
    redis_url: str = "redis://localhost:6379"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # Agent Configuration
    max_agents_per_user: int = 10
    max_concurrent_agents: int = 5
    agent_timeout_seconds: int = 300
    
    # API Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Ensure directories exist
os.makedirs(settings.agents_dir, exist_ok=True)
os.makedirs(settings.logs_dir, exist_ok=True)
os.makedirs(settings.uploads_dir, exist_ok=True)
