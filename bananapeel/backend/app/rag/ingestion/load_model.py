from sentence_transformers import SentenceTransformer


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def load_model() -> SentenceTransformer:
    """Load the embedding model only when embedding is actually run."""
    return model