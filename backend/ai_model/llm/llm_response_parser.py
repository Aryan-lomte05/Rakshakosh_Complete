class LLMResponseParser:
    """
    Parses raw LLM output into structured fields.
    """

    def parse(self, raw_text: str) -> dict:
        return {
            "answer": raw_text.strip(),
            "confidence_hint": self._estimate_confidence(raw_text)
        }

    def _estimate_confidence(self, text: str) -> float:
        length = len(text.split())
        if length > 120:
            return 0.9
        if length > 60:
            return 0.8
        return 0.7
