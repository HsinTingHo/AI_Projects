"""Persist text chunks and their matching embeddings together."""
from collections.abc import Sequence
import math
from uuid import UUID

import psycopg

from app.rag.ingestion.chunking import ReportChunk


class EmbeddingRepository:
    def __init__(self, conn: psycopg.AsyncConnection):
        self.conn = conn

    async def save_embeddings(
        self,
        document_id: str | UUID,
        chunks: Sequence[ReportChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Pair chunks and vectors by position; insert or update each chunk.

        Accepts nested lists or a two-dimensional NumPy array. The report must
        already exist. Retries preserve chunk IDs. Other chunks and report/job
        statuses remain unchanged; workers must enforce job lease ownership.
        """
        report_id = UUID(str(document_id))
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding")
        if len({chunk.chunk_index for chunk in chunks}) != len(chunks):
            raise ValueError("chunk indexes must be unique")
        rows = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if (chunk.chunk_index < 0 or chunk.page_start < 1
                    or chunk.page_end < chunk.page_start or not chunk.content.strip()):
                raise ValueError("Each chunk needs a valid index, page range, and content")
            vector = [float(value) for value in embedding]
            if len(vector) != 384:
                raise ValueError("Each embedding must have 384 dimensions")
            if not all(math.isfinite(value) and abs(value) <= 3.4028234663852886e38
                       for value in vector):
                raise ValueError("Embedding values must be finite float32 numbers")
            if not any(abs(value) >= 1.401298464324817e-45 for value in vector):
                raise ValueError("Embeddings must be nonzero for cosine search")
            rows.append((report_id, chunk.chunk_index, chunk.page_start,
                         chunk.page_end, chunk.content,
                         "[" + ",".join(map(str, vector)) + "]"))
        if not rows:
            return
        # Explicit casts work without a connection-specific pgvector adapter.
        async with self.conn.transaction():
            async with self.conn.cursor() as cursor:
                await cursor.executemany(
                    """INSERT INTO report_chunks
                       (report_id, chunk_index, page_start, page_end, content, embedding)
                       VALUES (%s, %s, %s, %s, %s, %s::vector)
                       ON CONFLICT (report_id, chunk_index) DO UPDATE SET
                           page_start = EXCLUDED.page_start,
                           page_end = EXCLUDED.page_end,
                           content = EXCLUDED.content,
                           embedding = EXCLUDED.embedding""",
                    rows,
                )
