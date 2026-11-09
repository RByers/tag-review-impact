# Design

Goal: estimate the impact W3C TAG design reviews have had on web platform features. That means two
questions per review, answered for every issue in
[w3ctag/design-reviews](https://github.com/w3ctag/design-reviews/issues):

1. **How long did the review take**, not counting time the TAG spent waiting on the requesters?
2. **Did it change the feature**, how much, and does the thread credit the TAG?

Plus a link from each review to the Chrome feature it reviewed, and to that feature's blink-dev Intent
to Ship thread where there is one.

## Pipeline

```
GitHub GraphQL ──fetch_issues──▶ data/private/issues/<n>.json ─┐   (untrusted text; never read in bulk
chromestatus API ─chromestatus fetch─▶ data/private/chromestatus.json │    by a tool-enabled agent)
                                                                │
           ┌───────────── structure only ───────────────────────┤
           ▼                                                     ▼
  latency.compute (Python)                   render.thread_text ─▶ llm.ask (bwrap jail, no tools,
  chromestatus.links (regex on URLs)                                JSON schema)
           │                                    ├─ discover (Fable, once): propose taxonomy
           │                                    ├─ classify (Haiku, every issue) ─▶ data/private/labels/
           │                                    └─ audit (Fable, 40-issue sample) ─▶ data/private/labels-audit/
           ▼                                                     │
         build ───────────────▶ data/public/reviews.json ◀───────┘ (enums + cleaned short reason)
                                data/public/audit.json
                                        │
                                        ▼
                                web/ (Vite, static) on port 5184
```

| Module | Does |
| --- | --- |
| `tagimpact/fetch_issues.py` | All issues with every comment and label/close/assign/reopen/cross-reference event, via `gh api graphql`. Closed issues already fetched are skipped unless `--refresh`. |
| `tagimpact/chromestatus.py` | All chromestatus features (`/api/v0/features`, 500 a page), and the review↔feature links. [chromestatus.md](chromestatus.md). |
| `tagimpact/latency.py` | TAG time vs time waiting on requesters, from timestamps, logins and labels only. [latency.md](latency.md). |
| `tagimpact/render.py` | A thread as numbered plain text for a prompt (`C0` body, `C1`… comments, `[TAG]`/`[REQUESTER]` from metadata), truncating long threads in the middle. |
| `tagimpact/llm.py`, `sandbox.py` | The only way thread text reaches a model. [../SECURITY.md](../SECURITY.md). |
| `tagimpact/discover.py` | One Fable call over 30 stratified threads proposing the label set. [taxonomy.md](taxonomy.md). |
| `tagimpact/taxonomy.py` | The label set, prompt definitions, JSON schema, validation, and the derived "TAG impact" outcome. |
| `tagimpact/classify.py` | One Haiku call per issue, 4 at a time; resumable. |
| `tagimpact/audit.py` | Fable relabels a 40-review stratified sample with the same prompt; agreement goes to `audit.json`. |
| `tagimpact/build.py` | Joins everything into `data/public/reviews.json` for the dashboard. |
| `web/` | Static dashboard, no framework or chart library. |

## Running it

```sh
python3 -m tagimpact.fetch_issues           # ~10 min for 1,212 issues; GraphQL ~400 points
python3 -m tagimpact.chromestatus fetch     # ~1 min
python3 -m tagimpact.discover               # optional: Fable proposes categories (~7 min, ~$4)
python3 -m tagimpact.classify               # Haiku, ~25 min, ~$3 for everything
python3 -m tagimpact.audit label && python3 -m tagimpact.audit report
python3 -m tagimpact.build
cd web && npm install && npm run serve      # http://localhost:5184
```

Tests: `nice -n 5 python3 -m unittest discover -s tests -t .` and `npm --prefix web test` (vitest,
4 workers max, nice +5 via `web/test-priority.ts`). `python3 -m scripts.sandbox_check` checks the jail.

## Choices

- **Python stdlib only** for the pipeline, like cosh: nothing to install, and nothing third-party
  touches untrusted text.
- **Structure first.** Latency, TAG membership, links and review kind use only metadata and URL
  regexes. Models are used only where reading is unavoidable (did the design change?).
- **One Haiku call per thread**, not batches: threads are long, and a hijacked thread can then only
  skew its own labels.
- **Labels keep a short reason and cited comment numbers**, so the dashboard's detail view can link
  straight to the comments behind a label for spot checks.
- **Charters and questions are split out** (`build.kind`, from title patterns): about 45 issues are
  W3C group charter reviews and about 14 are questions or meta issues. The dashboard shows feature
  and spec reviews by default.
- **The dashboard is static**, so it could go on GitHub Pages later. `data/public/` is committed.

## Known gaps / next steps

- TAG membership is inferred from triage actions (latency.md); an authoritative list of member terms
  would sharpen the TAG/requester split.
- Older chromestatus features often lack the Intent to Ship URL (chromestatus.md); matching blink-dev
  threads directly would need the Groups archive.
- The latency model counts any requester-side reply as the end of a wait; a third party's comment
  ends it early.
- Labels are one model's reading of a thread. The audit measures agreement with a stronger model,
  not truth; a human-labelled gold set would be the next step.
