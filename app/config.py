"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_key: str = "your-secret-api-key-here"
    port: int = 8000
    
    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "google", "ollama", "groq", "grok"] = "groq"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    google_api_key: str | None = None
    google_model: str = "gemini-3-flash-preview"
    
    # Groq Configuration (FAST & FREE!)
    groq_api_key: str | None = None
    groq_backup_key: str | None = None  # Backup key for rate limit failover
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    
    # Grok (xAI) Configuration
    grok_api_key: str | None = None
    grok_model: str = "grok-3"
    grok_base_url: str = "https://api.x.ai/v1"
    
    # Ollama Configuration (for FREE local LLMs)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # GUVI Configuration
    guvi_callback_url: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Session Configuration
    session_timeout_seconds: int = 300
    max_conversation_turns: int = 30
    min_intelligence_items: int = 1  # Lowered from 2 to trigger callback faster
    
    # Application Settings
    log_level: str = "INFO"
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
