import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("ai_analyst_backend.services.analysis.statistics")


def safe_float(val: Any) -> Optional[float]:
    """Converts a value to float, safely returning None for NaN, Inf, or unparseable values."""
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def calculate_numeric_summary(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Computes extended parametric and non-parametric statistics for all numeric columns.
    Includes mean, median, std, variance, IQR, skewness, and kurtosis.
    """
    summary: Dict[str, Dict[str, Any]] = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            summary[col] = {
                "count": 0,
                "null_count": int(df[col].isna().sum()),
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "max": None
            }
            continue

        q25 = safe_float(series.quantile(0.25))
        q75 = safe_float(series.quantile(0.75))
        iqr = safe_float(q75 - q25) if (q25 is not None and q75 is not None) else None
        variance = safe_float(series.var())
        skew = safe_float(series.skew()) if len(series) > 2 else None
        kurt = safe_float(series.kurt()) if len(series) > 3 else None

        summary[col] = {
            "count": int(len(series)),
            "null_count": int(df[col].isna().sum()),
            "null_percentage": round((df[col].isna().sum() / len(df)) * 100, 2),
            "mean": safe_float(series.mean()),
            "median": safe_float(series.median()),
            "std": safe_float(series.std()),
            "variance": variance,
            "min": safe_float(series.min()),
            "q25": q25,
            "q75": q75,
            "max": safe_float(series.max()),
            "iqr": iqr,
            "skewness": skew,
            "kurtosis": kurt
        }

    return summary


def calculate_categorical_summary(df: pd.DataFrame, max_categories: int = 10) -> Dict[str, Dict[str, Any]]:
    """
    Computes distribution counts and frequencies for non-numeric columns.
    """
    summary: Dict[str, Dict[str, Any]] = {}
    non_numeric_cols = df.select_dtypes(exclude=[np.number]).columns

    for col in non_numeric_cols:
        series = df[col]
        total_len = len(df)
        null_count = int(series.isna().sum())
        non_null_series = series.dropna().astype(str)
        unique_count = int(non_null_series.nunique())

        val_counts = non_null_series.value_counts().head(max_categories)
        top_categories = []
        for val, count in val_counts.items():
            top_categories.append({
                "value": str(val),
                "count": int(count),
                "percentage": round((count / total_len) * 100, 2)
            })

        summary[col] = {
            "count": int(len(non_null_series)),
            "null_count": null_count,
            "null_percentage": round((null_count / total_len) * 100, 2) if total_len > 0 else 0,
            "unique_count": unique_count,
            "top_categories": top_categories
        }

    return summary


def compute_correlation_matrix(df: pd.DataFrame, threshold: float = 0.4) -> Dict[str, Any]:
    """
    Calculates the Pearson correlation matrix for all numeric columns,
    identifying statistically meaningful pairs sorted by absolute correlation strength.
    """
    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2 or len(numeric_df) < 3:
        return {"matrix": {}, "significant_pairs": []}

    corr_df = numeric_df.corr(method="pearson")
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    for col in corr_df.columns:
        matrix[col] = {}
        for row in corr_df.index:
            val = corr_df.loc[row, col]
            matrix[col][row] = safe_float(val)

    significant_pairs: List[Dict[str, Any]] = []
    cols = list(corr_df.columns)
    seen_pairs = set()

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            col1 = cols[i]
            col2 = cols[j]
            r = corr_df.loc[col1, col2]
            if pd.isna(r):
                continue

            r_val = float(r)
            if abs(r_val) >= threshold:
                if r_val >= 0.7:
                    strength = "strong positive"
                elif r_val >= 0.4:
                    strength = "moderate positive"
                elif r_val <= -0.7:
                    strength = "strong negative"
                else:
                    strength = "moderate negative"

                pair_key = tuple(sorted([col1, col2]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    significant_pairs.append({
                        "column_1": col1,
                        "column_2": col2,
                        "correlation": round(r_val, 4),
                        "strength": strength,
                        "interpretation": f"{col1} and {col2} exhibit a {strength} correlation (r={round(r_val, 2)})."
                    })

    significant_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return {
        "matrix": matrix,
        "significant_pairs": significant_pairs
    }


def compute_temporal_trends(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detects datetime columns and computes trend summaries such as date ranges,
    overall trajectory, and sample period metrics.
    """
    trends: List[Dict[str, Any]] = []

    for col in df.columns:
        is_datetime = False
        parsed_dates = None

        if pd.api.types.is_datetime64_any_dtype(df[col]):
            is_datetime = True
            parsed_dates = df[col].dropna()
        else:
            # Check if column name or samples look like dates
            lower_name = col.lower()
            if any(term in lower_name for term in ["date", "time", "timestamp", "year", "month"]):
                try:
                    converted = pd.to_datetime(df[col], errors="coerce")
                    if converted.notna().sum() > len(df) * 0.5:
                        is_datetime = True
                        parsed_dates = converted.dropna()
                except Exception:
                    pass

        if is_datetime and parsed_dates is not None and len(parsed_dates) > 2:
            min_date = parsed_dates.min()
            max_date = parsed_dates.max()
            span_days = int((max_date - min_date).days) if hasattr(max_date - min_date, "days") else 0

            # Determine temporal frequency
            trends.append({
                "column": col,
                "min_date": str(min_date),
                "max_date": str(max_date),
                "span_days": span_days,
                "non_null_records": int(len(parsed_dates)),
                "is_chronological": bool(parsed_dates.is_monotonic_increasing)
            })

    return trends


def calculate_dataset_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Orchestrates complete statistical computation across numeric, categorical,
    correlation, and temporal dimensions.
    """
    logger.info(f"Computing dataset statistics for {len(df)} rows and {len(df.columns)} columns.")
    numeric_stats = calculate_numeric_summary(df)
    categorical_stats = calculate_categorical_summary(df)
    correlations = compute_correlation_matrix(df)
    trends = compute_temporal_trends(df)

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_summary": numeric_stats,
        "categorical_summary": categorical_stats,
        "correlations": correlations,
        "temporal_trends": trends
    }


# ==============================================================================
# FILE SUMMARY: backend/services/analysis/statistics.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides statistical analysis services for tabular datasets:
#   1. calculate_numeric_summary(): Computes parametric and non-parametric stats
#      (mean, median, std, variance, IQR, skewness, kurtosis, quartiles).
#   2. calculate_categorical_summary(): Computes frequency distributions, unique counts,
#      and percentage breakdowns for text/category columns.
#   3. compute_correlation_matrix(): Calculates Pearson correlation matrix and filters
#      statistically significant pairs with plain-English interpretations.
#   4. compute_temporal_trends(): Identifies datetime columns, date spans, and chronological ordering.
#   5. calculate_dataset_statistics(): Master aggregator generating the full statistical profile.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/api/datasets.py' endpoint GET /datasets/{dataset_id}/statistics.
# - Used by 'backend/services/analysis/visualizations.py' to inform intelligent chart recommendations.
# - Outputs dictionaries conforming to 'DatasetStatisticsResponse' in 'backend/models/schemas.py'.
# ==============================================================================
