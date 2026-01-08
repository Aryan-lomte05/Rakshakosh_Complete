"""
LLM-Based Reranker using Ollama (Phi3) - OPTIMIZED BATCH VERSION
Uses a single LLM call to rank all chunks at once.
Target: < 5 seconds for reranking.
"""
import re
from typing import List, Dict
from backend.ai_model.llm.ollama_client import OllamaClient
from backend.utils.logger import RakshaLogger


class LLMReranker:
    """
    Reranks retrieval results using LLM-based relevance scoring.
    OPTIMIZED: Single LLM call for all chunks (batch ranking).
    """
    
    def __init__(self, model_name: str = "phi3"):
        self.llm = OllamaClient(model_name=model_name)
        RakshaLogger.info("LLMReranker", f"🎯 Initialized LLM Reranker (Batch Mode)")
    
    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Rerank chunks using a SINGLE batched LLM call.
        Much faster than individual scoring.
        """
        if not chunks:
            return []
        
        # Limit to top 10 candidates to keep prompt small
        candidates = chunks[:10]
        
        RakshaLogger.info("LLMReranker", f"🔄 Batch reranking {len(candidates)} chunks...")
        
        # Build batch prompt
        chunk_list = ""
        for i, chunk in enumerate(candidates):
            # Truncate each chunk to 200 chars for speed
            text_preview = chunk["text"][:200].replace("\n", " ")
            chunk_list += f"[{i+1}] {text_preview}\n\n"
        
        prompt = f"""Rank these passages by how well they DEFINE or EXPLAIN the concept in the query.

RANKING PRIORITY:
1. Direct definitions ("X is..." or "X means...")  
2. Conceptual explanations of how something works
3. Practical examples or use cases
4. Code snippets (lowest priority unless query asks for code)

QUERY: {query}

PASSAGES:
{chunk_list}

OUTPUT: Just the passage numbers from best to worst, separated by commas.
RANKING:"""
        
        try:
            RakshaLogger.debug("LLMReranker", "🧠 Sending batch to LLM...")
            response = self.llm.generate(prompt)
            print(f"[LLM Ranking Response]: {response.strip()}")
            
            if "Error: Timeout" in response:
                RakshaLogger.warning("LLMReranker", "⚠️ Reranking timed out. Using original order.")
                # Fallback handled below
                return candidates[:top_k]
            
            # Parse ranking from response
            numbers = re.findall(r'\d+', response)
            ranking = []
            for num_str in numbers:
                idx = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= idx < len(candidates) and idx not in ranking:
                    ranking.append(idx)
            
            # Build reranked list
            reranked = []
            for rank, idx in enumerate(ranking[:top_k]):
                chunk = candidates[idx].copy()
                chunk["llm_score"] = 1.0 - (rank * 0.1)  # Assign score based on rank position
                chunk["rerank_score"] = chunk["llm_score"]  # Alias for compatibility
                reranked.append(chunk)
            
            # If parsing failed, fall back to original order
            if not reranked:
                RakshaLogger.warning("LLMReranker", "⚠️ Ranking parse failed, using original order")
                for i, chunk in enumerate(candidates[:top_k]):
                    chunk["llm_score"] = 0.5
                    chunk["rerank_score"] = 0.5
                    reranked.append(chunk)
            
            RakshaLogger.success("LLMReranker", f"✅ Batch rerank complete! Top chunk idx: {ranking[0] if ranking else 'N/A'}")
            return reranked
            
        except Exception as e:
            RakshaLogger.warning("LLMReranker", f"⚠️ Reranking failed: {e}")
            # Fallback: return original order
            return candidates[:top_k]


# Quick test
if __name__ == "__main__":
    reranker = LLMReranker()
    
    test_query = "What is the hook mechanism?"
    test_chunks = [
        {"text": "ReadSector() and WriteSector() are API functions for disk operations.", "doc_name": "test", "page_start": 1, "id": "1"},
        {"text": "The hook mechanism permits us to intercept and alter the flow of messages in the OS.", "doc_name": "test", "page_start": 2, "id": "2"},
        {"text": "Windows hooks can be put to many good uses.", "doc_name": "test", "page_start": 3, "id": "3"},
    ]
    
    results = reranker.rerank(test_query, test_chunks)
    print("\nResults:")
    for i, r in enumerate(results):
        print(f"{i+1}. [Score: {r.get('llm_score', 0):.2f}] {r['text'][:50]}...")
