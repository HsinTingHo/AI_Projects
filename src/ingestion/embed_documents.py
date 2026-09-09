"""Embed chunk records with all-MiniLM-L6-v2 for semantic retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "resources" / "corpus"
FILE_TO_CHUNK = "american_express_2025_chunks.jsonl"
CHUNK_PATH = CORPUS_DIR / FILE_TO_CHUNK
OUTPUT_FILENAME = "context_aware_embeddings"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks(chunks_path: Path = CHUNK_PATH) -> list[dict[str, object]]:
    """Read JSON Lines chunks while rejecting empty or malformed input early."""
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunk file does not exist: {chunks_path}")
    print(f"Loading chunk records from {chunks_path}...")
    with chunks_path.open(encoding="utf-8") as chunk_file:
        records = [json.loads(line) for line in chunk_file if line.strip()]
    if any("text" not in record for record in records):
        raise ValueError("Every chunk record must include a text field")
    return records


def load_embedding_model(model_name: str = MODEL_NAME):
    """Load the requested embedding model only when embedding is actually run."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise ImportError("Install sentence-transformers to create embeddings.") from error
    return SentenceTransformer(model_name)


def embed_documents(
    chunks_path: Path = CHUNK_PATH,
    output_dir: Path = CORPUS_DIR / "embedded",
    output_filename: str = OUTPUT_FILENAME,
    batch_size: int = 32,
    model_name: str = MODEL_NAME,
) -> np.ndarray:
    """Encode chunks and save aligned vectors and metadata for downstream search."""
    records = load_chunks(chunks_path)
    if not records:
        raise ValueError("No chunks are available to embed")

    model = load_embedding_model(model_name)
    embeddings = model.encode([str(record["text"]) for record in records], batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / f"{output_filename}.npy", np.asarray(embeddings, dtype=np.float32))
    (output_dir / f"{output_filename}_metadata.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return np.asarray(embeddings, dtype=np.float32)

def parse_args() -> argparse.Namespace:
    """Parse optional embedding paths and settings from the command line."""
    parser = argparse.ArgumentParser(
        description="Embed chunk records for RAG/vector search."
    )
    parser.add_argument(
        "--chunks-path",
        type=Path,
        default=CHUNK_PATH,
        help="JSON Lines chunk file to embed.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=CORPUS_DIR / "embedded",
        help="Directory for embeddings.npy and metadata.json.",
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        default=OUTPUT_FILENAME,
        help="Filename for the saved embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks to encode in each model batch.",
    )
    parser.add_argument(
        "--model-name",
        default=MODEL_NAME,
        help="Sentence Transformer model name or local model path.",
    )
    return parser.parse_args()

def main() -> None:
    """Run embedding from the command line and report the saved vector count."""
    args = parse_args()
    embeddings = embed_documents(
        chunks_path=args.chunks_path,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        batch_size=args.batch_size,
        model_name=args.model_name,
    )
    print(f"Saved {len(embeddings)} embedding(s) to {args.output_dir}")


if __name__ == "__main__":
    main()
