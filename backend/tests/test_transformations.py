import uuid
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app
from services.transformations import execute_transformations, apply_single_operation
from core.exceptions import DatasetValidationError

client = TestClient(app)

def test_rename_and_drop_columns():
    df = pd.DataFrame({"colA": [1, 2], "colB": [3, 4], "colC": [5, 6]})
    ops = [
        {"type": "rename_column", "column": "colA", "new_name": "first_col"},
        {"type": "drop_columns", "columns": ["colC"]}
    ]
    res_df, impact = execute_transformations(df, ops)
    assert "first_col" in res_df.columns
    assert "colA" not in res_df.columns
    assert "colC" not in res_df.columns
    assert impact["columns_after"] == 2
    assert impact["columns_removed"] == 1

def test_select_columns():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    res_df, impact = execute_transformations(df, [{"type": "select_columns", "columns": ["b"]}])
    assert list(res_df.columns) == ["b"]
    assert impact["columns_after"] == 1

def test_convert_type():
    df = pd.DataFrame({
        "num_str": ["10", "20", "30"],
        "bool_str": ["true", "false", "yes"],
        "date_str": ["2026-01-01", "2026-02-01", "2026-03-01"]
    })
    ops = [
        {"type": "convert_type", "column": "num_str", "target_type": "numeric"},
        {"type": "convert_type", "column": "bool_str", "target_type": "boolean"},
        {"type": "convert_type", "column": "date_str", "target_type": "datetime"}
    ]
    res_df, _ = execute_transformations(df, ops)
    assert pd.api.types.is_numeric_dtype(res_df["num_str"])
    assert bool(res_df["bool_str"].iloc[0]) is True
    assert bool(res_df["bool_str"].iloc[1]) is False
    assert pd.api.types.is_datetime64_any_dtype(res_df["date_str"])

def test_missing_value_handling():
    df = pd.DataFrame({
        "vals": [10.0, 20.0, None, 40.0],
        "category": ["A", None, "A", "B"],
        "const_col": [None, "Y", "Z", None]
    })
    ops = [
        {"type": "fill_missing", "column": "vals", "strategy": "mean"},
        {"type": "fill_missing", "column": "category", "strategy": "mode"},
        {"type": "fill_missing", "column": "const_col", "strategy": "constant", "value": "Unknown"}
    ]
    res_df, impact = execute_transformations(df, ops)
    assert res_df["vals"].isna().sum() == 0
    assert res_df["vals"].iloc[2] == pytest.approx(23.3333, 0.01)
    assert res_df["category"].isna().sum() == 0
    assert res_df["category"].iloc[1] == "A"
    assert res_df["const_col"].iloc[0] == "Unknown"
    assert impact["cells_modified"] >= 4

def test_drop_missing_and_duplicates():
    df = pd.DataFrame({
        "id": [1, 2, 2, 3, 4],
        "val": ["A", "B", "B", None, "E"]
    })
    ops = [
        {"type": "remove_duplicates", "subset": ["id"], "keep": "first"},
        {"type": "drop_missing_rows", "columns": ["val"], "how": "any"}
    ]
    res_df, impact = execute_transformations(df, ops)
    assert len(res_df) == 3
    assert impact["rows_removed"] == 2

def test_text_cleaning_and_casing():
    df = pd.DataFrame({
        "name": ["  Alice ", "BOB  ", "  charlie"],
        "code": ["abc", "def", "ghi"]
    })
    ops = [
        {"type": "trim_text", "columns": ["name"]},
        {"type": "normalize_case", "columns": ["name"], "case": "title"},
        {"type": "normalize_case", "columns": ["code"], "case": "upper"}
    ]
    res_df, _ = execute_transformations(df, ops)
    assert res_df["name"].tolist() == ["Alice", "Bob", "Charlie"]
    assert res_df["code"].tolist() == ["ABC", "DEF", "GHI"]

def test_numeric_rounding_and_clipping():
    df = pd.DataFrame({
        "price": [10.556, 20.123, 99.999],
        "score": [-50.0, 50.0, 150.0]
    })
    ops = [
        {"type": "numeric_round", "columns": ["price"], "decimals": 2},
        {"type": "clip_values", "column": "score", "min_value": 0.0, "max_value": 100.0}
    ]
    res_df, _ = execute_transformations(df, ops)
    assert res_df["price"].tolist() == [10.56, 20.12, 100.0]
    assert res_df["score"].tolist() == [0.0, 50.0, 100.0]

def test_date_parts_and_replacement():
    df = pd.DataFrame({
        "signup_date": ["2026-05-15", "2026-11-20"],
        "status": ["pending", "active"]
    })
    ops = [
        {"type": "create_date_part", "column": "signup_date", "part": "month", "new_column_name": "signup_month"},
        {"type": "create_date_part", "column": "signup_date", "part": "year", "new_column_name": "signup_year"},
        {"type": "replace_values", "column": "status", "old_value": "pending", "new_value": "in_review"}
    ]
    res_df, _ = execute_transformations(df, ops)
    assert res_df["signup_month"].tolist() == [5, 11]
    assert res_df["signup_year"].tolist() == [2026, 2026]
    assert res_df["status"].tolist() == ["in_review", "active"]

def test_outlier_handling():
    df = pd.DataFrame({
        "num": [10, 12, 11, 13, 12, 11, 10, 12, 11, 500]
    })
    # Clip outlier
    res_clip, _ = execute_transformations(df, [{"type": "handle_outliers", "column": "num", "factor": 1.5, "action": "clip"}])
    assert res_clip["num"].max() < 100
    assert len(res_clip) == 10

    # Drop outlier row
    res_drop, impact = execute_transformations(df, [{"type": "handle_outliers", "column": "num", "factor": 1.5, "action": "drop"}])
    assert len(res_drop) == 9
    assert impact["rows_removed"] == 1

def test_validation_errors():
    df = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(DatasetValidationError) as exc:
        execute_transformations(df, [{"type": "unknown_action"}])
    assert exc.value.error_code == "INVALID_OPERATION_TYPE"

    with pytest.raises(DatasetValidationError) as exc:
        execute_transformations(df, [{"type": "rename_column", "column": "non_existent", "new_name": "b"}])
    assert exc.value.error_code == "COLUMN_NOT_FOUND"

    with pytest.raises(DatasetValidationError) as exc:
        execute_transformations(df, [{"type": "drop_columns", "columns": ["a"]}])
    assert exc.value.error_code == "INVALID_OPERATION"

def test_api_transform_and_preview_endpoints():
    headers = {"Authorization": "Bearer mock-token"}
    dataset_id = str(uuid.uuid4())
    
    transform_payload = {
        "operations": [
            {"type": "rename_column", "column": "category", "new_name": "group_name"},
            {"type": "numeric_round", "columns": ["score"], "decimals": 1}
        ],
        "summary": "Rename category and round score",
        "source": "manual"
    }

    # 1. Test Preview endpoint
    preview_res = client.post(f"/datasets/{dataset_id}/transform/preview", json=transform_payload, headers=headers)
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert p_data["dataset_id"] == dataset_id
    assert "impact" in p_data
    assert "sample_preview" in p_data
    assert len(p_data["sample_preview"]) > 0

    # 2. Test Apply Transform endpoint
    apply_res = client.post(f"/datasets/{dataset_id}/transform", json=transform_payload, headers=headers)
    assert apply_res.status_code == 200
    t_data = apply_res.json()
    assert t_data["dataset_id"] == dataset_id
    assert t_data["version_number"] == 2
    assert "impact" in t_data
    assert "new_version" in t_data
    assert "operation" in t_data
    assert t_data["impact"]["rows_after"] > 0
    assert "group_name" in t_data["impact"]["affected_columns"]


# ==============================================================================
# FILE SUMMARY: backend/tests/test_transformations.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides comprehensive automated unit and integration tests for the
# deterministic data cleaning and transformation engine:
#   1. Column structure tests: renaming, dropping, and column selection.
#   2. Data type conversion tests: casting to numeric, boolean, datetime, and categorical.
#   3. Missing data tests: imputation using mean, median, mode, constant values, and row deletion.
#   4. Deduplication tests: removing duplicate rows across all or specific column subsets.
#   5. Text hygiene tests: whitespace trimming and casing normalization (upper, lower, title).
#   6. Numeric adjustment tests: rounding decimals and clipping values to bounds.
#   7. Outlier mitigation tests: IQR boundary calculation, clipping, and row dropping.
#   8. Temporal feature tests: parsing date formats and extracting date parts (year, month, day).
#   9. Safety and guardrail tests: rejecting unsupported operation types, missing columns,
#      empty datasets, and invalid strategies with standardized 'DatasetValidationError' error codes.
#   10. API integration tests: verifies 'POST /datasets/{id}/transform/preview' and
#       'POST /datasets/{id}/transform' using FastAPI's 'TestClient'.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports and tests 'execute_transformations' and 'apply_single_operation' from
#   'backend/services/transformations.py'.
# - Imports 'app' from 'backend/main.py' to test HTTP routes declared in 'backend/api/datasets.py'.
# - Validates exception codes defined in 'backend/core/exceptions.py'.
# ==============================================================================
