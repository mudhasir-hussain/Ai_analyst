import time
import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from core.exceptions import DatasetValidationError

logger = logging.getLogger("ai_analyst_backend.services.transformations")

ALLOWED_OPERATION_TYPES = {
    "rename_column",
    "drop_columns",
    "drop_column",
    "select_columns",
    "convert_type",
    "fill_missing",
    "drop_missing_rows",
    "remove_duplicates",
    "trim_text",
    "normalize_case",
    "numeric_round",
    "clip_values",
    "parse_date",
    "create_date_part",
    "handle_outliers",
    "replace_values"
}

def apply_single_operation(df: pd.DataFrame, operation: Dict[str, Any]) -> Tuple[pd.DataFrame, int, List[str]]:
    op_type = operation.get("type")
    if not op_type or op_type not in ALLOWED_OPERATION_TYPES:
        raise DatasetValidationError(
            detail=f"Unsupported or missing operation type '{op_type}'. Allowed types: {sorted(list(ALLOWED_OPERATION_TYPES))}",
            error_code="INVALID_OPERATION_TYPE"
        )

    cells_modified = 0
    affected_cols: List[str] = []

    if op_type == "rename_column":
        col = operation.get("column")
        new_name = operation.get("new_name")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")
        if not new_name or not str(new_name).strip():
            raise DatasetValidationError("Parameter 'new_name' cannot be blank.", "INVALID_PARAMETER")
        new_name = str(new_name).strip()
        if new_name in df.columns and new_name != col:
            raise DatasetValidationError(f"Column with name '{new_name}' already exists.", "DUPLICATE_COLUMN_NAME")
        
        df = df.rename(columns={col: new_name})
        affected_cols = [col, new_name]

    elif op_type in ("drop_columns", "drop_column"):
        cols = operation.get("columns") or ([operation.get("column")] if operation.get("column") else [])
        if not cols or not isinstance(cols, list):
            raise DatasetValidationError("Parameter 'columns' must be a non-empty list of column names.", "INVALID_PARAMETER")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        if len(cols) >= len(df.columns):
            raise DatasetValidationError("Cannot drop all columns from the dataset.", "INVALID_OPERATION")
        
        df = df.drop(columns=cols)
        affected_cols = cols

    elif op_type == "select_columns":
        cols = operation.get("columns") or ([operation.get("column")] if operation.get("column") else [])
        if not cols or not isinstance(cols, list):
            raise DatasetValidationError("Parameter 'columns' must be a non-empty list of column names.", "INVALID_PARAMETER")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        
        df = df[cols].copy()
        affected_cols = cols

    elif op_type == "convert_type":
        col = operation.get("column")
        target_type = operation.get("target_type")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")
        
        valid_targets = {"numeric", "text", "datetime", "boolean", "categorical"}
        if target_type not in valid_targets:
            raise DatasetValidationError(f"Target type '{target_type}' is invalid. Allowed: {valid_targets}", "INVALID_PARAMETER")
        
        orig_series = df[col].copy()
        if target_type == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif target_type == "text":
            df[col] = df[col].astype(str).replace({"nan": None, "None": None, "<NA>": None})
        elif target_type == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif target_type == "boolean":
            bool_map = {"true": True, "1": True, "yes": True, "y": True, 1: True, 1.0: True,
                        "false": False, "0": False, "no": False, "n": False, 0: False, 0.0: False}
            df[col] = df[col].map(lambda v: bool_map.get(str(v).lower().strip() if pd.notna(v) else v, v)).astype("boolean")
        elif target_type == "categorical":
            df[col] = df[col].astype("category")

        cells_modified = int((orig_series != df[col]).sum())
        affected_cols = [col]

    elif op_type == "fill_missing":
        col = operation.get("column")
        strategy = operation.get("strategy", "constant")
        val = operation.get("value") if operation.get("value") is not None else operation.get("fill_value")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")

        null_mask = df[col].isna()
        cells_to_fill = int(null_mask.sum())

        if strategy == "constant":
            if val is None:
                raise DatasetValidationError("Parameter 'value' or 'fill_value' required when strategy is 'constant'.", "INVALID_PARAMETER")
            df[col] = df[col].fillna(val)
        elif strategy == "mean":
            numeric_col = pd.to_numeric(df[col], errors="coerce")
            if numeric_col.dropna().empty:
                raise DatasetValidationError(f"Cannot calculate mean on empty or non-numeric column '{col}'.", "INVALID_STRATEGY")
            df[col] = df[col].fillna(numeric_col.mean())
        elif strategy == "median":
            numeric_col = pd.to_numeric(df[col], errors="coerce")
            if numeric_col.dropna().empty:
                raise DatasetValidationError(f"Cannot calculate median on empty or non-numeric column '{col}'.", "INVALID_STRATEGY")
            df[col] = df[col].fillna(numeric_col.median())
        elif strategy == "mode":
            mode_vals = df[col].mode()
            if mode_vals.empty:
                raise DatasetValidationError(f"Cannot calculate mode on empty column '{col}'.", "INVALID_STRATEGY")
            df[col] = df[col].fillna(mode_vals.iloc[0])
        else:
            raise DatasetValidationError(f"Unsupported strategy '{strategy}'. Allowed: constant, mean, median, mode.", "INVALID_STRATEGY")

        cells_modified = cells_to_fill
        affected_cols = [col]

    elif op_type == "drop_missing_rows":
        subset = operation.get("columns") or ([operation.get("column")] if operation.get("column") else None)
        how = operation.get("how", "any")
        if subset:
            missing = [c for c in subset if c not in df.columns]
            if missing:
                raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        if how not in {"any", "all"}:
            raise DatasetValidationError("Parameter 'how' must be 'any' or 'all'.", "INVALID_PARAMETER")
        
        orig_len = len(df)
        df = df.dropna(subset=subset, how=how).reset_index(drop=True)
        cells_modified = (orig_len - len(df)) * len(df.columns)
        affected_cols = subset or list(df.columns)

    elif op_type == "remove_duplicates":
        subset = operation.get("subset") or operation.get("columns") or ([operation.get("column")] if operation.get("column") else None)
        keep = operation.get("keep", "first")
        if subset:
            missing = [c for c in subset if c not in df.columns]
            if missing:
                raise DatasetValidationError(f"Subset columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        if keep not in {"first", "last", False}:
            raise DatasetValidationError("Parameter 'keep' must be 'first', 'last', or false.", "INVALID_PARAMETER")
        
        orig_len = len(df)
        df = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
        cells_modified = (orig_len - len(df)) * len(df.columns)
        affected_cols = subset or list(df.columns)

    elif op_type == "trim_text":
        cols = operation.get("columns") or ([operation.get("column")] if operation.get("column") else [])
        if not cols:
            raise DatasetValidationError("Parameter 'columns' or 'column' cannot be empty.", "INVALID_PARAMETER")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        
        for c in cols:
            if pd.api.types.is_numeric_dtype(df[c]):
                raise DatasetValidationError(
                    f"Column '{c}' is numeric ({df[c].dtype}). Text trimming can only be applied to text columns.",
                    "INVALID_COLUMN_TYPE"
                )
            series = df[c]
            mask = series.notna() & series.apply(lambda v: isinstance(v, str))
            if not mask.any():
                continue
            trimmed = series.astype(str).str.strip()
            diff_count = int((series != trimmed).sum())
            df[c] = df[c].astype(object)
            df.loc[mask, c] = trimmed.loc[mask]
            cells_modified += diff_count
        affected_cols = cols

    elif op_type == "normalize_case":
        cols = operation.get("columns") or ([operation.get("column")] if operation.get("column") else [])
        case = operation.get("case") or operation.get("case_type") or "lower"
        if not cols:
            raise DatasetValidationError("Parameter 'columns' or 'column' cannot be empty.", "INVALID_PARAMETER")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        if case not in {"upper", "lower", "title"}:
            raise DatasetValidationError("Parameter 'case' must be 'upper', 'lower', or 'title'.", "INVALID_PARAMETER")

        for c in cols:
            if pd.api.types.is_numeric_dtype(df[c]):
                raise DatasetValidationError(
                    f"Column '{c}' is numeric ({df[c].dtype}). Case normalization can only be applied to text columns.",
                    "INVALID_COLUMN_TYPE"
                )
            series = df[c]
            mask = series.notna() & series.apply(lambda v: isinstance(v, str))
            if not mask.any():
                continue
            if case == "upper":
                cased = series.astype(str).str.upper()
            elif case == "lower":
                cased = series.astype(str).str.lower()
            else:
                cased = series.astype(str).str.title()
            diff_count = int((series != cased).sum())
            df[c] = df[c].astype(object)
            df.loc[mask, c] = cased.loc[mask]
            cells_modified += diff_count
        affected_cols = cols

    elif op_type == "numeric_round":
        cols = operation.get("columns") or ([operation.get("column")] if operation.get("column") else [])
        decimals = operation.get("decimals", 2)
        if not cols:
            raise DatasetValidationError("Parameter 'columns' or 'column' cannot be empty.", "INVALID_PARAMETER")
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise DatasetValidationError(f"Columns not found in dataset: {missing}", "COLUMN_NOT_FOUND")
        if not isinstance(decimals, int) or decimals < 0:
            raise DatasetValidationError("Parameter 'decimals' must be a non-negative integer.", "INVALID_PARAMETER")

        for c in cols:
            num_series = pd.to_numeric(df[c], errors="coerce")
            rounded = num_series.round(decimals)
            diff_count = int((num_series != rounded).sum())
            df[c] = rounded
            cells_modified += diff_count
        affected_cols = cols

    elif op_type == "clip_values":
        col = operation.get("column")
        lower = operation.get("min_value")
        upper = operation.get("max_value")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")
        if lower is None and upper is None:
            raise DatasetValidationError("Provide at least one of 'min_value' or 'max_value' to clip.", "INVALID_PARAMETER")

        num_series = pd.to_numeric(df[col], errors="coerce")
        clipped = num_series.clip(lower=lower, upper=upper)
        cells_modified = int((num_series != clipped).sum())
        df[col] = clipped
        affected_cols = [col]

    elif op_type == "parse_date":
        col = operation.get("column")
        date_format = operation.get("date_format")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")

        orig_series = df[col].copy()
        df[col] = pd.to_datetime(df[col], format=date_format, errors="coerce")
        cells_modified = int((orig_series != df[col]).sum())
        affected_cols = [col]

    elif op_type == "create_date_part":
        col = operation.get("column")
        part = operation.get("part", "year")
        new_col = operation.get("new_column_name") or operation.get("new_column") or f"{col}_{part}"
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")

        valid_parts = {"year", "month", "day", "dayofweek", "hour"}
        if part not in valid_parts:
            raise DatasetValidationError(f"Date part '{part}' is invalid. Allowed: {valid_parts}", "INVALID_PARAMETER")

        dt_series = pd.to_datetime(df[col], errors="coerce")
        if part == "year":
            df[new_col] = dt_series.dt.year
        elif part == "month":
            df[new_col] = dt_series.dt.month
        elif part == "day":
            df[new_col] = dt_series.dt.day
        elif part == "dayofweek":
            df[new_col] = dt_series.dt.dayofweek
        elif part == "hour":
            df[new_col] = dt_series.dt.hour

        cells_modified = len(df)
        affected_cols = [col, new_col]

    elif op_type == "handle_outliers":
        col = operation.get("column")
        factor = float(operation.get("factor", 1.5))
        method = str(operation.get("method") or "").lower()
        action = operation.get("action") or ("drop" if "drop" in method else "clip")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")
        if action not in {"clip", "drop"}:
            raise DatasetValidationError("Parameter 'action' must be 'clip' or 'drop'.", "INVALID_PARAMETER")

        num_series = pd.to_numeric(df[col], errors="coerce")
        q25 = num_series.quantile(0.25)
        q75 = num_series.quantile(0.75)
        iqr = q75 - q25

        if pd.isna(iqr) or iqr == 0:
            logger.info(f"IQR for column '{col}' is zero or NaN; skipping outlier adjustments.")
            return df, 0, [col]

        lower_bound = q25 - factor * iqr
        upper_bound = q75 + factor * iqr

        if action == "clip":
            clipped = num_series.clip(lower=lower_bound, upper=upper_bound)
            cells_modified = int((num_series != clipped).sum())
            df[col] = clipped
        else:
            orig_len = len(df)
            mask = (num_series >= lower_bound) & (num_series <= upper_bound)
            df = df[mask].reset_index(drop=True)
            cells_modified = (orig_len - len(df)) * len(df.columns)

        affected_cols = [col]

    elif op_type == "replace_values":
        col = operation.get("column")
        old_val = operation.get("old_value")
        new_val = operation.get("new_value")
        if not col or col not in df.columns:
            raise DatasetValidationError(f"Column '{col}' not found in dataset.", "COLUMN_NOT_FOUND")

        match_count = int((df[col] == old_val).sum())
        df[col] = df[col].replace(old_val, new_val)
        cells_modified = match_count
        affected_cols = [col]

    return df, cells_modified, affected_cols

def execute_transformations(df: pd.DataFrame, operations: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    start_time = time.perf_counter()
    rows_before = len(df)
    cols_before = len(df.columns)
    
    transformed_df = df.copy()
    total_cells_modified = 0
    all_affected_columns = set()

    for idx, op in enumerate(operations):
        try:
            transformed_df, modified_count, affected = apply_single_operation(transformed_df, op)
            total_cells_modified += modified_count
            all_affected_columns.update(affected)
        except DatasetValidationError as dve:
            logger.warning(f"Transformation step {idx + 1} failed: {dve.detail}")
            raise dve
        except Exception as e:
            logger.error(f"Unexpected error in transformation step {idx + 1}: {e}")
            raise DatasetValidationError(
                detail=f"Error executing operation '{op.get('type')}': {str(e)}",
                error_code="TRANSFORMATION_FAILED"
            )

    rows_after = len(transformed_df)
    cols_after = len(transformed_df.columns)

    if rows_after == 0:
        raise DatasetValidationError("Transformation resulted in an empty dataset (0 rows remaining).", "EMPTY_RESULT_DATASET")
    if cols_after == 0:
        raise DatasetValidationError("Transformation resulted in 0 columns remaining.", "EMPTY_RESULT_DATASET")

    execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    impact_summary = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "columns_before": cols_before,
        "columns_after": cols_after,
        "rows_removed": max(0, rows_before - rows_after),
        "columns_removed": max(0, cols_before - cols_after),
        "cells_modified": total_cells_modified,
        "affected_columns": sorted(list(all_affected_columns)),
        "execution_time_ms": execution_time_ms
    }

    return transformed_df, impact_summary


# ==============================================================================
# FILE SUMMARY: backend/services/transformations.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file is the deterministic tabular cleaning and transformation execution engine.
# It receives a pandas DataFrame and a sequence of allowlisted structured operation
# dictionaries, validating parameters and executing changes deterministically:
#   - Structural edits: 'rename_column', 'drop_columns', 'select_columns'.
#   - Type casts: 'convert_type' (numeric, text, datetime, boolean, categorical).
#   - Null & Duplicate handling: 'fill_missing' (constant, mean, median, mode),
#     'drop_missing_rows', 'remove_duplicates'.
#   - Text & Value hygiene: 'trim_text', 'normalize_case', 'replace_values'.
#   - Numeric & Statistical adjustments: 'numeric_round', 'clip_values',
#     'handle_outliers' (IQR bounds clipping or row deletion).
#   - Temporal operations: 'parse_date', 'create_date_part' (year, month, day, etc.).
# For each transformation batch, it calculates a comprehensive impact summary:
# rows before/after, columns before/after, cells modified, and affected columns list.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/api/datasets.py' in the 'POST /datasets/{id}/transform' and
#   'POST /datasets/{id}/transform/preview' endpoints.
# - Raises 'DatasetValidationError' from 'backend/core/exceptions.py' if columns are missing
#   or parameters are invalid.
# - Outputs results formatted to fulfill 'TransformImpactSummary' in 'backend/models/schemas.py'.
# ==============================================================================
