import logging
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.auth import get_current_user
from core.exceptions import AppException
from api.datasets import router as datasets_router
from api.reports import router as reports_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_analyst_backend")

app = FastAPI(
    title="AI Data Analyst API",
    description="Backend API for the AI Data Analyst portfolio project. Handles file parsing, data cleaning, stats calculation, and AI interactions.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException caught: [{exc.error_code}] - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code
        }
    )

app.include_router(datasets_router)
app.include_router(reports_router)

@app.get("/health", tags=["System"])
def health_check():
    logger.info("Health check endpoint hit")
    return {
        "status": "healthy",
        "service": "AI Data Analyst API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER
    }

@app.get("/projects", tags=["Projects"])
def list_projects(current_user = Depends(get_current_user)):
    logger.info(f"User {current_user.id} requested project list")
    return {
        "message": f"Successfully authenticated user {current_user.email}",
        "user_id": str(current_user.id),
        "projects": [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "name": "Sample Workspace",
                "description": "Your initial workspace for data analysis"
            }
        ]
    }


# Mount static production frontend build if available (e.g. Docker / Hugging Face Spaces)
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = "frontend_dist" if os.path.exists("frontend_dist") else None
if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith(("datasets", "reports", "health", "projects", "docs", "openapi.json")):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
        target_file = os.path.join(frontend_dist, full_path)
        if os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


# ==============================================================================
# FILE SUMMARY: backend/main.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file serves as the main application entry point for the FastAPI backend server:
#   1. Instantiates the 'FastAPI' application with title, version, and metadata.
#   2. Configures 'CORSMiddleware' to permit cross-origin requests from the React frontend.
#   3. Registers a centralized '@app.exception_handler' for 'AppException' that catches
#      all domain errors and returns uniform JSON error payloads with status codes and error codes.
#   4. Mounts the dataset and report routers ('datasets_router', 'reports_router').
#   5. Mounts compiled static frontend assets ('frontend_dist' or '../frontend/dist')
#      when containerized or deployed to Hugging Face Spaces.
#   6. Defines system-level endpoints:
#      - 'GET /health': Unauthenticated ping endpoint reporting environment and LLM provider.
#      - 'GET /projects': Authenticated demonstration endpoint validating Bearer token auth.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports and mounts 'datasets_router' from 'backend/api/datasets.py' and
#   'reports_router' from 'backend/api/reports.py'.
# - Uses 'get_current_user' from 'backend/core/auth.py' to protect authenticated routes.
# - Intercepts 'AppException' from 'backend/core/exceptions.py' raised across services and routers.
# - Reads runtime environment metadata from 'settings' in 'backend/core/config.py'.
# ==============================================================================
