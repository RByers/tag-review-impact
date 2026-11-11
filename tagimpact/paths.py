"""Where data lives. data/private/ holds raw fetched text and model labels
(untrusted, gitignored); data/public/ holds derived data the dashboard reads
(committed, so it follows the checkout).

Private data is shared by every worktree: it lives in the main checkout's
data/private, found from the worktree's `.git` file, so fetches and model labels
(slow and paid for) are never duplicated or lost with a worktree. Set
TAGIMPACT_DATA to use another directory, e.g. a scratch copy for an experiment.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main_checkout(root):
    """The main checkout of the repository `root` belongs to, or `root` itself.

    A linked worktree has a `.git` file ("gitdir: <main>/.git/worktrees/<name>")
    whose directory holds a `commondir` file pointing at the shared `<main>/.git`.
    Anything unexpected (a plain checkout, a bare repo, no git) falls back to root."""
    dotgit = os.path.join(root, ".git")
    if not os.path.isfile(dotgit):
        return root
    try:
        with open(dotgit) as f:
            line = f.read().strip()
        if not line.startswith("gitdir:"):
            return root
        gitdir = os.path.normpath(os.path.join(root, line[len("gitdir:"):].strip()))
        with open(os.path.join(gitdir, "commondir")) as f:
            common = os.path.normpath(os.path.join(gitdir, f.read().strip()))
    except OSError:
        return root
    if os.path.basename(common) != ".git" or not os.path.isdir(common):
        return root
    return os.path.dirname(common)


PRIVATE = os.environ.get("TAGIMPACT_DATA") or os.path.join(main_checkout(ROOT), "data", "private")
PUBLIC = os.path.join(ROOT, "data", "public")
ISSUES_DIR = os.path.join(PRIVATE, "issues")
CHROMESTATUS = os.path.join(PRIVATE, "chromestatus.json")
LABELS_DIR = os.path.join(PRIVATE, "labels")
