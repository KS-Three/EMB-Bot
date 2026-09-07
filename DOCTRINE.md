# EMB-Bot — Doctrine

**What this is:** the standing content split out of `MASTER_SCOPE.md` on
2026-08-28 — what has already been **decided, tried, disproved, or paid for**.

Companion to [`MASTER_SCOPE.md`](MASTER_SCOPE.md), which carries current status
only. The two answer different questions and age differently: status goes stale
in days and lives under an 800-line budget; doctrine does not go stale and only
ever accumulates. Sharing one budget meant every new ruling competed with
current status for space, and status was losing — MASTER_SCOPE ran 268 lines
over before this split, and two compaction passes could not close the gap
without deleting content that still governs decisions.

**So this file has no line budget. It has a different rule instead:**

> Nothing enters unless it would change what someone DOES — a ruling, a
> rejected approach, a correction, a trap that cost a session. A measurement
> belongs in [`docs/scope-history.md`](docs/scope-history.md); a status belongs
> in [`MASTER_SCOPE.md`](MASTER_SCOPE.md).

**Every claim keeps its pointer** in the form `(verb date — source)`:
`confirmed` means checked against code or a passing test, `measured` means a
number was produced, `suspected` means neither.

**Do not tidy the Corrections section away.** It records suspicions this project
raised and then disproved, and it exists precisely because a parenthetical hedge
gets dropped when a sentence is rewritten while a verb cannot be. Two hedged
observations there hardened into stated defects before measurement disproved
both.

Moved verbatim 2026-08-28 — no section was rewritten in the move.

---

## Standing rulings — decided, do not re-litigate

- **Fill row spacing is settled: 0.15 mm, the professional's pitch.** Kent's
  call 2026-09-03 on two pieces of evidence, one of them cloth — his first
  stitch-out at 0.40 showed fabric between every fill row, and the
  commissioned files in `Embroidery Files.zip`, read as ROWS
  (`tools/row_pitch_union.py`, the union of every pass), lay their fills at
  0.141 (Hotel Fremont patch ground, one pass), 0.169 and 0.166 mm (both
  Becker letter bodies). `machine.FILL_ROW_MM` is 0.15; fabric presets still
  scale it. The coverage grader's thresholds are re-based in FILL LAYERS
  (`COVERAGE_FILL_LAYER_UNITS`), so every coverage number recorded before
  this date is 2.67× smaller than the same stack reads today. Sew-out card
  block 2 now verifies the ruling rather than deciding it; stiffness and
  pucker on light fabrics are the accepted risk, and a fabric that puckers
  gets a preset, not a different constant. **Do not quote
  `tools/fill_pitch.py` on a professional file** — its per-pass
  autocorrelation reads a tatami's penetration cycle, ~2.7× the row pitch.
  ROADMAP gate 1 keeps every other physical constant. *(Kent's call
  2026-09-03 — `docs/sewout-findings-2026-09-03.md`; scope-history
  2026-09-03)*

- **A gradient design whose ramp fits is ONE sweep — segmented as one region
  per piece, sewn as one set of shade bands.** Kent's call 2026-09-03 on the
  sew-out's blocky bands ("one region when the design ramp fits").
  `design_ramp.fit_design_ramp` decides: a trimmed-then-consensus PLANE per
  Lab channel over the stitched foreground, passing only at r² ≥ 0.4 on the
  consensus, ≥ 60% of the foreground riding it, a robust scatter ≤ 4 Lab
  units (under half a shade step) and a sweep of at least one shade step.
  The sweep's COLOUR is a profile along its axis, not the plane (a hue
  rotation is an arc in a*b*); the plane gates, the profile flattens. Stage
  2 then merges on Lab with the sweep subtracted, and stage 6 sews every
  region that rides the ramp with the DESIGN's bands — one shade count, one
  thread set, band edges at the same millimetres in every piece — and a
  riding region never takes the satin rung. A design the gate refuses is
  untouched, its shared fill angle included (the plain fit stays as the
  angle's fallback). **Do not widen the gate to catch busy logos** — drone,
  summit, `region_blobs`, the owl are what it exists to refuse (a coarse
  trend across flat colours is not a sweep; flattening by it merges what the
  segmenter keeps apart) — **do not gate on the profile** (the owl passes a
  profile gate), and do not move its numbers without re-measuring the
  fixture table in `design_ramp.py`'s docstring. **The radial fit (2026-09-04)
  needs three rules the plane does not:** r² ≥ 0.6 (a free centre fits
  more), at most 2 of 17 radius knots under 50% consensus (summit's vignette
  reads r² 0.93 — its emblem IS the centre, 10 knots blank), and the centre
  no farther from the foreground than the sweep is long (`lo ≤ hi − lo`: a
  huge circle is a line — the linear fixture's radial centre lands 1,250 mm
  out at r² 1.00, `lo` fifteen sweeps; a box test was tried first and is
  knife-edge for a half-disc or a corner glow, whose centre sits ON the
  edge). Radial wins only
  when it passes AND beats the plane's r², so a linear design is byte for
  byte what it was. The pass side is calibrated on ONE synthetic fixture —
  a real radial logo is the missing evidence, not a reason to loosen it. **Blend bands sew at
  `FILL_ROW_MM`, never `FILL_ROW_MM × n`:** the n× layout was one sparse
  layer per band, a third to a fifth of a fill, and PR #339's preflight
  exemption for it rested on the false premise that the layers interleaved.
  **Band seams are feathered** (Kent's call 2026-09-04, on the ruling's
  render): where rows run along the seam, a `machine.BLEND_FEATHER_MM`
  zone is sewn by both shades on one row lattice, alternating thread row by
  row, so the sweep reads as one gradient; the 0.25 mm underlap is the seam
  rule only where rows cross the bands or `blend_feather_mm` is 0. Every
  band of a region sews on ONE row lattice (`stage6_blend._emit_bands`),
  so a seam never shows a half-row step. **Blend regions sew `p.polygon`**
  (2026-09-04): stage 7 had handed the tier the region alone and it sewed
  the raw artwork — no pull comp, no tongue — on every gradient-class
  design for a month while `tools/seam_underlap.py` read the tongue as
  present, because that instrument measures stage 5's PLAN. **Prove a seam
  on the stitches** (`tools/sewn_compensation.py`), never on the plan; the
  colour is still read from the artwork, or a white neighbour's tongue
  pulls white into the sweep. **A shade band's runs are NOT named after their
  region** — `stage6_blend` stamps `<shape_id>-blend<i>` and the streamline
  tier `-shade<i>` — and every consumer that matched a region id against a
  run id went blind on gradients because of it (2026-09-04, four sites in one
  day: preflight's bare-fabric check examined NOTHING on a one-region sweep,
  its thread match scored five cones against one, and the service filed a
  gradient's sew order and its block shape ids under names no review shape
  has). `preflight._owning_region_id` is the one rule — strip the derived
  suffix, then require the remainder to be a real region id. **A prefix test
  is not a substitute:** region ids are not prefix-free (the repro plans both
  `S5afb1e0a` and `S5afb1e0a-2`), so a naive scan attributes
  `S5afb1e0a-2-blend0` to the shorter, wrong region. **A raster paints a hole half a pixel small**
  (2026-09-04): `cv2.fillPoly` paints its boundary pixels, so a hole painted
  in 0 ate half a pixel of its own edge and the satin's hole-side rail
  stopped 0.18 mm short of the outline; `shapefield.hole_px` shrinks the
  hole first, in both byte-equal raster twins (`test_shapefield`) — change
  one, change both. **Do not redraw the boundary as material instead:**
  measured to close a three-pixel counter to a speck (the drone's satin "A"
  lost its upper legs) and spur larger holes. **No physical tests until Kent
  says** (2026-09-04): the stitchviz render is the interim judge of
  quality; put before/after renders in every PR that changes stitches.
  *(Kent's calls 2026-09-03/04 — `docs/sewout-findings-2026-09-03.md`
  item 4; scope-history 2026-09-04)*

- **Bold never closes a counter, hairline faces included — the guard stays
  as built.** The font path's Bold widening is held per rail wherever a rail
  faces another across a gap the 0.5 mm cross floor cannot spare (PR #332),
  and on a hairline script at a small cap that leaves the word as satin
  fragments and runs where the old unguarded Bold read as a solid blob on
  screen with 0.06 mm gaps. Kent looked at the picture
  (`docs/renders/fine-lettering-2026-09-03/font_mai_en_fleur_bold_25mm.png`)
  and ruled: keep it. Neither version sews at that cap, the lettering note
  says so, and the screen must show the true state rather than a false
  solid. **Do not exempt hairline columns from the hold, and do not add a
  "let Bold close gaps" switch.** *(Kent's call 2026-09-03 — review doc §9
  and §11; PR #335)*

- **"Is this a photograph" lives in ONE place (`config.is_photographic`), and is
  DECLARED today only because nothing is wired to answer it yet.** Stage 0's
  COLOUR signals cannot: real photographs are the LOWEST `unique_color_mass`
  content in the corpus, *below every gradient logo* — so re-tuning that gate is
  not the answer, and would be stage-0 recalibration (gate 2) besides. **Two
  signals the repo ALREADY OWNS do separate them, and neither is a colour
  statistic:** EXIF camera Make/Model (4/4 photos, 0/9 logos) and the YuNet
  detector at `stage1_photo_prep.detect_faces_seam` (4/4 portraits, 0/9 logos).
  Each has a blind spot — EXIF dies on re-save (`owl_kent` has none), faces miss
  pets and landscapes — so the route is EXIF-or-face with the declaration as
  FALLBACK, never a checkbox as the primary mechanism. Not built.
  The gate was written in 15 places across 5 modules with `PHOTO_CLASSES`
  defined 3 times; that is how a photograph in the `gradient` lane missed the
  palette bind and was graded on the tatami yardstick. **NOT wired:**
  `effective_split_tonal` (gate 3) and `stage6_satin`'s width floor (defect 2).
  *(measured 2026-08-25 — PR #245; detail in scope-history 08-25)*

- **A photo sews FILLED — on a HIGH-CONTRAST SUBJECT. On a human face it is
  REFUTED, and faces are TABLED, not abandoned.** Lane A was answered on an owl
  and two landscapes, then tested the same day on four real portraits and
  inverted: filled quantizes a face to one flat skin field and the eyes and nose
  disappear — on one, the person vanished entirely, leaving a floating shirt.
  Thread-paint rendered both as recognisable people, at 3–4x the trims. **The
  mechanism is the subject's own contrast:** an owl's features ARE distinct
  colour regions and survive quantization; a face's are continuous low-contrast
  tone and do not. Kent: *"let's just table it for later when the tool gets more
  powerful."* The ruling stands for the content we ship against; faces are
  parked pending a more capable tier, since neither existing tier renders one
  well. *(ruled 2026-08-25 — Kent, twice; measured — scope-history 08-25)*
  **RE-VERIFIED 2026-08-26 through the fixed renderer, and it holds — harder.**
  Every arm of this ruling was judged on the PRE-FIX render, which had no light
  in it, so sparse thread drew as tidy hatching. Re-rendered lit, thread-paint's
  0.52–0.59 coverage reads as what it is — bare cloth between strokes — while
  filled is unchanged at 0.99. The old instrument FLATTERED the arm Kent
  rejected and he rejected it anyway. Coverage figures did not move by
  construction (see the `lit=False` note under "Traps"). *(re-measured
  2026-08-26 — `owl_kent` 0.991/0.594, `photo_sunset_backlit` 0.994/0.547,
  `photo_dof_meadow` 0.991/0.544, `drone_render` 0.516/0.364)*

- **Satin borders go on shapes significant AND smooth, never blanket.** *"if
  it's abrupt, it probably doesn't require a border, or is wrong."* Blanket
  `border="auto"` spends **+60% stitches to worsen the silhouette**; the
  selective rule takes 4 of 35 shapes for **+4%**. Shipped
  `border="significant"`. Abruptness is the ONLY live gate: measured per RING (a
  thin smooth ring is not abrupt) and it tracks MACRO SPRAWL, not edge noise.
  **The 3.5 cutoff is validated beyond its origin fixture** — it lands in a real
  empty gap on all four real portraits, not just the owl. **The area-share half
  is disabled (0.0)**: inert at the 80 mm it was tuned on, and at 160 mm it
  deleted 8 of 9 borders at iris scale, because a fixed share INVERTS with size
  (bigger design → more regions → smaller shares → stricter gate). Significance
  is tested downstream by `border_runs` against `BORDER_WIDTH_MM`.
  *(ruled 2026-08-25 — Kent; measured — PR #241, corrected #243)*
  **RE-VERIFIED 2026-08-26 through the fixed renderer.** Re-run on `owl_kent`:
  off 11,370 st, `significant` 11,845 (**+4.2%**, recorded +4%), blanket
  `auto` 18,138 (**+59.5%**, recorded +60%). Both figures reproduce, and lit
  rendering makes the silhouette claim plainer than it was: blanket wraps every
  shape in a heavy rim so the bird reads as a cut-out, while `significant`
  spends its 4% on the eyes. *(re-measured 2026-08-26)*

- **The satin stitch angle is DERIVED from the art, never chosen: house =
  perpendicular to the dominant stem family (where two balance, the stems
  are the family square to the LINE OF TEXT — never the bisector, and NOT
  "the longer family": THERMAL and ENTHUSIAST measure their bars longer);
  a stroke that cannot span it takes its own perpendicular, the lean fading
  to zero along the house axis rather than snapping to a side; diagonals
  lean toward the house by at most 30° (`SATIN_HOUSE_MIN_SPAN_DEG` 45 → 60);
  station spacing / cos(lean) so the 0.4 mm pitch holds across the thread;
  ≥ 45° corners get the Goldman through-member + butt-join.** Measured on the pro file (axial columns
  4.7–7.9° off perpendicular, diagonals 15.9°, p90 43°), 86 shipped fonts
  (stems 1.8°, bars 3.0°, diagonals 18°, one-angle-per-glyph in 5 of 64) and
  two expired patents. The 45° bisector `satin_house_fourfold` first shipped is
  what none of them do — it was a workaround for the ±45 side flip, and at
  fixed spine spacing it is 1.41× density (the ENTHUSIAST N pile). Do not
  re-open 45 vs 135. Pass 1 (fade, cap, density) built the same day: thread
  pitch on leaned columns 0.152 → 0.20 mm, and Kent flipped
  `satin_house_fourfold` ON on those numbers; the Goldman join (pass 2)
  built the same session — a corner is a ≥ 45° spine turn WITH a reflex
  boundary corner, joined inside one stroke, never a split into strokes
  (a split costs a trim per piece). *(ruled
  2026-09-03 — Kent, both the rule and the 30° cap; built and the line-of-
  text correction measured 2026-09-03; `docs/stitch-angle-convention-2026-09-03.md` §7)*
- **The 3 Arabic fonts can never work, engine or not:** they carry ONLY base-block
  letters and zero presentation forms. *(measured 2026-08-22 — font.json blocks)*
- **We do not rework font data to make it importable.** A candidate is either
  close to plug-and-play or not a candidate — this rejected the Hershey faces,
  and makes Terminus's under-tagged glyphs a reason to omit. *(ruled 2026-08-21 — Kent)*
- **The sellable/personal font split is at BUILD time, not runtime.** Kent asked
  for "all fonts for me, questionable ones off on the user's end"; by the time a
  viewer could flip a toggle the bytes are on their disk, so excluded fonts are
  never packaged. *(ruled 2026-08-21 — Kent)*
- **Golden re-capture is pre-authorized on Linux CI**, under same-failure-set
  discipline: a session may re-capture when the failure set is identical before
  and after, and must report the diff. Never on Windows. *(ruled 2026-08-21 — Kent)*
- **The sew-out is accepted as-is — not a scheduled to-do.** Stop treating "no
  sew-out yet" as a blocker awaiting action; dependent scores stay `pending
  sew-out` permanently, and ROADMAP gate 1 is a standing refusal, not a
  temporary one. Does NOT decide the two items parked behind it (DST codec fix,
  `split_tonal_regions`) — those need their own call. *(ruled 2026-08-21 — Kent)*
- **The shading fix goes UPSTREAM.** Two options were on the table: teach
  stage 5/7 that one region can own several thread stops, or split
  tonally-diverse regions at segmentation so the existing one-thread-per-region
  model carries them. Kent picked the second — smaller blast radius, no new
  machinery downstream. Implemented as `split_tonal_regions`
  (`stage2_photo_segment`, **default OFF**). *(ruled 2026-08-12 — scope-history)*
- **Option A for the ramp-less path: tatami + shade bands.** Add a
  darkness-based fallback at `stage6_blend.blend_fill`'s `if model is None:`
  branch so a ramp-less region still decomposes into 3–5 shades. That branch is
  the norm, not an edge case — all 25 regions of `owl_kent.jpg` land there. The
  obstacle, and where the design effort goes: `_shade_layers` returns a
  *continuous* membership function, and tatami needs actual polygons per shade.
  `_band_clip` does not help — it slices by ramp position, which is exactly what
  doesn't exist here. **Write the design before the code.** *(ruled 2026-08-12 — scope-history)*
- **Engine quality is a parallel investment, NOT a launch gate.** SAM2 ships
  post-v1 as an opt-in download. *(ruled 2026-08-11 — PRODUCT.md,
  `docs/sam2-ship-path-brief-2026-08-11.md`)*
- **Real-photo provenance is not a concern**, so real photos are cleared to land
  as corpus fixtures. *(ruled 2026-08-12 — scope-history)*
- **Draw shapes stays a right-click canvas tool**, not an upload tile — Kent's
  amendment to "remove all of the unnecessary upload buttons". *(ruled 2026-08-13 — PR #138)*
- **Leave `MERGE_DELTAE00_THRESH` at 26.0.** No evidence for retuning it on a
  real photo, and its own tuning history says a global change costs more than it
  gains. *(measured 2026-08-12 — `stage2_photo_segment.py:452-496`)*
- **Do not spend time on `stage4_vectorize`'s re-snap code.** Current-thread
  error sits within ~1 dE00 of best-possible on nearly every shape; the re-snap
  is working and has almost nothing left to win. A shape whose own pixels differ
  from each other by more than the error being complained about cannot be
  matched by any single thread. *(measured 2026-08-12 — scope-history)*
- **`photo_segment_sam2_max_side_px` stays 1024.** *(2026-08-11 — `config.py`)*
- **The photo subject cutout ships ON, and rembg is a DEPLOY REQUIREMENT.**
  `photo_prep` + `photo_prep_background_removal` default True as a PAIR, never
  singly; an unavailable cutout skips prep entirely rather than degrading onto
  prep-alone. **Ships KNOWINGLY INERT for real uploads** — all four acceptance
  photos classify `gradient` at 1.00, which the gate excludes; revisit at gate 2. *(ruled 2026-08-24 — Kent; [area 1](docs/scope/1-auto-digitizing-quality.md))*
- **`feat/svg-import-shapes` is not resumed.** Far behind, and the one task
  attempted past the tokenizer is broken against its own tolerance. Treat a
  revival as a fresh plan against `main`, not a rebase; branch left in place,
  deleting it is Kent's call. *(decided 2026-08-07 — scope-history)*

---

## Measured negatives — built or proposed, then rejected. Do not rebuild.

- **Binding the thread re-snap to the palette on every class is a REAL trade,
  not a free win — and it is not a yardstick artefact.**
  `cfg.bind_resnap_all_classes` closes defect 15's escape exactly (19 colour
  stops removed across five designs) and costs **+2 blocks net** on the shipped
  scorecard: `screenshot_phone_ui_golke` 10 -> 8, `logo_golden_tee` 2 -> **5**,
  `logo_bridge_bar` 3 -> **4**. **The hypothesis that those extra blocks were
  the gradient lane's RAW yardstick (F-wall cause 1) is REFUTED**: with the
  excess yardstick forced on every route, `golden_tee` still goes D 52 ->
  **F 22** and `drone_render` D 40 -> **F 28** — the latter with no
  thread-match block moving at all, so part of the price is the +3.1% stitches
  and their density cost, not colour. **Rule: the re-snap's chart-wide argmin
  is the pipeline BUYING colour accuracy with cones the operator must load.
  Treat it as an unpriced trade, not a bug — closing it costs colour.** Built,
  tested, DEFAULT OFF; do not flip it without a reason the corpus does not
  currently supply. *(measured 2026-09-06 — scope-history 09-06)*

- **Letting a re-snapped SHARD pick any spool on the chart costs more than it
  buys — two constructions measured, both rejected.** `cfg.
  revalidate_small_shapes` lowers `revalidate_threads`' pixel floor to
  preflight's 50 so the 50-199 px band stops being condemnable-but-uncorrectable
  (MASTER_SCOPE 28). What a shard admitted by that floor may CHOOSE from was
  measured three ways on the 26-fixture corpus:
  **(a) the whole chart** — the shipped off-photo behaviour — pulls new spools
  in: `logo_bridge_bar` 18 -> **22** cones, `drone_render` 19 -> **21**, and
  each new spool is another row `THREAD_MATCH_POOR` scores, so `drone_render`
  went **4 -> 5 blocks on cones it did not previously carry**. It is the only
  construction that ever moved a block count in the good direction
  (`screenshot` 10 -> 9) and it is not worth a regression plus four colour
  stops on a customer logo.
  **(b) the stage-2 palette** (`q.thread_indices`) — no regression AND no win.
  Measured cause: `select_palette` chose **13** spools while the design carries
  **16**, because earlier re-snaps already moved shapes outside it, so the
  palette forbids moves onto cones ALREADY ON THE MACHINE (`S967c0c7f` stayed
  on `0111 Whale` over 182-grey artwork with `0142` loaded).
  **(c) the cones the design carried at pass entry** — what ships.
  **And "never grows the cone set" is FALSE even for (c)**: `drone_render` goes
  19 -> **20** because the extra cone `0674` was in the entry set and the
  shipped pass VACATES it (its last region re-snaps away), so a shard landing
  there keeps it alive. The honest invariant is *"can only take a cone the
  design already carried when the pass began."* **Rule: a sub-1 mm2 shard is
  never worth a colour change on the machine — the choice set for a shard is
  what is already threaded, and the entry snapshot must NOT be unioned with the
  palette** (that re-admits spools nothing wears). *(measured 2026-09-06 —
  scope-history 09-06)*

- **Do not tune a threshold on `becker_marine_logo.png` — its source is
  146 x 91 px.** That is **1.46 px/mm at 100 mm**, the lowest-resolution
  fixture in the corpus by a wide margin (whitebg 800 px, enthusiast 1400,
  Fremont 2500), so one source pixel is ~0.68 mm and every width it reports is
  quantised in ~0.7 mm steps. Consequences measured 2026-09-05/06, all of
  which look like artwork properties and are not: its 17 regions cluster
  within +-0.10 of the `cv = 0.50` gate (11 of 17 at 80 mm, 16 of 17 at
  100 mm); 80 mm and 100 mm segment to region sets sharing NO shape ids; and
  `stage4_vectorize._CURVE_MIN_PX_PER_MM` (20.0) gates curve refinement off
  for it entirely at 4.0 prepped px/mm, which is the staircase visible on
  every curve in its renders and is NOT an engine defect — the detail is not
  in the artwork to recover. Becker is an excellent END-TO-END fixture (it is
  the one with a professional's own file to compare against) and a bad one for
  calibrating anything threshold-sensitive.

  **There is no higher-resolution Becker source in the repo, and the files
  that look like one are a trap.** `testdata/reference/becker_*.jpg` are
  ~810 px and CLAUDE.md calls them artwork, but each sits 1:1 beside a
  `.dst`/`.pes` and each is a STITCH-FILE PREVIEW — the professional's
  embroidery rendered on white and on black, two panels to an image.
  Digitizing one would be digitizing a picture of embroidery: it would run
  happily and produce nonsense. Making Becker's threshold numbers meaningful
  needs the original logo from Kent, not anything already committed.
  *(measured 2026-09-06)*

- **A per-stroke satin rung must treat the machine cap as a VETO, never as a
  vote.** Scoring `dt_p90_cap` per stroke and then letting an area majority
  outweigh it is a different rule, and the difference is bare cloth: measured
  2026-09-06 on `becker_marine_logo` at 100 mm, `S92a90056` (1,022 mm²) passed
  at frac 0.79 carrying 97.5 mm² of over-cap strokes, one of them **9.32 mm
  against the 5.0 mm cap**, and `_rail_points`' per-station guard left the
  middle of it unsewn — `uncovered_total_mm2` 0.0 → 28.0, ARTWORK_UNCOVERED
  where there had been none. `dt_irregular` strokes stay outvotable: pooled
  irregularity is the artifact the rung exists to correct, a stroke wider than
  the needle can hold is not. **Found by rendering it, not by the suite** —
  every test was green and the geometric numbers looked like a win (35%
  crossing) right up until the picture showed hollow letters.
  *(measured 2026-09-06 — `docs/renders/satin-per-stroke-2026-09-06/`)*

- **Splitting a region is not a way around a REGION-LEVEL floor.** Any rung
  that decomposes a shape and re-runs the satin gates per piece must re-apply
  `_floor_or` (Law 31's `PHOTO_MIN_SATIN_WIDTH_MM`) to each piece, or a
  hairline that the region call correctly refused sews anyway. Caught
  2026-09-05 on `classify_strokes`, which took `design_class` and forwarded it
  only to the region call: five `meadow`/`sunset` regions of 0.42-0.55 mm read
  `photo_width_floor -> stroke_ribbon`. The gates that are region properties
  (width cap, aspect) are the ones a per-piece path may skip; the floors that
  describe what a NEEDLE can sew are not. *(measured 2026-09-05 —
  `tools/ribbon_stability.py --variant strokes`)*

- **A per-stroke satin rung must be PROMOTION-ONLY — `region.satin OR
  per-stroke pass`, never a replacement.** Measured 2026-09-05 over 14
  fixtures at 80 mm: written as a replacement it demotes **15 regions that
  sew satin today**, most of them `promoted_ribbon` shapes the shipped
  `explained` path deliberately rescued — Becker's `Sead76620` at **638.8 mm²**
  (frac 0.71), `S579cb1c2` at 226.4 (frac 0.19), four `logo_bridge_bar`
  regions at frac **0.00**. Corpus-wide the flips are +143.8 mm² (2%, 21
  regions), so a replacement costs more area than it wins.
  *(`stage6_satin.classify_strokes`, `tools/stroke_verdicts.py`; plan
  2026-09-04-per-stroke-satin-routing §PR 2)*

- **Never quote a Becker satin share without its width — the design sits ON
  the `cv = 0.50` gate.** `becker_marine_logo.png` reads **88.2% satin at
  80 mm and 7.6% at 100 mm**, same 17 regions, same design class. The
  classifier is not at fault: scaling a fixed polygon by 1.25 moves its cv by
  under 0.02 and changes only `dt_p90_cap`, correctly. It is that **11 of 17
  regions sit within ±0.10 of the gate at 80 mm and 16 of 17 at 100 mm**, and
  the two widths segment to region sets sharing no shape ids — so which side
  they land on is that run's segmentation, not the artwork. Defect 26's
  threshold fragility at whole-design scale. *(measured 2026-09-05)*

- **The stitch simulator already exists — do not build a second one.**
  `app/src/lib/simulate.js` plus EmbroideryField's `simbar`. This was nearly
  rebuilt from scratch on the assumption it was a gap. *(confirmed 2026-08-25 —
  driven in a browser; moved here from MASTER_SCOPE 2026-09-02)*

- **Merging near-identical cones by folding LAYER PALETTE SLOTS — built,
  measured inert, reverted. Do not rebuild it that way.** A layer's palette is
  not its region cone list (`drone_render`: 16 palette slots against 19 region
  cones) and blocks key on the region's own `thread_index`, so folding slots
  matched nothing the sequencer reads — the pass ran on every fixture, found no
  pairs, and reported success. It would also have clobbered
  `rehome_resnapped_regions`: a folded slot discards the re-snap that put a
  region in its cone's layer. **Fold on REGION cones if this is ever rebuilt.**
  Same shape as the four thresholds-on-the-wrong-population findings — the tell
  was again a pass that should find something finding nothing. What survived
  and shipped: `digitizer/tools/cone_merge_survey.py` (near-cone pairs, split
  within-layer vs across-layer) and `threads.delta_e`, the pairwise question
  that had existed only inline in five places. *(2026-09-02 — PR #318; the
  colour question itself is TABLED by Kent — MASTER_SCOPE queue 12)*

- **The borders-last trim on `enthusiast_logo` is NOT cheaply winnable — three
  approaches measured, all rejected. Do not re-run them.** The `borders_last`
  default flip (PR #302) costs exactly one trim on the benchmark: chained
  trims 10 → 11, **3.76 → 4.16 per 1k**, past the 4.1 professional-corpus
  ceiling `test_chaining` pins — which is why `main` went red at 903c937.
  Isolated to the **within-group** half; the layer half
  (`borders_last_layers`) is free. The cone is a degenerate case — **26 satin
  shapes and ONE fill** — so the blanket rule drags that lone fill to the
  front and knocks the nearest-neighbour sweep off its optimum. What was
  tried:
  1. **Area-dominance guard** (mirroring `borders_last_layers`' own
     satin-outweighs-the-rest test, applied to the group): recovers the trim
     exactly (3.76/1k) but lets a satin sew before its cone's fill —
     `test_repro_fixture_border_satin_sews_after_its_cone_s_fills` catches
     it. Trades the sew-out fix for the trim.
  2. **Extreme-start at the fills→satins pool switch** (the code's own
     anti-stranding argument, applied to the second pool): **21 trims,
     8.12/1k.** Dramatically worse.
  3. **Cover-aware waiting** — a satin waits only for fills whose seam it
     rides (`_seam_band` at `_BORDER_SEAM_EPS_MM`). Recovers the benchmark
     to 3.76 AND improves the repro's own trims 11 → 10 — but **the sew-out
     defect returns**: the repro's first thread down becomes `S7cfe53b9`,
     a border satin, because it sits 3.44 mm from the nearest fill and
     shares a seam with none of them. Seam-coincidence is too narrow a test
     of "covers"; widening it to proximity means inventing a tuned distance
     constant, which is gate 1.
  **The blanket rule is load-bearing for the defect, and the trim is its
  genuine price.** Chaining cannot pay it back either: every refused link on
  that fixture is *"no covered route"*, not one is distance-limited, so
  recovering them means loosening cover — gate 3, the failure mode that
  already hid needle-down thread on bare fabric once. Separately: the
  fixture had ALREADY drifted before the flip — its own docstring claims
  82 mm was chosen for a 3.41/1k margin "not cherry-picked to the edge of
  the threshold", but it measures **3.76 with the flag OFF today**, so most
  of the erosion toward 4.1 is not the flip's. **SETTLED the same day by
  re-pitching the fixture, NOT by moving the ceiling** (PR #306): the
  benchmark went 82 mm -> 93 mm, where chaining cuts trims 19 -> 8 at
  **2.43/1k against the unchanged 4.1** — a 1.67 margin instead of hugging
  the threshold, and the strongest chaining win in that sweep. The corpus
  law is intact; what moved was a benchmark pitch small enough that ONE
  trim swung the rate 0.42. Read that assertion as "still inside the
  professional corpus band", never as an exact number — drifting out of it
  is what happened here. main was red from 903c937 to 769c609 and green
  again at b7fe492.
  *(measured 2026-09-01 — all four numbers on one machine so platform
  numerics cancel; `tests/test_chaining.py`, `tests/test_borders_last.py`;
  resolution verified on main, CI run 33570264885 all five jobs green, and
  a local full suite at 3 failed / 1599 passed — exactly the three
  platform-numeric goldens CI deselects)*

- **Smoothing region polygons to fix "ragged edges" — NO EFFECT, do not build.**
  Douglas-Peucker already runs (`stage4_vectorize`, `simplify_tol_mm` 0.2 mm)
  and meets its tolerance to 0.002 mm, so there is no staircase left at the
  polygon's scale. The raggedness number is MACRO SPRAWL, not edge noise —
  solidity 0.873/0.476/0.329 on owl_kent's three largest — and Gaussian
  smoothing at 8.6× the tolerance moved the worst by 0.04 (11.59→11.55). A
  smoothing radius would also be a NEW gate-1 physical constant, and at the
  only sigma that helped anything it erased the owl's pupils.
  *(measured 2026-08-25 — staircase lever; independently re-checked)*

- **Terminus is CLOSED — omitted, do not re-propose.** The one genuinely new
  font outside upstream: four broken letters (incl. `t`) from paths upstream
  never tagged `satin_column`, a 1/10-width space in a FIXED-WIDTH font, an OFL
  Reserved Font Name, and no size value. Repairing it is the rework ruled out
  above. *(ruled 2026-08-22 — Kent; `docs/font-hunt-external-2026-08-21.md` §2)*
- **The upstream re-census after the transform fix is DONE — do not redo it.**
  All 142 re-imported and re-QC'd, since the original census judged them on
  collapsed geometry. Yield five: `cyrillic` (466 glyphs, 252 Cyrillic; its old
  "detached accent" defect WAS the transform bug), `inkstitch_masego`,
  `fold_inkstitch` (excluded by a FILENAME, not a licence) and two Hebrew faces.
  The 11 refused cross-stitch fonts re-refuse at the same fits.
  *(measured 2026-08-22 — 137 of 142 imported)*
- **There is no external font supply. Do not re-run the hunt.** Ink/Stitch is a
  monoculture: `horiz_adv_x_space` returns 16 files across all of GitHub, and the
  non-upstream remainder is four `font.json` files, none viable. Independent
  non-satin Ink/Stitch lettering fonts: zero. Eleven upstream cross-stitch
  picture-fonts are separately refused — outlines off-grid at 26.2%–87.5%
  against a 0.9 threshold. *(measured 2026-08-21/22 — font-hunt doc; import runs)*
- **`blend_tonal_bands`** (banding inside the fill tier) — built, measured,
  **removed** in the same pass. It decomposed the geometry correctly and changed
  nothing visible, because the shades still shared one thread: 7,725 → 10,126
  stitches, trims 33 → 105, `color_changes` unchanged at 13. *(measured 2026-08-12 — scope-history)*
- **Subject-relative streamline `d_sep`** (the "cheap" alternative to option A)
  — retunes a tier with its own calibration history, against designs that
  currently work. Not cheaper than A, lower ceiling. *(measured 2026-08-12 — scope-history)*
- **DT-first classifier architecture swap** — the patented rule as printed sends
  62/83 clean satins to fill; corrected arms lose every disagreement they
  create. *(measured 2026-08-11 — `docs/dt-first-verdict-2026-08-11.md`)*
- **Junction-free DT width, and one-directional satin/fill gate tuning
  generally** — relaxing `_dt_regular_and_within_cap`'s `p90` moves the corpus
  54.76 → 54.60 and `sttype` 0.217 → 0.198, 12 designs worse to 9 better. The
  diagnosis stands (`p90` rejects branchy, not wide) but the mix is already
  right, so **no cap/`p90`/aspect/regularity move in one direction can fix
  routing — only better discrimination can.** Governs live defect 5. *(measured
  2026-08-14 — PR #152, closed 2026-08-21; detail in area 1)*
- **Swapping the SAM model** — in automatic-mask-generation mode SAM2's encoder
  is only ~8% of per-image cost and the `points_per_side**2` prompt loop is
  ~92%, while every lightweight variant optimizes the encoder; SAM 1 is
  *heavier* (375 MB). And FastSAM (AGPL-3.0 despite a README claiming Apache)
  and EdgeSAM (non-commercial, NTU S-Lab 1.0) are license-disqualified — that
  half **suspected**, from a subagent, never re-verified.
  *(researched 2026-08-11 — `docs/sam-alternatives-research-2026-08-11.md`)*
- **Size-proportional `simplify_tol_mm`** — the fixed 0.2 mm constant is correct
  as-is; Ember's scaling equivalent is not a like-for-like comparison. No change
  made, and the investigation is closed rather than open. *(measured 2026-08-07 — `docs/scope/research-backlog.md`)*
  **The curve question is a second knob, not this one:** `curve_turn_deg`
  bounds the TURN at a vertex and leaves the 0.2 mm deviation alone; built
  OFF and then flipped ON the same day, gated to 20 px/mm (2026-09-03,
  `docs/round-curves-2026-09-03.md`). One consequence for THIS ruling: the
  "realized deviation is scale-invariant at 0.2 mm" evidence now belongs to
  the OFF path -- above the line the default re-reads arcs and the realized
  deviation drops to ~0.05 mm, which is the flip doing what Kent asked, not
  the constant moving (the invariance test pins it with the flag off).
  Splitting a
  Douglas-Peucker edge at its max-deviation point with a near-pixel tolerance
  re-picks staircase corners — split at the arc's midpoint instead.
- **Raising `SATIN_MAX_WIDTH_MM` 5.0 → 7.0 — BOTH coherent routes break
  something measured, and neither failure is golden churn.** Prompted by an
  80 mm Instagram icon whose two white ring bands (5.31 / 5.32 mm ribbon width,
  dt_cv 0.014 / 0.017 — as regular as ribbons get) miss the 5.0 cap by 0.3 mm
  and fall to single-angle tatami, so the rows run straight through the curves.
  Built and measured both ways against a same-machine baseline of 3 failures:
  - **Coupled** (move the one constant): **18 failures**. It also moves
    `_rail_points`' per-station guard (`SATIN_MAX_WIDTH_MM / 2`, 2.5 → 3.5 mm)
    — the 2026-08-05 fix for crosses that physically overlap, measured then at
    2580 crossing rail-to-rail pairs and a 9.57-layer coverage spike. Breaks
    `test_satin_crosses_do_not_self_overlap_across_a_wide_junction`,
    `test_promotion_cannot_reopen_the_width_cap` (whose fixture is a 40×5.5 mm
    bar chosen precisely to sit over 5.0) and four preflight density tests.
  - **Split** (new classifier constant, emitter pinned at 5.0): **13
    failures**. Restores all six safety tests, but the classifier then admits
    bands the emitter refuses to cover — `_rail_points` will not lay a cross
    past 5.0 mm — and `test_a_clean_fixture_leaves_no_artwork_uncovered` goes
    `uncovered_worst_mm2` 0.0 → 0.2 against a fixture whose promise is zero. A
    genuinely 7 mm band would sew ~2 mm bare.
  This is `one-directional satin/fill gate tuning` (above) demonstrated
  mechanically rather than cited: the classifier ceiling and the emitter guard
  are deliberately ONE number (`_rail_points`: "a flat per-station cap at that
  ceiling, not a new number"), so they cannot be moved independently, and
  moving them together reopens a fixed defect. **Any route past 5.0 needs the
  overlap guard rebuilt on real local geometry — better discrimination, not a
  bigger number.** Reverted whole; nothing shipped.
  *(measured 2026-09-02 — branch `claude/satin-width-cap-7mm`, reverted)*
- **`SATIN_MAX_WIDTH_MM = 5.0` is NOT the industry ceiling, and the gap is the
  open question, not the answer.** Wilcom's published guidance is "ideal
  maximum around 12 mm, stay within 10 mm", naming Auto Split — which this
  engine already applies above `SPLIT_SATIN_ABOVE_MM` — as the answer to
  snagging; practitioner guidance for wearables is ~7 mm. So 5.0 is roughly
  half the industry's working ceiling and measured what 19 sampled files
  happened to contain, not what thread can take. **This does NOT clear ROADMAP
  gate 1** — a web citation is not fabric, and the gate names satin width
  explicitly. It makes the sew-out worth doing, nothing more. Note also
  `docs/corpus-laws-round3-2026-08-01.md` flags its own >7.0 mm bucket as 82%
  non-ribbon junk, so 7.0 sits on that edge.
  *(researched 2026-09-02 — wilcom.com, "Mastering Satin Stitch and Tatami Stitch")*

---

## Corrections — suspicions this document itself raised, then disproved

- **"Our satin-vs-fill MIX nearly matches the professional's" was an AREA
  statistic, and by thread it is false.** Defect 5 carried that premise from
  `tools/pro_parity/scorecard.py`'s `cell_stats`, which assigns ONE stitch
  type per 2 mm cell (`CELL = 2.0`), so a column of ours claims a cell exactly
  as the professional's 2.52 mm column does. Measured as thread on 2026-09-04
  with `tools/satin_columns.py`, on the professional's own file for a logo we
  also digitize: **2.2% of our penetrations sit in a column against their
  44.3%**. The paragraph's CONCLUSION survives — retuning `satin_max` is still
  a measured negative, separately, below — but not for the reason it gave: the
  mix was never already right.
  **The WIDTH half of this entry was contaminated and is withdrawn
  (2026-09-06).** It read "our median column 0.29 mm against their 2.52, and
  84% of ours under the 0.7 mm the needle can hold" — that is
  `satin_columns.py`'s WHOLE-PLAN row, 80% of it tatami turns rather than
  columns. Our SATIN runs on that fixture measure **3.82 mm median, p90 4.93,
  23% under 1.0 mm** against the pro's 2.52 / 5.00 / 7%: our columns are not
  hairlines, there are simply very few of them. The 2.2%-vs-44.3% SHARE is
  unaffected (both sides whole-plan, same detector) and carries the entry on
  its own. What is NOT re-derived here is the original mechanism sentence — it
  explained the cell-level tie by our columns being hairline-thin, and that
  premise is gone; the blindness of an area-per-cell statistic to a share this
  small is real either way, but do not quote a width to argue it.
  **Two instruments carry the same blind spot and are annotated in place:**
  `cell_stats` (area, not thread) and `tools/study_pro.py`'s `classify`,
  which gates satin at a median segment ≥ 0.7 mm and therefore *structurally
  cannot* see our narrowest columns — any ours-vs-pro comparison built on
  either undercounts our hairline satin as "other". Use `satin_columns.py`
  for a thread statistic. *(measured 2026-09-04 — scope-history)*

Kept rather than deleted: the shared failure mode — **a hedged observation loses
its hedge as it is copied forward** — is why this file is split.

- **Widening preview thread would NOT "hide the open fill-density item".** The
  area-3 paragraph on `THREAD_WIDTH_MM` first read that it would hide
  "FILL_ROW_MM running ~2x light" — overstating a hedge into a defect. The
  ~0.20 mm figure is a satin-rail **artifact** for one file population
  (refuted) and a genuine denser pitch on 43 commissioned cap logos (still
  alive): unresolved, not open-and-known. Imported from the 2026-08-09 Ember
  teardown without re-checking it was still live. The paragraph's actual rule
  stands — physical thread width is gate 1, do not widen it to flatter a fill.
  *(corrected 2026-08-25; moved here from MASTER_SCOPE 2026-09-02)*

- **Four committed "real customer artwork" fixtures are the vendor's PREVIEW
  RENDERS** — `testdata/reference/becker_*.jpg` are two-panel stitch simulations
  of the pro's own output, md5-identical to files in the delivery zip: a run
  digitizes two half-scale copies of an input derived from the pro's own answer,
  the recon lane's class, which flattered by 11.3 points. `chain_links` -33%
  survives (same input both arms); "1-3 fill shapes" does not. Genuine art:
  `becker_marine_logo.png`, `logo_script_tires.png`. *(md5-verified 2026-08-23)*

- **`streamline_mode: "layered"` does NOT have the blend tier's row-pitch bug.**
  It was flagged as a likely twin on the strength of a note that layered
  "measured a negative (3,220 stitches, sparser than baseline)". That note
  compared layered against **tatami**, not against streamline-mono. Run directly,
  layered is consistently *denser*: `owl_kent.jpg` 1,902 → 3,215 (2.1×),
  `fur_ramp.png` 326 → 696 (1.7×), `gradient_ramp_linear.png` 614 → 1,918
  (3.1×). **No fix needed; do not go looking for one.** *(measured 2026-08-13 — scope-history)*
- **`_speckle_ratio` is not scale-broken.** The original note (0.35 max vs
  values of 39.93 / 49.45 / 78.72 on real regions) was hedged "confirm before
  trusting it" and hardened into a stated defect as it was copied. It computes
  an **unnormalised Laplacian-gain ratio**, so its scale is not comparable to a
  0–1 ratio by inspection, and it discriminates correctly at the shipped
  threshold. *(confirmed 2026-08-14 — `stage6_blend.py:295-299`)*
- **Not a defect, recorded so it isn't re-found:** the noise fixture in
  `test_blend_falls_back_to_ordinary_tatami_on_speckle` never reaches the speckle
  gate — r² is tested first and random noise fails it, so the branch that test is
  named for is not the one it exercises. Behaviour is correct; the test now says
  so. *(confirmed 2026-08-12 — scope-history)*
- **`_hoist_same_thread` does NOT leave `sequence`'s sew cursor stale in
  practice. Do not "fix" it.** The reasoning is sound and the conclusion is
  still wrong, which is why it is written down. `sequence` sets `cursor` from
  the last artwork block (~L1927), `_hoist_same_thread` then REORDERS
  `art_blocks` below it (~L1942), and `cursor` is consumed afterwards as
  `detail_runs(..., entry=cursor)` (~L1978), where `cur = entry` seeds the
  nearest-neighbour ordering of the detail lines. The hoist's scan starts at
  the last position, and the repo's own
  `test_a_revisit_is_hoisted_when_it_clears_everything_it_jumps` proves the
  reorder CAN change which block sews last (`[t7, t9, t7]` -> `[7, 7, 9]`), so
  by construction the entry point can go stale. **Measured: it never does.**
  Eight fixtures at 100 mm with `is_photographic=True, detail_layer=True` —
  `owl_kent`, `logo_bridge_bar`, `logo_golden_tee`, `drone_render`,
  `photo_owl_pale`, `logo_gaulke_roofing`, `enthusiast_logo`,
  `photo_sunset_backlit`. Four reorder (the owl goes 16 blocks -> 14); **zero
  move the last block**, and `entry` equals the true final art stitch to
  within 1e-9 every time. The structural reason: the hoist only ever moves a
  block EARLIER, toward a same-thread block that precedes it, so the last
  block moves only when its own thread also appears earlier and clears the
  disjointness gate — and a sew order ends on its last layer's cone, which
  characteristically appears once.
  **What would make it real:** a design whose final block shares a thread with
  an earlier block AND is geometrically disjoint from everything between them.
  Worth re-measuring if the hoist margin is raised, or if `revalidate_threads`
  starts re-snapping late layers onto earlier cones. As of 2026-08-31
  `rehome_resnapped_regions` consolidates the RE-SNAP splits upstream of
  stage 5 (owl: merge-off equals merge-on) — but duplicate quantize-time
  declarations still put one cone in two layers on committed artwork
  (`drone_render` 80 mm: t16 sews at 30.9% and again at 98.9%, t119 at 74.2%
  and again as the FINAL block, 99.4%), so same-thread splits still reach
  the hoist, and drone's final block now shares a thread with an earlier one
  — half of the "what would make it real" precondition above. Re-measure
  against drone first if this entry is ever re-opened. Even then the cost is
  bounded — no stitch is misplaced, because the art->detail seam is forced
  `jump=True, trim=True` either way; only the detail sew order and the `jumps`
  tally move. *(raised and disproved in one session, 2026-08-31 — filed as a
  live defect on the code read, then withdrawn on the measurement; instrument:
  scratch sweep patching `_hoist_same_thread` and `detail_runs`)*

- **The Studio's "Make it bigger" button was justified by a misquote, and the
  quote was wrong on the day it was written.** `DigitizePanel.svelte`'s
  `FIX_FOR` comment read *"`LETTERING_TOO_SMALL`'s own message ends 'Enlarging
  helps', and until now nothing offered to enlarge it."* At that commit
  (`1c20ec9`, 2026-09-02) the message already read *"Enlarging helps **but does
  not fully clear it**: the smallest shapes regenerate at any size. Remove or
  simplify the smallest lettering."* The quote stopped at the word where the
  sentence reverses, and the action it justified ("make it bigger") is not the
  action the message ends on ("remove or simplify"). **No checker can catch
  this** — "Enlarging helps" IS a truthful substring of the source string, so
  fidelity checking passes; only reading the rest of the sentence finds it.
  Corrected in place 2026-09-06; the button was LEFT alone, because whether a
  partial remedy earns a button is Kent's call, not a session's.
  **And then the button was MEASURED** (`tools/enlarge_cure.py`, the ten corpus
  fixtures that fire `STITCHES_TOO_SHORT` at 80 mm, swept through one press and
  two): **one press cleared the finding on 1 of 10**, two presses on 4 of 10,
  and it made the number **WORSE on 3 of 10** — `photo_dof_meadow`
  0.36 → 0.58 → **0.71**, worse at every press; `logo_bridge_bar` 0.30 → 0.36;
  `photo_sunset_backlit` 0.65 → 0.66. The satin SHAPE count rose on **every**
  fixture (2 → 9, 42 → 71), which is `_lettering_findings`' own *"the smallest
  shapes regenerate at any size"* seen from the short-step side: enlarging buys
  new small shapes as fast as it widens the ones already there. **Claim nothing
  about grades from that sweep** — several checks move with size at once, and 5
  of the 10 sit on the clamped score floor where nothing registers either way.
  The knob is real; the cure is one in ten.

- **A trim INSIDE a shape and a trim BETWEEN shapes need opposite advice, and
  the corpus splits them almost evenly.** 26 fixtures at 80 mm: **866 trims,
  456 in-shape (53%), 410 between (47%)**, with the majority flipping per
  design — in-shape dominant on 11 fixtures, between-shape on 11, one tie,
  from `photo_grass_macro` at 93% in-shape to `logo_alpha` and `logo_whitebg`
  at 100% between. Merging or removing shapes removes a BETWEEN cut and cannot
  touch an IN-shape one: `satin_shape` may travel over UNSEWN strokes only, and
  the walk on a 27-stroke region succeeds up to 40% sewn and never again after.
  **This was not a discovery** — MASTER_SCOPE defect 6 has said "the trim bulk
  is INSIDE one shape, 69% intra-shape" since 2026-08-21, on one design. What
  was missing is that `TRIM_HEAVY` never reported it, so every design got the
  between-shape remedy. Fixed 2026-09-06. `tools/trim_locality.py` re-measures
  it; Becker reproduces the August number independently at 19 of 28 (68%), the
  1-point gap being the file's first cut, which does not exist.

- **A constant re-base fixes the code and leaves the PROSE lying, and the
  prose is what people read.** `COVERAGE_WARN_UNITS`/`COVERAGE_BLOCK_UNITS`
  became `2.5 *` and `3.5 * COVERAGE_FILL_LAYER_UNITS` on 2026-09-03 when
  `FILL_ROW_MM` moved to 0.15 — so they evaluate to **6.67 and 9.33**, and
  `machine.py` says so at length. Four places still quoted the old bare
  numbers three days later, found 2026-09-06: `preflight`'s module docstring
  ("1.0 is one full covering layer" — 1.0 is one 0.40 mm ribbon; a fill lays
  2.67), `_coverage_findings`' docstring (naming both constants and giving
  "2.5 and 3.5" as their values), and two `test_preflight.py` docstrings
  quoting 3.00 and 3.5 beside assertions that compute 8.00 and 9.33. **The
  harm is specific:** a reader comparing the corpus's peaks (2.20 to 7.97)
  against "3.5" concludes every design is grossly over the block ceiling when
  in fact **none of them reaches it**. `machine.py`'s own warning — *"every
  coverage number recorded before this date is in the old base and is 2.67x
  smaller"* — was written for exactly this and did not save the files beside
  it. **When a constant is re-based, grep the prose, and prefer pinning a
  RELATIONSHIP in tests over a number** (`tests/test_stacked_where.py` asserts
  the 2.5x/3.5x multiple, not 6.67/9.33).

- **`DENSITY_STACKED` has never fired on real artwork — do not read its
  silence as a clean corpus, and do not delete its synthetic tests.** Swept
  2026-09-06 over all 26 fixtures at 80 mm: **0 of 52 design/garment combos**
  produce the finding. Six carry a PEAK over the warn level
  (`photo_dof_meadow` 7.97, `drone_render` and `gaulke_roofing` 7.51,
  `chrome_specular` 7.09, `sunset_backlit` 7.04, `bridge_bar` 6.89) and every
  one yields **0.0 mm² of qualifying patch**: `_COVERAGE_MIN_PATCH_MM2` (25
  mm²) is doing all the work, which is what it was built to do — clean work
  speckles over the warn level wherever two satin columns join. So the whole
  test coverage of this `block`-severity check is the synthetic `_stacked(n)`
  plans in `tests/test_preflight.py` and `tests/test_stacked_where.py`. A
  corpus A/B can prove nothing about it either way.

- **The same-hole RATE is a ratio whose denominator moved on 2026-09-03, and
  the fall is dilution, not improvement.** `SAME_HOLE_HEAVY` scores
  (points struck 2+ times) / (total penetrations). `FILL_ROW_MM` went
  0.40 → 0.15 that day, so the denominator grew and the numerator did not.
  A/B'd at both row pitches on four fixtures (2026-09-06):

  | fixture | penetrations | repeat points | 3+ points | `max_strikes` |
  |---|---:|---:|---:|---|
  | `logo_whitebg` | **×2.30** | ×1.00 (28 vs 28) | ×1.13 | 8 → **8** |
  | `becker_marine_logo` | ×1.17 | ×0.98 | ×1.00 | 4 → **4** |
  | `logo_hotel_fremont` | ×1.62 | ×1.15 | ×0.98 | 8 → **8** |
  | `screenshot_phone_ui` | ×1.37 | ×1.09 | ×1.02 | 9 → **9** |

  The rate fell to **0.43–0.83×** while `max_strikes` was **identical on every
  one**. The needle is not landing in fewer old holes; there is more
  denominator. So the docstring's *"our benchmark is 9.8%"* is in the old base
  and now reads about 2.7%, the corpus runs **0.001–0.103**, and the finding
  fires on **0 of 26** against a threshold set as "far above" 9.8%. **Its
  silence is not evidence that anything improved.** This is ROADMAP gate 4 in
  miniature — a raw ratio moves when the mix moves — on a check nobody thought
  the fill-row ruling touched. **`SAME_HOLE_RATE_MAX` was deliberately NOT
  retuned**: its baseline is a professional corpus measured at its own row
  pitch, and re-deriving the comparison means re-walking the pro files, not
  rescaling our side. Fixed instead by emitting the density-invariant half —
  `max_strikes`, `points_3plus`, `worst_at_mm`.
  *(measured 2026-09-06 — scope-history 09-06)*

- **"The cone is already loaded, so the merge is FREE" prices the THREAD and
  not the SEQUENCE — and every remaining duplicate is 7 to 11 blocks apart.**
  Measured over 26 fixtures × 2 garments with `tools/cone_revisits.py`: the
  4 surviving duplicate cones sit at block gaps of 7 (`screenshot_phone_ui`,
  `3971`) and 11 (`region_blobs`, `0182`), and **not one of the four is
  adjacent**. Folding block 12 into block 1 moves regions past everything in
  between, and stage 5 built `covered_by` from the un-merged order — which is
  exactly the across-layer case `cone_merge_survey.py` had already measured as
  the expensive kind. **Do not quote "free" without the gap.** The saving is
  one machine stop; the cost is a reorder.

- **CI's `digitizer` job runs 10 to 42 minutes, not the 12–18 every doc said —
  and the cause is NOT concurrency.** Measured 2026-09-06 from the Actions API
  over the last 220 completed jobs. The daily median walked 15.0 → 16.5 → 17.6
  → 18.7 → 20.7 and jumped to **29.6** on 2026-09-06 (max 41.8); the old figure
  was true when written (medians 15.0–15.2 on 2026-08-27/28) and now holds for
  half the jobs. Three things are settled and one is not:
  - **All of it is in the test step.** `Install` measures 0.27 min on fast and
    slow runs alike, Tesseract 0.20/0.17; `Digitizer tests` is 14.3 against
    32.4. Not caching, not dependency install.
  - **Concurrency is refuted, not merely doubted.** Bucketing every job by how
    many other `digitizer` jobs overlapped it: the **41.8-minute worst case ran
    with ZERO**, and the most-contended bucket (2+) tops out at 19.8 min. The
    obvious hypothesis is backwards.
  - **Suite growth cannot carry it either.** The SAME test count lands
    19.6–34.5 min (1,851 tests) and 17.9–33.7 (1,968) — a **1.9× spread on
    identical work** — with seconds-per-test at 0.54–1.32.
  - **What is left is the runner, and nothing recorded which one we drew.** The
    job now echoes `nproc` before pytest for exactly that reason. Until a log
    settles it, do not attribute a slow job to a cause; the three above are
    already eliminated.

  **Practical consequence: budget half an hour and read a 35-minute job as
  normal rather than stuck.** This does not weaken item 7's rule — three green
  checks is still not a green PR — it makes the wait longer than the rule
  implied, so the temptation to merge early is stronger, not weaker.

  Re-confirmed by re-running with the flag rather than trusting the record:
  `cfg.bind_resnap_all_classes` takes `screenshot_phone_ui` from **17 blocks to
  11 with the duplicate gone**, and leaves `region_blobs` at 16 with its
  duplicate intact. So the open blend-band half is **one design, and it is a
  GENERATED fixture** — `make_photo_region_fixture.py` renders `region_blobs`
  as three Gaussian-falloff blobs. No client artwork in the corpus produces
  one. Re-run the tool after any sequencing change; a real design appearing
  there changes the arithmetic.

- **`STITCHES_TOO_SHORT` and `LETTERING_TOO_SMALL` bill 24 points for one
  defect — but do NOT delete either to "dedupe" them.** They measure the SAME
  quantity at the SAME threshold: `MIN_COLUMN_MM` **is**
  `machine.MIN_STITCH_MM`, and both read the consecutive-step distance inside a
  satin run, which crosses the column. They differ only in aggregation —
  per-shape MEDIAN against a global FRACTION. Over the 26-fixture corpus at
  80 mm the short-stitch check **never fired without the size check** (10 both,
  1 lettering only, **0 alone**), so as a design-level signal it is redundant.
  As a LOCATION report it is not: only **66%** of the short steps sat inside a
  shape lettering named, because a shape passes lettering on its MEDIAN. The
  residue is not small lettering — uncovered carriers run **1.1 to 3.2 mm
  median column**, and `logo_bridge_bar`'s worst has a **2.65 mm median** with
  205 of its 1,597 steps under the needle minimum: sewable columns with a
  narrow WAIST, which lettering's median test cannot see and should not. The
  redundancy is in the SCORE; the information is not. Fixed 2026-09-06 by
  making the finding emit `shapes` / `uncovered_shapes` and stop recommending
  a cure the neighbouring docstring had already measured false.
  *(measure it again with `tools/short_satin_overlap.py`, and expect both
  numbers to move once per-stroke satin routing lands — that is the documented
  root cause of the short columns, and it is scale-invariant)*

---

## Gotchas — cost someone a session once

- **`StitchRun.jump` is NOT travel — never filter on it to decide whether a
  shape is sewn.** The field means *"the machine must lift the needle to reach
  `points[0]`"*; the class above it is *"One needle-down path."* A jump says
  how the needle ARRIVED. An instrument that skipped `run.jump` runs when
  counting a region's emitted stitches reported **11 of 25 blocking
  `THREAD_MATCH_POOR` findings as riding on shapes that sew nothing — all
  three of `gaulke_roofing`'s, 6 of 10 on `screenshot_phone_ui`, including its
  headline 33.0 dE00 shard. The true count is 0.** The filter discards exactly
  the shapes a thread finding is likeliest to name, because a small isolated
  shape is one the router must jump to: re-measured, `S43831dcd` sews 24
  stitches, `Se6eddd27` 60, `Sf90801f2` 162. **The sewn count is
  `len(run.points)` summed over EVERY run whose `_owning_region_id` resolves,
  jumps included** — the form `preflight._uncovered_findings` already uses.
  Caught only because the fix built on it scored 26 fixtures and moved
  nothing: **a no-op where a large effect was predicted is evidence about the
  instrument.** `tests/test_thread_match_enclosed_background.py::
  test_jump_runs_are_sewing_not_travel` fails if the filter comes back.
  *(measured 2026-09-06 — scope-history 09-06)*

- **A denominator taken from the PLAN empties a preflight check whenever the
  caller passes a plan that is not that design's — and ten `test_preflight.py`
  cases do exactly that on purpose.** Skipping regions the plan emits no run
  for is the right idea (`_uncovered_findings` does it, quoting
  `SHAPES_LEFT_UNSEWN`), but in `_region_color_errors` it broke ten deliberate
  tests — among them *"the single-row path must survive an empty plan"* —
  to remove ONE finding across the whole 26-fixture matrix. The region's own
  `enclosed_background` flag says the same thing without making the row set
  depend on the plan, and cost exactly one test, the one whose contract the
  change corrects. On `logo_gaulke_roofing` the two sets are identical anyway:
  all 46 of its 56 runless regions are enclosed background. **Rule: before
  deriving a denominator from the plan, check what the module's own tests
  pass in as a plan.** *(measured 2026-09-06 — scope-history 09-06)*

- **"NOT wired / nothing calls this" comments go stale silently — verify one
  before you trust it.** Nothing tests a comment, so a module docstring keeps
  asserting an absence long after the seam it describes was built, and the
  cost is real: it sends the next reader off to build something that already
  exists. Three found in one sweep on 2026-09-06, all of which had been true
  when written:
  `directionfield.py` said "nothing in the pipeline imports this module" while
  `stage6_streamline` imports it at module level and a forced `photo_subject`
  run emits 7,090 stitches from its field; `stage6_detail.py` said YuNet
  landmarks were "NOT wired into any stage", 2026-08-04 having wired them into
  stage 1.5 with `stage2_photo_segment` consuming eye/skin classes; and
  `stage6_satin.py` said its per-stroke block was "deliberately inert" one PR
  after the flag wired it. `match_shape_ids`' "no production caller" is the
  one that checked out. The cheap verification is a grep for the symbol plus a
  spy on a real `digitize()` — and mind the environment: YuNet's gate needs
  `rembg`, so on a container without it a spy counts zero calls and the
  wiring still exists. *(measured 2026-09-06)*

- **There are TWO segmenting lanes, and a rule one of them has is not a rule
  the other has. Grep the other lane before you build a mechanism.** The flat
  lane (`stage2_quantize._quantize_population`) has run "majority filter, then
  phantom-blend dissolve" since before the photo lane existed; the SLIC+RAG
  lane (`stage2_photo_segment.segment`) never got it, which is the whole of
  Bridge Bar's six grey JPEG-halo cones (defect 27). The record was not silent
  either — `Prep.bg_edge_rgb`'s docstring says outright that stage 2 needs it
  "as a virtual endpoint when testing whether a cluster is an anti-alias
  blend", so a `grep bg_edge_rgb` found the existing rule in one command.
  Building the same test from scratch would have shipped a second, differently
  tuned copy of a rule this repo already has. **The port is also not a copy:**
  the flat lane's numbers assume its own preceding steps (its 0.9 edge fraction
  assumes the majority filter has thinned halos to one pixel; its
  "between any two clusters" assumes at most `max_colors` of them), and both
  had to be restated for a lane that arrives with 57 labels and no majority
  filter — and its 0.15-0.85 window assumes ONE cluster sitting between two
  colours, where ringing here arrives as a STACK that tiles the whole segment,
  so the window had to move from the band to the structure (band-by-band it
  put the outermost ring at t 0.89, outside the window, and the fixture came
  out worse than doing nothing). Port the QUESTION verbatim; re-measure every
  threshold, and check what each one was assuming about its own lane.
  *(2026-09-04 — scope-history 09-04)*

- **A pass that visibly fires and changes nothing downstream is folding things
  somewhere they are not adjacent to.** The first cut of the halo dissolve
  reassigned phantom labels to the nearest surviving colour anywhere in the
  design, as the flat lane does. On Bridge Bar the outermost grey ring (L 87)
  found YELLOW (L 86) nearest and landed in the disc's label, on the far side
  of the black it was ringing: **3,989 px moved, 57 labels became 20, and the
  connected-component count did not shift by one** — as many shapes split as
  merged. Region counts, block counts and stitch totals were byte-identical,
  so every summary read "no change" while the array underneath was being
  scrambled. If a merge pass moves pixels and the component count is flat,
  check adjacency before checking the wiring. *(2026-09-04 — same entry)*

- **`machine.SATIN_MAX_WIDTH_MM` is load-bearing in FOUR places, not one.
  Changing it to move the satin/fill decision silently moves three other
  things.** Enumerated 2026-09-02 after a 5.0 → 7.0 edit took the suite from 3
  failures to 18:
  1. the satin/fill classifier — `stage5_overlap` and `stage7_sequence`, both
     via `cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM` (the intended one);
  2. `stage6_satin._rail_points`' per-station width cap, `/ 2` — the guard
     against crosses that physically overlap each other;
  3. `_stroke_underlay`'s oversize trigger;
  4. `_stroke_underlay`'s leg clamp, `× 0.82`.
  Roles 1 and 2 are the SAME ceiling on purpose — `_rail_points` says so
  outright ("a flat per-station cap at that ceiling, not a new number") — so
  splitting them is not a tidy-up, it decouples the classifier from what the
  emitter can actually sew and leaves artwork bare. Read all four before
  touching the constant, and check whether a fifth has appeared.
  *(measured 2026-09-02 — branch `claude/satin-width-cap-7mm`, reverted)*
- **A shipped `.embf` answers more than it looks like it can — decode it before
  asking Kent for source files.** The 26-dead-glyph item sat in the queue for
  six days marked "needs YOUR MACHINE", because telling `stripRunParamsIfSatin`
  apart from "upstream authored no length" was assumed to need the Ink/Stitch
  SVGs. It does not: the strip fires if and only if the font has any satin
  glyph, and that is readable straight out of the binary
  (`EMB.decodeFontBin`). Four of the six fonts have ZERO satin, which acquits
  the strip for them outright. A session went hunting through Google Drive for
  sources before checking the artefact already committed to the repo.
  *(measured 2026-08-28 — scope-history 08-28)*
- **`cfg.is_photographic` and the Studio's user-declared photo control are
  DIFFERENT CONTROLS, and measuring one tells you nothing about the other.**
  (That control is the reading row's "It's a photo" correction in
  `DigitizePanel.svelte`; it was a "This is a photo" checkbox in the params
  list until 2026-08-30, when it was renamed and moved. It sends exactly what
  it always sent, so every number in this entry stands as measured.)
  The field declares the art photographic: the palette bind and depth
  sequencing come on, the class and the fill tier do not move. The checkbox
  sends `forced_class="photo_subject"` (`app/src/lib/digitizer.js:144`), which
  additionally fires `auto_photo_tier` → streamline. On `owl_kent.jpg` at
  100 mm that is 12 stops / 0.990 coverage against 26 stops / 0.591 — opposite
  directions from the same-sounding intent. A session measured the field,
  reported the number as what the checkbox does, and told Kent four times to
  tick a box that would have made his artwork worse on every axis he had
  named. `is_photographic` has 0 hits in `app/src`: it is not reachable from
  the UI at all. **Before quoting a config field as a user-facing setting,
  grep the Studio for it and read what the checkbox actually sends.**
  *(measured 2026-08-28 — scope-history 08-28)*
- **`pipeline.py` binds stage functions at IMPORT, so patching the source
  module to instrument a run does nothing — and the silence looks like
  evidence.** It does `from .stage4_vectorize import revalidate_threads`, so
  `s4.revalidate_threads = spy` never fires and you conclude the stage did not
  run. Patch `pipeline.<name>` instead. `_shade_blocks` IS spy-able through
  `stage7_sequence` only because stage 7 calls it via its own module globals.
  Cost a session two wrong conclusions in a row, one of which ("depth_sort_layers
  never ran") happened to be true for an unrelated reason and so did not
  self-correct. *(confirmed 2026-08-28 — colour-stop investigation)*
- **`stitches.apply_ties` is NOT idempotent.** It folds lock stitches into
  `run.points` in place; its own docstring warns that tying twice "doubles the
  lock into eight stitches of thread piled in one spot". Anything that
  re-partitions blocks must run BEFORE ties, never after — there is no
  un-tie. Deferring ties is safe for the sew cursor, because `tie_run` "both
  starts and ends at `at`" and so moves neither `points[0]` nor `points[-1]`;
  a +0 stitch delta across the change is the cheap proof you tied once.
  *(confirmed 2026-08-28 — PR #291)*
- **A colour-stop complaint is probably NOT `_shade_blocks`.** The per-shade
  block split is the obvious suspect and was wrong on the one real design that
  prompted the question: `owl_kent.jpg` gives 20 groups, one block each, zero
  shade splits — the blend path was not active at all. Count groups and splits
  before theorising. The real mechanism is `revalidate_threads` re-snapping a
  region onto a better cone without moving it to that cone's LAYER, so one
  spool ends up owned by layers that sew at different positions.
  *(measured 2026-08-28 — scope-history 08-28)*
- **Six phase-numbering schemes exist; only ROADMAP.md's five engine phases
  are live.** Historical: the 4-phase pro-stitch roadmap, 11 digitizer steps,
  7 launch items, 8 Studio slices, 16 rows (0–15). *(confirmed 2026-08-18 — docs/scope/1-auto-digitizing-quality.md:1506 and photo plan §2)*
- **The venv holds a STALE non-editable install of `digitizer_core`, and cwd
  decides which one you get.** `pytest` from `digitizer/` imports the working
  tree, so tests are honest — but from any other cwd the same interpreter
  imports `.venv/.../site-packages/digitizer_core/`, whose files differ from
  both the working tree and `HEAD`. A service or script launched from
  elsewhere can run code that is not in the repo. Reinstall
  (`pip install -e digitizer`) before trusting any out-of-tree run.
  *(confirmed 2026-08-17)*

- **Stage 0's `photo_subject` gate is bimodal** — textured subjects on smooth
  backdrops can't reach `photo_subject`. Pinned in the routing test's docstring.
  *(confirmed 2026-08-12 — scope-history)*
- **`stage0_classify._load` treats raw ndarrays as BGR** — A/B probes must
  convert first. *(confirmed 2026-08-12 — scope-history)*
- **A UI affordance that gates on service health fails indistinguishably from
  the service itself.** An overflow clipped "+ Auto-digitize" by 111px, so a
  hidden button read as a dead service and silently routed photo work through
  the browser engine — a full SAM2 on/off comparison was published that never
  touched SAM2. Closed for the upload path; remember the *class*.
  *(confirmed 2026-08-13 — PR #122, PR #138)*

- **Pro-parity scores from before 2026-08-14 are on a different scale and do
  not compare.** `direction` and `sttype` were bounded agreement measures
  with a floor near 0.5, so about half their combined 40 points were paid out
  for a wrong answer; both are now chance-corrected. Anything quoting a
  pro-parity number from before that date reads ~16 points high at corpus
  level. `score_raw`/`parts_raw` in `score.json` carry the old scale when the
  two genuinely need lining up. *(measured 2026-08-14 — PR #151)*

- **Every pro-parity number before 2026-08-15 was measured on artwork
  RECONSTRUCTED from the pro's own stitches, and was flattered by 11.3 points.**
  Honest baseline on Kent's 7 real artworks (15 designs): **42.5**. That
  rescaling compounds with the chance-correction above; treat any pre-08-15
  figure as unusable. *(measured 2026-08-15 —
  `docs/pro-parity-real-art-2026-08-15.md`)*

- **The pro-parity 95 target is above the metric's own ceiling. Do not read
  `score/95` as an engine deficit** — any plan quoting "we need to get to 95"
  is quoting an unreachable number. Two of the PRO's own files for one logo,
  scored against each other, give **75-84**. The scorecard is not broken (it
  returns 96-100 on one job saved twice), but `direction` ceilings as low as
  0.11 against a 20-point weight — it measures a choice, not a standard, and is
  the least defensible weight; `density`/`underlay`/`travel` ceiling at
  0.89-1.00. **Deliberately NOT revised: n=2.** Growing n needs
  scale-normalised registration in `scorecard.py`.
  *(measured 2026-08-15 — `docs/pro-parity-real-art-2026-08-15.md` §11)*

- **Pro-parity numbers measured before 2026-08-26 are on a THIRD scale, and the
  delta is still unquantified.** `scorecard.py`'s `surface()` was handed
  colour-keyed buckets and painted each colour at its EARLIEST block, so an
  outline-last build (black, red, black on top) had the outline painted first
  and buried by the red it physically covers — the grader scored a picture of
  the pro's design that the pro's customer would never see, and did the same to
  ours. `colour_runs()` now walks consecutive runs instead. `colour_groups` is
  deliberately unchanged: per-colour recall wants every block of a thread
  together and order cannot matter there. **The corpus-wide delta needs a run
  on Kent's machine** — `scratch_corpus/` is gitignored and absent from a cloud
  container, so this could not be quantified where it was fixed.
  *(fixed 2026-08-26 — PR #269; delta NOT measured)*

- **The golden divergence is PER-FIXTURE, not per-platform.** CI deselects
  exactly THREE by name — `pushcomp[logo_whitebg.png-towel]` and the
  `[photo/enthusiast_logo.png]` rows of `flat_lane_byte_identical` and
  `stage2_photo_segment`. The two `logo_alpha` rows were REMOVED 2026-08-22
  after the remove-and-see check ran green without them. **Consequence:** an
  `enthusiast_logo` failure locally is expected; a `logo_alpha` failure
  anywhere is a genuine regression — per-platform reasoning gets that
  backwards. **Still binding: never re-capture a golden from a Windows run.**
  Judge a change by "same failure set before and after". Rationale:
  `docs/pro-parity-real-art-2026-08-15.md` §0b and the CI workflow comment.
  *(measured 2026-08-22 — green CI run at `db0e642`; Windows column
  last re-run 2026-08-17)*

- **OCR tests skip, not fail, without the `tesseract` binary — and never skip
  on CI.** The five real-read tests carry `requires_tesseract`
  (`tests/conftest.py`), which skips only when the binary is missing AND `CI`
  is unset, so a workflow refactor losing the install fails loud instead of
  going dark. The TOTAL skip count is environment-dependent — tesseract, and
  whether `rembg_isolated/venv` is built — so judge it by the per-class
  accounting in COOKBOOK "Running things", never by the total.
  *(measured 2026-08-17; accounting refreshed 2026-08-24)*
- **Breaking a guard on purpose does not prove it is not blind — ask what
  SHAPE of failure it would miss.** A guard that catches a deliberate break
  can still be blind to the failure mode that actually occurs; construct the
  realistic failure, not the convenient one. *(2026-08-22)*

- **Measure pro-parity in a git worktree, never in a shared checkout.** Three
  baselines were invalidated 2026-08-15 by commits landing mid-run, one from a
  second Claude session on the same branch. It looks like engine
  non-determinism; the engine is deterministic. Verify module resolution hits
  the worktree's own `digitizer_core`. *(measured 2026-08-15 —
  `docs/pro-parity-real-art-2026-08-15.md` §1)*
- **Three photo hypotheses are disproven** — palette collapse merging subject
  into background, `max_colors` as binding constraint, `MERGE_DELTAE00_THRESH`
  needing a retune. All three extrapolated the *synthetic* `photo_owl_pale.png`,
  a blob with one region at 98.1% of canvas. *(2026-08-12 — scope-history)*
- **Keep `main` green while work is in flight — a red suite makes "same failure
  set" unjudgeable against.** Goldens are re-captured on Linux, never Windows.
  *(moved from ROADMAP 2026-08-19 — 60-line budget, decision by Kent)*
- **Read `MASTER_SCOPE.md` and `docs/scope-digest/` before proposing any
  work.** What has already been built, measured and rejected here is the most
  expensive knowledge in this repo; phase numbers in any other doc are
  historical. *(moved from ROADMAP 2026-08-19 — decision by Kent)*

- **`git log -- <path>` on a SHALLOW clone names the graft root as every file's
  last author — wearing a real merge's subject line.** Every cloud session
  starts from a shallow clone. The boundary commit keeps its own message, so
  `git log -1 -- <path>` returns a plausible hash, a plausible date and a
  plausible subject for a file it never touched; only `%p` gives it away (a
  graft root prints no parents). This dated the scorecard baseline to
  2026-08-24 and produced a published claim that the baseline was incoherent
  and had to be recaptured. `git fetch --unshallow` (219 → 1390 commits) put
  the real capture at `4f7d80f3`, 2026-08-12 — **206 merges earlier** — and all
  38 rows then reproduced exactly. **Run `git rev-parse
  --is-shallow-repository` before attributing anything to a commit**, and
  `git fetch --all` before concluding prior work does not exist (CLAUDE.md 8).
  *(2026-09-02 — `docs/scorecard-baseline-attribution-2026-09-02.md`)*

- **A `vi.mock` that omits an export the component newly calls does not fail
  the spec — it silently disables the feature under test.**
  `DownloadStep.spec.js` mocked `../lib/hoop.js` without `hoopFitNote`; the
  component calls it inside a try/catch, so the throw was swallowed and every
  export-gate spec passed against a gate that never ran. The suite was green
  *because* the feature was dead. **When you add a call to an already-mocked
  module, add it to the mock and watch one spec go red first** — the same
  discipline the `satin_shape(angle_deg=)` inert-wiring finding already
  demanded. *(2026-09-02 — PR #317)*

- **A test whose NAME claims both directions will often assert only one.**
  `test_explicit_flag_still_wins_everywhere` checked only that the config flag
  could turn tonal splitting ON. `effective_split_tonal` ORed the flag with the
  class, so the OFF direction had never worked at all and no test noticed —
  the override was advertised as an override and was really a one-way switch.
  Read the assertions, not the name, especially on a test guarding an override
  or a default. *(2026-09-02 — PR #316)*

- **A `var(--x, fallback)` whose name is undefined is not a fallback — it is a
  silent bespoke value.** Three such names shipped in `app/src/theme.css`; two
  more tokens failed WCAG AA on the app's own non-white grounds while passing
  on white. The named cases are fixed, but the CHECK is standing: **re-run it
  whenever a new component lands.** It is two halves and only one is cheap.
  The grep half — every `var(--name` used under `app/src` against every
  `--name:` defined — **re-run 2026-09-02 and CLEAN: 52 used, 54 defined, zero
  undefined**, covering the three components that landed that day (export
  confirm dialog, adjustment chips, run-delta line). The contrast half needs
  COMPUTED styles in a real browser on the app's non-white grounds, and was
  **not** re-run against those three. *(2026-08-25 — theme.css; moved here and
  half re-run 2026-09-02)*

- **A ±10% stitch-count swing with nothing visibly moved can be a threshold
  sitting on a float boundary, not geometry.** `stitches.split_long_moves`
  split any step over the cap with a bare `>`, and a fill step laid at
  exactly the cap measures `3.0000000000000004` mm as often as
  `2.9999999999999996` once the row is rotated back — so which rows got
  half-stitches depended on the row angle's cosine, and a change that moved
  nothing visible (a vertex, an angle rule) swung `logo_whitebg` 8% and
  `photo_sunset_backlit` 10% while every row, angle, trim and region stayed
  put. A session chased that swing as a curve-refinement effect for most of
  a day. Closed with `SPLIT_TOLERANCE_MM = 1e-6` (defect 25, PR #328). Two
  standing rules. **A count delta with no row/angle/trim/region delta is a
  comparison at a boundary until proven otherwise** — go find the `>` before
  theorising about the geometry. **And a count from any tree before PR #328
  is not comparable to one after it** — `tools/fill_dust.py` run on the old
  tree says how much of that fixture's count was dust (whitebg 180, Fremont
  576, sunset 1198), subtract it first. *(2026-09-03 — defect 25;
  `docs/round-curves-2026-09-03.md`)*

- **A synthetic fixture can be exactly right about itself and wrong about
  the goldens.** Defect 23 went into MASTER_SCOPE as "one whole rail 15%
  short, in every satin golden" from a 3 mm bar with an exact spine. On real
  art the ulp coin flip it described was 1–11% of the rail retreats, and the
  micron that fixes the bar completely moved four stitches on Fremont. The
  real-art mechanism sat next to it — a 15% ladder step on sub-pixel
  overshoots — and only a census of the containment misses on the real
  fixtures found it; the option Kent chose was priced on the bar. **Rule:
  a defect does not get "in every golden" until it has been measured on a
  golden, and a fix is priced on the fixture census, not the probe.**
  *(2026-09-03 — `docs/rail-dents-2026-09-03.md`)*

- **A per-shape gate in stage 4 is not per shape — a small letter is also
  its background's HOLE, and stage 5 reshapes it against that hole.** The
  near-floor curve guard skipped Fremont's 0.4 mm letters correctly (their
  polygons byte-identical flag on/off) and they fell to fill anyway,
  because the background's letter-shaped holes were refined and
  `resolve_overlaps` re-cut the letters against them. Anything in stage 4
  that treats one shape differently has to make the same decision for every
  ring that shape appears as, holes included. *(2026-09-03 — review of
  PR #328; `docs/round-curves-2026-09-03.md`)*

- **A sub-pixel refinement below a few pixels of tolerance reads raster
  texture as geometry, and the damage shows up in the CLASSIFIER, not the
  polygon.** The curve refinement (defect 22) is floored at one pixel; at
  10–16 px/mm that is half the tolerance, so antialiasing and JPEG edges
  earned vertices, every such fixture got rougher, and two borderline
  ribbons changed tier because the DT classifier's 1-px skeleton grew
  spurs off the new vertices (`explained` 0.83 → 0.70 on a 12 × 3 mm
  ribbon that is satin by any eye). Raising the floor costs the thing the
  feature exists for (Fremont's O: 33 → 17 vertices at 2 px). The cure
  was a gate on tolerance-in-pixels, and the instrument that found all of
  it was a PER-SHAPE tier diff (`tools/curve_tiers.py`) — a design-level
  stitch count saw none of it. **Rule: any stage-4 geometry change flips
  with a per-shape tier diff on every fixture, paired by centroid, not by
  shape id (ids are content-derived and move with the polygon).**
  *(2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

- **The satin/fill classifier's boundary-detail sensitivity is intrinsic
  to its thresholds — eight cures measured, all worse, do not rebuild.**
  Five verdicts in 219 flip when only a polygon's boundary detail changes
  (`tools/ribbon_stability.py`), four of them shapes sitting on a
  threshold (cv 0.5, aspect 3, `explained` 0.80). Pruning skeleton spurs
  at three strengths, the sewing spur rule, a hybrid that keeps the blob
  detector on the full skeleton, morphological smoothing of the
  classifier's raster at 1 and 2 px, and a margin band on the regularity
  edge: flips 3–12 against 5, shipped verdicts changed 2–48, and the 2 px
  smoothing turns the BAR and T archetypes into fill. The mechanism: on a
  compact shape the spurs ARE the medial axis, so pruning collapses the
  spine and the remainder reads *regular* — into satin through the
  ordinary path, which has no elongation guard. **Rule: a classifier
  robustness change is scored on shipped verdicts changed AND flips left,
  on the real fixtures, before any threshold is touched; and the one
  mitigation that works is not feeding it boundary detail
  (`_CURVE_MIN_PX_PER_MM`).** A verdict with a margin needs a memory, and a
  classifier that does not rasterize is a different construction — both
  Kent's call. *(2026-09-03 — `docs/classifier-stability-2026-09-03.md`)*

- **"Rail points more than 0.1 mm inside the art" is geometry, not
  coverage — score satin coverage as bare area.** The number (17–23% of
  lettering rail points) was read as the far rail stopping short; every
  one of Becker's 670 was instrumented and none was that: 353 were the
  short-stitch guard's retractions on bends (by design), 115 corridor caps
  at junctions, 129 corners and oblique edges where the rail is on the
  edge along its own normal, 48 tip zones. A rail change that put thread
  on a quarter of the bare area moved that metric by one point. **Rule:
  a coverage claim is measured as the artwork outside a thread's width of
  the sewn crosses (`tools/rail_edge.py --bare`), never as a distance from
  a penetration to the nearest boundary.** *(2026-09-03 —
  `docs/rail-dents-2026-09-03.md` §7)*

- **An area percentage is a fraction of what SEWS, never of what the
  classifier looked at.** `tools/stroke_verdicts.py` divided satin area by all
  region area, and on `becker_marine_logo` @ 100 mm that denominator carries
  1,462 mm² of `BACKGROUND_ENCLOSED` shapes the plan leaves open by design —
  40% of the design, never thread. The published headline "274.0 mm² of satin,
  7.6% of region area" was **75.2 mm² and 3.5%** once measured against the
  2,125.6 mm² that actually sews: `S805585ef` (191.4) and `S501501b6` (7.4)
  are enclosed background, so 27% of that figure was real. The same divisor
  sat under both sides of every "x% → y%" arrow quoted for the per-stroke
  rung. **Rule: derive the shape ids from `plan_stitches(...).iter_runs()` and
  report both columns — a verdict on a region that never becomes thread is not
  coverage, and a report that prints only the flattering one will be quoted.**
  Same family as the pull-comp defect above: prove it on the emitted stitches,
  never on the plan — here the plan is the honest half and the CLASSIFIER is
  the flattering one, which is why the rule has to name the source rather than
  the layer. *(measured 2026-09-06 — scope-history 09-06)*

- **A report tool must CALL the shipped function, not restate its rule.**
  The same tool printed the plan's bare `frac >= 0.75` arithmetic under the
  heading "would flip", and that read as what `cfg.satin_per_stroke` does: 5
  regions and 1,434.3 mm². What ships takes **3 regions and 78.8 mm²** — the
  cap veto and Law 31's floor both sit between the arithmetic and the verdict,
  and neither existed when the report was written. Restating a rule in a tool
  gives you a second copy that drifts the moment the first one is corrected,
  and nothing fails when it does. **Rule: call `classify_ribbon` both ways and
  diff the verdicts; keep the plan's arithmetic only if it is LABELLED as not
  shipped.** The rewrite reproduced 3/78.8 independently, which is the
  cross-check that had been missing while every number came from one path.
  It also surfaced the veto on real artwork rather than on the fixture built
  for it: `S4d48640b` reads frac 0.83, and one of its eight strokes measures
  p90 5.52 mm against the 5.0 cap. *(measured 2026-09-06)*

- **A geometric column detector counts fill turns as columns — read OUR
  numbers off the satin runs, the file's off the whole plan.**
  `tools/satin_columns.py` finds columns by sign-alternating leg pairs
  because a professional's file has no run kinds, and on our own plan that
  also catches tatami row turns: 0.2–0.5 mm "columns" that swamp the real
  population wherever fill dominates. On `becker_marine_logo` @ 100 mm,
  **148 of 184 columns were not satin**, dragging the reported median to
  0.29 mm when our satin measures **3.82 mm** (p90 4.93). At 80 mm, where
  the design is satin-heavy, only 34 of 2,876 stray and the number is fine —
  so the defect hides exactly where the design is worst, and 100 mm is where
  every per-stroke figure was quoted from. It also inverted the tool's own
  hairline alarm: 87% of "our" columns under 1.0 mm is 23% for the ones we
  sew. **Rule: `passes_from_plan(..., kinds=...)` for our own width
  distribution; whole-plan only for the cross-file comparison, which is all a
  machine file can offer.** *(measured 2026-09-06 — scope-history 09-06)*

- **`SATIN_MAX_WIDTH_MM = 5.0` is not what separates us from the pro — the
  professional's own p90 column is 5.00 mm.** The record diagnosed the
  residual gap to the pro's 44.3% as "the 5 mm cap against Becker's genuinely
  6–9 mm letter strokes". Measured on the pro's own files with our own
  instrument: median column **2.52 mm, p90 5.00** on `beckers_logolc.dst`,
  which is **95.7 × 58.3 mm** — the same artwork at essentially our 100 mm
  test size, so the scale confound is ruled out by measurement rather than
  assumed. Whatever that digitizer chose to satin, they satined it under the
  cap. **Do not propose raising `SATIN_MAX_WIDTH_MM` to close this gap.** What
  differs is how few shapes reach the tier — ONE satin shape at 100 mm — and
  the columns we do sew are already professional width (3.82 median). The gap
  is segmentation, full stop. *(measured 2026-09-06)*

- **A p90 width gate IS blind to a 3% tail — but that tail is NOT what leaves
  the bare cloth. Hypothesised, tested and refuted the same day.**
  `classify_ribbon` admits a shape when the DOUBLED p90 medial radius is under
  `SATIN_MAX_WIDTH_MM`, and `promoted_ribbon`'s guard is the same statistic, so
  `Sead76620` @ 80 mm passes at **p90 2.67 mm** while its medial width MAXES at
  **7.80 mm**, 2.8% of the spine over the cap (`Sf6b42aaf` @ 90 mm: 2.85 /
  8.86 / 3.5%). That gap is real and worth knowing. The inference drawn from it
  was not. `_rail_points`' hard ceiling — `min(..., machine.SATIN_MAX_WIDTH_MM
  / 2)`, ~line 2085, whose own comment justifies itself with *"a satin cross
  this module will not classify past 5.0mm in the first place"*, which the p90
  gate makes FALSE — looked like the mechanism. **Lifting that ceiling to 99 mm
  moved uncovered 23.8 → 22.8 mm² and cost 718 stitches (+13%).**
  `satin_rails_follow_edge=True` moved it to 21.0. Neither is the cause.
  **What stands:** 100% of that fixture's `ARTWORK_UNCOVERED` at 80 AND 90 mm
  is inside SATIN shapes — read off preflight's own per-shape attribution — and
  it is the whole reason it grades B 76. **What does not:** any claim about
  WHY. Under a corridor model (farther from the spine than 1.25x the local
  half-width + 0.2) the shape carries 160.6 mm² outside every stroke's corridor
  in **163 components**, largest 15.6 mm² — diffuse shortfall across a branchy
  27-stroke shape, not one missed arm and not one bulge. **Rule: judge a width
  gate on the tail it cannot see — print the MAX and the fraction over cap —
  but never attribute bare cloth to that tail without lifting the ceiling and
  re-measuring.** Both experiments were cheap and I nearly skipped both.
  *(measured and refuted 2026-09-06 — scope-history 09-06)*


- **Bare cloth in a satin shape is at the JUNCTION, and no cross-length knob
  reaches it — four of them measured.** Across the whole corpus at 80 mm,
  `tools/width_tail.py --corpus` finds **2 of 255 satin shapes** leaving any
  bare cloth: `Sead76620` (`becker_marine_logo`, 23.8 mm²) and `Sf80b4c46`
  (`photo_scene_stub`, 6.5). Both `promoted_ribbon`, both MAX medial width
  ≈ 7.8 mm, both p90 under the cap. A `MAX > 6.0` gate demotes exactly those
  two with ZERO false demotions — but read it as a MARKER, not a mechanism,
  and note n = 2: MAX ≫ p90 means "this shape has a big junction", and the
  junction is where the thread is missing. Located by replicating preflight's
  own coverage grid: the dominant patch is 37.2 mm², **0.42 mm from a stroke
  END, with five strokes within 3 mm**. Ruled out, each by experiment on
  Becker (23.8 mm² shipped): `_rail_points`' 5 mm ceiling lifted to 99 → 22.8
  for +13% thread; `satin_rails_follow_edge` → 21.0; the corridor cap
  `floors*1.6` → `floors*3.5` → **23.8, no change at all**;
  `_JUNCTION_TUCK_MM` 0.4 → 1.6 → 22.8. **Every one of those changes how LONG
  a cross is; none changes WHERE crosses are placed** — along a spine,
  perpendicular to one arm, sized by a ray that measures that arm's width, so
  at a junction it reads ~2 mm and not the junction's 5.27. The interior is
  covered only by arm overlap, which is what the docstring intends ("the
  junction gets the modest overlap of its arms") and which does not close on
  five arms. **Rule: do not reach for a cap when thread is missing at a
  junction — check whether any cross is PLACED there first.** The fix, if the
  hypothesis holds, is covering a junction explicitly; it is untested.
  *(measured 2026-09-06 — scope-history 09-06)*

- **When thread is missing at a junction, sew the hole — do not tune a cross.**
  The fix that worked, after four that did not: `cfg.satin_patch_junctions`
  (2026-09-06, DEFAULT OFF, byte-identical off) rasterizes the thread a satin
  shape actually emitted, using the same `machine.COVERAGE_THREAD_W_MM` ribbon
  `preflight._coverage_map` grades with, finds the artwork that thread missed,
  and sews patches over 5.0 mm² as tatami under the shape's own id. On
  `becker_marine_logo`: `ARTWORK_UNCOVERED` **23.8 → 0.0 mm² at 80 mm and
  44.5 → 0.0 at 90**, B 76 → B 88, for +7-8% stitches and 3-4 trims — and on
  the corpus's only other positive, `photo_scene_stub`, **6.5 → 0.0** for +2%.
  **30.3 → 0.0 mm², 100% of the corpus's bare cloth**, at no cost on the 253
  shapes with nothing to find. Two
  patches on `Sead76620` — the K's crotch (37.2 mm²) and an R (8.6) — 45.8
  against preflight's eroded 23.8, the difference being that erosion plus a
  deliberate 0.30 mm grow so the patch runs UNDER the columns around it
  instead of butting against them and leaving a thread-width seam on every
  side. **Two rules fall out.** First: the patch floor is
  `preflight._UNCOVERED_MIN_PATCH_MM2` on purpose — a fix that patches to a
  different floor than the grader measures either leaves findings standing or
  spends thread on holes nobody grades. Second: **prove the fix through the
  instrument that reported the defect**, not on the geometry the fix computed
  for itself, or you have only tested that a function agrees with itself.
  Two costs disclosed rather than buried: the patch sews at
  `best_fill_angle_deg`, so its sheen will not match the satin around it
  (Kent's eye, not a number — the whole reason the flag is OFF), and it is
  appended at the END of the shape, so the needle hops in and out and Becker
  goes 29 → 32 trims at 80 mm on a fixture `TRIM_HEAVY` already flags. *(2026-09-06 —
  scope-history 09-06; renders in `docs/renders/junction-bare-2026-09-06/`)*

- **Becker's TRIM_HEAVY is the "never travel over finished satin" rule meeting
  a 27-stroke shape. Four hypotheses, all measured, all refuted.** Ours runs 29
  trims on 5,531 stitches (5.2/1k) against the professional's 12 on 11,274
  (1.1/1k) for the SAME artwork; 19 of our 28 pen-ups stay inside `Sead76620`.
  `_graph_travel` already walks the unsewn skeleton — 32 calls, 8 succeed.
  **(1) Order.** A connectivity-aware `_order_strokes` preferring reachable
  strokes gives **29 trims, 5,531 stitches, byte-identical**; it changed the
  pick zero times in 32.
  **(2) `TRIM_AT_MM`.** Raising it from 3.0 looked obvious (16 of 28 pen-ups
  are 3.5-8.4 mm; a 10 mm threshold gives exactly the pro's 12) and the pro
  file appeared to show 71 JUMPs against 12 trims. **Wrong reading.**
  Classifying every needle-up move in all five pro files: **69 cut, ZERO
  floats**, shortest cut **3.9 mm**, p50 21.3. The "jumps" are DST encoding a
  long move. Professionals cut everything to ~4 mm. **Do not raise it.**
  **(3) Spurs.** The degree histogram is `{1: 1, 2: 1, 3: 17, 5: 23, 6: 4,
  7: 1, 8: 1, 10: 1}` — one degree-1 node in 49. Pruning buys nothing.
  **(4) The Eulerian floor.** `odd/2 − 1` = 20 against 19 in-shape trims is a
  tempting match, and widening `_build_travel_graph`'s 0.5 mm `node_at` merge
  lowers it (1.0 → 17, 1.5 → 14). Measured end to end: **29 trims at every
  radius 0.5-2.0 mm.** A real bound, not the binding one.
  **(5) Eulerian chaining.** Consecutive strokes that SHARE an endpoint need no
  travel at all, so an Eulerian order should beat any distance heuristic. It is
  **worse: 32 trims against 29.** The reason also explains the 9 "cursor
  off-web" and 2 "target off-web" failures — **a satin column starts at a
  cap-extended RAIL point, not at a spine node**, and the underlay starts
  somewhere else again. The web is built from skeletons; the needle lives on
  rails, so chaining spines buys nothing.
  **What binds is TEMPORAL.** Travel is permitted over unsewn strokes only, so
  logging that shape's 20-stroke sequence against progress: ok at 5/15/20/40%,
  then **"no route" on all nine calls from 45% to 85%.** After 40% of a shape
  is down the walk never succeeds again, and a 27-stroke shape spends nearly
  all its life mostly-sewn.
  **The fill tier got here first** — `docs/scope/1-auto-digitizing-quality.md`
  ruled out ordering, threshold and travel for `stage6_fill` on 2026-08-21
  (*"no route stays inside the shape, at any length"*, 52 of 56; travel's
  ceiling 4 of 56). Two tiers, two shapes, three weeks apart, same answer —
  **cite it rather than re-deriving it.** What the satin side adds is WHEN it
  dies: "no path to find" is not a fixed property of a shape, it BECOMES true
  as the shape fills in, which is why no static property of the geometry
  predicts it. **Rule: a trim count on a many-stroke satin shape
  is the price of not running stitches over finished satin — check how far
  through the shape the failures start before touching any knob.** The lever is
  the number of strokes in the shape; WHERE to change that (segmentation,
  skeletonization, stroke decomposition) is not established.
  *(measured 2026-09-06 — scope-history 09-06)*

- **`cfg.satin_patch_junctions` costs +0.25% across the corpus — and over-fires
  on one fixture.** ON vs OFF over all 26 scorecard fixtures at 80 mm: **23
  byte-cost-identical, 3 patched, 315,371 → 316,160 stitches.** Becker +383
  (uncovered 23.8 → 0.0), `photo_scene_stub` +347 (6.5 → 0.0), and
  **`logo_bridge_bar` +59 with 0.0 uncovered BOTH ways** — a patch on a hole
  the grader does not count, because this pass is deliberately stricter than
  preflight (no 0.4 mm erosion, a 0.25 mm cell against 0.5) so a patch clears
  the finding with margin. **Correct the absolute claim: "nothing pays for it
  where there is nothing to find" holds for 23 of 26, not all.** And read "100%
  of the corpus's bare cloth" as *100% of the bare cloth in SATIN shapes* — the
  two largest figures in the corpus are `photo_subject_stub` **956.0 mm²
  (23.4%, D 58)** and `photo_grass_macro` **407.5 mm² (8.9%, B 76)**, both the
  recorded baseline and an order of magnitude larger than the 30.3 mm² this flag
  clears — and **both are the PARKED thread-paint ruling, not open defects**: a
  tier spy shows `photo_subject` routes to `streamline_fill` (`photo_scene` goes
  to `stage6_fill.stitch_shape` — meadow, 10 calls, coverage p50 2.95, uncovered
  0.0), and their coverage p50 of 0.49 / 0.54 sits inside the 0.52-0.59 band
  recorded above for thread-paint, which Kent tabled. The grader is correctly
  reporting a deliberate choice. **Do not re-open it.** (Their runs carry `fill`
  KIND, which is not the fill TIER; a first draft confused the two.) *(measured 2026-09-06 —
  scope-history 09-06)*

- **All seven F-grade fixtures fail on ONE finding, and it is three unrelated
  problems.** `THREAD_MATCH_POOR:block` grades 7 of 26 corpus fixtures (14 of
  52 matrix entries) at F 0, all baseline, all class `gradient` — which is
  where real logo art goes. Isolating the yardstick line
  (`photo = _is_photo_class(...)`; forcing `_is_photo_class` itself is a
  CONFOUND, it also gates `PHOTO_RESOLUTION_LOW` and the subject check):
  **(1) the raw yardstick, 4 of 7.** `golden_tee`, `drone_render`,
  `region_blobs`, `summit_badge` clear every block under EXCESS scoring and are
  untouched by halo dissolve — their assignments are already optimal and raw
  distance condemns them anyway, which is the exact failure the photo route's
  2026-08-24 rescoring was built for and which the gradient lane never got.
  **(2) halo cones, 1 of 7.** `gaulke_roofing` needs no yardstick change:
  `cfg.dissolve_phantom_blends` alone gives **F 0 → C 64, blocks 3 → 0, worst
  ΔE 63.6 → 6.8, −15% stitches** (B 76 with excess too). Kent ruled that flag
  OFF 2026-09-04 on trims, cones and worst-excess; **the record carries no
  grade for it and this is it.** It costs elsewhere — bridge_bar 3 → 4 blocks.
  **(3) region colour != the artwork under it, 2 of 7.** `bridge_bar` and
  `screenshot_phone_ui` block under every combination, and the screenshot's
  looks blatant: **`0111 Whale` (127,127,127) scores 33.0 ΔE on artwork read
  as (252,252,252) while the design already loads `0015 White`**. **It is NOT
  a permuted palette, and the code says so without another measurement:**
  `select_palette` ends `assignment = np.argmin(dist[:, sel], axis=1)` — every
  region gets its NEAREST selected medoid, so with White selected the region's
  own colour must be nearer Whale. So the fault is UPSTREAM: the region's
  stored colour disagrees with the artwork inside its own polygon, which
  rasterising that polygon over the re-read artwork confirms — 114 clean
  pixels at (252,252,252) on a 0.94 mm² shard holding a 127 grey.
  **It is not the erosion fallback** (that path never fires here) **and it is
  not systematic**: slivers of 0.45-0.60 mm² at 251-253 take `0015 White`
  correctly and a 41 mm² region at 118 takes Whale correctly. Two regions of a
  hundred-plus are wrong, and the 53%-area block on the same fixture is an
  honest "no closer cone" (artwork 46 vs Dark Charcoal 40,40,33, ΔE 10.5).
  **What separates them from the slivers beside them is that they are
  BIMODAL** — luminance 24-254 and 0-255, 18% and 42% below mid-grey, against
  a correctly-assigned 0.60 mm² control whose 117 pixels sit in ONE 32-wide
  bin. **I read that as a palette failure (a mean over a bimodal pool) and
  that was WRONG.** `revalidate_threads` names bimodality as the fingerprint
  of something else: *"a drifted sliver is bimodal by construction — part of
  it still sits on the colour its thread was chosen from, part has moved onto
  something else."* **The real cause is that stage 4 ALREADY FIXES THIS and a
  pixel floor excludes exactly these shapes.** `revalidate_threads` (fix #6.3,
  2026-08-11) re-reads every final polygon and re-snaps the drifted — on this
  fixture 46 of 153 shapes wear a thread that differs from the stage-2 label
  under their own outline, i.e. it ran and worked. Instrumenting the real
  function: **74 asked, 67 skipped as `enclosed_background` (by design), 12
  REFUSED on `THREAD_REVALIDATE_MIN_PX = 200` — every one of them 50-199 px.**
  **`preflight._MIN_COLOR_PIXELS` is 50.** A shape in that band is scored and
  BLOCKED by preflight and can never be corrected by stage 4; the F lives in
  the gap between two floors that were set 4x apart by different authors.
  Asking anyway for those 12, with the function's own estimator, argmin and
  3.0 dE gate: **7 would change answer**, worst `S43831dcd` — 0.94 mm²,
  **177 px against a floor of 200** — `0111 Whale` at 32.7 dE, would take
  `0015 White` at **1.4**. And this CLOSES the hedge an earlier entry left
  open: `S05f7940d` holds Silver though its mean sits nearer Whale because at
  365 px it is ABOVE the floor, so it WAS re-asked and moved there on the
  median-per-pixel estimator — its thread was never a mean of anything, and
  no stage-2 instrumentation was needed. **And `split_tonal_regions` does NOT
  reach them** — checked, not assumed: its `TONAL_SPLIT_MIN_AREA_MM2` is
  **150.0 mm²** against these 0.94 and 1.72, and turning it on leaves
  `screenshot_phone_ui_golke` identical in grade, blocks, region count and
  stitch count. That mechanism is for LARGE bimodal regions (the 4,200 mm²
  owl body it was built for) and was never the answer here, because this
  bimodality is drift — *"below this the split just manufactures slivers"*.
  Do not flip that flag expecting this wall to move. **The corpus separates
  along exactly this line, which is the independent check on a decomposition
  I got wrong three times first:** refused-on-the-floor counts across the
  seven F fixtures are `golden_tee` 0, `region_blobs` 0, `gaulke_roofing` 0
  (46 of its 56 regions are `enclosed_background` — cause 2 is its story),
  `drone_render` 7, `summit_badge` 4 — against **`bridge_bar` 63 and
  `screenshot` 12**, the two cause 3 is about. `bridge_bar`'s 29 movers
  exceed its 23 in-band shapes: six are UNDER 50 px, so preflight will not
  score them and stage 4 will not fix them — a wrong colour no instrument in
  this repo reports. Instrument: `digitizer/tools/revalidate_floor.py`. **Rule: before calling a cone assignment wrong,
  rasterise the region's own polygon over the artwork and compare — `argmin`
  cannot mis-pair, so a bad cone means the thread was chosen from different
  pixels, and check whether its neighbours of the same size and colour got it
  right before calling it systematic.** **Rule: a bimodal shape in this
  pipeline means DRIFT, not a bad segmentation colour — `revalidate_threads`
  says so in its own docstring, and the next question is always whether that
  function was allowed to run on it.** **Rule: when two instruments disagree
  about what is measurable, read both floors — a defect that one can report
  and the other cannot fix is invisible from either side alone.**
  Unrecorded before 2026-09-06.
  **Rule: never treat a THREAD_MATCH_POOR wall as one defect — split it by
  yardstick, palette and assignment before proposing anything.**
  *(measured 2026-09-06 — scope-history 09-06)*

- **`THREAD_MATCH_POOR` has NO area floor, and half its blocks ride on
  slivers.** It is driven by "each thread's worst such patch", with no minimum.
  Across the seven F fixtures, 25 blocking findings; the worst shape behind
  each measures **min 0.58 mm², p50 3.17, max 1,648.5 — and 12 of the 23
  measurable ones are under 5 mm².** `gaulke_roofing`'s 63.6 ΔE rides a
  **0.58 mm² shard, 0.02% of the design**; `drone_render`'s 14.1 rides
  **1,648.5 mm², 53.6%**. Both emit `block` — "do not sew". Every sibling check
  here has a floor (`_uncovered_findings` 5.0 mm², `_lettering_findings`
  `MIN_LETTER_EXTENT_MM` 4.0). **Rule: when a design grades F on thread match,
  read the worst shape's AREA before believing the design is unsewable** — the
  finding SAYS it as of 2026-09-06 (`0.58 mm² — 0.03% of the design`, plus
  `worst_shape_area_mm2` / `worst_shape_area_frac` in `extra`), so this no
  longer costs a measurement. The share is over the SCORED regions, not all of
  them: `logo_gaulke_roofing` has 46 enclosed-background regions of 56, and
  counting those would shrink every share. **So every share the finding prints
  is slightly LARGER than the row above** — 54.48% against 53.6% on
  `drone_render`, 0.03% against 0.02% on `gaulke_roofing`. The rows are the
  older all-regions denominator, kept as the numbers that were actually
  measured; the finding is the better one. Neither is a drift to chase.
  Whether the check should have a floor is a product call — moving it re-bases
  the scorecard for at least four fixtures — so this is recorded as a
  measurement, not a proposal. *(measured 2026-09-06)*


- **Publish the number the instrument PRINTS. A figure from a side probe is
  itself an unchecked claim — and the entry announcing a claim-checker made
  exactly that mistake.** `doc_claims.py`'s own 2026-09-06 entry reported the
  sweep as *"11 flag defaults and 16 constants in `MASTER_SCOPE.md` and
  `DOCTRINE.md` all agree"*. Re-run at that same commit, the tool prints **no
  flag count at all** and `18` constant checks **across every doc, not the two
  strict ones**; the reproducible strict-doc figures are **6 and 9**. The
  CLEAN verdict was right and still is — only the two numbers beside it were
  produced by a throwaway probe nobody could re-run. **Rule: if the tool does
  not print the number you want to publish, add the print, then quote it.**
  The tool now prints both counts, so the next entry can be copied rather than
  re-derived.

  Two smaller things fell out of the same look, both worth keeping:

  - **A count of CHECKS is not a count of THINGS.** The 18 covers **11
    distinct names**: `FILL_ROW_MM` and `SATIN_MAX_WIDTH_MM` are each defined
    in two modules, so one documented claim is two checks, and a name quoted
    in three docs is three more. The output now says both, because the larger
    number silently overstates coverage.
  - **A clean run that examined nothing reads exactly like a clean run that
    examined everything** — the same trap as CLAUDE.md's quiet-venv
    failure, where a 3.11 venv leaves no pystitch in it and `node --test`
    SKIPS the six format cross-validation tests and still reports green.
    Four separate `continue`s in `check_defaults` dropped a flag claim
    silently (name is not a field; no plain default; a non-bool default like
    `edge_cap`'s `'none'`; a line stating both ON and OFF), so a skipped flag
    and a passing flag were indistinguishable. All four now report. Measured
    the same day: **all 33 `cfg.<flag>` mentions across the eight docs resolve
    to real fields, and no line states both** — so this is insurance, not a
    haul, and `tests/test_doc_claims.py` is what keeps it honest.
  *(measured 2026-09-06 — scope-history 09-06)*

- **When a field's ABSENCE is the signal, adding that field somewhere else
  silently breaks a contract nobody wrote down.** `THREAD_MATCH_POOR` carried
  `excess_delta_e` only on the photo route, and
  `test_non_photo_routes_keep_the_raw_yardstick_untouched` read that
  emptiness as *"this was judged on raw distance"* — stating the reason
  outright: *"the excess fields stay None so nothing downstream can mistake a
  raw finding for a rescored one."* Reporting the excess on every route
  (2026-09-06) is strictly more information and still destroyed that signal,
  and the test that caught it looked at first like a test to relax. **It was
  not: the guarantee was real, only its encoding was accidental.** The fix is
  to state the fact — the payload gained `yardstick: "excess" | "raw"` — and
  assert it directly. **Rule: before widening where a field appears, grep for
  what reads its absence.** A test asserting `x is None` is the cheap way to
  find it; a downstream consumer inferring the same thing is not, which is why
  the fact is now stated instead of encoded. *(2026-09-06 — scope-history)*

- **A `--durations` line under a shared cache is NOT a saving you can bank by
  deleting the test, and `lru_cache` does not survive xdist.** The five
  `test_off_is_byte_identical_to_the_shipped_engine` instances took the top
  two slots in the whole digitizer suite and four of the top six — **over 380
  seconds**. Dropping all five saved **13**. A plugin wrapping
  `pipeline.run_stages` and dumping calls per worker says why:
  `test_bind_resnap_all_classes.py` does **20 real pipeline runs for 8
  distinct `(fixture, flag)` cases** (gw0 3, gw1 6, gw2 4, gw3 7) —
  `lru_cache` is **per-process**, xdist puts tests in different processes, and
  `screenshot_phone_ui_golke(False)` was computed on three workers. A duration
  is that test's share of a bill several workers each pay anyway, and
  wall-clock is the slowest worker's queue. **Rule: `--durations` before
  optimising a suite, and a run-count before believing `--durations`.**
  `--dist loadfile` recovers some of it — measured at CI's two workers,
  23m53s → **22m27s**, 5.8%, same 1889 passed — but it floors wall-clock at
  the slowest single FILE, so it is recorded as an option with its trade
  named, not taken. *(measured 2026-09-06 — scope-history 09-06)*

- **A long benchmark and an active worktree cannot share a machine.** Two
  measurements of the above were thrown away for the same reason: pytest reads
  the tree at COLLECTION, so any edit between two runs of a pair silently
  re-bases the comparison. Attempt 1 compared different trees (accounted-for
  counts 1887 against a collected 1888). Attempt 2 looked like a clean frozen
  pair — until the passed counts read **1870 against 1878**, because a branch
  reset onto a newly-merged `main` mid-pair added another PR's 8 tests between
  the halves; the loadfile side did MORE work, so its "31 seconds slower" was
  not a result in either direction. **The corruption always shows as a passed
  count differing by exactly the tests you added — which is easy to skim past
  when the wall-clock numbers look plausible.** Attempt 3 recorded `HEAD` and
  `git status` before AND after, so the freeze is checkable rather than
  asserted. Sequence it the other way round: edit first, benchmark when the
  tree is quiet. *(2026-09-06 — scope-history 09-06)*

- **Before building a fix for a newly found mechanism, check whether an
  existing, already-priced flag removes its CAUSE.** `COLOR_STOPS_HEAVY`'s new
  `repeated_cones` field found 4 of 52 corpus combos still sewing a cone in
  two blocks with `cfg.merge_duplicate_cones` ON, and the obvious next move
  was a flag extending the fold. **Half the problem did not need one.** A
  duplicate arising from a re-snap onto a cone NO layer declares is invisible
  to both passes that could rejoin it — `rehome_resnapped_regions` refuses it
  by design (*"there is no 'home' to send it to, and inventing one would
  reorder against nothing"*) and the fold works on the same quantize-time
  layer→cone list — but such a cone exists ONLY because the re-snap escaped
  the selected palette, which is defect 15, which already has a built,
  measured, default-OFF switch waiting on Kent. Measured:
  `cfg.bind_resnap_all_classes` takes `screenshot_phone_ui_golke` from **17
  blocks / 16 distinct with `3971` twice to 11 / 11 with none**. Patching the
  rehome would have shipped a SECOND switch for one underlying problem, and
  split the decision across two flags. The half-hour of measurement cost less
  than the flag, its tests, a corpus A/B and that second decision. **Both
  passes were individually correct — the gap fell between them, which is why
  neither looked wrong on inspection.** (The other half, two gradient BANDS of
  different parents landing on one cone, is genuinely separate: bands are
  built in stage 6, long after the fold, and the bind does not touch it.)
  *(measured 2026-09-06 — scope-history 09-06)*

- **A CLAMPED score hides magnitude — read the unclamped value before
  concluding a fix "moved nothing".** `run_preflight` prints
  `max(0, 100 - 30*blocks - 12*warns)`, and **12 of the corpus's 52
  design/garment combos sit on exactly 0 with unclamped scores from −272 to
  −38** (`tools/floor_depth.py`, 2026-09-06) — a 234-point spread behind one
  printed value. `screenshot_phone_ui_golke` must clear **312 points, about
  eleven blocking findings**, before its grade moves a single letter, so a fix
  clearing TEN of them still prints `F 0`. This is the missing half of
  yardstick-disagreement 1: a real thread fix there is invisible because
  `THREAD_MATCH_POOR` judges per thread on its worst patch **and** because the
  design is hundreds of points under water. It also explains the exception —
  `dissolve_phantom_blends` moves `gaulke_roofing` F 0 → C 64 because gaulke
  grades F **4**, shallow rather than floored, so its improvement had
  somewhere to go. **Rule: on a floored design the grade is not evidence in
  either direction; quote the metric that moved, or the render.** Un-clamping
  or widening the bands re-bases every grade in the scorecard, so it is a
  product call, not a cleanup. *(measured 2026-09-06 — scope-history 09-06)*

- **A checker's first output is not evidence its pattern is right — read the
  MATCHES, not the count.** A first cut of `doc_claims`' test-count check
  matched "the first number within 40 characters of the filename" and
  reported **six drifts** in `docs/scope/1`, the worst `test_satin.py` at a
  documented 43 against 99 collected. Every one was false: `**43/43**` is a
  pass/total at the time, `gains 6` and `(17 → 22 tests)` are deltas, and
  `together **46/46**` is two files combined. **None was a claim about the
  file's current size at all.** Shipping on that count would have produced
  exactly what this tool's own design note warns against — a checker that
  cries wolf on legitimate narrative is a checker nobody runs. The same
  discipline killed a sibling idea outright: sweeping doc-cited FILE PATHS
  found **373 references and 0 stale**, because a path here is either right or
  cited inside a sentence saying it was deleted (`tools/bundle.mjs`,
  `src/app.js`) — so that checker was not built. **Rule: before building a
  checker, sweep for the thing it would catch; then read what it matched, and
  only then decide the pattern.** *(measured 2026-09-06 — scope-history 09-06)*
