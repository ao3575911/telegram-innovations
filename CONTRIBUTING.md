# Contributing

RallyPoint is an early public MVP. Changes should preserve its single commitment card interaction, explicit Bot API limits, and privacy model. Open an issue describing the user problem and proposed behaviour before adding a new product surface.

For code changes, use Python 3.12+ and `uv`. Run `./scripts/check.sh` before submitting a pull request. Add tests for changes to state transitions, authorisation, transport retries, migrations, or data retention. Include the specific Telegram API method and failure mode when changing delivery behaviour. Update the relevant documentation when commands or privacy semantics change.

Do not include real bot tokens, account IDs from real users, chat content, database copies, or personal data in issues, pull requests, test fixtures, or logs. Use synthetic fixtures. For security defects, contact the repository maintainer privately through an available GitHub private reporting channel; do not publish a working exploit or secret in a public issue.

The maintainers may defer features that require bot administrator privileges, external services, new cryptographic claims, or permanent personal data until their user benefit and trust model are demonstrated.
