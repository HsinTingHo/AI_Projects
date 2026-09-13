"""Build grounded prompts and validate citations for financial RAG answers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


DEFAULT_MAX_CONTEXT_CHUNKS = 5
DEFAULT_MAX_CONTEXT_CHARACTERS = 12_000
_CITATION_PATTERN = re.compile(r"\[Chunk\s+(\d+)(?:\s*,\s*Page\s+[^\]]+)?\]", re.IGNORECASE)


def _value_from_chunk(chunk: Mapping[str, Any], field: str) -> Any:
    """Read a field from a result or its nested metadata for flexible retrieval inputs."""
    return chunk.get(field, chunk.get("metadata", {}).get(field))


def chunk_reference(chunk: Mapping[str, Any]) -> str:
    """Create a stable human-readable source label so answers can cite their evidence."""
    chunk_id = _value_from_chunk(chunk, "chunk_id")
    if chunk_id is None:
        chunk_id = _value_from_chunk(chunk, "id")
    if chunk_id is None:
        raise ValueError("Each retrieved chunk must include a 'chunk_id' or 'id'.")

    page = _value_from_chunk(chunk, "page")
    return f"[Chunk {chunk_id}]" if page is None else f"[Chunk {chunk_id}, Page {page}]"


def select_context_chunks(
    retrieved_chunks: Sequence[Mapping[str, Any]],
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_characters: int = DEFAULT_MAX_CONTEXT_CHARACTERS,
) -> list[Mapping[str, Any]]:
    """Keep distinct, ranked evidence within a bounded context window to focus generation."""
    if max_chunks < 1 or max_characters < 1:
        raise ValueError("max_chunks and max_characters must both be positive.")

    selected: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    used_characters = 0
    for chunk in retrieved_chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        identifier = str(_value_from_chunk(chunk, "chunk_id") or _value_from_chunk(chunk, "id") or text)
        if identifier in seen_ids:
            continue
        if selected and used_characters + len(text) > max_characters:
            continue

        selected.append(chunk)
        seen_ids.add(identifier)
        used_characters += len(text)
        if len(selected) == max_chunks:
            break
    return selected


def build_context(
    retrieved_chunks: Sequence[Mapping[str, Any]],
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_characters: int = DEFAULT_MAX_CONTEXT_CHARACTERS,
) -> str:
    """Format retrieved evidence with source labels so the model can make verifiable claims."""
    selected = select_context_chunks(retrieved_chunks, max_chunks, max_characters)
    if not selected:
        return "No retrieved evidence was supplied."

    sections = []
    for chunk in selected:
        text = str(chunk["text"]).strip()
        sections.append(f"{chunk_reference(chunk)}\n{text}")
    return "\n\n".join(sections)


def build_system_instructions() -> str:
    """Set grounding rules that prevent the model from treating unsupported claims as facts."""
    return (
        "You are a financial-report question-answering assistant. Answer only from the "
        "provided retrieved evidence. Cite every factual claim with its exact source label "
        "in the form [Chunk <id>, Page <page>] or [Chunk <id>]. Do not invent citations, "
        "numbers, dates, or explanations. If the evidence does not answer the question, say "
        "'I do not have enough information in the retrieved context to answer this question.'"
    )


def build_user_prompt(
    query: str,
    retrieved_chunks: Sequence[Mapping[str, Any]],
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_characters: int = DEFAULT_MAX_CONTEXT_CHARACTERS,
) -> str:
    """Combine a user question and bounded retrieved evidence into one generation request."""
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("query must not be empty.")
    context = build_context(retrieved_chunks, max_chunks, max_characters)
    return f"Question:\n{cleaned_query}\n\nRetrieved evidence:\n{context}\n\nAnswer:"


def extract_citation_ids(answer: str) -> list[int]:
    """Extract cited chunk IDs so callers can check whether an answer stayed grounded."""
    return [int(chunk_id) for chunk_id in _CITATION_PATTERN.findall(answer)]


def validate_citations(answer: str, retrieved_chunks: Sequence[Mapping[str, Any]]) -> dict[str, list[int]]:
    """Separate valid from invalid citations to make unsupported model output easy to flag."""
    available_ids = {
        int(chunk_id)
        for chunk in retrieved_chunks
        if (chunk_id := _value_from_chunk(chunk, "chunk_id") or _value_from_chunk(chunk, "id")) is not None
        and str(chunk_id).isdigit()
    }
    cited_ids = extract_citation_ids(answer)
    valid_ids = [chunk_id for chunk_id in cited_ids if chunk_id in available_ids]
    invalid_ids = [chunk_id for chunk_id in cited_ids if chunk_id not in available_ids]
    return {
        "cited_chunk_ids": cited_ids,
        "valid_citation_ids": valid_ids,
        "invalid_citation_ids": invalid_ids,
    }
