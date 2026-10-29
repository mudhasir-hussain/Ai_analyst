import uuid
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from main import app
from services.datasets import cache_dev_dataframe
from services.reports.insights import generate_narrative_insights
from services.reports.generator import (
    generate_dataset_report,
    get_dataset_report,
    _DEV_REPORTS_CACHE
)
from services.reports.exporter import export_dataset
from models.schemas import ReportCreateRequest
from core.exceptions import DatasetValidationError, ResourceNotFoundError

client = TestClient(app)
MOCK_AUTH_HEADER = {"Authorization": "Bearer mock-token"}


@pytest.fixture
def sales_report_df():
    np.random.seed(101)
    n = 120
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    categories = np.random.choice(["Software", "Hardware", "Services"], p=[0.7, 0.2, 0.1], size=n)
    cost = np.random.uniform(20.0, 80.0, size=n)
    margin = np.random.uniform(1.1, 2.5, size=n)
    revenue = cost * margin + np.random.normal(0, 2, size=n)

    # Insert an outlier and null
    revenue[10] = 75000.0
    cost[20] = np.nan

    return pd.DataFrame({
        "order_date": dates,
        "category": categories,
        "cost": cost,
        "revenue": revenue
    })


def test_generate_narrative_insights(sales_report_df):
    insights = generate_narrative_insights(sales_report_df)
    assert len(insights) >= 3

    categories = [i["category"] for i in insights]
    assert "quality" in categories

    # Verify no correlation claims causation
    corr_insights = [i for i in insights if i["category"] == "correlation"]
    for ci in corr_insights:
        assert "causation" in ci["implication"].lower() or "correlation" in ci["implication"].lower()


def test_generate_dataset_report_json(sales_report_df):
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    req = ReportCreateRequest(format="json", title="Quarterly Analytics")
    report = generate_dataset_report(
        df=sales_report_df,
        dataset_id=dataset_id,
        version_id=version_id,
        version_number=1,
        user_id=user_id,
        request=req
    )

    assert report.title == "Quarterly Analytics"
    assert report.format == "json"
    assert report.content is None
    assert len(report.insights) > 0
    assert report.health_score > 0
    assert str(report.id) in _DEV_REPORTS_CACHE


def test_generate_dataset_report_markdown(sales_report_df):
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    req = ReportCreateRequest(format="markdown")
    report = generate_dataset_report(
        df=sales_report_df,
        dataset_id=dataset_id,
        version_id=version_id,
        version_number=2,
        user_id=user_id,
        request=req
    )

    assert report.format == "markdown"
    assert report.content is not None
    assert "# Executive Data Analysis Report - v2" in report.content
    assert "## Executive Summary" in report.content
    assert "## Analytical Limitations & Disclaimers" in report.content


def test_generate_dataset_report_html(sales_report_df):
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    req = ReportCreateRequest(format="html", title="HTML Executive Brief")
    report = generate_dataset_report(
        df=sales_report_df,
        dataset_id=dataset_id,
        version_id=version_id,
        version_number=1,
        user_id=user_id,
        request=req
    )

    assert report.format == "html"
    assert report.content is not None
    assert "<!DOCTYPE html>" in report.content
    assert "HTML Executive Brief" in report.content
    assert "metrics-grid" in report.content


def test_get_dataset_report(sales_report_df):
    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()
    user_id = uuid.uuid4()

    req = ReportCreateRequest(format="json")
    created_report = generate_dataset_report(
        df=sales_report_df,
        dataset_id=dataset_id,
        version_id=version_id,
        version_number=1,
        user_id=user_id,
        request=req
    )

    fetched = get_dataset_report(created_report.id)
    assert fetched.id == created_report.id
    assert fetched.title == created_report.title

    with pytest.raises(ResourceNotFoundError):
        get_dataset_report(uuid.uuid4())


def test_export_dataset_csv_and_xlsx(sales_report_df):
    # CSV export
    csv_bytes, media_type, filename = export_dataset(sales_report_df, format="csv", filename_prefix="sales")
    assert media_type == "text/csv"
    assert filename == "sales_export.csv"
    assert b"order_date,category,cost,revenue" in csv_bytes

    # Excel export
    excel_bytes, media_type, filename = export_dataset(sales_report_df, format="xlsx", filename_prefix="sales")
    assert "openxmlformats" in media_type
    assert filename == "sales_export.xlsx"
    assert len(excel_bytes) > 100

    # Unsupported format
    with pytest.raises(DatasetValidationError) as exc:
        export_dataset(sales_report_df, format="parquet")
    assert exc.value.error_code == "UNSUPPORTED_EXPORT_FORMAT"


def test_api_create_report_endpoint(sales_report_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sales_report_df)

    res = client.post(
        f"/datasets/{dataset_id}/reports",
        headers=MOCK_AUTH_HEADER,
        json={"format": "markdown", "title": "API Test Report"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "API Test Report"
    assert data["format"] == "markdown"
    assert "# API Test Report" in data["content"]
    assert "id" in data

    report_id = data["id"]

    # Verify retrieval endpoint GET /reports/{report_id}
    get_res = client.get(
        f"/reports/{report_id}",
        headers=MOCK_AUTH_HEADER
    )
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["id"] == report_id
    assert fetched_data["title"] == "API Test Report"


def test_api_get_report_not_found():
    random_id = str(uuid.uuid4())
    res = client.get(
        f"/reports/{random_id}",
        headers=MOCK_AUTH_HEADER
    )
    assert res.status_code == 404
    assert res.json()["error_code"] == "REPORT_NOT_FOUND"


def test_api_export_csv_endpoint(sales_report_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sales_report_df)

    res = client.post(
        f"/datasets/{dataset_id}/export",
        headers=MOCK_AUTH_HEADER,
        json={"format": "csv"}
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers["content-disposition"]
    assert "order_date,category,cost,revenue" in res.text


def test_api_export_xlsx_endpoint(sales_report_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sales_report_df)

    res = client.post(
        f"/datasets/{dataset_id}/export",
        headers=MOCK_AUTH_HEADER,
        json={"format": "xlsx"}
    )
    assert res.status_code == 200
    assert "openxmlformats" in res.headers["content-type"]
    assert "attachment" in res.headers["content-disposition"]
    assert len(res.content) > 100


def test_api_create_report_matches_active_version_number(sales_report_df):
    from services.history.service import register_dev_version
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sales_report_df)

    # Register version 1 and version 2
    register_dev_version(dataset_id, {
        "id": str(uuid.uuid4()),
        "dataset_id": dataset_id,
        "version_number": 1,
        "row_count": len(sales_report_df),
        "column_count": len(sales_report_df.columns),
        "created_at": "2026-01-01T00:00:00Z"
    })
    v2_id = str(uuid.uuid4())
    register_dev_version(dataset_id, {
        "id": v2_id,
        "dataset_id": dataset_id,
        "version_number": 2,
        "row_count": len(sales_report_df),
        "column_count": len(sales_report_df.columns),
        "created_at": "2026-01-02T00:00:00Z"
    })

    res = client.post(
        f"/datasets/{dataset_id}/reports",
        headers=MOCK_AUTH_HEADER,
        json={"format": "markdown"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["version_number"] == 2
    assert "v2" in data["title"] or "Version: v2" in data["content"]


# ==============================================================================
# FILE SUMMARY: backend/tests/test_reports.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides automated tests for narrative reporting and dataset exports:
#   1. Narrative insight extraction across quality, distribution, correlation, and trends.
#   2. Multi-format report compilation: JSON structure, Markdown, and responsive HTML.
#   3. Report retrieval and 404 error handling.
#   4. CSV and XLSX binary export serialization.
#   5. End-to-end HTTP integration tests for POST /datasets/{id}/reports,
#      GET /reports/{id}, and POST /datasets/{id}/export.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Tests services from 'backend/services/reports/'.
# - Tests endpoints in 'backend/api/datasets.py' and 'backend/api/reports.py'.
# - Leverages FastAPI TestClient and mock credentials from 'backend/core/auth.py'.
# ==============================================================================
