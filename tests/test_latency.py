import unittest

from tagimpact.latency import DAY, compute, tag_logins, union


def c(login, day, assoc="NONE"):
    return {"author": login, "authorAssociation": assoc, "createdAt": f"2024-01-{day:02d}T00:00:00Z",
            "url": f"u{day}", "databaseId": day}


def ev(kind, label, day, actor="tagger"):
    return {"__typename": kind, "label": label, "actor": actor, "createdAt": f"2024-01-{day:02d}T00:00:00Z"}


def issue(comments, events=(), closed_day=30, labels=()):
    return {"number": 1, "author": "req", "createdAt": "2024-01-01T00:00:00Z",
            "state": "CLOSED" if closed_day else "OPEN",
            "closedAt": f"2024-01-{closed_day:02d}T00:00:00Z" if closed_day else None,
            "labels": list(labels), "comments": list(comments), "events": list(events)}


class Latency(unittest.TestCase):
    def test_union(self):
        self.assertEqual(union([[5, 7], [1, 3], [2, 4], [7, 8]]), [[1, 4], [5, 8]])

    def test_tag_logins_from_actors_and_membership(self):
        i = issue([c("member", 2, "MEMBER"), c("rando", 3)],
                  [ev("LabeledEvent", "Topic: x", d, "tagger") for d in (2, 3, 4)]
                  + [ev("LabeledEvent", "y", 1, "req"), ev("LabeledEvent", "z", 1, "once")])
        tag = tag_logins([i])
        self.assertEqual(set(tag), {"member", "tagger"})
        self.assertIsNone(tag["member"])
        lo, hi = tag["tagger"]
        self.assertAlmostEqual(hi - lo, 2 * DAY + 2 * 60 * DAY)

    def test_membership_window(self):
        # "late" joins the TAG long after commenting on this issue as an outsider.
        t0 = 1704067200
        i = issue([c("late", 5), c("req", 15)])
        r = compute(i, {"late": (t0 + 400 * DAY, t0 + 800 * DAY)}, now=0)
        self.assertEqual(r["tag_comments"], 0)
        self.assertEqual(r["author_wait_days"], 0)

    def test_turn_wait(self):
        # TAG asks on day 5, requester answers day 15: 10 days waiting.
        i = issue([c("tagger", 5), c("req", 15), c("tagger", 20)])
        r = compute(i, {"tagger": None}, now=0)
        self.assertEqual(r["total_days"], 29)
        self.assertEqual(r["author_wait_days"], 10)
        self.assertEqual(r["tag_days"], 19)
        self.assertEqual(r["first_tag_comment_days"], 4)

    def test_label_wait_overlaps_turn(self):
        i = issue([c("tagger", 5), c("req", 15)],
                  [ev("LabeledEvent", "Progress: pending external feedback", 5),
                   ev("UnlabeledEvent", "Progress: pending external feedback", 20)])
        r = compute(i, {"tagger": None}, now=0)
        self.assertEqual(r["author_wait_days"], 15)   # union of [5,15] and [5,20]
        self.assertEqual(r["label_wait_days"], 15)
        self.assertEqual(r["turn_wait_days"], 10)

    def test_label_still_on_at_close(self):
        i = issue([], [ev("LabeledEvent", "Progress: pending editor update", 25)])
        r = compute(i, {}, now=0)
        self.assertEqual(r["author_wait_days"], 5)

    def test_open_issue_runs_to_now(self):
        i = issue([c("tagger", 3)], closed_day=None)
        now = 1704067200 + 10 * DAY   # 2024-01-11
        r = compute(i, {"tagger": None}, now=now)
        self.assertTrue(r["open"])
        self.assertEqual(r["total_days"], 10)
        self.assertIsNone(r["closed"])

    def test_tag_followup_is_tag_time(self):
        # Two TAG comments in a row: the gap between them is TAG time.
        i = issue([c("tagger", 5), c("tagger", 25)])
        self.assertEqual(compute(i, {"tagger": None}, now=0)["author_wait_days"], 0)




class Resolution(unittest.TestCase):
    def test_position_beats_procedure_then_latest(self):
        from tagimpact.latency import resolution
        i = issue([], [ev("LabeledEvent", "Resolution: satisfied", 5), ev("LabeledEvent", "Resolution: timed out", 9)],
                  labels=["Resolution: timed out", "Resolution: satisfied", "Topic: CSS"])
        self.assertEqual(resolution(i), "satisfied")
        i = issue([], [ev("LabeledEvent", "Resolution: too early", 5), ev("LabeledEvent", "Resolution: timed out", 9)],
                  labels=["Resolution: too early", "Resolution: timed out"])
        self.assertEqual(resolution(i), "timed out")
        self.assertIsNone(resolution(issue([], labels=["Topic: CSS"])))


if __name__ == "__main__":
    unittest.main()
