from services.reports.insights import generate_narrative_insights
from services.reports.generator import (
    generate_dataset_report,
    get_dataset_report,
    render_markdown_report,
    render_html_report,
    _DEV_REPORTS_CACHE
)
from services.reports.exporter import export_dataset

__all__ = [
    "generate_narrative_insights",
    "generate_dataset_report",
    "get_dataset_report",
    "render_markdown_report",
    "render_html_report",
    "export_dataset",
    "_DEV_REPORTS_CACHE"
]


# ==============================================================================
# FILE SUMMARY: backend/services/reports/__init__.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file initializes the reports and export package:
#   - Exposes narrative insight generator ('generate_narrative_insights').
#   - Exposes multi-format report generator ('generate_dataset_report', 'get_dataset_report').
#   - Exposes dataset exporter ('export_dataset').
#
# HOW IT CONNECTS TO OTHER FILES:
# - Consumed by report and export API routes in 'backend/api/datasets.py'.
# - Tested in 'backend/tests/test_reports.py'.
# ==============================================================================
