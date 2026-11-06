# Concept exploration and selection

Scores are reasoned product hypotheses, not market research. All scores use 1–10; higher is better. For feasibility and cost, higher means easier to deliver or cheaper to operate.

| Dimension | Weight |
|---|---:|
| Originality and differentiation | 15% |
| Real-world utility and target audience | 20% |
| Telegram-native advantage | 15% |
| Technical feasibility and API fit | 15% |
| Privacy and security | 10% |
| Retention, sharing, network effects | 10% |
| Monetisation potential | 10% |
| Development complexity and operating cost | 5% |

| Concept | Originality | Utility | Telegram | Feasibility | Privacy | Retention | Revenue | Cost | Weighted /10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RallyPoint: conditional group commitment cards** | 8 | 9 | 10 | 9 | 8 | 9 | 7 | 9 | **8.70** |
| Pocket Arcade: asynchronous cooperative expeditions | 7 | 5 | 9 | 8 | 8 | 9 | 7 | 6 | 7.30 |
| QuietDrop: time-limited document collection inbox | 6 | 8 | 8 | 8 | 5 | 7 | 7 | 7 | 7.10 |
| ScamLens: user-submitted link safety triage | 7 | 9 | 8 | 5 | 6 | 7 | 8 | 4 | 7.10 |
| ClaimPass: selective-disclosure community membership | 9 | 6 | 7 | 4 | 6 | 6 | 6 | 3 | 6.15 |
| HandleWatch: public brand-name availability alerts | 5 | 6 | 6 | 3 | 7 | 6 | 7 | 5 | 5.55 |

The weighted score is `sum(score × weight) / 100`. This table compares different products, not a feature wishlist.

## Why each concept might matter

- **RallyPoint:** Organisers and small communities need a decision before committing effort. Shared messages and callbacks make participation lightweight. Each organiser introduces the utility to a whole group; recurring activities support repeat use. The main uncertainty is whether conditional commitment improves attendance relative to polls.
- **Pocket Arcade:** Telegram groups can play a turn-based expedition with shared inventory. Play supports retention and cosmetic purchases, but requires ongoing content and abuse-resistant economies. It is entertainment rather than the strongest demonstrated practical need.
- **QuietDrop:** Teachers and coordinators can request documents privately and see collection progress. Telegram file handling is a natural fit, but sensitive attachments, retention, scanning, and upload limits create a substantial privacy and operations burden.
- **ScamLens:** Community moderators could submit suspicious links for triage. It offers recurring utility, but useful results depend on external threat intelligence, safe URL fetching, freshness, and careful false-positive handling. It must never imply that an unflagged URL is safe.
- **ClaimPass:** Communities could accept a membership proof without exposing unrelated attributes. That requires a real credential issuer, a defined trust model, and cryptographic review. Telegram itself still knows accounts. A novel proof without an issuer ecosystem does not solve adoption.
- **HandleWatch:** Organisations want naming consistency. The Bot API cannot reliably enumerate arbitrary username availability or atomically transfer usernames. A useful version would depend on allowed external integrations or user-authorised clients, making it a poor Bot API-only MVP.

## Challenge and refinement

**“This is just a poll.”** Polls count preferences. RallyPoint states an explicit target, supports reversible participation, and records whether the target was met at a deadline. That distinction is useful only if groups care about a minimum team. The pilot should compare completed activities against the group's existing poll workflow.

**“A Join click means someone will turn up.”** It does not. The card says quorum is provisional until the deadline and the final result records commitments, not attendance. No financial escrow, enforcement, or attendance guarantee is implied.

**“Counts without names prevent coordination.”** Counts reduce public pressure but leave execution to the existing group conversation. A future opt-in roster may help some communities; it must not silently change existing privacy expectations.

**“Anonymous clicks are abuse-resistant.”** They are not anonymous, and one Telegram account is not one human. The MVP limits one active vote per account per card, caps creation, and rate-limits interactions. It does not solve Sybil attacks.

**“A Mini App or AI would make it better.”** Neither is required to create a pact or join it. Native command and callback interactions keep installation, permission review, and operating cost small.

The refined MVP contains one signature interaction, not calendars, payment deposits, reputation scores, AI scheduling, or custom cryptographic credentials. The next investment is a consented pilot that tests whether the interaction changes behaviour.
