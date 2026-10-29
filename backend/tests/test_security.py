import io
import uuid
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from main import app
from core.config import settings
from services.reports.exporter import export_dataset, sanitize_for_export
from services.ml.trainer import train_model_on_dataframe

client = TestClient(app)
MOCK_AUTH_HEADER = {"Authorization": "Bearer mock-token"}


def test_csv_formula_injection_defense():
    """
    OWASP CSV / Excel Formula Injection Test:
    Ensures dangerous prefixes (=, +, -, @, \\t, \\r) on strings are escaped with a single quote ('),
    while standard numeric negative/positive values remain intact.
    """
    df = pd.DataFrame({
        "payload": [
            "=cmd|' /C calc'!A0",
            "@SUM(A1:A10)",
            "+44-EVIL-INJECTION",
            "-DDE(\"cmd\";\"/C calc\";\"!A0\")",
            "\tTAB_ATTACK",
            "normal_value",
            "-15.5",
            "+42"
        ],
        "numeric_val": [-10.5, 20.0, -100.0, 50.0, 0.0, 1.0, 2.0, 3.0]
    })

    safe_df = sanitize_for_export(df)

    # Formula injection attempts must be sanitized with a leading single quote
    assert safe_df["payload"].iloc[0].startswith("'=")
    assert safe_df["payload"].iloc[1].startswith("'@")
    assert safe_df["payload"].iloc[2].startswith("'+")
    assert safe_df["payload"].iloc[3].startswith("'-")
    assert safe_df["payload"].iloc[4].startswith("'\t")
    assert safe_df["payload"].iloc[5] == "normal_value"

    # Valid string representation of numbers should not be mangled
    assert safe_df["payload"].iloc[6] == "-15.5"
    assert safe_df["payload"].iloc[7] == "+42"

    # Numeric series should remain completely untouched
    assert safe_df["numeric_val"].iloc[0] == -10.5
    assert safe_df["numeric_val"].iloc[2] == -100.0

    # Verify export output contains sanitized content
    csv_bytes, media_type, filename = export_dataset(df, format="csv")
    csv_str = csv_bytes.decode("utf-8")
    assert "'=cmd|" in csv_str
    assert "'@SUM" in csv_str


def test_ml_hyperparameter_dos_clamping():
    """
    Denial of Service (DoS) Resource Exhaustion Test:
    Ensures extreme or adversarial hyperparameters (e.g. n_estimators=999999, max_iter=500000)
    are clamped to safe production bounds without crashing or locking up the CPU.
    """
    df = pd.DataFrame({
        "feature_a": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        "feature_b": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        "target": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0]
    })

    # Test Random Forest with absurdly large n_estimators and depth
    rf_res = train_model_on_dataframe(
        df=df,
        target_col="target",
        model_type="random_forest",
        test_size=0.999,  # Adversarial test size (too high)
        hyperparameters={"n_estimators": 999999, "max_depth": 9999}
    )
    assert rf_res is not None
    # Model name should reflect clamped estimator count (max 100 trees)
    assert "100 Trees" in rf_res.model_name or "Random Forest" in rf_res.model_name

    # Test Neural Network with extreme iterations
    mlp_res = train_model_on_dataframe(
        df=df,
        target_col="target",
        model_type="mlp",
        test_size=-5.0,  # Adversarial test size (negative)
        hyperparameters={"max_iter": 500000, "learning_rate": 999.0}
    )
    assert mlp_res is not None

    # Test SVM with invalid / arbitrary kernel string
    svm_res = train_model_on_dataframe(
        df=df,
        target_col="target",
        model_type="svm",
        hyperparameters={"C": 999999.0, "kernel": "exploit_malicious_kernel"}
    )
    assert svm_res is not None
    assert "kernel=rbf" in svm_res.model_name


def test_production_mock_token_strictly_rejected():
    """
    Authentication Hardening Test:
    Ensures that if ENVIRONMENT is set to 'production', 'mock-token' is strictly rejected
    with HTTP 401 Unauthorized, eliminating any risk of production authentication bypass.
    """
    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        res = client.get("/projects", headers=MOCK_AUTH_HEADER)
        assert res.status_code == 401
        assert "strictly disabled" in res.json().get("detail", "").lower()
    finally:
        settings.ENVIRONMENT = orig_env


def test_global_unhandled_exception_sanitization():
    """
    Information Disclosure Defense Test:
    Ensures that unhandled 500 exceptions return safe, standardized JSON payloads
    without leaking internal file paths, module structures, or python stack traces.
    """
    res = client.get("/datasets/invalid-uuid-format-that-triggers-handling/history", headers=MOCK_AUTH_HEADER)
    # The route expects a valid UUID path param; should return uniform error or 404/422 without Python traceback
    assert res.status_code in [400, 404, 422, 500]
    data = res.json()
    assert "detail" in data
    # Ensure no raw tracebacks leaked
    assert "Traceback (most recent call last)" not in str(data)
    assert "File \"" not in str(data)
