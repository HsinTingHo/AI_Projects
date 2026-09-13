"""Run retrieval and grounded generation for one financial-report question."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from generation.llm import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_MODEL, generate_answer
except ImportError:  # Supports importing the app as src.app from the project root.
    from src.generation.llm import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_MODEL, generate_answer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings_metadata.json"
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "resources" / "evaluations" / "results" / "app" / "rag_runs.jsonl"


def load_metadata(metadata_path: Path = METADATA_PATH) -> list[dict[str, Any]]:
    """Load chunk metadata so retrieved indexes become citeable report evidence."""
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Embedding metadata was not found: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def get_semantic_search() -> Callable[..., list[dict[str, Any]]]:
    """Import the existing search module without changing its current package layout."""
    retrieval_path = str(PROJECT_ROOT / "src" / "retrival")
    if retrieval_path not in sys.path:
        sys.path.insert(0, retrieval_path)
    return importlib.import_module("semanticSearch").semantic_search


def retrieve_evidence(question: str, metadata: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Run hybrid search and attach stable chunk metadata required for LLM citations."""
    results = get_semantic_search()(question, top_k=top_k, verbose=True)
    evidence: list[dict[str, Any]] = []
    for result in results:
        index = int(result["index"])
        if not 0 <= index < len(metadata):
            raise IndexError(f"Search returned chunk index {index}, outside the metadata range.")
        evidence.append({**metadata[index], "retrieval": result})
    return evidence


def build_run_record(question: str, evidence: list[dict[str, Any]], generation: dict[str, Any]) -> dict[str, Any]:
    """Create a JSON-safe retrieval and generation record for later inspection."""
    retrieval_results = []
    for rank, chunk in enumerate(evidence, start=1):
        metadata = chunk.get("metadata", {})
        scores = chunk["retrieval"]
        retrieval_results.append(
            {
                "rank": rank,
                "chunk_id": chunk.get("chunk_id"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "subsection": metadata.get("subsection"),
                "hybrid_score": scores["score"],
                "semantic_score": scores["semantic_score"],
                "lexical_score": scores["lexical_score"],
                "text_preview": " ".join(str(chunk["text"]).split())[:500],
            }
        )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "retrieval_results": retrieval_results,
        "generation": generation,
    }


def save_run_record(record: dict[str, Any], results_path: Path) -> Path:
    """Append one run record so earlier manual questions remain available for review."""
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8") as results_file:
        results_file.write(json.dumps(record) + "\n")
    return results_path


def parse_args() -> argparse.Namespace:
    """Read a question and optional generation settings from the command line."""
    parser = argparse.ArgumentParser(description="Answer a financial-report question with RAG.")
    parser.add_argument("question", help="Question to answer from the embedded annual report.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve (default: 5).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model to use (default: {DEFAULT_MODEL}).")
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help=f"Maximum visible and reasoning tokens (default: {DEFAULT_MAX_OUTPUT_TOKENS}).",
    )
    parser.add_argument("--results-file", type=Path, default=DEFAULT_RESULTS_PATH, help="JSONL file that receives each run record.")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if args.max_output_tokens < 1:
        parser.error("--max-output-tokens must be positive")
    return args


def main() -> None:
    """Retrieve evidence, generate a cited answer, save the run, and print the answer."""
    args = parse_args()
    question = args.question.strip()
    if not question:
        raise ValueError("question must not be empty")

    evidence = retrieve_evidence(question, load_metadata(), args.top_k)
    generation = generate_answer(
        question,
        evidence,
        model=args.model,
        max_output_tokens=args.max_output_tokens,
    )
    saved_path = save_run_record(build_run_record(question, evidence, generation), args.results_file)
    print(generation["answer"])
    print(f"\nSaved retrieval and generation record to {saved_path}")
    if generation["invalid_citation_ids"]:
        print(f"Warning: unsupported citation IDs: {generation['invalid_citation_ids']}")


if __name__ == "__main__":
    main()
