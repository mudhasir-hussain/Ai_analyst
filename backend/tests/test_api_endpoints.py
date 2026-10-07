import pytest
import uuid
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_dataset_profile_endpoint():
    headers = {"Authorization": "Bearer mock-token"}
    dataset_id = str(uuid.uuid4())
    response = client.get(f"/datasets/{dataset_id}/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == dataset_id
    assert "profile" in data
    assert "columns" in data["profile"]

def test_get_dataset_health_endpoint():
    headers = {"Authorization": "Bearer mock-token"}
    dataset_id = str(uuid.uuid4())
    response = client.get(f"/datasets/{dataset_id}/health", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == dataset_id
    assert "health_score" in data
    assert "rating" in data
    assert "issues" in data


# ==============================================================================
# FILE SUMMARY: backend/tests/test_api_endpoints.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides automated integration tests using FastAPI's 'TestClient':
#   1. 'test_health_check_endpoint': Asserts the '/health' endpoint returns HTTP 200
#      with a status of 'healthy'.
#   2. 'test_get_dataset_profile_endpoint': Uses the development 'mock-token' bearer
#      auth to query 'GET /datasets/{dataset_id}/profile' and validates that the
#      statistical profile and columns dictionary are returned.
#   3. 'test_get_dataset_health_endpoint': Verifies 'GET /datasets/{dataset_id}/health'
#      returns HTTP 200, containing the health score, rating, and quality issues list.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports 'app' from 'backend/main.py' to run against the live FastAPI instance.
# - Tests endpoints defined in 'backend/api/datasets.py' and 'backend/main.py'.
# - Verifies that authentication via 'backend/core/auth.py' properly accepts 'mock-token'
#   in the development environment.
# ==============================================================================
