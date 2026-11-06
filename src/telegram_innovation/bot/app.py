"""Telegram interaction layer. All persistent mutations pass through Store."""

import hashlib
import hmac
import logging
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from telegram_innovation.core.config import Config
from telegram_innovation.integrations.telegram import TelegramAPI, TelegramError
from telegram_innovation.security.ratelimit import RateLimiter
from telegram_innovation.storage import Card, DomainError, Store

LOG = logging.getLogger(__name__)
HELP = (
    "RallyPoint · I’m in if enough others are.\n\n"
    "In a group: /pact 3 60m | Saturday park cleanup\n"
    "Join or Leave before the deadline. READY is provisional; the final count is sealed "
    "at the deadline. No attendance guarantee.\n\n"
    "/pacts — active cards here\n/cancel ID — owner or group administrator\n"
    "/privacy — data policy\n/settings — operating policy\n"
    "/forget — erase your participation records (private chat only)\n"
    "Cards show counts, not member lists. Telegram and this bot receive your account ID."
)
PRIVACY = (
    "RallyPoint stores card titles, group/chat and message IDs, deadlines, counts, and "
    "per-card keyed pseudonyms for participants and creators. Titles are necessary card "
    "content: do not include secrets. It does not store names, usernames, raw user IDs, "
    "or unrelated messages. Telegram still sees interactions; this is not anonymous. "
    "Private /forget removes your stored participation and creator pseudonyms, including "
    "active commitments; final aggregate counts stay unchanged. It cannot erase Telegram "
    "messages or operator backups. Deleted records may persist in SQLite/WAL or backups "
    "until overwritten/expired. Operators must protect their host and backups."
)


def integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def render(card: Card) -> tuple[str, dict[str, Any]]:
    deadline = datetime.fromtimestamp(card.deadline, UTC).strftime("%Y-%m-%d %H:%M UTC")
    label = {
        "OPEN": "Waiting for the group",
        "READY": "Target met · provisional",
        "MET": "Closed · target met",
        "MISSED": "Closed · target missed",
        "CANCELLED": "Cancelled",
    }[card.status]
    text = (
        f"RallyPoint · {label}\n\n{card.title}\n\n"
        f"{card.count}/{card.target} joined · Deadline {deadline}\n"
        "Join means: I intend to participate if the target is met. "
        "You can leave until the deadline. This is not a guarantee of attendance.\n"
        f"Card ID: {card.id}"
    )
    buttons = []
    if card.status in {"OPEN", "READY"}:
        buttons = [
            [
                {"text": "I’m in", "callback_data": f"v1:j:{card.id}"},
                {"text": "Leave", "callback_data": f"v1:l:{card.id}"},
            ],
            [
                {"text": "Refresh", "callback_data": f"v1:r:{card.id}"},
                {"text": "Cancel card", "callback_data": f"v1:c:{card.id}"},
            ],
        ]
    return text, {"inline_keyboard": buttons}


class Bot:
    def __init__(
        self, config: Config, store: Store, api: TelegramAPI, username: str = "rallypoint_bot"
    ):
        self.config = config
        self.store = store
        self.api = api
        self.username = username
        self.limiter = RateLimiter()
        self.global_limiter = RateLimiter(capacity=30, refill=15, max_keys=1)

    async def send(self, chat_id: int, text: str, thread_id: int | None = None) -> Any:
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "link_preview_options": {"is_disabled": True},
        }
        if thread_id is not None:
            params["message_thread_id"] = thread_id
        return await self.api.call("sendMessage", **params)

    async def reconcile(self) -> None:
        self.store.tick()
        for card in self.store.dirty_cards():
            text, markup = render(card)
            params: dict[str, Any] = {
                "chat_id": card.chat_id,
                "text": text,
                "reply_markup": markup,
                "link_preview_options": {"is_disabled": True},
            }
            try:
                if card.message_id is None:
                    if card.thread_id is not None:
                        params["message_thread_id"] = card.thread_id
                    result = await self.api.call("sendMessage", **params)
                    if not isinstance(result, dict) or not integer(result.get("message_id")):
                        raise TelegramError(0)
                    self.store.set_message(card.id, result["message_id"])
                else:
                    await self.api.call("editMessageText", message_id=card.message_id, **params)
                self.store.mark_clean(card.id)
            except TelegramError as exc:
                LOG.warning("", extra={"event": "card_delivery_failed", "error_code": exc.code})
                if exc.code in {400, 403}:
                    # Deleted messages / removed bot: do not hammer an unrecoverable destination.
                    self.store.mark_clean(card.id)
                else:
                    raise

    async def handle(self, update: dict[str, Any]) -> None:
        raw_update_id = update.get("update_id")
        if not isinstance(raw_update_id, int) or isinstance(raw_update_id, bool):
            return
        update_id: int = raw_update_id
        if update_id < self.store.get_offset():
            return
        started = time.monotonic()
        correlation = uuid.uuid4().hex[:12]
        callback = update.get("callback_query")
        message = update.get("message")
        event = callback if isinstance(callback, dict) else message
        if not isinstance(event, dict):
            self.store.set_offset(update_id + 1)
            return
        user = event.get("from")
        if (
            not isinstance(user, dict)
            or not integer(user.get("id"))
            or user["id"] <= 0
            or user.get("is_bot")
        ):
            self.store.set_offset(update_id + 1)
            return
        user_id = user["id"]
        key = hmac.new(self.config.secret, str(user_id).encode(), hashlib.sha256).hexdigest()
        if not self.global_limiter.allow("global") or not self.limiter.allow(key):
            LOG.warning("", extra={"event": "rate_limited", "correlation": correlation})
            self.store.set_offset(update_id + 1)
            return
        if isinstance(callback, dict):
            await self._callback(callback, user_id)
        elif isinstance(message, dict):
            await self._message(message, user_id, update_id)
        self.store.set_offset(update_id + 1)
        LOG.info(
            "",
            extra={
                "event": "update_handled",
                "correlation": correlation,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "operation": "callback" if callback else "message",
            },
        )

    async def _admin(self, chat_id: int, user_id: int) -> bool:
        try:
            result = await self.api.call("getChatMember", chat_id=chat_id, user_id=user_id)
        except TelegramError as exc:
            if exc.code in {400, 403}:
                return False
            raise
        return isinstance(result, dict) and result.get("status") in {"creator", "administrator"}

    async def _cancel(self, card_id: str, user_id: int, chat_id: int) -> None:
        try:
            self.store.cancel(card_id, user_id, chat_id)
        except DomainError:
            if chat_id < 0 and await self._admin(chat_id, user_id):
                self.store.cancel(card_id, user_id, chat_id, is_admin=True)
            else:
                LOG.warning("", extra={"event": "authorization_denied", "operation": "cancel"})
                raise DomainError(
                    "Only the card creator or a verified group administrator can cancel."
                ) from None

    async def _callback(self, callback: dict[str, Any], user_id: int) -> None:
        query_id = callback.get("id")
        if not isinstance(query_id, str) or len(query_id) > 256:
            return
        answer = "Updated."
        try:
            data = callback.get("data")
            message = callback.get("message")
            match = (
                re.fullmatch(r"v1:([jlrc]):([a-f0-9]{16,32})", data)
                if isinstance(data, str)
                else None
            )
            if not match or not isinstance(message, dict) or message.get("date") == 0:
                raise DomainError("This button is unavailable. Open the original group card.")
            chat = message.get("chat")
            if not isinstance(chat, dict) or not integer(chat.get("id")):
                raise DomainError("Invalid card context.")
            card = self.store.get(match[2])
            if (
                card is None
                or card.chat_id != chat["id"]
                or card.message_id != message.get("message_id")
            ):
                raise DomainError("Use the original card in its original group.")
            if match[1] in {"j", "l"}:
                self.store.vote(card.id, user_id, match[1] == "j", card.chat_id)
            elif match[1] == "c":
                await self._cancel(card.id, user_id, card.chat_id)
            else:
                self.store.tick()
                current = self.store.get(card.id)
                if current is not None:
                    text, markup = render(current)
                    await self.api.call(
                        "editMessageText",
                        chat_id=card.chat_id,
                        message_id=card.message_id,
                        text=text,
                        reply_markup=markup,
                    )
            await self.reconcile()
        except DomainError as exc:
            answer = str(exc)
            LOG.info("", extra={"event": "callback_rejected"})
        await self.api.call("answerCallbackQuery", callback_query_id=query_id, text=answer[:200])

    async def _message(self, message: dict[str, Any], user_id: int, update_id: int) -> None:
        text = message.get("text")
        chat = message.get("chat")
        if (
            not isinstance(text, str)
            or not text.startswith("/")
            or not isinstance(chat, dict)
            or not integer(chat.get("id"))
        ):
            return
        # Anonymous administrator/channel sender identities cannot own cards.
        if message.get("sender_chat"):
            return
        chat_id = chat["id"]
        private = chat.get("type") == "private"
        thread = message.get("message_thread_id")
        thread = thread if integer(thread) else None
        command, _, arguments = text.partition(" ")
        name, _, mention = command.partition("@")
        if mention and mention.lower() != self.username.lower():
            return
        LOG.info(
            "",
            extra={
                "event": "command",
                "operation": name
                if name
                in {
                    "/start",
                    "/help",
                    "/pact",
                    "/pacts",
                    "/cancel",
                    "/forget",
                    "/diagnostics",
                    "/privacy",
                    "/settings",
                }
                else "unknown",
            },
        )
        try:
            if name in {"/start", "/help"}:
                await self.send(chat_id, HELP, thread)
            elif name == "/privacy":
                await self.send(
                    chat_id,
                    PRIVACY + f" Terminal cards expire after {self.config.retention_days} days.",
                    thread,
                )
            elif name == "/settings":
                await self.send(
                    chat_id,
                    f"Retention: {self.config.retention_days} days after deadline. "
                    "Counts are public; member lists are never published. No analytics service. "
                    "Policy is set by the operator. /privacy",
                    thread,
                )
            elif name == "/pact":
                if chat.get("type") not in {"group", "supergroup"}:
                    raise DomainError("Create cards in a group. Then use /pact 3 60m | Your plan")
                match = re.fullmatch(
                    r"\s*(\d{1,3})\s+(\d{1,5})([mhd])\s*\|\s*(.{1,200})\s*", arguments
                )
                if not match:
                    raise DomainError(
                        "Use /pact 3 60m | Your plan "
                        "(2–100 people, 1m–7d, title up to 200 characters)."
                    )
                duration = int(match[2]) * {"m": 60, "h": 3600, "d": 86400}[match[3]]
                self.store.create(
                    update_id,
                    chat_id,
                    user_id,
                    match[4].strip(),
                    int(match[1]),
                    int(time.time()) + duration + 1,
                    thread,
                )
                await self.reconcile()
            elif name == "/pacts":
                self.store.tick()
                cards = self.store.active(chat_id)
                summary = (
                    "Active cards (up to 10):\n"
                    + "\n".join(f"{c.id} · {c.count}/{c.target} · {c.title}" for c in cards)
                    if cards
                    else "No active cards here. /pact 3 60m | Your plan"
                )
                await self.send(chat_id, summary, thread)
            elif name == "/cancel":
                if not re.fullmatch(r"[a-f0-9]{16,32}", arguments.strip()):
                    raise DomainError("Use /cancel CARD_ID from the card in this group.")
                await self._cancel(arguments.strip(), user_id, chat_id)
                await self.reconcile()
            elif name == "/forget":
                if not private:
                    raise DomainError("For privacy, send /forget in a private chat with this bot.")
                count = self.store.forget(user_id)
                await self.send(
                    chat_id,
                    f"Removed your participation/ownership records from {count} cards. "
                    "Active commitments are withdrawn. Final counts and Telegram messages remain.",
                )
                await self.reconcile()
            elif name == "/diagnostics":
                if not private or user_id not in self.config.admin_ids:
                    LOG.warning(
                        "", extra={"event": "authorization_denied", "operation": "diagnostics"}
                    )
                    raise DomainError(
                        "Diagnostics require a configured operator in a private chat."
                    )
                stats = self.store.health()
                if stats["database"] != "ok":
                    raise RuntimeError("Database integrity check failed")
                await self.send(
                    chat_id, "Database healthy. " + ", ".join(f"{k}: {v}" for k, v in stats.items())
                )
            else:
                await self.send(chat_id, "Unknown command. /help", thread)
        except DomainError as exc:
            await self.send(chat_id, str(exc), thread)
