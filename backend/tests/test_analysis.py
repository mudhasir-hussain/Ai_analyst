import uuid
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from main import app
from services.datasets import cache_dev_dataframe
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
from core.exceptions import DatasetValidationError

client = TestClient(app)
MOCK_AUTH_HEADER = {"Authorization": "Bearer mock-token"}


@pytest.fixture
def analytics_sample_df():
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    categories = np.random.choice(["Electronics", "Home & Garden", "Apparel"], size=n)
    units_sold = np.random.randint(1, 50, size=n).astype(float)
    unit_price = np.random.uniform(10.0, 100.0, size=n)
    revenue = units_sold * unit_price + np.random.normal(0, 5, size=n)

    # Insert a couple of known outliers and nulls
    revenue[0] = 50000.0
    units_sold[5] = np.nan

    return pd.DataFrame({
        "order_date": dates,
        "category": categories,
        "units_sold": units_sold,
        "unit_price": unit_price,
        "revenue": revenue
    })


def test_calculate_numeric_summary(analytics_sample_df):
    summary = calculate_numeric_summary(analytics_sample_df)
    assert "revenue" in summary
    assert "units_sold" in summary
    assert summary["revenue"]["count"] == 100
    assert summary["units_sold"]["null_count"] == 1
    assert summary["revenue"]["mean"] is not None
    assert summary["revenue"]["median"] is not None
    assert summary["revenue"]["iqr"] is not None
    assert summary["revenue"]["skewness"] is not None
    assert summary["revenue"]["kurtosis"] is not None


def test_calculate_categorical_summary(analytics_sample_df):
    summary = calculate_categorical_summary(analytics_sample_df)
    assert "category" in summary
    cat_summary = summary["category"]
    assert cat_summary["unique_count"] == 3
    assert len(cat_summary["top_categories"]) == 3
    assert cat_summary["null_count"] == 0
    top_cat = cat_summary["top_categories"][0]
    assert "percentage" in top_cat
    assert "count" in top_cat


def test_compute_correlation_matrix(analytics_sample_df):
    corr = compute_correlation_matrix(analytics_sample_df, threshold=0.1)
    matrix = corr["matrix"]
    assert "revenue" in matrix
    assert "units_sold" in matrix
    assert matrix["revenue"]["revenue"] == 1.0

    pairs = corr["significant_pairs"]
    assert isinstance(pairs, list)
    if pairs:
        assert "column_1" in pairs[0]
        assert "column_2" in pairs[0]
        assert "strength" in pairs[0]


def test_compute_temporal_trends(analytics_sample_df):
    trends = compute_temporal_trends(analytics_sample_df)
    assert len(trends) >= 1
    date_trend = trends[0]
    assert date_trend["column"] == "order_date"
    assert date_trend["span_days"] == 99
    assert date_trend["is_chronological"] is True


def test_generate_chart_recommendations(analytics_sample_df):
    recs = generate_chart_recommendations(analytics_sample_df)
    assert len(recs) >= 3
    chart_types = [r["chart_type"] for r in recs]
    assert "line" in chart_types
    assert "bar" in chart_types
    assert "histogram" in chart_types
    assert all("reason" in r for r in recs)


def test_build_visualization_bar_chart(analytics_sample_df):
    # Aggregated sum
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="bar",
        x_column="category",
        y_column="revenue",
        aggregation="sum"
    )
    assert vis["chart_type"] == "bar"
    assert len(vis["data"]) == 3
    assert "category" in vis["data"][0]
    assert "revenue" in vis["data"][0]
    assert len(vis["insights"]) > 0


def test_build_visualization_line_chart(analytics_sample_df):
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="line",
        x_column="order_date",
        y_column="revenue"
    )
    assert vis["chart_type"] == "line"
    assert len(vis["data"]) > 0
    assert "order_date" in vis["data"][0]
    assert "revenue" in vis["data"][0]


def test_build_visualization_scatter_plot(analytics_sample_df):
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="scatter",
        x_column="units_sold",
        y_column="revenue"
    )
    assert vis["chart_type"] == "scatter"
    assert len(vis["data"]) > 0
    assert "units_sold" in vis["data"][0]
    assert "revenue" in vis["data"][0]


def test_build_visualization_histogram(analytics_sample_df):
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="histogram",
        x_column="unit_price"
    )
    assert vis["chart_type"] == "histogram"
    assert len(vis["data"]) == 15
    assert "bin_start" in vis["data"][0]
    assert "count" in vis["data"][0]


def test_build_visualization_box_plot(analytics_sample_df):
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="box",
        y_column="revenue"
    )
    assert vis["chart_type"] == "box"
    assert len(vis["data"]) == 1
    box = vis["data"][0]
    assert "q25" in box
    assert "median" in box
    assert "q75" in box
    assert box["outliers_count"] >= 1  # Should catch the 50000.0 outlier


def test_build_visualization_heatmap(analytics_sample_df):
    vis = build_visualization_data(
        df=analytics_sample_df,
        chart_type="heatmap"
    )
    assert vis["chart_type"] == "heatmap"
    assert len(vis["data"]) > 0
    assert "x" in vis["data"][0]
    assert "y" in vis["data"][0]
    assert "correlation" in vis["data"][0]


def test_build_visualization_errors(analytics_sample_df):
    with pytest.raises(DatasetValidationError) as exc_chart:
        build_visualization_data(analytics_sample_df, chart_type="radar")
    assert exc_chart.value.error_code == "INVALID_CHART_TYPE"

    with pytest.raises(DatasetValidationError) as exc_col:
        build_visualization_data(analytics_sample_df, chart_type="bar", x_column="non_existent")
    assert exc_col.value.error_code == "COLUMN_NOT_FOUND"


def test_api_get_statistics_endpoint(analytics_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, analytics_sample_df)

    res = client.get(
        f"/datasets/{dataset_id}/statistics",
        headers=MOCK_AUTH_HEADER
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert "numeric_summary" in data
    assert "categorical_summary" in data
    assert "correlations" in data
    assert "temporal_trends" in data
    assert data["row_count"] == 100


def test_api_post_visualizations_recommendations(analytics_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, analytics_sample_df)

    res = client.post(
        f"/datasets/{dataset_id}/visualizations",
        headers=MOCK_AUTH_HEADER,
        json=None
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_id"] == dataset_id
    assert "recommended_charts" in data
    assert len(data["recommended_charts"]) >= 3
    assert len(data["previews"]) >= 1


def test_api_post_visualizations_custom_chart(analytics_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, analytics_sample_df)

    payload = {
        "chart_type": "bar",
        "x_column": "category",
        "y_column": "revenue",
        "aggregation": "mean",
        "limit": 5
    }
    res = client.post(
        f"/datasets/{dataset_id}/visualizations",
        headers=MOCK_AUTH_HEADER,
        json=payload
    )
    assert res.status_code == 200
    data = res.json()
    assert data["chart_type"] == "bar"
    assert len(data["data"]) == 3
    assert "insights" in data


# ==============================================================================
# FILE SUMMARY: backend/tests/test_analysis.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides automated test coverage for the statistical analysis and
# visualization recommendation engines:
#   1. Parametric & non-parametric stats verification (mean, median, IQR, skewness, kurtosis).
#   2. Categorical distribution & frequency analysis.
#   3. Pearson correlation matrix and significant relationship detection.
#   4. Temporal trend calculation and chronological continuity checks.
#   5. Intelligent chart recommendation selection across column datatypes.
#   6. Visual data generators for Bar, Line, Scatter, Histogram, Box plot, and Heatmap.
#   7. Validation error handling for unknown chart types and missing columns.
#   8. Full HTTP endpoint integration for GET /datasets/{id}/statistics and
#      POST /datasets/{id}/visualizations.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports and tests services from 'backend/services/analysis/'.
# - Verifies endpoints in 'backend/api/datasets.py' using FastAPI's TestClient.
# - Utilizes local auth mock tokens from 'backend/core/auth.py'.
# ==============================================================================
