"""
Retriever Bridge - Enhanced with Query Expansion
"""
from backend.retrieval.interactive_retriever import InteractiveRetriever

class RetrieverBridge:

    def __init__(self):
        self.retriever = InteractiveRetriever()

    def expand_query(self, query: str) -> str:
        """
        Expand short queries for better semantic matching.
        Example: "the hook mechanism" → "hook mechanism definition explanation Windows programming"
        """
        query_lower = query.lower().strip()
        expansions = []
        
        # Add definitional terms for short "what is X" type queries
        if len(query.split()) <= 4:
            expansions.append("definition")
            expansions.append("explanation")
            expansions.append("what is")
        
        # Domain-specific expansions
        programming_keywords = ["hook", "dll", "api", "function", "pointer", "memory", "stack"]
        if any(kw in query_lower for kw in programming_keywords):
            expansions.append("programming")
            expansions.append("mechanism")
        
        # Combine original query with expansions
        if expansions:
            return f"{query} {' '.join(expansions)}"
        return query

    def retrieve(self, query, conversation_history, intent, mode="raw"):
        # Expand query for better retrieval
        enriched_query = self.expand_query(query)
        
        # Add conversation context for follow-ups
        if intent == "follow_up" and conversation_history:
            enriched_query = conversation_history[-1]["user"] + " " + enriched_query

        print(f"[Query Expansion] Original: '{query}' → Expanded: '{enriched_query}'")
        
        # Skip LLM Reranking for RAW mode (Speed Optimization)
        skip_rerank = (mode == "raw")

        results = self.retriever.search_with_window(
            query=enriched_query,
            top_k=5,  # Increased from 3 to 5 for better coverage
            window_size=2,
            show_process=False,
            skip_rerank=skip_rerank
        )

        return results["expanded_chunks"]

