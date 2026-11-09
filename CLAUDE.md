# tag-review-impact

Dashboard estimating the impact of W3C TAG design reviews on web platform features.

## Git workflow: staged

Work lands on local `main` in batches. The operator manually tests the dev server and decides when
to push. There are no pull requests, and history is linear (never a merge commit).

- Work on a branch in a worktree under `.claude/worktrees/` (`EnterWorktree`), branched from local
  `main`. Check it's up to date with `main` before starting.
- When work is complete (tests pass, changes committed), land it without asking: `git rebase main`
  in the worktree, exit the worktree (ExitWorktree `keep`), then in the main checkout run
  `git merge --ff-only <branch>`, `git worktree remove .claude/worktrees/<name>` and
  `git branch -d <branch>`.
- If the fast-forward fails, rebase again. `main` only moves forward: never `reset`, `branch -f`
  or `checkout -B` it, because other agents land here concurrently.
- **Push only when the operator explicitly asks.** Then `git fetch` and `git push origin main`. If
  `origin/main` has moved, rebase only the unpushed commits onto it first. Never force-push;
  GitHub rulesets reject it anyway.
- Don't open pull requests or create branches on origin.
