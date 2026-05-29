from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantIntent:
    action: str
    target: str
    message: str
