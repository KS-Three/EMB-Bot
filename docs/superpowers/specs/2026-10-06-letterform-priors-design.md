# Letterform priors — make a low-res letter letter-shaped before construction (2026-10-06)

**Status:** design brief, Kent's pick 2026-10-06 (over text-scoped halo dissolve
and over wiring outline-cut; the sibling lane `claude/outline-cut-columns` is
NOT this and must not be touched). First deliverable is a **spike**: standalone
code under `digitizer/tools/letterform_priors_spike/`, a write-up, sheets for
Kent. Wiring into stage 4/5 is a second decision, default-OFF, his flip.

## Why

Kent, 2026-10-05: lettering "looks like worms"; he wants "structured, smooth
flowing lettering". The outline-cut spike (`docs/outline-cut-columns-2026-10-05.md`
on its lane) takes a column's rails from the outline and found its own ceiling:

> **Blob outlines from low-res input.** Bridge, and BECKER's outlined band.
> The letter is not letter-shaped before construction starts. No cut rule
> fixes this.

All five of its Becker failures after the second look are the BECKER band;
bridge got *worse* when its blobs were cut. Becker's upload is a 146 px
trace (about 0.55–0.66 mm per source pixel at 95.7 mm). Stage 4 tracks that
raster faithfully — the sub-pixel read (`subpixel_edges_upscaled`, ON) puts the
polygon on the ramp, but the ramp of a 0.6 mm pixel is not a letter's edge.
A professional tracing a blurry logo draws straight stems, true arcs, one
stroke width, one baseline. Nothing in the engine does that for real
lettering: `regularize_text_clusters` redraws only the rescued-small door at a
shared stroke width (textcluster.py; read it first — build beside it, never a
second copy).

## The idea

For each lettering group (`_lettering_groups`, textcluster.py), refit every
member's traced polygon to typographic primitives under word-shared
parameters:

- **Primitives:** straight segments and circular arcs (no free splines).
  Corners between primitives are explicit vertices.
- **Word-shared parameters:** stem direction = the group's house line + slant
  (`satin_house_from_line` / `satin_house_anchor` already compute line and
  slant — reuse, do not re-derive); one stroke width per word (or a small
  set: stem / hairline), stems snapped parallel; shared baseline and cap /
  x-height lines; counters keep their minimum opening.
- **Tolerance tied to the source pixel:** a vertex may move at most
  `k × source_px_mm` (k about 0.75, to be measured), so a clean upload
  (enthusiast, 0.068 mm px) is **byte-identical** and only a low-res one is
  touched. This is the rule that keeps the customer's font: the fit may not
  invent what the raster could not have carried.
- **Refuse when the fit does not explain the shape:** residual over tolerance
  on more than a small share of the outline → leave that letter alone and
  say so (per-letter, not per-word).

The output is a polygon with the same shape_id and meta, so everything
downstream (stage 5, stage 6 satin today, outline-cut tomorrow) reads it
unchanged.

## Scope

In: text-tagged regions on the seven `REAL_ART` logos the outline-cut spike
used (becker, fremont, enthusiast, tires, bridge, gaulke, drone — see its
`run.py` for the exact `CASES` table and rebuild inputs the same way on
**current `origin/main`**). Fixtures where it should bite: Becker (band and
MARINE), bridge, gaulke's first S. Fixtures where it must not: enthusiast,
drone's PRECISION/THERMAL.

Out: script lettering (not text-tagged — ruled, `bridge-border-and-script`),
the width floor for tube letters (ROADMAP gate 1, a sew-out constant), halo
strands (defect C, its own lane if picked), any stage-6 change, any default
change.

## Go / no-go (measure before claiming)

1. **Clean art untouched:** enthusiast and drone polygons byte-identical
   (hash the WKB) with the refit on.
2. **Against the pro where he exists:** Becker's pro DST/PES in `scratch_kent/`
   (the outline-cut lane's scratch `wlib.py` loads them; copy the loader, it is
   not committed). Per letter: Hausdorff and IoU of the refit outline vs the
   pro's sewn outline, beside the traced outline's. A refit that moves AWAY
   from the pro on any letter is a finding, not a tuning target.
3. **Structure stats, before/after:** primitives per letter, stem-angle
   spread within a word, stroke-width CV within a word (the instrument
   `regularize_text_clusters` already measures width — reuse).
4. **Downstream, both engines:** feed refit polygons to today's stage 6
   (`tools/edge_wobble.py`, `tools/rail_edge.py --bare`) AND to the
   outline-cut spike's `batch.py` (read-only use of that lane's committed
   tools; copy, don't edit). The question is whether its failure class 2
   clears: Becker band letters pass its over-long check, bridge stops
   getting worse.
5. **Sheets for Kent:** per letter, artwork / traced polygon / refit
   polygon / pro where available, at a size he can judge. Do not tell him
   which side looks better before he has judged it.

Numbers from any check tuned on the fixture it measures are not evidence
(the outline-cut lane's own lesson). Keep a held-out logo untouched by every
threshold.

## Constraints

- ROADMAP gates: this is geometry, not a physical constant (gate 1 does not
  apply); nothing flips ON (gate 3); no stage-0 work (gate 2).
- Public repo: inputs and sheets hold client artwork — keep them in a
  gitignored `scratch_letterform_priors/` in the lane; commit code with
  machine paths removed and the write-up only.
- Patent note from the sibling lane: Adobe US11704848 covers medial-axis →
  stroke width → stroked path. Outline refit to primitives is a different
  method; record anything that looks adjacent, read no full claims
  (counsel's question).

## Deliverables

1. `digitizer/tools/letterform_priors_spike/` — the fit, a `run.py` that
   rebuilds inputs, a `batch.py` that runs all seven and prints the go/no-go
   table, a sheet renderer. Tests for the pure-geometry parts (tolerance
   rule, byte-identical pass-through, arc/segment fit on synthetic letters).
2. `docs/letterform-priors-2026-10-06.md` — same shape as the outline-cut
   write-up: status, why, idea, what it does, results table, failure classes
   largest first, tried-and-backed-out, not built, caveats, how to pick up.
3. A PR, ready for review, auto-merge armed, body carrying the table and the
   recommendation: wire it (where, behind what flag) or stop, with the
   evidence either way.
