"""UI session state (SDD 13.3, 13.5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionState:
    authenticated: bool = False
    language: str = "fr"
    theme: str = "light"
    current_project_id: int | None = None
    replace_token: str | None = None
    messages: list[tuple[str, str]] = field(default_factory=list)  # (type, text)

    def push_message(self, message_type: str, text: str) -> None:
        self.messages.append((message_type, text))

    def drain_messages(self) -> list[tuple[str, str]]:
        messages = self.messages
        self.messages = []
        return messages
