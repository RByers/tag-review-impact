# Initial findings (2026-11-10)

First pass over all 1,212 issues in w3ctag/design-reviews; reproduce with
`python3 -m scripts.latency_stats` and `python3 -m scripts.impact_stats`. Impact numbers are Haiku
labels (taxonomy v1), audited against Fable on 40 reviews ([taxonomy.md](taxonomy.md)): treat
them as estimates good to a few points at the headline level, and spot-check before quoting
fine-grained counts.

Scope: 1,102 concluded feature and spec reviews. Charter reviews (about 45) and questions/meta issues
(about 14) are excluded; 61 reviews are still open.

## Latency

- Median **127 days** open to close, of which a median **86 days** are TAG time (waiting on requesters
  removed). The first TAG comment comes after a median 28 days.
- Waiting on requesters is skewed: the median review waits 2 days, but a quarter wait two months or
  more.
- Reviews have sped up: median TAG time 186 days for reviews opened 2013–16, 98 for 2017–19, 75 for
  2020–22, 66 for 2023–26 (the last partly censored by still-open reviews).
- Reviews that led to a functional or larger TAG-credited change took longer (median 127 TAG days)
  than ones with no change (71). Substantive feedback takes more rounds.

## Impact

| TAG impact | Reviews | Share |
| --- | --- | --- |
| No change | 589 | 53% |
| Docs/cosmetic change, TAG credited | 234 | 21% |
| Functional or significant change, TAG credited | 119 | 11% |
| Changed, credited elsewhere or unclear | 63 | 6% |
| Undetermined | 52 | 5% |
| Abandoned, other reason | 26 | 2% |
| Blocked (abandoned, TAG credited) | 19 | 2% |

- About **a third of reviews (32%) led to a change the thread credits to the TAG**. Most of those are
  documentation: explainer sections, privacy and security considerations, use cases.
- The commonest kinds of change are documentation (370 reviews), API shape (121), privacy/security
  mitigations (85), naming (79) and scope cuts (79). Architecture changes are rare (38).
- Changes landed in explainers (226) and spec text (172) far more than in implementation (22).
  **199 reviews end with a promised change** the thread never shows landing.
- Verdicts, from the TAG's own Resolution labels (2026-11-11; [taxonomy.md](taxonomy.md)): 41% of
  reviews have none, almost all from before the labels started in May 2019. Of the 650 labelled:
  satisfied 63%, satisfied with concerns 12%, unsatisfied 6%, timed out 5%, decline 5%, the rest
  2% or less each.
- **Reviews the TAG labelled unsatisfied changed the most**: 54% led to a TAG-credited change,
  against 36% for satisfied and 33% for satisfied with concerns. Timed out, declined, withdrawn and
  overtaken reviews rarely did (9–20%).
- **Chrome-linked reviews change more**: 40% of reviews linked from chromestatus led to a
  TAG-credited change, against 22% of the rest. That fits Blink's launch process, which asks owners
  to respond to TAG feedback before shipping. It could also reflect what kinds of features get
  chromestatus entries.
- By era, the TAG-credited change rate rose from 25% (2013–16) to 37% (2020–22), and is 30% for
  2023–26, which is partly incomplete.

## Caveats

- "No change" includes reviews where the TAG was satisfied from the start; a review that finds
  nothing wrong is still doing its job. Impact here means changes, not value.
- Attribution comes from the thread alone. Changes made off-thread (in spec repos, at meetings) and
  never mentioned on the issue are invisible, so these are lower bounds.
- See [latency.md](latency.md) for the limits of the waiting model.
