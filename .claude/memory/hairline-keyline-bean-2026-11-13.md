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

**Second pass, same day (Kent: "Show me more comparisons of on vs off, why
are you recomending to keep off?").** The real file IS in the repo:
`digitizer/testdata/art/commons_lettering/hed_p_e_logo.png` (transparent
ground, so no cream counters). OFF | ON sheets on it at 40-140 mm and a scan
of 22 repo logos at 60 and 100 mm found four faults in the first build, all
fixed in the follow-up PR:
- 40 mm: the word's hold was refused (the cut split its polygon at a neck),
  fill 0.62 mm past the line. `held` now bridges the pieces at the neck only.
- 40 and 127 mm: a white counter body stayed in its old layer, 4 colour stops
  for 3 threads. `sew_last` takes a body of the keyline's own thread along.
- 150 mm: rings either side of the gate, bean and satin mixed in one design.
  The gate is now per THREAD (outlines pooled, 2A/P).
- The gate took any thin ring. To-a-T Machine at 50-60 mm: the black frame
  the pro borders in satin went to a wire, its O and A to hollow outlines.
  Commons "Ahora" at 50-60 mm: the white gear lost its teeth. Now a thread
  must be nearly all keyline (rings >= `OUTLINE_REACH_FRAC` of its sewn
  area: the logo 0.98-1.00, To-a-T 0.23) and its outlines' plain width under
  the gate (the gear 0.72-0.86 mm). Neither is taken; of the 22 only the
  logo is.
Real file, OFF -> ON stitches: 40 mm 2,064 -> 1,544; 60 mm 3,492 -> 2,527;
100 mm 6,291 -> 5,228; 127 mm 9,099 -> 7,267; 3 colour stops both ways. Over
about 145 mm the keyline passes 0.6 mm and sews the 1.5 mm loop again.

**Third pass: the prompt and the flip (same day).** Asked what to do with
the outline, Kent: "When it gets digitized can you have items like this
throb/pulse and glow (ask user to keep or remove)". Asked what the first
digitize shows: "sewn thin, but do not include letters for this". So:
- The flag is ON by default (PRE_FLIP pins False). A ring the lettering lane
  takes (`columns.is_lettering`) is never a keyline.
- The engine marks the shapes (`meta["hairline_outline"]`, wire
  `review.shapes[].hairline_outline`, contract v1.10), sewn or not.
- Studio (`app/src/lib/outlinePrompt.js`): marked, sewn, unanswered shapes
  glow green on the canvas and the panel asks Keep / Remove under the stats
  line. Keep = `keptOutlineIds` (never stale). Remove = `deletedShapeIds`
  (stitches go at once, restorable). Then "Put back".
- Real app, the logo at 95 mm: 11 shapes, 4,856 stitches, Remove 3,098.
- Traps hit: the prompt first sat beside the attention warnings, which live
  inside Advanced (shut by default), so the real app never showed it;
  `preview_start` serves the MAIN checkout, not the lane (use the driver's
  `--serve` from the lane); port 8721 was another session's service (ran
  mine on 8741 with localStorage `embstudio:digitizerUrl`).

**Lesson.** I recommended OFF on thin grounds (one logo, a screenshot). The
ground that mattered only showed when the flag was run on OTHER art: run a
new flag across every repo logo and LOOK before recommending either way.

**Open.**
- Gate 1: where the fill meets the line on fabric (the fill is held at the
  bean's centreline, so pull-in may open a hair of cloth) is a sew-out
  question.
- Finer than 0.18 mm p95 needs a finer trace of the keyline than stage 4's.
- The cliff near 145 mm: a 0.62 mm keyline sews 1.5 mm satin (2.4x). Nothing
  between 0.6 and To-a-T's 0.8 mm has a pro file.
- A dot's or counter's body that sews satin still passes the line by 0.3 mm
  (rails carry the pull); only plain-fill bodies are held.
- The real file's bodies snap to two reds (2011 and 1335). Not this flag's.

**How to apply:** a bean outline is judged at needle-point precision: corners,
closure, shared holes, what sews after it, what shows past it. Render it
zoomed with the art's edges drawn in before calling it done. Related:
[[eye-first-diagnosis-2026-11-13]], [[border-from-outline-line-art-guard-2026-10-25]],
[[outlined-bean-ink-2026-10-27]].
