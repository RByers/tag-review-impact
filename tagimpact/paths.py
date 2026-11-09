"""Where data lives. data/private/ holds raw fetched text (untrusted, gitignored);
data/public/ holds derived data the dashboard reads (committed)."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE = os.path.join(ROOT, "data", "private")
PUBLIC = os.path.join(ROOT, "data", "public")
ISSUES_DIR = os.path.join(PRIVATE, "issues")
CHROMESTATUS = os.path.join(PRIVATE, "chromestatus.json")
LABELS_DIR = os.path.join(PRIVATE, "labels")
