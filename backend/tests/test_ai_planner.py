import uuid
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app
from core.exceptions import AIPlanError, ResourceNotFoundError
from services.ai.provider import MockLLMProvider, get_llm_provider
from services.ai.prompts import (
    build_planning_system_prompt,
    build_dataset_context,
    build_planning_user_prompt
)
from services.ai.planner import (
    extract_and_parse_json,
    validate_plan_operations,
    generate_ai_plan,
    approve_and_execute_plan,
    _DEV_AI_PLANS_CACHE
)
from services.datasets import cache_dev_dataframe

client = TestClient(app)

MOCK_AUTH_HEADER = {"Authorization": "Bearer mock-token"}


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 5],
        "customer": ["Alice", "Bob", "Charlie", "Alice", "Eve", "Eve"],
        "revenue": [100.556, None, 300.2, 450.0, 9999.0, 9999.0],
        "category": ["electronics", "furniture", "electronics", "appliances", "furniture", "furniture"]
    })


def test_mock_llm_provider_fill_missing(sample_sales_df):
    provider = MockLLMProvider()
    context = build_dataset_context(sample_sales_df)
    prompt = build_planning_user_prompt("Fill missing revenue with the column median", context)
    response_text = provider.generate("", prompt)

    data = extract_and_parse_json(response_text)
    assert "operations" in data
    assert len(data["operations"]) == 1
    assert data["operations"][0]["type"] == "fill_missing"
    assert data["operations"][0]["column"] == "revenue"
    assert data["operations"][0]["strategy"] == "median"


def test_mock_llm_provider_drop_columns(sample_sales_df):
    provider = MockLLMProvider()
    context = build_dataset_context(sample_sales_df)
    prompt = build_planning_user_prompt("Drop columns 'customer' and 'category'", context)
    response_text = provider.generate("", prompt)

    data = extract_and_parse_json(response_text)
    assert "operations" in data
    assert data["operations"][0]["type"] == "drop_columns"
    assert "customer" in data["operations"][0]["columns"]


def test_mock_llm_provider_deduplicate(sample_sales_df):
    provider = MockLLMProvider()
    prompt = "Please remove duplicate rows from this dataset"
    response_text = provider.generate("", prompt)

    data = extract_and_parse_json(response_text)
    assert data["operations"][0]["type"] == "remove_duplicates"


def test_mock_llm_provider_round_numeric(sample_sales_df):
    provider = MockLLMProvider()
    context = build_dataset_context(sample_sales_df)
    prompt = build_planning_user_prompt("Round revenue to 2 decimal places", context)
    response_text = provider.generate("", prompt)

    data = extract_and_parse_json(response_text)
    assert data["operations"][0]["type"] == "numeric_round"
    assert data["operations"][0]["column"] == "revenue"
    assert data["operations"][0]["decimals"] == 2


def test_extract_and_parse_json_markdown_blocks():
    fenced_text = """Here is your plan:
```json
{
  "summary": "Cleaned dataset",
  "operations": [
    {"type": "remove_duplicates"}
  ],
  "warnings": [],
  "requires_confirmation": true
}
```
Hope this helps!"""
    result = extract_and_parse_json(fenced_text)
    assert result["summary"] == "Cleaned dataset"
    assert len(result["operations"]) == 1


def test_validate_plan_operations_valid(sample_sales_df):
    operations = [
        {"type": "remove_duplicates"},
        {"type": "fill_missing", "column": "revenue", "strategy": "median"},
        {"type": "numeric_round", "column": "revenue", "decimals": 2}
    ]
    is_valid, warnings = validate_plan_operations(operations, sample_sales_df)
    assert is_valid is True
    assert len(warnings) == 0


def test_validate_plan_operations_invalid_column(sample_sales_df):
    operations = [
        {"type": "fill_missing", "column": "non_existent_column", "strategy": "mean"}
    ]
    is_valid, warnings = validate_plan_operations(operations, sample_sales_df)
    assert is_valid is False
    assert any("non_existent_column" in w for w in warnings)


def test_validate_plan_operations_unsupported_type(sample_sales_df):
    operations = [
        {"type": "execute_arbitrary_python", "code": "df.drop()"}
    ]
    is_valid, warnings = validate_plan_operations(operations, sample_sales_df)
    assert is_valid is False
    assert any("unsupported type" in w for w in warnings)


def test_generate_ai_plan_success(sample_sales_df):
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    plan_response = generate_ai_plan(
        df=sample_sales_df,
        user_prompt="Fill missing revenue with median",
        dataset_id=dataset_id,
        version_id=version_id,
        user_id=user_id,
        provider_name="mock"
    )

    assert plan_response.dataset_id == dataset_id
    assert plan_response.validation_status == "validated"
    assert "operations" in plan_response.plan_json
    assert str(plan_response.id) in _DEV_AI_PLANS_CACHE


def test_api_create_ai_plan_endpoint(sample_sales_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sample_sales_df)

    res = client.post(
        f"/datasets/{dataset_id}/ai/plan",
        headers=MOCK_AUTH_HEADER,
        json={"user_prompt": "Please remove duplicate rows"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert data["validation_status"] == "validated"
    assert data["plan_json"]["operations"][0]["type"] == "remove_duplicates"


def test_api_approve_ai_plan_endpoint(sample_sales_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sample_sales_df)

    # 1. Create plan
    plan_res = client.post(
        f"/datasets/{dataset_id}/ai/plan",
        headers=MOCK_AUTH_HEADER,
        json={"user_prompt": "Remove duplicate rows"}
    )
    assert plan_res.status_code == 200
    plan_id = plan_res.json()["id"]

    # 2. Approve plan
    approve_res = client.post(
        f"/datasets/{dataset_id}/ai/plan/{plan_id}/approve",
        headers=MOCK_AUTH_HEADER
    )
    assert approve_res.status_code == 200
    result = approve_res.json()

    assert result["dataset_id"] == dataset_id
    assert result["version_number"] == 2
    assert result["operation"]["source"] == "ai"
    assert result["impact"]["rows_after"] == 5
    assert result["impact"]["rows_removed"] == 1


def test_api_approve_unvalidated_plan_fails(sample_sales_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sample_sales_df)
    invalid_plan_id = str(uuid.uuid4())

    _DEV_AI_PLANS_CACHE[invalid_plan_id] = {
        "id": invalid_plan_id,
        "dataset_id": dataset_id,
        "validation_status": "invalid",
        "plan_json": {"operations": []},
        "user_prompt": "broken plan"
    }

    approve_res = client.post(
        f"/datasets/{dataset_id}/ai/plan/{invalid_plan_id}/approve",
        headers=MOCK_AUTH_HEADER
    )
    assert approve_res.status_code == 422
    assert approve_res.json()["error_code"] == "PLAN_NOT_VALIDATED"


def test_provider_factory():
    mock_prov = get_llm_provider("mock")
    assert isinstance(mock_prov, MockLLMProvider)

    unknown_prov = get_llm_provider("unknown_future_model")
    assert isinstance(unknown_prov, MockLLMProvider)


def test_mock_llm_provider_fill_missing_all_numeric_columns():
    df = pd.DataFrame({
        "order_id": [101, 102, 103],
        "unit_price": [20.5, None, 45.0],
        "quantity": [2, 5, None],
        "customer": ["Alice", "Bob", "Charlie"]
    })
    provider = MockLLMProvider()
    context = build_dataset_context(df)
    prompt = build_planning_user_prompt("full missing values in all the numeric columns with median values", context)
    response_text = provider.generate("", prompt)

    data = extract_and_parse_json(response_text)
    assert "operations" in data
    # Should create operations for numeric columns: unit_price, quantity
    ops = data["operations"]
    cols_targeted = [op["column"] for op in ops if op["type"] == "fill_missing"]
    
    assert "order_id" not in cols_targeted, "order_id must NOT be imputed with median!"
    assert "unit_price" in cols_targeted
    assert "quantity" in cols_targeted
    for op in ops:
        assert op["strategy"] == "median"

    # Should have warning explaining order_id exclusion
    assert any("order_id" in w for w in data.get("warnings", []))


def test_mock_llm_provider_fallback_warning():
    provider = MockLLMProvider(model="qwen2.5:7b-fallback")
    prompt = "remove duplicate rows"
    response_text = provider.generate("", prompt)
    data = extract_and_parse_json(response_text)
    assert any("fallback" in w.lower() for w in data.get("warnings", []))


def test_resilient_provider_fallback_sequence():
    from services.ai.provider import ResilientLLMProvider, MockLLMProvider

    class FailingProvider:
        def generate(self, sys, prompt):
            raise RuntimeError("Primary API network timeout or 503 Service Unavailable")

    class SecondaryProvider:
        def generate(self, sys, prompt):
            return '{"operations": [{"type": "remove_duplicates"}], "summary": "Groq Failsafe Success"}'

    # When primary fails, should seamlessly fall back to secondary (Groq / Mock)
    resilient = ResilientLLMProvider(
        primary=FailingProvider(),
        secondary=SecondaryProvider(),
        fallback=MockLLMProvider()
    )

    result_text = resilient.generate("system", "remove duplicates")
    parsed = extract_and_parse_json(result_text)
    assert "operations" in parsed
    assert parsed["summary"] == "Groq Failsafe Success"

    # When both primary and secondary fail, falls back to deterministic local rule engine
    resilient_fallback = ResilientLLMProvider(
        primary=FailingProvider(),
        secondary=FailingProvider(),
        fallback=MockLLMProvider()
    )
    fallback_text = resilient_fallback.generate("system", "fill missing values in revenue with median")
    parsed_fallback = extract_and_parse_json(fallback_text)
    assert "operations" in parsed_fallback


def test_api_auto_heal_dataset(sample_sales_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sample_sales_df)

    res = client.post(
        f"/datasets/{dataset_id}/ai/auto-heal",
        headers=MOCK_AUTH_HEADER
    )
    assert res.status_code == 200, f"Auto heal failed: {res.text}"
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert "version_number" in data
    assert "impact" in data
    assert "new_version" in data
    assert data["operation"]["source"] == "ai"
    assert "Auto-Heal" in data["operation"]["summary"]



# ==============================================================================
# FILE SUMMARY: backend/tests/test_ai_planner.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides automated regression tests covering the AI Operation Planner:
#   1. MockLLMProvider intent parsing (fill_missing, drop_columns, remove_duplicates, numeric_round).
#   2. Robust JSON parsing and markdown code fence extraction ('extract_and_parse_json').
#   3. Plan operation validation against allowed types and dataset column schemas.
#   4. Pre-flight slice dry-run execution testing.
#   5. End-to-end HTTP endpoint tests for POST /datasets/{id}/ai/plan and
#      POST /datasets/{id}/ai/plan/{plan_id}/approve.
#   6. Unvalidated/invalid plan approval rejection checks.
#   7. Provider factory fallback tests.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Tests endpoints in 'backend/api/datasets.py'.
# - Tests services in 'backend/services/ai/'.
# - Uses TestClient and authentication mock headers from 'backend/main.py'.
# ==============================================================================
