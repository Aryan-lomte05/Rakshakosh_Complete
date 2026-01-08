from langchain_ollama import ChatOllama
import json
from typing import List
from backend.utils.logger import RakshaLogger

class QueryDecomposer:
    """
    Decomposes complex queries into simpler sub-queries (USP 1.1).
    Used for "Multi-hop Reasoning" where a single retrieval might miss context.
    """
    
    def __init__(self, model_name="llama3.1:8b"):
        self.llm = ChatOllama(model=model_name, temperature=0)
        RakshaLogger.info("Agent", "🧠 Query Decomposer Initialized")

    def decompose(self, query: str) -> List[str]:
        """
        Breaks a complex query into sub-queries.
        Returns a list of strings (including the original query).
        """
        prompt = f"""
        You are an expert AI Assistant Planner.
        Break down the following user query into 2-3 distinct, simple sub-queries that would match documents.
        Focus on splitting distinct concepts (e.g., "Compare X and Y" -> "What is X?", "What is Y?").
        
        User Query: "{query}"
        
        Output ONLY a JSON array of strings. No markdown, no explanation.
        Example: ["What is X?", "What is Y?"]
        """
        
        try:
            response = self.llm.invoke(prompt).content.strip()
            # Clean potential markdown
            response = response.replace("```json", "").replace("```", "")
            sub_queries = json.loads(response)
            
            if isinstance(sub_queries, list):
                # Always keep the original query for context
                if query not in sub_queries:
                    sub_queries.append(query)
                RakshaLogger.success("Agent", f"🧩 Decomposed: {sub_queries}")
                return sub_queries
            else:
                return [query]
                
        except Exception as e:
            RakshaLogger.warning("Agent", f"Decomposition failed, using original: {e}")
            return [query]
