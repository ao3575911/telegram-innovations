"""HTTP boundary tests use real httpx serialization with a fake Telegram server."""

import json

import httpx
import pytest

from telegram_innovation.integrations.telegram import TelegramAPI, TelegramError

TOKEN = "123456:" + "A" * 35


@pytest.mark.asyncio
async def test_success_serializes_json_and_returns_result():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        api = TelegramAPI(TOKEN, client=client)
        assert await api.call("sendMessage", chat_id=-100, text="Hello") == {"message_id": 42}
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {"chat_id": -100, "text": "Hello"}
    assert requests[0].url.path.endswith("/sendMessage")


@pytest.mark.asyncio
@pytest.mark.parametrize("retry,expected", [(7, 7), (0, 1), (999999, 3600), ("bad", None)])
async def test_rate_limit_is_bounded_and_never_auto_retries_send(retry, expected):
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            429,
            json={
                "ok": False,
                "error_code": 429,
                "description": TOKEN,
                "parameters": {"retry_after": retry},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(TelegramError) as failure:
            await TelegramAPI(TOKEN, client).call("sendMessage", chat_id=123, text="secret content")
    assert calls == 1
    assert failure.value.code == 429
    assert failure.value.retry_after == expected
    assert TOKEN not in str(failure.value)
    assert "secret content" not in str(failure.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(502, text="upstream failure"),
        httpx.Response(200, json=[]),
        httpx.Response(403, json={"ok": False, "error_code": 403, "description": TOKEN}),
    ],
)
async def test_invalid_and_error_responses_are_safe(response):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises(TelegramError) as failure:
            await TelegramAPI(TOKEN, client).call("getMe")
    assert TOKEN not in str(failure.value)
    assert "upstream failure" not in str(failure.value)


@pytest.mark.asyncio
async def test_timeout_hides_token_bearing_url():
    def respond(request):
        raise httpx.ReadTimeout(str(request.url), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(TelegramError) as failure:
            await TelegramAPI(TOKEN, client).call("getUpdates")
    assert failure.value.code == 0
    assert TOKEN not in str(failure.value)


@pytest.mark.asyncio
async def test_repeated_edit_is_success_but_other_bad_requests_fail():
    def respond(request):
        return httpx.Response(
            400,
            json={
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message is not modified",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        api = TelegramAPI(TOKEN, client)
        assert await api.call("editMessageText", chat_id=1, message_id=2, text="Existing") is True
        with pytest.raises(TelegramError):
            await api.call("sendMessage", chat_id=1, text="Existing")
