"""Render an issue thread as plain text for a model prompt.

The text is untrusted. It is fenced in a way the prompt explains, comments
are numbered (C0 is the issue body) so the model can cite them by index, and
each one carries the side its author is on (from tagimpact.latency, i.e.
from structure, not from anything the text claims).
"""

from .latency import side, ts

BODY_LIMIT = 12000      # characters kept from the issue body
COMMENT_LIMIT = 4000    # from each comment
THREAD_LIMIT = 90000    # whole thread; middle comments are dropped first


def _cut(s, n):
    s = (s or "").replace("\r\n", "\n")
    return s if len(s) <= n else s[:n] + f"\n[... {len(s) - n} more characters cut]"


def thread_text(issue, tag, limit=THREAD_LIMIT, body_limit=BODY_LIMIT, comment_limit=COMMENT_LIMIT):
    head = (f"ISSUE #{issue['number']}: {issue.get('title', '')}\n"
            f"Opened {issue['createdAt'][:10]} by {issue.get('author')} [REQUESTER]; "
            f"state {issue.get('state')}{' closed ' + issue['closedAt'][:10] if issue.get('closedAt') else ''}; "
            f"labels: {', '.join(issue.get('labels', []))}\n")
    parts = [f"--- C0 {issue['createdAt'][:10]} {issue.get('author')} [REQUESTER] (issue body)\n"
             f"{_cut(issue.get('body'), body_limit)}\n"]
    for i, c in enumerate(sorted(issue.get("comments", []), key=lambda c: c["createdAt"]), 1):
        s = side(c.get("author"), issue, tag, ts(c["createdAt"])) or "bot"
        parts.append(f"--- C{i} {c['createdAt'][:10]} {c.get('author')} [{s.upper()}]\n"
                     f"{_cut(c.get('body'), comment_limit)}\n")
    # Keep the start and the end of long threads: the request, and how it concluded.
    total = len(head) + sum(map(len, parts))
    dropped = 0
    while total > limit and len(parts) > 6:
        mid = len(parts) // 2
        total -= len(parts.pop(mid))
        dropped += 1
    if dropped:
        parts.insert(len(parts) // 2, f"--- [{dropped} comments from the middle of the thread omitted]\n")
    return head + "".join(parts)


def comment_index(issue):
    """C<n> -> (comment url, databaseId); C0 is the issue itself."""
    out = {0: (issue.get("url"), None)}
    for i, c in enumerate(sorted(issue.get("comments", []), key=lambda c: c["createdAt"]), 1):
        out[i] = (c.get("url"), c.get("databaseId"))
    return out
