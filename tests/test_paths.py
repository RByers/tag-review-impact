import os
import tempfile
import unittest

from tagimpact.paths import main_checkout


class MainCheckout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.main = os.path.join(self.tmp.name, "proj")
        os.makedirs(os.path.join(self.main, ".git", "worktrees", "wt"))
        self.wt = os.path.join(self.main, ".claude", "worktrees", "wt")
        os.makedirs(self.wt)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        with open(path, "w") as f:
            f.write(text)

    def test_main_checkout_is_itself(self):
        self.assertEqual(main_checkout(self.main), self.main)

    def test_worktree_finds_main(self):
        gitdir = os.path.join(self.main, ".git", "worktrees", "wt")
        self.write(os.path.join(self.wt, ".git"), f"gitdir: {gitdir}\n")
        self.write(os.path.join(gitdir, "commondir"), "../..\n")
        self.assertEqual(main_checkout(self.wt), self.main)

    def test_relative_gitdir(self):
        gitdir = os.path.join(self.main, ".git", "worktrees", "wt")
        self.write(os.path.join(self.wt, ".git"), "gitdir: ../../../.git/worktrees/wt\n")
        self.write(os.path.join(gitdir, "commondir"), "../..\n")
        self.assertEqual(main_checkout(self.wt), self.main)

    def test_anything_odd_falls_back(self):
        self.write(os.path.join(self.wt, ".git"), "not a gitdir line\n")
        self.assertEqual(main_checkout(self.wt), self.wt)
        gitdir = os.path.join(self.main, ".git", "worktrees", "wt")
        self.write(os.path.join(self.wt, ".git"), f"gitdir: {gitdir}\n")   # no commondir file
        self.assertEqual(main_checkout(self.wt), self.wt)
        empty = os.path.join(self.tmp.name, "nogit")
        os.makedirs(empty)
        self.assertEqual(main_checkout(empty), empty)


if __name__ == "__main__":
    unittest.main()
