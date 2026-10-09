import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
import pandas as pd
from fastapi import APIRouter, Depends, status

from core.auth import get_current_user
from core.config import settings
from core.exceptions import ResourceNotFoundError, ValidationError
from core.supabase_client import supabase
from models.schemas import (
    MLTrainRequest,
    MLTrainResponse,
    MLCompareRequest,
    MLCompareResponse
)
from services.datasets import load_version_dataframe, _DEV_DATAFRAME_CACHE
from services.ml.trainer import (
    train_model_on_dataframe,
    get_candidate_targets
)
from services.ml.comparator import compare_model_across_dataframes

logger = logging.getLogger("ai_analyst_backend.api.ml")

router = APIRouter(prefix="/datasets/{dataset_id}/ml", tags=["Machine Learning"])


def _load_dataframe_for_version(
    dataset_id: UUID,
    version_id: Optional[UUID] = None,
    version_number: Optional[int] = None
) -> Tuple[pd.DataFrame, int]:
    """
    Helper resolving DataFrame and version number for training or comparison.
    """
    str_dataset_id = str(dataset_id)

    # 1. Mock / Local Dev Mode
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        target_vnum = version_number or 1
        key = f"{str_dataset_id}_v{target_vnum}"
        if key in _DEV_DATAFRAME_CACHE:
            return _DEV_DATAFRAME_CACHE[key].copy(), target_vnum
        if str_dataset_id in _DEV_DATAFRAME_CACHE:
            return _DEV_DATAFRAME_CACHE[str_dataset_id].copy(), target_vnum

        # Search any cache matching dataset_id
        for k, df in _DEV_DATAFRAME_CACHE.items():
            if str_dataset_id in k:
                return df.copy(), target_vnum

        # Fallback to sample data
        sample_df = load_version_dataframe("mock_bucket/sample.csv", str_dataset_id)
        return sample_df, target_vnum

    # 2. Supabase Cloud Database Mode
    d_res = supabase.table("datasets").select("*").eq("id", str_dataset_id).execute()
    if not d_res.data:
        raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
    dataset = d_res.data[0]

    if version_id:
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(version_id)).execute()
    elif version_number:
        v_res = supabase.table("dataset_versions").select("*").eq("dataset_id", str_dataset_id).eq("version_number", version_number).execute()
    else:
        active_vid = dataset.get("active_version_id")
        if not active_vid:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(active_vid)).execute()

    if not v_res.data:
        raise ResourceNotFoundError("Dataset version snapshot not found.", "VERSION_NOT_FOUND")

    version_record = v_res.data[0]
    storage_path = version_record.get("storage_path", "")
    v_num = version_record.get("version_number", 1)

    df = load_version_dataframe(storage_path, str_dataset_id)
    return df, v_num


@router.get("/targets", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
def get_ml_target_candidates(
    dataset_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Inspects active version columns and returns candidates suitable for Regression or Classification.
    """
    logger.info(f"User {current_user.id} requested ML targets for dataset {dataset_id}")
    df, _ = _load_dataframe_for_version(dataset_id)
    return get_candidate_targets(df)


@router.post("/train", response_model=MLTrainResponse, status_code=status.HTTP_200_OK)
def train_ml_model(
    dataset_id: UUID,
    payload: MLTrainRequest,
    current_user = Depends(get_current_user)
):
    """
    Trains a Scikit-Learn model in-memory on the active or specified version.
    Tracks gradient descent loss curves (for Neural Networks), evaluates overfitting,
    computes feature importances, and returns pedagogical takeaways.
    """
    logger.info(f"User {current_user.id} training {payload.model_type} on target '{payload.target_column}' for dataset {dataset_id}")
    df, v_num = _load_dataframe_for_version(dataset_id, version_id=payload.version_id)

    if payload.target_column not in df.columns:
        raise ValidationError(f"Target column '{payload.target_column}' does not exist in dataset.", "COLUMN_NOT_FOUND")

    return train_model_on_dataframe(
        df=df,
        target_col=payload.target_column,
        model_type=payload.model_type,
        test_size=payload.test_size,
        hyperparameters=payload.hyperparameters,
        version_number=v_num,
        selected_features=payload.selected_features
    )


@router.post("/compare", response_model=MLCompareResponse, status_code=status.HTTP_200_OK)
def compare_ml_across_versions(
    dataset_id: UUID,
    payload: MLCompareRequest,
    current_user = Depends(get_current_user)
):
    """
    Trains an identical model architecture across two dataset versions (e.g. Raw v1 vs Cleaned v2)
    and quantifies the direct impact of data preprocessing on accuracy, R2, and overfitting reduction.
    """
    logger.info(f"User {current_user.id} comparing {payload.model_type} across versions for dataset {dataset_id}")

    base_vnum = payload.base_version_number or 1
    df_base, actual_base_vnum = _load_dataframe_for_version(dataset_id, version_number=base_vnum)

    target_vnum = payload.target_version_number
    df_target, actual_target_vnum = _load_dataframe_for_version(dataset_id, version_number=target_vnum)

    if payload.target_column not in df_base.columns:
        raise ValidationError(f"Target column '{payload.target_column}' does not exist in base version v{actual_base_vnum}.", "COLUMN_NOT_FOUND")
    if payload.target_column not in df_target.columns:
        raise ValidationError(f"Target column '{payload.target_column}' does not exist in target version v{actual_target_vnum}.", "COLUMN_NOT_FOUND")

    return compare_model_across_dataframes(
        df_base=df_base,
        df_target=df_target,
        target_column=payload.target_column,
        model_type=payload.model_type,
        base_version_number=actual_base_vnum,
        target_version_number=actual_target_vnum,
        hyperparameters=payload.hyperparameters,
        selected_features=payload.selected_features
    )


# ==============================================================================
# FILE SUMMARY: backend/api/ml.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the FastAPI routing endpoints for Machine Learning & Model Pedagogy:
#   1. GET /datasets/{id}/ml/targets: Discovers candidate target columns with inferred tasks.
#   2. POST /datasets/{id}/ml/train: Fits in-memory models (Ridge, DecisionTree,
#      RandomForest, Neural Network MLP), returns train vs. test scores, loss curves,
#      feature rankings, and overfitting diagnostics.
#   3. POST /datasets/{id}/ml/compare: Cross-version benchmark isolating the direct
#      performance delta achieved through data cleaning.
# ==============================================================================
