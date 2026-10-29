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


def test_train_gradient_boosting(sample_ml_dataframe):
    # Test regression with staged loss curve
    res_reg = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="gradient_boosting",
        hyperparameters={"n_estimators": 25, "max_depth": 3}
    )
    assert res_reg.task_type == "regression"
    assert "Gradient Boosting" in res_reg.model_name
    assert len(res_reg.loss_curve) == 25
    assert len(res_reg.feature_importance) > 0
    assert any("Gradient Boosting" in t for t in res_reg.educational_takeaways)

    # Test classification
    res_clf = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="gradient_boosting",
        hyperparameters={"n_estimators": 20}
    )
    assert res_clf.task_type == "classification"
    assert res_clf.metrics.classification_metrics is not None
    assert len(res_clf.loss_curve) == 20


def test_train_knn(sample_ml_dataframe):
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="knn",
        hyperparameters={"n_neighbors": 3}
    )
    assert res.task_type == "classification"
    assert "K-Nearest Neighbors" in res.model_name
    assert res.metrics.classification_metrics is not None
    assert any("K-Nearest Neighbors" in t for t in res.educational_takeaways)


def test_train_svm(sample_ml_dataframe):
    # Classification with RBF kernel
    res_clf = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="svm",
        hyperparameters={"kernel": "rbf", "C": 1.0}
    )
    assert res_clf.task_type == "classification"
    assert "Support Vector" in res_clf.model_name
    assert res_clf.metrics.classification_metrics is not None
    assert any("Support Vector" in t for t in res_clf.educational_takeaways)

    # Regression with linear kernel
    res_reg = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="revenue",
        model_type="svm",
        hyperparameters={"kernel": "linear", "C": 1.0}
    )
    assert res_reg.task_type == "regression"
    assert "Support Vector" in res_reg.model_name


def test_target_suitability_and_failsafes(sample_ml_dataframe):
    from core.exceptions import ValidationError

    df = sample_ml_dataframe.copy()
    df["order_id"] = [f"ORD_{1000 + i}" for i in range(len(df))]
    df["customer_name"] = [f"Client_{i}" for i in range(len(df))]
    df["constant_feature"] = 42

    targets = get_candidate_targets(df)
    target_map = {t["column"]: t for t in targets}

    # order_id, customer_name, and constant_feature should be flagged as ineligible
    assert target_map["order_id"]["is_suitable"] is False
    assert target_map["customer_name"]["is_suitable"] is False
    assert target_map["constant_feature"]["is_suitable"] is False
    assert "Identifier" in target_map["order_id"]["suitability_reason"]

    # revenue and churn must remain suitable
    assert target_map["revenue"]["is_suitable"] is True
    assert target_map["churn"]["is_suitable"] is True

    # Attempting to detect or train on order_id must raise ValidationError
    with pytest.raises(ValidationError):
        detect_ml_task(df, "order_id")

    with pytest.raises(ValidationError):
        train_model_on_dataframe(df, target_col="order_id", model_type="linear_regression")

    # Attempting to train on customer_name must raise ValidationError
    with pytest.raises(ValidationError):
        train_model_on_dataframe(df, target_col="customer_name", model_type="random_forest")


def test_feature_specs_and_single_record_prediction(sample_ml_dataframe):
    from services.ml.trainer import train_model_on_dataframe, predict_single_record, export_inference_code
    from uuid import uuid4

    test_id = str(uuid4())
    # Train model on dataset
    res = train_model_on_dataframe(
        df=sample_ml_dataframe,
        target_col="churn",
        model_type="decision_tree",
        dataset_id=test_id
    )
    assert len(res.feature_specs) > 0
    spec_names = [f.name for f in res.feature_specs]
    assert "revenue" in spec_names or "units_sold" in spec_names

    # Test single record prediction
    sample_inputs = {f.name: f.default_val for f in res.feature_specs}
    pred = predict_single_record(dataset_id=test_id, input_features=sample_inputs)
    assert pred.task_type == "classification"
    assert pred.predicted_class is not None
    assert pred.probabilities is not None

    # Test code export
    export_code = export_inference_code(dataset_id=test_id)
    assert "import" in export_code
    assert "def run_inference" in export_code




