"""Page-aware chunking using the embedding model's supplied token counter."""
import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

from app.rag.ingestion.extraction import ExtractedPage


@dataclass(frozen=True)
class ReportChunk:
    chunk_index: int
    page_start: int
    page_end: int
    content: str


def _validate_budget(max_tokens: int, overlap_tokens: int) -> None:
    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than zero")
    if not 0 <= overlap_tokens < max_tokens:
        raise ValueError("overlap_tokens must be nonnegative and less than max_tokens")


def _pieces(text: str, count_tokens: Callable[[str], int], budget: int) -> Iterator[str]:
    """Prefer paragraph, sentence, then word boundaries; preserve every character."""
    if count_tokens(text) <= budget:
        yield text
        return
    for pattern in (r"\n\s*\n", r"(?<=[.!?])\s+", r"\s+"):
        # Attach separators to preceding text rather than discarding them.
        ends = [match.end() for match in re.finditer(pattern, text) if match.end() < len(text)]
        if ends:
            start = 0
            for end in [*ends, len(text)]:
                yield from _pieces(text[start:end], count_tokens, budget)
                start = end
            return
    if len(text) <= 1:
        raise ValueError("Token budget cannot accommodate a single character")
    middle = len(text) // 2
    yield from _pieces(text[:middle], count_tokens, budget)
    yield from _pieces(text[middle:], count_tokens, budget)


def _overlap(previous: str, following: str, count_tokens: Callable[[str], int],
             max_tokens: int, overlap_tokens: int) -> str:
    """Keep a bounded suffix only when the next piece still fits.

    Overlap is a maximum, not a promise of an exact token count. Shrinking by
    characters guarantees progress without assuming token counts are monotonic.
    """
    if not overlap_tokens:
        return ""
    suffix = previous
    while suffix:
        if (count_tokens(suffix) <= overlap_tokens
                and count_tokens(suffix + following) <= max_tokens):
            return suffix
        suffix = suffix[max(1, len(suffix) // 2):]
    return ""

def count_tokens(text: str, tokenizer) -> int:
    return len(tokenizer.encode(
        text,
        add_special_tokens=False,
        truncation=False,
    ))

def split_by_tokens(text: str, count_tokens: Callable[[str], int], max_tokens: int,
                    overlap_tokens: int = 0) -> list[str]:
    """Split without truncation, counting each complete candidate including separators.

    The counter must use the embedding model's tokenizer. max_tokens excludes
    space reserved for special tokens. No approximate fallback is used.
    """
    _validate_budget(max_tokens, overlap_tokens)
    if not text.strip():
        return []
    chunks: list[str] = []
    current = ""
    for piece in _pieces(text, count_tokens, max_tokens):
        candidate = current + piece
        if current and count_tokens(candidate) > max_tokens:
            if current.strip():
                chunks.append(current)
            current = _overlap(current, piece, count_tokens, max_tokens, overlap_tokens) + piece
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return chunks


def chunk_pages(pages: Sequence[ExtractedPage], *, count_tokens: Callable[[str], int],
                max_tokens: int, overlap_tokens: int = 0) -> list[ReportChunk]:
    """Chunk each page separately, retaining its original citation page number."""
    _validate_budget(max_tokens, overlap_tokens)
    result: list[ReportChunk] = []
    for page in pages:
        for content in split_by_tokens(page.text, count_tokens, max_tokens, overlap_tokens):
            result.append(ReportChunk(
                chunk_index=len(result), page_start=page.page_number,
                page_end=page.page_number, content=content,
            ))
    return result
