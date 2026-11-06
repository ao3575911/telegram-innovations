"""Small, explicit commitment-card state machine."""

import unicodedata
from dataclasses import dataclass, field

ACTIVE_STATES = ("OPEN", "READY")
TERMINAL_STATES = ("MET", "MISSED", "CANCELLED")


class DomainError(ValueError):
    """A deliberately safe message that may be shown to a Telegram user."""


@dataclass(frozen=True, slots=True)
class Card:
    id: str
    chat_id: int
    thread_id: int | None
    message_id: int | None
    title: str
    target: int
    deadline: int
    status: str
    count: int
    creator_key: str = field(repr=False)


def validate_card(title: str, target: int, deadline: int, now: int) -> None:
    if not title.strip() or len(title) > 200:
        raise DomainError("Use a title between 1 and 200 characters.")
    if any(unicodedata.category(char).startswith("C") for char in title):
        raise DomainError("Titles cannot contain control or invisible formatting characters.")
    if isinstance(target, bool) or not 2 <= target <= 100:
        raise DomainError("Choose a target between 2 and 100 people.")
    if not 60 <= deadline - now <= 7 * 24 * 3600:
        raise DomainError("Choose a deadline from 1 minute to 7 days from now.")
