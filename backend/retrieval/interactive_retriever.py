#!/usr/bin/env python3
"""
Interactive Retrieval System - Compatible with aryan.py
Accepts user input and performs hybrid search + reranking + n±2 sliding window
"""

import time
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
import numpy as np
from backend.utils.logger import RakshaLogger

# LLM-based reranker (USP: Domain-agnostic reranking)
from backend.ai_model.rag.llm_reranker import LLMReranker

class InteractiveRetriever:
    """Interactive retrieval system with user input"""

    def __init__(self,
                 collection_name: str = "lollllll",  # Original collection with working data
                 embed_model: str = "BAAI/bge-base-en-v1.5",
                 rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 use_llm_reranker: bool = True):  # NEW: Toggle LLM-based reranking

        RakshaLogger.info("Retriever", "🔧 Initializing Interactive Retriever...")
        self.collection_name = collection_name
        self.client = QdrantClient(url="http://localhost:6333")
        self.use_llm_reranker = use_llm_reranker

        RakshaLogger.info("Retriever", "📥 Loading models...")
        self.embed_model = SentenceTransformer(embed_model)
        
        # Choose reranker based on flag
        if use_llm_reranker:
            RakshaLogger.info("Retriever", "🎯 Using LLM-based reranker (Phi3)")
            self.llm_reranker = LLMReranker()
            self.reranker = None  # Disable cross-encoder
        else:
            RakshaLogger.info("Retriever", "🎯 Using CrossEncoder reranker")
            self.reranker = CrossEncoder(rerank_model)
            self.llm_reranker = None

        # Load all chunks for BM25
        RakshaLogger.info("Retriever", "📚 Loading corpus for BM25...")
        
        self.chunks = []
        self.chunk_lookups = {}  # (doc_name, chunk_index) -> chunk
        corpus = []
        
        try:
            points, _ = self.client.scroll(
                collection_name=collection_name,
                limit=10000,  # Increased limit for more documents
                with_payload=True,
                with_vectors=False
            )

            for point in points:
                # Updated to match aryan.py payload structure
                chunk_data = {
                    "id": point.id,
                    "text": point.payload["text"],
                    "doc_name": point.payload["doc_name"],
                    "page_start": point.payload["page_start"],
                    "chunk_type": point.payload["chunk_type"],
                    "chunk_id": point.payload["chunk_id"],
                    "chunk_index": point.payload.get("chunk_index"),  # Extract chunk_index
                    "prev_chunk_id": point.payload.get("prev_chunk_id"),
                    "next_chunk_id": point.payload.get("next_chunk_id")
                }
                self.chunks.append(chunk_data)
                corpus.append(point.payload["text"])

                # Populate lookup map
                if chunk_data["chunk_index"] is not None:
                    self.chunk_lookups[(chunk_data["doc_name"], chunk_data["chunk_index"])] = chunk_data
                    
        except Exception as e:
            RakshaLogger.warning("Retriever", f"⚠️ Collection '{collection_name}' not found or empty. Starting fresh. Error: {e}")

        if not self.chunks:
            RakshaLogger.warning("Retriever", "⚠️ WARNING: Collection is empty. BM25 disabled. Upload documents to begin!")
            self.bm25 = None
        else:
            tokenized_corpus = [doc.lower().split() for doc in corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)

        RakshaLogger.success("Retriever", f"✅ Ready! Loaded {len(self.chunks)} chunks")

    def reload_corpus(self):
        """
        Hot-reload the BM25 corpus from Qdrant without restarting the server.
        Call this after new documents are ingested.
        """
        RakshaLogger.info("Retriever", "🔄 Hot-reloading corpus from Qdrant...")
        
        self.chunks = []
        self.chunk_lookups = {}
        corpus = []
        
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )

            for point in points:
                chunk_data = {
                    "id": point.id,
                    "text": point.payload["text"],
                    "doc_name": point.payload["doc_name"],
                    "page_start": point.payload["page_start"],
                    "chunk_type": point.payload["chunk_type"],
                    "chunk_id": point.payload["chunk_id"],
                    "chunk_index": point.payload.get("chunk_index"),
                    "prev_chunk_id": point.payload.get("prev_chunk_id"),
                    "next_chunk_id": point.payload.get("next_chunk_id")
                }
                self.chunks.append(chunk_data)
                corpus.append(point.payload["text"])

                if chunk_data["chunk_index"] is not None:
                    self.chunk_lookups[(chunk_data["doc_name"], chunk_data["chunk_index"])] = chunk_data
                    
        except Exception as e:
            RakshaLogger.warning("Retriever", f"⚠️ Failed to reload corpus: {e}")
            return False

        if self.chunks:
            tokenized_corpus = [doc.lower().split() for doc in corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            RakshaLogger.success("Retriever", f"✅ Hot-reload complete! Now have {len(self.chunks)} chunks")
            return True
        else:
            self.bm25 = None
            RakshaLogger.warning("Retriever", "⚠️ Corpus still empty after reload")
            return False

    def hybrid_search(self, query: str, top_k: int = 10, doc_filter: str = None) -> List[Dict]:
        """Hybrid search with optional document filter"""

        # Vector search
        query_vector = self.embed_model.encode(query, normalize_embeddings=True)

        search_params = {
            "collection_name": self.collection_name,
            "query": query_vector.tolist(),
            "limit": top_k * 2
        }

        # Add document filter if specified
        if doc_filter:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            search_params["query_filter"] = Filter(
                must=[FieldCondition(key="doc_name", match=MatchValue(value=doc_filter))]
            )

        # Use query_points instead of search
        vector_results = self.client.query_points(**search_params).points
        
        # 🔍 DEBUG: Vector search results
        print(f"[DEBUG] Vector search returned {len(vector_results)} results for: '{query[:50]}...'")

        # BM25 search (if available)
        if self.bm25:
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)

            # Apply doc filter to BM25
            if doc_filter:
                for i, chunk in enumerate(self.chunks):
                    if chunk["doc_name"] != doc_filter:
                        scores[i] = 0
            
            top_indices = np.argsort(scores)[::-1][:top_k * 2]
            # 🔍 DEBUG: BM25 results
            print(f"[DEBUG] BM25 top score: {scores[top_indices[0]] if len(top_indices) > 0 else 0:.4f}, corpus size: {len(self.chunks)}")
        else:
            scores = []
            top_indices = []
            print(f"[DEBUG] BM25 disabled (corpus empty or not loaded)")

        # Reciprocal Rank Fusion
        k = 60
        fused_scores = {}

        for rank, result in enumerate(vector_results, 1):
            fused_scores[result.id] = fused_scores.get(result.id, 0) + 1.0 / (k + rank)

        if self.bm25:
            for rank, idx in enumerate(top_indices, 1):
                if scores[idx] > 0:
                    chunk_id = self.chunks[idx]["id"]
                    fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1.0 / (k + rank)

        # Get top results
        seen = set()
        results = []

        for result in sorted(vector_results, key=lambda x: fused_scores.get(x.id, 0), reverse=True):
            if result.id not in seen:
                results.append({
                    "id": result.id,
                    "text": result.payload["text"],
                    "doc_name": result.payload["doc_name"],
                    "page_start": result.payload["page_start"],
                    "chunk_type": result.payload["chunk_type"],
                    "chunk_index": result.payload.get("chunk_index"),  # Include chunk_index in result
                    "score": fused_scores.get(result.id, 0)
                })
                seen.add(result.id)
                if len(results) >= top_k:
                    break

        return results

    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        """Rerank with LLM or CrossEncoder based on configuration"""

        if not results:
            return []

        # Use LLM-based reranker if enabled
        if self.use_llm_reranker and self.llm_reranker:
            return self.llm_reranker.rerank(query, results, top_k)
        
        # Fallback to CrossEncoder
        if self.reranker:
            pairs = [[query, r["text"]] for r in results]
            scores = self.reranker.predict(pairs)

            for result, score in zip(results, scores):
                result["rerank_score"] = float(score)

            reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
            return reranked[:top_k]
        
        # No reranker available, return as-is
        return results[:top_k]

    def expand_to_sliding_window(self, matched_chunks: List[Dict], window_size: int = 2) -> List[Dict]:
        """
        Expand matched chunks to n±window_size neighbors
        Args:
            matched_chunks: Top chunks from reranking (ordered by relevance)
            window_size: Number of neighbors on each side (default: 2 for n±2)
        Returns:
            Expanded chunks with MATCHED CHUNKS FIRST (highest relevance), then neighbors in order
        """

        expanded_ids = set()
        result_chunks = []
        neighbor_chunks = []

        # First: Add matched chunks in their rerank order (most relevant first)
        for matched in matched_chunks:
            if matched["id"] not in expanded_ids:
                matched["is_matched"] = True  # Mark as primary match
                result_chunks.append(matched)
                expanded_ids.add(matched["id"])

        # Second: Add neighbors around each matched chunk
        for matched in matched_chunks:
            chunk_index = matched.get("chunk_index")
            doc_name = matched["doc_name"]

            if chunk_index is None:
                continue

            # Expand window: n-2, n-1, n+1, n+2 (skip n itself, already added)
            for offset in range(-window_size, window_size + 1):
                if offset == 0:
                    continue  # Skip the matched chunk itself
                    
                target_index = chunk_index + offset
                neighbor = self.chunk_lookups.get((doc_name, target_index))
                
                if neighbor and neighbor["id"] not in expanded_ids:
                    neighbor["is_matched"] = False  # Mark as context
                    neighbor_chunks.append(neighbor)
                    expanded_ids.add(neighbor["id"])

        # Sort neighbors by document order for coherent reading
        neighbor_chunks = sorted(neighbor_chunks, key=lambda x: (x["doc_name"], x.get("chunk_index", 0)))
        
        # Final order: Matched chunks first (by relevance), then neighbors (by document order)
        return result_chunks + neighbor_chunks

    def search_with_window(self, query: str, top_k: int = 3, window_size: int = 2,
                          doc_filter: str = None, show_process: bool = True, skip_rerank: bool = False):
        """
        Complete search pipeline with sliding window expansion
        Args:
            query: Search query
            top_k: Number of top chunks to retrieve
            window_size: Sliding window size (2 = n±2)
            doc_filter: Optional document name filter
            show_process: Print debug info
            skip_rerank: If True, skip LLM reranking (faster, for RAW mode)
        Returns:
            dict with matched_chunks, expanded_chunks, and context string
        """

        start = time.time()

        if show_process:
            print(f"\n{'='*70}")
            print(f"🔍 QUERY: {query}")
            if skip_rerank:
                print(f"⚡ FAST MODE: LLM Reranking Skipped")
            if doc_filter:
                print(f"📄 Filter: {doc_filter}")
            print(f"{'='*70}\n")

        # Step 1: Hybrid search
        candidates = self.hybrid_search(query, top_k=15, doc_filter=doc_filter)

        if show_process:
            print(f"📊 Hybrid search: {len(candidates)} candidates")

        # Step 2: Rerank (or skip)
        if skip_rerank:
            # Just take top K from hybrid search
            matched_chunks = candidates[:top_k]
        else:
            matched_chunks = self.rerank(query, candidates, top_k=top_k)

        # Step 3: Expand to sliding window
        expanded_chunks = self.expand_to_sliding_window(matched_chunks, window_size=window_size)

        # Build context string for LLM
        context = "\n\n".join([
            f"[Doc: {c['doc_name']} | Page: {c['page_start']}]\n{c['text']}"
            for c in expanded_chunks
        ])

        elapsed = time.time() - start

        if show_process:
            print(f"🎯 Matched: {len(matched_chunks)} chunks")
            print(f"📏 Expanded: {len(expanded_chunks)} chunks (n±{window_size})")
            print(f"⏱️ Time: {elapsed:.3f}s\n")

        return {
            "matched_chunks": matched_chunks,
            "expanded_chunks": expanded_chunks,
            "context": context,
            "num_matched": len(matched_chunks),
            "num_expanded": len(expanded_chunks),
            "time": elapsed
        }

    def display_results(self, results: Dict):
        """Display search results"""

        matched_chunks = results["matched_chunks"]

        if not matched_chunks:
            print("❌ No results\n")
            return

        print(f"\n🎯 TOP MATCHED CHUNKS:\n")

        for i, chunk in enumerate(matched_chunks, 1):
            print(f"{'─'*70}")
            print(f"[{i}] Score: {chunk['rerank_score']:.4f} | {chunk['chunk_type']}")
            print(f" 📄 {chunk['doc_name']} | Page {chunk['page_start']}")
            print(f"{'─'*70}")
            preview = chunk['text'][:350] + "..." if len(chunk['text']) > 350 else chunk['text']
            print(preview)
            print()

        # Show expanded context info
        print(f"\n📄 EXPANDED CONTEXT INFO:")
        print(f" Chunk IDs: {[c['id'] for c in results['expanded_chunks']]}")
        print(f" Total chunks: {results['num_expanded']}")
        print(f" Total tokens: ~{sum(len(c['text'].split()) for c in results['expanded_chunks'])}")
        print(f" Context length: {len(results['context'])} characters\n")

    def interactive_mode(self):
        """Run in interactive mode with user input"""

        print(f"\n{'='*70}")
        print(f"🚀 INTERACTIVE RETRIEVAL MODE")
        print(f"{'='*70}")
        print(f"Type your questions (or 'quit' to exit)")
        print(f"{'='*70}\n")

        while True:
            try:
                # Get user input
                query = input("\n🔍 Enter your question: ").strip()

                if not query:
                    print("⚠️ Please enter a valid question\n")
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!\n")
                    break

                # Optional: Ask for document filter
                doc_filter = input("📄 Filter by document (press Enter to skip): ").strip()
                doc_filter = doc_filter if doc_filter else None

                # Perform search with sliding window
                results = self.search_with_window(
                    query=query,
                    top_k=3,
                    window_size=2,
                    doc_filter=doc_filter,
                    show_process=True
                )

                # Display results
                self.display_results(results)

                # Show final context preview
                print(f"\n{'='*70}")
                print(f"🤖 FINAL CONTEXT FOR LLM (Preview):")
                print(f"{'='*70}")
                print(results['context'][:500] + "...\n")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


    def get_unique_documents(self) -> List[str]:
        """
        Get list of all unique document names currently in the corpus.
        Using in-memory chunks list for speed.
        """
        if not self.chunks:
            return []
        return sorted(list(set(c["doc_name"] for c in self.chunks)))


def main():
    """Main function"""

    # Initialize retriever with collection name from aryan.py
    retriever = InteractiveRetriever(
        collection_name="lollllll",  # Original collection with working data
        embed_model="BAAI/bge-base-en-v1.5",
        rerank_model="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Run interactive mode
    retriever.interactive_mode()


if __name__ == "__main__":
    main()
