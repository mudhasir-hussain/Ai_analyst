import json
import logging
from typing import Optional, Dict, Any, List
import pandas as pd
from services.transformations import ALLOWED_OPERATION_TYPES

logger = logging.getLogger("ai_analyst_backend.services.ai.prompts")


def build_planning_system_prompt() -> str:
    """
    Constructs the system prompt instructing the LLM to output structured
    cleaning and transformation plans strictly adhering to allowed operations.
    """
    allowed_list_str = ", ".join(sorted(list(ALLOWED_OPERATION_TYPES)))
    return f"""You are an expert Data Analyst AI planning assistant.
Your job is to translate the user's natural language request into a safe, deterministic data transformation plan.

CRITICAL CONSTRAINTS:
1. You MUST NEVER generate raw Python code, Pandas scripts, SQL queries, or shell commands.
2. Every operation MUST use one of the following ALLOWED operation types:
   {allowed_list_str}
3. Referenced columns MUST exist in the dataset schema provided.
4. Output MUST be ONLY a single valid JSON object, without markdown formatting, preamble, or commentary.
5. MULTI-COLUMN EXPANSION: When the user asks to operate on "all numeric columns", "all columns", or a group of columns (e.g., "fill missing in all numeric columns"), you MUST emit a distinct operation in the "operations" list for EACH matching column in the dataset schema. NEVER generate only one operation when multiple columns were requested.
6. IDENTIFIER INTEGRITY: NEVER apply statistical calculations or imputations ("mean", "median", "mode") to identifier or key columns (e.g., columns named 'id', '*_id', 'order_id', 'customer_id', or primary/foreign keys). If an identifier has missing values, suggest dropping missing rows or warn the user, but NEVER impute an ID with a median or mean.
7. GENERAL PREPROCESSING PIPELINES: When the user asks for a "good plan to preprocess this data", "clean data", or general preparation, formulate a robust, cohesive multi-step pipeline combining duplicate removal, missingness imputation (median for numeric columns with nulls), and string whitespace trimming.
8. INFORMATIONAL & DATA INQUIRIES: If the user is asking a question about the dataset (e.g., what a column means, abbreviations like 'Parch' or 'c' and 'q', data definitions, or statistical observations), provide a direct, helpful, and concise plain-English explanation (under 80 words) in the 'summary' field, and set "operations": []. NEVER refuse to answer legitimate data questions with "this is not a transformation".

OPERATION SCHEMAS:
- "rename_column": {{"type": "rename_column", "column": "<existing_col>", "new_name": "<new_name>"}}
- "drop_columns": {{"type": "drop_columns", "columns": ["<col1>", "<col2>"]}}
- "select_columns": {{"type": "select_columns", "columns": ["<col1>", "<col2>"]}}
- "convert_type": {{"type": "convert_type", "column": "<col>", "target_type": "numeric"|"text"|"datetime"|"boolean"|"categorical"}}
- "fill_missing": {{"type": "fill_missing", "column": "<col>", "strategy": "constant"|"mean"|"median"|"mode", "fill_value": <val_if_constant>}}
- "drop_missing_rows": {{"type": "drop_missing_rows", "columns": ["<col>"], "how": "any"|"all"}}
- "remove_duplicates": {{"type": "remove_duplicates", "subset": ["<optional_cols>"], "keep": "first"|"last"}}
- "trim_text": {{"type": "trim_text", "column": "<col>"}}
- "normalize_case": {{"type": "normalize_case", "column": "<col>", "case_type": "lower"|"upper"|"title"}}
- "numeric_round": {{"type": "numeric_round", "column": "<col>", "decimals": <int>}}
- "clip_values": {{"type": "clip_values", "column": "<col>", "lower": <min_val>, "upper": <max_val>}}
- "parse_date": {{"type": "parse_date", "column": "<col>", "format": "<optional_format>"}}
- "create_date_part": {{"type": "create_date_part", "column": "<col>", "part": "year"|"month"|"day"|"dayofweek"|"hour", "new_column_name": "<name>"}}
- "handle_outliers": {{"type": "handle_outliers", "column": "<col>", "method": "iqr", "factor": 1.5, "action": "clip"|"filter"}}
- "replace_values": {{"type": "replace_values", "column": "<col>", "old_value": <val>, "new_value": <val>}}

OUTPUT FORMAT:
Return a JSON object conforming exactly to this structure:
{{
  "summary": "Clear, concise human-readable description of what will be done.",
  "operations": [
    {{"type": "<allowed_type>", ...}}
  ],
  "warnings": [
    "Optional list of potential side effects or warnings (e.g. data loss, column dropping)."
  ],
  "requires_confirmation": true
}}
"""


def build_dataset_context(
    df: pd.DataFrame,
    profile: Optional[Dict[str, Any]] = None,
    health: Optional[Dict[str, Any]] = None,
    max_sample_rows: int = 3
) -> str:
    """
    Constructs a token-efficient, privacy-safe summary of the dataset for LLM ingestion.
    Redacts obvious PII and bounds sample values.
    """
    lines: List[str] = []
    lines.append(f"DATASET DIMENSIONS: {len(df)} rows, {len(df.columns)} columns")
    lines.append("\nCOLUMNS AND SUMMARY:")

    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        null_count = int(series.isna().sum())
        null_pct = round((null_count / len(df)) * 100, 1) if len(df) > 0 else 0
        unique_count = int(series.nunique(dropna=True))

        sample_vals = series.dropna().head(max_sample_rows).tolist()
        # Redact obvious email/phone samples
        clean_samples = []
        for val in sample_vals:
            v_str = str(val)
            if "@" in v_str:
                clean_samples.append("[REDACTED_EMAIL]")
            elif len(v_str) > 30:
                clean_samples.append(v_str[:27] + "...")
            else:
                clean_samples.append(val)

        col_line = f"- Column '{col}': type={dtype}, nulls={null_count} ({null_pct}%), uniques={unique_count}, samples={clean_samples}"
        lines.append(col_line)

    if health and health.get("issues"):
        lines.append("\nKNOWN DATA HEALTH ISSUES:")
        for issue in health["issues"][:5]:
            affected = f" on column '{issue.get('column')}'" if issue.get("column") else ""
            lines.append(f"- [{issue.get('level', 'warning').upper()}]{affected}: {issue.get('message')} (Recommendation: {issue.get('recommendation')})")

    return "\n".join(lines)


def build_planning_user_prompt(user_intent: str, dataset_context: str) -> str:
    """
    Combines the user request and dataset context into the final LLM prompt.
    """
    return f"""DATASET CONTEXT:
{dataset_context}

USER REQUEST:
"{user_intent}"

Please formulate a valid JSON transformation plan to fulfill the user's request.
"""


# ==============================================================================
# FILE SUMMARY: backend/services/ai/prompts.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file constructs prompts for the AI planning assistant:
#   1. build_planning_system_prompt(): Emits system instructions that enforce strict JSON output
#      and specify the schemas for all 15 deterministic data operations in transformations.py.
#   2. build_dataset_context(): Extracts a token-minimized, PII-safe representation of the dataset
#      including column names, types, null counts, unique counts, bounded samples, and health issues.
#   3. build_planning_user_prompt(): Combines user natural language queries with dataset context.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Imports 'ALLOWED_OPERATION_TYPES' from 'backend/services/transformations.py'.
# - Invoked by 'backend/services/ai/planner.py' before querying the LLM provider.
# ==============================================================================
