import logging
from supabase import create_client, Client
from core.config import settings

logger = logging.getLogger("ai_analyst_backend.supabase")

supabase: Client = None

try:
    logger.info("Initializing Supabase Client...")
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    logger.info("Supabase Client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    if settings.ENVIRONMENT == "production":
        raise e

def get_supabase() -> Client:
    if supabase is None:
        raise RuntimeError("Supabase client is not initialized. Check your environment configurations.")
    return supabase


# ==============================================================================
# FILE SUMMARY: backend/core/supabase_client.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This module initializes and exposes the client connection to Supabase using the
# official 'supabase-py' SDK. It reads project credentials from the configuration
# settings and exposes two access mechanisms:
#   1. A module-level global instance ('supabase') for direct queries and storage calls.
#   2. A FastAPI dependency function ('get_supabase') for dependency-injected route access.
# If initialization fails in development mode (e.g. placeholder keys), it logs a warning
# without crashing the process, but strictly raises errors in production mode.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports 'settings' from 'backend/core/config.py' for 'SUPABASE_URL' and 'SUPABASE_ANON_KEY'.
# - Used by 'backend/core/auth.py' via 'get_supabase' to authenticate user JWT tokens.
# - Used by 'backend/api/datasets.py' and 'backend/services/datasets.py' to upload raw files
#   to Supabase Storage ('supabase.storage.from_("datasets")') and manage database rows
#   in the 'datasets' and 'dataset_versions' PostgreSQL tables.
# ==============================================================================
