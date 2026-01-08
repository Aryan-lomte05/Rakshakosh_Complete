from enum import Enum

class ConversationPhase(str, Enum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


class ConversationState:
    def __init__(self):
        self.phase = ConversationPhase.INITIAL
        self.last_intent = None
