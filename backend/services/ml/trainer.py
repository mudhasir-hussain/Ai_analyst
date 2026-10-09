import logging
import re
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier
)
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
from sklearn.svm import SVR, SVC
from sklearn.neural_network import MLPRegressor, MLPClassifier

from models.schemas import (
    MLTrainResponse,
    MLLossEpochPoint,
    MLFeatureImportance
)
from core.exceptions import ValidationError
from .evaluator import evaluate_model_pedagogy

logger = logging.getLogger(__name__)

ID_COLUMN_PATTERN = re.compile(
    r"(?:^|[_\W])(id|uuid|guid|key|pk|hash|token|ssn|index)(?:$|[_\W])",
    re.IGNORECASE
)

FREE_TEXT_NAME_PATTERN = re.compile(
    r"(?:^|[_\W])(name|full_name|first_name|last_name|email|phone|url|address|city|street|zip|description|notes|comment|review|title|bio|summary)(?:$|[_\W])",
    re.IGNORECASE
)


def evaluate_target_suitability(series: pd.Series, col_name: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether a column is eligible to be modeled as a supervised ML target.
    Returns (is_suitable, reason_if_not_suitable).
    """
    non_null = series.dropna()
    total_len = len(series)
    non_null_len = len(non_null)

    if non_null_len < 5:
        return False, "Fewer than 5 non-null rows"

    if (total_len - non_null_len) / total_len > 0.60:
        pct = round((total_len - non_null_len) / total_len * 100)
        return False, f"Excessive missing values ({pct}% null)"

    unique_count = int(non_null.nunique())
    if unique_count <= 1:
        return False, "Constant column (zero variance)"

    # Datetime timestamp check
    if pd.api.types.is_datetime64_any_dtype(series) or col_name.lower().endswith(('_date', '_time', '_at', 'timestamp')):
        return False, "Datetime timestamp (cannot predict raw dates)"

    col_lower = col_name.lower().strip()

    # Identifiers / Primary Keys
    is_id_name = bool(ID_COLUMN_PATTERN.search(col_name)) or col_lower.endswith('_id') or col_lower.startswith('id_')
    if is_id_name:
        if unique_count > 15 or unique_count / non_null_len > 0.4:
            return False, "Identifier / Unique key (arbitrary IDs cannot be predicted)"

    # Text / Names / Emails
    is_text_name = bool(FREE_TEXT_NAME_PATTERN.search(col_name))
    if not pd.api.types.is_numeric_dtype(series):
        if is_text_name and unique_count > 10:
            return False, f"Name/Text entity ({unique_count} distinct text values)"
        if unique_count > 25:
            return False, f"High-cardinality text ({unique_count} categories; max 25 for classification)"
        if unique_count / non_null_len > 0.35 and unique_count > 8:
            return False, "High-cardinality non-numeric values (near-unique text)"

    # Numeric sequential index
    if pd.api.types.is_numeric_dtype(series):
        if is_id_name and unique_count == non_null_len:
            return False, "Sequential numeric index / ID"

    return True, None


def detect_ml_task(df: pd.DataFrame, target_col: str, enforce_suitability: bool = True) -> str:
    """
    Infers whether the given target column represents a Regression or Classification task,
    while enforcing strict validation failsafes against ID/name/unsuitable columns.
    """
    if target_col not in df.columns:
        raise ValidationError(f"Target column '{target_col}' not found in dataset.", "COLUMN_NOT_FOUND")

    series = df[target_col]
    if enforce_suitability:
        is_suitable, reason = evaluate_target_suitability(series, target_col)
        if not is_suitable:
            raise ValidationError(
                f"Column '{target_col}' cannot be used as an ML target: {reason}.",
                "INVALID_TARGET_COLUMN"
            )

    clean_series = series.dropna()
    if len(clean_series) == 0:
        raise ValidationError(f"Target column '{target_col}' has no non-null values.", "EMPTY_TARGET")

    # String, category, boolean, or object types are classification
    if not pd.api.types.is_numeric_dtype(clean_series):
        return "classification"

    unique_vals = clean_series.nunique()
    # Low unique counts or binary 0/1 are classification
    if unique_vals <= 2:
        return "classification"
    if unique_vals <= 10 and (clean_series % 1 == 0).all():
        return "classification"

    return "regression"


def get_candidate_targets(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Inspects all dataset columns and evaluates suitability as ML targets.
    Returns categorized candidates with task type, suitability flag, and explanatory reason.
    Suitable columns are sorted first.
    """
    candidates = []
    for col in df.columns:
        try:
            series = df[col]
            is_suitable, reason = evaluate_target_suitability(series, col)
            task = detect_ml_task(df, col, enforce_suitability=False) if is_suitable else "ineligible"
            unique_count = int(series.dropna().nunique())
            candidates.append({
                "column": col,
                "task_type": task,
                "data_type": str(series.dtype),
                "unique_values": unique_count,
                "null_count": int(series.isnull().sum()),
                "is_suitable": is_suitable,
                "suitability_reason": reason
            })
        except Exception:
            continue

    # Sort so suitable targets appear first, then alphabetically
    candidates.sort(key=lambda c: (not c["is_suitable"], c["column"]))
    return candidates


def prepare_features(
    df: pd.DataFrame,
    target_col: str,
    selected_features: Optional[List[str]] = None
) -> Tuple[np.ndarray, np.ndarray, List[str], ColumnTransformer]:
    """
    Preprocesses feature columns into numeric matrices with scaling and one-hot encoding.
    """
    # Filter rows with non-null target
    clean_df = df.dropna(subset=[target_col]).copy()
    if len(clean_df) < 5:
        raise ValidationError("Dataset must contain at least 5 rows with non-null target values.", "INSUFFICIENT_DATA")

    y_raw = clean_df[target_col].values
    X_df = clean_df.drop(columns=[target_col])

    if selected_features is not None:
        valid_selected = [c for c in selected_features if c in X_df.columns]
        if not valid_selected:
            raise ValidationError("At least one selected feature must exist in the dataset.", "NO_FEATURES")
        X_df = X_df[valid_selected]

    if X_df.shape[1] == 0:
        raise ValidationError("At least one feature column is required besides the target.", "NO_FEATURES")

    # Drop obvious high-cardinality unique ID columns if not explicitly selected
    if selected_features is None:
        drop_candidates = []
        for col in X_df.columns:
            if X_df[col].nunique() == len(X_df) and not pd.api.types.is_numeric_dtype(X_df[col]):
                drop_candidates.append(col)
            elif pd.api.types.is_datetime64_any_dtype(X_df[col]):
                drop_candidates.append(col)

        if drop_candidates and len(drop_candidates) < X_df.shape[1]:
            X_df = X_df.drop(columns=drop_candidates)

    numeric_cols = [c for c in X_df.columns if pd.api.types.is_numeric_dtype(X_df[c])]
    categorical_cols = [c for c in X_df.columns if c not in numeric_cols]

    transformers = []
    if numeric_cols:
        num_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", num_pipeline, numeric_cols))

    if categorical_cols:
        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    X_processed = preprocessor.fit_transform(X_df)

    # Reconstruct feature names
    feature_names = []
    if numeric_cols:
        feature_names.extend(numeric_cols)
    if categorical_cols:
        try:
            ohe = preprocessor.named_transformers_["cat"].named_steps["ohe"]
            cat_feature_names = ohe.get_feature_names_out(categorical_cols).tolist()
            feature_names.extend(cat_feature_names)
        except Exception:
            feature_names.extend([f"cat_{i}" for i in range(X_processed.shape[1] - len(numeric_cols))])

    # Convert y to appropriate type
    task = detect_ml_task(df, target_col)
    if task == "classification":
        # Label encode if non-numeric
        if not pd.api.types.is_numeric_dtype(clean_df[target_col]):
            labels, uniques = pd.factorize(clean_df[target_col])
            y_processed = labels
        else:
            y_processed = y_raw.astype(int)
    else:
        y_processed = y_raw.astype(float)

    return X_processed, y_processed, feature_names, preprocessor


def train_model_on_dataframe(
    df: pd.DataFrame,
    target_col: str,
    model_type: str = "linear_regression",
    test_size: float = 0.2,
    hyperparameters: Optional[Dict[str, Any]] = None,
    version_number: int = 1,
    selected_features: Optional[List[str]] = None
) -> MLTrainResponse:
    """
    Trains the chosen model on the DataFrame, tracks gradient descent loss curves
    (for MLP), computes overfitting gap, and compiles pedagogical diagnostics.
    """
    params = hyperparameters or {}
    task_type = detect_ml_task(df, target_col)
    X, y, feature_names, _ = prepare_features(df, target_col, selected_features=selected_features)

    # Train / Test split
    stratify = None
    if task_type == "classification":
        # Only stratify if all classes have at least 2 instances
        class_counts = pd.Series(y).value_counts()
        if (class_counts >= 2).all() and len(class_counts) > 1:
            stratify = y

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )

    model_key = model_type.lower().strip()
    loss_curve_points: List[MLLossEpochPoint] = []
    model = None
    model_name = "Model"

    # 1. Linear / Logistic Models
    if model_key in {"linear", "linear_regression"}:
        if task_type == "regression":
            model = Ridge(alpha=1.0)
            model_name = "Linear Regression (Ridge Regularized)"
        else:
            model = LogisticRegression(max_iter=500, random_state=42)
            model_name = "Logistic Regression"

    # 2. Decision Tree Models (pedagogical overfitting example)
    elif model_key in {"tree", "decision_tree"}:
        max_depth = params.get("max_depth")
        if max_depth is not None and str(max_depth).isdigit():
            max_depth = int(max_depth)
        else:
            max_depth = None  # Unconstrained depth allows memorization of duplicates/noise

        if task_type == "regression":
            model = DecisionTreeRegressor(max_depth=max_depth, random_state=42)
            model_name = f"Decision Tree Regressor (Depth: {max_depth or 'Unconstrained'})"
        else:
            model = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
            model_name = f"Decision Tree Classifier (Depth: {max_depth or 'Unconstrained'})"

    # 3. Random Forest Models (ensemble generalization)
    elif model_key in {"forest", "random_forest"}:
        n_estimators = int(params.get("n_estimators", 40))
        max_depth = params.get("max_depth")
        if max_depth is not None and str(max_depth).isdigit():
            max_depth = int(max_depth)
        else:
            max_depth = 8

        if task_type == "regression":
            model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
            model_name = f"Random Forest Regressor ({n_estimators} Trees)"
        else:
            model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
            model_name = f"Random Forest Classifier ({n_estimators} Trees)"

    # 4. Neural Network (Multi-Layer Perceptron)
    elif model_key in {"mlp", "neural_network", "neural_network_mlp", "nn"}:
        max_iter = int(params.get("max_iter", 75))
        lr = float(params.get("learning_rate", 0.01))
        hidden_layers = (32, 16)

        if task_type == "regression":
            model = MLPRegressor(
                hidden_layer_sizes=hidden_layers,
                max_iter=max_iter,
                learning_rate_init=lr,
                random_state=42,
                early_stopping=False
            )
            model_name = f"Multi-Layer Perceptron (NN: {hidden_layers[0]}x{hidden_layers[1]})"
        else:
            model = MLPClassifier(
                hidden_layer_sizes=hidden_layers,
                max_iter=max_iter,
                learning_rate_init=lr,
                random_state=42,
                early_stopping=False
            )
            model_name = f"Multi-Layer Perceptron Classifier (NN: {hidden_layers[0]}x{hidden_layers[1]})"

    # 5. Gradient Boosting Decision Trees (GBDT)
    elif model_key in {"gradient_boosting", "gbdt", "gradient_boost"}:
        n_estimators = int(params.get("n_estimators", 45))
        max_depth = params.get("max_depth")
        if max_depth is not None and str(max_depth).isdigit():
            max_depth = int(max_depth)
        else:
            max_depth = 3
        learning_rate = float(params.get("learning_rate", 0.1))

        if task_type == "regression":
            model = GradientBoostingRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                random_state=42
            )
            model_name = f"Gradient Boosting Regressor ({n_estimators} Trees, Depth: {max_depth})"
        else:
            model = GradientBoostingClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                random_state=42
            )
            model_name = f"Gradient Boosting Classifier ({n_estimators} Trees, Depth: {max_depth})"

    # 6. K-Nearest Neighbors (KNN Distance-Based)
    elif model_key in {"knn", "k_nearest_neighbors", "kneighbors"}:
        raw_k = int(params.get("n_neighbors", 5))
        # Ensure k is valid for sample size
        n_neighbors = max(1, min(raw_k, max(1, len(X_train) - 1)))

        if task_type == "regression":
            model = KNeighborsRegressor(n_neighbors=n_neighbors, weights="distance")
            model_name = f"K-Nearest Neighbors Regressor (K={n_neighbors})"
        else:
            model = KNeighborsClassifier(n_neighbors=n_neighbors, weights="distance")
            model_name = f"K-Nearest Neighbors Classifier (K={n_neighbors})"

    # 7. Support Vector Machine (SVM / SVR)
    elif model_key in {"svm", "svc", "svr", "support_vector_machine"}:
        c_param = float(params.get("C", 1.0))
        kernel = str(params.get("kernel", "rbf"))

        if task_type == "regression":
            model = SVR(C=c_param, kernel=kernel)
            model_name = f"Support Vector Regressor (SVR, kernel={kernel})"
        else:
            model = SVC(C=c_param, kernel=kernel, probability=True, random_state=42)
            model_name = f"Support Vector Classifier (SVC, kernel={kernel})"

    else:
        # Default fallback
        if task_type == "regression":
            model = Ridge(alpha=1.0)
            model_name = "Linear Regression (Ridge Regularized)"
        else:
            model = LogisticRegression(max_iter=500, random_state=42)
            model_name = "Logistic Regression"

    # Fit Model
    model.fit(X_train, y_train)

    # Extract Neural Network or Gradient Boosting Loss Curves
    if hasattr(model, "loss_curve_"):
        raw_losses = getattr(model, "loss_curve_", [])
        for epoch_idx, l_val in enumerate(raw_losses, 1):
            loss_curve_points.append(
                MLLossEpochPoint(
                    epoch=epoch_idx,
                    loss=float(round(l_val, 4))
                )
            )
    elif hasattr(model, "train_score_"):
        raw_losses = getattr(model, "train_score_", [])
        for stage_idx, l_val in enumerate(raw_losses, 1):
            loss_curve_points.append(
                MLLossEpochPoint(
                    epoch=stage_idx,
                    loss=float(round(l_val, 4))
                )
            )

    # Extract Feature Importance / Coefficients
    feature_importances: List[MLFeatureImportance] = []
    try:
        raw_importances = None
        if hasattr(model, "feature_importances_"):
            raw_importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            raw_importances = np.abs(model.coef_)
            if raw_importances.ndim > 1:
                raw_importances = np.mean(raw_importances, axis=0)

        if raw_importances is not None and len(raw_importances) == len(feature_names):
            norm_factor = np.sum(raw_importances)
            if norm_factor > 0:
                normalized = raw_importances / norm_factor
            else:
                normalized = raw_importances

            ranked = sorted(zip(feature_names, normalized), key=lambda x: x[1], reverse=True)
            for f_name, imp_val in ranked[:12]:
                feature_importances.append(
                    MLFeatureImportance(
                        feature=f_name,
                        importance=float(round(imp_val, 4))
                    )
                )
    except Exception as e:
        logger.warning(f"Could not calculate feature importances: {e}")

    # Evaluate Pedagogy, Overfitting, Residuals, and Takeaways
    return evaluate_model_pedagogy(
        model=model,
        model_name=model_name,
        model_type=model_key,
        task_type=task_type,
        target_column=target_col,
        version_number=version_number,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        feature_count=X.shape[1],
        total_samples=len(X),
        feature_importance=feature_importances,
        loss_curve=loss_curve_points
    )


# ==============================================================================
# FILE SUMMARY: backend/services/ml/trainer.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the deterministic in-memory Machine Learning training pipeline:
#   1. 'detect_ml_task': Automatically identifies Regression vs. Classification tasks.
#   2. 'get_candidate_targets': Inspects all dataset columns and suggests suitable prediction targets.
#   3. 'prepare_features': Cleans and encodes feature matrices with Median Imputation,
#      One-Hot Encoding, and Standard Scaling.
#   4. 'train_model_on_dataframe': Fits Scikit-Learn models (Ridge/Logistic, DecisionTree,
#      RandomForest, Gradient Boosting GBDT, K-Nearest Neighbors, Support Vector Machines,
#      and MLP Neural Networks), captures iterative/per-epoch loss curves, computes feature
#      importances, and invokes 'evaluate_model_pedagogy'.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/api/ml.py' and 'backend/services/ml/comparator.py'.
# - Returns structured Pydantic response models defined in 'backend/models/schemas.py'.
# ==============================================================================
