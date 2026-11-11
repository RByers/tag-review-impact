"""Compare the TAG's `Resolution:` labels with the model-inferred verdicts.

    python3 -m scripts.resolution_check

Structure only (labels, label events, dates) plus the stored model verdict
enums; no thread text.
"""

import collections
import glob
import json
import os

from tagimpact.build import kind
from tagimpact.discover import load_all
from tagimpact.paths import LABELS_DIR


def model_verdicts():
    out = {}
    for p in glob.glob(os.path.join(LABELS_DIR, "*.json")):
        with open(p) as f:
            x = json.load(f)
        out[x["number"]] = x["labels"].get("verdict")
    return out


def main():
    issues = load_all()
    mv = model_verdicts()
    reviews = [i for i in issues if kind(i.get("title")) == "review" and i.get("state") == "CLOSED"]
    print(f"{len(reviews)} concluded feature/spec reviews")

    res = {i["number"]: [l[12:] for l in i.get("labels", []) if l.startswith("Resolution: ")] for i in reviews}
    multi = {n: r for n, r in res.items() if len(r) > 1}
    print(f"with a Resolution label: {sum(1 for r in res.values() if r)}; none: {sum(1 for r in res.values() if not r)}; "
          f"more than one: {len(multi)} {sorted(multi.items())[:15]}")

    # When did Resolution labels start being used?
    first = {}
    for i in issues:
        for e in i.get("events", []):
            if e.get("__typename") == "LabeledEvent" and (e.get("label") or "").startswith("Resolution: "):
                first.setdefault(e["label"], e["createdAt"][:10])
                first[e["label"]] = min(first[e["label"]], e["createdAt"][:10])
    print("first use of each label:", dict(sorted(first.items(), key=lambda kv: kv[1])))

    by_year = collections.defaultdict(lambda: [0, 0])
    by_close = collections.defaultdict(lambda: [0, 0])
    for i in reviews:
        has = bool(res[i["number"]])
        by_year[i["createdAt"][:4]][has] += 1
        by_close[i["closedAt"][:4]][has] += 1
    print("labelled share by year opened:", {y: f"{v[1]}/{v[0] + v[1]}" for y, v in sorted(by_year.items())})
    print("labelled share by year closed:", {y: f"{v[1]}/{v[0] + v[1]}" for y, v in sorted(by_close.items())})

    # Closed without a label, by close reason (GitHub's stateReason).
    print("unlabelled by stateReason:",
          collections.Counter(i.get("stateReason") for i in reviews if not res[i["number"]]).most_common())

    # Crosstab: label (first) x model verdict.
    tab = collections.defaultdict(collections.Counter)
    for i in reviews:
        lab = res[i["number"]][0] if res[i["number"]] else "(none)"
        tab[lab][mv.get(i["number"])] += 1
    cols = ["satisfied", "satisfied_with_concerns", "unsatisfied", "recommends_against", "deferred", "withdrawn",
            "no_verdict", "not_a_review"]
    print(f"\n{'label \\ model':26}" + "".join(f"{c[:9]:>10}" for c in cols) + f"{'agree':>8}")
    agree_map = {"satisfied": {"satisfied"}, "validated": {"satisfied"},
                 "satisfied with concerns": {"satisfied_with_concerns"}, "ambivalent": {"satisfied_with_concerns"},
                 "unsatisfied": {"unsatisfied"}, "object": {"recommends_against"},
                 "withdrawn": {"withdrawn"}, "overtaken": {"withdrawn"},
                 "decline": {"deferred"}, "too early": {"deferred"}, "out of scope": {"deferred", "not_a_review"},
                 "too late": {"deferred"}, "timed out": {"no_verdict"}, "lack of consensus": {"no_verdict"}}
    tot_agree = tot = 0
    for lab, c in sorted(tab.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(c.values())
        ok = sum(c[v] for v in agree_map.get(lab, ()))
        if lab != "(none)":
            tot_agree += ok
            tot += n
        print(f"{lab:26}" + "".join(f"{c[v]:>10}" for v in cols) + (f"{100 * ok / n:7.0f}%" if lab != "(none)" else ""))
    print(f"\nagreement where a label exists: {100 * tot_agree / tot:.0f}% of {tot}")

    # Strong disagreements worth spot-checking.
    strong = [(i["number"], res[i["number"]][0], mv.get(i["number"])) for i in reviews if res[i["number"]]
              and ((res[i["number"]][0] in ("satisfied", "validated") and mv.get(i["number"]) in
                    ("unsatisfied", "recommends_against"))
                   or (res[i["number"]][0] in ("unsatisfied", "object") and mv.get(i["number"]) == "satisfied"))]
    print("strong disagreements:", strong)


if __name__ == "__main__":
    main()
