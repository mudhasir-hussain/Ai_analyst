import pytest
from fastapi.testclient import TestClient
from main import app
from core.rate_limit import limiter
from core.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Resets the rate limiter history before each test."""
    limiter.reset()
    yield
    limiter.reset()


def test_rate_limit_headers_present():
    """Verify that successful requests include X-RateLimit headers."""
    response = client.get("/projects", headers={"Authorization": "Bearer mock-token"})
    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert int(response.headers["x-ratelimit-remaining"]) < int(response.headers["x-ratelimit-limit"])


def test_health_check_exempt_from_rate_limiting():
    """Verify that system health check is exempt from rate limiting."""
    response = client.get("/health")
    assert response.status_code == 200
    # Exempt endpoints don't count towards rate limiting
    assert "x-ratelimit-limit" not in response.headers


def test_rate_limit_exceeded_returns_429():
    """Verify that exceeding limit triggers HTTP 429 Too Many Requests."""
    # Test client key with tight simulated limit
    test_client_id = "test-rapid-client"
    bucket = "general"
    limit = 5

    # Consume all allowed tokens
    for i in range(limit):
        allowed, remaining, _ = limiter.is_allowed(test_client_id, bucket, limit)
        assert allowed is True
        assert remaining == limit - (i + 1)

    # Next request must be rejected
    allowed, remaining, retry_after = limiter.is_allowed(test_client_id, bucket, limit)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


def test_middleware_blocks_when_rate_limit_exceeded(monkeypatch):
    """Verify middleware intercepts and returns JSON error when limit is breached."""
    # Temporarily set low limit
    monkeypatch.setattr(settings, "DEFAULT_RATE_LIMIT_PER_MINUTE", 3)
    headers = {"Authorization": "Bearer mock-token"}

    # 3 allowed requests
    for _ in range(3):
        r = client.get("/projects", headers=headers)
        assert r.status_code == 200

    # 4th request must be rejected with 429
    blocked_res = client.get("/projects", headers=headers)
    assert blocked_res.status_code == 429
    data = blocked_res.json()
    assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert "Rate limit exceeded" in data["detail"]
    assert "retry-after" in blocked_res.headers
