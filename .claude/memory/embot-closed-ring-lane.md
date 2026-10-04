---
name: embot-closed-ring-lane
description: "EMB-Bot PRs #621 (offsetRing on a ring that repeats a point) and #625 (double-click gesture, stacked on it); defect 55's offset half still waits on Kent"
metadata:
  type: project
---

*Imported 2026-10-04 as a SNAPSHOT from the memory folder of sessions rooted outside this repo (`~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, session `bbcdacb6-2052-49c0-b440-803a17a0c9c3`, last written 2026-10-04T04:44:26.503Z); see [[wrong-root-sessions-and-global-guards-2026-10-04]]. The source may have moved on since. "I" below is the session that wrote it. PR states re-checked at import: #621 and #625 both open, neither armed.*

EMB-Bot lane worked 2026-10-03. One worktree, `.claude\worktrees\offset-ring-closed`, holds BOTH branches (it is checked out on the second; `app/node_modules` was copied into it, 162 MB). See [[embot-browser-fill-lane-state]] for the neighbouring lanes and [[parallel-agent-with-embot]] for the reach-check lesson this lane cost.

**PR #621 `claude/offset-ring-closed`** (head `5fc0dd47`, base main, not armed; all four checks green 2026-10-03). `offsetRing` in `src/digitize.js` moves a ring's corners said once (`distinctCorners`, 1e-9 px) and `isConvexRing` reads them. A ring handed over closed (`[p0..pn, p0]`) got a 3x mitre wedge, sewn under any fabric preset (terry: 1.8 mm outside a 40 mm box, 0.6 is right); outline, hole and island alike. Rings with no repeat are byte-identical (4,536 outputs; an independent audit's 12,365). MASTER_SCOPE defect 54. Instrument: `node tools/closed-ring-census.mjs [srcDir]` (`--hash`, `--compare`).

**PR #625 `claude/double-click-slip`** (head `0207f9a4`, base main, STACKED on #621: "merge #621 first", not armed). The audit of #621 found the same clamp from a NEAR repeat: a hand-drawn shape finished with a double-click whose second click slipped more than 0.5 canvas px kept the slip as an anchor (terry, 40 mm box: fill 1.73 mm past the drawn ring, 0.85 clean). Kent picked "fix the gesture" on 2026-10-03: `ManualPanel.onCanvasClick` now lets a click with `detail > 1` go by. Real-browser spec `app/e2e/manual-double-click.spec.js`.

**Why:** the wedge under a preset is thread outside the drawing; Kent wanted to know whether customers' files carry it. Exact repeats: no Studio lane sends one. Near repeats: the hand-drawn lane did.

**Still open, Kent's call, do not build unasked:** MASTER_SCOPE defect 55's OFFSET half. Shapes saved before #625 keep their slipped anchor and spike, and two anchors dragged to one hoop corner make another. The cure is a bevel past the mitre clamp in `offsetRing`, which moves every sharp corner under a preset.

**How to apply:**
- Merging both PRs is Kent's. If #621 goes DIRTY (every lane appends to `docs/scope-history.md`): in that worktree `git checkout claude/offset-ring-closed`, merge `origin/main` keep-both (main's entries first), push, then merge that into `claude/double-click-slip` and push. The tree must be clean before switching.
- #621 and #620 (island audit) both add `distinctCorners` with the same body in different places; git merges them into a double declaration (155 tests pass on the union). Whichever lands second deletes one copy; if #620 landed first, also drop its `offsetRing(distinctCorners(hh), ...)` and the comment beside it. Two SendMessage notes to the #620 session expired unapproved, so #621's body is the only record.
- Vitest in that worktree needs `--hookTimeout=180000` when the laptop is loaded (font preload exceeds the 10 s default); local e2e fails only `configurator-smoke`'s page-load check when no digitizer service is up.
- Left on purpose (measured, in the record): a closed ring's underlay still differs from the open ring's, because `insetRing`, `orderShapes` and `pcaAngleDeg` read the points. The one-place cure is to strip repeats at the builder's door, which would move closed-ring stitches with no preset too: also Kent's call, not asked yet.
