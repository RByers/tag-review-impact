"""Build the dashboard dataset, data/public/reviews.json.

    python3 -m tagimpact.build

Joins, per design-review issue:
  - the latency record (tagimpact.latency), from structure only;
  - chromestatus features linked to it (tagimpact.chromestatus), either from
    the feature's side (its tag_review field or another field) or from a
    chromestatus.com/feature/<id> URL in the issue body;
  - the impact labels from tagimpact.classify, if present
    (data/private/labels/<n>.json), reduced to known keys and cleaned text.

Untrusted strings that reach the public file: issue titles, feature names and
cleaned model reasons, all length-capped and stripped of control characters.
The dashboard shows them as text only (SECURITY.md). URLs that reach it:
blink-dev thread URLs, kept only on the groups.google.com/a/chromium.org host.
"""

import json
import os
import re
import time

from . import taxonomy
from .chromestatus import feature_record, links as cs_links, load as cs_load
from .discover import load_all
from .latency import compute, tag_logins
from .llm import clean_text
from .paths import LABELS_DIR, PUBLIC

FEATURE_RE = re.compile(r"chromestatus\.com/(?:features?|guide/edit|feature)/(\d{6,20})", re.I)
BLINK_DEV = re.compile(r"^https://groups\.google\.com/a/chromium\.org/[\w/#!.?=&%+-]*$")
CTRL = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮⁦-⁩]")
REVIEW_TYPES = re.compile(r"^Review type: ")


CHARTER = re.compile(r"^\s*\[(?:wg|ig|cg)/|\bcharter\b", re.I)
QUESTION = re.compile(r"^\s*(?:question\s*:|\[meta\])", re.I)


def kind(title):
    """'charter' (W3C group charter reviews), 'question' (questions and meta
    issues) or 'review' (feature and spec design reviews), from the title."""
    t = title or ""
    if CHARTER.search(t):
        return "charter"
    if QUESTION.search(t):
        return "question"
    return "review"


def plain(s, n):
    return re.sub(r"\s+", " ", CTRL.sub(" ", str(s or ""))).strip()[:n]


def public_feature(rec):
    return {
        "id": rec["id"] if isinstance(rec.get("id"), int) else None,
        "name": plain(rec.get("name"), 160),
        "link_source": rec.get("link_source"),
        "i2s_url": rec["i2s_url"] if rec.get("i2s_url") and BLINK_DEV.match(rec["i2s_url"]) else None,
        "i2p_url": rec["i2p_url"] if rec.get("i2p_url") and BLINK_DEV.match(rec["i2p_url"]) else None,
        "ship_milestone": rec.get("ship_milestone") if isinstance(rec.get("ship_milestone"), int) else None,
        "chrome_status": plain(rec.get("chrome_status"), 60),
        "tag_review_status": plain(rec.get("tag_review_status"), 40),
        "has_origin_trial": bool(rec.get("has_origin_trial")),
    }


def load_labels(n):
    try:
        with open(os.path.join(LABELS_DIR, f"{n:05d}.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def public_labels(raw):
    """Keep only taxonomy keys and values, comment indexes and cleaned reasons."""
    if not raw:
        return None
    out = taxonomy.validate(raw.get("labels") or {})
    out["outcome"] = taxonomy.outcome(out)
    out["reason"] = clean_text(raw.get("labels", {}).get("reason"), taxonomy.REASON_MAX)
    ev = raw.get("labels", {}).get("evidence_comments") or []
    out["evidence_comments"] = [i for i in ev if isinstance(i, int) and 0 <= i <= 10000][:5]
    out["model"] = plain(raw.get("model"), 40)
    out["prompt_version"] = plain(raw.get("prompt_version"), 20)
    return out


def main():
    issues = load_all()
    tag = tag_logins(issues)
    now = time.time()
    features = cs_load()
    by_id = {f.get("id"): f for f in features}
    linked = cs_links(features)
    reviews = []
    for i in issues:
        rec = compute(i, tag, now)
        feats = {f["id"]: f for f in linked.get(i["number"], [])}
        for fid in FEATURE_RE.findall(i.get("body") or ""):
            f = by_id.get(int(fid))
            if f and int(fid) not in feats and not f.get("deleted"):
                feats[int(fid)] = dict(feature_record(f), link_source="issue_body")
        labels = public_labels(load_labels(i["number"]))
        if labels:
            # Evidence C<k> -> comment database id for links; C0 (the issue body) -> 0.
            order = [c.get("databaseId") for c in sorted(i.get("comments", []), key=lambda c: c["createdAt"])]
            ids = []
            for k in labels.pop("evidence_comments"):
                cid = 0 if k == 0 else order[k - 1] if k <= len(order) else None
                if isinstance(cid, int) and cid not in ids:
                    ids.append(cid)
            labels["evidence_ids"] = ids
        rec.update(
            title=plain(i.get("title"), 200),
            kind=kind(i.get("title")),
            requester=plain(i.get("author"), 40),
            review_type=[l[len("Review type: "):] for l in i.get("labels", []) if REVIEW_TYPES.match(l)],
            venues=[l[len("Venue: "):] for l in i.get("labels", []) if l.startswith("Venue: ")],
            topics=[l[len("Topic: "):] for l in i.get("labels", []) if l.startswith("Topic: ")],
            features=[public_feature(f) for f in feats.values()],
            impact=labels,
        )
        reviews.append(rec)
    os.makedirs(PUBLIC, exist_ok=True)
    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "taxonomy": taxonomy.public(),
        "tag_logins": sorted(tag),
        "reviews": reviews,
    }
    path = os.path.join(PUBLIC, "reviews.json")
    with open(path + ".tmp", "w") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(path + ".tmp", path)
    n_lab = sum(1 for r in reviews if r["impact"])
    n_feat = sum(1 for r in reviews if r["features"])
    print(f"{len(reviews)} reviews, {n_feat} linked to chromestatus, {n_lab} labelled -> {path} "
          f"({os.path.getsize(path) // 1024} KiB)")


if __name__ == "__main__":
    main()
