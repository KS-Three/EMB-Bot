---
name: hairline-keyline-bean-2026-11-13
description: "2026-11-13 — `border_from_outline_hairline_run` built OFF (Kent: \"Build guard, OFF\"): a 0.4 mm art keyline sewed as 1.5 mm satin loops (OUTLINE_WIDTH_MM floor); ON it is a bean on the vector centreline, corner-exact, sewn last, fill held to the line"
metadata:
  type: project
---

# Hairline keyline as a bean (`border_from_outline_hairline_run`) — 2026-11-13

**What Kent showed.** A Studio render of a red wordmark with a thin white
keyline (a screenshot, the file is not in the repo and the logo is third-party
art: do not name or commit it). The white sewed as a fat satin border, the
small letters were a blob. He then showed the original.

**Cause, traced by eye stage by stage** (`debug_dir` dumps, main `bb5655bf`
and again on `49bb5a2b`). Stages 0-4 are right. `border_from_outline` reads
the white keyline as an art outline and sews a satin loop at the art's band
clamped to `machine.OUTLINE_WIDTH_MM` (1.5, 2.5). The art's keyline is
0.36-0.42 mm at 100 mm wide, so every loop sewed at 1.50 mm (white satin
median stitch 1.51), 3.7x the art. The floor is fixed, so at 60 mm it is
relatively fatter. The 1.5 floor was read off outlines of 0.8 mm and up.

**Kent's rulings, verbatim.**
- "Build guard, OFF (Recommended)" (the flag, default OFF; the flip is his).
- "When you are doing bean stitch outlines, you need to look at it as if you
  are building a swiss watch, and not a playhouse out of logs." Said when the
  first build sewed the keyline as the hairline tier's raster-skeleton run.

**What was built** (`digitizer_core/keyline_bean.py`, PR from lane
`hairline-keyline-guard`).
- Gate: an art outline that is a ring the hairline tier's width gate admits
  whole (`stage6_hairline.measure` `shape_admit`, 0.6 mm at 40 wt), plus every
  other thin ring of the same thread (a dot's keyline is too short a loop to
  be an outline). No new constant.
- Path: each body's vector edge (a hole of the keyline polygon) moved out by
  half the band's width, mitred. Never a raster skeleton.
- Stations: a needle point exactly on every corner (`curve_fidelity.CORNER_DEG`),
  even stations between at about `BEAN_STITCH_MM`, loop closed on its first
  hole, `BEAN_PASSES` passes in the same holes.
- A band two bodies share is sewn once: the later loop sews only its own
  arcs, each ended in a hole the first loop made.
- `sew_last`: keylines move to the last layers (before stage 5). Without it
  the brackets' fill sewed after the white and buried it.
- `hold_bodies` / `body_limits`: no body's fill passes the bean's needle line.
  Stage 5's underlap plus pull put the fill 0.5 mm outside the line; the
  outline-body path in stage 7 also regrows a `satin_tier` body by the pull
  and needed the same hold.

**Measured on Kent's screenshot** (scratch instruments, not committed).
- 100 mm: stitches 7,620 OFF, 6,684 ON; colour stops 4 to 3 (the two red
  layers now merge). 60 mm: 4,215 to 3,320.
- Every loop closed, corner miss 0.0000 mm, stitch 0.54-0.81 mm (100 mm),
  fill past the line 0.00 mm, arc ends 0.0000 mm from a laid hole.
- Against the SOURCE pixels' own white centre: needle points median 0.06 mm
  off (one source pixel is 0.095 mm), p95 0.18 mm. The residue is stage 4's
  0.2 mm `simplify_tol_mm`; curve softening made no measurable difference.
- Corpus: 16 paired jobs hold 8 art outlines, thinnest 1.25 mm (2A/P); the
  guard takes none. So nothing in the paired corpus moves, and no pro file
  says what a digitizer does with a 0.4 mm keyline.

**Open.**
- Gate 1: where the fill meets the line on fabric (the fill is held at the
  bean's centreline, so pull-in may open a hair of cloth) is a sew-out
  question.
- Finer than 0.18 mm p95 needs a finer trace of the keyline than stage 4's.
- The screenshot's putty page inside the counters sewed as cream thread; the
  real file may differ. Not this flag's.

**How to apply:** a bean outline is judged at needle-point precision: corners,
closure, shared holes, what sews after it, what shows past it. Render it
zoomed with the art's edges drawn in before calling it done. Related:
[[eye-first-diagnosis-2026-11-13]], [[border-from-outline-line-art-guard-2026-10-25]],
[[outlined-bean-ink-2026-10-27]].
