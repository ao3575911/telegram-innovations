"""Per-card pseudonyms; not anonymity or proof of one human per account."""

import hashlib
import hmac


def participant_key(secret: bytes, card_id: str, user_id: int) -> str:
    """Bind a Telegram account to one card without persisting its raw ID.

    Keeping the server secret enables the operator to recompute these values.
    Different cards get different pseudonyms. Telegram itself knows the user.
    """
    value = f"rallypoint:participant:v1:{card_id}:{user_id}".encode("ascii")
    return hmac.new(secret, value, hashlib.sha256).hexdigest()
