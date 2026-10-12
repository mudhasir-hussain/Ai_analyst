import abc
import json
import re
import logging
import os
from typing import Optional, Dict, Any
import httpx
from core.config import settings
from core.exceptions import LLMProviderError

logger = logging.getLogger("ai_analyst_backend.services.ai.provider")


class BaseLLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Execute text generation synchronously with system and user instructions."""
        pass


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL_NAME
        self.timeout = timeout or getattr(settings, "LLM_TIMEOUT_SECONDS", 30)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json"
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload)
                if response.status_code != 200:
                    raise LLMProviderError(
                        detail=f"Ollama returned HTTP error {response.status_code}: {response.text}",
                        error_code="OLLAMA_HTTP_ERROR"
                    )
                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise LLMProviderError("Ollama returned an empty response.", "EMPTY_LLM_RESPONSE")
                return content
        except httpx.ConnectError as ce:
            logger.warning(f"Cannot connect to Ollama at {self.base_url} ({ce}). Falling back to MockLLMProvider.")
            if settings.ENVIRONMENT == "development":
                return MockLLMProvider(model=f"{self.model}-fallback").generate(system_prompt, user_prompt)
            raise LLMProviderError(
                detail=f"Unable to connect to local Ollama server at {self.base_url}. Ensure Ollama is running.",
                error_code="OLLAMA_CONNECTION_ERROR"
            )
        except httpx.TimeoutException:
            logger.warning(f"Ollama request timed out after {self.timeout}s. Falling back to MockLLMProvider.")
            if settings.ENVIRONMENT == "development":
                return MockLLMProvider(model=f"{self.model}-fallback").generate(system_prompt, user_prompt)
            raise LLMProviderError(
                detail=f"Ollama generation timed out after {self.timeout} seconds.",
                error_code="OLLAMA_TIMEOUT"
            )
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OllamaProvider: {e}")
            raise LLMProviderError(detail=f"Ollama generation failed: {str(e)}", error_code="OLLAMA_ERROR")


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", None) or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL_NAME or "gpt-4o-mini"
        self.timeout = timeout or getattr(settings, "LLM_TIMEOUT_SECONDS", 30)
        if not self.api_key:
            raise LLMProviderError("OpenAI API key not configured.", "OPENAI_KEY_MISSING")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    raise LLMProviderError(
                        detail=f"OpenAI API returned status {response.status_code}: {response.text}",
                        error_code="OPENAI_API_ERROR"
                    )
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("OpenAI returned no completions.", "EMPTY_LLM_RESPONSE")
                return choices[0].get("message", {}).get("content", "")
        except httpx.TimeoutException:
            raise LLMProviderError(f"OpenAI request timed out after {self.timeout}s.", "OPENAI_TIMEOUT")
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"OpenAI request failed: {str(e)}", "OPENAI_ERROR")


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or settings.LLM_API_KEY or os.environ.get("GEMINI_API_KEY")
        self.model = model or getattr(settings, "LLM_MODEL_NAME", None) or "gemini-2.5-flash"
        self.timeout = timeout or getattr(settings, "LLM_TIMEOUT_SECONDS", 30)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            if settings.ENVIRONMENT in {"development", "test"}:
                logger.warning("Gemini API key not configured. Falling back to MockLLMProvider.")
                return MockLLMProvider(model="gemini-fallback").generate(system_prompt, user_prompt)
            raise LLMProviderError("Google Gemini API key not configured. Set GEMINI_API_KEY in backend/.env.", "GEMINI_KEY_MISSING")

        # 1. First attempt: Official google-genai SDK
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config
            )
            if response and response.text:
                return response.text
        except Exception as sdk_err:
            logger.warning(f"google-genai SDK call error ({sdk_err}). Trying direct HTTP REST API.")

        # 2. Second attempt: Direct HTTP REST call to Gemini endpoint
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload)
                if response.status_code != 200:
                    raise LLMProviderError(
                        detail=f"Gemini API returned status {response.status_code}: {response.text}",
                        error_code="GEMINI_API_ERROR"
                    )
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMProviderError("Gemini returned no response candidates.", "EMPTY_LLM_RESPONSE")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise LLMProviderError("Gemini candidate has no content parts.", "EMPTY_LLM_RESPONSE")
                return parts[0].get("text", "")
        except httpx.TimeoutException:
            if settings.ENVIRONMENT in {"development", "test"}:
                logger.warning(f"Gemini request timed out after {self.timeout}s. Falling back to MockLLMProvider.")
                return MockLLMProvider(model="gemini-fallback").generate(system_prompt, user_prompt)
            raise LLMProviderError(f"Gemini request timed out after {self.timeout}s.", "GEMINI_TIMEOUT")
        except LLMProviderError as lpe:
            if settings.ENVIRONMENT in {"development", "test"}:
                logger.warning(f"Gemini error ({lpe.detail}). Falling back to MockLLMProvider.")
                return MockLLMProvider(model="gemini-fallback").generate(system_prompt, user_prompt)
            raise
        except Exception as e:
            if settings.ENVIRONMENT in {"development", "test"}:
                logger.warning(f"Gemini unexpected error ({e}). Falling back to MockLLMProvider.")
                return MockLLMProvider(model="gemini-fallback").generate(system_prompt, user_prompt)
            raise LLMProviderError(f"Gemini request failed: {str(e)}", "GEMINI_ERROR")


class HuggingFaceProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None):
        self.api_key = api_key or getattr(settings, "HUGGINGFACE_API_KEY", None) or settings.LLM_API_KEY
        self.model = model or "meta-llama/Meta-Llama-3-8B-Instruct"
        self.timeout = timeout or getattr(settings, "LLM_TIMEOUT_SECONDS", 30)
        if not self.api_key:
            raise LLMProviderError("Hugging Face API key not configured.", "HUGGINGFACE_KEY_MISSING")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = f"https://api-inference.huggingface.co/models/{self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        prompt = f"<|system|>\n{system_prompt}</s>\n<|user|>\n{user_prompt}</s>\n<|assistant|>\n"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "return_full_text": False
            }
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    raise LLMProviderError(
                        detail=f"Hugging Face returned status {response.status_code}: {response.text}",
                        error_code="HUGGINGFACE_API_ERROR"
                    )
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    return data.get("generated_text", "")
                return str(data)
        except httpx.TimeoutException:
            raise LLMProviderError(f"Hugging Face request timed out after {self.timeout}s.", "HUGGINGFACE_TIMEOUT")
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Hugging Face request failed: {str(e)}", "HUGGINGFACE_ERROR")


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic rule-based intent parser for testing and offline local development.
    Maps natural language prompts into valid JSON operation plans.
    """
    def __init__(self, model: str = "mock-rule-based"):
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Extract explicit user request section if prompt was wrapped with context
        user_req_match = re.search(
            r'USER REQUEST:\s*["\']?(.*?)["\']?\s*(?:Please formulate|\Z)',
            user_prompt,
            re.DOTALL | re.IGNORECASE
        )
        intent_text = user_req_match.group(1).strip() if user_req_match else user_prompt.strip()
        prompt_lower = intent_text.lower()

        operations = []
        warnings = []
        summary = "Applied cleaning operations based on user request."

        # Add clear notice if running in offline fallback mode
        if "fallback" in self.model:
            warnings.append(
                f"Offline fallback engine active ({self.model}). Add GEMINI_API_KEY in backend/.env for live cloud-accelerated Gemini AI."
            )

        # Extract available columns and metadata from dataset context inside prompt if provided
        # Format in prompt: - Column '{col}': type={dtype}, nulls={null_count} ({null_pct}%), uniques={unique_count}, samples={clean_samples}
        col_meta_matches = re.findall(
            r"- Column ['\"]?([a-zA-Z0-9_\s]+)['\"]?:\s*type=([a-zA-Z0-9_]+)(?:,\s*nulls=(\d+))?",
            user_prompt
        )
        parsed_cols = []
        if col_meta_matches:
            for c_name, c_type, c_nulls in col_meta_matches:
                c_name = c_name.strip()
                c_type = c_type.strip().lower()
                null_val = int(c_nulls) if c_nulls else 0
                is_num = any(t in c_type for t in ["int", "float", "double", "num", "decimal"])
                is_id = (
                    c_name.lower() in {"id", "uuid", "guid", "pk", "key", "index"}
                    or c_name.lower().endswith(("_id", ".id", "-id", "_key", "_pk"))
                    or c_name.lower().startswith(("id_", "pk_"))
                )
                parsed_cols.append({
                    "name": c_name,
                    "type": c_type,
                    "nulls": null_val,
                    "is_numeric": is_num,
                    "is_id": is_id
                })
            available_columns = [c["name"] for c in parsed_cols]
        else:
            cols_match = re.findall(r"- Column ['\"]?([a-zA-Z0-9_\s]+)['\"]?:", user_prompt)
            available_columns = [c.strip() for c in cols_match] if cols_match else []
            parsed_cols = [{
                "name": c,
                "type": "unknown",
                "nulls": 0,
                "is_numeric": not (
                    c.lower() in {"id", "uuid", "guid", "pk", "key", "index"}
                    or c.lower().endswith(("_id", ".id", "-id", "_key", "_pk"))
                    or c.lower().startswith(("id_", "pk_"))
                ),
                "is_id": (
                    c.lower() in {"id", "uuid", "guid", "pk", "key", "index"}
                    or c.lower().endswith(("_id", ".id", "-id", "_key", "_pk"))
                    or c.lower().startswith(("id_", "pk_"))
                )
            } for c in available_columns]

        def is_identifier_column(name: str) -> bool:
            nl = name.strip().lower()
            return (
                nl in {"id", "uuid", "guid", "pk", "key", "index"}
                or nl.endswith(("_id", ".id", "-id", "_key", "_pk"))
                or nl.startswith(("id_", "pk_"))
            )

        def get_numeric_columns(exclude_ids: bool = True) -> List[str]:
            num_cols = []
            for c in parsed_cols:
                if c["is_numeric"]:
                    if exclude_ids and c["is_id"]:
                        continue
                    num_cols.append(c["name"])
            if not num_cols and available_columns:
                for c in available_columns:
                    if exclude_ids and is_identifier_column(c):
                        continue
                    if any(term in c.lower() for term in ["price", "cost", "revenue", "amount", "total", "margin", "rating", "discount", "qty", "quantity", "units", "score", "age", "count", "num"]):
                        num_cols.append(c)
            return num_cols

        def detect_column_in_intent(default_col: Optional[str] = None, numeric_only: bool = False, exclude_ids: bool = False) -> Optional[str]:
            for c in available_columns:
                pattern = r'\b' + re.escape(c.lower()) + r'\b'
                if re.search(pattern, prompt_lower):
                    return c
            # Fallback to quoted names
            quoted = re.findall(r"['\"]([a-zA-Z0-9_]+)['\"]", intent_text)
            if quoted:
                return quoted[0]
            if default_col:
                return default_col
            candidates = available_columns
            if numeric_only:
                candidates = get_numeric_columns(exclude_ids=exclude_ids)
            elif exclude_ids:
                candidates = [c for c in available_columns if not is_identifier_column(c)]
            return candidates[0] if candidates else (available_columns[0] if available_columns else None)

        def detect_all_columns_in_intent() -> List[str]:
            found = []
            for c in available_columns:
                pattern = r'\b' + re.escape(c.lower()) + r'\b'
                if re.search(pattern, prompt_lower):
                    found.append(c)
            if not found:
                quoted = re.findall(r"['\"]([a-zA-Z0-9_]+)['\"]", intent_text)
                found = quoted
            return found

        # Intent 0: General preprocessing / comprehensive data cleaning
        if any(w in prompt_lower for w in ["preprocess", "pre-process", "prepare data", "clean data", "clean dataset", "prepare this data", "clean this data", "recommend plan", "suggest plan", "good plan", "pipeline"]):
            operations.append({"type": "remove_duplicates"})
            
            # Impute missing values for numeric columns
            null_numeric = [c["name"] for c in parsed_cols if c["is_numeric"] and not c["is_id"] and c["nulls"] > 0]
            if not null_numeric:
                null_numeric = [c["name"] for c in parsed_cols if c["is_numeric"] and not c["is_id"]]

            for nc in null_numeric[:3]:
                operations.append({"type": "fill_missing", "column": nc, "strategy": "median"})

            # Trim text columns
            text_cols = [c["name"] for c in parsed_cols if not c["is_numeric"] and not c["is_id"]]
            for tc in text_cols[:2]:
                operations.append({"type": "trim_text", "column": tc})

            cols_desc = ", ".join(null_numeric[:3]) if null_numeric else "numeric columns"
            summary = f"Comprehensive Preprocessing: Remove duplicate rows, impute missing values in {cols_desc} with median, and trim whitespace."
            warnings.append("Applied foundational hygiene: deduplication and median imputation for null values.")

        # Intent 1: Drop columns
        elif ("drop" in prompt_lower or "remove column" in prompt_lower or "delete column" in prompt_lower) and not ("missing" in prompt_lower or "null" in prompt_lower):
            cols_found = detect_all_columns_in_intent()
            if not cols_found and available_columns:
                cols_found = [available_columns[-1]]

            operations.append({"type": "drop_columns", "columns": cols_found})
            summary = f"Drop columns: {cols_found}."
            warnings.append(f"Permanently removes columns {cols_found} from future versions.")

        # Intent 2: Remove duplicates / deduplicate
        elif "duplicate" in prompt_lower or "deduplicate" in prompt_lower:
            operations.append({"type": "remove_duplicates"})
            summary = "Remove duplicate rows from dataset."

        # Intent 3: Fill missing / Impute
        elif any(w in prompt_lower for w in ["fill", "full", "missing", "impute", "null"]):
            strategy = "constant"
            if "median" in prompt_lower:
                strategy = "median"
            elif "mean" in prompt_lower or "average" in prompt_lower:
                strategy = "mean"
            elif "mode" in prompt_lower:
                strategy = "mode"

            val_match = re.search(r"with (?:value )?['\"]?([^'\".,\s]+)['\"]?", prompt_lower)
            fill_val = val_match.group(1) if val_match and strategy == "constant" else 0

            # Check if user requested all numeric columns / all columns
            is_all_numeric = bool(
                re.search(r'\b(?:all|every|each|across)\s+(?:the\s+)?(?:numeric|numerical|number|float|integer)\s+columns?\b', prompt_lower)
                or re.search(r'\b(?:numeric|numerical)\s+columns?\b', prompt_lower)
            )
            is_all_cols = bool(
                re.search(r'\b(?:all|every|each|across)\s+(?:the\s+)?columns?\b', prompt_lower)
            )

            explicit_cols = detect_all_columns_in_intent()

            if is_all_numeric or (is_all_cols and strategy in {"mean", "median"}):
                target_cols = get_numeric_columns(exclude_ids=True)
                id_cols = [c["name"] for c in parsed_cols if c["is_id"]] or [c for c in available_columns if is_identifier_column(c)]
                if id_cols:
                    warnings.append(
                        f"Skipped identifier column(s) {id_cols} because statistical imputation ('{strategy}') is inappropriate for unique identifiers."
                    )
                if not target_cols and available_columns:
                    target_cols = [c for c in available_columns if not is_identifier_column(c)]

                for col in target_cols:
                    op = {"type": "fill_missing", "column": col, "strategy": strategy}
                    if strategy == "constant":
                        op["fill_value"] = fill_val
                    operations.append(op)

                summary = f"Fill missing values in {len(target_cols)} numeric column(s) ({', '.join(target_cols)}) using strategy '{strategy}'."

            elif explicit_cols:
                for col in explicit_cols:
                    if is_identifier_column(col) and strategy in {"mean", "median"}:
                        warnings.append(
                            f"Warning: Applying statistical '{strategy}' to identifier column '{col}' may distort keys."
                        )
                    op = {"type": "fill_missing", "column": col, "strategy": strategy}
                    if strategy == "constant":
                        op["fill_value"] = fill_val
                    operations.append(op)
                summary = f"Fill missing values in column(s) {explicit_cols} using strategy '{strategy}'."

            else:
                # If no specific column was named, find candidate columns that actually have missing values
                cols_with_nulls = [c["name"] for c in parsed_cols if c["nulls"] > 0 and (not c["is_id"] or strategy == "constant")]
                if cols_with_nulls:
                    for col in cols_with_nulls:
                        op = {"type": "fill_missing", "column": col, "strategy": strategy}
                        if strategy == "constant":
                            op["fill_value"] = fill_val
                        operations.append(op)
                    summary = f"Fill missing values in columns with nulls ({', '.join(cols_with_nulls)}) using strategy '{strategy}'."
                else:
                    target_col = detect_column_in_intent(
                        default_col="revenue" if "revenue" in available_columns else None,
                        numeric_only=(strategy in {"mean", "median"}),
                        exclude_ids=True
                    )
                    op = {"type": "fill_missing", "column": target_col, "strategy": strategy}
                    if strategy == "constant":
                        op["fill_value"] = fill_val
                    operations.append(op)
                    summary = f"Fill missing values in column '{target_col}' using strategy '{strategy}'."

        # Intent 4: Round numeric
        elif "round" in prompt_lower:
            dec_match = re.search(r"(\d+)\s*(?:decimals?|places?)", prompt_lower)
            decimals = int(dec_match.group(1)) if dec_match else 2

            is_all_numeric = bool(
                re.search(r'\b(?:all|every|each|across)\s+(?:the\s+)?(?:numeric|numerical|number|float)?\s*columns?\b', prompt_lower)
            )
            explicit_cols = detect_all_columns_in_intent()

            if is_all_numeric and not explicit_cols:
                target_cols = get_numeric_columns(exclude_ids=True)
                for col in target_cols:
                    operations.append({"type": "numeric_round", "column": col, "decimals": decimals})
                summary = f"Round {len(target_cols)} numeric column(s) ({', '.join(target_cols)}) to {decimals} decimal places."
            else:
                target_col = explicit_cols[0] if explicit_cols else detect_column_in_intent(
                    default_col="revenue" if "revenue" in available_columns else None,
                    numeric_only=True,
                    exclude_ids=True
                )
                operations.append({"type": "numeric_round", "column": target_col, "decimals": decimals})
                summary = f"Round values in '{target_col}' to {decimals} decimal places."

        # Intent 5: Trim text / whitespace
        elif "trim" in prompt_lower:
            target_col = detect_column_in_intent()
            operations.append({"type": "trim_text", "column": target_col})
            summary = f"Trim whitespace in column '{target_col}'."

        # Intent 6: Normalize case
        elif any(w in prompt_lower for w in ["lowercase", "uppercase", "capitalize", "titlecase"]):
            case_type = "lower"
            if "upper" in prompt_lower:
                case_type = "upper"
            elif "title" in prompt_lower or "capitalize" in prompt_lower:
                case_type = "title"

            target_col = detect_column_in_intent()
            operations.append({"type": "normalize_case", "column": target_col, "case_type": case_type})
            summary = f"Normalize case of column '{target_col}' to {case_type}."

        # Intent 7: Convert type
        elif "convert" in prompt_lower or "cast" in prompt_lower:
            target_type = "numeric"
            if "datetime" in prompt_lower or "date" in prompt_lower:
                target_type = "datetime"
            elif "text" in prompt_lower or "string" in prompt_lower:
                target_type = "text"
            elif "bool" in prompt_lower:
                target_type = "boolean"
            elif "categor" in prompt_lower:
                target_type = "categorical"

            target_col = detect_column_in_intent()
            operations.append({"type": "convert_type", "column": target_col, "target_type": target_type})
            summary = f"Convert column '{target_col}' to type '{target_type}'."

        # Intent 8: Rename column
        elif "rename" in prompt_lower:
            rename_match = re.search(r"rename\s+['\"]?([a-zA-Z0-9_]+)['\"]?\s+to\s+['\"]?([a-zA-Z0-9_]+)['\"]?", prompt_lower)
            if rename_match:
                old_c, new_c = rename_match.group(1), rename_match.group(2)
            else:
                old_c = detect_column_in_intent() or "old_col"
                new_c = "renamed_col"
            operations.append({"type": "rename_column", "column": old_c, "new_name": new_c})
            summary = f"Rename column '{old_c}' to '{new_c}'."

        # Intent 9: Handle outliers
        elif "outlier" in prompt_lower:
            action = "filter" if "remove" in prompt_lower or "drop" in prompt_lower else "clip"
            target_col = detect_column_in_intent()
            operations.append({"type": "handle_outliers", "column": target_col, "method": "iqr", "action": action})
            summary = f"Handle outliers in '{target_col}' using IQR {action}."

        # Default fallback: Remove duplicates
        else:
            operations.append({"type": "remove_duplicates"})
            summary = "Clean dataset hygiene: deduplicate identical rows."

        plan_dict = {
            "summary": summary,
            "operations": operations,
            "warnings": warnings,
            "requires_confirmation": True
        }
        return json.dumps(plan_dict, indent=2)


def get_llm_provider(provider_name: Optional[str] = None, timeout: Optional[int] = None) -> BaseLLMProvider:
    """
    Factory creating an instance of the configured LLM provider.
    Falls back gracefully to MockLLMProvider in development/test if requested provider is unreachable.
    """
    target = (provider_name or settings.LLM_PROVIDER or "gemini").lower().strip()

    if target == "mock":
        return MockLLMProvider()

    elif target in {"gemini", "google"}:
        return GeminiProvider(timeout=timeout)

    elif target in {"openai", "chatgpt"}:
        return OpenAIProvider(timeout=timeout)

    elif target == "ollama":
        return OllamaProvider(timeout=timeout)

    elif target in {"huggingface", "hf"}:
        return HuggingFaceProvider(timeout=timeout)

    else:
        logger.warning(f"Unknown LLM provider '{target}', defaulting to MockLLMProvider.")
        return MockLLMProvider()


# ==============================================================================
# FILE SUMMARY: backend/services/ai/provider.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file defines the LLM Provider abstraction layer for natural language planning:
#   1. BaseLLMProvider: Abstract base class enforcing a synchronous 'generate(system, user)' interface.
#   2. OllamaProvider: Connects to local Ollama runtime via HTTP POST /api/chat with JSON mode.
#   3. OpenAIProvider: Connects to OpenAI chat completions endpoint enforcing JSON schema outputs.
#   4. GeminiProvider: Connects to Google Gemini generateContent REST API requesting JSON mime-type.
#   5. HuggingFaceProvider: Connects to Hugging Face Serverless / Dedicated Inference endpoints.
#   6. MockLLMProvider: Fast, deterministic, rule-based natural language intent parser capable of
#      translating user requests into valid cleaning operations offline without external dependencies.
#   7. get_llm_provider(): Provider factory reading settings.LLM_PROVIDER with fallback handling.
#
# HOW IT CONNECTS TO OTHER FILES:
# - Invoked by 'backend/services/ai/planner.py' to generate raw JSON plans from prompts.
# - Reads settings ('LLM_PROVIDER', 'LLM_MODEL_NAME', 'OLLAMA_BASE_URL', etc.) from 'backend/core/config.py'.
# - Raises 'LLMProviderError' from 'backend/core/exceptions.py' upon timeouts or network failures.
# ==============================================================================
