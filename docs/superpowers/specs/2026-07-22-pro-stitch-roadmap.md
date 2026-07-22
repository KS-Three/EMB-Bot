# Pro-Stitch Roadmap — Queued Build Spec

**Date:** 2026-07-22 · **Owner:** Kent · **Decisions:** garment auto-picks fabric
(with override dropdown); auto angles + per-color override; build order below.

Craft principle for all phases: the tool encodes known digitizing rules as
presets and exposes knobs; Kent's on-machine sew-outs are the feedback loop.
When a preset proves wrong on real fabric, we adjust the preset, not the file.

## Phase 1 — Trims + Sequencing  ← BUILD FIRST (stitchability defect)
Current files never command a trim: travel is jump-only, which drags thread
loops across the design on a real machine. Pro files trim deliberately.
1. **Trim commands:** new `{type:"trim"}` handling. DST: emit the Tajima
   convention — 3 consecutive zero-delta jump records (machines read ≥3 jumps
   as trim). EXP: zero-delta `0x80 0x04` control. PES: best-effort (existing
   long-form jump flag).
2. **Trim policy in `buildQualityDesign`:** trim before any travel longer than
   `trimAtMm` (default 3.0mm, later fabric-preset-driven) and before every
   color change. Short hops stay jumps (excess trims slow the machine).
3. **Nearest-neighbor shape ordering:** within each color block, order shapes
   greedily by centroid proximity (start each block at the shape nearest the
   previous end) — shorter travel, fewer trims, fewer registration errors.
4. **Cap center-out:** when the garment is `hat_front` (or `beanie`), order
   each color block's shapes center-out (|x-centroid| ascending, bottom-up
   tiebreak) — crown distortion control.
Acceptance: decoded DST of the flattened drone logo shows trims at long
travels (dozens, not thousands); shape order measurably shortens total travel;
cap mode reorders center-out; suite green.

## Phase 2 — Fabric presets → pull comp + underlay
1. `FABRICS` table: structured-cap, pique-knit, jersey/tee, fleece/sweatshirt,
   canvas/tote, towel(terry), woven-dress. Each: `{pullCompMm, underlay
   style(s), densityAdjust, trimAtMm, notes}`. Garment→fabric default mapping
   (hat→structured-cap, left_chest/polo→pique, sweatshirt→fleece, tote→canvas,
   towel→terry, blanket→fleece, patch→twill…), Fabric dropdown overrides.
2. **Pull comp for fills:** outset each shape's outer ring (and inset holes)
   by `pullCompMm` along the axis PERPENDICULAR to that shape's stitch angle
   (pull is along the stitch axis; compensation widens across it). Polygon
   offsetting: per-vertex normal offset with miter clamp — adequate for traced
   art; note limits on sharp concave spikes.
3. **Underlay styles per fill type:** center-run (narrow satin <2mm), zigzag
   (satin 2–3mm), edge-run + lattice (fills), double-lattice (fleece/terry).
   Selected by shape type + fabric preset; overridable.
Acceptance: presets change emitted geometry/underlay verifiably in tests;
sew-out tuning loop documented in README.

## Phase 3 — Stitch direction & sheen control
1. Keep PCA auto-angle; add **per-color angle override** dial next to each
   flatten swatch (blank = auto).
2. Smarter auto: same element keeps one angle; adjacent same-color shapes get
   deliberate contrast (e.g., ±30°) so surfaces read separately; long thin
   fills align to their axis.
Acceptance: angle override round-trips to stitches; auto rules unit-tested.

## Phase 4 — Sequencing polish (push/pull-aware)
Background-before-border element ordering within colors, center-out for large
fills on all garments, optional "minimize color changes" toggle that groups
same-thread blocks when design allows (vs. strict light→dark).

## Out of scope (unchanged)
Per-stroke satin lettering (skeletonization), SVG import, stitch simulation
with fabric physics.
