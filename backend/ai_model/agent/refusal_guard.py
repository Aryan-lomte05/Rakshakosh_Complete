class RefusalGuard:

    def should_refuse(self, intent, retrieved_chunks) -> bool:
        if intent == "out_of_scope":
            return True

        if not retrieved_chunks or len(retrieved_chunks) == 0:
            return True

        return False

    def refusal_message(self) -> str:
        return (
            "I cannot answer this question based on the currently indexed documents. "
            "Please upload relevant material or ask a document-grounded question."
        )
