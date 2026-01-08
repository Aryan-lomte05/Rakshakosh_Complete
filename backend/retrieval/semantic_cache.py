from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import time
import hashlib
from typing import Optional, Dict
from backend.utils.logger import RakshaLogger

class SemanticCache:
    """
    Semantic Caching Layer (USP 1.3).
    Caches queries and their responses in a vector database (Qdrant).
    If a new query is semantically similar (>0.95) to a cached one, return cached response.
    Latency: ~50ms vs ~3-5s for full RAG.
    """
    
    def __init__(self, collection_name="semantic_cache"):
        self.client = QdrantClient(host="localhost", port=6333)
        self.collection_name = collection_name
        # Using a lightweight model for cache lookup speed
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2') 
        self._init_collection()
        RakshaLogger.info("Cache", "🚀 Semantic Cache Initialized")

    def _init_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def lookup(self, query: str, threshold: float = 0.95) -> Optional[Dict]:
        """
        Check cache for semantically similar query.
        """
        try:
            vector = self.encoder.encode(query).tolist()
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=1,
                score_threshold=threshold
            )
            
            if results:
                hit = results[0]
                RakshaLogger.success("Cache", f"⚡ Cache HIT! (Score: {hit.score:.4f})")
                return hit.payload["response"]
            
            RakshaLogger.info("Cache", "❌ Cache MISS")
            return None
        except Exception as e:
            RakshaLogger.error("Cache", f"Lookup failed: {e}")
            return None

    def store(self, query: str, response: Dict):
        """
        Store query and response in cache.
        """
        try:
            vector = self.encoder.encode(query).tolist()
            doc_id = hashlib.sha256(query.encode()).hexdigest()
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=doc_id, # Using hash of query as ID
                        vector=vector,
                        payload={"query": query, "response": response, "timestamp": time.time()}
                    )
                ]
            )
        except Exception as e:
            RakshaLogger.error("Cache", f"Store failed: {e}")
