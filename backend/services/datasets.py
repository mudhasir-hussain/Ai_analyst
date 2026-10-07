import io
import os
import logging
import hashlib
from typing import Optional, Tuple, Dict, Any, List
import pandas as pd
import chardet
from fastapi import UploadFile
from core.exceptions import FileLimitError, DatasetValidationError, ParsingError, DatabaseStorageError
from core.config import settings
from core.supabase_client import supabase
from services.profiling import generate_extended_profile, evaluate_dataset_health

logger = logging.getLogger("ai_analyst_backend.services.datasets")

_DEV_DATAFRAME_CACHE: Dict[str, pd.DataFrame] = {}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_ROWS = 100000
MAX_COLUMNS = 50
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

def validate_file_size_and_type(file: UploadFile) -> str:
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected upload for file {filename}: unsupported extension {ext}")
        raise FileLimitError(
            detail=f"Unsupported file format '{ext}'. Only CSV and XLSX files are allowed.",
            error_code="UNSUPPORTED_FILE_TYPE"
        )
        
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE_BYTES:
        logger.warning(f"Rejected upload for file {filename}: header size {content_length} bytes exceeds 25MB")
        raise FileLimitError(
            detail="File size exceeds the maximum limit of 25MB.",
            error_code="FILE_TOO_LARGE"
        )
        
    return ext

def detect_encoding(file_content: bytes) -> str:
    try:
        sample = file_content[:50000]
        result = chardet.detect(sample)
        encoding = result.get("encoding") or "utf-8"
        confidence = result.get("confidence") or 0.0
        
        logger.info(f"Detected encoding: {encoding} with confidence {confidence:.2f}")
        
        if confidence < 0.5:
            return "utf-8"
        return encoding
    except Exception as e:
        logger.warning(f"Error detecting encoding: {e}. Defaulting to utf-8")
        return "utf-8"

def sanitize_and_uniquify_headers(columns: List[Any]) -> List[str]:
    sanitized_cols = []
    seen_names = {}
    
    for idx, col in enumerate(columns):
        col_str = str(col).strip() if pd.notna(col) else ""
        
        if not col_str:
            col_str = f"unnamed_col_{idx + 1}"
            
        if col_str in seen_names:
            seen_names[col_str] += 1
            col_str = f"{col_str}_{seen_names[col_str]}"
        else:
            seen_names[col_str] = 0
            
        sanitized_cols.append(col_str)
        
    return sanitized_cols

def infer_column_type(series: pd.Series) -> str:
    dtype = str(series.dtype)
    
    if "int" in dtype or "float" in dtype:
        if series.dropna().isin([0, 1]).all() and series.dropna().nunique() <= 2:
            return "boolean"
        return "numeric"
    elif "bool" in dtype:
        return "boolean"
    elif "datetime" in dtype or "date" in dtype:
        return "datetime"
    else:
        non_null = series.dropna()
        if not non_null.empty and non_null.nunique() > 1:
            try:
                sample_dates = pd.to_datetime(non_null.head(100), errors="coerce")
                if sample_dates.notna().sum() / len(sample_dates) > 0.8:
                    return "datetime"
            except Exception:
                pass
                
        unique_pct = series.nunique() / len(series) if len(series) > 0 else 1.0
        if unique_pct < 0.1 and series.nunique() < 50:
            return "categorical"
            
        return "text"

def generate_profile_and_schema(df: pd.DataFrame) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    profile_json = generate_extended_profile(df)
    health_json = evaluate_dataset_health(df, profile_json)
    profile_json["health"] = health_json

    schema_json = {col: stats["type"] for col, stats in profile_json["columns"].items()}
    return schema_json, profile_json

def parse_and_validate_dataset(
    file_content: bytes, 
    filename: str, 
    sheet_name: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE_BYTES:
        logger.warning(f"Rejected parse for {filename}: content size {file_size} exceeds 25MB limit")
        raise FileLimitError(
            detail=f"File exceeds maximum size constraint of 25MB (Current size: {file_size / (1024*1024):.2f}MB)",
            error_code="FILE_TOO_LARGE"
        )
        
    if file_size == 0:
        raise ParsingError(
            detail="The uploaded file is empty.",
            error_code="EMPTY_FILE"
        )

    _, ext = os.path.splitext(filename.lower())
    
    try:
        if ext == ".csv":
            encoding = detect_encoding(file_content)
            df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
            
        elif ext == ".xlsx":
            excel_file = pd.ExcelFile(io.BytesIO(file_content))
            sheet_names = excel_file.sheet_names
            
            if len(sheet_names) > 1 and not sheet_name:
                logger.info(f"Multiple sheets found in {filename}: {sheet_names}")
                raise ParsingError(
                    detail="Multiple sheets found. Please specify which sheet to load.",
                    error_code="MULTIPLE_SHEETS_FOUND"
                )
                
            selected_sheet = sheet_name or sheet_names[0]
            if selected_sheet not in sheet_names:
                raise ParsingError(
                    detail=f"Sheet '{selected_sheet}' not found in workbook. Available sheets: {sheet_names}",
                    error_code="SHEET_NOT_FOUND"
                )
                
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=selected_sheet)
            
        else:
            raise ParsingError(
                detail="Unsupported extension. Must be CSV or XLSX.",
                error_code="UNSUPPORTED_FORMAT"
            )
            
    except AppException as ae:
        raise ae
    except Exception as e:
        logger.error(f"Failed to parse {filename}: {e}")
        raise ParsingError(
            detail=f"Failed to parse tabular data: {str(e)}",
            error_code="PARSING_FAILED"
        )

    rows_count = len(df)
    cols_count = len(df.columns)
    
    logger.info(f"Successfully parsed dataset: {rows_count} rows, {cols_count} columns")
    
    if rows_count > MAX_ROWS:
        logger.warning(f"File {filename} exceeded row limit: {rows_count} rows")
        raise DatasetValidationError(
            detail=f"Dataset exceeds the limit of {MAX_ROWS} rows. Found {rows_count} rows.",
            error_code="ROW_LIMIT_EXCEEDED"
        )
        
    if cols_count > MAX_COLUMNS:
        logger.warning(f"File {filename} exceeded column limit: {cols_count} columns")
        raise DatasetValidationError(
            detail=f"Dataset exceeds the limit of {MAX_COLUMNS} columns. Found {cols_count} columns.",
            error_code="COLUMN_LIMIT_EXCEEDED"
        )

    df.columns = sanitize_and_uniquify_headers(df.columns)
    schema_json, profile_json = generate_profile_and_schema(df)
    
    return df, schema_json, profile_json

def upload_to_supabase_storage(
    file_content: bytes, 
    user_id: str, 
    project_id: str, 
    dataset_id: str, 
    filename: str
) -> str:
    _, ext = os.path.splitext(filename.lower())
    storage_path = f"originals/{user_id}/{project_id}/{dataset_id}/original{ext}"
    
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        logger.info(f"[Mock Mode] Skipping Supabase Storage upload. Path: {storage_path}")
        return f"mock_bucket/{storage_path}"
        
    try:
        logger.info(f"Uploading file to Supabase storage path: {storage_path}")
        response = supabase.storage.from_("datasets").upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": "application/octet-stream"}
        )
        
        if not response:
            raise DatabaseStorageError(
                detail="No response received from storage provider during upload.",
                error_code="STORAGE_UPLOAD_FAILED"
            )
            
        logger.info("Storage upload completed successfully.")
        return storage_path
        
    except Exception as e:
        logger.error(f"Supabase Storage upload error: {e}")
        raise DatabaseStorageError(
            detail=f"Failed to save file to cloud storage: {str(e)}",
            error_code="STORAGE_UPLOAD_ERROR"
        )

def cache_dev_dataframe(key: str, df: pd.DataFrame) -> None:
    _DEV_DATAFRAME_CACHE[key] = df.copy()

def get_dev_dataframe(key: str) -> Optional[pd.DataFrame]:
    return _DEV_DATAFRAME_CACHE.get(key)

def save_version_dataframe(
    df: pd.DataFrame,
    user_id: str,
    project_id: str,
    dataset_id: str,
    version_number: int
) -> Tuple[str, str, bytes]:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    checksum = hashlib.sha256(csv_bytes).hexdigest()
    storage_path = f"versions/{user_id}/{project_id}/{dataset_id}/v{version_number}.csv"

    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co":
        logger.info(f"[Mock Mode] Skipping Supabase Storage upload for version {version_number}. Path: {storage_path}")
        cache_dev_dataframe(f"{dataset_id}_v{version_number}", df)
        cache_dev_dataframe(str(dataset_id), df)
        return f"mock_bucket/{storage_path}", checksum, csv_bytes

    try:
        logger.info(f"Uploading version {version_number} snapshot to Supabase storage: {storage_path}")
        response = supabase.storage.from_("datasets").upload(
            path=storage_path,
            file=csv_bytes,
            file_options={"content-type": "text/csv"}
        )
        if not response:
            raise DatabaseStorageError("No response received from storage provider during version upload.", "STORAGE_UPLOAD_FAILED")
        return storage_path, checksum, csv_bytes
    except Exception as e:
        logger.error(f"Supabase Storage version upload error: {e}")
        raise DatabaseStorageError(f"Failed to save version to cloud storage: {str(e)}", "STORAGE_UPLOAD_ERROR")

def load_version_dataframe(storage_path: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    if settings.SUPABASE_URL == "https://your-supabase-project.supabase.co" or storage_path.startswith("mock_bucket/"):
        if dataset_id and dataset_id in _DEV_DATAFRAME_CACHE:
            return _DEV_DATAFRAME_CACHE[dataset_id].copy()
        for k, cached_df in _DEV_DATAFRAME_CACHE.items():
            if dataset_id and dataset_id in k:
                return cached_df.copy()
        return pd.DataFrame({
            "id": list(range(1, 101)),
            "category": ["Alpha" if i % 2 == 0 else "Beta" for i in range(1, 101)],
            "score": [float(i * 1.5) for i in range(1, 101)],
            "email": [f"user{i}@example.com" for i in range(1, 101)],
            "created_at": ["2026-01-01" for _ in range(100)]
        })

    try:
        logger.info(f"Downloading dataset version from Supabase storage: {storage_path}")
        data = supabase.storage.from_("datasets").download(storage_path)
        if not data:
            raise DatabaseStorageError("Empty response received when downloading version file.", "STORAGE_DOWNLOAD_FAILED")
        
        _, ext = os.path.splitext(storage_path.lower())
        if ext == ".parquet":
            return pd.read_parquet(io.BytesIO(data))
        elif ext == ".xlsx":
            return pd.read_excel(io.BytesIO(data))
        else:
            encoding = detect_encoding(data)
            return pd.read_csv(io.BytesIO(data), encoding=encoding)
    except Exception as e:
        logger.error(f"Supabase Storage download error: {e}")
        raise DatabaseStorageError(f"Failed to load version data from cloud storage: {str(e)}", "STORAGE_DOWNLOAD_ERROR")


# ==============================================================================
# FILE SUMMARY: backend/services/datasets.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file is the tabular data ingestion, parsing, and storage engine. It provides:
#   1. Strict limits and pre-flight validation ('validate_file_size_and_type'):
#      Restricts uploads to CSV and XLSX under 25MB.
#   2. Encoding detection ('detect_encoding'): Uses 'chardet' to sample the first 50KB
#      of CSV files and discover their character set before parsing.
#   3. Header normalization ('sanitize_and_uniquify_headers'): Strips whitespace, replaces
#      empty headers with 'unnamed_col_X', and appends sequential suffixes to duplicates.
#   4. Column type inference ('infer_column_type'): Converts raw pandas types into high-level
#      analytical categories: 'numeric', 'categorical', 'boolean', 'datetime', and 'text'.
#   5. Parsing and boundary validation ('parse_and_validate_dataset'): Parses memory bytes
#      into a pandas DataFrame, verifies the <=100,000 row and <=50 column caps, and triggers
#      profiling and health evaluation.
#   6. Cloud storage routers:
#      - 'upload_to_supabase_storage': Uploads raw original files to 'originals/...'.
#      - 'save_version_dataframe': Encodes transformed DataFrames to CSV, computes SHA-256
#        checksums, and stores immutable version snapshots in 'versions/...'.
#      - 'load_version_dataframe': Downloads and decodes Parquet, CSV, or XLSX files from
#        storage, with local in-memory fallback cache for development and testing.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked directly by 'backend/api/datasets.py' during upload and transformation flows.
# - Calls profiling functions 'generate_extended_profile' and 'evaluate_dataset_health' from
#   'backend/services/profiling.py' to produce dataset summaries.
# - Raises custom exceptions defined in 'backend/core/exceptions.py' ('FileLimitError',
#   'DatasetValidationError', 'ParsingError', 'DatabaseStorageError').
# - Reads environment settings from 'backend/core/config.py'.
# - Uses the Supabase client from 'backend/core/supabase_client.py' for storage operations.
# ==============================================================================
