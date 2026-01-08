from enum import Enum

class AgentIntent(str, Enum):
    INFORMATION = "information"
    FOLLOW_UP = "follow_up"
    COMPARISON = "comparison"
    SUMMARY = "summary"
    GREETING = "greeting"
    CHITCHAT = "chitchat"
    OUT_OF_SCOPE = "out_of_scope"
