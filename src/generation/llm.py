"""Call an LLM to produce evidence-grounded answers from retrieved chunks."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

try:
    from .prompt import build_system_instructions, build_user_prompt, validate_citations
except ImportError:  # Supports running this file directly from its folder.
    from prompt import build_system_instructions, build_user_prompt, validate_citations


API_KEY_ENVIRONMENT_VARIABLE = "FINANCIAL_RAG_API_KEY"
DEFAULT_MODEL = "gpt-5"
DEFAULT_MAX_OUTPUT_TOKENS = 1_500


def get_api_key() -> str:
    """Read the API key from the environment so secrets never live in source code."""
    api_key = os.getenv(API_KEY_ENVIRONMENT_VARIABLE, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Set {API_KEY_ENVIRONMENT_VARIABLE} before running generation. "
            "For example: export FINANCIAL_RAG_API_KEY='your-api-key'."
        )
    return api_key


def create_llm_client(api_key: str | None = None) -> Any:
    """Create the OpenAI client lazily so prompt utilities remain usable without the SDK."""
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Install the 'openai' package to use the generation stage.") from error
    return OpenAI(api_key=api_key or get_api_key())


def describe_empty_response(response: Any) -> str:
    """Summarize API completion details so an empty answer can be diagnosed quickly."""
    incomplete_details = getattr(response, "incomplete_details", None)
    incomplete_reason = getattr(incomplete_details, "reason", None)
    if isinstance(incomplete_details, dict):
        incomplete_reason = incomplete_details.get("reason")
    error = getattr(response, "error", None)
    error_message = getattr(error, "message", None) if error else None
    if isinstance(error, dict):
        error_message = error.get("message")
    return (
        f"status={getattr(response, 'status', None)!r}, "
        f"incomplete_reason={incomplete_reason!r}, error={error_message!r}, "
        f"response_id={getattr(response, 'id', None)!r}"
    )


def generate_answer(
    query: str,
    retrieved_chunks: Sequence[Mapping[str, Any]],
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    client: Any | None = None,
) -> dict[str, Any]:
    """Generate a cited answer and report citation validity for downstream quality checks."""
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive.")

    response = (client or create_llm_client()).responses.create(
        model=model,
        instructions=build_system_instructions(),
        input=build_user_prompt(query, retrieved_chunks),
        max_output_tokens=max_output_tokens,
    )
    answer = (response.output_text or "").strip()
    if not answer:
        raise RuntimeError(
            "The LLM returned no visible answer. "
            f"Response details: {describe_empty_response(response)}. "
            "Increase max_output_tokens or inspect the response ID in the OpenAI dashboard."
        )
    citation_check = validate_citations(answer, retrieved_chunks)
    return {
        "answer": answer,
        "model": model,
        "response_id": getattr(response, "id", None),
        **citation_check,
    }
