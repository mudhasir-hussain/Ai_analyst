from services.ai.provider import (
    BaseLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    GeminiProvider,
    HuggingFaceProvider,
    MockLLMProvider,
    get_llm_provider
)
from services.ai.prompts import (
    build_planning_system_prompt,
    build_dataset_context,
    build_planning_user_prompt
)
from services.ai.planner import (
    generate_ai_plan,
    approve_and_execute_plan,
    validate_plan_operations,
    extract_and_parse_json,
    _DEV_AI_PLANS_CACHE
)

__all__ = [
    "BaseLLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "HuggingFaceProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "build_planning_system_prompt",
    "build_dataset_context",
    "build_planning_user_prompt",
    "generate_ai_plan",
    "approve_and_execute_plan",
    "validate_plan_operations",
    "extract_and_parse_json",
    "_DEV_AI_PLANS_CACHE"
]


# ==============================================================================
# FILE SUMMARY: backend/services/ai/__init__.py
# ==============================================================================
# WHAT THIS FILE CONTAINS AND DOES:
# This file initializes the AI planning package and exposes its key components:
#   - LLM Provider classes and factory ('get_llm_provider', 'BaseLLMProvider', 'MockLLMProvider', etc.)
#   - Prompt construction utilities ('build_planning_system_prompt', 'build_dataset_context', etc.)
#   - Planning and execution orchestration ('generate_ai_plan', 'approve_and_execute_plan')
#
# HOW IT CONNECTS TO OTHER FILES:
# - Exported to 'backend/api/datasets.py' and test suites for natural language data transformation.
# ==============================================================================
