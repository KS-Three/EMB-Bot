---
name: inside-stagger-2026-10-23
description: The inside of a satin pivot (L fold corner, S curl) read with one rule on the pro's DSTs and ours. The pro ALSO alternates short stitches; what separates us is that our full-length inner ends pile into one hole (16-79 re-entries per band vs his 2-5) and our short stitch is 35% deep vs his ~20%. Built as `lettering_columns_inside_stagger` (OFF). The "0.6-0.7 mm progressive spread" in #1054 was a reader-window artefact.
metadata:
  type: project
---

2026-10-23, lane `claude/inside-stagger-folds-66ecde` (task L2), stacked on
#1054 (corner folds). Renders and table: `docs/renders/inside-stagger-2026-10-23/`.
Reader: `tools/inside_stagger.py` (pivot zones: four or more stations whose
inner ends stay in a 0.6 mm disc while the crosses sweep 50 deg; long end =
local max of cross length, short = local min).

**The brief's premise measured half-false.** "His inner ends spread
progressively 0.6-0.7 mm instead of alternating" came from
`pro_corner_folds.py`, whose 0.45 mm window caps the spread at 0.9 by
construction; at a 0.6 window his zones and ours both read 0.8-1.0. The pro
alternates too (cross-length alternation 0.75-0.83, short frac 0.28-0.40).
What separates us: (1) his full-length inner ends step ~0.3 mm (median
0.28-0.32 between long ends, under 0.1 mm in 2-7%) and almost never share a
hole; ours piled (28-56% of long steps under 0.1 mm on Drone/MFab/Proseal;
same-hole re-entries per band 16-79 vs his 2-5). (2) his short stitch is
~20% of the cross (0.29 mm at Fremont's 1.4 mm, 0.57 at Becker's), ours
27-36% (the guard's 35% capped 0.6 mm). (3) Fremont crosses under 1 mm at
pivots: ours 37, his 8. The director approved the replacement rule.

**Built:** `columns._inside_stagger` replaces `_short_stitch_guard` under the
flag. Short: a crowded step (under `SATIN_SHORT_STITCH_AT_MM`) pulled 20% of
its cross, gaps of one then two full crosses in turn (two in five), shorts
applied last, each against the far rail AS SEWN, so two crowded rails never
pull one cross under the floor together. Pile: a stretch of ends each within
a crowded step of SOME end already in it (not only the previous one), holding
a step under 0.1 mm; its full ends spaced evenly along the course from the
end before to the end after, through the rail's ends in order but only those
that go ON along the lo->hi chord, widened up to two stations into each leg
for 0.3 mm each. The windows never overlap (`floor`).

**Traps, each hit once:** a slide square to each cross turns with the cross
and walks ends back over their own holes. A greedy "0.3 past the last full
one" hits its cap and re-piles at the cap. Sub-clusters 0.3 apart (the pull
pushes each fold cross along its own direction) split a step-based stretch
into overlapping windows. A centroid course spikes out past the corner and
back (Fremont's pushed pile sits ~0.3 outside the corner). Unbounded widening
re-spaced 3 mm of leg at 0.3 and leaned its crosses. Spreading the ends can
make a zone vanish from the reader (Drone "on" 4 -> 2 zones): quote the zone
count beside every number.

**Why:** the pile is a needle re-entering one hole, which cuts thread and
fabric. **How to apply:** read pivots with `tools/inside_stagger.py`, one
rule on both files, and never quote a spread that a reader's window sets.

Related: [[column-corner-folds-2026-10-23]], [[lettering-5-10mm-band-2026-10-23]],
[[layout-judged-in-preview-2026-10-22]], [[rail-wobble-is-the-models-floor-2026-09-21]].
