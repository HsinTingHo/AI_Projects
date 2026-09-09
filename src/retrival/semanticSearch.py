"""Retrieve annual-report chunks with hybrid semantic and lexical search."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings.npy"
METADATA_PATH = PROJECT_ROOT / "resources" / "corpus" / "embedded" / "context_aware_embeddings_metadata.json"
MODEL_NAME = "all-MiniLM-L6-v2"
QUERY_STOPWORDS = {"a", "an", "and", "are", "does", "do", "for", "how", "in", "is", "of", "the", "to", "what", "which"}


def tokenize(text: str) -> list[str]:
    """Normalize words so lexical matching handles simple plurals consistently."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token[:-1] if token.endswith("s") and len(token) > 3 else token for token in tokens]


def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """Calculate vector similarity while safely handling an empty embedding."""
    denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    return float(np.dot(vector_a, vector_b) / denominator) if denominator else 0.0


def min_max_normalize(scores: np.ndarray) -> np.ndarray:
    """Scale scores per query so dense and lexical signals can be combined."""
    score_range = scores.max() - scores.min()
    return (scores - scores.min()) / score_range if score_range else np.zeros_like(scores)


def bm25_scores(query_tokens: Sequence[str], documents: Sequence[str]) -> np.ndarray:
    """Score documents lexically so exact terms and financial labels are preserved."""
    tokenized_documents = [tokenize(document) for document in documents]
    document_count = len(tokenized_documents)
    average_length = sum(map(len, tokenized_documents)) / document_count if document_count else 0.0
    document_frequency = Counter(token for tokens in tokenized_documents for token in set(tokens))
    k1, b = 1.5, 0.75
    scores = np.zeros(document_count, dtype=np.float32)

    for index, tokens in enumerate(tokenized_documents):
        term_frequency = Counter(tokens)
        for token in set(query_tokens):
            if not term_frequency[token]:
                continue
            inverse_frequency = math.log(1 + (document_count - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5))
            numerator = term_frequency[token] * (k1 + 1)
            denominator = term_frequency[token] + k1 * (1 - b + b * len(tokens) / average_length)
            scores[index] += inverse_frequency * numerator / denominator
    return scores


def phrase_boosts(query_tokens: Sequence[str], documents: Sequence[str]) -> np.ndarray:
    """Favor chunks containing exact multiword query phrases over broad topical matches."""
    query_phrases = {
        " ".join(query_tokens[start:end])
        for start in range(len(query_tokens))
        for end in range(start + 3, min(len(query_tokens), start + 5) + 1)
    }
    query_phrases.update(
        " ".join(query_tokens[start:start + 2])
        for start in range(len(query_tokens) - 1)
        if not QUERY_STOPWORDS.intersection(query_tokens[start:start + 2])
    )
    boosts = np.zeros(len(documents), dtype=np.float32)
    for index, document in enumerate(documents):
        normalized_document = f" {' '.join(tokenize(document))} "
        longest_match = max((len(phrase.split()) for phrase in query_phrases if f" {phrase} " in normalized_document), default=0)
        boosts[index] = 0.20 * longest_match if longest_match else 0.0
    return boosts


def load_documents_from_metadata(metadata_path: Path) -> list[str]:
    """Load chunk text from embedding metadata so result text is available to callers."""
    records = json.loads(metadata_path.read_text(encoding="utf-8"))
    return [str(record["text"]) for record in records]


def semantic_search(
    query: str,
    documents: Optional[Sequence[str]] = None,
    embeddings_path: Path | str = EMBEDDINGS_PATH,
    metadata_path: Path | str | None = METADATA_PATH,
    top_k: int = 5,
    model_name: str = MODEL_NAME,
    lexical_weight: float = 0.60,
) -> list[dict[str, Any]]:
    """Rank chunks with combined semantic, BM25, and exact-phrase relevance signals."""
    if not 0.0 <= lexical_weight <= 1.0:
        raise ValueError("lexical_weight must be between 0.0 and 1.0")

    embeddings_path = Path(embeddings_path)
    if documents is None and metadata_path is not None:
        documents = load_documents_from_metadata(Path(metadata_path))
    if documents is None:
        raise ValueError("documents or metadata_path must be provided for hybrid search")

    documents = list(documents)
    document_embeddings = np.load(embeddings_path)
    if len(document_embeddings) != len(documents):
        raise ValueError("embeddings and documents must have the same length")

    model = SentenceTransformer(model_name)
    query_embedding = model.encode([query], convert_to_numpy=True)[0]
    dense_scores = np.array([cosine_similarity(query_embedding, embedding) for embedding in document_embeddings])
    query_tokens = tokenize(query)
    lexical_tokens = [token for token in query_tokens if token not in QUERY_STOPWORDS]
    lexical_scores = bm25_scores(lexical_tokens, documents)
    hybrid_scores = (1 - lexical_weight) * min_max_normalize(dense_scores) + lexical_weight * min_max_normalize(lexical_scores) + phrase_boosts(query_tokens, documents)
    top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

    return [
        {
            "index": int(index),
            "text": documents[index],
            "score": float(hybrid_scores[index]),
            "semantic_score": float(dense_scores[index]),
            "lexical_score": float(lexical_scores[index]),
        }
        for index in top_indices
    ]


def main() -> None:
    """Run the sample annual-report queries and print their hybrid top results."""
    queries = [
        "What range of products and services does the company offer?",
        "What is the total revenue in 2025?",
    ]
    for query in queries:
        print(f"\nQuery: {query}")
        for result in semantic_search(query, top_k=5):
            preview = result["text"].replace("\n", " ")[:240]
            print(f"Index {result['index']} | hybrid={result['score']:.4f} | semantic={result['semantic_score']:.4f} | lexical={result['lexical_score']:.4f}\n{preview}\n")


if __name__ == "__main__":
    main()
