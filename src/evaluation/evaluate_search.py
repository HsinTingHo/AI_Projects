"""Evaluate annual-report hybrid search against answer-chunk labels."""

from __future__ import annotations

import importlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATION_PATH = PROJECT_ROOT / "resources" / "evaluations" / "american_express_2025_factual_category_1_eval.jsonl"
EMBEDDINGS_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings.npy"
METADATA_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings_metadata.json"
TOP_K = 5
_SEMANTIC_SEARCH: Callable[..., list[dict[str, Any]]] | None = None


def load_evaluation_queries(path: Path = EVALUATION_PATH) -> list[dict[str, Any]]:
    """Load one annual-report evaluation record from each JSONL line."""
    with path.open(encoding="utf-8") as evaluation_file:
        return [json.loads(line) for line in evaluation_file if line.strip()]


def load_metadata(path: Path = METADATA_PATH) -> list[dict[str, Any]]:
    """Load embedding metadata used to map search indexes to chunk IDs."""
    return json.loads(path.read_text(encoding="utf-8"))


def answer_chunk_ids(query: dict[str, Any]) -> set[int]:
    """Extract ungraded relevant chunk IDs from an evaluation record."""
    return {int(chunk["chunk_id"]) for chunk in query.get("answer_chunks", [])}


def recall_at_k(ranked_chunk_ids: list[int], relevant_chunk_ids: set[int], k: int = TOP_K) -> float:
    """Measure the share of labeled answer chunks retrieved in the first k ranks."""
    return len(set(ranked_chunk_ids[:k]) & relevant_chunk_ids) / len(relevant_chunk_ids) if relevant_chunk_ids else 0.0


def ndcg_at_k(ranked_chunk_ids: list[int], relevant_chunk_ids: set[int], k: int = TOP_K) -> float:
    """Measure discounted binary answer-chunk relevance in the first k ranks."""
    dcg = sum(1 / math.log2(rank + 2) for rank, chunk_id in enumerate(ranked_chunk_ids[:k]) if chunk_id in relevant_chunk_ids)
    ideal_dcg = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(relevant_chunk_ids))))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def reciprocal_rank(ranked_chunk_ids: list[int], relevant_chunk_ids: set[int]) -> float:
    """Return the inverse rank of the first labeled answer chunk."""
    for rank, chunk_id in enumerate(ranked_chunk_ids, start=1):
        if chunk_id in relevant_chunk_ids:
            return 1.0 / rank
    return 0.0


def get_semantic_search() -> Callable[..., list[dict[str, Any]]]:
    """Import hybrid search and cache its model for efficient evaluation runs."""
    global _SEMANTIC_SEARCH
    if _SEMANTIC_SEARCH is not None:
        return _SEMANTIC_SEARCH

    retrieval_dir = PROJECT_ROOT / "src" / "retrival"
    sys.path.insert(0, str(retrieval_dir))
    module = importlib.import_module("semanticSearch")
    model = module.SentenceTransformer("all-MiniLM-L6-v2")
    module.SentenceTransformer = lambda _model_name: model
    _SEMANTIC_SEARCH = module.semantic_search
    return _SEMANTIC_SEARCH


def rank_chunks(query_text: str, metadata: list[dict[str, Any]]) -> list[int]:
    """Search all embedded chunks and return their IDs in descending relevance order."""
    semantic_search = get_semantic_search()
    documents = [str(record["text"]) for record in metadata]
    results = semantic_search(
        query=query_text,
        documents=documents,
        embeddings_path=EMBEDDINGS_PATH,
        top_k=len(documents),
        verbose=True,
        log_top_k=TOP_K,
    )
    return [int(metadata[result["index"]]["chunk_id"]) for result in results]


def evaluate_queries(queries: list[dict[str, Any]], metadata: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Average binary retrieval metrics for each annual-report evaluation category."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, int] = defaultdict(int)
    for query in queries:
        relevant_chunk_ids = answer_chunk_ids(query)
        ranked_chunk_ids = rank_chunks(str(query["query"]), metadata)
        print(f"Answer Chunks: {relevant_chunk_ids}")
        category = str(query["eval_category"])
        totals[category]["recall@5"] += recall_at_k(ranked_chunk_ids, relevant_chunk_ids)
        totals[category]["nDCG@5"] += ndcg_at_k(ranked_chunk_ids, relevant_chunk_ids)
        totals[category]["MRR"] += reciprocal_rank(ranked_chunk_ids, relevant_chunk_ids)
        counts[category] += 1
    return {category: {metric: value / counts[category] for metric, value in metrics.items()} for category, metrics in totals.items()}


def print_metrics(metrics_by_category: dict[str, dict[str, float]]) -> None:
    """Print consistently ordered category-level retrieval metrics."""
    for category in sorted(metrics_by_category):
        metrics = metrics_by_category[category]
        print(f"{category}: Recall@5={metrics['recall@5']:.4f}  nDCG@5={metrics['nDCG@5']:.4f}  MRR={metrics['MRR']:.4f}")


def main() -> None:
    """Run the annual-report evaluation from the command line."""
    print_metrics(evaluate_queries(load_evaluation_queries(), load_metadata()))


if __name__ == "__main__":
    main()
