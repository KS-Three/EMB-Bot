---
name: built-off-sitting-2026-10-03
description: 2026-10-03 — one page for the built-OFF flags with no verdict; a flag listed as "waiting on Kent" was already the shipped engine; the artifact republish was refused twice before it went through, and how to avoid both
metadata:
  type: project
---

Kent asked a fresh session whether the project was on track, then picked "one
sitting page for the four built-OFF flags" (`cap_recentre`, `patch_junctions`,
`keep_counters`, `bean_letters`). Record and numbers:
`docs/eye-pairs-2026-10-03/README.md`.

**What changes what you do:**

- **Render a flag against shipped before listing it as waiting on Kent.**
  `satin_patch_junctions="satin"` sat in MASTER_SCOPE "Waiting on Kent" 19 as
  a flip call, but `satin_junction_stack` (ON 2026-09-19) hands the cover that
  same setting as its part C: off and on were one design on 8 of 8 logos. A
  test file had said so since the flip. One `--render --arms <arm>` on two
  logos would have shown it; so would a grep for where the flag is consumed.
- **Two of four flags had no pair on a real logo** (`patch_junctions`,
  `keep_counters`). An arm that is identical everywhere keeps its head on the
  page; say why in its table caption rather than leave a bare zero.
- **Check the live page's own tag in the store before replacing it.** The
  page held `back-1001` (`split_off`, five pairs) with no verdict two days on.
  Carry such an arm onto the new page, redrawn on today's base.
- **Put a flip Kent has made but not merged into the base.** `satin_crown_cover`
  ON was a local commit in another lane; it was cherry-picked as a render-only
  top commit and dropped before the PR. The envelope's ruling had been
  confounded by `satin_tip_caps` exactly this way.
- **The republish can be refused, twice over.** In auto permission mode the
  `Artifact` publish to the labelled page's URL was denied as a data-sharing
  upload. Do not route around it; ask Kent (he allowed it at once). Then a
  Read rule refused the images because the gallery sat in a temp directory:
  build or copy it to the lane's `digitizer/eye_pairs_out/gallery/`
  (gitignored, inside the session folder) and publish from there. To drive
  the page first, serve the gallery over localhost (`python -m http.server
  --directory <gallery>` through a temporary `.claude/launch.json` entry,
  reverted after); a `file://` tab cannot be scripted.
- **Kent's box, four render lanes beside another session's full suite:** 48
  arm-runs took 84 minutes; a run 2 to 12.5 minutes. Budget ninety.
- **The memory junction reads the MAIN checkout's working tree.** It was 77
  commits behind `origin/main` with three notes untracked, so every desktop
  session loaded a stale index. Fast-forward it at session start; a note
  written through the junction is uncommitted until someone lands it, so
  write notes in the lane that carries the PR.
- **The CLAUDE.md a session is handed is that stale checkout's too, and it
  cost a false finding.** The loaded copy said MASTER_SCOPE has an 800-line
  budget; `main` had said 27,000 words since 2026-09-14, with
  `tests/test_scope_budget.py` enforcing it. This session told Kent the file
  was over budget with no guard, three times and in a PR body, before the
  `update-master-scope` skill contradicted it. Before reporting that a
  documented rule is broken, read the rule on `origin/main` and grep for the
  test that already enforces it.

Related: [[second-sitting-eleven-flags-2026-09-28]],
[[flag-before-after-2026-09-18]], [[bridge-border-and-script-2026-09-30]],
[[concurrent-session-designed-the-same-tool-2026-09-17]].
