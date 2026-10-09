from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics import (
    r2_score,
    mean_squared_error,
    mean_absolute_error,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)
from models.schemas import (
    MLTrainResponse,
    MLEvaluationMetrics,
    MLConfusionMatrix,
    MLPredictionPoint,
    MLFeatureImportance,
    MLLossEpochPoint
)


def evaluate_model_pedagogy(
    model: Any,
    model_name: str,
    model_type: str,
    task_type: str,
    target_column: str,
    version_number: int,
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    feature_count: int,
    total_samples: int,
    feature_importance: List[MLFeatureImportance],
    loss_curve: List[MLLossEpochPoint]
) -> MLTrainResponse:
    """
    Computes regression or classification evaluation metrics, diagnoses
    overfitting vs underfitting, extracts scatter predictions, and drafts
    educational takeaways on data quality impact.
    """
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    regression_metrics: Optional[Dict[str, float]] = None
    classification_metrics: Optional[Dict[str, float]] = None

    if task_type == "regression":
        # R2 score can be negative on poor fits; bound reasonably for display
        train_score = float(round(r2_score(y_train, y_train_pred), 4))
        test_score = float(round(r2_score(y_test, y_test_pred), 4))

        rmse = float(round(np.sqrt(mean_squared_error(y_test, y_test_pred)), 4))
        mae = float(round(mean_absolute_error(y_test, y_test_pred), 4))

        # Safe MAPE calculation
        non_zero_mask = y_test != 0
        if np.any(non_zero_mask):
            mape = float(round(np.mean(np.abs((y_test[non_zero_mask] - y_test_pred[non_zero_mask]) / y_test[non_zero_mask])) * 100, 2))
        else:
            mape = 0.0

        regression_metrics = {
            "r2_score": test_score,
            "rmse": rmse,
            "mae": mae,
            "mape_percent": mape
        }

    else:
        # Classification Accuracy
        train_score = float(round(accuracy_score(y_train, y_train_pred), 4))
        test_score = float(round(accuracy_score(y_test, y_test_pred), 4))

        prec = float(round(precision_score(y_test, y_test_pred, average="weighted", zero_division=0), 4))
        rec = float(round(recall_score(y_test, y_test_pred, average="weighted", zero_division=0), 4))
        f1 = float(round(f1_score(y_test, y_test_pred, average="weighted", zero_division=0), 4))

        classification_metrics = {
            "accuracy": test_score,
            "precision": prec,
            "recall": rec,
            "f1_score": f1
        }

    # Overfitting Gap Calculation
    overfitting_score = float(round(train_score - test_score, 4))

    # Diagnose Generalization Status
    if overfitting_score >= 0.25 or (train_score >= 0.92 and test_score <= 0.65):
        overfitting_status = "severe_overfitting"
        overfitting_explanation = (
            f"Severe overfitting detected (gap: {round(overfitting_score * 100, 1)}%). "
            f"The model achieved high performance on training data ({round(train_score * 100, 1)}%) "
            f"but dropped significantly on unseen test records ({round(test_score * 100, 1)}%). "
            "This commonly occurs when uncleaned duplicate rows leak into training, when outliers distort splits, "
            "or when an unconstrained Decision Tree memorizes noise rather than generalizable signals."
        )
    elif overfitting_score >= 0.12:
        overfitting_status = "moderate_overfitting"
        overfitting_explanation = (
            f"Moderate overfitting observed (gap: {round(overfitting_score * 100, 1)}%). "
            "The model is capturing sample-specific nuances. Pruning tree depth, regularizing linear weights, "
            "or removing correlated redundant features will improve holdout stability."
        )
    elif train_score < 0.40 and test_score < 0.40:
        overfitting_status = "underfitting"
        overfitting_explanation = (
            f"Underfitting detected (Train: {round(train_score * 100, 1)}%, Test: {round(test_score * 100, 1)}%). "
            "The model lacks the capacity to capture patterns in the target, or the dataset has unhandled missing values, "
            "non-standardized scales, or weak feature correlations."
        )
    else:
        overfitting_status = "healthy_generalization"
        overfitting_explanation = (
            f"Healthy generalization achieved (Train: {round(train_score * 100, 1)}%, Test: {round(test_score * 100, 1)}%). "
            f"The small gap of {round(overfitting_score * 100, 1)}% confirms that the model will generalize reliably "
            "to novel holdout data without memorizing noise."
        )

    # Sample Prediction Coordinates (up to 40 points for SVG visualization)
    predictions: List[MLPredictionPoint] = []
    sample_indices = np.linspace(0, len(y_test) - 1, min(40, len(y_test)), dtype=int)
    for idx in sample_indices:
        act = float(round(y_test[idx], 2))
        prd = float(round(y_test_pred[idx], 2))
        res = float(round(act - prd, 2))
        predictions.append(
            MLPredictionPoint(
                actual=act,
                predicted=prd,
                residual=res
            )
        )

    # Pedagogical Takeaways based on model family and data characteristics
    takeaways = [
        f"Model: {model_name} trained on Version {version_number} with {feature_count} features across {total_samples} samples."
    ]

    if "decision_tree" in model_type:
        takeaways.append(
            "Decision Trees are highly vulnerable to noisy duplicate samples. An unconstrained tree splits repeatedly "
            "until training error is zero, causing massive variance on fresh test samples."
        )
    elif "random_forest" in model_type:
        takeaways.append(
            "Random Forests mitigate overfitting through bagging (bootstrap aggregation), averaging multiple decorrelated trees "
            "to produce smoother decision boundaries and lower variance."
        )
    elif "gradient_boosting" in model_type or "gbdt" in model_type:
        takeaways.append(
            "Gradient Boosting constructs decision trees sequentially, with each tree correcting the residual errors "
            "of the previous ones. Notice how the staged loss/deviance drops iteration by iteration in the Loss Curve tab."
        )
    elif "knn" in model_type or "k_nearest_neighbors" in model_type:
        takeaways.append(
            "K-Nearest Neighbors is an instance-based distance learner. Without feature standardization or when extreme "
            "outliers exist, high-magnitude dimensions dominate Euclidean distances, severely degrading neighbor queries."
        )
    elif "svm" in model_type or "svc" in model_type or "svr" in model_type:
        takeaways.append(
            "Support Vector Machines construct optimal maximum-margin separating hyperplanes. Noise and outlier points "
            "situated near decision boundaries can misplace the margin and destabilize classification confidence."
        )
    elif "mlp" in model_type or "neural_network" in model_type:
        takeaways.append(
            "Neural Networks rely on backpropagation and gradient descent. Unscaled features or extreme outliers cause gradients "
            "to explode or oscillate, whereas standardized inputs produce smooth convergence across training epochs."
        )
    else:
        takeaways.append(
            "Linear models assume additive relationships. Outliers disproportionately tilt the regression hyper-plane; "
            "clipping or removing statistical outliers dramatically stabilizes model coefficients."
        )

    if overfitting_status in {"severe_overfitting", "moderate_overfitting"}:
        takeaways.append(
            "💡 Data Action: Run 'Remove Duplicate Rows' and 'Handle Outliers (IQR Clip)' to observe the overfitting gap close."
        )

    conf_matrix: Optional[MLConfusionMatrix] = None
    if task_type != "regression":
        try:
            labels_unique = np.unique(np.concatenate([y_test, y_test_pred]))
            cm = confusion_matrix(y_test, y_test_pred, labels=labels_unique)
            conf_matrix = MLConfusionMatrix(
                labels=[str(lbl) for lbl in labels_unique],
                matrix=[[int(val) for val in row] for row in cm],
                total_samples=int(len(y_test))
            )
        except Exception:
            conf_matrix = None

    metrics = MLEvaluationMetrics(
        task_type=task_type,
        train_score=train_score,
        test_score=test_score,
        overfitting_score=overfitting_score,
        overfitting_status=overfitting_status,
        overfitting_explanation=overfitting_explanation,
        regression_metrics=regression_metrics,
        classification_metrics=classification_metrics,
        confusion_matrix=conf_matrix
    )

    return MLTrainResponse(
        model_name=model_name,
        model_type=model_type,
        target_column=target_column,
        task_type=task_type,
        version_number=version_number,
        total_samples=total_samples,
        feature_count=feature_count,
        metrics=metrics,
        feature_importance=feature_importance,
        loss_curve=loss_curve,
        predictions=predictions,
        educational_takeaways=takeaways
    )


# ==============================================================================
# FILE SUMMARY: backend/services/ml/evaluator.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the pedagogical evaluation and overfitting diagnostic engine:
#   1. Computes standardized R2, RMSE, MAE, MAPE (Regression) or Accuracy, F1 (Classification).
#   2. Calculates the Overfitting Score (train_score - test_score) and categorizes generalization.
#   3. Generates educational explanations linking data hygiene defects (duplicates, outliers)
#      to generalization dropoffs.
#   4. Samples actual vs. predicted points for SVG visualization.
# ==============================================================================
