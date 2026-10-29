import re
import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from pydantic import UUID4
from core.config import settings
from core.supabase_client import supabase
from core.exceptions import AIPlanError, ResourceNotFoundError, DatabaseStorageError
from models.schemas import (
    AIPlanResponse,
    TransformResponse,
    TransformImpactSummary,
    DatasetVersionResponse,
    OperationResponse
)
from services.transformations import ALLOWED_OPERATION_TYPES, execute_transformations
from services.datasets import (
    load_version_dataframe,
    save_version_dataframe,
    generate_profile_and_schema,
    cache_dev_dataframe
)
from services.ai.provider import get_llm_provider
from services.ai.prompts import (
    build_planning_system_prompt,
    build_dataset_context,
    build_planning_user_prompt
)

logger = logging.getLogger("ai_analyst_backend.services.ai.planner")

_DEV_AI_PLANS_CACHE: Dict[str, Dict[str, Any]] = {}


def extract_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Cleans and extracts JSON payload from LLM response text, stripping markdown code blocks.
    """
    cleaned = text.strip()

    # Strip code block wrappers
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # If extra text precedes or follows the JSON object, extract outer braces
    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        cleaned = brace_match.group(1).strip()

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise AIPlanError("LLM response did not contain a JSON object.", "INVALID_JSON_STRUCTURE")
        return data
    except json.JSONDecodeError as jde:
        logger.error(f"Failed to decode LLM JSON: {jde}. Raw text: {text[:200]}")
        raise AIPlanError(f"Model generated invalid JSON: {str(jde)}", "JSON_DECODE_FAILED")


def validate_plan_operations(operations: Any, df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Verifies that all operations in the plan are allowed, validly configured,
    and reference actual columns in the dataset.
    """
    warnings: List[str] = []
    if not isinstance(operations, list):
        return False, ["Plan operations must be a list."]
    if len(operations) == 0:
        return True, []

    current_cols = set(df.columns)

    for idx, op in enumerate(operations):
        if not isinstance(op, dict):
            return False, [f"Operation #{idx+1} is not a valid JSON object."]

        op_type = op.get("type")
        if not op_type or op_type not in ALLOWED_OPERATION_TYPES:
            return False, [f"Operation #{idx+1} has unsupported type '{op_type}'. Allowed types: {sorted(list(ALLOWED_OPERATION_TYPES))}"]

        # Validate column existence for operations acting on single column
        if "column" in op:
            c = op.get("column")
            if not c or c not in current_cols:
                return False, [f"Operation #{idx+1} ({op_type}) references non-existent column '{c}'."]

        # Validate column existence for operations acting on multiple columns
        if "columns" in op:
            cols = op.get("columns")
            if not isinstance(cols, list) or len(cols) == 0:
                return False, [f"Operation #{idx+1} ({op_type}) must supply a non-empty list of columns."]
            missing = [c for c in cols if c not in current_cols]
            if missing:
                return False, [f"Operation #{idx+1} ({op_type}) references non-existent columns: {missing}."]

        # Operation-specific parameter checks
        if op_type == "rename_column":
            new_name = op.get("new_name")
            if not new_name or not str(new_name).strip():
                return False, [f"Operation #{idx+1} (rename_column) missing required 'new_name'."]
            current_cols.remove(op["column"])
            current_cols.add(str(new_name).strip())

        elif op_type == "drop_columns":
            for c in op["columns"]:
                current_cols.discard(c)
            warnings.append(f"Operation #{idx+1} permanently drops columns: {op['columns']}.")

        elif op_type == "convert_type":
            target = op.get("target_type")
            valid_targets = {"numeric", "text", "datetime", "boolean", "categorical"}
            if target not in valid_targets:
                return False, [f"Operation #{idx+1} (convert_type) target_type '{target}' invalid. Allowed: {valid_targets}"]

        elif op_type == "fill_missing":
            strat = op.get("strategy", "constant")
            valid_strats = {"constant", "mean", "median", "mode"}
            if strat not in valid_strats:
                return False, [f"Operation #{idx+1} (fill_missing) strategy '{strat}' invalid. Allowed: {valid_strats}"]

        elif op_type == "handle_outliers":
            action = op.get("action", "clip")
            if action not in {"clip", "filter"}:
                return False, [f"Operation #{idx+1} (handle_outliers) action must be 'clip' or 'filter'."]
            warnings.append(f"Outlier adjustments on '{op.get('column')}' may modify or filter values.")

    return True, warnings


def generate_ai_plan(
    df: pd.DataFrame,
    user_prompt: str,
    dataset_id: UUID4,
    version_id: UUID4,
    user_id: UUID4,
    profile: Optional[Dict[str, Any]] = None,
    health: Optional[Dict[str, Any]] = None,
    provider_name: Optional[str] = None
) -> AIPlanResponse:
    """
    Coordinates plan formulation:
      1. Builds condensed context.
      2. Invokes LLM provider.
      3. Parses and validates returned operations.
      4. Executes safe pre-flight test on slice.
      5. Persists plan and returns AIPlanResponse.
    """
    logger.info(f"Generating AI plan for dataset {dataset_id} with prompt: '{user_prompt}'")
    system_prompt = build_planning_system_prompt()
    dataset_context = build_dataset_context(df, profile, health)
    full_user_prompt = build_planning_user_prompt(user_prompt, dataset_context)

    provider = get_llm_provider(provider_name)
    raw_response = provider.generate(system_prompt=system_prompt, user_prompt=full_user_prompt)

    try:
        plan_dict = extract_and_parse_json(raw_response)
    except AIPlanError as e:
        logger.warning(f"LLM generated unparseable or truncated JSON: {e}. Falling back to deterministic rule engine failsafe...")
        from services.ai.provider import MockLLMProvider
        fallback_raw = MockLLMProvider(model="deterministic-failsafe").generate(system_prompt=system_prompt, user_prompt=full_user_prompt)
        plan_dict = extract_and_parse_json(fallback_raw)

    operations = plan_dict.get("operations", [])
    model_warnings = plan_dict.get("warnings", [])
    if isinstance(model_warnings, list):
        warnings = [str(w) for w in model_warnings]
    else:
        warnings = []

    is_valid, validation_errors = validate_plan_operations(operations, df)

    if not is_valid:
        validation_status = "invalid"
        warnings.extend(validation_errors)
    elif len(operations) == 0:
        validation_status = "informational"
    else:
        # Pre-flight dry run on slice
        try:
            sample_slice = df.head(50).copy()
            execute_transformations(sample_slice, operations)
            validation_status = "validated"
        except Exception as e:
            logger.warning(f"Pre-flight plan dry run failed: {e}")
            validation_status = "invalid"
            warnings.append(f"Pre-flight execution check failed: {str(e)}")

    plan_id = uuid.uuid4()
    now = datetime.datetime.now(datetime.timezone.utc)
    provider_type = getattr(provider, "model", type(provider).__name__)

    plan_record = {
        "id": str(plan_id),
        "dataset_id": str(dataset_id),
        "version_id": str(version_id),
        "requested_by": str(user_id),
        "user_prompt": user_prompt,
        "provider": type(provider).__name__,
        "model": str(provider_type),
        "plan_json": plan_dict,
        "validation_status": validation_status,
        "warnings_json": warnings,
        "created_at": now.isoformat()
    }

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        _DEV_AI_PLANS_CACHE[str(plan_id)] = plan_record
    else:
        try:
            supabase.table("ai_plans").insert(plan_record).execute()
        except Exception as e:
            logger.warning(f"Could not persist plan to Supabase ai_plans table: {e}. Storing in memory.")
            _DEV_AI_PLANS_CACHE[str(plan_id)] = plan_record

    return AIPlanResponse(
        id=plan_id,
        plan_id=plan_id,
        dataset_id=dataset_id,
        version_id=version_id,
        requested_by=user_id,
        user_prompt=user_prompt,
        provider=type(provider).__name__,
        model=str(provider_type),
        summary=plan_dict.get("summary", "AI Cleaning and Transformation Plan"),
        operations=operations,
        warnings=warnings,
        plan_json=plan_dict,
        validation_status=validation_status,
        warnings_json=warnings,
        created_at=now
    )


def approve_and_execute_plan(
    dataset_id: UUID4,
    plan_id: UUID4,
    current_user_id: UUID4
) -> TransformResponse:
    """
    Approves and applies a previously validated AI plan, generating an immutable
    new DatasetVersion with source='ai'.
    """
    logger.info(f"User {current_user_id} approving AI plan {plan_id} for dataset {dataset_id}")

    # Fetch plan record
    plan_data = _DEV_AI_PLANS_CACHE.get(str(plan_id))
    if not plan_data:
        if settings.SUPABASE_URL != "https://your-supabase-project.supabase.co":
            res = supabase.table("ai_plans").select("*").eq("id", str(plan_id)).execute()
            if res.data:
                plan_data = res.data[0]

    if not plan_data:
        raise ResourceNotFoundError(f"AI Plan '{plan_id}' not found.", "PLAN_NOT_FOUND")

    if plan_data.get("validation_status") != "validated":
        raise AIPlanError(
            detail=f"Cannot approve plan with status '{plan_data.get('validation_status')}'. Only 'validated' plans can be executed.",
            error_code="PLAN_NOT_VALIDATED"
        )

    plan_json = plan_data.get("plan_json", {})
    operations = plan_json.get("operations", [])
    summary = plan_json.get("summary") or plan_data.get("user_prompt")

    # Load active version dataframe
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        from services.history.service import _ensure_dev_base_version, _DEV_VERSIONS_REGISTRY
        _ensure_dev_base_version(dataset_id)
        existing_versions = _DEV_VERSIONS_REGISTRY.get(str(dataset_id), [])
        if existing_versions:
            last_version = existing_versions[-1]
            source_version_id = UUID4(str(last_version["id"]))
            active_version_number = int(last_version.get("version_number", 1))
        else:
            source_version_id = uuid.uuid4()
            active_version_number = 1
        df = load_version_dataframe("mock_bucket/sample.csv", str(dataset_id))
    else:
        d_res = supabase.table("datasets").select("*").eq("id", str(dataset_id)).execute()
        if not d_res.data:
            raise ResourceNotFoundError(f"Dataset '{dataset_id}' not found.", "DATASET_NOT_FOUND")
        dataset = d_res.data[0]
        source_version_id = dataset.get("active_version_id")
        v_res = supabase.table("dataset_versions").select("*").eq("id", str(source_version_id)).execute()
        if not v_res.data:
            raise ResourceNotFoundError("Active version record not found.", "VERSION_NOT_FOUND")
        curr_version = v_res.data[0]
        active_version_number = curr_version.get("version_number", 1)
        df = load_version_dataframe(curr_version.get("storage_path", ""), str(dataset_id))

    transformed_df, impact_dict = execute_transformations(df, operations)

    new_version_id = uuid.uuid4()
    operation_id = uuid.uuid4()
    new_version_number = active_version_number + 1

    new_storage_path, checksum, _ = save_version_dataframe(
        df=transformed_df,
        user_id=str(current_user_id),
        project_id=str(dataset_id),
        dataset_id=str(dataset_id),
        version_number=new_version_number
    )

    schema_json, profile_json = generate_profile_and_schema(transformed_df)
    now = datetime.datetime.now(datetime.timezone.utc)

    new_version_row = {
        "id": str(new_version_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": str(source_version_id),
        "version_number": new_version_number,
        "storage_path": new_storage_path,
        "row_count": len(transformed_df),
        "column_count": len(transformed_df.columns),
        "schema_json": schema_json,
        "profile_json": profile_json,
        "checksum": checksum,
        "status": "active",
        "created_by": str(current_user_id)
    }

    operation_row = {
        "id": str(operation_id),
        "dataset_id": str(dataset_id),
        "source_version_id": str(source_version_id),
        "result_version_id": str(new_version_id),
        "initiated_by": str(current_user_id),
        "source": "ai",
        "operation_plan_json": plan_json,
        "summary": summary,
        "status": "success",
        "impact_json": impact_dict,
        "error_code": None
    }

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        cache_dev_dataframe(str(new_version_id), transformed_df)
        cache_dev_dataframe(str(dataset_id), transformed_df)
        cache_dev_dataframe(f"{dataset_id}_v{new_version_number}", transformed_df)
        from services.history import register_dev_version, register_dev_operation
        register_dev_version(str(dataset_id), {**new_version_row, "created_at": now.isoformat()})
        register_dev_operation(str(dataset_id), {**operation_row, "created_at": now.isoformat()})
    else:
        try:
            supabase.table("dataset_versions").insert(new_version_row).execute()
            supabase.table("datasets").update({"active_version_id": str(new_version_id)}).eq("id", str(dataset_id)).execute()
            supabase.table("operations").insert(operation_row).execute()
        except Exception as e:
            logger.error(f"Error persisting AI plan execution to Supabase: {e}")
            raise DatabaseStorageError(f"Failed to record approved AI version: {str(e)}", "STORAGE_ERROR")

    impact = TransformImpactSummary(**impact_dict)
    new_version = DatasetVersionResponse(**new_version_row, created_at=now)
    operation_record = OperationResponse(**operation_row, created_at=now, completed_at=now)

    return TransformResponse(
        dataset_id=dataset_id,
        source_version_id=UUID4(str(source_version_id)),
        result_version_id=new_version_id,
        version_number=new_version_number,
        impact=impact,
        new_version=new_version,
        operation=operation_record
    )


# ==============================================================================
# FILE SUMMARY: backend/services/ai/planner.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file coordinates the end-to-end AI Operation Planning workflow:
#   1. extract_and_parse_json(): Sanitizes LLM outputs, extracts enclosed JSON blocks,
#      and strips surrounding markdown code fences.
#   2. validate_plan_operations(): Validates the proposed operations against the 15 supported
#      deterministic cleaning operations and verifies all referenced columns exist in the DataFrame.
#   3. generate_ai_plan(): Coordinates prompt construction, LLM generation, operation validation,
#      and pre-flight dry run on a sample slice, returning a validated or rejected AIPlanResponse.
#   4. approve_and_execute_plan(): Executes an approved, validated AI plan on the active dataset version,
#      persists the new immutable version via save_version_dataframe, logs the audit record in the
#      operations table with source='ai', and returns a complete TransformResponse.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by API endpoints in 'backend/api/datasets.py' for plan generation and approval.
# - Uses 'get_llm_provider' from 'backend/services/ai/provider.py' for model inference.
# - Uses 'build_planning_system_prompt' and 'build_dataset_context' from 'backend/services/ai/prompts.py'.
# - Executes deterministic data modifications via 'execute_transformations' from 'backend/services/transformations.py'.
# - Saves versions and updates cache via 'services/datasets.py' and 'services/history/'.
# - Uses schemas from 'backend/models/schemas.py' ('AIPlanResponse', 'TransformResponse', 'TransformImpactSummary').
# ==============================================================================
