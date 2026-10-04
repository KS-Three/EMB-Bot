---
name: fill-columns-2026-10-03
description: "2026-10-03 — the browser (JS) fill laid thread across every hole and notch, unseen by its test and (unless Jumps is on) by the Studio; `fillColumns` built OFF (Kent's flip, not sewn); three builds, the first two failed independent audits; what it costs and what each failure taught"
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
and a float has none. The Studio's field draws jumps only with its **Jumps**
toggle on, and that is off by default; with it on, 77 dashed lines cross the
12 mm cut-out. (First written as "the preview cannot show it, `render.js`
draws no jumps". `render.js` is the PDF sheet's renderer; the field is
`app/src/lib/preview.js`. Grep the app for the word before saying what the
screen cannot do.)

**What is built (OFF).** `tatamiFill({ columns: true })`: a port of
`stage6_fill._columns`. Every move of every pass of a fill shape is asked
what ground it runs over (`groundUnder`), the ground being what the FILL
covers. On it: may float. On the rim, no deeper than a fill row: sewn. Deeper:
the thread goes round (the hole's own edge; in by a strip's far end; the
shortest way through the columns' corners) and is cut only with no way round.
`buildQualityDesign({ fillColumns })` applies it to FILL shapes only. Sheet
and cost tables: `docs/renders/fill-columns-2026-10-03/`.

**Three builds, three audits, and each audit failed the build before it.**

1. Twenty tests passed. An independent audit (own clipper, 11,724 fills)
   found underlay rows 1.7 mm inside a cut-out ("under one pitch" was the
   pass's OWN pitch), a T left to the old walk, and a plain square gaining a
   cut (tested against the true outline, not the pull-compensated one).
2. The rebuild cut instead of crossing. A second audit found it sewing across
   a 1 mm slot (the tolerance was "the pull compensation", but a thin hole is
   not shrunk), edge runs 0.6 mm inside holes on enlarged designs (an inset
   in px), 306 rim-grazing floats, and 35 to 122 cuts on a 36-hole badge with
   2,025 holes taking 94 s. Its own cost table had said 42.
3. This one travels. 255 designs: floats off the fill's ground 16,550 → 0,
   designs with thread deeper than a fill row off it 242 → 0, the badge's
   cuts 1 → 0 on every preset at any angle. Stitches +1% to +14%. A third
   audit (12,880 designs, all seven presets, three scales) found the ground
   test itself wrong: a move along a line the shape's own corners lie on was
   read differently in its two directions, and the sheet's own wide U under
   terry sewed 14.8 mm of fill across its notch. Also an island's edge run on
   the hole side, 14 s of build on 2,025 holes at 30° (one loop; now 1.5 s),
   and "no cut on a holed shape", which was 95 of 3,317 keeping one. Fixed in
   the same PR; what it costs in travel is in the README because that audit
   was asked to measure it.

**Why:** routing, so no gate, but it moves every browser-lane design with a
hole or a notch, and it has NOT been sewn. Kent's flip: MASTER_SCOPE defect
52, Waiting on Kent 22.

**How to apply:**

- A change to stitch geometry gets an independent re-measure before it is
  armed, with the claims handed over as claims, and again after a rebuild.
  Tests written beside the code share its blind spots: mine boxed the middle
  of the hole, ran at one scale, and priced cuts on one drawing at one angle.
- The cheap way to keep thread off a place is to cut it. Count the cuts by
  WHERE they are, at the angle the engine picks and at one it does not.
- Run the seeded random shapes (`test/fill.test.js`, "shapes nobody chose")
  with thousands, not the suite's 150, after any change to a rule; and mutate
  the rule. Two rules of the third build were wrong and green: travel put a
  stitch on every vertex of a traced curve, and a check I removed as
  unreachable was reachable.
- Ask a geometric test both ways round, on whole-number shapes, and sweep
  EVERY preset (`FABRICS.FABRICS`), not three. My 9,000 random shapes never
  ran a move along a line of corners; terry was the preset that sewed the
  fill upward.
- "None" needs its denominator. Say "95 of 3,317", and where they are.
- Before an audit, list what you have NOT measured and ask for it as a
  number. Here that was travel over sewn rows and thread piling on rims.
- To ask "is this ground clear", walk the MOVES and measure depth from the
  edge of what the fill COVERS (`offCoverMm`, `floatsOffCover` in
  `test/digitize.test.js`), floats apart from sewn thread. Skip the `end`
  record: it sits at the origin, inside a centred hole.
- `fabricForGarment()` returns a preset ID. Pass
  `getFabric(fabricForGarment(id))`, as `generate.js` does; a bare string is
  truthy and takes the fabric path with every field undefined.
- Never `git stash` in a worktree here to compare before and after: the
  stash stack is shared by every lane. Copy `src/` to a scratch folder. And
  `sed -i` from Git Bash rewrites a file's line endings; use the Edit tool.
- This came from a second, parallel session. What was needed first was not
  new work: two armed PRs stuck, three lanes only on the laptop, COOKBOOK
  still saying the DST writer was transposed. `gh pr list`, a lane sweep and
  a stale-claim pass come before features.
- Before changing how thread is routed, count the cuts by WHERE they are:
  inside a pass, on the float into it, on the float out, and what kind of
  run is either side. Two fixes went to the walk's inside; the most of any
  kind (2,261 of 14,190) was the float OUT of an underlay into a pass the
  plain walk sews, which nothing asked about, and telling the pass where the
  thread goes next
  took it to 13 (2026-10-04). The next most, edge run into a plain walk
  (2,342: 1,680 a fill, 662 an underlay pass), is not the walk's at all and
  is still there.
- A greedy walk's result turns on where it starts. Walking it again from the
  other starts, only when it comes out cut, and keeping the fewest cuts,
  moved no design of two sweeps that did not lose a cut. Count the caller's
  cuts too (the float in, the float out), or a cut is moved and called saved.
- "No design of my sweeps" was not "no design". Its re-measure drew mazes,
  spirals and long combs, which 56,120 designs of combs, badges and letters
  did not have, and found: a walk that saved a cut by stranding a row (one
  stitch, cut to and cut from), so a walk is now judged by its short threads
  as well; 615 cuts on a 100-tooth comb that no option sews with 1 (the
  good walks begin at an END of the pass, and the tries are nearest first:
  not built); a pass of 2,003 columns walked nine times for nothing; and a
  fill that lays 404 mm more travel to save one cut. When a rule keeps "the
  best" of several walks, say what best does NOT count, and sweep for it.
- Run ALL of `node --test`, not the files being changed: a stagger test and
  a census tool wrapped `tatamiFill` and took a new null-returning question
  for a pass. Green on two files, red on the suite.

Related: [[orphan-lane-sweep-2026-09-30]],
[[concurrent-session-designed-the-same-tool-2026-09-17]],
[[check-shipped-before-building-2026-09-29]].
