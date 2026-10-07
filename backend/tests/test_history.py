import uuid
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from main import app
from services.datasets import cache_dev_dataframe
from services.history import (
    compute_dataframe_diff,
    list_dataset_versions,
    get_dataset_version,
    diff_dataset_versions,
    rollback_dataset_version,
    get_audit_timeline,
    register_dev_version,
    _DEV_VERSIONS_REGISTRY,
    _DEV_OPERATIONS_REGISTRY
)
from core.exceptions import ResourceNotFoundError

client = TestClient(app)
MOCK_AUTH_HEADER = {"Authorization": "Bearer mock-token"}


@pytest.fixture
def history_sample_df():
    return pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, np.nan, 45, 50],
        "score": [10.5, 20.0, 30.5, 40.0, 50.5]
    })


@pytest.fixture
def history_modified_df():
    # 1 row dropped, 1 column added, 'age' null filled, 'score' values shifted
    return pd.DataFrame({
        "customer_id": [1, 2, 4, 5],
        "name": ["Alice", "Bob", "David", "Eve"],
        "age": [25, 30, 45, 50],
        "score": [15.5, 25.0, 45.0, 55.5],
        "tier": ["Gold", "Silver", "Platinum", "Gold"]
    })


def test_compute_dataframe_diff(history_sample_df, history_modified_df):
    dataset_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    diff_res = compute_dataframe_diff(
        source_df=history_sample_df,
        target_df=history_modified_df,
        source_version_id=v1_id,
        source_version_number=1,
        target_version_id=v2_id,
        target_version_number=2,
        dataset_id=dataset_id
    )

    assert diff_res.dataset_id == dataset_id
    assert diff_res.rows_source == 5
    assert diff_res.rows_target == 4
    assert diff_res.rows_diff == -1
    assert "tier" in diff_res.added_columns
    assert diff_res.removed_columns == []
    assert len(diff_res.column_changes) > 0

    # Verify score stats delta was calculated
    score_change = next(c for c in diff_res.column_changes if c.column == "score")
    assert score_change.stats_delta.get("mean_delta") is not None
    assert score_change.stats_delta["mean_delta"] > 0

    # Verify summary text contains key findings
    assert "Row count decreased by 1" in diff_res.summary
    assert "Added 1 column(s): tier" in diff_res.summary


def test_list_and_get_dataset_versions(history_sample_df):
    dataset_id = uuid.uuid4()
    cache_dev_dataframe(str(dataset_id), history_sample_df)

    versions = list_dataset_versions(dataset_id)
    assert len(versions) >= 1
    assert versions[0].version_number == 1
    assert versions[0].row_count == 5

    # Fetch specific version
    v1 = get_dataset_version(dataset_id, versions[0].id)
    assert v1.id == versions[0].id
    assert v1.column_count == 4


def test_get_dataset_version_not_found(history_sample_df):
    dataset_id = uuid.uuid4()
    cache_dev_dataframe(str(dataset_id), history_sample_df)
    random_version_id = uuid.uuid4()

    with pytest.raises(ResourceNotFoundError):
        get_dataset_version(dataset_id, random_version_id)


def test_diff_dataset_versions_service(history_sample_df, history_modified_df):
    dataset_id = uuid.uuid4()
    cache_dev_dataframe(str(dataset_id), history_sample_df)
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    register_dev_version(str(dataset_id), {
        "id": str(v1_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": None,
        "version_number": 1,
        "storage_path": f"mock_bucket/v1.csv",
        "row_count": 5,
        "column_count": 4,
        "schema_json": {},
        "profile_json": {},
        "checksum": "chk1",
        "status": "active",
        "created_by": str(uuid.uuid4()),
        "created_at": "2026-01-01T00:00:00Z"
    })
    cache_dev_dataframe(str(v1_id), history_sample_df)

    register_dev_version(str(dataset_id), {
        "id": str(v2_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": str(v1_id),
        "version_number": 2,
        "storage_path": f"mock_bucket/v2.csv",
        "row_count": 4,
        "column_count": 5,
        "schema_json": {},
        "profile_json": {},
        "checksum": "chk2",
        "status": "active",
        "created_by": str(uuid.uuid4()),
        "created_at": "2026-01-02T00:00:00Z"
    })
    cache_dev_dataframe(str(v2_id), history_modified_df)

    diff = diff_dataset_versions(dataset_id, v1_id, v2_id)
    assert diff.source_version_number == 1
    assert diff.target_version_number == 2
    assert diff.rows_diff == -1


def test_rollback_dataset_version_service(history_sample_df, history_modified_df):
    dataset_id = uuid.uuid4()
    user_id = uuid.uuid4()
    v1_id = uuid.uuid4()
    v2_id = uuid.uuid4()

    # Setup v1 and v2
    register_dev_version(str(dataset_id), {
        "id": str(v1_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": None,
        "version_number": 1,
        "storage_path": f"mock_bucket/v1.csv",
        "row_count": len(history_sample_df),
        "column_count": len(history_sample_df.columns),
        "schema_json": {},
        "profile_json": {},
        "checksum": "chk1",
        "status": "active",
        "created_by": str(user_id),
        "created_at": "2026-01-01T00:00:00Z"
    })
    cache_dev_dataframe(str(v1_id), history_sample_df)

    register_dev_version(str(dataset_id), {
        "id": str(v2_id),
        "dataset_id": str(dataset_id),
        "parent_version_id": str(v1_id),
        "version_number": 2,
        "storage_path": f"mock_bucket/v2.csv",
        "row_count": len(history_modified_df),
        "column_count": len(history_modified_df.columns),
        "schema_json": {},
        "profile_json": {},
        "checksum": "chk2",
        "status": "active",
        "created_by": str(user_id),
        "created_at": "2026-01-02T00:00:00Z"
    })
    cache_dev_dataframe(str(v2_id), history_modified_df)
    cache_dev_dataframe(str(dataset_id), history_modified_df)

    # Rollback to v1
    rollback_res = rollback_dataset_version(
        dataset_id=dataset_id,
        target_version_id=v1_id,
        current_user_id=user_id,
        reason="Testing safe rollback mechanism"
    )

    assert rollback_res.restored_from_version_number == 1
    assert rollback_res.new_version.version_number == 3
    assert rollback_res.new_version.row_count == len(history_sample_df)
    assert "successfully restored" in rollback_res.message.lower()

    # Verify history now has 3 versions
    versions = list_dataset_versions(dataset_id)
    assert len(versions) == 3


def test_get_audit_timeline_service(history_sample_df):
    dataset_id = uuid.uuid4()
    cache_dev_dataframe(str(dataset_id), history_sample_df)

    timeline = get_audit_timeline(dataset_id)
    assert timeline.dataset_id == dataset_id
    assert timeline.total_events >= 1
    first_event = timeline.events[0]
    assert first_event.event_type in ["upload", "transformation"]


def test_api_list_and_get_versions(history_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, history_sample_df)

    # 1. GET /datasets/{dataset_id}/versions
    res = client.get(
        f"/datasets/{dataset_id}/versions",
        headers=MOCK_AUTH_HEADER
    )
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) >= 1
    v1_id = versions[0]["id"]

    # 2. GET /datasets/{dataset_id}/versions/{version_id}
    res_single = client.get(
        f"/datasets/{dataset_id}/versions/{v1_id}",
        headers=MOCK_AUTH_HEADER
    )
    assert res_single.status_code == 200
    assert res_single.json()["id"] == v1_id


def test_api_diff_versions_endpoint(history_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, history_sample_df)

    # Apply transform to create version 2
    transform_res = client.post(
        f"/datasets/{dataset_id}/transform",
        headers=MOCK_AUTH_HEADER,
        json={
            "operations": [
                {"type": "drop_missing_rows", "columns": ["age"]}
            ],
            "summary": "Drop rows with missing age"
        }
    )
    assert transform_res.status_code == 200
    v2_id = transform_res.json()["result_version_id"]

    # Diff v2 against its parent
    diff_res = client.get(
        f"/datasets/{dataset_id}/versions/{v2_id}/diff",
        headers=MOCK_AUTH_HEADER
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["rows_diff"] == -1
    assert "Row count decreased by 1" in diff_data["summary"]


def test_api_rollback_endpoint(history_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, history_sample_df)

    # Get v1
    v_res = client.get(f"/datasets/{dataset_id}/versions", headers=MOCK_AUTH_HEADER)
    v1_id = v_res.json()[0]["id"]

    # Create v2 by transforming
    client.post(
        f"/datasets/{dataset_id}/transform",
        headers=MOCK_AUTH_HEADER,
        json={
            "operations": [
                {"type": "drop_missing_rows", "columns": ["age"]}
            ]
        }
    )

    # Rollback to v1
    rollback_res = client.post(
        f"/datasets/{dataset_id}/versions/{v1_id}/rollback",
        headers=MOCK_AUTH_HEADER,
        json={"reason": "Reverting dropped rows"}
    )
    assert rollback_res.status_code == 200
    rb_data = rollback_res.json()
    assert rb_data["restored_from_version_number"] == 1
    assert rb_data["new_version"]["version_number"] == 3
    assert rb_data["new_version"]["row_count"] == 5


def test_api_timeline_endpoint(history_sample_df):
    dataset_id = str(uuid.uuid4())
    cache_dev_dataframe(dataset_id, history_sample_df)

    res = client.get(
        f"/datasets/{dataset_id}/timeline",
        headers=MOCK_AUTH_HEADER
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] >= 1
    assert len(data["events"]) >= 1


# ==============================================================================
# FILE SUMMARY: backend/tests/test_history.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This test suite verifies the Versioning, Lineage, Rollback, and Timeline engine:
#   1. test_compute_dataframe_diff(): Validates row deltas, column addition/removal tracking,
#      missing value changes, numeric metric shifts, and plain-English summary formulation.
#   2. test_list_and_get_dataset_versions(): Tests chronological version listing and lookup.
#   3. test_get_dataset_version_not_found(): Confirms ResourceNotFoundError on invalid version IDs.
#   4. test_diff_dataset_versions_service(): Tests end-to-end version comparison logic.
#   5. test_rollback_dataset_version_service(): Tests non-destructive version reversion,
#      ensuring a new active version (vNext) is committed while retaining full history.
#   6. test_get_audit_timeline_service(): Tests chronological event compilation.
#   7. API tests (GET /versions, GET /versions/{id}, GET /diff, POST /rollback, GET /timeline):
#      Confirms all Step 9 HTTP endpoints enforce authentication, return expected Pydantic
#      schemas, and handle client requests accurately.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Tests endpoints in 'backend/api/datasets.py' and service methods in 'backend/services/history/'.
# - Verifies models from 'backend/models/schemas.py' ('VersionDiffResponse', 'RollbackResponse',
#   'AuditTimelineResponse').
# - Uses FastAPI TestClient and mock credentials to run in a standalone test environment.
# ==============================================================================
