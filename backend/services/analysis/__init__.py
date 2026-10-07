from services.analysis.statistics import (
    calculate_dataset_statistics,
    calculate_numeric_summary,
    calculate_categorical_summary,
    compute_correlation_matrix,
    compute_temporal_trends
)
from services.analysis.visualizations import (
    generate_chart_recommendations,
    build_visualization_data
)

__all__ = [
    "calculate_dataset_statistics",
    "calculate_numeric_summary",
    "calculate_categorical_summary",
    "compute_correlation_matrix",
    "compute_temporal_trends",
    "generate_chart_recommendations",
    "build_visualization_data"
]


# ==============================================================================
# FILE SUMMARY: backend/services/analysis/__init__.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file initializes the statistical analysis and visualization package:
#   - Exposes statistical computation functions ('calculate_dataset_statistics',
#     'compute_correlation_matrix', etc.).
#   - Exposes chart recommendation and visual data builder functions
#     ('generate_chart_recommendations', 'build_visualization_data').
#
# HOW IT CONNECTS TO OTHER FILES:
# - Consumed by API endpoints in 'backend/api/datasets.py' for GET /statistics
#   and POST /visualizations.
# - Tested in 'backend/tests/test_analysis.py'.
# ==============================================================================
