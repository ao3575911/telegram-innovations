# Interfaces and platform limits

## External API

RallyPoint uses Telegram's HTTPS Bot API with a token obtained from BotFather. It polls for message and callback-query updates; no inbound HTTP listener or public DNS is required. The adapter isolates HTTP transport, response parsing, API failure categories, and retry-after behaviour from product rules.

The application uses these standard Bot API operations:

| Method | Purpose |
|---|---|
| `getMe` | Validate bot identity and determine username |
| `getWebhookInfo` | Refuse polling when an existing webhook is configured |
| `setMyCommands` | Register the public command menu at startup |
| `getUpdates` | Receive updates with a persisted offset |
| `sendMessage` | Publish help, replies, and initial pact cards |
| `editMessageText` | Reconcile existing card text and buttons |
| `answerCallbackQuery` | Acknowledge button interactions |
| `getChatMember` | Verify administrator cancellation authority |

The bot never uses MTProto, a user session, contact scraping, username transfers, or arbitrary account lookups. `getChatMember` has platform restrictions; non-creator cancellation must fail safely if the bot cannot verify the requesting administrator. A private `/start` does not permit the bot to inspect other chats or contact arbitrary users.

## Commands and callbacks

Commands and validation are specified in [COMMANDS.md](COMMANDS.md). Callback payloads follow `v1:<action>:<card_id>` with actions `j`, `l`, `r`, and `c`. They fit Telegram's callback-data byte limit. The payload contains no user ID or secret; knowing it confers no authority. Unsupported versions, malformed IDs, and absent or inaccessible messages are rejected safely.

IDs supplied by Telegram are parsed as integers and used only where the operation requires them. User-supplied title text is sent as plain text with no HTML or Markdown parse mode, so Telegram does not interpret it as markup. The adapter sends JSON payloads over verified TLS and never logs the token-bearing URL.

## Storage contract

The SQLite store exposes card creation, lookup, explicit Join/Leave intent, cancellation, message binding, dirty-card reconciliation, deadline settlement, forgetting, retention, active-card listing, health, and persistent polling offsets. Domain failures are safe user messages; infrastructure failures are operational events.

Creation is idempotent by update ID. Membership changes are idempotent by desired state. Cancellation and settlement are terminal transitions. Database migrations are versioned and applied on startup. An existing schema newer than the application must not be silently interpreted as compatible.

This is an internal Python interface, not a public REST service. There are no external API keys beyond the bot token and no third-party data processors added by the application itself.

## Delivery guarantees

Stored changes survive restart once their transaction commits. Telegram display is eventually reconciled and can lag during outages or rate limits. `sendMessage` has no general application idempotency key; duplicate outbound cards are possible after an ambiguous send or crash. The application cannot remove stale forwarded copies, guarantee Telegram delivery, guarantee immediate closure while offline, or prove that a committed member attended.
