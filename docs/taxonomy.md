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
  label (they disagree surprisingly often).
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

## v1 dimensions

| Dimension | Kind | Values |
| --- | --- | --- |
| `change` (Design change) | one, ordinal | none, documentation, cosmetic, functional, significant, abandoned, undetermined (off-scale) |
| `change_type` (Kind of change) | several | naming, api_shape, privacy_security, scope_reduction, architecture, documentation, venue_or_process, none |
| `change_locus` (Where it landed) | several | explainer, spec_text, implementation, issue_filed, promised_only, none |
| `attribution` (Credit to the TAG) | one | tag_explicit, tag_implicit, shared, external, unclear, not_applicable |
| `verdict` (TAG verdict) | one | satisfied, satisfied_with_concerns, unsatisfied, recommends_against, deferred, withdrawn, no_verdict, not_a_review |

Definitions are in `taxonomy.py` and in the dashboard (hover a value).

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

AUDIT_RESULTS
