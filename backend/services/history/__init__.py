from services.history.diff import compute_dataframe_diff
from services.history.service import (
    list_dataset_versions,
    get_dataset_version,
    diff_dataset_versions,
    rollback_dataset_version,
    get_audit_timeline,
    register_dev_version,
    register_dev_operation,
    _DEV_VERSIONS_REGISTRY,
    _DEV_OPERATIONS_REGISTRY
)

__all__ = [
    "compute_dataframe_diff",
    "list_dataset_versions",
    "get_dataset_version",
    "diff_dataset_versions",
    "rollback_dataset_version",
    "get_audit_timeline",
    "register_dev_version",
    "register_dev_operation",
    "_DEV_VERSIONS_REGISTRY",
    "_DEV_OPERATIONS_REGISTRY"
]


# ==============================================================================
# FILE SUMMARY: backend/services/history/__init__.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file initializes the history and versioning package:
#   - Exposes version comparison and DataFrame diff computation ('compute_dataframe_diff').
#   - Exposes version listing, retrieval, diffing, rollback, and audit timeline
#     services ('list_dataset_versions', 'get_dataset_version', 'diff_dataset_versions',
#     'rollback_dataset_version', 'get_audit_timeline').
#   - Exposes development registries for local in-memory state tracking.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imported by API routes in 'backend/api/datasets.py'.
# - Tested in 'backend/tests/test_history.py'.
# ==============================================================================
