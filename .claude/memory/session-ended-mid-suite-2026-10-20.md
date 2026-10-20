---
name: session-ended-mid-suite-2026-10-20
description: a session that ends mid-suite leaves a ruled flip uncommitted in its lane and a hung pytest tree; a status sweep found Kent's "ON at 0.7" that way (#1017); what a sweep checks, and how to predict which goldens a bean flip moves before pushing
metadata:
  type: project
---

Status sweep 2026-10-20 (Kent: "how is the embot project looking, anything
uncommitted, anything to push, any questions"). SNAPSHOT of the lesson, not
of lane state — [[lane-cleanup-2026-10-20]] has the census.

## What the sweep found that `git status` and `gh pr list` did not

The "Hotel Fremont logo feedback" session had an `AskUserQuestion` answered
by Kent ("ON at 0.7 mm" for `bean_letter_straight_mm`), built the flip in
its lane, said "the full suite is running, about an hour", and ended. The
app listed it idle. #1016 had merged with the knob OFF. Fifty-seven minutes
later the lane held nine modified tracked files, nothing committed, and the
PowerShell pytest it started was still alive: a controller with ten CPU
seconds and nine xdist workers at zero CPU and 5 MB each, a tree with no
reader on its pipe. Nothing in the repo, the PR list, the session list or
the previous night's cleanup memo knew the ruling existed.

**Why:** a turn that ends while its verification is in flight leaves the
decision only in the transcript and the lane diff. The last cleanup memo
is always one session old, so its census cannot know the newest lane.

**How to apply.** A project sweep is three checks past the obvious two:
1. Every lane for dirty TRACKED files (`git status --porcelain
   --untracked-files=no` per `git worktree list --porcelain`, parsed with
   `awk` because the path has a space); the newest session's lane first.
2. `Get-CimInstance Win32_Process` for `python … -m pytest` trees older
   than the suite's normal runtime (~9 min on Kent's box) whose workers
   (`-u -c "import sys;ex…"`) show zero CPU: hung, kill the tree, re-run.
3. `list_events` on the newest session: an assistant line of the shape
   "Flip applied … running the suite" with no later turn means a ruling
   that never reached a commit. Carry it as Kent's, as the memo says — and
   read MASTER_SCOPE for a reversal first ([[lane-cleanup-2026-10-20]]).

## Predicting which goldens a default flip moves, before CI does

#1017's first CI run went red on four shards: six tests the flip moved.
`grep -l bean_letter_counter_hold_mm digitizer/tests/*.py` (the PREVIOUS
bean flip's knob) names five of the six files; the sixth
(`test_detail_spokes.py`) pinned its stream after that flip, so it never
carried the pin. Three shapes, each with its fix:

- A test asserting a card tool's pinned ARM DICT: add the key the tool now
  pins (`sewout_card_*`).
- A test pinning "main's md5" for an UNRELATED subject, with an OFF dict
  already in it (`HOLDS_OFF` in `test_hairline_lines_strand_mass.py`):
  add the knob to that dict. Same for a fixture captured before the flip
  whose subject is something else (`test_detail_spokes.py`'s Fremont
  arms): pin, never re-capture on Windows.
- A test whose SUBJECT is the default config's output
  (`test_small_text_counter_guard.py`): re-pin, document the move with
  stitch counts in the file's own paragraph, and prove host-independence
  by reproducing CI's new md5 locally with the knob at both values.

Run the grep and fix those files in the flip's own PR; CI's 25-minute
round trip is the cost of not doing so.
