import logging
from typing import Dict, Any, List
import pandas as pd
from pydantic import UUID4
from models.schemas import VersionDiffColumnChange, VersionDiffResponse
from services.datasets import infer_column_type

logger = logging.getLogger("ai_analyst_backend.services.history.diff")


def compute_dataframe_diff(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    source_version_id: UUID4,
    source_version_number: int,
    target_version_id: UUID4,
    target_version_number: int,
    dataset_id: UUID4
) -> VersionDiffResponse:
    """
    Computes a comprehensive semantic diff between two version snapshot DataFrames.
    """
    logger.info(
        f"Diffing dataset {dataset_id}: v{source_version_number} ({source_version_id}) "
        f"vs v{target_version_number} ({target_version_id})"
    )

    rows_source = len(source_df)
    rows_target = len(target_df)
    rows_diff = rows_target - rows_source

    source_cols = list(source_df.columns)
    target_cols = list(target_df.columns)

    added_cols = [c for c in target_cols if c not in source_cols]
    removed_cols = [c for c in source_cols if c not in target_cols]
    common_cols = [c for c in source_cols if c in target_cols]

    columns_diff = len(target_cols) - len(source_cols)
    type_changed_cols = []
    column_changes: List[VersionDiffColumnChange] = []

    # Added columns
    for col in added_cols:
        col_type = infer_column_type(target_df[col])
        null_count = int(target_df[col].isna().sum())
        column_changes.append(
            VersionDiffColumnChange(
                column=col,
                change_type="added",
                source_type=None,
                target_type=col_type,
                source_null_count=None,
                target_null_count=null_count,
                null_delta=null_count,
                stats_delta={}
            )
        )

    # Removed columns
    for col in removed_cols:
        col_type = infer_column_type(source_df[col])
        null_count = int(source_df[col].isna().sum())
        column_changes.append(
            VersionDiffColumnChange(
                column=col,
                change_type="removed",
                source_type=col_type,
                target_type=None,
                source_null_count=null_count,
                target_null_count=None,
                null_delta=-null_count,
                stats_delta={}
            )
        )

    # Common columns
    total_null_delta = 0
    for col in common_cols:
        s_series = source_df[col]
        t_series = target_df[col]

        s_type = infer_column_type(s_series)
        t_type = infer_column_type(t_series)

        s_nulls = int(s_series.isna().sum())
        t_nulls = int(t_series.isna().sum())
        null_delta = t_nulls - s_nulls
        total_null_delta += null_delta

        stats_delta: Dict[str, Any] = {}
        if s_type == "numeric" and t_type == "numeric":
            s_clean = s_series.dropna()
            t_clean = t_series.dropna()
            if not s_clean.empty and not t_clean.empty:
                s_mean = float(s_clean.mean())
                t_mean = float(t_clean.mean())
                stats_delta["mean_delta"] = round(t_mean - s_mean, 4)

                s_min = float(s_clean.min())
                t_min = float(t_clean.min())
                stats_delta["min_delta"] = round(t_min - s_min, 4)

                s_max = float(s_clean.max())
                t_max = float(t_clean.max())
                stats_delta["max_delta"] = round(t_max - s_max, 4)

        if s_type != t_type:
            type_changed_cols.append(col)
            change_type = "type_changed"
        elif null_delta != 0 or bool(stats_delta):
            change_type = "modified"
        elif len(s_series) == len(t_series) and s_series.equals(t_series):
            change_type = "unchanged"
        else:
            change_type = "modified"

        column_changes.append(
            VersionDiffColumnChange(
                column=col,
                change_type=change_type,
                source_type=s_type,
                target_type=t_type,
                source_null_count=s_nulls,
                target_null_count=t_nulls,
                null_delta=null_delta,
                stats_delta=stats_delta
            )
        )

    # Generate plain-English summary
    summary_parts = []
    if rows_diff > 0:
        summary_parts.append(f"Row count increased by {rows_diff} (from {rows_source} to {rows_target}).")
    elif rows_diff < 0:
        summary_parts.append(f"Row count decreased by {abs(rows_diff)} (from {rows_source} to {rows_target}).")
    else:
        summary_parts.append(f"Row count remained constant at {rows_source}.")

    if added_cols:
        summary_parts.append(f"Added {len(added_cols)} column(s): {', '.join(added_cols)}.")
    if removed_cols:
        summary_parts.append(f"Removed {len(removed_cols)} column(s): {', '.join(removed_cols)}.")
    if type_changed_cols:
        summary_parts.append(f"Data type changed for {len(type_changed_cols)} column(s): {', '.join(type_changed_cols)}.")

    if total_null_delta < 0:
        summary_parts.append(f"Data quality improved: {abs(total_null_delta)} null values were resolved/filled.")
    elif total_null_delta > 0:
        summary_parts.append(f"Null values increased by {total_null_delta}.")

    if not summary_parts:
        summary_text = f"No structural differences detected between v{source_version_number} and v{target_version_number}."
    else:
        summary_text = f"Comparing v{source_version_number} to v{target_version_number}: " + " ".join(summary_parts)

    return VersionDiffResponse(
        dataset_id=dataset_id,
        source_version_id=source_version_id,
        source_version_number=source_version_number,
        target_version_id=target_version_id,
        target_version_number=target_version_number,
        rows_source=rows_source,
        rows_target=rows_target,
        rows_diff=rows_diff,
        columns_source=len(source_cols),
        columns_target=len(target_cols),
        columns_diff=columns_diff,
        added_columns=added_cols,
        removed_columns=removed_cols,
        type_changed_columns=type_changed_cols,
        column_changes=column_changes,
        summary=summary_text
    )


# ==============================================================================
# FILE SUMMARY: backend/services/history/diff.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the semantic dataset version comparison engine:
#   1. compute_dataframe_diff(): Evaluates two version snapshot DataFrames and identifies:
#      - Row count differences (additions/deletions/filtering).
#      - Column schema modifications (added, removed, type conversions).
#      - Missing value shifts (null count deltas per column and across dataset).
#      - Numerical parametric metric deltas (mean, min, max deltas).
#   2. Formulates an executive, plain-English change summary explaining the delta
#      between version A and version B.
#   3. Returns structured 'VersionDiffResponse' conforming to backend schemas.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/services/history/service.py' for GET /datasets/{dataset_id}/versions/{version_id}/diff.
# - Leverages 'infer_column_type' from 'backend/services/datasets.py' for type classification.
# - Populates Pydantic models 'VersionDiffColumnChange' and 'VersionDiffResponse'
#   from 'backend/models/schemas.py'.
# ==============================================================================
