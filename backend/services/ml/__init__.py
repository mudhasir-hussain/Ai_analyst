"""
Machine Learning Impact Lab & Pedagogical Model Service Package.
Provides deterministic in-memory training, gradient descent loss curve tracking,
overfitting/underfitting diagnostics, and cross-version data quality comparisons.
"""

from .trainer import train_model_on_dataframe, detect_ml_task, get_candidate_targets
from .evaluator import evaluate_model_pedagogy
from .comparator import compare_model_across_dataframes

__all__ = [
    "train_model_on_dataframe",
    "detect_ml_task",
    "get_candidate_targets",
    "evaluate_model_pedagogy",
    "compare_model_across_dataframes"
]
