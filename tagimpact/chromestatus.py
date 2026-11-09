"""Fetch every chromestatus.com feature and link them to TAG design reviews.

    python3 -m tagimpact.chromestatus fetch   # -> data/private/chromestatus.json
    python3 -m tagimpact.chromestatus links   # print link stats

Feature text (summaries, motivation...) is written by feature owners, so it is
treated as untrusted like the GitHub threads (SECURITY.md). We only pull URLs,
ids, dates, milestones and enums out of it with regexes; nothing reads the
prose.

Links come from two places:
  - the feature's `tag_review` field, which links the review issue directly;
  - any other field mentioning a design-reviews issue URL (explainer notes,
    comments), recorded with a lower confidence.
The blink-dev "Intent to Ship" thread is the `intent_thread_url` of the
feature's shipping stage (stage types below, from chromium-dashboard's
internals/core_enums.py).
"""

import json
import os
import re
import sys
import time
import urllib.request

from .paths import CHROMESTATUS, PRIVATE

API = "https://chromestatus.com/api/v0/features"
PAGE = 500
UA = "tag-review-impact/0.1 (research dataset)"

# chromium-dashboard internals/core_enums.py
SHIP_STAGES = {160: "blink", 260: "fast", 360: "psa", 460: "deprecation"}
PROTOTYPE_STAGES = {120: "blink", 220: "fast", 320: "psa", 410: "deprecation"}
OT_STAGES = {150, 151, 250, 251, 450, 451}

REVIEW_RE = re.compile(r"github\.com/w3ctag/design-reviews/issues/(\d+)", re.I)
BLINK_DEV_RE = re.compile(r"^https://groups\.google\.com/a/chromium\.org/[gd]/(?:msg|topic)?/?blink-dev/", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            raw = urllib.request.urlopen(req, timeout=180).read().decode()
            if raw.startswith(")]}'"):
                raw = raw[raw.index("\n") + 1:]
            return json.loads(raw)
        except Exception as e:      # network hiccups: retry with backoff
            print(f"retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}")


def fetch():
    features, start = [], 0
    while True:
        d = get(f"{API}?num={PAGE}&start={start}")
        page = d.get("features") or []
        features += page
        print(f"{len(features)} / {d.get('total_count')}", file=sys.stderr)
        if not page or len(features) >= (d.get("total_count") or 0):
            break
        start += len(page)
    os.makedirs(PRIVATE, mode=0o700, exist_ok=True)
    with open(CHROMESTATUS + ".tmp", "w") as f:
        json.dump({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "features": features}, f)
    os.replace(CHROMESTATUS + ".tmp", CHROMESTATUS)


def strings(obj, path=""):
    """Every (path, string) inside a JSON value."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


def safe_url(u):
    """Only http(s) URLs, else None. The dashboard re-checks the host."""
    return u if isinstance(u, str) and re.match(r"^https?://[^\s\"'<>]+$", u) else None


def first_ship_milestone(feature):
    best = None
    for st in feature.get("stages") or []:
        if st.get("stage_type") in SHIP_STAGES:
            for k in ("desktop_first", "android_first", "ios_first", "webview_first"):
                v = st.get(k)
                if isinstance(v, int) and (best is None or v < best):
                    best = v
    return best


def feature_record(f):
    stages = f.get("stages") or []
    ship = [s for s in stages if s.get("stage_type") in SHIP_STAGES]
    proto = [s for s in stages if s.get("stage_type") in PROTOTYPE_STAGES]
    i2s = next((safe_url(s.get("intent_thread_url")) for s in ship if safe_url(s.get("intent_thread_url"))), None)
    i2p = next((safe_url(s.get("intent_thread_url")) for s in proto if safe_url(s.get("intent_thread_url"))), None)
    chrome = ((f.get("browsers") or {}).get("chrome") or {})
    status = chrome.get("status") or {}
    return {
        "id": f.get("id"),
        "name": f.get("name"),
        "created": (f.get("created") or {}).get("when") if isinstance(f.get("created"), dict) else f.get("created"),
        "feature_type": f.get("feature_type"),
        "intent_stage": f.get("intent_stage"),
        "chrome_status": status.get("text") if isinstance(status, dict) else status,
        "ship_milestone": first_ship_milestone(f),
        "tag_review_status": f.get("tag_review_status"),
        "i2s_url": i2s,
        "i2p_url": i2p,
        "has_origin_trial": any(s.get("stage_type") in OT_STAGES for s in stages),
        "deleted": bool(f.get("deleted")),
    }


def links(features):
    """{issue number: [link]} where link = feature record + how it was found."""
    out = {}
    for f in features:
        if f.get("deleted") or f.get("unlisted"):
            continue
        found = {}
        for n in REVIEW_RE.findall(f.get("tag_review") or ""):
            found[int(n)] = "tag_review"
        for path, s in strings(f):
            if path == "tag_review":
                continue
            for n in REVIEW_RE.findall(s):
                found.setdefault(int(n), "other_field")
        if not found:
            continue
        rec = feature_record(f)
        for n, how in found.items():
            out.setdefault(n, []).append(dict(rec, link_source=how))
    return out


def load():
    with open(CHROMESTATUS) as f:
        return json.load(f)["features"]


def main(argv=None):
    cmd = (argv or sys.argv[1:] or ["fetch"])[0]
    if cmd == "fetch":
        fetch()
    elif cmd == "links":
        L = links(load())
        direct = sum(1 for v in L.values() if any(x["link_source"] == "tag_review" for x in v))
        i2s = sum(1 for v in L.values() if any(x["i2s_url"] for x in v))
        print(f"{len(L)} review issues linked from chromestatus; {direct} via tag_review; {i2s} with an I2S thread")
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
