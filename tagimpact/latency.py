"""How long each design review took, net of time spent waiting on the requesters.

Everything here uses the structure of an issue (timestamps, logins, labels,
author associations), never comment text. See docs/latency.md for the
reasoning and its limits.

Who is on which side:
  - TAG side: logins that applied labels, closed or assigned issues they
    didn't open (only people with triage rights can), during the window they
    did so (tag_logins), plus commenters whose authorAssociation is MEMBER or
    OWNER of the w3ctag org. That includes W3C staff, which is what we want:
    they act for the TAG.
  - Requester side: the issue author, and any other commenter not on the TAG
    side (co-editors, implementers, the public).
  - Bots (`*[bot]`, logins without a user) are ignored.

Waiting on the requester is the union of:
  1. label intervals: while a PAUSE_LABELS label is on the issue;
  2. turn intervals: from a TAG comment to the next comment, when that next
     comment is from the requester side. The TAG spoke and the next move was
     the requester's.
Everything else between opening and closing is TAG time.
"""

import datetime as dt

PAUSE_LABELS = {
    "Progress: pending external feedback",
    "Progress: pending editor update",
}
TAG_ASSOCIATIONS = {"MEMBER", "OWNER"}
ACTOR_EVENTS = {"LabeledEvent", "UnlabeledEvent", "ClosedEvent", "AssignedEvent", "ReopenedEvent"}
DAY = 86400.0


def ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


BOTS = {"ghost", "w3c-tag-bot", "w3cbot"}
TAG_LABEL_PREFIXES = ("Progress:", "Resolution:", "Topic:", "Venue:", "Review type:", "Priority:", "Missing:",
                      "Mode:", "Provenance:", "Focus:")
MIN_ACTIONS = 3          # fewer triage actions than this is noise, not membership
WINDOW_PAD = 60 * DAY    # TAG side from this long before the first action to after the last


def is_bot(login):
    return not login or login.endswith("[bot]") or login in BOTS


def tag_logins(issues):
    """{login: (from, to) or None} for the TAG side (see the module docstring).

    A login with at least MIN_ACTIONS triage actions (labels, closes, assigns
    on issues they didn't open) is TAG side between its first and last action,
    padded by WINDOW_PAD: TAG membership is for terms, and people file reviews
    before or after serving. A login whose only evidence is a MEMBER/OWNER
    association (GitHub reports the current one) and no actions is TAG side
    throughout (None): early members from before labels were used."""
    actions, member = {}, set()
    for i in issues:
        for e in i.get("events", []):
            a = e.get("actor")
            if e.get("__typename") in ACTOR_EVENTS and a and a != i.get("author") and not is_bot(a) \
                    and tag_process_event(e):
                actions.setdefault(a, []).append(ts(e["createdAt"]))
        for c in i.get("comments", []):
            if c.get("authorAssociation") in TAG_ASSOCIATIONS and not is_bot(c.get("author")):
                member.add(c["author"])
    tag = {}
    for a, times in actions.items():
        if len(times) >= MIN_ACTIONS:
            tag[a] = (min(times) - WINDOW_PAD, max(times) + WINDOW_PAD)
    for m in member:
        if m in tag:
            continue
        # A current org member with a few actions: TAG side around those actions only
        # (e.g. a past member who now files reviews). With none: always.
        times = actions.get(m)
        tag[m] = (min(times) - WINDOW_PAD, max(times) + WINDOW_PAD) if times else None
    return tag


def tag_process_event(e):
    """Closing, reopening, assigning, and labels in the TAG's own namespaces
    count as triage. Other labels (e.g. `chromium-high-priority`, applied by
    requesters' colleagues with triage rights) don't."""
    if e.get("__typename") in ("LabeledEvent", "UnlabeledEvent"):
        return (e.get("label") or "").startswith(TAG_LABEL_PREFIXES)
    return True


def on_tag(login, t, tag):
    if login not in tag:
        return False
    w = tag[login]
    return w is None or w[0] <= t <= w[1]


def side(login, issue, tag, t=None):
    """'tag', 'requester' or None (bots). Without a time, membership windows are ignored."""
    if is_bot(login):
        return None
    if login == issue.get("author"):
        return "requester"
    if t is None:
        return "tag" if login in tag else "requester"
    return "tag" if on_tag(login, t, tag) else "requester"


def union(intervals):
    out = []
    for a, b in sorted(i for i in intervals if i[1] > i[0]):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def clip(intervals, lo, hi):
    return [[max(a, lo), min(b, hi)] for a, b in intervals if min(b, hi) > max(a, lo)]


def label_intervals(issue, end):
    """[start, end] while each pause label was on the issue."""
    on, out = {}, []
    for e in sorted(issue.get("events", []), key=lambda e: e["createdAt"]):
        lab = e.get("label")
        if lab not in PAUSE_LABELS:
            continue
        t = ts(e["createdAt"])
        if e["__typename"] == "LabeledEvent":
            on.setdefault(lab, t)
        elif e["__typename"] == "UnlabeledEvent" and lab in on:
            out.append([on.pop(lab), t])
    out += [[t, end] for t in on.values()]
    return out


def turn_intervals(comments):
    """From each TAG comment to the next comment, when that one is the requester's."""
    out = []
    for prev, nxt in zip(comments, comments[1:]):
        if prev["side"] == "tag" and nxt["side"] == "requester":
            out.append([prev["t"], nxt["t"]])
    return out


def conclusion(issue):
    """When the review concluded: the final close, or None if still open."""
    if issue.get("state") != "CLOSED" or not issue.get("closedAt"):
        return None
    return ts(issue["closedAt"])


# Resolutions that state the TAG's position on the design, as opposed to how the review ended.
POSITIONS = {"satisfied", "validated", "satisfied with concerns", "ambivalent", "unsatisfied", "object",
             "lack of consensus"}


def resolution(issue):
    """The TAG's `Resolution:` label, without the prefix, or None. Six issues carry
    two, usually applied together (e.g. 'satisfied' and 'timed out'): a label that
    states a position beats a procedural one, then the one applied last wins."""
    labs = [l[len("Resolution: "):] for l in issue.get("labels", []) if l.startswith("Resolution: ")]
    if not labs:
        return None
    applied = {e["label"][len("Resolution: "):]: e["createdAt"] for e in issue.get("events", [])
               if e.get("__typename") == "LabeledEvent" and (e.get("label") or "").startswith("Resolution: ")}
    return max(labs, key=lambda l: (l in POSITIONS, applied.get(l, ""), l))


def compute(issue, tag, now):
    """The latency record for one issue. `now` closes still-open reviews (censored)."""
    opened = ts(issue["createdAt"])
    concluded = conclusion(issue)
    end = concluded if concluded is not None else now
    comments = []
    for c in issue.get("comments", []):
        s = side(c.get("author"), issue, tag, ts(c["createdAt"]))
        if s:
            comments.append({"t": ts(c["createdAt"]), "side": s, "login": c.get("author"),
                             "url": c.get("url"), "id": c.get("databaseId")})
    comments.sort(key=lambda c: c["t"])
    labels = clip(union(label_intervals(issue, end)), opened, end)
    turns = clip(union(turn_intervals(comments)), opened, end)
    waiting = union(labels + turns)
    wait_s = sum(b - a for a, b in waiting)
    total_s = end - opened
    first_tag = next((c["t"] for c in comments if c["side"] == "tag"), None)
    return {
        "number": issue["number"],
        "opened": issue["createdAt"],
        "closed": issue.get("closedAt") if concluded is not None else None,
        "open": concluded is None,
        "resolution": resolution(issue),
        "state_reason": issue.get("stateReason"),
        "total_days": round(total_s / DAY, 2),
        "author_wait_days": round(wait_s / DAY, 2),
        "tag_days": round((total_s - wait_s) / DAY, 2),
        "label_wait_days": round(sum(b - a for a, b in labels) / DAY, 2),
        "turn_wait_days": round(sum(b - a for a, b in turns) / DAY, 2),
        "first_tag_comment_days": round((first_tag - opened) / DAY, 2) if first_tag else None,
        "comments": len(comments),
        "tag_comments": sum(1 for c in comments if c["side"] == "tag"),
        "requester_comments": sum(1 for c in comments if c["side"] == "requester"),
        "wait_segments": [[round(a), round(b)] for a, b in waiting],
        "timeline": [{"t": round(c["t"]), "side": c["side"], "login": c["login"], "id": c["id"]}
                     for c in comments],
    }
