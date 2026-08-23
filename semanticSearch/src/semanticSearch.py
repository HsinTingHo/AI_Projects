import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

def open_source_documents():
    json_path = Path(__file__).resolve().parent.parent / "resources" / "documents.json"
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data["documents"]
    except FileNotFoundError:
        print(f"File not found: {json_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file: {json_path}")
        return []

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)

def semantic_search(query, documents, top_k=5):
    print("Initializing the sentence transformer model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    texts = [doc["text"] for doc in documents]
    
    embeddings = model.encode(texts)

    query_embedding = model.encode([query])[0]

    results = []
    for doc, embedding in zip(documents, embeddings):
        similarity = cosine_similarity(query_embedding, embedding)
        results.append({
            "id": doc["id"],
            "text": doc["text"],
            "similarity": similarity
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    for result in results[:top_k]:
        print(f"Document ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        print(f"Text: {result['text']}\n")

if __name__ == "__main__":
    try:
        print("Opening source documents...")
        documents = open_source_documents()
        if not documents:
            print("No documents found.")
        else:
            print(f"Loaded {len(documents)} documents.")
        queries = [
            "What tickets are past their deadline?",
            "Can Jira integrate with Github?",
            "Can I use Jira for project management?",
            "Is code development status visible to project manager in Jira?",
            "Can I view stories in Jira like a Kanban board?",
        ]
        
        for query in queries:
            print(f"\nPerforming semantic search for query: '{query}'")
            semantic_search(query, documents, top_k=3)
     
    except Exception as e:
        print(f"An error occurred: {e}")