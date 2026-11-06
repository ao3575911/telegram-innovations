# Commands and interaction reference

Use `/command@YourBotUsername` in a busy group when needed. Commands addressed to a different bot are ignored. All durations are relative to creation; displayed cutoffs use UTC.

| Command | Scope | Behaviour |
|---|---|---|
| `/start` | Private or group | Explain the product and basic use |
| `/help` | Private or group | Show commands and examples |
| `/pact 3 60m \| River cleanup` | Group/supergroup | Create a pact needing 3 accounts within 60 minutes |
| `/pacts` | Current chat | List current active pacts |
| `/cancel <card_id>` | Originating chat | Cancel as creator or verified group administrator |
| `/privacy` | Private or group | Explain stored data, visibility, and forgetting |
| `/forget` | Private only | Erase caller's retained participant and creator references |
| `/settings` | Private or group | Display deployment policy; read only |
| `/diagnostics` | Private operator only | Return aggregate operational health |

`/pact` requires an integer target from 2 through 100, a duration from 1 minute through 7 days, and a nonempty title up to 200 characters. Use suffixes `m`, `h`, or `d`, for example `30m`, `2h`, or `1d`. Control characters and malformed syntax are rejected. The bot does not automatically add the creator's vote. At most 20 pacts can be active in a chat.

Examples:

```text
/pact 4 2h | Four people for tonight's study sprint
/pact 6 1d | Weekend neighbourhood cleanup
/pacts
/cancel <id shown by the bot>
```

## Buttons

| Button | Payload action | Effect |
|---|---|---|
| Join | `v1:j:<id>` | Set caller's membership to present |
| Leave | `v1:l:<id>` | Set caller's membership to absent |
| Refresh | `v1:r:<id>` | Read/reconcile current authoritative state |
| Cancel | `v1:c:<id>` | Cancel after creator/admin authorisation |

Join and Leave are separate intents so repeated delivery cannot accidentally toggle a vote. The button is labelled “I’m in” in the app. Count and target are public, but names are not displayed. Group membership does not entitle a user to another member's vote history.

## Status meanings

| Status | Meaning |
|---|---|
| OPEN | Below target and still accepting changes |
| READY | Target currently reached; participation can still change |
| MET | Deadline passed with the target met |
| MISSED | Deadline passed below target |
| CANCELLED | Creator or administrator cancelled before settlement |

READY is provisional. MET records the count at the cutoff and does not establish actual attendance. Users can stop future participation with Leave before closure or request personal-reference removal with private `/forget` later.

The bot registers this command menu at startup:

```text
start - How RallyPoint works
pact - Create: 3 60m | Your plan
pacts - Active group cards
cancel - Cancel a card by its ID
privacy - Data and privacy policy
forget - Erase your participation records privately
settings - Operator policy
help - Commands and examples
```
