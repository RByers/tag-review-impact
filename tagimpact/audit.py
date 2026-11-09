"""Audit the Haiku labels against a stronger model on a stratified sample.

    python3 -m tagimpact.audit label [--n 40] [--model fable] [--seed 11]   # sandboxed calls
    python3 -m tagimpact.audit report                                      # -> data/public/audit.json

`label` runs tagimpact.classify's exact prompt and schema with the reference
model on a sample of feature/spec reviews (not charters or questions),
stratified by year and thread length, into data/private/labels-audit/<model>/.
`report` compares them with data/private/labels/: per-dimension agreement
(exact match for single-choice, mean Jaccard for multi-select) and the
confusion matrix for the design-change scale. Only enum keys and numbers reach
the public file.
"""

import argparse
import collections
import glob
import json
import os
import random

from . import taxonomy
from .build import kind
from .classify import main as classify_main
from .discover import load_all
from .paths import LABELS_DIR, PRIVATE, PUBLIC

AUDIT_DIR = os.path.join(PRIVATE, "labels-audit")


def sample(issues, n, seed):
    rng = random.Random(seed)
    pool = [i for i in issues if kind(i.get("title")) == "review" and len(i.get("comments", [])) >= 2]
    strata = collections.defaultdict(list)
    for i in pool:
        y = int(i["createdAt"][:4])
        era = "early" if y < 2019 else "mid" if y < 2023 else "recent"
        size = "short" if len(i["comments"]) < 10 else "long"
        strata[(era, size)].append(i["number"])
    keys = sorted(strata)
    picked = []
    while len(picked) < n and any(strata[k] for k in keys):
        for k in keys:
            if strata[k] and len(picked) < n:
                picked.append(strata[k].pop(rng.randrange(len(strata[k]))))
    return sorted(picked)


def load_dir(d):
    out = {}
    for p in glob.glob(os.path.join(d, "*.json")):
        with open(p) as f:
            x = json.load(f)
        if x.get("prompt_version") == taxonomy.VERSION:
            out[x["number"]] = x["labels"]
    return out


def report(model):
    ref = load_dir(os.path.join(AUDIT_DIR, model))
    test = load_dir(LABELS_DIR)
    common = sorted(set(ref) & set(test))
    dims = {}
    for d in taxonomy.DIMENSIONS:
        k = d["key"]
        if d["multi"]:
            js = []
            for n in common:
                a, b = set(ref[n].get(k) or []), set(test[n].get(k) or [])
                js.append(len(a & b) / len(a | b) if a | b else 1.0)
            dims[k] = {"metric": "mean_jaccard", "value": round(sum(js) / len(js), 3) if js else None}
        else:
            same = sum(1 for n in common if ref[n].get(k) == test[n].get(k))
            dims[k] = {"metric": "exact", "value": round(same / len(common), 3) if common else None}
    scale = [v[0] for v in taxonomy.DIMENSIONS[0]["values"]]
    confusion = {a: {b: 0 for b in scale} for a in scale}
    for n in common:
        a, b = ref[n].get("change"), test[n].get("change")
        if a in confusion and b in confusion[a]:
            confusion[a][b] += 1
    within_one = sum(1 for n in common if ref[n].get("change") in scale[:5] and test[n].get("change") in scale[:5]
                     and abs(scale.index(ref[n]["change"]) - scale.index(test[n]["change"])) <= 1)
    on_scale = sum(1 for n in common if ref[n].get("change") in scale[:5] and test[n].get("change") in scale[:5])
    credit = lambda l: l.get("attribution") in taxonomy.TAG_CREDIT and l.get("change") in taxonomy.CHANGED
    credit_agree = sum(1 for n in common if credit(ref[n]) == credit(test[n]))
    out = {
        "reference_model": model, "test_model": "haiku", "taxonomy": taxonomy.VERSION, "n": len(common),
        "dimensions": dims,
        "change_confusion": {"rows_reference": scale, "matrix": confusion},
        "change_within_one_step": round(within_one / on_scale, 3) if on_scale else None,
        "tag_credited_change_agreement": round(credit_agree / len(common), 3) if common else None,
        "tag_credited_change_rate": {"reference": round(sum(map(credit, (ref[n] for n in common))) / len(common), 3)
                                     if common else None,
                                     "test": round(sum(map(credit, (test[n] for n in common))) / len(common), 3)
                                     if common else None},
        "issues": common,
    }
    os.makedirs(PUBLIC, exist_ok=True)
    with open(os.path.join(PUBLIC, "audit.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "issues"}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["label", "report"])
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--model", default="fable")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args(argv)
    if a.cmd == "label":
        nums = sample(load_all(), a.n, a.seed)
        classify_main(["--model", a.model, "--jobs", str(a.jobs), "--out", os.path.join(AUDIT_DIR, a.model),
                       "--only", *map(str, nums)])
    else:
        report(a.model)


if __name__ == "__main__":
    main()
