# Build plan and review gates

| Stage | Deliverable | Acceptance gate |
|---|---|---|
| 1. Select | Weighted comparison and bounded product thesis | Signature feature feasible with Bot API alone |
| 2. Model | Pact states, scoped membership, SQLite schema | Duplicate joins and repeated creation cannot inflate counts |
| 3. Integrate | Async Telegram adapter and command/callback routing | Mocked end-to-end create, join, leave, cancel, and deadline flows |
| 4. Harden | Validation, permission checks, rate limits, redaction | Malformed payloads, cross-chat mutation, and token leaks rejected |
| 5. Operate | CLI, native install, systemd, logs, health | Clean install and local check commands succeed |
| 6. Package | Documentation, lockfile, licence, complete ZIP | Archive integrity and contents checked; limitations recorded |
| 7. Pilot | Live bot in consented test groups | Human Telegram acceptance checklist and useful repeat use |

Stages 1–6 describe the repository delivery. Exact executed checks and unresolved external validation appear in [TEST_REPORT.md](TEST_REPORT.md); a listed gate is not itself proof that a check ran. Stage 7 requires a real BotFather token and test group, which are intentionally absent from the archive.

Changes to participation semantics need matching domain tests and privacy documentation. Changes to Telegram delivery need failure/retry tests. Release reviews should focus on authorisation, persistent state, logging, and mismatches between displayed and authoritative status.
