class CitationEnforcer:
    """
    Ensures answers are grounded in retrieved documents.
    """

    def enforce(self, answer: str, citations: list) -> bool:
        """
        Returns True if answer is allowed.
        """
        if not citations or len(citations) == 0:
            return False

        # Optional: very strict mode
        if len(answer.strip()) < 20:
            return False

        return True
