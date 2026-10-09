import pytest
import uuid
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from main import app
from services.datasets import cache_dev_dataframe
from services.ml.trainer import (
    detect_ml_task,
    get_candidate_targets,
    train_model_on_dataframe
)
from services.ml.comparator import compare_model_across_dataframes

client = TestClient(app)


@pytest.fixture
def sample_ml_dataframe():
    np.random.seed(42)
    n = 100
    price = np.random.uniform(10, 100, n)
    units = np.random.randint(1, 20, n)
    # Target: revenue = price * units + noise
    revenue = price * units + np.random.normal(0, 15, n)
    category = np.random.choice(["Hardware", "Software", "Cloud", "Support"], n)
    churn = np.random.choice([0, 1], n)

    df = pd.DataFrame({
        "unit_price": price,
        "units_sold": units,
        "category": category,
        "revenue": revenue,
        "churn": churn
    })
    # Add a few duplicate rows to simulate real dirty data
    duplicates = df.iloc[:5].copy()
    return pd.concat([df, duplicates], ignore_index=True)


def test_detect_ml_task(sample_ml_dataframe):
    assert detect_ml_task(sample_ml_dataframe, "revenue") == "regression"
    assert detect_ml_task(sample_ml_dataframe, "churn") == "classification"
    assert detect_ml_task(sample_ml_dataframe, "category") == "classification"


def test_get_candidate_targets(sample_ml_dataframe):
    targets = get_candidate_targets(sample_ml_dataframe)
    cols = [t["column"] for t in targets]
    assert "revenue" in cols
    assert "churn" in cols
    assert "unit_price" in cols


def test_train_linear_regression(sample_ml_dataframe):
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="linear_regression",
        version_number=1
    )
    assert res.task_type == "regression"
    assert res.metrics.regression_metrics is not None
    assert "r2_score" in res.metrics.regression_metrics
    assert "rmse" in res.metrics.regression_metrics
    assert len(res.predictions) > 0
    assert len(res.feature_importance) > 0
    assert len(res.educational_takeaways) > 0


def test_train_decision_tree_overfitting(sample_ml_dataframe):
    # Unconstrained decision tree on small duplicate dataset should overfit
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="decision_tree",
        hyperparameters={"max_depth": None},
        version_number=1
    )
    assert res.task_type == "regression"
    assert res.metrics.train_score > res.metrics.test_score
    assert res.metrics.overfitting_status in {"severe_overfitting", "moderate_overfitting", "healthy_generalization"}
    assert "Decision Tree" in res.model_name


def test_train_random_forest(sample_ml_dataframe):
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="random_forest",
        version_number=1
    )
    assert res.task_type == "classification"
    assert res.metrics.classification_metrics is not None
    assert "accuracy" in res.metrics.classification_metrics
    assert "f1_score" in res.metrics.classification_metrics


def test_train_neural_network_mlp(sample_ml_dataframe):
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="neural_network_mlp",
        hyperparameters={"max_iter": 30},
        version_number=1
    )
    assert res.task_type == "regression"
    assert len(res.loss_curve) > 0
    assert res.loss_curve[0].epoch == 1
    assert res.loss_curve[0].loss > 0


def test_compare_model_across_dataframes(sample_ml_dataframe):
    # Base version: dirty data with duplicates
    df_base = sample_ml_dataframe.copy()
    # Target version: preprocessed (deduplicated)
    df_target = sample_ml_dataframe.drop_duplicates().copy()

    comp = compare_model_across_dataframes(
        df_base=df_base,
        df_target=df_target,
        target_column="revenue",
        model_type="linear_regression",
        base_version_number=1,
        target_version_number=2
    )

    assert comp.model_type == "linear_regression"
    assert comp.target_column == "revenue"
    assert comp.base_version.version_number == 1
    assert comp.target_version.version_number == 2
    assert isinstance(comp.score_delta, float)
    assert len(comp.summary) > 10


def test_api_ml_endpoints(sample_ml_dataframe):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, sample_ml_dataframe)
    cache_dev_dataframe(f"{dataset_id}_v1", sample_ml_dataframe)
    cache_dev_dataframe(f"{dataset_id}_v2", sample_ml_dataframe.drop_duplicates())

    headers = {"Authorization": "Bearer mock-token"}

    # 1. Targets endpoint
    t_resp = client.get(f"/datasets/{dataset_id}/ml/targets", headers=headers)
    assert t_resp.status_code == 200
    targets = t_resp.json()
    assert any(t["column"] == "revenue" for t in targets)

    # 2. Train endpoint
    train_payload = {
        "target_column": "revenue",
        "model_type": "linear_regression",
        "test_size": 0.2
    }
    train_resp = client.post(f"/datasets/{dataset_id}/ml/train", json=train_payload, headers=headers)
    assert train_resp.status_code == 200
    data = train_resp.json()
    assert data["target_column"] == "revenue"
    assert "metrics" in data
    assert "predictions" in data

    # 3. Compare endpoint
    comp_payload = {
        "target_column": "revenue",
        "model_type": "decision_tree",
        "base_version_number": 1,
        "target_version_number": 2
    }
    comp_resp = client.post(f"/datasets/{dataset_id}/ml/compare", json=comp_payload, headers=headers)
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert "score_delta" in comp_data
    assert "summary" in comp_data


def test_feature_selection_filtering(sample_ml_dataframe):
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="linear_regression",
        selected_features=["units_sold"]
    )
    assert res.feature_count == 1
    assert len(res.feature_importance) == 1
    assert res.feature_importance[0].feature == "units_sold"


def test_classification_confusion_matrix(sample_ml_dataframe):
    # 'churn' is binary 0/1
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="logistic_regression"
    )
    assert res.task_type == "classification"
    assert res.metrics.confusion_matrix is not None
    assert len(res.metrics.confusion_matrix.labels) >= 2
    assert len(res.metrics.confusion_matrix.matrix) >= 2
    assert res.metrics.confusion_matrix.total_samples > 0

