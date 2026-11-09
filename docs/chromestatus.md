# Linking reviews to Chrome features and blink-dev intents

Research notes, 2026-11-09. Code: `tagimpact/chromestatus.py`, `build.py`.

## Where the data is

Blink's launch process asks every Intent to Prototype / Ship email on
[blink-dev](https://groups.google.com/a/chromium.org/g/blink-dev/) to link the TAG review. Those emails
are generated from [chromestatus.com](https://chromestatus.com) feature entries
([GoogleChrome/chromium-dashboard](https://github.com/GoogleChrome/chromium-dashboard)), so the structured
form of "blink-dev threads that link a TAG review" is the feature entries themselves:

- `GET https://chromestatus.com/api/v0/features?num=500&start=N` returns full feature objects (after a
  `)]}'` XSSI prefix line). 3,591 features on 2026-11-09. The `q=` search syntax didn't match any of
  the TAG fields we tried (`tag_review_status=*`, `tag_review:github`), so we page through everything.
- `tag_review`: free text where owners paste the review URL (or explain why there is none: "N/A —
  minor spec-compliance update", "It's already in the HTML spec").
- `tag_review_status`: Pending (2,194), Not applicable (1,058), Issues addressed (302), Issues open (37).
  "Pending" is the default and is rarely updated, so it says little.
- `stages[]`: each stage has a `stage_type` and an `intent_thread_url` (the blink-dev thread). Stage
  types from `internals/core_enums.py`: shipping = 160 (new feature), 260 (existing standard), 360
  (web developer facing change / PSA), 460 (deprecation); prototyping = 120, 220, 320, 410; origin
  trials = 150, 151, 250, 251, 450, 451. Milestones are on the stage (`desktop_first`, …).

## Linking

1. **Feature → review**: regex `github.com/w3ctag/design-reviews/issues/(\d+)` on `tag_review`
   (519 reviews), then on every other string field (a further 9).
2. **Review → feature**: regex `chromestatus.com/feature/(\d+)` on the issue body; the review
   template asks for the chromestatus entry. Only the URL is extracted; nothing reads the prose.
3. The **Intent to Ship thread** is the first shipping stage's `intent_thread_url`, kept only if it is
   an `https://groups.google.com/a/chromium.org/` URL.

Result: **643 of 1,212** issues link to at least one feature; 528 from the feature side, the rest from
issue bodies. 386 linked reviews have an Intent to Ship URL.

## Gaps

- Only 607 of 2,549 shipping stages carry an `intent_thread_url`. Features from before the 2022
  stage redesign mostly don't, so older Intent to Ship threads aren't linked. Filling them would need
  searching the blink-dev archive for each feature name or for design-reviews URLs (Google Groups has
  no public API; scraping it would be untrusted bulk text, so it would go through the sandbox too).
- A feature can link several reviews (e.g. an early and a later review), and a review several
  features (one review covering several launch entries). The dashboard lists all.
- Non-Chromium reviews (Mozilla, WebKit, W3C WG specs) have no chromestatus entry by design: about
  half of all reviews.
