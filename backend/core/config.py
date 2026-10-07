import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    SUPABASE_URL: str = "https://your-supabase-project.supabase.co"
    SUPABASE_ANON_KEY: str = "your-supabase-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "your-supabase-service-role-key"
    
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL_NAME: str = "qwen2.5:7b"
    LLM_API_KEY: Optional[str] = None
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    LLM_TIMEOUT_SECONDS: int = 60
    
    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(BASE_DIR, ".env"),
            os.path.join(BASE_DIR.parent, ".env")
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()


# ==============================================================================
# FILE SUMMARY: backend/core/config.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file manages application configuration and environment variables through
# Pydantic Settings ('BaseSettings'). It automatically reads settings from system
# environment variables or from a local '.env' file, supplying safe defaults for:
#   - Server environment mode ('ENVIRONMENT', 'PORT').
#   - Supabase connection secrets ('SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_ROLE_KEY').
#   - LLM provider configurations ('LLM_PROVIDER', 'LLM_MODEL_NAME', 'LLM_API_KEY',
#     'OLLAMA_BASE_URL', 'OPENAI_API_KEY', 'GEMINI_API_KEY', 'HUGGINGFACE_API_KEY',
#     'LLM_TIMEOUT_SECONDS').
#
# HOW IT CONNECTS TO OTHER FILES:
# - Exports the singleton 'settings' instance consumed across the entire backend:
#   - 'backend/main.py': Uses 'settings' to report environment status in the health check.
#   - 'backend/core/auth.py': Checks 'settings.ENVIRONMENT' to allow local mock authentication.
#   - 'backend/core/supabase_client.py': Passes URL and credentials to initialize Supabase.
#   - 'backend/api/datasets.py' and 'backend/services/datasets.py': Checks 'settings.SUPABASE_URL'
#     to determine whether to use live cloud storage/database or local mock mode.
#   - 'backend/services/ai/provider.py': Consumes LLM provider names, API keys, endpoints, and timeouts.
# ==============================================================================
