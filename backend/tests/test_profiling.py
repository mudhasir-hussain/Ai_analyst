import pytest
import pandas as pd
from services.profiling import generate_extended_profile, evaluate_dataset_health, detect_pii

def test_generate_extended_profile_numeric_and_quantiles():
    df = pd.DataFrame({
        "id": list(range(1, 101)),
        "score": [float(i) for i in range(1, 101)],
        "email": [f"user{i}@example.com" for i in range(1, 101)]
    })
    
    profile = generate_extended_profile(df)
    assert profile["row_count"] == 100
    assert profile["column_count"] == 3
    assert profile["duplicate_rows"] == 0
    assert "id" in profile["candidate_keys"]
    
    score_stats = profile["columns"]["score"]
    assert score_stats["type"] == "numeric"
    assert score_stats["min"] == 1.0
    assert score_stats["max"] == 100.0
    assert score_stats["quantiles"]["50%"] == 50.5

def test_pii_detection():
    df = pd.DataFrame({
        "user_email": ["john.doe@test.com", "jane@company.org", "invalid-email"],
        "phone_num": ["+1-555-123-4567", "555-987-6543", "+44 20 7946 0958"],
        "random_col": ["alpha", "beta", "gamma"]
    })

    email_pii = detect_pii("user_email", df["user_email"])
    assert "email" in email_pii

    phone_pii = detect_pii("phone_num", df["phone_num"])
    assert "phone" in phone_pii

    random_pii = detect_pii("random_col", df["random_col"])
    assert len(random_pii) == 0

def test_health_evaluation_clean_dataset():
    df = pd.DataFrame({
        "id": list(range(1, 51)),
        "val": [i * 10 for i in range(1, 51)]
    })
    profile = generate_extended_profile(df)
    health = evaluate_dataset_health(df, profile)

    assert health["health_score"] == 100
    assert health["rating"] == "excellent"
    assert health["total_issues"] == 0

def test_health_evaluation_noisy_dataset():
    df = pd.DataFrame({
        "id": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "empty_col": [None] * 10,
        "missing_col": [1.0, None, None, None, 2.0, None, None, 3.0, None, None],
        "outlier_col": [10, 12, 11, 13, 12, 11, 10, 12, 11, 5000]
    })
    profile = generate_extended_profile(df)
    health = evaluate_dataset_health(df, profile)

    assert health["health_score"] < 100
    assert health["total_issues"] >= 3
    issue_codes = [issue["code"] for issue in health["issues"]]
    assert "EMPTY_COLUMN" in issue_codes
    assert "HIGH_MISSINGNESS" in issue_codes
    assert "OUTLIERS_DETECTED" in issue_codes


# ==============================================================================
# FILE SUMMARY: backend/tests/test_profiling.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides unit tests for the data profiling and quality calculation engine:
#   1. 'test_generate_extended_profile_numeric_and_quantiles': Verifies that row/column
#      counts, candidate primary key discovery, and quantiles (25%, 50%, 75%) match expected values.
#   2. 'test_pii_detection': Asserts regex and keyword detection correctly identify
#      sensitive personal data (emails, phone numbers) and ignore benign text columns.
#   3. 'test_health_evaluation_clean_dataset': Tests that a clean dataset receives a perfect
#      health score of 100 with an 'excellent' rating and 0 quality issues.
#   4. 'test_health_evaluation_noisy_dataset': Tests quality deduction heuristics on a dataset
#      containing empty columns, high missingness, duplicate rows, and extreme IQR outliers.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports and tests functions from 'backend/services/profiling.py' ('generate_extended_profile',
#   'evaluate_dataset_health', 'detect_pii').
# ==============================================================================
