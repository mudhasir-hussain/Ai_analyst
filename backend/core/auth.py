import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from core.config import settings
from core.supabase_client import get_supabase

logger = logging.getLogger("ai_analyst_backend.auth")
security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_client: Client = Depends(get_supabase)
):
    if not credentials:
        logger.warning("Missing authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials are required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if settings.ENVIRONMENT == "development" and token == "mock-token":
        logger.info("Authenticated using local mock token")
        class MockUser:
            id = "00000000-0000-0000-0000-000000000000"
            email = "developer@local.test"
        return MockUser()

    try:
        user_response = supabase_client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session could not be verified.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_response.user
        
    except Exception as e:
        logger.error(f"Supabase JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==============================================================================
# FILE SUMMARY: backend/core/auth.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the central authentication dependency ('get_current_user') for
# FastAPI routes. It extracts bearer JWT tokens from incoming HTTP Authorization
# headers and verifies them against Supabase Auth.
#   - If a valid token is provided, it returns the verified Supabase User object.
#   - If the request lacks a token, it raises an HTTP 401 Unauthorized error.
#   - For friction-free local development and automated testing, if ENVIRONMENT is
#     'development' and the bearer token equals 'mock-token', it returns a mock user.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Injected as a FastAPI dependency ('Depends(get_current_user)') into endpoints
#   across 'backend/api/datasets.py' and 'backend/main.py' to enforce route security.
# - Reads environment settings from 'backend/core/config.py' (such as ENVIRONMENT).
# - Uses the Supabase client accessor 'get_supabase' from 'backend/core/supabase_client.py'
#   to execute Supabase Auth validation ('supabase_client.auth.get_user(token)').
# ==============================================================================
