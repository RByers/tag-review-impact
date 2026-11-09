"""Fetch every issue in w3ctag/design-reviews, with all comments and the
label/close timeline, into data/private/issues/<number>.json.

The issue and comment *text* is untrusted (SECURITY.md): this module only
moves it from the API to disk as JSON. Nothing here interprets it, and a
tool-enabled agent session must not read those files in bulk.

    python3 -I -m tagimpact.fetch_issues [--refresh] [--only N ...]

Closed issues already on disk are skipped unless --refresh. Open issues are
always re-fetched, since they may have changed.
"""

import argparse
import json
import os
import subprocess
import sys
import time

from .paths import ISSUES_DIR

OWNER, REPO = "w3ctag", "design-reviews"
PAGE = 10   # issues per query; each brings up to 100 comments and 100 events

ISSUE_FIELDS = """
  number title url state stateReason createdAt closedAt
  author { login }
  authorAssociation
  body
  labels(first: 50) { nodes { name } }
  assignees(first: 20) { nodes { login } }
  comments(first: 100) { totalCount pageInfo { hasNextPage endCursor } nodes { %s } }
  timelineItems(first: 100, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT, REOPENED_EVENT,
                                        ASSIGNED_EVENT, CROSS_REFERENCED_EVENT]) {
    totalCount pageInfo { hasNextPage endCursor } nodes { %s }
  }
"""
COMMENT_FIELDS = "databaseId url createdAt author { login } authorAssociation body"
EVENT_FIELDS = """
  __typename
  ... on LabeledEvent { createdAt actor { login } label { name } }
  ... on UnlabeledEvent { createdAt actor { login } label { name } }
  ... on ClosedEvent { createdAt actor { login } stateReason }
  ... on ReopenedEvent { createdAt actor { login } }
  ... on AssignedEvent { createdAt actor { login } assignee { ... on User { login } } }
  ... on CrossReferencedEvent { createdAt source { __typename ... on Issue { url } ... on PullRequest { url } } }
"""
FIELDS = ISSUE_FIELDS % (COMMENT_FIELDS, EVENT_FIELDS)

LIST_QUERY = """query($owner: String!, $repo: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: %d, after: $after, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes { %s }
    }
  }
  rateLimit { remaining resetAt }
}""" % (PAGE, FIELDS)

ONE_QUERY = """query($owner: String!, $repo: String!, $n: Int!) {
  repository(owner: $owner, name: $repo) { issue(number: $n) { %s } }
}""" % FIELDS

MORE_COMMENTS = """query($owner: String!, $repo: String!, $n: Int!, $after: String) {
  repository(owner: $owner, name: $repo) { issue(number: $n) {
    comments(first: 100, after: $after) { pageInfo { hasNextPage endCursor } nodes { %s } } } }
}""" % COMMENT_FIELDS

MORE_EVENTS = """query($owner: String!, $repo: String!, $n: Int!, $after: String) {
  repository(owner: $owner, name: $repo) { issue(number: $n) {
    timelineItems(first: 100, after: $after, itemTypes: [LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT,
        REOPENED_EVENT, ASSIGNED_EVENT, CROSS_REFERENCED_EVENT]) {
      pageInfo { hasNextPage endCursor } nodes { %s } } } }
}""" % EVENT_FIELDS


def graphql(query, **variables):
    """One GraphQL call through `gh` (argv, no shell). Retries transient errors."""
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for k, v in variables.items():
        if v is None:
            continue
        args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    for attempt in range(5):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            d = json.loads(p.stdout)
            if not d.get("errors"):
                return d["data"]
            err = json.dumps(d["errors"])[:300]
        else:
            err = (p.stderr or p.stdout)[:300]
        print(f"graphql retry {attempt + 1}: {err}", file=sys.stderr)
        time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"graphql failed: {err}")


def complete(issue):
    """Page in comments and timeline events beyond the first 100."""
    n = issue["number"]
    for key, query in (("comments", MORE_COMMENTS), ("timelineItems", MORE_EVENTS)):
        conn = issue[key]
        while conn["pageInfo"]["hasNextPage"]:
            more = graphql(query, owner=OWNER, repo=REPO, n=n, after=conn["pageInfo"]["endCursor"])
            page = more["repository"]["issue"][key]
            conn["nodes"] += page["nodes"]
            conn["pageInfo"] = page["pageInfo"]
    return issue


def flatten(issue):
    """The JSON we store: connections reduced to plain lists."""
    out = {k: v for k, v in issue.items() if k not in ("labels", "assignees", "comments", "timelineItems")}
    out["author"] = (issue.get("author") or {}).get("login")
    out["labels"] = [l["name"] for l in issue["labels"]["nodes"]]
    out["assignees"] = [a["login"] for a in issue["assignees"]["nodes"]]
    out["comments"] = [dict(c, author=(c.get("author") or {}).get("login")) for c in issue["comments"]["nodes"]]
    events = []
    for e in issue["timelineItems"]["nodes"]:
        e = dict(e)
        if "actor" in e:
            e["actor"] = (e.get("actor") or {}).get("login")
        if "label" in e:
            e["label"] = (e.get("label") or {}).get("name")
        if "assignee" in e:
            e["assignee"] = (e.get("assignee") or {}).get("login")
        if "source" in e:
            e["source"] = (e.get("source") or {}).get("url")
        events.append(e)
    out["events"] = events
    out["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return out


def path_for(n):
    return os.path.join(ISSUES_DIR, f"{n:05d}.json")


def save(issue):
    os.makedirs(ISSUES_DIR, mode=0o700, exist_ok=True)
    tmp = path_for(issue["number"]) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(issue, f, ensure_ascii=False)
    os.replace(tmp, path_for(issue["number"]))


def have_closed(n):
    try:
        with open(path_for(n)) as f:
            return json.load(f).get("state") == "CLOSED"
    except (OSError, ValueError):
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refresh", action="store_true", help="re-fetch closed issues already on disk")
    ap.add_argument("--only", type=int, nargs="*", help="fetch just these issue numbers")
    a = ap.parse_args(argv)
    if a.only:
        for n in a.only:
            save(flatten(complete(graphql(ONE_QUERY, owner=OWNER, repo=REPO, n=n)["repository"]["issue"])))
            print(f"#{n}", file=sys.stderr)
        return
    after, count, skipped = None, 0, 0
    while True:
        d = graphql(LIST_QUERY, owner=OWNER, repo=REPO, after=after)
        conn = d["repository"]["issues"]
        for issue in conn["nodes"]:
            if not a.refresh and issue["state"] == "CLOSED" and have_closed(issue["number"]):
                skipped += 1
                continue
            save(flatten(complete(issue)))
            count += 1
        rl = d["rateLimit"]
        print(f"saved {count}, skipped {skipped}, rate limit left {rl['remaining']}", file=sys.stderr)
        if rl["remaining"] < 100:
            print(f"rate limit low; resets {rl['resetAt']}", file=sys.stderr)
            time.sleep(600)
        if not conn["pageInfo"]["hasNextPage"]:
            break
        after = conn["pageInfo"]["endCursor"]


if __name__ == "__main__":
    main()
