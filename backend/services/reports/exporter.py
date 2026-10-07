import io
import logging
from typing import Tuple
import pandas as pd
from core.exceptions import DatasetValidationError

logger = logging.getLogger("ai_analyst_backend.services.reports.exporter")


def export_dataset(df: pd.DataFrame, format: str = "csv", filename_prefix: str = "dataset") -> Tuple[bytes, str, str]:
    """
    Serializes a DataFrame into downloadable CSV or Excel (XLSX) bytes with appropriate MIME type.
    """
    clean_fmt = format.lower().strip()

    if clean_fmt == "csv":
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        media_type = "text/csv"
        filename = f"{filename_prefix}_export.csv"
        return csv_bytes, media_type, filename

    elif clean_fmt in {"xlsx", "excel"}:
        buf = io.BytesIO()
        try:
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Data")
            buf.seek(0)
            excel_bytes = buf.getvalue()
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"{filename_prefix}_export.xlsx"
            return excel_bytes, media_type, filename
        except Exception as e:
            logger.error(f"Error serializing Excel export: {e}")
            raise DatasetValidationError(f"Failed to generate Excel export: {str(e)}", "EXPORT_FAILED")

    else:
        raise DatasetValidationError(
            detail=f"Unsupported export format '{format}'. Allowed formats: ['csv', 'xlsx'].",
            error_code="UNSUPPORTED_EXPORT_FORMAT"
        )


# ==============================================================================
# FILE SUMMARY: backend/services/reports/exporter.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file provides the dataset file export service:
#   1. export_dataset(): Encodes a pandas DataFrame into raw bytes for CSV or XLSX downloads,
#      returning the byte stream, corresponding HTTP Content-Type, and safe suggested filename.
#   2. Enforces defensive format checks and catches OpenPyXL serialization exceptions.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by POST /datasets/{dataset_id}/export in 'backend/api/datasets.py'.
# - Leverages 'DatasetValidationError' from 'backend/core/exceptions.py'.
# ==============================================================================
