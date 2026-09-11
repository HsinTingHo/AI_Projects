"""Evaluate annual-report hybrid search against answer-chunk labels."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATIONS_DIR = PROJECT_ROOT / "resources" / "evaluations"
EVALUATION_PATH = EVALUATIONS_DIR / "american_express_2025_factual_category_1_eval.jsonl"
RESULTS_DIR = EVALUATIONS_DIR / "results"
EMBEDDINGS_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings.npy"
METADATA_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings_metadata.json"
TOP_K = 5
DEBUG_TOP_K = 20
_SEMANTIC_SEARCH: Callable[..., list[dict[str, Any]]] | None = None


def load_evaluation_queries(path: Path = EVALUATION_PATH) -> list[dict[str, Any]]:
    """Load one annual-report evaluation record from each JSONL line."""
    with path.open(encoding="utf-8") as evaluation_file:
        return [json.loads(line) for line in evaluation_file if line.strip()]


def resolve_evaluation_path(evaluation_file: str) -> Path:
    """Resolve a filename in the evaluations folder or accept an explicit path."""
    candidate = Path(evaluation_file)
    return candidate if candidate.is_absolute() or candidate.exists() else EVALUATIONS_DIR / candidate


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


def rank_chunks(query_text: str, metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Search all embedded chunks and return detailed results in relevance order."""
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
    return results


def ranked_chunk_ids(results: list[dict[str, Any]], metadata: list[dict[str, Any]]) -> list[int]:
    """Map ranked search indexes to their stable annual-report chunk IDs."""
    return [int(metadata[result["index"]]["chunk_id"]) for result in results]


def first_relevant_rank(ranked_ids: list[int], relevant_ids: set[int]) -> int | None:
    """Find the first one-based rank containing an expected answer chunk."""
    return next((rank for rank, chunk_id in enumerate(ranked_ids, start=1) if chunk_id in relevant_ids), None)


def build_ranking_record(
    query: dict[str, Any],
    results: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    relevant_ids: set[int],
) -> dict[str, Any]:
    """Build one JSONL-friendly ranking diagnostic record for an evaluation query."""
    ranked_ids = ranked_chunk_ids(results, metadata)
    top_results = []
    for rank, result in enumerate(results[:DEBUG_TOP_K], start=1):
        chunk_record = metadata[result["index"]]
        chunk_metadata = chunk_record.get("metadata", {})
        chunk_id = int(chunk_record["chunk_id"])
        top_results.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "page": chunk_metadata.get("page"),
                "section": chunk_metadata.get("section"),
                "subsection": chunk_metadata.get("subsection"),
                "hybrid_score": result["score"],
                "semantic_score": result["semantic_score"],
                "lexical_score": result["lexical_score"],
                "is_relevant": chunk_id in relevant_ids,
                "text_preview": " ".join(str(result["text"]).split())[:300],
            }
        )
    return {
        "eval_id": query["eval_id"],
        "query": query["query"],
        "intended_question": query.get("intended_question"),
        "answer": query.get("answer"),
        "eval_category": query["eval_category"],
        "expected_chunk_ids": sorted(relevant_ids),
        "first_relevant_rank": first_relevant_rank(ranked_ids, relevant_ids),
        "recall_at_5": recall_at_k(ranked_ids, relevant_ids),
        "ndcg_at_5": ndcg_at_k(ranked_ids, relevant_ids),
        "mrr": reciprocal_rank(ranked_ids, relevant_ids),
        "results": top_results,
    }


def evaluate_queries(
    queries: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    ranking_records: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, float]]:
    """Average binary retrieval metrics for each annual-report evaluation category."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, int] = defaultdict(int)
    for query in queries:
        relevant_chunk_ids = answer_chunk_ids(query)
        results = rank_chunks(str(query["query"]), metadata)
        ranked_ids = ranked_chunk_ids(results, metadata)
        print(f"Answer Chunks: {relevant_chunk_ids}")
        category = str(query["eval_category"])
        totals[category]["recall@5"] += recall_at_k(ranked_ids, relevant_chunk_ids)
        totals[category]["nDCG@5"] += ndcg_at_k(ranked_ids, relevant_chunk_ids)
        totals[category]["MRR"] += reciprocal_rank(ranked_ids, relevant_chunk_ids)
        counts[category] += 1
        if ranking_records is not None:
            ranking_records.append(build_ranking_record(query, results, metadata, relevant_chunk_ids))
    return {category: {metric: value / counts[category] for metric, value in metrics.items()} for category, metrics in totals.items()}


def print_metrics(metrics_by_category: dict[str, dict[str, float]]) -> None:
    """Print consistently ordered category-level retrieval metrics."""
    for category in sorted(metrics_by_category):
        metrics = metrics_by_category[category]
        print(f"{category}: Recall@5={metrics['recall@5']:.4f}  nDCG@5={metrics['nDCG@5']:.4f}  MRR={metrics['MRR']:.4f}")


def save_metrics(metrics_by_category: dict[str, dict[str, float]], evaluation_path: Path, version: str) -> Path:
    """Write category metrics as one JSONL record inside the requested version folder."""
    if not version or Path(version).name != version:
        raise ValueError("version must be a single folder name")
    output_dir = RESULTS_DIR / version
    output_path = output_dir / f"{evaluation_path.stem}_metrics.{version}.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics_by_category) + "\n", encoding="utf-8")
    return output_path


def save_rankings(ranking_records: list[dict[str, Any]], evaluation_path: Path, version: str) -> Path:
    """Write one ranked-result diagnostic record per query into a version folder."""
    if not version or Path(version).name != version:
        raise ValueError("version must be a single folder name")
    output_dir = RESULTS_DIR / version
    output_path = output_dir / f"{evaluation_path.stem}_rank.{version}.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as ranking_file:
        for record in ranking_records:
            ranking_file.write(json.dumps(record) + "\n")
    return output_path


def parse_args() -> argparse.Namespace:
    """Parse the evaluation filename and optional metrics-result version."""
    parser = argparse.ArgumentParser(description="Evaluate annual-report retrieval quality.")
    parser.add_argument(
        "--evaluation-file",
        default=EVALUATION_PATH.name,
        help="Evaluation JSONL filename in resources/evaluations or an explicit path.",
    )
    parser.add_argument(
        "--version",
        help="Optional version used for the results folder and metrics filename.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the annual-report evaluation from the command line."""
    args = parse_args()
    evaluation_path = resolve_evaluation_path(args.evaluation_file)
    ranking_records: list[dict[str, Any]] | None = [] if args.version else None
    metrics_by_category = evaluate_queries(load_evaluation_queries(evaluation_path), load_metadata(), ranking_records)
    print_metrics(metrics_by_category)
    if args.version:
        metrics_path = save_metrics(metrics_by_category, evaluation_path, args.version)
        rankings_path = save_rankings(ranking_records or [], evaluation_path, args.version)
        print(f"Saved metrics to {metrics_path}")
        print(f"Saved ranking diagnostics to {rankings_path}")


if __name__ == "__main__":
    main()
