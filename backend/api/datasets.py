import logging
import uuid
import hashlib
import datetime
from typing import Optional, Union, List
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, UploadFile, Form, status, Response
from pydantic import UUID4
from core.auth import get_current_user
from core.config import settings
from core.supabase_client import supabase
from core.exceptions import DatabaseStorageError, ParsingError, ResourceNotFoundError
from models.schemas import (
    DatasetResponse,
    DatasetProfileResponse,
    DatasetHealthResponse,
    DatasetVersionResponse,
    OperationResponse,
    TransformRequest,
    TransformResponse,
    TransformPreviewResponse,
    TransformImpactSummary,
    AIPlanCreate,
    AIPlanResponse,
    AIAskRequest,
    AIAskResponse,
    DatasetStatisticsResponse,
    ChartRecommendation,
    VisualizationRequest,
    VisualizationResponse,
    DatasetVisualizationsResponse,
    ReportCreateRequest,
    ReportResponse,
    ExportRequest,
    VersionDiffResponse,
    RollbackRequest,
    RollbackResponse,
    AuditTimelineResponse
)
from services.datasets import (
    validate_file_size_and_type,
    parse_and_validate_dataset,
    upload_to_supabase_storage,
    save_version_dataframe,
    load_version_dataframe,
    generate_profile_and_schema,
    cache_dev_dataframe
)
from services.transformations import execute_transformations
from services.ai import (
    generate_ai_plan,
    approve_and_execute_plan,
    get_llm_provider,
    extract_and_parse_json,
    build_dataset_context,
    _DEV_AI_PLANS_CACHE
)
from services.analysis import (
    calculate_dataset_statistics,
    generate_chart_recommendations,
    build_visualization_data
)
from services.reports import (
    generate_dataset_report,
    export_dataset
)
from services.history import (
    list_dataset_versions,
    get_dataset_version,
    diff_dataset_versions,
    rollback_dataset_version,
    get_audit_timeline,
    register_dev_version,
    register_dev_operation,
    _DEV_VERSIONS_REGISTRY
)

logger = logging.getLogger("ai_analyst_backend.api.datasets")
router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    project_id: UUID4 = Form(..., description="The project workspace UUID this dataset belongs to."),
    sheet_name: Optional[str] = Form(None, description="Sheet name if uploading a multi-sheet XLSX."),
    file: UploadFile = File(..., description="The CSV or XLSX file to ingest."),
    current_user = Depends(get_current_user)
):
    filename = file.filename or "upload.csv"
    logger.info(f"Received upload request for file '{filename}' from user {current_user.email} in project {project_id}")

    ext = validate_file_size_and_type(file)

    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading upload file stream: {e}")
        raise ParsingError(
            detail=f"Failed to read uploaded file: {str(e)}",
            error_code="READ_ERROR"
        )

    df, schema_json, profile_json = parse_and_validate_dataset(
        file_content=file_content,
        filename=filename,
        sheet_name=sheet_name
    )

    dataset_id = uuid.uuid4()
    version_id = uuid.uuid4()

    storage_path = upload_to_supabase_storage(
        file_content=file_content,
        user_id=str(current_user.id),
        project_id=str(project_id),
        dataset_id=str(dataset_id),
        filename=filename
    )

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        logger.info("[Mock Mode] Simulating database insertions...")
        cache_dev_dataframe(str(dataset_id), df)
        cache_dev_dataframe(str(version_id), df)
        cache_dev_dataframe(f"{dataset_id}_v1", df)

        checksum = hashlib.sha256(file_content).hexdigest()
        now = datetime.datetime.now(datetime.timezone.utc)
        register_dev_version(str(dataset_id), {
            "id": str(version_id),
            "dataset_id": str(dataset_id),
            "parent_version_id": None,
            "version_number": 1,
            "storage_path": storage_path,
            "row_count": len(df),
            "column_count": len(df.columns),
            "schema_json": schema_json,
            "profile_json": profile_json,
            "checksum": checksum,
            "status": "active",
            "created_by": str(current_user.id),
            "created_at": now.isoformat()
        })
        register_dev_operation(str(dataset_id), {
            "id": str(uuid.uuid4()),
            "dataset_id": str(dataset_id),
            "source_version_id": str(version_id),
            "result_version_id": str(version_id),
            "initiated_by": str(current_user.id),
            "source": "upload",
            "summary": f"Initial upload of file '{filename}'",
            "operation_plan_json": {"action": "upload", "filename": filename, "format": ext.lstrip(".")},
            "impact_json": {
                "rows_before": 0,
                "rows_after": len(df),
                "columns_before": 0,
                "columns_after": len(df.columns),
                "rows_removed": 0,
                "columns_removed": 0,
                "cells_modified": 0
            },
            "status": "success",
            "created_at": now.isoformat()
        })

        return DatasetResponse(
            id=dataset_id,
            project_id=project_id,
            owner_id=current_user.id,
            original_filename=filename,
            source_format=ext.lstrip("."),
            sheet_name=sheet_name,
            original_storage_path=storage_path,
            active_version_id=version_id,
            status="active",
            created_at=now
        )

    try:
        logger.info(f"Inserting dataset metadata for {dataset_id}")
        dataset_record = {
            "id": str(dataset_id),
            "project_id": str(project_id),
            "owner_id": str(current_user.id),
            "original_filename": filename,
            "source_format": ext.lstrip("."),
            "sheet_name": sheet_name,
            "original_storage_path": storage_path,
            "active_version_id": None,
            "status": "processing"
        }
        supabase.table("datasets").insert(dataset_record).execute()

        checksum = hashlib.sha256(file_content).hexdigest()
        version_record = {
            "id": str(version_id),
            "dataset_id": str(dataset_id),
            "parent_version_id": None,
            "version_number": 1,
            "storage_path": storage_path,
            "row_count": len(df),
            "column_count": len(df.columns),
            "schema_json": schema_json,
            "profile_json": profile_json,
            "checksum": checksum,
            "status": "active",
            "created_by": str(current_user.id)
        }
        supabase.table("dataset_versions").insert(version_record).execute()

        supabase.table("datasets").update({
            "active_version_id": str(version_id),
            "status": "active"
        }).eq("id", str(dataset_id)).execute()

        logger.info("Database transactions completed successfully.")
        
        response = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not response.data:
            raise DatabaseStorageError(
                detail="Dataset metadata insertion verified, but retrieve failed.",
                error_code="METADATA_RETRIEVAL_FAILED"
            )
            
        return DatasetResponse(**response.data[0])

    except Exception as e:
        logger.error(f"Supabase Database transaction failed: {e}")
        raise DatabaseStorageError(
            detail=f"Failed to record dataset metadata: {str(e)}",
            error_code="DATABASE_INSERTION_ERROR"
        )


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def get_dataset_profile(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested profile for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if existing_versions:
            latest_v = existing_versions[-1]
            return DatasetProfileResponse(
                dataset_id=dataset_id,
                version_id=UUID4(latest_v["id"]),
                profile=latest_v.get("profile_json", {})
            )

        mock_version_id = uuid.uuid4()
        mock_profile = {
            "row_count": 100,
            "column_count": 4,
            "estimated_memory_bytes": 4096,
            "estimated_memory_mb": 0.0,
            "total_null_cells": 5,
            "null_percentage": 1.25,
            "duplicate_rows": 0,
            "duplicate_percentage": 0.0,
            "candidate_keys": ["id"],
            "columns": {
                "id": {"type": "numeric", "null_count": 0, "null_percentage": 0.0, "unique_count": 100, "min": 1, "max": 100, "pii_detected": []},
                "name": {"type": "text", "null_count": 0, "null_percentage": 0.0, "unique_count": 95, "avg_length": 12.4, "pii_detected": []},
                "email": {"type": "text", "null_count": 2, "null_percentage": 2.0, "unique_count": 98, "pii_detected": ["email"]},
                "score": {"type": "numeric", "null_count": 3, "null_percentage": 3.0, "unique_count": 45, "mean": 78.5, "median": 80.0, "pii_detected": []}
            }
        }
        return DatasetProfileResponse(
            dataset_id=dataset_id,
            version_id=mock_version_id,
            profile=mock_profile
        )

    res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
    if not res.data:
        raise ResourceNotFoundError(
            detail=f"Dataset with ID '{dataset_id}' not found.",
            error_code="DATASET_NOT_FOUND"
        )
    
    dataset = res.data[0]
    active_version_id = dataset.get("active_version_id")
    if not active_version_id:
        raise ResourceNotFoundError(
            detail=f"Dataset '{dataset_id}' has no active version snapshot.",
            error_code="NO_ACTIVE_VERSION"
        )

    v_res = supabase.table("dataset_versions").select("*").eq("id", str(active_version_id)).execute()
    if not v_res.data:
        raise ResourceNotFoundError(
            detail="Active dataset version snapshot record not found.",
            error_code="VERSION_NOT_FOUND"
        )

    version_record = v_res.data[0]
    return DatasetProfileResponse(
        dataset_id=dataset_id,
        version_id=active_version_id,
        profile=version_record.get("profile_json", {})
    )


@router.get("/{dataset_id}/health", response_model=DatasetHealthResponse)
async def get_dataset_health(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested health evaluation for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if existing_versions:
            latest_v = existing_versions[-1]
            profile_json = latest_v.get("profile_json", {})
            health_data = profile_json.get("health", {})
            return DatasetHealthResponse(
                dataset_id=dataset_id,
                version_id=UUID4(latest_v["id"]),
                health_score=health_data.get("health_score", 100),
                rating=health_data.get("rating", "excellent"),
                total_issues=health_data.get("total_issues", 0),
                issues=health_data.get("issues", [])
            )

        mock_version_id = uuid.uuid4()
        return DatasetHealthResponse(
            dataset_id=dataset_id,
            version_id=mock_version_id,
            health_score=92,
            rating="excellent",
            total_issues=1,
            issues=[
                {
                    "code": "PII_DETECTED",
                    "level": "warning",
                    "column": "email",
                    "message": "Column 'email' contains sensitive PII data: email.",
                    "metric_value": 1.0,
                    "recommendation": "Anonymize or drop sensitive PII column 'email' before exporting."
                }
            ]
        )

    res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
    if not res.data:
        raise ResourceNotFoundError(
            detail=f"Dataset with ID '{dataset_id}' not found.",
            error_code="DATASET_NOT_FOUND"
        )

    dataset = res.data[0]
    active_version_id = dataset.get("active_version_id")
    if not active_version_id:
        raise ResourceNotFoundError(
            detail=f"Dataset '{dataset_id}' has no active version snapshot.",
            error_code="NO_ACTIVE_VERSION"
        )

    v_res = supabase.table("dataset_versions").select("*").eq("id", str(active_version_id)).execute()
    if not v_res.data:
        raise ResourceNotFoundError(
            detail="Active dataset version snapshot record not found.",
            error_code="VERSION_NOT_FOUND"
        )

    version_record = v_res.data[0]
    profile_json = version_record.get("profile_json", {})
    health_data = profile_json.get("health", {})

    return DatasetHealthResponse(
        dataset_id=dataset_id,
        version_id=active_version_id,
        health_score=health_data.get("health_score", 100),
        rating=health_data.get("rating", "excellent"),
        total_issues=health_data.get("total_issues", 0),
        issues=health_data.get("issues", [])
    )


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: UUID4,
    limit: int = 50,
    current_user = Depends(get_current_user)
):
    """
    Returns column names, paginated row records, and total row count for the active version.
    """
    logger.info(f"User {current_user.id} requested preview for dataset {dataset_id} (limit={limit})")
    
    storage_path = "mock_bucket/sample.csv"
    if settings.SUPABASE_URL != "https://your-supabase-project.supabase.co":
        res = supabase.table("datasets").select("active_version_id").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(
                detail=f"Dataset with ID '{dataset_id}' not found.",
                error_code="DATASET_NOT_FOUND"
            )
        active_version_id = res.data[0].get("active_version_id")
        if active_version_id:
            v_res = supabase.table("dataset_versions").select("storage_path").eq("id", str(active_version_id)).execute()
            if v_res.data:
                storage_path = v_res.data[0].get("storage_path", storage_path)

    df = load_version_dataframe(storage_path, str(dataset_id))
    df_slice = df.head(limit)

    clean_df = df_slice.replace({np.nan: None, float("inf"): None, float("-inf"): None})
    clean_df = clean_df.where(pd.notnull(clean_df), None)
    rows = clean_df.to_dict(orient="records")

    return {
        "columns": list(df.columns),
        "rows": rows,
        "total_rows": len(df)
    }


@router.post("/{dataset_id}/transform", response_model=TransformResponse)
async def transform_dataset(
    dataset_id: UUID4,
    payload: TransformRequest,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested transformations for dataset {dataset_id}: {len(payload.operations)} operations")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if not existing_versions:
            from services.history.service import _ensure_dev_base_version
            base_v = _ensure_dev_base_version(dataset_id)
            if base_v:
                existing_versions = [base_v]

        source_version_id = UUID4(existing_versions[-1]["id"]) if existing_versions else uuid.uuid4()
        new_version_id = uuid.uuid4()
        operation_id = uuid.uuid4()
        project_id = uuid.uuid4()

        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
        transformed_df, impact_dict = execute_transformations(df, payload.operations)
        schema_json, profile_json = generate_profile_and_schema(transformed_df)

        next_ver_num = len(existing_versions) + 1 if existing_versions else 2

        storage_path, checksum, _ = save_version_dataframe(
            df=transformed_df,
            user_id=str(current_user.id),
            project_id=str(project_id),
            dataset_id=str(dataset_id),
            version_number=next_ver_num
        )
        cache_dev_dataframe(str(dataset_id), transformed_df)
        cache_dev_dataframe(str(new_version_id), transformed_df)
        cache_dev_dataframe(f"{dataset_id}_v{next_ver_num}", transformed_df)

        now = datetime.datetime.now(datetime.timezone.utc)
        impact = TransformImpactSummary(**impact_dict)

        new_version = DatasetVersionResponse(
            id=new_version_id,
            dataset_id=dataset_id,
            parent_version_id=source_version_id,
            version_number=next_ver_num,
            storage_path=storage_path,
            row_count=len(transformed_df),
            column_count=len(transformed_df.columns),
            schema_json=schema_json,
            profile_json=profile_json,
            checksum=checksum,
            status="active",
            created_by=current_user.id,
            created_at=now
        )

        operation_record = OperationResponse(
            id=operation_id,
            dataset_id=dataset_id,
            source_version_id=source_version_id,
            result_version_id=new_version_id,
            initiated_by=current_user.id,
            source=payload.source,
            operation_plan_json={"operations": payload.operations},
            summary=payload.summary or f"Applied {len(payload.operations)} cleaning operations",
            status="success",
            impact_json=impact_dict,
            error_code=None,
            created_at=now,
            completed_at=now
        )

        register_dev_version(str(dataset_id), new_version.model_dump(mode="json"))
        register_dev_operation(str(dataset_id), operation_record.model_dump(mode="json"))

        return TransformResponse(
            dataset_id=dataset_id,
            source_version_id=source_version_id,
            result_version_id=new_version_id,
            version_number=next_ver_num,
            impact=impact,
            new_version=new_version,
            operation=operation_record
        )

    res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
    if not res.data:
        raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")

    dataset = res.data[0]
    active_version_id = dataset.get("active_version_id")
    project_id = dataset.get("project_id")
    if not active_version_id:
        raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")

    v_res = supabase.table("dataset_versions").select("*").eq("id", str(active_version_id)).execute()
    if not v_res.data:
        raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")

    curr_version = v_res.data[0]
    curr_version_number = curr_version.get("version_number", 1)
    new_version_number = curr_version_number + 1
    new_version_id = uuid.uuid4()
    operation_id = uuid.uuid4()

    storage_path = curr_version.get("storage_path", "")
    df = load_version_dataframe(storage_path, str(dataset_id))

    transformed_df, impact_dict = execute_transformations(df, payload.operations)
    schema_json, profile_json = generate_profile_and_schema(transformed_df)

    new_storage_path, checksum, _ = save_version_dataframe(
        df=transformed_df,
        user_id=str(current_user.id),
        project_id=str(project_id),
        dataset_id=str(dataset_id),
        version_number=new_version_number
    )

    now = datetime.datetime.now(datetime.timezone.utc)

    new_version_row = {
        "id": str(new_version_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": str(active_version_id),
        "version_number": new_version_number,
        "storage_path": new_storage_path,
        "row_count": len(transformed_df),
        "column_count": len(transformed_df.columns),
        "schema_json": schema_json,
        "profile_json": profile_json,
        "checksum": checksum,
        "status": "active",
        "created_by": str(current_user.id)
    }
    supabase.table("dataset_versions").insert(new_version_row).execute()

    supabase.table("datasets").update({"active_version_id": str(new_version_id)}).eq("id", str(dataset_id)).execute()

    operation_row = {
        "id": str(operation_id),
        "dataset_id": str(dataset_id),
        "source_version_id": str(active_version_id),
        "result_version_id": str(new_version_id),
        "initiated_by": str(current_user.id),
        "source": payload.source,
        "operation_plan_json": {"operations": payload.operations},
        "summary": payload.summary or f"Applied {len(payload.operations)} cleaning operations",
        "status": "success",
        "impact_json": impact_dict,
        "error_code": None
    }
    supabase.table("operations").insert(operation_row).execute()

    impact = TransformImpactSummary(**impact_dict)
    new_version = DatasetVersionResponse(**new_version_row, created_at=now)
    operation_record = OperationResponse(**operation_row, created_at=now, completed_at=now)

    return TransformResponse(
        dataset_id=dataset_id,
        source_version_id=UUID4(active_version_id),
        result_version_id=new_version_id,
        version_number=new_version_number,
        impact=impact,
        new_version=new_version,
        operation=operation_record
    )


@router.post("/{dataset_id}/transform/preview", response_model=TransformPreviewResponse)
async def preview_transform_dataset(
    dataset_id: UUID4,
    payload: TransformRequest,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested transformation preview for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        source_version_id = uuid.uuid4()
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    transformed_df, impact_dict = execute_transformations(df, payload.operations)
    sample_preview = transformed_df.head(10).replace({np.nan: None}).to_dict(orient="records")

    return TransformPreviewResponse(
        dataset_id=dataset_id,
        source_version_id=UUID4(str(source_version_id)),
        impact=TransformImpactSummary(**impact_dict),
        sample_preview=sample_preview
    )


@router.post("/{dataset_id}/ai/plan", response_model=AIPlanResponse)
def create_ai_plan_for_dataset(
    dataset_id: UUID4,
    payload: AIPlanCreate,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested AI plan for dataset {dataset_id}")
    profile_data = None
    health_data = None

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if existing_versions:
            last_version = existing_versions[-1]
            source_version_id = UUID4(str(last_version["id"]))
            profile_data = last_version.get("profile_json")
        else:
            source_version_id = uuid.uuid4()
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        profile_data = curr_version.get("profile_json")
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    return generate_ai_plan(
        df=df,
        user_prompt=payload.user_prompt,
        dataset_id=dataset_id,
        version_id=UUID4(str(source_version_id)),
        user_id=current_user.id,
        profile=profile_data,
        health=health_data
    )


@router.post("/{dataset_id}/ai/plan/{plan_id}/approve", response_model=TransformResponse)
def approve_ai_plan_for_dataset(
    dataset_id: UUID4,
    plan_id: UUID4,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} approving AI plan {plan_id} for dataset {dataset_id}")
    return approve_and_execute_plan(
        dataset_id=dataset_id,
        plan_id=plan_id,
        current_user_id=current_user.id
    )


@router.post("/{dataset_id}/ai/auto-heal", response_model=TransformResponse)
def auto_heal_dataset(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    """
    1-Click AI Auto-Heal: Diagnoses all active data health issues and formulates
    an optimal composite cleaning pipeline to remediate quality defects.
    Immediately applies the remediation, bumps the dataset version, and returns
    the resulting transformed version with updated health profile.
    """
    logger.info(f"User {current_user.id} requested 1-Click AI Auto-Heal for dataset {dataset_id}")
    str_dataset_id = str(dataset_id)
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str_dataset_id, [])
        if existing_versions:
            source_version_id = existing_versions[-1]["id"]
        else:
            source_version_id = uuid.uuid4()
        df = load_version_dataframe("mock_bucket/sample.csv", str_dataset_id)
    else:
        res = supabase.table("datasets").select("*").eq("id", str_dataset_id).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        source_version_id = res.data[0].get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError(f"Active version snapshot not found for dataset '{dataset_id}'.", "VERSION_NOT_FOUND")
        df = load_version_dataframe(v_res.data[0].get("storage_path", ""), str_dataset_id)

    operations = []
    # 1. Duplicates
    if int(df.duplicated().sum()) > 0:
        operations.append({"type": "remove_duplicates"})

    # 2. Impute nulls & 3. Clip outliers
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if pd.api.types.is_numeric_dtype(df[col]):
            if null_count > 0:
                operations.append({"type": "fill_missing", "column": col, "strategy": "median"})
            series_clean = df[col].dropna()
            if len(series_clean) > 4:
                q25, q75 = float(series_clean.quantile(0.25)), float(series_clean.quantile(0.75))
                iqr = q75 - q25
                if iqr > 0:
                    lower_bound = q25 - (1.5 * iqr)
                    upper_bound = q75 + (1.5 * iqr)
                    outliers_count = int(((series_clean < lower_bound) | (series_clean > upper_bound)).sum())
                    if outliers_count > 0:
                        operations.append({
                            "type": "handle_outliers",
                            "column": col,
                            "method": "iqr",
                            "action": "clip",
                            "factor": 1.5
                        })
        else:
            if null_count > 0:
                operations.append({"type": "fill_missing", "column": col, "strategy": "mode"})
            operations.append({"type": "trim_text", "column": col})

    if not operations:
        operations.append({"type": "remove_duplicates"})

    plan_id = uuid.uuid4()
    plan_dict = {
        "summary": "AI Auto-Heal: Comprehensive 100% Data Quality Remediation Pipeline",
        "operations": operations,
        "warnings": ["Auto-Heal applied median imputation, IQR outlier clipping, and string trimming."],
        "requires_confirmation": False
    }

    plan_record = {
        "id": str(plan_id),
        "dataset_id": str(dataset_id),
        "version_id": str(source_version_id),
        "requested_by": str(current_user.id),
        "user_prompt": "Auto-heal and optimize dataset hygiene to 100%",
        "provider": "AIAutoHealEngine",
        "model": "auto-heal-pipeline",
        "plan_json": plan_dict,
        "validation_status": "validated",
        "warnings_json": plan_dict["warnings"],
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    _DEV_AI_PLANS_CACHE[str(plan_id)] = plan_record

    return approve_and_execute_plan(
        dataset_id=dataset_id,
        plan_id=plan_id,
        current_user_id=current_user.id
    )


@router.post("/{dataset_id}/ai/ask", response_model=AIAskResponse)
def ask_ai_about_dataset(
    dataset_id: UUID4,
    payload: AIAskRequest,
    current_user = Depends(get_current_user)
):
    """
    'Talk to Your Data': Answers analytical business questions about trends,
    patterns, and risk drivers using the resilient Gemini + Groq cloud pipeline.
    """
    logger.info(f"User {current_user.id} asked AI: '{payload.question}' on dataset {dataset_id}")
    str_dataset_id = str(dataset_id)
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        df = load_version_dataframe("mock_bucket/sample.csv", str_dataset_id)
    else:
        res = supabase.table("datasets").select("*").eq("id", str_dataset_id).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        source_version_id = res.data[0].get("active_version_id")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        df = load_version_dataframe(v_res.data[0].get("storage_path", ""), str_dataset_id)

    dataset_context = build_dataset_context(df)
    system_prompt = """You are the AI Data Analyst Assistant.
Your core mission is to answer user questions strictly about:
1. The uploaded dataset's metrics, columns, rows, correlations, and trends.
2. Recommended data cleaning and transformation steps (deduplication, imputation, outliers).
3. Machine learning concepts and performance comparisons on this platform.
4. Using the platform's features (upload, profile, clean, compare, reports).

STRICT BOUNDARY & GUARDRAILS:
- If the user asks anything unrelated to data analysis, data cleaning, machine learning, or this platform (e.g. general trivia, celebrities, movies, recipes, history, gaming, non-data coding, creative writing, politics, or absurd queries), you MUST politely decline:
  "I am your specialized AI Data Analyst. I can only assist with dataset analysis, data cleaning, and machine learning workflows on this platform. Please ask a question related to your data or our tools!"
- STRICT WORD LIMIT: Keep your answer concise (under 100 words total). Deliver crisp, direct, high-value insights. Do NOT write long essays. Save tokens.
- Plain English: Avoid academic jargon (no 'pedagogical', 'regression hyper-plane', etc.). Use friendly, accessible language.

Output MUST be ONLY a single valid JSON object adhering strictly to this schema:
{
  "answer": "Concise plain-English answer (under 100 words). If off-topic, provide the polite refusal.",
  "key_findings": [
    "Key takeaway 1 with specific figures or column metrics (if applicable)",
    "Key takeaway 2 (if applicable)"
  ],
  "suggested_questions": [
    "Relevant follow-up analytical question 1?",
    "Relevant follow-up analytical question 2?"
  ]
}"""
    user_prompt = f"{dataset_context}\n\nUSER QUESTION:\n{payload.question}\n\nFormulate your concise executive answer in the specified JSON format."

    provider = get_llm_provider()
    raw_response = provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
    provider_name = getattr(provider, "last_provider_used", None) or type(provider).__name__

    try:
        parsed = extract_and_parse_json(raw_response)
        findings = [str(f) for f in parsed.get("key_findings", [])]
        if provider_name == "rule-based-fallback":
            findings.append("Tip: Add GEMINI_API_KEY in backend/.env for live cloud-accelerated Gemini AI.")
        return AIAskResponse(
            answer=parsed.get("answer", "Analysis completed based on dataset statistics."),
            key_findings=findings,
            suggested_questions=[str(q) for q in parsed.get("suggested_questions", [])],
            provider_used=provider_name
        )
    except Exception as e:
        logger.warning(f"Could not parse AI response as JSON: {e}. Returning formatted text.")
        return AIAskResponse(
            answer=raw_response[:800],
            key_findings=["Direct analysis generated from dataset distributions."],
            suggested_questions=["What is the distribution of key metrics?", "Which segment has the highest variance?"],
            provider_used=provider_name
        )


@router.get("/{dataset_id}/statistics", response_model=DatasetStatisticsResponse)
async def get_dataset_statistics(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested statistics for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        source_version_id = UUID4(str(existing_versions[-1]["id"])) if existing_versions else uuid.uuid4()
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    stats = calculate_dataset_statistics(df)
    return DatasetStatisticsResponse(
        dataset_id=dataset_id,
        version_id=UUID4(str(source_version_id)),
        **stats
    )


@router.get("/{dataset_id}/visualizations", response_model=DatasetVisualizationsResponse)
async def get_visualizations(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    return await get_or_build_visualizations(dataset_id=dataset_id, payload=None, current_user=current_user)


@router.post("/{dataset_id}/visualizations", response_model=Union[DatasetVisualizationsResponse, VisualizationResponse])
async def get_or_build_visualizations(
    dataset_id: UUID4,
    payload: Optional[VisualizationRequest] = None,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested visualizations for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        source_version_id = UUID4(str(existing_versions[-1]["id"])) if existing_versions else uuid.uuid4()
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    if payload is None:
        recommendations = generate_chart_recommendations(df)
        previews = []
        for rec in recommendations[:2]:
            try:
                vis_data = build_visualization_data(
                    df=df,
                    chart_type=rec["chart_type"],
                    x_column=rec.get("x_column"),
                    y_column=rec.get("y_column"),
                    aggregation=rec.get("aggregation") or "sum",
                    limit=10
                )
                previews.append(VisualizationResponse(**vis_data))
            except Exception as e:
                logger.warning(f"Failed to generate preview for chart '{rec.get('title')}': {e}")

        return DatasetVisualizationsResponse(
            dataset_id=dataset_id,
            version_id=UUID4(str(source_version_id)),
            recommended_charts=[ChartRecommendation(**r) for r in recommendations],
            previews=previews
        )
    else:
        vis_data = build_visualization_data(
            df=df,
            chart_type=payload.chart_type,
            x_column=payload.x_column,
            y_column=payload.y_column,
            aggregation=payload.aggregation,
            group_by_column=payload.group_by_column,
            limit=payload.limit or 20
        )
        return VisualizationResponse(**vis_data)


@router.post("/{dataset_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_dataset_report(
    dataset_id: UUID4,
    payload: ReportCreateRequest,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested report generation for dataset {dataset_id}")
    profile_data = None
    active_version_number = 1

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if existing_versions:
            last_version = existing_versions[-1]
            source_version_id = UUID4(str(last_version["id"]))
            active_version_number = int(last_version.get("version_number", 1))
            profile_data = last_version.get("profile_json")
        else:
            source_version_id = uuid.uuid4()
            active_version_number = 1
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        active_version_number = curr_version.get("version_number", 1)
        profile_data = curr_version.get("profile_json")
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    return generate_dataset_report(
        df=df,
        dataset_id=dataset_id,
        version_id=UUID4(str(source_version_id)),
        version_number=active_version_number,
        user_id=current_user.id,
        request=payload,
        profile=profile_data
    )


@router.post("/{dataset_id}/export")
async def export_dataset_endpoint(
    dataset_id: UUID4,
    payload: ExportRequest,
    current_user = Depends(get_current_user)
):
    logger.info(f"User {current_user.id} requested '{payload.format}' export for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
        prefix = f"dataset_{str(dataset_id)[:8]}"
    else:
        res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = res.data[0]
        prefix = dataset.get("original_filename", f"dataset_{str(dataset_id)[:8]}")
        source_version_id = dataset.get("active_version_id")
        if not source_version_id:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' has no active version snapshot.", "NO_ACTIVE_VERSION")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active dataset version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    content_bytes, media_type, filename = export_dataset(df, format=payload.format, filename_prefix=prefix)
    return Response(
        content=content_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ------------------------------------------------------------------------------
# STEP 9: HISTORY, VERSIONING & AUDIT TIMELINE ENDPOINTS
# ------------------------------------------------------------------------------

@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
async def list_versions_endpoint(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    """
    Returns all immutable snapshot versions of a dataset, ordered sequentially.
    """
    logger.info(f"User {current_user.id} requested all versions for dataset {dataset_id}")
    return list_dataset_versions(dataset_id)


@router.get("/{dataset_id}/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_version_endpoint(
    dataset_id: UUID4,
    version_id: UUID4,
    current_user = Depends(get_current_user)
):
    """
    Retrieves metadata and statistical profile for a specific dataset version snapshot.
    """
    logger.info(f"User {current_user.id} requested version {version_id} for dataset {dataset_id}")
    return get_dataset_version(dataset_id, version_id)


@router.get("/{dataset_id}/versions/{version_id}/diff", response_model=VersionDiffResponse)
async def diff_version_endpoint(
    dataset_id: UUID4,
    version_id: UUID4,
    target_version_id: Optional[UUID4] = None,
    current_user = Depends(get_current_user)
):
    """
    Computes a semantic difference comparison between two dataset versions.
    If target_version_id is omitted, compares version_id to its immediate parent.
    """
    logger.info(f"User {current_user.id} requested diff for dataset {dataset_id}, source={version_id}, target={target_version_id}")
    return diff_dataset_versions(dataset_id, version_id, target_version_id)


@router.post("/{dataset_id}/versions/{version_id}/rollback", response_model=RollbackResponse)
async def rollback_version_endpoint(
    dataset_id: UUID4,
    version_id: UUID4,
    payload: Optional[RollbackRequest] = None,
    current_user = Depends(get_current_user)
):
    """
    Restores the dataset state to a selected version snapshot. Creates a new immutable
    version snapshot (vNext) without destructively modifying previous versions.
    """
    reason = payload.reason if payload else None
    logger.info(f"User {current_user.id} requested rollback for dataset {dataset_id} to version {version_id}")
    return rollback_dataset_version(dataset_id, version_id, current_user.id, reason)


@router.get("/{dataset_id}/timeline", response_model=AuditTimelineResponse)
async def get_timeline_endpoint(
    dataset_id: UUID4,
    current_user = Depends(get_current_user)
):
    """
    Returns the complete chronological audit timeline (uploads, manual operations,
    AI operation plans, and rollbacks) for a dataset.
    """
    logger.info(f"User {current_user.id} requested audit timeline for dataset {dataset_id}")
    return get_audit_timeline(dataset_id)


# ==============================================================================
# FILE SUMMARY: backend/api/datasets.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file is the primary HTTP routing interface for all dataset-related actions.
# It defines seventeen FastAPI endpoints mounted under the '/datasets' URL prefix:
#   1. POST /datasets/upload: Ingests, validates, parses, profiles, and registers a
#      new dataset, creating Version 1 and saving original bytes to storage.
#   2. GET /datasets/{dataset_id}/profile: Fetches statistical summaries, column types,
#      memory usage, and PII flags for the active version.
#   3. GET /datasets/{dataset_id}/health: Returns the 0-100 quality scorecard,
#      detected issues, and actionable remediation recommendations.
#   4. GET /datasets/{dataset_id}/preview: Returns paginated row dictionaries, column
#      names, and total count for tabular rendering.
#   5. POST /datasets/{dataset_id}/transform: Executes deterministic data cleaning
#      operations, generates a new immutable snapshot version, updates active version
#      pointers, records an audit log in the operations table, and returns impact metrics.
#   5. POST /datasets/{dataset_id}/transform/preview: Executes transformations in-memory
#      to return before/after impact summaries and 10-row data previews without persisting changes.
#   6. POST /datasets/{dataset_id}/ai/plan: Translates natural language requests into
#      strictly structured, pre-flight validated cleaning plans with impact warnings.
#   7. POST /datasets/{dataset_id}/ai/plan/{plan_id}/approve: Approves and applies a
#      previously validated AI operation plan, committing an immutable new DatasetVersion
#      marked with source='ai'.
#   8. GET /datasets/{dataset_id}/statistics: Calculates parametric and non-parametric
#      descriptive statistics, Pearson correlation matrix, and temporal trend analyses.
#   9. POST /datasets/{dataset_id}/visualizations: Generates intelligent chart recommendations
#      with previews or renders custom aggregated visual series for Bar, Line, Scatter,
#      Histogram, Box plot, and Heatmap charts.
#   10. POST /datasets/{dataset_id}/reports: Compiles executive reports across JSON,
#       GitHub Markdown, or responsive HTML formats.
#   11. POST /datasets/{dataset_id}/export: Streams active version data as downloadable
#       CSV or XLSX attachments.
#   12. GET /datasets/{dataset_id}/versions: Retrieves all sequential immutable version snapshots.
#   13. GET /datasets/{dataset_id}/versions/{version_id}: Retrieves metadata for a single version.
#   14. GET /datasets/{dataset_id}/versions/{version_id}/diff: Computes a semantic diff comparing
#       two version snapshots (shape deltas, column additions/removals/type shifts, null deltas).
#   15. POST /datasets/{dataset_id}/versions/{version_id}/rollback: Safely reverts dataset state
#       to a previous version by committing a new immutable snapshot (vNext).
#   16. GET /datasets/{dataset_id}/timeline: Retrieves a comprehensive chronological audit trail
#       of all ingestion, transformation, AI planning, and rollback operations.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Mounted directly into the main FastAPI app in 'backend/main.py' via app.include_router.
# - Enforces user authentication on all routes via 'get_current_user' in 'backend/core/auth.py'.
# - Reads environment parameters (such as SUPABASE_URL) from 'backend/core/config.py'.
# - Interacts with the Supabase database and storage client defined in 'backend/core/supabase_client.py'.
# - Raises structured domain exceptions defined in 'backend/core/exceptions.py'.
# - Validates payloads using Pydantic models from 'backend/models/schemas.py'.
# - Delegates parsing and version storage to 'backend/services/datasets.py' and deterministic
#   transformation operations to 'backend/services/transformations.py'.
# - Coordinates LLM-assisted operation planning through 'backend/services/ai/'.
# - Executes statistical calculations and chart data generation via 'backend/services/analysis/'.
# - Generates multi-format reports and binary exports via 'backend/services/reports/'.
# - Manages version lineage, diffing, rollbacks, and audit timelines via 'backend/services/history/'.
# ==============================================================================

