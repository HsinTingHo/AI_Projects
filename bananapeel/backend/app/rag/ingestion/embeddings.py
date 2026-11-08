from sentence_transformers import SentenceTransformer
from app.rag.ingestion.chunking import ReportChunk

import numpy as np

def embed_documents(
        model: SentenceTransformer,
        chunks: list[ReportChunk],
) -> np.ndarray:
    try:
        embeddings = model.encode(
            [chunk.content for chunk in chunks],
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        return np.asarray(embeddings, dtype=np.float32)
    except Exception as error:
        #log error
        raise ValueError("Failed to generate embeddings") from error