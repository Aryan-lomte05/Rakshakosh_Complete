from .agent_types import AgentIntent

class IntentClassifier:

    def classify(self, query: str, has_history: bool) -> AgentIntent:
        q = query.lower().strip()
        
        # Greetings
        if q in ["hi", "hello", "hey", "greetings", "good morning", "good evening", "hi there", "hello rakshakosh"]:
            return AgentIntent.GREETING
            
        # Identity / Chitchat
        if any(x in q for x in ["who are you", "what are you", "your name", "are you ai", "are you a bot", "how are you"]):
            return AgentIntent.CHITCHAT

        if any(x in q for x in ["compare", "difference", "vs"]):
            return AgentIntent.COMPARISON

        if has_history and any(x in q for x in ["and", "what about", "also", "that"]):
            return AgentIntent.FOLLOW_UP

        if any(x in q for x in ["summarize", "summary"]):
            return AgentIntent.SUMMARY

        if any(x in q for x in ["opinion", "guess", "outside", "general knowledge"]):
            return AgentIntent.OUT_OF_SCOPE

        return AgentIntent.INFORMATION
