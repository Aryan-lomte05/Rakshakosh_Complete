class FollowUpResolver:
    """
    Resolves ambiguous follow-up queries.
    """

    def resolve(self, query: str, history: list) -> str:
        if not history:
            return query

        last_user_query = history[-1]["user"]

        # Simple but powerful
        return f"{last_user_query}. Follow-up question: {query}"
