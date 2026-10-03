---
name: fill-columns-2026-10-03
description: "2026-10-03 — the browser (JS) fill laid thread across every hole and notch, unseen by its test and by the preview; `fillColumns` built OFF (Kent's flip); the first build passed 20 tests and failed an independent audit three ways; what the cuts cost and where"
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
shows a clean hole.

**What was built (OFF).** `tatamiFill({ columns: true, openTol })`: a port of
`stage6_fill._columns`, each column its own boustrophedon, a level finished
before the walk descends. Every move (to the next column, a row turn, between
two runs of a shape) is asked what ground it runs over (`groundUnder`).
Inside the fill: it may float. On the rim, outside but no deeper than
`openTol`: sewn, never floated. Deeper: cut. `buildQualityDesign({
fillColumns })` applies it to FILL shapes only. Sheet and cost tables:
`docs/renders/fill-columns-2026-10-03/`.

**The first build was wrong and green.** Twenty tests passed. An independent
audit (own clipper, 11,724 fills, 1,980 designs) found: underlay rows 2 mm
apart sewing 1.7 mm inside a cut-out, because "under one pitch" was the
pass's OWN pitch; a T left to the old walk because no row of it forks; and a
plain square gaining a cut because the test was against the true outline, not
the pull-compensated one the fill covers. It also priced the cuts (a 36-hole
badge 1 → 79–143), which is what led to the level-first order.

**The rebuild missed one more, also green.** Depth was the wrong single
question: the turn at the step of a T runs along the step's edge, under a
fill row out, and the plain walk FLOATS it (6–28 mm, 35 of 165 notched
designs). Found by re-measuring floats and sewn thread separately, against
the exact pull-compensated rings (`DG.offsetRing`), before asking for the
re-audit. Now 16,550 → 0 over 255 designs.

**Why:** routing only, no physical constant, so no gate — but it moves every
browser-lane design with a hole or notch, and it costs cuts: one per ROW of
holes in the fill, about one per hole in an edge-run underlay, one per strip
in a tatami underlay (that badge: 42 on pique, 76–94 elsewhere). No cut in
the JS lanes is locked. Kent's flip: MASTER_SCOPE defect 52, Waiting on Kent
22.

**How to apply:**

- Before flipping for hole-heavy art, build travel that follows a hole's
  EDGE (Python: `_ring_route`); it removes most underlay cuts. Row stagger is
  the other unbuilt half.
- A change to stitch geometry gets an independent re-measure before it is
  armed, with the claims handed over as claims. The repo's
  `stitch-geometry-auditor` brief is the template. Tests written beside the
  code share its blind spots: mine boxed the middle of the hole.
- To ask "is this ground clear", walk the MOVES and measure depth from the
  edge (`openGroundMm` in `test/digitize.test.js`), and count floats apart
  from sewn thread (`floatsOffCover`). Skip the `end` record: it sits at the
  origin, inside a centred hole.
- Never `git stash` in a worktree here to compare before and after: the
  stash stack is shared by every lane. Copy `src/` to a scratch folder.
- `fabricForGarment()` returns a preset ID. Pass
  `getFabric(fabricForGarment(id))`, as `generate.js` does; a bare string is
  truthy and takes the fabric path with every field undefined.
- This came from a second, parallel session. What was needed first was not
  new work: two armed PRs stuck, three lanes only on the laptop, COOKBOOK
  still saying the DST writer was transposed. `gh pr list`, a lane sweep and
  a stale-claim pass come before features.

Related: [[orphan-lane-sweep-2026-09-30]],
[[concurrent-session-designed-the-same-tool-2026-09-17]],
[[check-shipped-before-building-2026-09-29]].
