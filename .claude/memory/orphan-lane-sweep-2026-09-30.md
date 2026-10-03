---
name: orphan-lane-sweep-2026-09-30
description: "2026-09-30 — a sweep of every worktree and lane found two pushed-but-never-PR'd lanes; eye-pairs-followup revived as PR #583, pro-overlay-diff still parked; how to tell landed from orphaned under squash merges; Developer Mode turned on for symlinks"
metadata:
  node_type: memory
  type: project
  originSessionId: 31f70c2d-2042-4a90-ab36-d2b34366105a
  modified: 2026-10-01T01:55:42.555Z
---

# The orphan-lane sweep — 2026-09-30

Kent asked what could be done in parallel with three live sessions. The
answer was not new work: a red PR nobody was watching (#572) and two lanes
pushed weeks earlier with no PR.

- **`claude/pro-overlay-diff` is STILL PARKED** (Kent's call, 2026-09-30):
  9 commits from 2026-09-11, no PR. `digitizer/tools/pro_parity/diff.py`
  (region-by-region catalogue against the pro's file), its tests, the first
  run on Becker LC / Becker hat / Fremont. Its DOCTRINE and MASTER_SCOPE
  edits are stale and need judging before a revival.
- **`claude/eye-pairs-followup` became PR #583** on
  `claude/eye-pairs-followup-revive` (18 commits from 2026-09-18).

**How to apply:**

- **`git log origin/main..lane` cannot tell landed from orphaned here** —
  every lane is squash-merged, so it lists everything. `git apply --check -R`
  of the tip's patch also fails once the files move on. What worked: for the
  lane's newest commits, count how many ADDED lines exist verbatim in
  `origin/main`'s copy of the same file (70/71 = landed, 0/47 = orphan), and
  ask `gh pr list --state all --head <branch>`.
- **A red PR with auto-merge armed just sits.** #572 was red for 8 hours
  after a merge of main. Check `gh pr list` for one before proposing work.
- **Developer Mode is ON on Kent's box since 2026-09-30**, so Python can
  create symlinks. Before that `refarm.link_photo_prep` returned False in
  silence (WinError 1314) and #581's photo-prep fix did nothing locally —
  which also HID a test that only fails where the link succeeds. A test
  green on a box that cannot symlink says nothing about CI.
- A flag-pricing test re-pinned as a RATIO breaks when another default
  moves both arms unevenly (#567's envelope: +4.8% became +20%). Pin the
  engine the flag was priced on, as `test_edge_cap_lettering._run` does.

See [[concurrent-session-designed-the-same-tool-2026-09-17]],
[[eye-pairs-build-2026-09-17]], [[worktree-venv-and-baselines]].
