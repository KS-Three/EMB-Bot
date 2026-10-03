---
name: fill-columns-2026-10-03
description: "2026-10-03 — the browser (JS) fill laid thread across every hole and notch, unseen by its test and by the preview; `fillColumns` built OFF (Kent's flip); how to read thread instead of needle points; what a parallel session found by sweeping PRs, lanes and docs first"
metadata:
  type: project
---

# Fill columns — 2026-10-03

**The defect.** `src/fill.js` `tatamiFill` sews row by row. Where a shape
splits a row (a hole, or the mouth of a U) it went from one span straight to
the next: a float when the gap is over `maxStitch` (4 mm), a plain STITCH when
it is not. Measured on a 40 mm manual fill with two cut-outs: 76 untrimmed
floats across the 12 mm one (912 mm of thread), 20 stitches across the 3 mm
one. Quality review 2026-09-08 §4 had named it; nobody owned it; cut-outs
(#591) made holes something a customer draws.

**Why nothing saw it.** The engine test counts needle points inside the hole
and a float has none. `src/render.js` draws no jumps, so the Studio preview
shows a clean hole. Screen, suite and file were three views and two were
blind.

**What was built (OFF).** `tatamiFill({ columns: true })`: a port of
`stage6_fill._columns`, each column its own boustrophedon, nearest-first by
the closest of four corners, and between columns one stitch inside the shape
or a CUT. `buildQualityDesign({ fillColumns })` passes it to the fill and
every tatami underlay, and cuts the move between two RUNS of one shape when it
crosses open ground. Floats 79/89/148/121 → 2/2/1/1 on four manual shapes;
cuts 1 → 3/2/5/1; stitches +2–9%. Sheet: `docs/renders/fill-columns-2026-10-03/`.

**Why:** routing only, no physical constant, so no gate — but it moves every
browser-lane design with a hole or notch, so it is Kent's flip (MASTER_SCOPE
defect 52, Waiting on Kent 22).

**How to apply:**

- Not built: travel under cover (how Python avoids most of the cuts) and row
  stagger. Either is a clean follow-up; neither is a flip.
- To ask "is this ground clear", walk the MOVES (`threadThrough` in
  `test/fill.test.js`, `threadAcross` in `test/digitize.test.js`). Skip the
  `end` record: it sits at the origin, inside a centred hole.
- `fabricForGarment()` returns a preset ID, not the preset. Pass
  `getFabric(fabricForGarment(id))`, as `generate.js` does; a bare string is
  truthy and silently takes the fabric path with every field undefined.
- The session that found this was a second, parallel one. What was actually
  needed first was not new work: two armed PRs sat stuck (one red on a
  260-char memory line, one conflicted), three lanes existed only on the
  laptop, and COOKBOOK still told readers the DST writer was transposed.
  `gh pr list`, a lane sweep and a stale-claim pass come before features.

Related: [[orphan-lane-sweep-2026-09-30]],
[[concurrent-session-designed-the-same-tool-2026-09-17]],
[[check-shipped-before-building-2026-09-29]].
