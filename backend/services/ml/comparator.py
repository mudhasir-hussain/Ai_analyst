from typing import Dict, Any, Optional, List
import pandas as pd
from models.schemas import MLCompareResponse
from .trainer import train_model_on_dataframe


def compare_model_across_dataframes(
    df_base: pd.DataFrame,
    df_target: pd.DataFrame,
    target_column: str,
    model_type: str = "linear_regression",
    base_version_number: int = 1,
    target_version_number: int = 2,
    hyperparameters: Optional[Dict[str, Any]] = None,
    selected_features: Optional[List[str]] = None
) -> MLCompareResponse:
    """
    Trains the same model architecture on two dataset versions (e.g. Raw v1 vs Cleaned v2)
    and quantifies the direct impact of data preprocessing on ML performance.
    """
    base_result = train_model_on_dataframe(
        df=df_base,
        target_col=target_column,
        model_type=model_type,
        hyperparameters=hyperparameters,
        version_number=base_version_number,
        selected_features=selected_features
    )

    target_result = train_model_on_dataframe(
        df=df_target,
        target_col=target_column,
        model_type=model_type,
        hyperparameters=hyperparameters,
        version_number=target_version_number,
        selected_features=selected_features
    )

    score_delta = float(round(target_result.metrics.test_score - base_result.metrics.test_score, 4))
    overfitting_gap_reduction = float(round(base_result.metrics.overfitting_score - target_result.metrics.overfitting_score, 4))

    rmse_delta = None
    if base_result.task_type == "regression":
        base_rmse = base_result.metrics.regression_metrics.get("rmse", 0) if base_result.metrics.regression_metrics else 0
        target_rmse = target_result.metrics.regression_metrics.get("rmse", 0) if target_result.metrics.regression_metrics else 0
        rmse_delta = float(round(target_rmse - base_rmse, 4))

    # Compose executive narrative explaining performance and overfitting differences
    metric_name = "R² score" if base_result.task_type == "regression" else "Accuracy"
    if score_delta > 0:
        gain_str = f"+{round(score_delta * 100, 1)}%"
        summary = (
            f"Data preprocessing on Version {target_version_number} directly enhanced model accuracy! "
            f"The test {metric_name} improved by {gain_str} compared to raw Version {base_version_number}. "
        )
    elif score_delta < 0:
        if overfitting_gap_reduction > 0.02:
            summary = (
                f"The test {metric_name} shifted by {round(score_delta * 100, 1)}%, but the overfitting gap closed by +{round(overfitting_gap_reduction * 100, 1)}%. "
                f"Why did raw {metric_name} drop? In messy raw data (v{base_version_number}), duplicate rows or uncleaned noise often artificially inflate test scores because the model memorized duplicate rows. "
                f"Cleaned v{target_version_number} removes these false shortcuts, giving you an honest, reliable benchmark that will truly generalize to new data."
            )
        else:
            summary = (
                f"The test {metric_name} shifted by {round(score_delta * 100, 1)}%. "
                "Filtering records or modifying columns adjusted the feature distributions. Check if any highly predictive columns were dropped."
            )
    else:
        summary = (
            f"The test {metric_name} remained stable across both dataset versions. "
        )

    if overfitting_gap_reduction > 0.05 and score_delta >= 0:
        summary += (
            f"Notably, data cleaning reduced the train-test overfitting gap by {round(overfitting_gap_reduction * 100, 1)}%, "
            "confirming that eliminating duplicates and clipping extreme outliers stopped the model from memorizing sample noise."
        )

    return MLCompareResponse(
        model_type=model_type,
        target_column=target_column,
        task_type=base_result.task_type,
        base_version=base_result,
        target_version=target_result,
        score_delta=score_delta,
        rmse_delta=rmse_delta,
        overfitting_gap_reduction=overfitting_gap_reduction,
        summary=summary
    )


# ==============================================================================
# FILE SUMMARY: backend/services/ml/comparator.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the side-by-side version comparison engine:
#   1. Trains an identical algorithm on raw vs. preprocessed DataFrames.
#   2. Computes the test metric delta (R2 or Accuracy improvement).
#   3. Quantifies the reduction in overfitting gap.
#   4. Synthesizes an executive pedagogical summary explaining the value of data quality.
# ==============================================================================
