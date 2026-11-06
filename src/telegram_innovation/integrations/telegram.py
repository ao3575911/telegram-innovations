"""Small Bot API boundary. Never expose URL/token or server descriptions in errors."""

from typing import Any

import httpx


class TelegramError(Exception):
    def __init__(self, code: int, retry_after: int | None = None):
        super().__init__(f"Telegram API request failed (code {code})")
        self.code = code
        self.retry_after = retry_after


class TelegramAPI:
    def __init__(self, token: str, client: httpx.AsyncClient | None = None):
        self._base = "https://api.telegram.org/bot" + token + "/"
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0))
        self._owned = client is None

    async def call(self, method: str, **params: Any) -> Any:
        try:
            response = await self._client.post(self._base + method, json=params)
        except httpx.HTTPError:
            raise TelegramError(0) from None
        try:
            body = response.json()
        except ValueError:
            raise TelegramError(response.status_code) from None
        if not isinstance(body, dict):
            raise TelegramError(response.status_code)
        if response.status_code >= 400 or body.get("ok") is not True:
            code = body.get("error_code", response.status_code)
            code = code if isinstance(code, int) else response.status_code
            parameters = body.get("parameters")
            retry = parameters.get("retry_after") if isinstance(parameters, dict) else None
            retry = max(1, min(retry, 3600)) if isinstance(retry, int) else None
            # Telegram rejects an edit whose contents already match. Reconciliation succeeded.
            description = body.get("description", "")
            if (
                method == "editMessageText"
                and code == 400
                and isinstance(description, str)
                and "message is not modified" in description.lower()
            ):
                return True
            raise TelegramError(code, retry)
        return body.get("result")

    async def close(self) -> None:
        if self._owned:
            await self._client.aclose()
