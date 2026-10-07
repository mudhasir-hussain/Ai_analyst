import re
import logging
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger("ai_analyst_backend.services.profiling")

PII_PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    "phone": re.compile(r"^\+?[\d\s\-\(\)]{7,15}$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "credit_card": re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$"),
    "zipcode": re.compile(r"^\d{5}(-\d{4})?$")
}

PII_KEYWORD_NAMES = {
    "email": ["email", "e-mail", "mail_addr"],
    "phone": ["phone", "telephone", "mobile", "cell", "fax"],
    "ssn": ["ssn", "social_security", "social_sec"],
    "credit_card": ["card_num", "credit_card", "cardnumber", "cc_num"],
    "zipcode": ["zipcode", "zip_code", "postal_code", "zip"]
}

def detect_pii(col_name: str, series: pd.Series) -> List[str]:
    detected_types = set()
    clean_col_name = col_name.lower().strip()

    for pii_type, keywords in PII_KEYWORD_NAMES.items():
        if any(kw in clean_col_name for kw in keywords):
            detected_types.add(pii_type)

    non_null_samples = series.dropna().astype(str).head(50)
    if not non_null_samples.empty:
        for pii_type, pattern in PII_PATTERNS.items():
            matches = non_null_samples.apply(lambda val: bool(pattern.match(val.strip())))
            if matches.sum() / len(non_null_samples) >= 0.3:
                detected_types.add(pii_type)

    return sorted(list(detected_types))

def generate_extended_profile(df: pd.DataFrame) -> Dict[str, Any]:
    row_count = len(df)
    col_count = len(df.columns)
    total_cells = row_count * col_count
    total_nulls = int(df.isna().sum().sum())
    null_pct = round((total_nulls / total_cells * 100), 2) if total_cells > 0 else 0.0
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / row_count * 100), 2) if row_count > 0 else 0.0
    memory_bytes = int(df.memory_usage(deep=True).sum())

    columns_profile = {}
    candidate_keys = []

    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        col_null_pct = round((null_count / row_count * 100), 2) if row_count > 0 else 0.0
        unique_count = int(series.nunique())
        unique_pct = round((unique_count / row_count * 100), 2) if row_count > 0 else 0.0

        if unique_count == row_count and null_count == 0 and row_count > 0:
            candidate_keys.append(str(col))

        dtype_str = str(series.dtype)
        if "int" in dtype_str or "float" in dtype_str:
            inferred_type = "numeric"
        elif "bool" in dtype_str:
            inferred_type = "boolean"
        elif "datetime" in dtype_str:
            inferred_type = "datetime"
        else:
            if unique_pct < 10.0 and unique_count < 50:
                inferred_type = "categorical"
            else:
                inferred_type = "text"

        pii_flags = detect_pii(str(col), series)

        col_stats: Dict[str, Any] = {
            "type": inferred_type,
            "null_count": null_count,
            "null_percentage": col_null_pct,
            "unique_count": unique_count,
            "unique_percentage": unique_pct,
            "pii_detected": pii_flags,
        }

        if inferred_type == "numeric":
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            if not num_series.empty:
                q25, q50, q75 = num_series.quantile([0.25, 0.50, 0.75])
                col_stats.update({
                    "min": float(num_series.min()),
                    "max": float(num_series.max()),
                    "mean": float(round(num_series.mean(), 4)),
                    "median": float(round(num_series.median(), 4)),
                    "std": float(round(num_series.std(), 4)) if len(num_series) > 1 else 0.0,
                    "quantiles": {
                        "25%": float(round(q25, 4)),
                        "50%": float(round(q50, 4)),
                        "75%": float(round(q75, 4))
                    }
                })
        elif inferred_type == "categorical":
            val_counts = series.value_counts(dropna=False).head(5)
            col_stats["top_categories"] = [
                {"value": str(k) if pd.notna(k) else "<NULL>", "count": int(v)} for k, v in val_counts.items()
            ]
        elif inferred_type == "text":
            text_lengths = series.dropna().astype(str).str.len()
            if not text_lengths.empty:
                col_stats.update({
                    "min_length": int(text_lengths.min()),
                    "max_length": int(text_lengths.max()),
                    "avg_length": float(round(text_lengths.mean(), 2))
                })
        elif inferred_type == "datetime":
            dt_series = pd.to_datetime(series, errors="coerce").dropna()
            if not dt_series.empty:
                col_stats.update({
                    "min_date": str(dt_series.min()),
                    "max_date": str(dt_series.max())
                })

        columns_profile[str(col)] = col_stats

    return {
        "row_count": row_count,
        "column_count": col_count,
        "estimated_memory_bytes": memory_bytes,
        "estimated_memory_mb": round(memory_bytes / (1024 * 1024), 2),
        "total_null_cells": total_nulls,
        "null_percentage": null_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_pct,
        "candidate_keys": candidate_keys,
        "columns": columns_profile
    }

def evaluate_dataset_health(df: pd.DataFrame, profile: Dict[str, Any]) -> Dict[str, Any]:
    row_count = profile["row_count"]
    issues: List[Dict[str, Any]] = []
    score_deductions = 0

    duplicate_pct = profile["duplicate_percentage"]
    if duplicate_pct > 0:
        deduction = min(15, int(duplicate_pct * 1.5) + 5)
        score_deductions += deduction
        issues.append({
            "code": "DUPLICATE_ROWS",
            "level": "warning" if duplicate_pct < 10 else "critical",
            "column": None,
            "message": f"Dataset contains {profile['duplicate_rows']} duplicate rows ({duplicate_pct}%).",
            "metric_value": duplicate_pct,
            "recommendation": "Remove duplicate rows using deduplication cleaning tool."
        })

    for col_name, stats in profile["columns"].items():
        null_pct = stats["null_percentage"]
        if null_pct == 100.0:
            score_deductions += 10
            issues.append({
                "code": "EMPTY_COLUMN",
                "level": "critical",
                "column": col_name,
                "message": f"Column '{col_name}' is 100% empty (all values missing).",
                "metric_value": 100.0,
                "recommendation": f"Drop empty column '{col_name}'."
            })
        elif null_pct >= 20.0:
            score_deductions += 5
            issues.append({
                "code": "HIGH_MISSINGNESS",
                "level": "warning",
                "column": col_name,
                "message": f"Column '{col_name}' has {null_pct}% missing values.",
                "metric_value": null_pct,
                "recommendation": f"Fill missing values in '{col_name}' or consider dropping."
            })

    for col_name, stats in profile["columns"].items():
        if stats["unique_count"] == 1 and row_count > 1:
            score_deductions += 5
            issues.append({
                "code": "CONSTANT_COLUMN",
                "level": "info",
                "column": col_name,
                "message": f"Column '{col_name}' contains a single constant value for all rows.",
                "metric_value": 1.0,
                "recommendation": f"Consider dropping constant column '{col_name}'."
            })

    for col_name, stats in profile["columns"].items():
        if stats["type"] == "numeric" and row_count > 5:
            num_series = pd.to_numeric(df[col_name], errors="coerce").dropna()
            if len(num_series) > 5:
                q25 = num_series.quantile(0.25)
                q75 = num_series.quantile(0.75)
                iqr = q75 - q25
                if iqr > 0:
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers = num_series[(num_series < lower_bound) | (num_series > upper_bound)]
                    outlier_count = len(outliers)
                    outlier_pct = round((outlier_count / len(num_series) * 100), 2)
                    if outlier_pct >= 2.0:
                        score_deductions += 3
                        issues.append({
                            "code": "OUTLIERS_DETECTED",
                            "level": "warning",
                            "column": col_name,
                            "message": f"Column '{col_name}' has {outlier_count} potential outliers ({outlier_pct}%) via IQR method.",
                            "metric_value": outlier_pct,
                            "recommendation": f"Inspect and clip or remove outliers in '{col_name}'."
                        })

    for col_name, stats in profile["columns"].items():
        if stats["pii_detected"]:
            pii_list = ", ".join(stats["pii_detected"])
            issues.append({
                "code": "PII_DETECTED",
                "level": "warning",
                "column": col_name,
                "message": f"Column '{col_name}' contains sensitive PII data: {pii_list}.",
                "metric_value": len(stats["pii_detected"]),
                "recommendation": f"Anonymize or drop sensitive PII column '{col_name}' before exporting."
            })

    health_score = max(0, min(100, 100 - score_deductions))

    if health_score >= 85:
        rating = "excellent"
    elif health_score >= 70:
        rating = "good"
    elif health_score >= 50:
        rating = "fair"
    else:
        rating = "poor"

    return {
        "health_score": health_score,
        "rating": rating,
        "total_issues": len(issues),
        "issues": issues
    }


# ==============================================================================
# FILE SUMMARY: backend/services/profiling.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file is the mathematical and heuristic engine that inspects tabular data to
# generate statistical profiles and calculate data health scores:
#   1. PII Detection ('detect_pii'): Evaluates column names and non-null string samples
#      using regular expressions and keyword lookups to detect emails, phone numbers,
#      social security numbers, credit cards, and zip codes.
#   2. Extended Profiling ('generate_extended_profile'): Calculates comprehensive
#      metrics for the dataset (row count, column count, memory footprint, null count/%,
#      duplicate row count/%, candidate primary keys) and column-level metrics (mean,
#      median, std, 25%/50%/75% quantiles for numeric columns; top frequency categories
#      for categorical columns; min/max/average string length for text columns; min/max
#      dates for datetime columns).
#   3. Quality Health Evaluation ('evaluate_dataset_health'): Computes an overall health
#      score on a 0-100 scale, categorizes it ('excellent', 'good', 'fair', 'poor'), and
#      generates an issues list with severity levels ('critical', 'warning', 'info')
#      and actionable remediation recommendations by checking for duplicates, missingness,
#      constant columns, IQR-based statistical outliers, and exposed PII.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Called by 'backend/services/datasets.py' inside 'generate_profile_and_schema' to
#   generate version snapshot summaries when datasets are uploaded.
# - The resulting dictionaries are structured to fulfill the response contracts defined in
#   'backend/models/schemas.py' ('DatasetProfileResponse', 'DatasetHealthResponse').
# - Directly verified by automated tests in 'backend/tests/test_profiling.py'.
# ==============================================================================
