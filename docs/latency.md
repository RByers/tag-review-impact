# Review latency

How long a design review takes, net of time the TAG spent waiting on the requesters.
Code: `tagimpact/latency.py`, tests: `tests/test_latency.py`.

## Definitions

- **Opened**: the issue's `createdAt`.
- **Concluded**: the issue's final `closedAt`. Reopened-and-reclosed issues run to the last close.
  Comments after the close don't count. Open issues run to the build time and are shown as open
  (right-censored); the dashboard's default view excludes them.
- **Total**: concluded − opened.
- **Waiting on requesters**: the union (overlaps counted once) of
  1. **label intervals**: while `Progress: pending external feedback` or `Progress: pending editor
     update` was on the issue. The TAG applies these when it is waiting for the requester or editors;
     a label still on at close runs to the close;
  2. **turn intervals**: from a TAG comment to the next comment, when that next comment is from the
     requester side. The TAG had spoken, and the next move was the requester's.
- **TAG time**: total − waiting on requesters.
- **First TAG comment**: days from opening to the first TAG-side comment.

## Who is "TAG side"

GitHub doesn't record TAG membership history, so it is inferred from structure:

- Logins with at least 3 **triage actions** on issues they didn't open: closing, reopening,
  assigning, or adding/removing a label in the TAG's own namespaces (`Progress:`, `Resolution:`,
  `Topic:`, `Venue:`, `Review type:`, `Priority:`, `Missing:`, `Mode:`, …). Only people with triage
  rights can do these. They count as TAG side from 60 days before their first action to 60 days after
  their last, because membership runs in terms and people file reviews before or after serving.
- Org members (`authorAssociation` MEMBER/OWNER) with fewer actions: TAG side around their actions
  if they have any, else always (early members from before labels were used).
- Bots (`w3c-tag-bot`, `w3cbot`, `*[bot]`) are ignored.
- The issue author is always requester side on their own issue.

That gives 39 logins (2026-11-09), including W3C staff, which is intended: they act for the TAG.

### Why the windows and the label filter

The first version counted anyone who ever triaged as TAG forever. The Fable discovery pass
([taxonomy.md](taxonomy.md)) flagged threads where a requester-side person was tagged `[TAG]`:

- a current TAG member's comments on reviews they filed or championed years before joining;
- `chrishtr`, whose "triage" was mostly the `chromium-high-priority` label, applied as a Chrome
  stakeholder;
- `domenic`, a 2015 member and still an org member, speaking for features in 2022.

Windows and the namespace filter fix the first and second cases (chrishtr keeps a 2022–2023 window
from `Progress:` label changes). The domenic case is fixed by giving org members with any actions a
window around them.

## Results (2026-11-09, 1,151 concluded issues, all kinds)

| Measure | Median | p25 | p75 | p90 |
| --- | --- | --- | --- | --- |
| Total days | 117 | 48 | 285 | 511 |
| TAG days | 83 | 34 | 174 | 348 |
| Waiting on requesters | 1.4 | 0 | 58 | 205 |
| Label-based waiting | 0 | 0 | 24 | 169 |
| Turn-based waiting | 0.6 | 0 | 14 | 59 |
| Days to first TAG comment | 27.5 | 11 | 69 | 105 |

Waiting is concentrated in a minority of reviews: most have little, while a quarter waited about two
months or more. Reviews have been getting faster since 2023; median total days by year opened: 2023
132, 2024 91, 2025 56, 2026 41. Recent years are partly censored: long 2026 reviews are still open.
`python3 -m scripts.latency_stats` reproduces these numbers.

## Limits

- **A third party ends a wait.** Anyone not TAG side counts as the requester side, so a drive-by
  comment after a TAG question ends the waiting interval early. That understates waiting.
- **A TAG comment isn't always a question.** "Thanks, we'll discuss at our F2F" followed by a
  requester's "any update?" counts as waiting even though the ball was in the TAG's court. That
  overstates waiting. Telling the two apart needs reading the comment (a later model pass could
  mark which TAG comments ask the requester for something).
- **Labels depend on TAG practice**, which varied over the years; early reviews rarely used the
  pending labels.
- **Closing isn't always concluding.** Some reviews are closed and then discussed further, or closed
  in a batch long after the substance ended (timed out, stalled).
