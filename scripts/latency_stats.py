"""Summary statistics of the latency model, for docs/latency.md.

    python3 -m scripts.latency_stats
"""

import collections
import statistics
import time

from tagimpact.discover import load_all
from tagimpact.latency import compute, tag_logins


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def main():
    issues = load_all()
    tag = tag_logins(issues)
    print(f"{len(issues)} issues, {len(tag)} TAG-side logins")
    recs = [compute(i, tag, time.time()) for i in issues]
    closed = [r for r in recs if not r["open"]]
    print(f"closed {len(closed)}, open {len(recs) - len(closed)}")
    for k in ("total_days", "tag_days", "author_wait_days", "label_wait_days", "turn_wait_days",
              "first_tag_comment_days"):
        xs = [r[k] for r in closed if r[k] is not None]
        print(f"{k:24} median {statistics.median(xs):7.1f}  p25 {q(xs, .25):7.1f}  p75 {q(xs, .75):7.1f}  "
              f"p90 {q(xs, .9):7.1f}  mean {statistics.mean(xs):7.1f}")
    by_year = collections.defaultdict(list)
    for r in closed:
        by_year[r["opened"][:4]].append(r)
    print("year  n  median_total median_tag median_wait")
    for y in sorted(by_year):
        rs = by_year[y]
        print(y, len(rs), statistics.median(r["total_days"] for r in rs),
              statistics.median(r["tag_days"] for r in rs), statistics.median(r["author_wait_days"] for r in rs))
    print(collections.Counter(r["resolution"] for r in recs).most_common())
    print("no TAG comment at all:", sum(1 for r in closed if not r["tag_comments"]))


if __name__ == "__main__":
    main()
