import logging
from fastapi import APIRouter, Depends
from pydantic import UUID4
from core.auth import get_current_user
from models.schemas import ReportResponse
from services.reports import get_dataset_report

logger = logging.getLogger("ai_analyst_backend.api.reports")
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_by_id(
    report_id: UUID4,
    current_user = Depends(get_current_user)
):
    """
    Retrieves a previously generated executive data analysis report by its unique ID.
    """
    logger.info(f"User {current_user.id} requested report {report_id}")
    return get_dataset_report(report_id)


# ==============================================================================
# FILE SUMMARY: backend/api/reports.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the HTTP route for retrieving generated reports:
#   - GET /reports/{report_id}: Retrieves a report record by its UUID, returning
#     structured metadata, executive findings, and formatted Markdown or HTML document body.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Mounted into the main FastAPI application in 'backend/main.py'.
# - Protected by authentication via 'get_current_user' from 'backend/core/auth.py'.
# - Delegates report lookup to 'get_dataset_report' in 'backend/services/reports/'.
# - Returns Pydantic 'ReportResponse' schema from 'backend/models/schemas.py'.
# ==============================================================================
