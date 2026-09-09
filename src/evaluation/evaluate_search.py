"""Evaluate semantic search against the labeled job-query benchmark."""

from __future__ import annotations

import contextlib
import io
import importlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "resources" / "corpus"
QUERIES_PATH = CORPUS_DIR / "labled_queries.txt"
EMBEDDINGS_PATH = CORPUS_DIR / "embedded" / "embeddings.npy"
METADATA_PATH = CORPUS_DIR / "embedded" / "metadata.json"
TOP_K = 5
_SEMANTIC_SEARCH: Callable[..., list[dict[str, Any]]] | None = None


def load_labeled_queries(path: Path = QUERIES_PATH) -> list[dict[str, Any]]:
    """Load benchmark queries and graded job relevance labels from JSON text."""
    content = path.read_text(encoding="utf-8").strip()
    if content.startswith("[") and not content.endswith("]"):
        content += "\n]"
    return json.loads(content)


def load_metadata(path: Path = METADATA_PATH) -> list[dict[str, Any]]:
    """Load chunk metadata so search result indexes can be mapped to job postings."""
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(value: str) -> str:
    """Normalize names so label companies match filenames despite punctuation changes."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def job_name_for_source(source_file: str, known_labels: set[str]) -> str:
    """Map a cleaned filename to its labeled company name when one is available."""
    normalized_source = normalize_name(Path(source_file).stem)
    for label in sorted(known_labels, key=len, reverse=True):
        if normalize_name(label) in normalized_source:
            return label
    return Path(source_file).stem


def relevance_grades(query: dict[str, Any]) -> dict[str, int]:
    """Convert graded benchmark labels into numeric gains for ranking metrics."""
    relevance = query["relevance"]
    grades = {name: 1 for name in relevance.get("partially_relevant", [])}
    grades.update({name: 2 for name in relevance.get("highly_relevant", [])})
    return grades


def recall_at_k(ranked_jobs: list[str], grades: dict[str, int], k: int = TOP_K) -> float:
    """Measure the share of all labeled-relevant jobs retrieved in the first k ranks."""
    relevant_jobs = set(grades)
    return len(set(ranked_jobs[:k]) & relevant_jobs) / len(relevant_jobs) if relevant_jobs else 0.0


def ndcg_at_k(ranked_jobs: list[str], grades: dict[str, int], k: int = TOP_K) -> float:
    """Reward highly relevant jobs more strongly while discounting lower ranks."""
    def dcg(job_names: list[str]) -> float:
        return sum((2 ** grades.get(name, 0) - 1) / math.log2(rank + 2) for rank, name in enumerate(job_names[:k]))

    ideal_jobs = sorted(grades, key=grades.get, reverse=True)
    ideal_dcg = dcg(ideal_jobs)
    return dcg(ranked_jobs) / ideal_dcg if ideal_dcg else 0.0


def reciprocal_rank(ranked_jobs: list[str], grades: dict[str, int]) -> float:
    """Return the inverse rank of the first job with any positive relevance grade."""
    for rank, job_name in enumerate(ranked_jobs, start=1):
        if grades.get(job_name, 0) > 0:
            return 1.0 / rank
    return 0.0


def get_semantic_search() -> Callable[..., list[dict[str, Any]]]:
    """Import the existing search and reuse one model to keep evaluation practical."""
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


def rank_jobs(query_text: str, metadata: list[dict[str, Any]], known_labels: set[str]) -> list[str]:
    """Search all chunks and collapse their highest scores into one rank per job."""
    semantic_search = get_semantic_search()
    documents = [str(record["text"]) for record in metadata]
    # with contextlib.redirect_stdout(io.StringIO()):
    chunk_results = semantic_search(query=query_text, documents=documents, embeddings_path=str(EMBEDDINGS_PATH), top_k=len(documents))

    job_scores: dict[str, float] = {}
    for result in chunk_results:
        job_name = job_name_for_source(str(metadata[result["index"]]["source_file"]), known_labels)
        job_scores[job_name] = max(job_scores.get(job_name, float("-inf")), float(result["score"]))
    return [name for name, _ in sorted(job_scores.items(), key=lambda item: item[1], reverse=True)]


def evaluate_queries(queries: list[dict[str, Any]], metadata: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Evaluate every query and average Recall@5, nDCG@5, and MRR by category."""
    known_labels = {name for query in queries for name in relevance_grades(query)}
    totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, int] = defaultdict(int)
    for query in queries:
        grades = relevance_grades(query)
        ranked_jobs = rank_jobs(str(query["query"]), metadata, known_labels)
        category = str(query["category"])
        totals[category]["recall@5"] += recall_at_k(ranked_jobs, grades)
        totals[category]["nDCG@5"] += ndcg_at_k(ranked_jobs, grades)
        totals[category]["MRR"] += reciprocal_rank(ranked_jobs, grades)
        counts[category] += 1
    return {category: {metric: value / counts[category] for metric, value in metrics.items()} for category, metrics in totals.items()}


def print_metrics(metrics_by_category: dict[str, dict[str, float]]) -> None:
    """Print compact, consistently ordered category-level retrieval metrics."""
    for category in sorted(metrics_by_category):
        metrics = metrics_by_category[category]
        print(f"{category}: Recall@5={metrics['recall@5']:.4f}  nDCG@5={metrics['nDCG@5']:.4f}  MRR={metrics['MRR']:.4f}")


def main() -> None:
    """Run the labeled-query evaluation from the command line."""
    print_metrics(evaluate_queries(load_labeled_queries(), load_metadata()))


if __name__ == "__main__":
    main()
