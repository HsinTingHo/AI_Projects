"""Split cleaned job postings into overlapping, retrieval-friendly chunks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "resources" / "corpus"
CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 60


def split_long_paragraph(paragraph: str, max_words: int) -> list[str]:
    """Split oversized paragraphs at sentence boundaries to keep chunks readable."""
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    parts: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if current and current_words + len(sentence_words) > max_words:
            parts.append(" ".join(current))
            current, current_words = [], 0
        if len(sentence_words) > max_words:
            parts.extend(" ".join(sentence_words[index:index + max_words]) for index in range(0, len(sentence_words), max_words))
        else:
            current.append(sentence)
            current_words += len(sentence_words)
    if current:
        parts.append(" ".join(current))
    return parts


def get_paragraphs(text: str, max_words: int = CHUNK_SIZE_WORDS) -> list[str]:
    """Preserve paragraph meaning while preparing units that fit the target size."""
    paragraphs = [re.sub(r"\s+", " ", value).strip() for value in re.split(r"\n{2,}", text)]
    return [part for paragraph in paragraphs if paragraph for part in split_long_paragraph(paragraph, max_words)]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Build moderately sized word chunks with overlap to retain context at joins."""
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[str] = []
    current_words: list[str] = []
    for paragraph in get_paragraphs(text, chunk_size - overlap):
        paragraph_words = paragraph.split()
        if current_words and len(current_words) + len(paragraph_words) > chunk_size:
            chunks.append(" ".join(current_words))
            current_words = current_words[-overlap:] if overlap else []
        current_words.extend(paragraph_words)
    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def create_chunk_record(text: str, source_file: str, chunk_index: int) -> dict[str, object]:
    """Attach stable identifiers and source metadata to a text chunk."""
    digest = hashlib.sha256(f"{source_file}:{chunk_index}:{text}".encode("utf-8")).hexdigest()[:16]
    return {"id": f"{Path(source_file).stem}-{digest}", "text": text, "source_file": source_file, "chunk_index": chunk_index}


def chunk_documents(cleaned_dir: Path | None = None, output_path: Path | None = None) -> list[dict[str, object]]:
    """Chunk all cleaned postings and replace the single corpus chunk file."""
    cleaned_dir = cleaned_dir or CORPUS_DIR / "cleaned" /"financialStatement"
    output_path = output_path or CORPUS_DIR / "chunks"
    if not cleaned_dir.exists():
        raise FileNotFoundError(f"Cleaned corpus directory does not exist: {cleaned_dir}")

    records: list[dict[str, object]] = []
    for source_path in sorted(cleaned_dir.glob("*.txt")):
        text = source_path.read_text(encoding="utf-8").strip()
        records.extend(create_chunk_record(chunk, source_path.name, index) for index, chunk in enumerate(chunk_text(text)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


def main() -> None:
    """Run corpus chunking from the command line and report its result."""
    records = chunk_documents()
    print(f"Wrote {len(records)} chunk(s) to {CORPUS_DIR / 'chunks'}")


if __name__ == "__main__":
    main()
