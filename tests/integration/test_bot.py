"""Exercise complete command and callback flows without Telegram credentials."""

import copy
import json
import time
from itertools import count
from pathlib import Path
from typing import Any

import pytest

from telegram_innovation.bot.app import Bot
from telegram_innovation.core.config import Config
from telegram_innovation.storage import Store

GROUP = -1001234567
OWNER = 101
CALLBACK_UPDATES = count(2000)
FIXTURES = Path(__file__).parents[1] / "fixtures" / "updates.json"


class RecordingAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.next_message = 200
        self.admins: set[int] = set()

    async def call(self, method: str, **params: Any) -> Any:
        self.calls.append((method, params))
        if method == "sendMessage":
            self.next_message += 1
            return {"message_id": self.next_message, "chat": {"id": params["chat_id"]}}
        if method == "getChatMember":
            return {"status": "administrator" if params["user_id"] in self.admins else "member"}
        if method == "editMessageText":
            return {"message_id": params["message_id"]}
        return True

    def sent_text(self) -> str:
        return "\n".join(
            str(p.get("text", "")) for method, p in self.calls if method == "sendMessage"
        )


@pytest.fixture
def harness(tmp_path):
    store = Store(str(tmp_path / "test.sqlite3"), b"s" * 32)
    api = RecordingAPI()
    config = Config(
        token="123456:" + "a" * 35,
        secret=b"s" * 32,
        database_path=str(tmp_path / "test.sqlite3"),
        admin_ids=frozenset({999}),
    )
    bot = Bot(config, store, api, username="rallypoint_bot")
    yield bot, store, api
    store.close()


def message(text: str, user: int = OWNER, chat: int = GROUP, update: int = 900):
    return {
        "update_id": update,
        "message": {
            "message_id": update,
            "from": {"id": user, "is_bot": False, "first_name": "Not stored"},
            "chat": {"id": chat, "type": "private" if chat > 0 else "supergroup"},
            "text": text,
        },
    }


def callback(card, action: str, user: int = 202, chat: int = GROUP, msg: int = 900):
    return {
        "update_id": next(CALLBACK_UPDATES),
        "callback_query": {
            "id": f"query-{action}-{user}",
            "from": {"id": user, "is_bot": False},
            "data": f"v1:{action}:{card.id}",
            "message": {
                "message_id": msg,
                "date": int(time.time()),
                "chat": {"id": chat, "type": "supergroup"},
            },
        },
    }


def seed(store):
    card = store.create(1, GROUP, OWNER, "Community repair café", 2, int(time.time()) + 3600)
    store.set_message(card.id, 900)
    store.mark_clean(card.id)
    return store.get(card.id)


@pytest.mark.asyncio
async def test_create_from_fixture_and_replay_preserves_single_card(harness):
    bot, store, api = harness
    update = json.loads(FIXTURES.read_text())["create_group"]
    await bot.handle(update)
    await bot.reconcile()
    assert len(store.active(GROUP)) == 1
    card = store.active(GROUP)[0]
    assert card.title == "Repair café on Saturday"
    assert card.target == 3
    assert card.message_id is not None
    assert "Repair café" in api.sent_text()
    await bot.handle(copy.deepcopy(update))
    await bot.reconcile()
    assert len(store.active(GROUP)) == 1


@pytest.mark.asyncio
async def test_join_leave_and_refresh_update_the_existing_card(harness):
    bot, store, api = harness
    card = seed(store)
    await bot.handle(callback(card, "j", user=202))
    await bot.handle(callback(card, "j", user=202))
    assert store.get(card.id).count == 1
    await bot.handle(callback(card, "j", user=203))
    assert store.get(card.id).status == "READY"
    await bot.handle(callback(card, "l", user=202))
    assert store.get(card.id).status == "OPEN"
    await bot.handle(callback(card, "r", user=203))
    await bot.reconcile()
    assert any(method == "answerCallbackQuery" for method, _ in api.calls)
    assert any(method == "editMessageText" for method, _ in api.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_chat,bad_message", [(GROUP - 1, 900), (GROUP, 901)])
async def test_callback_is_bound_to_original_chat_and_message(harness, bad_chat, bad_message):
    bot, store, _ = harness
    card = seed(store)
    await bot.handle(callback(card, "j", chat=bad_chat, msg=bad_message))
    assert store.get(card.id).count == 0


@pytest.mark.asyncio
async def test_unauthorized_member_cannot_cancel_but_owner_can(harness):
    bot, store, _ = harness
    card = seed(store)
    await bot.handle(callback(card, "c", user=202))
    assert store.get(card.id).status == "OPEN"
    await bot.handle(callback(card, "c", user=OWNER))
    assert store.get(card.id).status == "CANCELLED"


@pytest.mark.asyncio
async def test_verified_group_administrator_can_cancel(harness):
    bot, store, api = harness
    card = seed(store)
    api.admins.add(202)
    await bot.handle(message(f"/cancel {card.id}", user=202))
    assert store.get(card.id).status == "CANCELLED"
    assert any(method == "getChatMember" for method, _ in api.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [400, 403])
async def test_unverifiable_group_administrator_is_denied_without_blocking_queue(
    harness, monkeypatch, code
):
    from telegram_innovation.integrations.telegram import TelegramError

    bot, store, api = harness
    card = seed(store)
    original_call = api.call

    async def blocked_lookup(method, **params):
        if method == "getChatMember":
            raise TelegramError(code)
        return await original_call(method, **params)

    monkeypatch.setattr(api, "call", blocked_lookup)
    update = message(f"/cancel {card.id}", user=202)
    await bot.handle(update)
    assert store.get(card.id).status == "OPEN"
    assert store.get_offset() == update["update_id"] + 1
    assert "verified group administrator" in api.sent_text()


@pytest.mark.asyncio
async def test_forget_private_only_and_erases_own_membership(harness):
    bot, store, _ = harness
    card = seed(store)
    store.vote(card.id, OWNER, True, GROUP)
    await bot.handle(message("/forget"))
    assert store.get(card.id).count == 1
    await bot.handle(message("/forget", chat=OWNER, update=901))
    assert store.get(card.id).count == 0


@pytest.mark.asyncio
async def test_private_onboarding_and_group_only_creation(harness):
    bot, store, api = harness
    start = json.loads(FIXTURES.read_text())["private_start"]
    await bot.handle(start)
    assert api.sent_text()
    await bot.handle(message("/pact 2 1h | Alone", chat=OWNER))
    assert store.active(OWNER) == []


@pytest.mark.asyncio
async def test_targeted_command_and_topics_preserved(harness):
    bot, store, _ = harness
    update = message("/pact@rallypoint_bot 2 1h | Makers night")
    update["message"]["message_thread_id"] = 52
    await bot.handle(update)
    await bot.reconcile()
    assert store.active(GROUP)[0].thread_id == 52
    await bot.handle(message("/pact@another_bot 2 1h | Wrong bot", update=901))
    assert len(store.active(GROUP)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text", ["/pact", "/pact 0 1h | Invalid", "/pact 3 0m | Invalid", "/pact 2 1h | " + "x" * 201]
)
async def test_invalid_create_never_creates_card(harness, text):
    bot, store, _ = harness
    await bot.handle(message(text))
    assert not store.active(GROUP)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update",
    [
        {},
        {"update_id": 1},
        {"update_id": 1, "message": {}},
        {"update_id": 1, "callback_query": {"id": "q", "data": "v1:j:nope"}},
    ],
)
async def test_incomplete_updates_are_ignored_without_mutation(harness, update):
    bot, store, _ = harness
    await bot.handle(update)
    assert not store.active(GROUP)


@pytest.mark.asyncio
async def test_diagnostics_do_not_disclose_to_unconfigured_user_or_group(harness):
    bot, _, api = harness
    await bot.handle(message("/diagnostics", user=OWNER, chat=OWNER))
    unauthorized = api.sent_text()
    api.calls.clear()
    await bot.handle(message("/diagnostics", user=999, chat=GROUP, update=901))
    group_output = api.sent_text()
    api.calls.clear()
    await bot.handle(message("/diagnostics", user=999, chat=999, update=902))
    privileged = api.sent_text()
    assert privileged
    assert privileged != unauthorized
    assert privileged != group_output
    assert str(GROUP) not in privileged
    assert "123456:" not in privileged


@pytest.mark.asyncio
async def test_rate_limited_card_edit_keeps_cursor_and_replay_does_not_double_vote(
    harness, monkeypatch
):
    from telegram_innovation.integrations.telegram import TelegramError

    bot, store, api = harness
    card = seed(store)
    update = callback(card, "j")
    original_call = api.call
    failures = 1

    async def fail_once(method, **params):
        nonlocal failures
        if method == "editMessageText" and failures:
            failures -= 1
            raise TelegramError(429, 3)
        return await original_call(method, **params)

    monkeypatch.setattr(api, "call", fail_once)
    with pytest.raises(TelegramError) as error:
        await bot.handle(update)
    assert error.value.retry_after == 3
    assert store.get(card.id).count == 1
    assert store.get_offset() <= update["update_id"]
    await bot.handle(update)
    assert store.get(card.id).count == 1
    assert store.get_offset() == update["update_id"] + 1
    assert not store.dirty_cards()


@pytest.mark.asyncio
async def test_terminal_card_removes_buttons_and_rejects_late_join(harness):
    bot, store, api = harness
    card = seed(store)
    store.vote(card.id, 202, True, GROUP)
    store.vote(card.id, 203, True, GROUP)
    store.tick(now=card.deadline)
    await bot.reconcile()
    final_edits = [params for method, params in api.calls if method == "editMessageText"]
    assert final_edits[-1]["reply_markup"] == {"inline_keyboard": []}
    await bot.handle(callback(card, "j", user=204))
    assert store.get(card.id).count == 2
    assert store.get(card.id).status == "MET"


@pytest.mark.asyncio
async def test_html_like_titles_are_sent_without_markup_interpretation(harness):
    bot, store, api = harness
    await bot.handle(message('/pact 2 1h | <a href="https://example.org">Meet</a>'))
    assert len(store.active(GROUP)) == 1
    posts = [params for method, params in api.calls if method == "sendMessage"]
    assert '<a href="https://example.org">Meet</a>' in posts[-1]["text"]
    assert "parse_mode" not in posts[-1]
    assert posts[-1]["link_preview_options"]["is_disabled"] is True
