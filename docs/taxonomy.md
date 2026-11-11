# Impact taxonomy

How we label whether a design review changed the feature. Code: `tagimpact/taxonomy.py` (v1),
`discover.py`, `classify.py`, `audit.py`.

## Starting point

The brief proposed one scale: **none**, **cosmetic** (naming etc.), **functional** (a meaningful
change), **significant** (a different architecture), **blocked** (not pursued because of TAG
feedback) and **specification** (meaningful spec-level changes that don't directly change
implementation), noting these may be independent and not exhaustive.

## Discovery pass (Fable, 2026-11-09)

`python3 -m tagimpact.discover` sent 30 threads to Fable (`claude-fable-5-1`) in one sandboxed call
(291k characters, 6.6 minutes, $4.04). The threads were stratified by era (before 2019 / 2019–22 /
2023+), resolution label and thread length, with at least 3 comments. Fable proposed five
dimensions, labelled every sample thread, and listed pitfalls. The raw output is in
`data/private/discovery/` (model text shaped by untrusted threads: read it as data).

What changed from the seed scale:

- **"Blocked" split in two.** Several sampled proposals were abandoned for reasons the thread
  doesn't credit to the TAG (other browsers, product decisions, no reason given). So *abandoned* is
  a value of the change scale, and a separate **attribution** dimension says whether the TAG gets
  credit. *Blocked* = abandoned + TAG credited.
- **"Docs only" added below cosmetic.** The commonest outcome is the requester updating the
  explainer, the security & privacy questionnaire or considerations sections. Without its own value
  it gets over-labelled as functional.
- **"Specification" became a place, not a size.** A new **where it landed** dimension (explainer,
  spec text, implementation, issue filed, promised only), multi-select. A spec-level change is
  `spec_text`, at whatever size.
- **Kind of change** (multi-select): naming, API shape, privacy/security mitigation, scope cut,
  architecture, documentation, venue/process.
- **TAG verdict** as its own dimension, from the closing TAG comment rather than the Resolution
  label. Dropped in v2: the TAG's own Resolution labels are the verdict (below).
- **Undetermined** for threads that imply a change without showing it, or where evidence was cut.

### Pitfalls Fable listed (now in the classifier prompt)

1. `[TAG]`/`[REQUESTER]` tags were sometimes wrong (this led to the membership windows in
   [latency.md](latency.md)).
2. Labels and closing text disagree ("timed out" vs "no major outstanding concerns").
3. Explainer and questionnaire edits get over-labelled as functional.
4. Promised is not landed.
5. Renames and redesigns often come from the WG, other implementers or security teams; credit the
   TAG only with explicit evidence.
6. Withdrawal is not blocking.
7. Changes before the first TAG feedback don't count.
8. Truncated threads hide evidence: prefer undetermined.
9. Open threads get no verdict, even when TAG members voiced strong views.
10. TAG-internal outcomes (template changes) are not feature impact.
11. Shipping despite a TAG objection still gets an unsatisfied or with-concerns verdict.

Pitfalls 2, 9 and 11 were about the verdict and left the prompt with it in v2.

## v2 dimensions

| Dimension | Kind | Values |
| --- | --- | --- |
| `change` (Design change) | one, ordinal | none, documentation, cosmetic, functional, significant, abandoned, undetermined (off-scale) |
| `change_type` (Kind of change) | several | naming, api_shape, privacy_security, scope_reduction, architecture, documentation, venue_or_process, none |
| `change_locus` (Where it landed) | several | explainer, spec_text, implementation, issue_filed, promised_only, none |
| `attribution` (Credit to the TAG) | one | tag_explicit, tag_implicit, shared, external, unclear, not_applicable |

Definitions are in `taxonomy.py` and in the dashboard (hover a value).

**v1 → v2 (2026-11-11)** only removed the `verdict` dimension and its two prompt guidance lines.
The other definitions are unchanged, so the v1 labels (all 1,212 issues, and the audit runs) stay in
use (`taxonomy.ACCEPTED_VERSIONS`); `validate` drops their verdicts. Nothing was relabelled.

## TAG verdict: the Resolution labels, not a model

The TAG marks its verdict with a `Resolution:` label (descriptions from GitHub, in
`taxonomy.RESOLUTIONS`): satisfied, validated (early reviews it broadly supports), satisfied with
concerns, ambivalent, unsatisfied, object, lack of consensus, decline, too early, too late, out of
scope, timed out, withdrawn, overtaken. `latency.resolution` reads it; the dashboard shows it as
"TAG resolution (GitHub label)". `python3 -m scripts.resolution_check` compares it with v1's model
verdicts. Findings on 1,102 concluded feature/spec reviews (2026-11-11):

- **Coverage is the big gap.** 452 (41%) have no Resolution label. The labels started in May 2019
  (satisfied and unsatisfied first; satisfied with concerns in May 2021; decline in Dec 2023;
  object in Nov 2024), and old reviews weren't relabelled: none of the 2013–16 reviews have one,
  4 of 70 from 2017, 14 of 110 from 2018. About 90% of reviews opened since 2021 are labelled.
  Verdict statistics are therefore really 2019-onwards statistics.
- **Six issues have two labels**, mostly applied at the same moment: #512 and #569 satisfied + timed
  out, #711 and #773 satisfied with concerns + timed out, #1169 ambivalent + validated, and #1041 too
  early, then timed out a year later. A label stating the TAG's position beats a procedural one
  (timed out, too early); otherwise the one applied last wins. So #512/#569 count as satisfied,
  #711/#773 as with concerns, #1169 as validated, #1041 as timed out.
- **Where a label exists, the model agreed 75% of the time, and never contradicted it outright**:
  no review labelled satisfied or validated was read as unsatisfied or recommends-against, or the
  reverse. Most disagreement is the satisfied / with-concerns line: 77 reviews labelled
  satisfied were read as "with concerns" (the TAG closes as satisfied while leaving notes; about 1
  in 5, both before and after the with-concerns label existed). Other mismatches are naming:
  object (added Nov 2024) vs recommends-against, decline vs no verdict, overtaken vs deferred.
  The label is the TAG's own call, so it wins.

Among labelled reviews: satisfied 63%, satisfied with concerns 12%, unsatisfied 6%, timed out 5%,
decline 5%, then ambivalent, validated, withdrawn, overtaken and too early at about 2% each.

Reviews the TAG labelled **unsatisfied were the likeliest to change the feature with TAG credit**
(54%, n=39), against 36% for satisfied (n=410) and 33% for satisfied with concerns (n=78). Timed out,
decline, withdrawn and overtaken reviews rarely did (9–20%). Unsatisfied reviews are where the TAG
pushes hardest, and requesters move partway even when the TAG stays unsatisfied.

**Derived "TAG impact"** (`taxonomy.outcome`), which the dashboard leads with:

| Outcome | Rule |
| --- | --- |
| No change | change = none |
| Changed, not credited | changed, attribution external / unclear / not_applicable |
| Docs/cosmetic, TAG credited | documentation or cosmetic, attribution tag_explicit / tag_implicit / shared |
| Functional+, TAG credited | functional or significant, same attribution |
| Blocked | abandoned, TAG credited (alone or shared) |
| Abandoned, other reason | abandoned, not TAG credited |
| Undetermined | change = undetermined |

## Classifier

One Haiku call per issue (`classify.py`), same jail and schema rules as everything else. The thread
is rendered by `render.thread_text`: body up to 12k characters, each comment up to 4k, whole thread up
to 90k, dropping comments from the middle first (the request and the conclusion matter most). The
reply carries each dimension, a reason (cut to 300 characters and stripped of URLs and markup at
build time) and up to 5 cited comment numbers. Cost on 2026-11-09: about $0.0025 a thread.

## Audit

`python3 -m tagimpact.audit label` has Fable label a stratified sample of 40 feature/spec reviews with
the exact classifier prompt; `report` compares them with Haiku's labels and writes
`data/public/audit.json`, which the dashboard quotes. Agreement with a stronger model isn't accuracy,
but it shows which dimensions a small model can be trusted on.

### Results (2026-11-09, 40 reviews, Fable cost $6.69)

These and the model comparison below were run with v1, which still had a model-inferred verdict.
The verdict figures are kept as a record; the dashboard now uses the Resolution labels instead.

| Dimension | Agreement |
| --- | --- |
| Design change | 80% exact, 91% within one step of the scale (off-scale values excluded) |
| Kind of change | 0.83 mean Jaccard |
| Where it landed | 0.78 mean Jaccard |
| Credit to the TAG | 73% exact |
| TAG verdict | 63% exact |
| "Changed, TAG credited" (yes/no) | 92.5%; rate 32.5% (Fable) vs 35% (Haiku) |

Design change confusion (rows Fable, columns Haiku), on-diagonal counts: none 16/17, documentation
6/7, cosmetic 3/4, functional 3/5, significant 1/2, abandoned 3/3, undetermined 0/2. Haiku's misses
are mostly one step either way, with no systematic lean up or down the scale, and it never used
`undetermined` where Fable did.

### Would Sonnet or Opus do better? (2026-11-10)

Same 40 reviews, same prompt, schema and sandbox (`audit label --model sonnet|opus`), plus a second
Haiku run to measure Haiku's own run-to-run noise. `python3 -m tagimpact.audit compare` prints the
table. Agreement with Fable:

| Model | Design change | Within one step | TAG impact | Changed & TAG credited (y/n) | Credit to TAG | Verdict | $/review |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku (production run) | 82% | 94% | 80% | 92% | 72% | 65% | 0.001 |
| Haiku (second run) | 75% | 91% | 80% | 92% | 70% | 60% | 0.002 |
| Sonnet | 80% | 94% | 75% | 92% | 70% | 80% | 0.028 |
| Opus | 85% | 100% | 82% | 88% | 80% | 75% | 0.061 |

All four put the "changed, TAG credited" rate at 35–40%, against Fable's 32%.

- **On the headline measures (design change, TAG impact, changed-and-credited) the bigger models
  aren't measurably better.** The spread between them (75–85%) is no wider than Haiku's own
  run-to-run spread (82% vs 75%; the two Haiku runs agree with each other on design change for 90%
  of reviews). With 40 reviews one review is 2.5 points, and the 95% interval on 80% is about ±12
  points.
- **The TAG verdict is where size helps**: Sonnet 80% and Opus 75%, against Haiku's 60–65% (about 4–8
  more reviews out of 40). Opus also does somewhat better on credit to the TAG (80% vs 70–72%).
- **The models disagree with each other about as much as with Fable** (Opus vs Haiku 78% on design
  change). Much of the disagreement is ambiguity in the threads, not one model's mistakes. Fable is
  a reference, not ground truth.
- **Cost:** relabelling all 1,212 issues would cost about $34 with Sonnet or $73 with Opus, against
  about $3 with Haiku. The 40-review runs cost $1.13 and $2.42.

Recommendation: keep Haiku for the impact labels. (The verdict, where bigger models helped, is now
read from the Resolution labels, so no model is needed for it.) Better value than a bigger model: a
larger audit sample or a human-labelled gold set, to tighten the error bars, and majority votes over
a few cheap Haiku runs to cut its run-to-run noise.

Reading: the headline numbers (how often a review changed the feature, and whether the TAG gets
credit) are stable across models. The fine split between functional and its neighbours is less
reliable. Use the per-review detail view to spot-check before quoting fine-grained counts.

## Dashboard

The dashboard charts only TAG-caused change: the derived TAG impact plus the descriptive dimensions.
The raw `change` dimension (whoever caused it) is still labelled and feeds TAG impact, and shows in
the per-review detail, but has no chart of its own. The page also shows the full classifier prompt
(system prompt and user message with the thread elided), exported by `build.py` from `classify.py`.
