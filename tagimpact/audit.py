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


def labels_dir(model):
    """Haiku's labels are the production set; other models' are audit runs."""
    return LABELS_DIR if model == "haiku" else os.path.join(AUDIT_DIR, model)


def load_costs(d, nums):
    usd, wall = [], []
    for n in nums:
        try:
            with open(os.path.join(d, f"{n:05d}.json")) as f:
                c = json.load(f).get("cost") or {}
        except (OSError, ValueError):
            continue
        usd.append(c.get("usd") or 0)
        wall.append(c.get("wall") or 0)
    return (sum(usd) / len(usd) if usd else None), (sum(wall) / len(wall) if wall else None)


def metrics(ref, test, common):
    """Agreement of `test` with `ref` on the issues in `common`."""
    out = {}
    for d in taxonomy.DIMENSIONS:
        k = d["key"]
        if d["multi"]:
            js = []
            for n in common:
                a, b = set(ref[n].get(k) or []), set(test[n].get(k) or [])
                js.append(len(a & b) / len(a | b) if a | b else 1.0)
            out[k] = sum(js) / len(js)
        else:
            out[k] = sum(1 for n in common if ref[n].get(k) == test[n].get(k)) / len(common)
    scale = [v[0] for v in taxonomy.DIMENSIONS[0]["values"]][:5]
    pairs = [(ref[n].get("change"), test[n].get("change")) for n in common]
    pairs = [(a, b) for a, b in pairs if a in scale and b in scale]
    out["change_within_one"] = sum(1 for a, b in pairs if abs(scale.index(a) - scale.index(b)) <= 1) / len(pairs)
    credit = lambda l: l.get("attribution") in taxonomy.TAG_CREDIT and l.get("change") in taxonomy.CHANGED
    out["tag_credited"] = sum(1 for n in common if credit(ref[n]) == credit(test[n])) / len(common)
    out["tag_credited_rate"] = sum(1 for n in common if credit(test[n])) / len(common)
    out["outcome"] = sum(1 for n in common if taxonomy.outcome(ref[n]) == taxonomy.outcome(test[n])) / len(common)
    return out


COLUMNS = ["change", "change_within_one", "outcome", "tag_credited", "attribution", "verdict", "change_type",
           "change_locus"]


def compare(reference, models):
    """Each model against the reference, plus every pair of models (how much they agree with each other)."""
    sets = {m: load_dir(labels_dir(m)) for m in [reference, *models]}
    common = sorted(set.intersection(*(set(s) for s in sets.values())))
    print(f"{len(common)} reviews labelled by all of: {', '.join(sets)}")
    head = f"{'test vs reference':24}" + "".join(f"{c[:12]:>13}" for c in COLUMNS) + f"{'rate':>7}{'$/review':>10}{'s/review':>9}"
    print(head)
    pairs = [(m, reference) for m in models]
    pairs += [(models[j], models[i]) for i in range(len(models)) for j in range(i + 1, len(models))]
    rows = {}
    for m, other in pairs:
        r = metrics(sets[other], sets[m], common)
        rows[f"{m} vs {other}"] = r
        usd, wall = load_costs(labels_dir(m), common)
        print(f"{m + ' vs ' + other:24}" + "".join(f"{100 * r[c]:12.0f}%" for c in COLUMNS)
              + f"{100 * r['tag_credited_rate']:6.0f}%" + (f"{usd:10.4f}{wall:9.1f}" if usd is not None else ""))
    ref_rate = sum(1 for n in common if sets[reference][n].get("attribution") in taxonomy.TAG_CREDIT
                   and sets[reference][n].get("change") in taxonomy.CHANGED) / len(common)
    print(f"{reference} 'changed, TAG credited' rate: {100 * ref_rate:.0f}%")
    return rows


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
    ap.add_argument("cmd", choices=["label", "report", "compare"])
    ap.add_argument("--models", nargs="*", default=["haiku", "sonnet", "opus"],
                    help="compare: models to score against --model")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--model", default="fable")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args(argv)
    if a.cmd == "label":
        nums = sample(load_all(), a.n, a.seed)
        classify_main(["--model", a.model, "--jobs", str(a.jobs), "--out", os.path.join(AUDIT_DIR, a.model),
                       "--only", *map(str, nums)])
    elif a.cmd == "compare":
        compare(a.model, a.models)
    else:
        report(a.model)


if __name__ == "__main__":
    main()
