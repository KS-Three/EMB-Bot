---
name: eye-pairs-followup-2026-09-18
description: 2026-09-18 — the fourteen review items PR #506 skipped, and the traps around them; "merged" was open and red, a test that fails only where tesseract EXISTS, a word budget broken by the merge ref alone, and why FEATURES_SCHEMA was not bumped
metadata:
  type: project
---

# Eye pairs, the follow-up — 2026-09-18

Fourteen review items closed in `digitizer/tools/eye_pairs/`, one commit
each; what changed is dated paragraph by paragraph in
`docs/superpowers/specs/2026-09-17-eye-pairs-design.md`. This note is only
what that spec and the commits do not already say.

## What to carry forward

- **"Merged" was OPEN and red.** The brief said PR #506 had merged; `gh pr
  view 506` said open, auto-merge armed, `digitizer` failed, seven hours
  idle. One command before building on a PR someone calls merged. Kent's
  call was to push the two fixes to #506's own branch, let it merge, then
  `git rebase --onto origin/main <old tip>` — which replayed clean because
  the squash carried the branch's files over byte-identical (checked first:
  `git diff --stat <old tip> origin/main -- <the paths>` printed nothing).
- **A test can fail only where a dependency is PRESENT.** #506's red test
  simulated "no tesseract" by patching `legibility.measure` to raise. Kent's
  box has no tesseract, so preflight skips its own legibility check and the
  test passed. CI has the binary, so `run_preflight` called the same patched
  function and the raise escaped outside the guard under test. Simulate a
  missing binary WHOLE (`tesseract_available` False too). Reproduced locally
  with a fake `tesseract.bat` first on PATH — git-bash needs the `/c/...`
  form there; a `C:/...` entry is split at its colon and silently ignored.
- **A word budget can be broken by the MERGE REF alone.** MASTER_SCOPE read
  26,997 on the branch and under 27,000 on main; CI tests
  `refs/pull/N/merge`, where both sides' additions add up: 27,009.
  `git merge-tree --write-tree origin/main HEAD` gives the tree to count.
  Main read 26,990 once #506 landed — ten words under — so any PR that adds
  a sentence there is one other merge away from red.
- **Do not bump `FEATURES_SCHEMA` for a cache field.** A bump re-digitizes
  every arm, and a real `--render` (hours) was running in the main checkout
  that morning — found by reading `eye_pairs_out/` mtimes, not by asking.
  New row fields (`design_hash`, ref-arm `env`) are optional with a stated
  fallback; only a ref row lacking `env` is a cache miss.
- **Look for a live render before touching anything shared.** `git worktree
  list` showed `%TEMP%/eye-pairs-ref-25da2fe` and `Get-CimInstance
  Win32_Process` showed `python -m tools.eye_pairs --render`. Every git test
  here runs against a throwaway repo under `tmp_path` for that reason, and
  the local full suite was cut short to give the render its CPU.
- **git 2.55, measured:** `worktree remove --force` clears a registration
  whose directory is wholly GONE, but fails on a half-made worktree (the
  directory, no `.git` file) — and then every `add` at that path is refused
  as "missing but already registered". `worktree prune` after removing the
  directory is the cure, and it never touches a worktree still on disk. The
  first test written for this passed, because it assumed the wrong half.
- **A hardlink is not a copy.** `cv2.imwrite` rewrites in place, so a
  hardlinked `img/` picture would have changed under a live sitting. Renders
  are written to a temp name and `os.replace`d; the link keeps the old bytes.
- **The lane hook false-positives on a heredoc containing `del `** while cwd
  is under `.claude/worktrees/` ("this deletes or moves something"). Use the
  Edit tool for source; it is the better tool anyway.

See [[eye-pairs-build-2026-09-17]], [[worktree-venv-and-baselines]],
[[windows-goldens-fail-locally]].
