"""Headline impact numbers from data/public/reviews.json (feature & spec reviews, concluded).

    python3 -m scripts.impact_stats
"""

import collections
import json
import os
import statistics

from tagimpact.paths import PUBLIC


def main():
    with open(os.path.join(PUBLIC, "reviews.json")) as f:
        d = json.load(f)
    rs = [r for r in d["reviews"] if r["kind"] == "review" and not r["open"] and r["impact"]]
    print(f"{len(rs)} concluded feature/spec reviews, labelled")
    for key in ("outcome", "change", "attribution", "verdict"):
        c = collections.Counter(r["impact"].get(key) for r in rs)
        print(key, ", ".join(f"{k} {v} ({100 * v / len(rs):.0f}%)" for k, v in c.most_common()))
    for key in ("change_type", "change_locus"):
        c = collections.Counter(v for r in rs for v in r["impact"].get(key) or [])
        print(key, ", ".join(f"{k} {v}" for k, v in c.most_common()))
    credited = {"minor", "major"}
    for label, sub in (("chromestatus-linked", [r for r in rs if r["features"]]),
                       ("not linked", [r for r in rs if not r["features"]])):
        n = sum(1 for r in sub if r["impact"]["outcome"] in credited)
        print(f"{label}: {len(sub)} reviews, TAG-credited change {100 * n / len(sub):.0f}%")
    print("by era: TAG-credited change %, median TAG days")
    for lo, hi in ((2013, 2016), (2017, 2019), (2020, 2022), (2023, 2026)):
        sub = [r for r in rs if lo <= int(r["opened"][:4]) <= hi]
        n = sum(1 for r in sub if r["impact"]["outcome"] in credited)
        print(f"  {lo}-{hi}: n={len(sub)} {100 * n / len(sub):.0f}% {statistics.median(r['tag_days'] for r in sub):.0f}")
    by = collections.defaultdict(list)
    for r in rs:
        by[r["impact"]["outcome"]].append(r["tag_days"])
    print("median TAG days by outcome:", {k: round(statistics.median(v)) for k, v in by.items()})


if __name__ == "__main__":
    main()
