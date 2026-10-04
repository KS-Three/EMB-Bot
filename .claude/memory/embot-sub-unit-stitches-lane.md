---
name: embot-sub-unit-stitches-lane
description: "EMB-Bot lane \"two stitch records on one point\" (2026-10-03) — local branch claude/sub-unit-stitches, unpushed; note and census tool committed; rule choice put to Kent"
metadata:
  node_type: memory
  type: project
  originSessionId: 7bdbbefa-2143-4bb4-9273-639fbbfd6546
  modified: 2026-10-03T22:56:00.138Z
---

> **Snapshot, copied 2026-10-03 (evening) from outside the repo.** Sessions rooted in
> `C:\Users\EE-LT-11030\.claude-work` keep their memory in
> `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, which is not this
> folder: nothing written there rides a PR or reaches a session rooted in EMB-Bot.
> The original was still being edited when this was taken, so check a fact here
> before acting on it. See [[memory-outside-the-repo]].

EMB-Bot, task handed over from PR #617: the browser fill emits stitches shorter than the stitch file's 0.1 mm unit, so two `stitch` records land on one point. See [[embot-browser-fill-lane-state]] and [[embot-handover-numbers-and-stacked-branches]].

**State on 2026-10-03 (evening):**
- Worktree `C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\.claude\worktrees\sub-unit-stitches`, branch `claude/sub-unit-stitches`, cut from origin/main `cf9f89f1`. One commit, `ab2c238e`, LOCAL ONLY (not pushed, no PR): `docs/sub-unit-stitches-2026-10-03.md`, `tools/sub-unit-stitch-census.mjs`, a COOKBOOK bullet, a `docs/scope-history.md` entry. No file under `src/` or `test/` changed.
- Counts reproduced to the stitch by two readers of mine (16,575 on 7,097 of 8,255 flag absent; 3,783 on 2,553 with `fillColumns` on after #617; the audit's 15,566).
- The rule choice was put to Kent with AskUserQuestion. My recommendation: a record-stream rule in `pushRun` behind a NEW flag built OFF (no run lays a second stitch in one hole). If this memory still says "put to Kent", check the conversation or ask him; do not build without his pick. The task's rule: a PR only if he picks an option that changes code; test first; an independent re-measure by a separate agent before arming auto-merge; merging is Kent's.

**Why:** #616 and #617 were both still OPEN that evening, so "after #617" numbers need #617's head (`dcec1f91`), extracted with `git show <ref>:src/<file>` into a scratch dir. A rule in `pushRun` (digitize.js) does not depend on either PR; a rule in `fill.js` would be stacked on #617.

**How to apply:**
- `node tools/sub-unit-stitch-census.mjs [srcDir] [--corpus sweep|studio|file.cjs] [--against otherSrc] [--on k=v] [--off k=v]` prints every table in the note; `--against` proves "flag absent: the same stream".
- Spawned as its own task chip, not part of this lane: the Studio's preset star (12 points, inner ratio 0.15, 20 mm) sews 48,645 stitches as one satin shape.
