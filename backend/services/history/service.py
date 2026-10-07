import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from pydantic import UUID4
from core.config import settings
from core.supabase_client import supabase
from core.exceptions import ResourceNotFoundError, DatabaseStorageError
from models.schemas import (
    DatasetVersionResponse,
    VersionDiffResponse,
    RollbackResponse,
    TransformImpactSummary,
    AuditTimelineEvent,
    AuditTimelineResponse
)
from services.datasets import (
    save_version_dataframe,
    load_version_dataframe,
    cache_dev_dataframe,
    get_dev_dataframe,
    generate_profile_and_schema,
    infer_column_type
)
from services.history.diff import compute_dataframe_diff

logger = logging.getLogger("ai_analyst_backend.services.history.service")

# In-memory registries for local development and testing
_DEV_VERSIONS_REGISTRY: Dict[str, List[Dict[str, Any]]] = {}
_DEV_OPERATIONS_REGISTRY: Dict[str, List[Dict[str, Any]]] = {}


def register_dev_version(dataset_id: str, version_data: Dict[str, Any]) -> None:
    """
    Registers a new dataset version record in the development memory cache.
    """
    key = str(dataset_id)
    if key not in _DEV_VERSIONS_REGISTRY:
        _DEV_VERSIONS_REGISTRY[key] = []
    
    # Avoid duplicate version registrations
    for existing in _DEV_VERSIONS_REGISTRY[key]:
        if str(existing.get("id")) == str(version_data.get("id")):
            return
    _DEV_VERSIONS_REGISTRY[key].append(version_data)


def register_dev_operation(dataset_id: str, operation_data: Dict[str, Any]) -> None:
    """
    Registers an applied operation/audit record in the development memory cache.
    """
    key = str(dataset_id)
    if key not in _DEV_OPERATIONS_REGISTRY:
        _DEV_OPERATIONS_REGISTRY[key] = []
    
    for existing in _DEV_OPERATIONS_REGISTRY[key]:
        if str(existing.get("id")) == str(operation_data.get("id")):
            return
    _DEV_OPERATIONS_REGISTRY[key].append(operation_data)


def _ensure_dev_base_version(dataset_id: UUID4) -> Optional[Dict[str, Any]]:
    """
    Synthesizes and registers an initial Version 1 snapshot if a DataFrame exists in cache
    but no version records were explicitly registered.
    """
    key = str(dataset_id)
    df = get_dev_dataframe(key)
    if df is None:
        return None

    versions = _DEV_VERSIONS_REGISTRY.get(key, [])
    if versions:
        return versions[0]

    schema_json, profile_json = generate_profile_and_schema(df)
    v1_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    v1_record = {
        "id": str(v1_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": None,
        "version_number": 1,
        "storage_path": f"mock_bucket/versions/{dataset_id}/v1.csv",
        "row_count": len(df),
        "column_count": len(df.columns),
        "schema_json": schema_json,
        "profile_json": profile_json,
        "checksum": "mock_checksum_v1",
        "status": "active",
        "created_by": str(uuid.uuid4()),
        "created_at": now.isoformat()
    }
    register_dev_version(key, v1_record)
    cache_dev_dataframe(str(v1_id), df)
    cache_dev_dataframe(f"{key}_v1", df)

    # Register initial upload operation
    op_record = {
        "id": str(uuid.uuid4()),
        "dataset_id": str(dataset_id),
        "source_version_id": str(v1_id),
        "result_version_id": str(v1_id),
        "initiated_by": v1_record["created_by"],
        "source": "upload",
        "summary": "Initial dataset ingestion and validation",
        "operation_plan_json": {"action": "upload", "rows": len(df), "columns": len(df.columns)},
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
    }
    register_dev_operation(key, op_record)

    return v1_record


def list_dataset_versions(dataset_id: UUID4) -> List[DatasetVersionResponse]:
    """
    Returns all immutable versions for a dataset, ordered sequentially by version_number.
    """
    logger.info(f"Listing all versions for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        _ensure_dev_base_version(dataset_id)
        records = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if not records:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        records_sorted = sorted(records, key=lambda x: x.get("version_number", 1))
        return [DatasetVersionResponse(**r) for r in records_sorted]

    try:
        res = (
            supabase.table("dataset_versions")
            .select("*")
            .eq("dataset_id", str(dataset_id))
            .order("version_number", desc=False)
            .execute()
        )
        if not res.data:
            raise ResourceNotFoundError(f"Dataset with ID '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        return [DatasetVersionResponse(**r) for r in res.data]
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error fetching dataset versions from Supabase: {e}")
        raise DatabaseStorageError(f"Failed to query dataset versions: {str(e)}", "DATABASE_QUERY_ERROR")


def get_dataset_version(dataset_id: UUID4, version_id: UUID4) -> DatasetVersionResponse:
    """
    Retrieves a specific version record by dataset ID and version ID.
    """
    logger.info(f"Retrieving version {version_id} for dataset {dataset_id}")

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        _ensure_dev_base_version(dataset_id)
        versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        for v in versions:
            if str(v.get("id")) == str(version_id):
                return DatasetVersionResponse(**v)
        raise ResourceNotFoundError(f"Version with ID '{version_id}' not found.", "VERSION_NOT_FOUND")

    try:
        res = (
            supabase.table("dataset_versions")
            .select("*")
            .eq("dataset_id", str(dataset_id))
            .eq("id", str(version_id))
            .execute()
        )
        if not res.data:
            raise ResourceNotFoundError(f"Version with ID '{version_id}' not found.", "VERSION_NOT_FOUND")
        return DatasetVersionResponse(**res.data[0])
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dataset version: {e}")
        raise DatabaseStorageError(f"Failed to query dataset version: {str(e)}", "DATABASE_QUERY_ERROR")


def _load_df_for_version(dataset_id: UUID4, version: DatasetVersionResponse) -> pd.DataFrame:
    """
    Loads the underlying DataFrame for a given version snapshot.
    """
    # Check cache by version_id, version_number, or dataset_id
    cached = get_dev_dataframe(str(version.id))
    if cached is not None:
        return cached
    cached = get_dev_dataframe(f"{dataset_id}_v{version.version_number}")
    if cached is not None:
        return cached

    return load_version_dataframe(version.storage_path, str(dataset_id))


def diff_dataset_versions(
    dataset_id: UUID4,
    source_version_id: UUID4,
    target_version_id: Optional[UUID4] = None
) -> VersionDiffResponse:
    """
    Calculates a structured semantic diff between two version snapshots.
    If target_version_id is not specified, it defaults to the source's parent_version_id,
    or to Version 1 if no parent exists.
    """
    logger.info(f"Computing diff for dataset {dataset_id}: source={source_version_id}, target={target_version_id}")
    source_version = get_dataset_version(dataset_id, source_version_id)

    if target_version_id is None:
        base_version = None
        if source_version.parent_version_id:
            try:
                base_version = get_dataset_version(dataset_id, source_version.parent_version_id)
            except ResourceNotFoundError:
                pass
        if base_version is None:
            versions = list_dataset_versions(dataset_id)
            base_version = next(
                (v for v in versions if v.version_number == source_version.version_number - 1),
                versions[0] if versions else source_version
            )
        from_version = base_version
        to_version = source_version
    else:
        from_version = source_version
        to_version = get_dataset_version(dataset_id, target_version_id)

    source_df = _load_df_for_version(dataset_id, from_version)
    target_df = _load_df_for_version(dataset_id, to_version)

    return compute_dataframe_diff(
        source_df=source_df,
        target_df=target_df,
        source_version_id=from_version.id,
        source_version_number=from_version.version_number,
        target_version_id=to_version.id,
        target_version_number=to_version.version_number,
        dataset_id=dataset_id
    )


def rollback_dataset_version(
    dataset_id: UUID4,
    target_version_id: UUID4,
    current_user_id: UUID4,
    reason: Optional[str] = None
) -> RollbackResponse:
    """
    Restores the dataset state to a previous version snapshot.
    Creates a new immutable version (vNext) pointing back to the restored data,
    logs an operation audit entry with source='rollback', and updates the active version pointer.
    """
    logger.info(f"User {current_user_id} rolling back dataset {dataset_id} to version {target_version_id}")

    target_version = get_dataset_version(dataset_id, target_version_id)
    all_versions = list_dataset_versions(dataset_id)
    max_version_number = max((v.version_number for v in all_versions), default=1)
    new_version_number = max_version_number + 1

    # Load target snapshot data
    restored_df = _load_df_for_version(dataset_id, target_version)
    
    # Load current active data to calculate impact metrics
    current_active_version = all_versions[-1]
    current_df = _load_df_for_version(dataset_id, current_active_version)

    rows_before = len(current_df)
    rows_after = len(restored_df)
    columns_before = len(current_df.columns)
    columns_after = len(restored_df.columns)

    impact = TransformImpactSummary(
        rows_before=rows_before,
        rows_after=rows_after,
        columns_before=columns_before,
        columns_after=columns_after,
        rows_removed=max(0, rows_before - rows_after),
        columns_removed=max(0, columns_before - columns_after),
        cells_modified=abs(rows_after - rows_before) * columns_after,
        affected_columns=list(restored_df.columns),
        execution_time_ms=5.0
    )

    schema_json, profile_json = generate_profile_and_schema(restored_df)
    new_version_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Persist snapshot via save_version_dataframe
    storage_path, checksum, _ = save_version_dataframe(
        df=restored_df,
        user_id=str(current_user_id),
        project_id=str(dataset_id),
        dataset_id=str(dataset_id),
        version_number=new_version_number
    )

    new_version_record = {
        "id": str(new_version_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": str(current_active_version.id),
        "version_number": new_version_number,
        "storage_path": storage_path,
        "row_count": rows_after,
        "column_count": columns_after,
        "schema_json": schema_json,
        "profile_json": profile_json,
        "checksum": checksum,
        "status": "active",
        "created_by": str(current_user_id),
        "created_at": now.isoformat()
    }

    op_summary = (
        f"Rolled back dataset to state of Version {target_version.version_number}. "
        f"{reason or ''}".strip()
    )

    operation_record = {
        "id": str(uuid.uuid4()),
        "dataset_id": str(dataset_id),
        "source_version_id": str(current_active_version.id),
        "result_version_id": str(new_version_id),
        "initiated_by": str(current_user_id),
        "source": "rollback",
        "operation_plan_json": {
            "action": "rollback",
            "restored_from_version_id": str(target_version_id),
            "restored_from_version_number": target_version.version_number,
            "reason": reason
        },
        "summary": op_summary,
        "impact_json": impact.model_dump(),
        "status": "success",
        "created_at": now.isoformat()
    }

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        register_dev_version(str(dataset_id), new_version_record)
        register_dev_operation(str(dataset_id), operation_record)
        cache_dev_dataframe(str(dataset_id), restored_df)
        cache_dev_dataframe(str(new_version_id), restored_df)
        cache_dev_dataframe(f"{dataset_id}_v{new_version_number}", restored_df)
    else:
        try:
            supabase.table("dataset_versions").insert(new_version_record).execute()
            supabase.table("operations").insert(operation_record).execute()
            supabase.table("datasets").update({"active_version_id": str(new_version_id)}).eq("id", str(dataset_id)).execute()
        except Exception as e:
            logger.error(f"Failed to record rollback in Supabase: {e}")
            raise DatabaseStorageError(f"Failed to execute database rollback: {str(e)}", "ROLLBACK_STORAGE_ERROR")

    new_version_response = DatasetVersionResponse(**new_version_record)

    return RollbackResponse(
        dataset_id=dataset_id,
        restored_from_version_id=target_version_id,
        restored_from_version_number=target_version.version_number,
        new_version=new_version_response,
        impact=impact,
        message=f"Successfully restored dataset to Version {target_version.version_number} as new active Version {new_version_number}."
    )


def get_audit_timeline(dataset_id: UUID4) -> AuditTimelineResponse:
    """
    Compiles a complete chronological audit history of all versions, transformations,
    AI plans, and rollbacks for a dataset.
    """
    logger.info(f"Retrieving audit timeline for dataset {dataset_id}")
    all_versions = list_dataset_versions(dataset_id)
    version_map = {str(v.id): v for v in all_versions}

    operations: List[Dict[str, Any]] = []
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        operations = _DEV_OPERATIONS_REGISTRY.get(str(dataset_id), [])
    else:
        try:
            res = (
                supabase.table("operations")
                .select("*")
                .eq("dataset_id", str(dataset_id))
                .order("created_at", desc=False)
                .execute()
            )
            operations = res.data or []
        except Exception as e:
            logger.warning(f"Could not fetch operations for dataset {dataset_id}: {e}")
            operations = []

    events: List[AuditTimelineEvent] = []

    # Map operations into timeline events
    for op in operations:
        res_v_id = op.get("result_version_id") or op.get("source_version_id")
        v_obj = version_map.get(str(res_v_id))
        v_num = v_obj.version_number if v_obj else None

        created_at = op.get("created_at")
        if isinstance(created_at, str):
            dt = datetime.datetime.fromisoformat(created_at)
        elif isinstance(created_at, datetime.datetime):
            dt = created_at
        else:
            dt = datetime.datetime.now(datetime.timezone.utc)

        source = op.get("source", "system")
        if source == "upload":
            event_type = "upload"
        elif source == "rollback":
            event_type = "rollback"
        elif source == "ai":
            event_type = "ai_plan"
        else:
            event_type = "transformation"

        events.append(
            AuditTimelineEvent(
                id=UUID4(str(op.get("id", uuid.uuid4()))),
                event_type=event_type,
                source=source,
                timestamp=dt,
                version_id=UUID4(str(res_v_id)) if res_v_id else None,
                version_number=v_num,
                summary=op.get("summary", "Dataset operation performed."),
                user_id=UUID4(str(op.get("initiated_by", uuid.uuid4()))),
                impact=op.get("impact_json"),
                metadata=op.get("operation_plan_json") or {}
            )
        )

    # If no operations were recorded, populate from versions list
    if not events and all_versions:
        for v in all_versions:
            event_type = "upload" if v.version_number == 1 else "transformation"
            events.append(
                AuditTimelineEvent(
                    id=uuid.uuid4(),
                    event_type=event_type,
                    source="system" if v.version_number == 1 else "manual",
                    timestamp=v.created_at,
                    version_id=v.id,
                    version_number=v.version_number,
                    summary=f"Created Version {v.version_number} ({v.row_count} rows, {v.column_count} cols).",
                    user_id=v.created_by,
                    impact=None,
                    metadata={"status": v.status, "checksum": v.checksum}
                )
            )

    events_sorted = sorted(events, key=lambda e: e.timestamp)

    return AuditTimelineResponse(
        dataset_id=dataset_id,
        total_events=len(events_sorted),
        events=events_sorted
    )


# ==============================================================================
# FILE SUMMARY: backend/services/history/service.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the Version Management, Lineage, Rollback, and Audit Service:
#   1. list_dataset_versions(): Retrieves all immutable snapshots for a dataset
#      ordered chronologically by version number.
#   2. get_dataset_version(): Fetches a single version by dataset ID and version ID.
#   3. diff_dataset_versions(): Evaluates differences between two snapshot versions
#      or between a version and its immediate parent.
#   4. rollback_dataset_version(): Reverts a dataset to a previous state by creating
#      a new immutable version snapshot (vNext), ensuring complete reversibility
#      without destructively modifying historical records.
#   5. get_audit_timeline(): Compiles a unified chronological audit trail of all uploads,
#      manual transformations, AI plans, and rollbacks.
#   6. Development registries ('_DEV_VERSIONS_REGISTRY', '_DEV_OPERATIONS_REGISTRY'):
#      Provides local dev memory persistence when Supabase credentials are in mock mode.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by version management routes in 'backend/api/datasets.py'.
# - Uses 'compute_dataframe_diff' from 'backend/services/history/diff.py'.
# - Leverages 'save_version_dataframe' and 'load_version_dataframe' from 'backend/services/datasets.py'.
# - Interacts with Supabase tables ('dataset_versions', 'operations', 'datasets') via 'core/supabase_client.py'.
# - Returns Pydantic models from 'backend/models/schemas.py' ('DatasetVersionResponse',
#   'VersionDiffResponse', 'RollbackResponse', 'AuditTimelineResponse').
# ==============================================================================
