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
    MLLossEpochPoint,
    MLFeatureSpec
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
    loss_curve: List[MLLossEpochPoint],
    feature_specs: Optional[List[MLFeatureSpec]] = None
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

    # Plain English Takeaways based on model family and data characteristics
    takeaways = [
        f"Model: {model_name} trained on Version {version_number} with {feature_count} features across {total_samples} samples."
    ]

    if "decision_tree" in model_type:
        takeaways.append(
            "Decision Trees can easily memorize noise and duplicate rows. When a tree tries too hard to be 100% perfect on training data, "
            "it struggles to make accurate predictions on brand-new data."
        )
    elif "random_forest" in model_type:
        takeaways.append(
            "Random Forests prevent memorization by combining predictions from multiple diverse trees, "
            "making overall predictions much more reliable and balanced."
        )
    elif "gradient_boosting" in model_type or "gbdt" in model_type:
        takeaways.append(
            "Gradient Boosting builds trees one after another, where each new tree focuses on fixing the mistakes "
            "of the previous one to steadily improve accuracy."
        )
    elif "knn" in model_type or "k_nearest_neighbors" in model_type:
        takeaways.append(
            "K-Nearest Neighbors predicts by looking at the closest matching rows. Wild outliers or unscaled columns "
            "can distort distances, so cleaning and normalizing data helps it make fair comparisons."
        )
    elif "svm" in model_type or "svc" in model_type or "svr" in model_type:
        takeaways.append(
            "Support Vector Machines find a clear dividing boundary between groups. Outliers right near that boundary "
            "can pull the line off track, so cleaning boundary noise keeps predictions confident."
        )
    elif "mlp" in model_type or "neural_network" in model_type or "neural_net" in model_type or "nn" in model_type:
        takeaways.append(
            "Neural Networks learn step-by-step from patterns. When numbers are too large or have extreme outliers, "
            "learning becomes erratic; scaling your features helps the network learn smoothly."
        )
    else:
        takeaways.append(
            "Linear and logistic models draw a best-fit line through your data. A single extreme outlier can pull this line "
            "way off course; removing or clipping outliers keeps the model balanced and trustworthy."
        )

    if overfitting_status in {"severe_overfitting", "moderate_overfitting"}:
        takeaways.append(
            "💡 Recommended Action: Run 'Remove Duplicate Rows' and 'Handle Outliers (IQR Clip)' to prevent the model from memorizing noisy data."
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
        educational_takeaways=takeaways,
        feature_specs=feature_specs or []
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
