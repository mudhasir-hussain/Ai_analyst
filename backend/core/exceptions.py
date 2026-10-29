from fastapi import status

class AppException(Exception):
    def __init__(self, detail: str, error_code: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(detail)
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code


class FileLimitError(AppException):
    def __init__(self, detail: str, error_code: str = "FILE_LIMIT_EXCEEDED"):
        super().__init__(detail, error_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)


class DatasetValidationError(AppException):
    def __init__(self, detail: str, error_code: str = "DATASET_VALIDATION_FAILED"):
        super().__init__(detail, error_code, 422)


class ParsingError(AppException):
    def __init__(self, detail: str, error_code: str = "PARSING_FAILED"):
        super().__init__(detail, error_code, status.HTTP_400_BAD_REQUEST)


class DatabaseStorageError(AppException):
    def __init__(self, detail: str, error_code: str = "STORAGE_ERROR"):
        super().__init__(detail, error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResourceNotFoundError(AppException):
    def __init__(self, detail: str, error_code: str = "RESOURCE_NOT_FOUND"):
        super().__init__(detail, error_code, status.HTTP_404_NOT_FOUND)


class LLMProviderError(AppException):
    def __init__(self, detail: str, error_code: str = "LLM_PROVIDER_ERROR"):
        super().__init__(detail, error_code, status.HTTP_502_BAD_GATEWAY)


class AIPlanError(AppException):
    def __init__(self, detail: str, error_code: str = "AI_PLAN_ERROR"):
        super().__init__(detail, error_code, 422)


class MLValidationError(DatasetValidationError):
    def __init__(self, detail: str, error_code: str = "ML_VALIDATION_ERROR"):
        super().__init__(detail, error_code)


class RateLimitExceededError(AppException):
    def __init__(self, detail: str = "Rate limit exceeded. Too many requests.", error_code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(detail, error_code, status.HTTP_429_TOO_MANY_REQUESTS)


ValidationError = DatasetValidationError


# ==============================================================================
# FILE SUMMARY: backend/core/exceptions.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file establishes the application's domain exception hierarchy rooted at
# 'AppException'. Every custom error carries an HTTP status code, a descriptive
# human-readable message ('detail'), and a machine-readable error token ('error_code'):
#   - FileLimitError (HTTP 413): File exceeds the 25MB constraint or has an invalid type.
#   - DatasetValidationError (HTTP 422): Data violates limits or transformation checks.
#   - ParsingError (HTTP 400): Malformed CSV/XLSX, ambiguous sheets, or bad encodings.
#   - DatabaseStorageError (HTTP 500): Failures writing to Supabase storage or tables.
#   - ResourceNotFoundError (HTTP 404): Requested entity (dataset, version, plan) does not exist.
#   - LLMProviderError (HTTP 502): External or local LLM connection/timeout failures.
#   - AIPlanError (HTTP 422): Inability to formulate, validate, or approve an AI operation plan.
#
# HOW IT CONNECTS TO OTHER FILES:
# - 'backend/main.py' registers a global exception handler for 'AppException' to intercept
#   these errors and render standardized JSON responses without crashing or leaking traces.
# - 'backend/services/datasets.py' raises 'FileLimitError', 'ParsingError', and
#   'DatasetValidationError' when enforcing ingestion rules.
# - 'backend/services/transformations.py' raises 'DatasetValidationError' during data cleaning.
# - 'backend/services/ai/' raises 'LLMProviderError' and 'AIPlanError' during plan generation/execution.
# - 'backend/api/datasets.py' raises 'ParsingError', 'DatabaseStorageError', and
#   'ResourceNotFoundError' during route execution and database lookups.
# ==============================================================================
