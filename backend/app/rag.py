import json
import os
import logging
from backend.app.config import Config

logger = logging.getLogger("rag")

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_SEMANTIC_LIBS = True
except ImportError:
    logger.warning("FAISS or SentenceTransformers not installed. RAG will fall back to simple keyword matching.")
    HAS_SEMANTIC_LIBS = False

class StadiumRAG:
    def __init__(self):
        self.documents = []
        self.model = None
        self.index = None
        self.load_documents()
        
        if HAS_SEMANTIC_LIBS:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.initialize_index()
                logger.info("Semantic RAG loaded with FAISS & all-MiniLM-L6-v2.")
            except Exception as e:
                logger.error(f"Error initializing semantic index: {e}. Falling back to keyword search.")
                self.model = None
                self.index = None

    def load_documents(self):
        if os.path.exists(Config.STADIUM_FACTS_PATH):
            with open(Config.STADIUM_FACTS_PATH, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
        else:
            logger.error(f"Stadium facts JSON not found at {Config.STADIUM_FACTS_PATH}")
            self.documents = []

    def initialize_index(self):
        if not self.documents:
            return
        
        texts = [f"{doc['title']}: {doc['content']}" for doc in self.documents]
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")
        
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Cosine Similarity
        self.index.add(embeddings)

    def retrieve(self, query: str, top_k: int = 3):
        if not self.documents:
            return []
            
        # If semantic index is active, use FAISS
        if self.model and self.index:
            try:
                query_embedding = self.model.encode([query], show_progress_bar=False)
                query_embedding = np.array(query_embedding).astype("float32")
                faiss.normalize_L2(query_embedding)
                
                distances, indices = self.index.search(query_embedding, top_k)
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < len(self.documents) and idx >= 0:
                        doc = self.documents[idx]
                        results.append({
                            "id": doc["id"],
                            "category": doc["category"],
                            "title": doc["title"],
                            "content": doc["content"],
                            "similarity": float(dist)
                        })
                return results
            except Exception as e:
                logger.error(f"Semantic search failed: {e}. Falling back to keyword matching.")

        # Fallback keyword matching (simple TF-IDF-like word overlap)
        query_words = set(query.lower().split())
        scored_docs = []
        for doc in self.documents:
            text = f"{doc['title']} {doc['content']}".lower()
            score = sum(1 for word in query_words if word in text)
            scored_docs.append((score, doc))
        
        # Sort by overlap score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, doc in scored_docs[:top_k]:
            results.append({
                "id": doc["id"],
                "category": doc["category"],
                "title": doc["title"],
                "content": doc["content"],
                "similarity": float(score)
            })
        return results

# Singleton helper
_rag_instance = None

def get_rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = StadiumRAG()
    return _rag_instance
