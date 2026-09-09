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

- **Ink/Stitch is GPL-3.0 — concept-level clean-room reimplementation only.**
  No literal copying and no near-verbatim translation, however convenient.
  The one exception is `pystitch`, its MIT-licensed pyembroidery fork, which is
  usable as a real runtime dependency and has been adopted as one. Moved here
  from MASTER_SCOPE 2026-09-08: it is a constraint on how work may be done, not
  a status, so it does not belong in a file that holds current state.
  *(confirmed 2026-08-10 — `docs/inkstitch-research-2026-08-10.md` §0)*

- **Ember's own editor toolset is on file — read it before scoping manual
  digitizing work.** Pen/node, Closed Shape, Drawing Blocks, stitch simulator,
  realistic-view toggle. Named here so the next person checks the teardown
  instead of re-deriving a competitor's feature list.
  *(confirmed 2026-08-08 — `docs/ember-technical-teardown-2026-08-08.md`)*

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

- **A union of fills is NOT a silhouette until its cracks are filled — and the
  border loop gate cannot see a crack.** `unary_union` over neighbouring
  regions' polygons leaves hairline holes wherever two edges nearly coincide
  (Instagram icon at 80 mm: 20 of them, 0.0–0.1 mm wide, up to 7.7 mm long,
  owned by no region). `BORDER_MIN_LOOP_MM` is a PERIMETER floor, which a long
  thin crack clears; a hole's satin crosses are cast outward into the host,
  so they always fit; and nothing in `border_runs` asks a hole's WIDTH. Result:
  a 0.25 mm² crack sewn as an 89-cross, 3.4 mm satin bar mid-design — the
  "satin border leaving the infill perimeter" Kent saw with Design edge =
  Satin. Gate any hole on whether the column can stand in it
  (`stage6_border._fill_cracks`), never on its perimeter. The per-shape
  border's `visible` geometry (polygon minus later shapes) can carry the same
  cracks; it is not gated yet. *(measured + fixed 2026-09-08 — Kent's call:
  skip holes narrower than the column, keep real holes capped)*

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
- **The ERROR path is customer copy too — and an error caused by the
  CALLER'S own edit must keep its own message.** `jobs.py` set
  `job.error = f"{type(exc).__name__}: {exc}"` and `digitizer.js` throws that
  at the user, so a 1x1 upload read *"ValueError: no foreground pixels — the
  whole image reads as background"* three lines after the upload gate's two
  well-written rejections. Not pathological: `stage1_prep` raises it for any
  artwork whose subject the background detector eats.
  `digitizer_service/errors.py` maps the artwork-caused failures and puts the
  raw form in `job.detail` beside the traceback.

  **The correction is the reusable half.** The first cut replaced EVERY
  unmatched exception with one generic sentence, and three service tests
  failed: a bad `boundary_override` and a non-adjacent `merge_shape_ids` fail
  with messages naming the caller's own edit, which is the only thing that
  lets it be undone. **Engine-leak and caller-feedback look identical from the
  job boundary and are opposites.** So it is an ALLOWLIST of artwork failures,
  and anything unmatched passes through unchanged — `KeyError: thread_index`
  stays reachable in principle, which is the status quo, and buying it out
  costs three real contracts. `tests/test_job_errors.py` (9).
  *(found and fixed 2026-09-07 — scope-history 09-07)*

- **RUN THE APP. A screenshot found in one look what six hours of reading the
  same code did not.** 2026-09-07, after a session spent measuring warning
  voice, code seams and doc budgets by reading source: the Studio was launched
  and `logo_bridge_bar.jpg` pushed through it. The slider said **"Colors
  (max 6)"**. The caption said **"13 colors"**.

  Nothing in the repo was hiding it. `tools/warning_coverage.py` had run over
  the same fixture that morning and could not see it, because it read
  warnings; MASTER_SCOPE had said for weeks that stage 0 routes **six of seven
  real customer logos to gradient**, and `stage2_quantize`'s cap had a comment
  explaining itself. **The defect was the JOIN between three documented facts,
  and a join is what a screenshot shows and a file read does not.**

  Root cause: `stage2_quantize` caps the FLAT lane hard; the SLIC+RAG lane
  passes `max_k=cfg.max_colors` into k-medoids, which is a clustering
  parameter and not a cap. So the one control a customer has over thread count
  — **the cost driver**, one spool to buy and one manual re-thread per cone on
  a single-needle machine — was enforced on the artwork type customers do not
  have. Measured: **6 of 26 designs over the cap and all six gradient**, worst
  `drone_render` at **22 cones against a promised 6**, `COLOR_CAP_APPLIED`
  firing on zero of twenty-six. Fixed behind `cfg.enforce_color_cap`
  (MASTER_SCOPE 31): 6 over → 1.

  **The generalisation is not "test the UI".** It is that a promise made in
  one file and kept in another is invisible to every instrument that reads one
  file at a time, and this repo's instruments all read one file at a time.
  Drive the product when the question is whether it does what it says.

  *(found 2026-09-07 — `digitizer/tools/color_cap.py`; scope-history 09-07)*

- **Before capping, splitting or merging anything, ask WHERE the thing comes
  from — it is five minutes and it decides between a fix and a rewrite.**
  The cap above could only work at stage 4 if the surplus cones were REGION
  threads; if they were shade bands built in stage 6 it would have been
  useless there. One probe answered it: on `drone_render` (74 regions, 24
  region threads, 22 sewn) and `logo_bridge_bar` (74, 13, 13) the set of block
  threads that are NOT region threads is **empty on both**. Build at stage 4.

  The same probe named the residual honestly instead of rounding it off:
  `region_blobs` keeps 15 cones because it has only **4 region threads** — the
  cap correctly does nothing — and **12 of its 15 sewn cones are built after
  it**, in stage 6 blend bands. That is defect 16's open half, on a generated
  fixture no client artwork produces. "6 of 6 fixed" was the available
  sentence and it was not true. *(measured 2026-09-07)*

- **A budget nothing checks is a preference — and when MASTER_SCOPE's hit,
  the reclaim is NOT a defect.** `MASTER_SCOPE.md` has stated *"Current state
  ONLY, under an 800-line budget"* since it was split from DOCTRINE, with
  `docs/scope/` and `docs/scope-history.md` as the two places overflow goes.
  Nothing enforced it, and on 2026-09-07 it reached **799** — noticed only
  because the next entry did not fit. `tests/test_scope_budget.py` (6) now
  enforces it, and its failure message names the reclaim rather than just
  saying "too long", because a bare limit gets the next line squeezed in
  somewhere else.

  **Where the lines actually are** (`tools/scope_budget.py`, measured
  2026-09-07): capability areas **255**, cross-cutting **141**, live defects
  **138** over 30 numbered entries, waiting-on-Kent 95. Live defects are
  **17%** of the file — the instinct to retire one is aimed at the wrong
  section, and it reclaims **nothing** anyway, because the Closed section
  keeps every number *"because ten other docs cite them by number"*, so Live
  → Closed swaps a line for a line. **Area 1 alone takes 107 lines against a
  detail file of 3,871**; areas 2, 4 and 5 take 14, 21 and 43. Summarising
  area 1 back down to a summary is the document's own offload mechanism,
  already built and already linked from the section header.

  Two smaller notes from the same read. **The counter must be `wc -l`** —
  `split("\n")` on a trailing-newline file returns one extra element, and the
  first cut of the tool reported 800 for a file `wc -l` calls 799, which
  would have failed the budget a line early. And **the pressure is structural,
  not editorial**: entries here are single very long lines, so compacting an
  entry's prose reclaims nothing at all; only removing or offloading a
  paragraph does.

  **The same file states a SECOND rule nothing checked** — CLAUDE.md's *"Every
  claim carries a `(verb date — source)` pointer; one without a pointer is
  unverified."* Measured clean, **18 of 18** live entries, and all 12 closed
  pointers dated inline; both are asserted now, because an unsourced claim
  reads exactly like a measured one. **The first cut of that check reported
  twelve violations and every one was false**: `### Closed` is an H3 INSIDE
  the Live defects H2 and its entries are pointers by design, so slicing on
  the H2 alone swept them in. Read the matches, not the count — the third time
  in one day, after an uppercase-only warning-code regex and the palette
  tool's two overstatements. *(measured 2026-09-07 — scope-history 09-07)*

- **Preflight findings reach the customer ranked and coloured; pipeline
  warnings cannot be, because they carry no severity at all.**
  `QualityReport.svelte` sorts findings `{block: 0, warn: 1, info: 2}` and
  paints `sev-block` `--danger`, `sev-warn` `--warn`, `sev-info` `--muted`.
  The warnings list one panel over has no sort, no filter beyond a single
  hand-named code, and no colour — **and it could not have one**:
  `warnings_codes.warn()` returns `{code, message, **extra}` while
  `preflight.finding()` returns `{code, severity, message, **extra}`. So the
  weak surface is not a Studio oversight; the field does not exist upstream.
  Adding it means assigning a severity to each of 57 codes, which is a
  product call about voice and volume, not a refactor. **Recorded, not
  built.** *(measured 2026-09-07)*

- **A warning's SEVERITY is decided by its CONSUMERS, not by its own words.
  Read them before writing the number down.** `PALETTE_THREAD_MISMATCH` fires
  on **6 of 26** corpus fixtures, appears in NO document, and its own code
  comment says *"the operator loads a cone that sews nothing while the thread
  that IS sewn is missing from the list"*. That reads like a defect that
  ruins a job at the machine. It is not, and getting from there to the true
  answer took **three corrections, every one from reading a contract rather
  than from measuring harder** — each of which made the finding SMALLER:

  1. **Wrong list.** The first cut of `tools/palette_mismatch.py` compared
     `result.palette` against what sews and printed "RACK-WRONG". But the
     operator threads from `plan.palette` — per BLOCK, `palette[i]` describes
     `blocks[i]` — while `result.palette` is the per-LAYER list the review
     screen edits. Reading the layer list positionally against blocks is the
     exact mistake `StitchPlan.palette`'s own comment records as shipping
     `golf_hat`'s black block labelled "0020 Tangerine" until 2026-08-14. The
     operator list is now CHECKED per fixture rather than assumed: **26 of
     26 consistent.**
  2. **Confounded.** The second cut reported "threads that sew but are absent
     from the review list" — which is BY DESIGN: a blend or tonal region sews
     several shades inside one layer and the shades ride in `stats.blocks`.
     `gradient_ramp_linear` gave it away, **1** mismatched shape beside
     **4** "missing" threads.
  3. **Already defended.** The clean number is real — 34 shapes over the six
     fixtures, and on all six the thread those shapes sew is on **no review
     layer at all**. Then read the consumers. `reviewFromJob` resolves a
     shape's colour `byNumber.get(s.thread_number)` **with a `stats.blocks`
     fallback keyed by the shape's own `sew_block`**, and
     `QualityReport.svelte` refuses the layer palette outright with a comment
     saying why. **Nothing in the Studio renders the layer list as a cone
     list**, so the customer-visible impact today is nil.

  **So it is a real internal inconsistency with a nil blast radius, and the
  value of the warning is as a regression detector** for the day someone adds
  a consumer that reads `review.palette` positionally or as a cone list. That
  is worth knowing and worth NOT chasing. MASTER_SCOPE defect 30.

  **The reusable half:** an instrument that only ever confirms is not
  measuring. Three passes, three shrinks, and the correcting evidence was in
  a docstring each time — not in another corpus run.
  *(measured 2026-09-07 — `digitizer/tools/palette_mismatch.py`;
  scope-history 09-07)*

- **A DIAGNOSTIC and a CUSTOMER SENTENCE are two different strings. Never
  build one out of the other.** Three photo-prep seams degrade to a documented
  no-op when the machine cannot run them, and all three used to write
  `f"X was skipped — {reason}. ..."` while ALSO passing `reason=` beside it —
  so the panel printed the server's own filesystem: *"isolated rembg venv not
  found at /home/user/EMB-Bot/digitizer/rembg_isolated/venv/bin/python"*,
  *"YuNet model file missing at …"*, *"SAM2 worker exited 137: <the last line
  of somebody's STDERR>"*. None of the three codes is translated, and
  `describeWarnings` falls back to `String(w.message)` with no severity
  filter, so every one of them rendered verbatim as a list item. **Measured
  9 of 26 corpus fixtures for the background-removal one alone — and not a
  corpus artefact:** `cfg.photo_prep_background_removal` defaults True and the
  ruling directly above ships rembg as a DEPLOY REQUIREMENT, so this is the
  expected field condition, not an edge case. Fixed 2026-09-07 by routing all
  three through `pipeline._environment_warning`, which is a MOVE and not a
  deletion — the reason was already in the payload. **The reusable half is the
  shape, not the fix:** it was a FAMILY of three built from one pattern, and
  fixing only the site that was measured would have left two identical
  siblings, which is exactly the missing-port defect (27) this repo keeps
  rediscovering. `tests/test_environment_warnings.py` (7) carries an AST
  tripwire over the whole package that rejects a `warn()` message f-string
  interpolating any `*_reason` name; run against the pre-fix file it names all
  three sites and their line numbers. *(measured and fixed 2026-09-07 —
  `digitizer/tools/warning_coverage.py`; scope-history 09-07)*
- **`feat/svg-import-shapes` is not resumed.** Far behind, and the one task
  attempted past the tokenizer is broken against its own tolerance. Treat a
  revival as a fresh plan against `main`, not a rebase; branch left in place,
  deleting it is Kent's call. *(decided 2026-08-07 — scope-history)*
- **Stage 4 reads the anti-alias ramp: `subpixel_edges` is ON by default.**
  Kent's flip 2026-09-09, on the plan's own instrument and nothing softer
  (`docs/superpowers/plans/2026-09-08-subpixel-edges.md`;
  `tools/edge_truth_ladder.py`): every vertex a trace hands the simplifier
  moves to where the image crosses halfway between its two side colours (area
  conservation, not the interpolated 0.5 crossing), the refinement's floor
  follows that acceptance, and the polygon's vertices sit on the true edge at
  every rung drawn at its own resolution — circle vertex spread 0.049 →
  0.013 mm at 400 px, rectangles to 0.01 mm, boundary spread 0.057 → 0.036.
  The costs were measured before the flip and accepted with it: 45–155% more
  vertices on real logos at stitch counts within 3.5%, four borderline
  ribbons changing tier (three on drone, one on meadow), every flat-lane
  golden re-captured — on ubuntu-latest, by the temporary workflow that
  proves the runner on the pre-change engine first, never on this container
  (photo-lane drift) and never on Windows. Three things stay as they are and
  are named, not open: `curve_turn_deg` 15° (now the floor under the ring
  and ribbon; 10° would meet the ladder's criterion on the ring — Kent's if
  ever), sources stage 1 upscaled are declined (the 200 px rung got worse on
  every rectangle), and nothing is smoothed. `subpixel_edges=False` is the
  pre-flip polygon byte for byte and is how the ladder's baseline tests pin
  it. *(Kent's approval 2026-09-09 — scope-history's flip entry has the
  ladder, the tier diff and the golden deltas)*

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

- **A grade quoted without its ARM and its YARDSTICK is not a measurement —
  and I published one.** This session reported gaulke's `dissolve_phantom_blends`
  baseline as *"stale: B 76 with the flag OFF, zero blocking
  `THREAD_MATCH_POOR`, worst ΔE00 0.0"*. Re-measured on the merged tree with
  #396's own `tools/flip_sheet.py`, same config: **F 4, four cones, TWO
  blocking `THREAD_MATCH_POOR`, 10,229 stitches** — and the `halo` arm returns
  a byte-identical row, so the flag is INERT there and the claimed "4 cones →
  3, −14.5% stitches" is wrong too.

  **Where the number came from is the instructive part.** The 2026-09-06 entry
  reads *"F 0 → C 64 … and B 76 with excess as well"* — B 76 was the flag-**ON**
  state under the **excess** yardstick. It was carried across two axes at once,
  onto the OFF arm and onto the default yardstick, and then reported as a fresh
  measurement corroborating #380. It corroborated nothing; it was the same
  misread wearing a second hat.

  **The tell was in the entry it was lifted from.** That same 2026-09-06 line
  records `off` at **10,229 stitches**; the re-measurement returns exactly
  10,229. The baseline had not moved at all, and one number would have said so.

  Caught only because a merge with #396 put the two readings side by side and
  they disagreed — not by any check here. `THREAD_MATCH_POOR` already carries
  `yardstick` in `extra` for exactly this reason (MASTER_SCOPE defect 28's
  "the yardstick that judged the severity"), and this repo already had the
  rule. **Before quoting any grade: which arm, which yardstick, and does one
  cheap invariant from the same source agree?** *(2026-09-07)*

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
  threshold. *(confirmed 2026-08-14 — `stage6_blend._speckle_ratio`; the line reference this carried, `stage6_blend.py:295-299`, had drifted to a different function by 2026-09-07 — cite the symbol)*
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
  - **The runner's CORE COUNT is refuted too, on the diagnostic's first run.**
    The `nproc` echo was added by the very PR that proposed the core-count
    hypothesis, and answered it immediately: `nproc: 4`, `os.cpu_count: 4`,
    `MemTotal: 16 GB` — on a job that took **27m59s** for 1,984 tests, so
    `-n auto` had four workers. The local frozen-tree benchmark that suggested
    it (2 workers 23m53s against 4 workers ~14m00s) does not transfer: **this
    box does the same suite in ~15 minutes on four cores and the runner takes
    28 on four.** What remains is per-core throughput or hypervisor
    contention, and one reading cannot separate them.
    **Four hypotheses, four eliminated — do not attribute a slow job to a
    cause.** Every run now records its own `nproc`, so a fast one will say
    whether the core count varies at all.

  **Practical consequence: budget half an hour and read a 35-minute job as
  normal rather than stuck.** This does not weaken item 7's rule — three green
  checks is still not a green PR — it makes the wait longer than the rule
  implied, so the temptation to merge early is stronger, not weaker.

- **A cross-reference is not an update: a fix can land under one defect and
  leave its twin describing the world before it.** MASTER_SCOPE defect 11 said
  *"the setting that helps a misrouted photograph has no UI"* and that
  `cfg.is_photographic` *"appears **nowhere** in `app/src` (grep, 0 hits)"*.
  Kent's 2026-09-02 call made `isPhoto` send exactly that flag; defect **15**
  recorded the change fully and correctly, and defect 11 — which ends *"See
  defect 15"* — was never touched. Five days later it still asserted the fixed
  condition as live, with 14 grep hits against its stated 0. **Both source
  files had already flagged the staleness in their own comments**
  (`digitizer.js`: *"MASTER_SCOPE's 26-stop figure … predates the rehome …
  17 is what it measures today"*), so the code knew and the doc did not — the
  same shape as everything else that day.

  **The habit: when a fix lands under defect N, grep MASTER_SCOPE for every
  OTHER entry describing the same control.** Pointing at the updated entry
  from the stale one is what made this survive — a reader who follows the
  pointer gets the truth, and a reader who does not gets a false live claim,
  and nothing distinguishes them. Compacting 11 to a resolved pointer also
  bought **11 lines** of the 800-line budget, which is the rule-4 trade the
  file is supposed to make. *(confirmed 2026-09-07)*

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

- **A loose PROBE produces false positives at a steady rate, and the tell is
  always in what the tool reported rather than what the page looked like
  afterwards.** The neighbouring rule — *read the MATCHES, not the count* — is
  about building a checker. This is its cheaper cousin: the one-off measurement
  you take while driving the app, where there is no pattern to review and the
  temptation is to read the number and move. **Five of these in one session
  (2026-09-08), every one of which looked like a defect and was not:**

  | what looked wrong | what it actually was |
  |---|---|
  | `grep -c` said two fonts pulled for licensing were still in `satin-fonts.js` | the only hit was the comment recording their removal |
  | the simulator's scrub `max` was 3324 against a 3,367-stitch design | an internal STRAND index; the counter reads 3,367 / 3,367 at that position |
  | a DST read back with a stitch count that did not match | strands vs stitches again, one layer down |
  | a redo showed 2,253 for a 3,367-stitch design | the digitize panel's own element line, scraped from `document.body.innerText` instead of `.fieldmeta` |
  | the drawing tools "did nothing" when clicked | `ERR btn: no button matching "Basic shape"` — the click never landed |

  **Three of the five are the same mistake:** a pattern loose enough to match a
  neighbouring, differently-scoped quantity — an internal index, an element's
  own stats, a removal note. The other two are a tool that reported its own
  failure into a log nobody read.

  **The rule, and it costs one extra call each time:** before a probe's output
  becomes a finding, read the tool's OWN report (`ERR` lines, exit codes, what a
  click resolved to), and re-take the measurement against the narrowest element
  that can carry the answer — `.fieldmeta`, not the page. A finding that
  survives that is worth writing down; one that does not would have cost a
  reviewer their afternoon. *(2026-09-08 — five instances in one session)*

- **A "CLOSED, confirmed by code read" entry survived three weeks because the
  code WAS right and the product was not.** MASTER_SCOPE's DST section said
  the axis bug was unreachable from the real product: *"Auto-digitized designs
  leave by pyembroidery `/export`"*, confirmed 2026-08-17 by reading the code.
  `isPurelyDigitized` does say that, and reads correctly in isolation. What a
  code read cannot see is that **`defaultProject()` seeds an empty text
  element** which a customer who uploads a logo never removes — so
  `every(el => el.type === "digitized")` was false for essentially every real
  design, the `/export` preference never fired, and **every** DST left by the
  browser codec.

  **Measured on the artifact, not the code** — downloaded from the shipped UI,
  decoded with `pystitch`, the same third-party reader CI cross-validates
  against. The app claimed `81×16 mm`:

  | | bbox pystitch reads | colour |
  |---|---|---|
  | browser DST | **16.3 × 80.5 mm** | **0 COLOR_CHANGE, 1 SEQUIN_MODE + 10 SEQUIN_EJECT** |
  | service DST | 80.5 × 16.3 mm | 1 COLOR_CHANGE |
  | PES (either) | 80.5 × 16.3 mm | 1 COLOR_CHANGE, 2 threads |

  The colour-change byte is not merely unread — on a two-colour design it
  decodes as **switch to sequin mode and eject ten sequins**. That is a job
  that goes wrong loudly, not quietly.

  > **The colour half was FIXED 2026-09-08 (#412); the table above is the
  > measurement as it stood, not current behaviour.** `dst.js` wrote `0x43`
  > where the standard wants `0xC3` — the colour bit without the jump bit.
  > With `0xC3` a browser DST reads **1 COLOR_CHANGE, no sequin**, stitch
  > count unchanged, matching the service DST and PES in the colour column;
  > a six-block design with a trim before each stop reads back as exactly
  > 5 COLOR_CHANGE and 5 TRIM. **The axis half was then fixed too, later the
  > same day (#414), so the bbox column is historical as well** — this note
  > was written between the two and said the axis was "untouched and still
  > Kent's", which held for a few hours. Both weight tables were swapped to
  > match `pystitch.DstWriter.encode_record`, verified byte-identical across a
  > spread of deltas, and gate 1's DST entry was retired (#415). What made the
  > colour half separable is that it moves no geometry, and EMB-Bot's own
  > decode is byte-identical either way (`dstimport.js` already tested
  > `b2 & 0x40` ahead of the jump bit), so it was never really part of the
  > axis call it had been filed under since 2026-07-31.

  **The lesson is about the word "confirmed".** A code read confirms what the
  code says; only running the product confirms what the customer gets. Both
  entries were written honestly and the second one is what caught the first.
  When a closure rests on a code read, say so in the pointer — that entry did,
  which is the only reason this was checkable.

  **And the trade-off, stated because it is real:** `dstimport.js` is
  transposed too, so a service-encoded DST re-imported into EMB-Bot now reads
  `16×81`. The two bugs used to cancel for a browser→browser round trip. The
  machine is the side that matters — a stitch file exists to be sewn — but
  fixing the codec remains Kent's call.

  **The import half is not hypothetical, and it never was mine to introduce.**
  Imported the commissioned becker DSTs — a professional digitizer's own files,
  already in the repo — and EMB-Bot shows them **rotated**: `76.5×46.8 mm` as
  `47×77`, `101.9×62.1` as `62×102`. So a customer who brings a logo they paid
  a digitizer for sees it sideways, hoop-fitted wrong and auto-fit scaled off
  the wrong axis, and that has been true the whole time — independent of any
  change here. **MASTER_SCOPE's stated resolution path was "a sew-out or
  third-party read of a browser-encoded DST"; both directions are now read and
  neither needs a sew-out to settle.** What is left is genuinely a decision, not
  a measurement: fixing import alone breaks the self round-trip, fixing both
  makes every DST EMB-Bot has ever written read rotated until re-exported.
  That is why it is Kent's, and it is now costed rather than merely flagged.
  *(measured 2026-09-07)*

- **When you fix a rule, COUNT ITS READERS FIRST. Three defects in one
  session were the same shape.** Each was one question being answered in more
  than one place, with only one place right:
  1. **Two copies, drifted.** `GARMENT_FABRIC` and the `FABRICS` table exist
     in `src/fabrics.js` and `digitizer_core/fabrics.py`, hand-ported, with
     the Python file's docstring promising they match. A ruling landed in one.
  2. **Three readers, three versions.** "Is this element sewable" was in
     `canAdvance("create")`, absent from the review headline (which just said
     "Ready to stitch"), and a `{:else}` in the recap that assumed text.
  3. **Two callers, one fixed.** `loadPreferredPaletteId()` defaults the
     thread chart. The Download step's shopping list was given the design's
     own brand at 07:00; `ThreadPicker` was not, and was found half an hour
     later showing **"Studio basics" directly above a label reading
     `0134 Smoky`** — offering 56 generic shades to replace a cone chosen
     from 398, so picking one threw the catalog number away.
  **The third is the instructive one because it was MY OWN half-fix**, found
  by driving a screen I had not thought to open rather than by reading. The
  cheap habit that would have caught it: after changing a shared function,
  grep its name and look at every call site, not just the one the bug was
  reported on. `loadPreferredPaletteId` had two; `ThreadPicker` itself has
  **nine** call sites across seven components, which is why the fix is a
  store (`lib/designChart.js`) rather than a prop threaded through all of
  them — a fact that belongs to the project should not be carried by every
  component between it and the reader. *(2026-09-07)*

- **A refresh destroyed the offline user's artwork, and `_hasImage: true`
  was the only thing saved about it.** An `image` element's pixels lived in
  App's `runtime.workImages`, which is deliberately not persisted; the element
  itself carried nine scalar settings and no picture. Measured in a browser:
  **2739 stitches before a refresh, no stitch caption after**, the canvas back
  to "Your embroidery appears here as you add content", and not one word of
  explanation. The sibling `digitized` element had solved this from the start
  by keeping `sourcePng` on the element — same session, same fixture, 2187
  stitches before AND after — so the answer already existed one factory down.
  **Who it hit is the sharp part**: `image` is created only when the digitizer
  service is DOWN (`resolveArtworkType`), a state the Content step explicitly
  supports and advertises ("Artwork will be placed but not auto-digitized").
  The app invited people to work offline and then threw the work away.
  When runtime state is the ONLY home for something a user made, a refresh is
  a delete key. *(measured 2026-09-07; `sourcePng` at WORK_MAX_PX now on the
  element, restored by `lib/imageSource.js` from the load path)*

- **Restore in the load path, not in the panel that edits the thing.** The
  first cut put the rehydrate in `ImagePanel`, which mounts only on the
  Content step with that element selected. The embroidery field is beside
  EVERY step, so a reloaded project showed an empty field until the user
  happened to click Content — and `_hasImage` stayed false meanwhile, so the
  review step would have called a design with real artwork in it empty. It
  measured as "fixed" (the stitches came back) while still reading as lost
  work on the screen the reload lands on. Moving it to `enterProject` and boot
  covers every step at once, and leaves one path instead of two.
  **Its own trap**: Svelte hoists a function declaration but not the `let` it
  closes over, so calling `restoreArtwork(project)` up beside the `project`
  assignment threw *"Cannot access 'rehydrateToken' before initialization"* —
  and a throw in that block renders an EMPTY BODY, which looks like a dead
  server rather than a scripting error. Check `pageerror`, not the network.
  *(2026-09-07 — same session)*

- **A trailing `{:else}` answers a question about the wrong type, and a
  missing field renders as EMPTY rather than as "undefined".** The review
  step's recap branched `image` / `manual` / else-assume-text. Three of the six
  element types `addElement` builds are neither — `digitized`, `design`,
  `shape` — so all three landed on the text rung. `digitized` is the
  commonest path in the app, and on the screen immediately before Download it
  recapped a finished auto-digitized logo as **`Content: Text — ""`** above a
  blank `Font`. Svelte prints a missing property as nothing, so the wrong
  answer read as a plausible *empty* design rather than as a bug — which is
  why it survived; `Text — "undefined"` would have been reported in a day.
  **The suites all passed and always would have**: `wizard-smoke.spec.js`
  asserts the recap on the text and image paths, both of which have their own
  rung, and `quality-report.spec.js` drives the digitized path but only ever
  looked at `.quality`, below it. Two tests over the same screen, and the gap
  was exactly where they met. Cut to `lib/summary.js` with one branch per
  type, and `summary.spec.js` enumerates them from `project.js`'s OWN factory
  ternary, so a seventh type fails a test instead of shipping.
  **Found by breaking it**: adding `.trim()` to that line turned the silent
  wrong answer into a render-time throw, which took out step navigation
  entirely — the failing e2e pointed at a disabled-looking button on the
  Content step, three components away from the cause.
  *(measured 2026-09-07 in a browser; the mutation quotes the shipped string
  verbatim)*

- **The review step said "Ready to stitch" for a design with nothing in it.**
  A brand-new project holds one EMPTY text element, so the headline, the
  lead-in ("Looks good? The live field is your stitch-out.") and the summary
  all rendered over a canvas reading "Your embroidery appears here as you add
  content." `flow.js`'s `canAdvance("create", …)` already computed exactly the
  right predicate and ONLY the Next button consulted it — so the one signal
  the customer got was a disabled button with no reason attached. When a gate
  already exists, the copy above it should read from the same gate rather than
  assume the happy case. *(2026-09-07 — same session; e2e in
  `wizard-smoke.spec.js`, mutation-proved)*

- **A ruling marked "shipped" may have shipped into ONE of the two engines.**
  Corpus law 26 (`edge_lattice` → `edge_run` under a knit fill) is recorded as
  **shipped 2026-08-05**. It landed in `digitizer_core/fabrics.py` and never in
  `src/fabrics.js`, so for a month the browser engine ran an extra crosshatch
  pass under every fill on **left_chest, beanie and sleeve** — the commonest
  placement there is, plus two — worth **+1.4% to +5.7% stitches** against the
  Python engine on the same artwork. Three shipped Studio lanes read that table
  (image mode, manual digitizing, shape presets). Nothing failed: `fabrics.py`'s
  own docstring asserts the two tables are "the same values, deliberately", in
  prose, and **475 engine tests and 936 Studio tests all pass with either
  value** — no test pinned the knit underlay at all. When a status column says
  shipped, ask *shipped where*; a physical table that exists twice needs a test
  that compares the two copies, not a comment saying they match.
  *(found 2026-09-07 by diffing the tables field-for-field while checking
  whether the Studio's garment choice reaches the digitizer at all; both copies
  and both spacing constants now guarded by
  `digitizer/tests/test_fabric_wire.py`)*

- **A pass that can DELETE as well as relabel needs a probe that counts both,
  or it will look innocent.** `dissolve_phantom_blends` folds a label two
  ways: relabel it, or send it to the page. A probe written to find labels
  "whose pixels changed label" sees only the first — a page-dropped label
  keeps its label and leaves through `base_valid` — so it reported 9 tiny
  folds on a fixture where the real answer was 42 labels and 50.3 mm² of
  lettering. That miscount was published as a retraction of a correct
  diagnosis before the second count found it. Count every exit a pass has.
  *(2026-09-06 — scope-history 09-06)*

- **`~base_valid` is not the page.** Stage 2 hands a pass `base_valid`, which
  already has ENCLOSED pixels removed, so its complement covers donut holes,
  letter counters and the inside of a label as well as the real background.
  Any rule that treats that complement as "the background" will tell an
  interior feature it borders the page — and where the page is an endpoint
  that DELETES, that is artwork gone. Take stage 1's own background mask.
  *(2026-09-06 — same entry)*


- **When you ask "would this change the outcome?", compare the DECISION, not
  the score of the thing already chosen.** Twice in one day, on the same
  fixture set. `--yardstick` first: `_thread_match_findings` picks its top row
  on `_score`, so under excess a thread can block on its SECOND-worst raw row
  — 6 of 24 findings change row, and a probe that keeps the raw top and prints
  its excess answers a different question. Then `--masks` made the same
  mistake and shipped a wrong verdict: it compared the two masks on the
  ASSIGNED thread's dE00, found `bridge_bar` agreed to 1.3, and published
  *"not the mask"*. `revalidate_threads` re-snaps on the improvement over the
  best LOADED spool, and there the two masks read **1.8 against 10.3**, across
  a 3.0 gate — opposite answers. The corrected tool prints the floor check,
  the best loaded spool and the gain under each mask, then says whether each
  WOULD re-snap. **The quantity a check reads is the quantity to compare;
  anything else is a proxy that can agree while the decision disagrees.**
  *(2026-09-07 — `tools/spool_remedy.py --masks`, corrected before merge)*

- **Two functions can share an estimator and still score different artwork —
  check the MASK, not the formula.** `stage4_vectorize.revalidate_threads` and
  `preflight._region_color_errors` both take the median of the per-pixel
  CIEDE2000, each docstring says so, and they still disagreed by **52.2 dE00
  on one polygon**. The difference is two operations nobody had lined up:
  preflight erodes the polygon raster one pixel and drops `p.bg_mask`
  (*"to keep anti-alias halo pixels from dragging a flat color toward the
  background"*); `_region_footprint` is a bare `cv2.fillPoly` and does
  neither. On `logo_gaulke_roofing`'s `Se6eddd27` (0.58 mm2 at 16.1 px/mm)
  that is **247 px against 54**, and stage 4's set is BIMODAL — 103 near-black
  plus 65 near-white — so its median makes `3971 Silver` the chart-wide argmin
  at 11.4 while the region's own core is near-black and scores that same
  Silver **63.6**. **The re-snap picks a thread on pixels the grader refuses,
  and the grader then condemns the thread the re-snap picked.** This is the
  named cause of one of the F wall's three excess-surviving blocks. It is also
  the SAME failure `_region_color_errors`' docstring calls this instrument's
  original sin — *"the per-channel median of a bimodal pool is a colour almost
  no pixel carries"* — fixed on preflight's side 2026-08-11 and never
  inherited by stage 4. When two instruments disagree about one region, diff
  their pixel sets before their arithmetic.

  **It is also a SECOND cause of the resnap escape** (MASTER_SCOPE 15): an
  argmin run on halo pixels goes shopping for a spool matching a colour the
  artwork does not contain. On gaulke the shipped engine re-snaps its way to
  `1375 Dark Charcoal` and `3971 Silver` and loads NEITHER once the mask is
  right — region cones 6 -> 3, plan palette 4 -> 2.
  `bind_resnap_all_classes` restricts WHERE the argmin may land; this is WHY
  it goes wrong, and they are not the same fix.

  **FIXED behind `cfg.resnap_mask_matches_grader`, DEFAULT OFF**: 19 of 26
  fixtures byte-identical, -1,715 stitches, -5 blocks, -4 cones, +2 trims,
  `logo_gaulke_roofing` F 4 -> D 46, nothing down anywhere. **And fixing the
  mask does not finish the shape** — worth expecting. `Se6eddd27` goes
  63.6 -> **16.7**, not the 5.0 `1375 Dark Charcoal` would give it: once the
  halo is gone the region falls under the re-snap's own floor AND the cone
  list it could choose from has shrunk, so it keeps stage 2's `4174`.
  `revalidate_small_shapes` is byte-identical on top of this flag for the same
  reason. An earlier draft of its test asserted the shape would CLEAR; it does
  not, and the residual is pinned instead.
  *(2026-09-07 — `tools/spool_remedy.py --masks`;
  `tests/test_resnap_mask_matches_grader.py`, 10)*

- **A measurement cache must record the tree it was measured on, or a table
  will mix two engines and look consistent.** `flip_sheet.py` cached its first
  pass into `build/flip_sheet` before `dissolve_phantom_blends` was fixed; the
  two affected arms were re-measured into `build/flip_sheet_v2`; the published
  sheet then drew four rows from the first directory and two from the second,
  and asserted *"every number below is post-fix"*. It happened to be TRUE —
  all 26 `off` digests match across the two trees, so the flag gate provably
  holds and the four arms that leave the flag off could not have moved — but
  nothing checked, and the claim was an inference presented as a measurement.
  The cheap fix is structural: every row carries `head` now and `report`
  prints a **MIXED TREES** banner rather than comparing silently. If you write
  a tool that caches measurements, stamp the commit into each row.
  *(2026-09-07 — `tests/test_flip_sheet.py`)*

- **"Byte-identical to `off`" does not mean a flag is inert — it means it is
  inert on the geometry the DEFAULT produces.** `satin_patch_junctions` is
  byte-identical to `off` on `logo_script_tires`, so the sheet called it inert
  there. Turn on `dissolve_phantom_blends` as well and it adds **four fill
  runs and three trims** to that same fixture: the halo pass splits the script
  into two more satin strokes (7 → 9), and the patch pass then finds junctions
  between strokes that do not exist without it. Neither flag alone moves the
  fixture off A 100; together they take it to B 88. **A single-flag arm prices
  a flag against one geometry only**, so never generalise "no effect" from it
  — which is the whole reason `flip_sheet.py` has combination arms.
  *(2026-09-07 — `docs/flip-sheet-2026-09-06.md`, the interaction section)*

- **A row in an evidence doc is evidence about the TREE it was measured on,
  and the tree moves.** `yardstick-disagreements` row 7 ("it prefers a design
  that dropped its ink") was a correct measurement, correctly reported, and
  wrong one day later: the engine under it had the `~base_valid` bug, and the
  row was the artifact of the very bug it helped find. Fixing the bug reversed
  its direction — the arms that load real Black now grade HIGHER. **Before
  quoting a measured row at a gate or a decision, re-measure it.** The
  measurement is cheap; the doc is not self-invalidating.
  *(2026-09-07 — yardstick-disagreements row 7, retracted)*


- **A flag that removes a cone cannot be judged on its grade. Check the cone
  list.** `THREAD_MATCH_POOR` grades per thread on that thread's worst patch,
  so deleting a cone deletes the thread that was scoring badly — you cannot
  have a poor thread match on a thread you never loaded. **This rule is what
  found the `~base_valid` bug above**: `logo_gaulke_roofing` (black lettering
  on a white label) graded C 64 under `dissolve_phantom_blends` while loading
  nothing darker than L* 82, and MASTER_SCOPE carried "F 0 → C 64, the
  difference between 'do not sew' and a usable design" for two days about a
  design that had dropped its ink. Machine units do not save you either — the
  same change read "blocks 4→3, trims 30→18", both true.
  **The conclusion drawn NEXT was wrong, and that half is retracted
  (2026-09-07).** From those numbers the record concluded that the metric
  prefers a design that dropped its ink, and shipped it as
  yardstick-disagreements row 7. It was the bug's artifact: post-fix, every
  gaulke arm that loads real `0020 Black` grades HIGHER (F 16) than every arm
  that does not (F 4), and swept over seven arms × 26 fixtures, **ten
  (arm, fixture) pairs remove a cone and not one scores higher.** The rule
  above is sound; **"the metric rewards not sewing the hard part" was never
  measured on a correct engine and should not be repeated.**
  *(measured 2026-09-06, half retracted 2026-09-07 — `docs/flip-sheet-2026-09-06.md`;
  yardstick-disagreements row 7)*


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

- **`git checkout <file>` on an UNCOMMITTED file destroys it, with no
  confirmation and nothing in the reflog.** The reflex is "discard my edits to
  this one file", and it is correct — but only when the edits are the ones you
  meant to discard. Hit 2026-09-08: reaching for it to revert a probe mutation
  wiped a set of derivations made in the same file an hour earlier and not yet
  committed, and the tell was eight failing tests in a component nobody had
  touched. The same reflex came back an hour later on a second file and was
  blocked by the auto-mode permission classifier, which is the only reason it
  cost one incident and not two. **Copy the file to the scratchpad first and
  restore from that copy** — `cp <file> $SCRATCH/<name>.bak`, mutate, test,
  `cp` back. Cheap, reversible, and it works on a file git has never seen.
  Committing before mutating is the other answer, and is better when the state
  is worth keeping. `git stash push <paths>` is safe too (it is recoverable);
  a bare `git checkout` is not. *(2026-09-08)*

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
  silent bespoke value.** Three such names shipped in `app/src/ui/theme.css`; two
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
  **REPRODUCIBLE 2026-09-07** — `tools/spool_remedy.py --yardstick` names those
  same four and no others. It needs NO patch: excess has been reported on every
  route since 2026-09-06, so the confound this entry warns about (forcing
  `_is_photo_class`, which also gates `PHOTO_RESOLUTION_LOW` and the subject
  check) is avoidable entirely. **And the offender set moves with the
  yardstick** — `_thread_match_findings` picks the top row on `_score`, so a
  thread whose worst RAW patch has a close loaded alternative can block on its
  SECOND-worst under excess: 6 of the 24 findings change row. A probe that
  keeps the raw top and prints its excess answers a different question.
  **(2) halo cones, 1 of 7 — RETRACTED 2026-09-07, this category is EMPTY.**
  It read: *"`gaulke_roofing` needs no yardstick change:
  `cfg.dissolve_phantom_blends` alone gives F 0 → C 64, blocks 3 → 0, worst
  ΔE 63.6 → 6.8, −15% stitches."* Every one of those numbers was the flag
  DELETING gaulke's lettering — the `~base_valid`-is-not-the-page bug, fixed in
  #380. **On the fixed tree the flag is byte-identical to `off` on gaulke, on
  BOTH garments**: F 4, raw 4, 2 blocking `THREAD_MATCH_POOR`, worst ΔE **63.6
  unchanged**, same stitch count, same four cones. Blocks 3 → 0 was three
  blocks removed by not sewing the thread that carried them.
  **So the wall decomposes 4 + 0 + 2, and gaulke is the seventh, unexplained.**
  Do not plan against this category. The lead someone should follow instead is
  already in defect 28: gaulke's 63.6 ΔE names `1375`, **a spool the design
  already loads**, with 58.6 of that distance closable by a swap that costs the
  operator nothing — which points at the raw yardstick (category 1), not at
  halo cones. Whether it actually clears under excess scoring is UNMEASURED;
  do not assume it from this note.
  **(3) survives excess too — 3 of 7, not 2 (2026-09-07).** `gaulke_roofing`
  joins this group now that category (2) is empty: 2 raw blocks -> **1** under
  excess, and the survivor is `3971 Silver` at raw 63.6 / **excess 58.6**.
  **ROOT-CAUSED the same day** (`tools/spool_remedy.py --masks`): **the mask
  gap accounts for TWO of the three** — `gaulke` and `bridge_bar` — and
  `screenshot` is the small-shape floor already documented (`S43831dcd`,
  177/114 px, both footprints pick `0015` either way,
  `revalidate_small_shapes` takes it 32.7 -> 1.4). **A first version of this
  entry put `bridge_bar` in "neither"**, because it compared the two masks on
  the ASSIGNED thread's score (19.9 vs 21.3, agreement) — the wrong quantity.
  The gate reads the improvement over the best LOADED spool, and there they
  read **1.8 against 10.3**, on opposite sides of the 3.0 threshold. See the
  gotcha below.
  The other two are also **region colour != the artwork under it**:
  `bridge_bar` and `screenshot_phone_ui` block under every combination, and the screenshot's
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
  design is hundreds of points under water. **The "exception" this used to cite
  is withdrawn (2026-09-07)** — it read that `dissolve_phantom_blends` moves
  `gaulke_roofing` F 0 → C 64 because gaulke grades F **4**, shallow rather
  than floored, so its improvement had somewhere to go. The shallowness is
  real and still measured (F 4, raw 4, on both garments); the move was the
  flag deleting the lettering, and post-fix the flag does not move gaulke at
  all. **Rule: on a floored design the grade is not evidence in
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

  **Two more sweeps the next day, and now the DISCRIMINATOR is visible.**
  Five in all:

  | sweep | raw hits | real |
  |---|---:|---:|
  | doc file PATHS still exist | 24 | **0** |
  | documented TEST COUNTS drifted | 6 | **0** |
  | `extra:` comment fields, comma-parsed | 4 | 2 |
  | `file.ext:NNN` still points at its subject | 8 | **2** |
  | backticked `module.symbol` still defined | 19 | **0** |

  The symbol sweep is the clearest miss: all nineteen "unresolved" were `cfg.*`
  dataclass fields (indented and type-annotated, so a `^name =` pattern misses
  them), fixture filenames, third-party calls (`cv2.fillPoly`, `vi.mock`) and
  attribute access on local variables — **62 of 62 references are live**, and
  the convention of citing a symbol is sound.

  **What separates the one that paid is not effort, it is what the check
  RESOLVES AGAINST.** The line-number sweep found two real stale pointers
  because "does line N contain its subject?" has a single unambiguous ground
  truth you can go and read. The four that found nothing were pattern-matching
  prose, where a legitimate narrative sentence and a stale claim look
  identical. **Budget the resolution step, not the regex** — a sweep whose
  output has to be hand-classified before it can be believed has not saved
  anyone the reading. *(measured 2026-09-07)*

  **A SIXTH sweep the same day inverts the question, and the ruling above
  only half applies.** The Studio names Python warning and finding codes as
  bare string literals — `WARNING_TEXT`'s 28 keys, `FIX_FOR`'s three, eight
  `.code === "..."` switches, and four mirrored constants inside preflight
  holding five more:
  **34 distinct code strings crossing a module boundary by literal, over six
  sites, every one of them live.** By the rule above that is one more
  zero-yield sweep and the check should not be built. It was built anyway
  (`digitizer/tests/test_code_wires.py`, 6), and the distinction is worth
  carrying:

  **A SWEEP is judged on what it finds today. A TRIPWIRE is judged on what
  its failure would cost.** The five above looked for drift that had already
  happened, so a zero means the convention is sound and there is nothing to
  automate. This one guards a rename that has NOT happened — and when it
  does, `describeWarnings` falls back to `String(w.message)` and ships the
  engine's build-status prose to a customer without throwing, logging or
  blanking anything, while a stranded `FIX_FOR` key simply stops offering its
  button. Silent, customer-facing, and indistinguishable from a code that was
  never translated in the first place. The contrast is one module over:
  `stage7_sequence.py` consumes the same codes by IMPORT, and deleting one
  from `warnings_codes.py` stops the package loading with a named ImportError
  before any test runs.

  **The discriminator still decides WHICH tripwires earn their keep, and it is
  the same one** — this resolves against an OBJECT (a set of live wire values
  parsed from both owners) rather than pattern-matching prose, so its verdict
  needs no hand-classification.

  **The path sweep's "0 stale" was a FALSE NEGATIVE, found 2026-09-08 — and it
  lands exactly where the rule above predicts.** Re-swept the same docs and got
  the same cascade (651 raw → 363 → **19** once resolved against the right base
  directories), and 19 is again almost all deliberate. But one was real, and had
  been the whole time: **PRODUCT.md row 7 — the row gating the first dollar —
  cited `src/fonts/milli_marif_bold.LICENSE.txt` as the evidence that per-font
  licence research had been done.** That file was deleted 2026-08-04 *by* that
  research: the font was pulled for having no written confirmation the grant
  covered commercial distribution. The row was offering a pulled font's removed
  sidecar as proof of compliance.

  **Why the hand-pass cleared it.** The rule of thumb was *"a path here is
  either right or cited inside a sentence saying it was deleted"* — and row 7
  does say "All license-flagged fonts were pulled from the build in the
  2026-08-04 audit pass", one sentence later. The filter fired on the
  neighbouring sentence and never asked which claim the path was serving.

  **The entry above stands, and gets sharper: don't build the checker, and
  don't trust the hand-pass either.** The question a path sweep cannot answer is
  the only one that matters — *does the SENTENCE survive the file being gone?*
  "Cited in a deletion note" and "cited as live evidence" are the same string to
  a checker **and** to a reader skimming the paragraph for the word "pulled".
  Where a missing path sits in a row that gates money, read the clause it is in,
  not the paragraph around it. *(measured 2026-09-08)*

  **Two ways this class of test dies, both hit while writing that one.** Both
  are the `test_stitchviz.py` lesson (a first draft matched a `LIGHT_DEG` a
  merge had left behind as dead code and passed for weeks over a live canvas
  lighting from the wrong corner), and neither shows up as anything but green:

  - **A "not in" assertion over a parser that finds nothing passes
    trivially.** The first `_map_keys` sliced the object literal at a nearby
    `\n  };` and returned the right answer for both maps **by luck** — it
    never reached `FIX_FOR`'s nested braces. Fixing the slice is what
    surfaced the nesting, not any test.
  - **A MIRROR must never be allowed to vouch for a consumer.** preflight
    holds private copies of four pipeline codes; admitting them to the
    "live" set would have let a stale copy of a deleted string keep every
    Studio assertion green — a check comparing a string against a second
    copy of itself. Excluded by name, and the exclusion is itself asserted.

  **Every assertion was proved able to fail by mutating the source it reads**
  — six mutations, six reds, tree restored. Do that, or the file is
  decoration. *(measured 2026-09-07)*

- **A number that is the INPUT to a computation, reported as its OUTPUT — and
  the second display that already knew better.** `buildLetteringDesign` and
  `buildQualityDesign` both returned `fitScale`'s target box as the design's
  `widthMM`/`heightMM`. That box is what routing is handed: pull compensation
  and the weight preset then push the satin rails outward, so the thread lands
  outside the number naming it. Swept over 7,470 lettering designs (10 garments
  x 85 shipped fonts x 3 texts x 3 weights), **65.6% sew outside the placement
  box they were just fit to**, by up to 9.6 mm.

  **The tell was on screen the whole time, and it took driving the app to see
  it.** The Studio shows the size twice — the field caption from the design's
  `widthMM`, SizePanel from the stitch bbox — and on the first screen of the
  most common quick start they read `127×13 mm` and `5.05 in` (= 128.3 mm).
  The size field's own `max` was `5.00`, so the browser had it at
  `rangeOverflow: true, valid: false` on a design with nothing wrong with it.
  Nothing was red. No test compared the two numbers, because each was correct
  against the thing it was written against.

  **Three rules that generalise:**

  - **When two displays of one quantity disagree, one is measuring the input.**
    Look for the fit target, the request, the pre-clamp value. The honest
    display is the one derived from the artifact — here, the stitches.
    **Extended 2026-09-08: they need not be the SAME quantity, only linked
    ones** — and that is the harder case, because nothing looks duplicated.
    The review card carried `Colors 4` beside `Thread changes 1`, two rows
    apart. N colour blocks means N−1 changes, so those numbers cannot both be
    right; but they are not the same number, so no eye and no test compared
    them, and the pair shipped. `Colors` was the slider — the REQUEST, exactly
    what this rule says to look for — and `Thread changes` was counted off the
    design's own colour records. **Read a summary card as a system of
    equations, not a list of facts:** any two rows with an arithmetic relation
    are a free consistency check, and the one with no code path to the artifact
    is the one that is lying.
  - **A UI constraint and the value it constrains must measure the same
    thing.** `max` bounded what the user may REQUEST; the field displayed what
    the design SEWS. A request bound policing a sewn readout is a category
    error, and it renders as a broken input on a correct design.
  - **A gate is only as honest as its input.** The hoop CEILING check, which
    gates `DownloadStep`'s oversize-export confirm, ran on the under-reported
    number — 4 of the 7,470 said "fits" where the thread needs the hoop
    rotated. Fixing a check's threshold is worthless while what it reads is
    the wrong quantity.

  **The Python engine had it right the entire time.** `adapter.design_bbox_units`
  has always measured its own stitches ("jump/trim/color mark where the needle
  travels, not where thread lands"). So this was the recurring cross-language
  divergence again — except the browser held the wrong answer, and nothing
  compared them. The two engines use DIFFERENT record sets (JS takes
  stitch+jump+trim to match `preview.js`'s framing, Python sewn-only) and agree
  anyway, because a jump is emitted at the first point of the run it travels to
  and a trim at the previous sewn position — both already sewn points. Measured:
  0 disagreements over 249 designs plus the image path, worst gap 0.000 mm, and
  now pinned by a test so the day it stops holding is the day it shows up.

  **The blast radius was one number.** Every stitch coordinate is unchanged;
  exactly one engine snapshot and one Studio assertion moved, both of which were
  pinning "we report back the width you asked for" (40 → 40.2, 60 → 60.6). The
  e2e guard was proved to fail on the pre-fix engine before being kept.
  *(found by driving the app, measured 2026-09-07)*

- **A launch-checklist item verified against the module that CAN do the thing,
  not against the product that exposes it.** PRODUCT.md item 1 — *"PES hardened
  to byte-verified + JEF export"* — was marked ✅ Done on 2026-08-11 with the
  evidence *"PES/JEF live in `digitizer/digitizer_service/formats.py`"*. True,
  and checkable, and the reason nobody looked again. The Studio's Download step
  offered DST / PES / EXP, so **a Janome owner could not export anything from
  this product** for four weeks while a launch-scope row said the feature
  shipped.

  This is the same shape as the DST entry above (*"the code WAS right and the
  product was not"*) arriving through a different door: there the gate's
  condition was unreachable, here the capability had no control. **The test in
  both cases is the same — can a customer get to it?** A module that can write
  a format, a function that returns the right answer, a flag that defaults
  correctly: none of them is a feature until something on screen reaches it.

  **Two habits that would have caught it, and both are cheap:**

  - **Read the checklist's evidence as a claim about the PRODUCT, not the
    repo.** "Lives in `formats.py`" answers a different question than the row
    asks. A row about export is done when a button downloads the file.
  - **Enumerate the surface, not the capability.** The service advertises nine
    formats on `/health`; the Studio renders three of them. That is one `grep`
    against one `curl`, and it is the whole finding.

  Ship-check for the rest, measured the same day by decoding `/export`'s bytes
  with `pystitch`: VP3 (Husqvarna/Pfaff), XXX (Singer) and PEC all come back
  correct at 80.5×16.6 mm with 1 colour change and 2 threads. **U01 (Barudan)
  does not — ZERO colour changes on a two-colour design**, so a machine would
  sew both blocks in one thread. Adding a format is one line in
  `exporters.js`'s `SERVICE_ONLY_FORMATS` and one button; which machines this
  product supports is a scope call, and PRODUCT.md's is DST/PES/JEF (+EXP).
  *(found by comparing /health's format list against the Download step,
  2026-09-07)*

- **A message the code sets and the template cannot show — and the branch it
  was trapped in was the one that mattered.** `DigitizePanel`'s
  `{#if error}` lived beside the Digitize button, which sits in the `{:else}`
  arm of `{#if !element.sourcePng}`. So the upload error could only render
  once artwork had ALREADY loaded, and a file that fails to decode never sets
  `sourcePng`. Dropping a `.txt` on a fresh panel: `onFile` set
  *"Could not read this image file."*, and the screen did not change.

  The asymmetry is the whole lesson. **The case that stayed silent was the one
  where the customer has nothing on screen and no way to tell a rejected file
  from a broken app; the case that spoke was the one where their artwork is
  still visible and they can see it did not change.** Exactly backwards, and
  invisible to every test in the repo, because the string was correct, the
  handler was correct, and nothing asserted that a user could see it.

  **Check where an error renders relative to the state that produces it.** A
  message about a failed load belongs beside the *upload control*, not beside
  the controls that only exist once a load succeeded. The test that catches it
  has to start from the empty state — the spec for this panel deliberately
  seeded a truthy `sourcePng` "to clear the upload-prompt gate", which is
  exactly the gate the bug was behind.

- **`Math.min(1, MAX / longest)` is right for a raster and wrong for a
  vector, and it was copied three times.** `DigitizePanel`, `ImagePanel` and
  `TraceImportPanel` each held a byte-identical `loadImage` and its own copy
  of that work-size rule — one of them with a comment saying so (*"Identical …
  pattern DigitizePanel/ImagePanel already use"*), which is the repo noticing
  the duplication and keeping it anyway.

  Never scaling up is correct for a photo: a 300 px JPEG has 300 px of detail
  however big the canvas is. An SVG has no pixels at all, and its "natural"
  size is a **browser default** — Chrome gives a `viewBox`-only SVG a 300 px
  width, which is the shape SVGO and most hand-written exports produce. So an
  80 mm design built from a vector logo arrived at **3.1 px/mm** and the
  customer was told *"Enlarging it can't add detail that isn't in the file"* —
  false, and `INPUT_LOW_RESOLUTION` firing on the one format that cannot be
  low-resolution.

  **Measured before and after in the shipped app, same file: 3,445 stitches in
  4 colours with two warnings → 3,424 in 2 colours with none.** The two extra
  colours were anti-alias fringe from the small raster: two spools to buy and
  two machine stops the artwork never called for. That is what a resolution
  defect costs downstream — not blur, thread.

  The fix needs no SVG parsing, because Chrome re-rasterises an SVG at
  whatever destination size `drawImage` is handed. Measured on a 0.25-unit
  stripe in a 200-unit viewBox — thinner than one pixel at the default size —
  the darkest pixel produced: **160 at the natural 300 px, 0 at 1200**, and 0
  for both of the other two approaches (setting `img.width/height` first,
  injecting `width`/`height` into the SVG source). The cheapest of the three
  was already what the panels did; only the size they asked for was wrong.
  *(found by driving the app, 2026-09-07)*

- **A finding that states the problem and stops is half a finding — and the
  lettering path was the one place still doing it.** "This font can’t stitch
  «Р», «у», «с». Try a different font, or different text." is true, and a
  customer cannot act on it: three of the 85 shipped fonts cover Cyrillic,
  three cover Greek, two cover Hebrew, and **none covers Japanese, Korean or
  Arabic**, so for half the cases the advice was to keep looking for something
  that is not there.

  The convention was already settled and applied five times over on the
  digitizing side — `THREAD_MATCH_POOR` names a loaded better spool,
  `COLOR_STOPS_HEAVY` the cheapest merge, `STITCHES_TOO_SHORT` the shapes,
  `TRIM_HEAVY` and `DENSITY_STACKED` the same. **When a rule has been applied
  five times in one capability area, go look for the sixth place it has not
  been.** It is a cheaper search than finding a new rule.

  **Ask about the whole input, not the part that failed.** The obvious
  implementation checks which fonts cover the UNSUPPORTED characters, and it
  is wrong: `hebrew_font_large` holds 29 glyphs and no ASCII, so on "Shalom
  שלום" it covers exactly what failed and nothing that worked. Suggesting it
  moves the dead end one step along. Checking the whole text answers "no font
  in this library can" there, which is the truth.

  **And "nothing can" is a different sentence, not a weaker one.** The first
  cut composed one prefix with one suffix and produced *"This font can’t stitch
  «日», «本» and «語» — No font in this library can stitch those characters —
  try different text."*: two sentences arguing with each other, with the
  current font blamed for something no font can do. One builder that owns the
  whole message, three worded outcomes.
  *(found by typing a Russian name into the default font, 2026-09-07)*

- **`src/fonts/*.json` is a namespace with a rule, and the rule is enforced by
  four tests and the font build.** Every non-`manifest` JSON there is read as a
  font SOURCE — `test/embf-guard.test.js` states the invariant outright
  ("static JSON here ⇒ shipped") and `tools/build-embf.mjs` applies the
  identical filter when deciding what to build. Dropping a `coverage.json` in
  beside them broke four tests instantly and would have made the font build try
  to compile it into a `.embf`.

  The fix was not to widen the filter — that is the invariant's only teeth —
  but to use the escape hatch that already existed: the `manifest` prefix means
  "an artifact ABOUT the fonts, not one of them". `manifest.json` says which
  fonts ship; `manifest-coverage.json` says what each covers. **The guard's
  failure message now names that fix**, because "missing bin for coverage" sent
  the first reader looking for a font that never existed.
  *(2026-09-07)*

- **"Reachable" and "findable" are different questions, and this repo has now
  been bitten by both in one day.** JEF was a capability with no control
  (DOCTRINE above). The basic shapes tool is the mirror image: a control that
  exists, works end to end, and is behind a gesture nothing announces — the
  canvas's right-click menu, Kent's deliberate placement (2026-08-13, *"keep
  them, but as a right-click tool rather than an upload button"*). Two of
  PRODUCT.md's four launch-scope items live there. The Content step offers
  three tiles and no fourth thing to try.

  **The check that catches this is the same one either way: sit where the
  customer sits and count what they can see.** Listing the Content step's
  buttons is one line of `document.querySelectorAll`, and it is what turned
  this up.

  **And the obvious place to say it was the wrong place.** The drag hint reads
  "Drag the design to move it — corners resize", which is exactly the register
  wanted — but `hints.js` gates it on `stitchCount > 0` (condition A8), so it
  appears only once a design exists, i.e. after the question has stopped being
  asked. **When adding a hint, check what gates the hint you are copying**: an
  onboarding line behind a "you already succeeded" condition teaches nothing.
  The empty-canvas message is the one a customer reads while wondering what to
  do.

  Fixing discoverability did not require re-opening the placement ruling: it
  is one sentence, and reverting it is one string.
  *(2026-09-07)*

- **Two numbers on one screen measuring different things, again — and the
  second one was a unit label away.** Defect 34 was the design's width; this is
  the simulator's counter, one screen over. The field caption read "1289
  stitches" and the simulator bar read "1280 / 1280", both visible at once,
  nine apart. Neither was wrong: the simulator animates STRANDS — the segment
  between two consecutive stitches, chain broken at every jump, trim and colour
  change — so N stitches in K runs make N − K strands.

  **The tell is a bare number.** "1280 / 1280" carries no unit, sitting under a
  line that names one. Anything a customer will read as a quantity should say
  what quantity it is, and the moment it does, a mismatch with a neighbouring
  readout becomes visible instead of invisible.

  **Convert for display; do not change what the code runs on.** The animation
  still steps strands, because strands are what paint. Only the label maps back
  to stitches — and it maps to the LAST ORDINAL rather than
  `design.stitchCount`, because a run of a single stitch paints no segment and
  the simulator must never claim to have drawn a stitch it cannot.

  **The mapping walks the same records the renderer does, on purpose.** Two
  walks that "obviously" agree drift the day one of them learns about a new
  record type. The tests drive both from the same fixtures and assert their
  lengths match, which is the property that makes the two arrays index together.
  *(2026-09-07)*

- **Advice that names a lever the default state does not have.** "Size up for
  crisp letters" is the right fix for thin lettering — unless the design is
  already as wide as the garment's placement box, which is what auto-fit
  produces and therefore what every quick start produces. Lettering is fit by
  width, so at that box the cap height is fixed by the character count:
  measured on left_chest's 101.6 mm box with `medium_font`, "WIDE DESIGN TEXT
  HERE" gives a 4.33 mm cap, "SHORTER TEXT" 7.16, "ABC" 30.03 — all at the same
  101.6 mm.

  This is a third variant of the same defect this repo keeps finding, and they
  are worth naming together because they need different fixes:

  - **A capability with no control** (JEF): add the control.
  - **A control with no announcement** (the shapes tool behind a right-click):
    say where it is.
  - **Advice with no lever** (this): name the levers that exist in the state
    the customer is actually in.
  - **A true warning the case it describes never reaches** (the JEF
    hoop-header caveat, found later the same day — its own entry below): put
    it where the customer is, not where the nearest existing dialog is.

  The last two are the easiest to ship and the hardest to notice, because the
  sentence is *correct in general*. The test is not "is this true" but "can the
  person reading it see it, and do it, right now".

  **And derive the state from the REQUEST, not the result.** The obvious check
  — is the sewn width equal to the placement box — reads true for every design
  since defect 34, because the sewn extent sits slightly past the box by
  construction. `sizeMm == null` (auto-fit) is the exact signal.
  *(2026-09-07)*

- **A fallback that turns a missing constant into a plausible number, written
  by me, in the same session that spent all day on exactly this class.**
  `lib/estimate.js` quotes thread metres as `pathMm * (EMB.THREAD_LENGTH_FACTOR
  || 1)`. The factor lives in the engine, which `copy-engine.mjs` syncs into
  `app/public/engine/` on predev and prebuild — so against a stale copy the
  `|| 1` silently quoted the PATH LENGTH as thread: the review read **"1.5 m
  (estimate)" for a design that needs 2.1**, and nothing anywhere was red.

  Caught only because the same probe ran twice and the number moved between
  runs with no code change in between. **A number that changes when nothing
  changed is the loudest signal there is; a number that is merely wrong is
  silent.**

  `|| 1` is the shape to distrust — a default that is a VALID VALUE of the
  thing it defaults for. `?? 1` would be no better. **No factor, no row:** the
  estimate is withheld and everything countable is still counted. The test
  deletes the constant and asserts the row disappears.

- **Two engines, one operator-facing number, and the browser cannot quite get
  there.** `lib/estimate.js` had to quote thread on the same basis the service
  does, or a name and a logo in one project would be priced two ways. The basis
  is path length × `machine.THREAD_LENGTH_FACTOR` (1.35) — hand-ported into the
  JS engine and guarded by `test/digitize.test.js`, the third constant after
  `FILL_ROW_MM` and `SATIN_SPACING_MM` to take that treatment.

  **It still does not agree exactly: 4.95 m against the service's 4.87, 1.6%
  high on the same artwork.** `plan_to_design` emits a run the machine reaches
  WITHOUT travelling as plain consecutive stitches, so the design records carry
  no marker for that run boundary and the walk joins two runs, counting one
  segment the plan does not. **The design has lost information the plan had**,
  and no amount of care on the JS side recovers it.

  So the answer was not to make the numbers match — it was to make sure they
  are never both on screen. The browser figure is shown ONLY where the service
  has said nothing, which is exactly the lane that had no numbers at all. And
  that lane's own designs do not have the problem, because
  `buildLetteringDesign` SEWS its short travel as running stitch: everything
  the walk counts there is thread that really goes down.

  **When two implementations of one number cannot be reconciled, scope them so
  they never answer the same question.** Averaging them, or picking one and
  quoting it everywhere, would have shipped a number that is wrong somewhere.
  *(2026-09-07)*

- **A caveat is only as good as the screen it is on: the JEF hoop header, and
  the dialog that does not open for it.** A JEF file carries a hoop code in its
  header and a Janome reads it before it reads a stitch.
  `pystitch.JefWriter.get_jef_hoop_size` derives that code from the design's own
  bbox, correctly, and then falls off the end of its own ladder:
  `return HOOP_110X110` — the second SMALLEST of the five codes it knows —
  for anything at or over 200 mm in either axis. Read off the bytes `/export`
  actually returns: **199 mm declares 200x200 and fits; 201 mm declares 110x110
  and does not.**

  **The first version of the fix put the caveat inside the hoop-exceeds confirm
  dialog, and that was wrong for a reason worth keeping.** The dialog looked
  like the natural home — it is the one place the app already says "this design
  is too big", and it was already going to open for all four oversize garments.
  But the two conditions are not the same condition. The app's largest hoop is
  200x200 mm and its 6x10 is 160x250, so a **140 x 200 mm design FITS the
  largest hoop** and a 150 x 240 fits the 6x10: `hoopFitNote` returns null,
  no dialog opens, and the file is stamped 110x110 anyway. The caveat would
  have appeared on exactly the designs the customer had already been warned
  about and stayed silent on the ones they had not. **Check the overlap of the
  two conditions before hanging one warning off another's trigger — "it is
  already going to open" is a fact about the dialog, not about the defect.**
  It is now a persistent note beside the JEF button, the same convention the
  DST encoder-provenance note uses.

  **What the note may claim is bounded by gate 1.** That the header says
  110x110 is a byte, measured. What a given Janome *does* with a mismatch is a
  machine behaviour and there is no machine here — so the note says "may refuse
  the file" and stops. Same reason the obvious "fix" was not taken: rewriting
  the byte to the largest code the writer knows (200x200) is still a lie for a
  250 mm design, and the argument for it ("a machine that would accept 110
  accepts 200 too") is a claim about firmware, not about bytes. Recorded here
  as a live option for Kent rather than shipped.

  **The two levers the note names are both verified.** Under 200 mm the header
  is correct (measured, same route). And DST and EXP carry no hoop header at
  all — from grepping pystitch's writers, where exactly two mention a hoop:
  `JefWriter` and `PesWriter`. **PES is deliberately NOT named**, even though
  naming three formats would read better than two: its hoop bytes are a
  constant that never described the design (`0x64, 0x64` unconditionally), and
  whether a Brother acts on them is the same unmeasurable as above. A note that
  fixes "advice with no lever" by inventing a lever is the same defect wearing
  a different hat.

  Pinned by `digitizer/tests/test_jef_hoop_code.py` (10 tests, through the real
  `/export`), including the four fits-a-hoop-anyway pairs — which assert the
  Studio hoop table still takes them, so the day that table changes the test
  says the case stopped being the silent one it was written for, rather than
  quietly passing. If the whole file goes red, pystitch fixed the ladder: drop
  it and the MASTER_SCOPE area 4 note with it. *(2026-09-07)*

- **A bounding box cannot tell a rotation from a mirror, and the word you pick
  decides what fix anyone tries.** EMB-Bot's DST reader disagrees with the
  Tajima standard. That was measured correctly in August — five committed
  professional reference files, 5/5, width and height swapped — and then
  written down as *"an exact axis transposition"*, *"a quarter turn"*, *"arrives
  sideways"*. The Studio's import panel followed the word and told customers:
  *"Use Rotate to stand it up."*

  **It was a mirror.** Measured on the canvas 2026-09-07: an imported logo
  renders with its letters backwards. No rotation repairs that, the app has no
  mirror control, and a customer who followed the advice would have ended up
  with a right-way-up backwards logo and more confidence than before.

  Both facts were available in August. `tools/crossval-stitch-formats.mjs` had
  been reporting `anti-transpose` — a reflection — for the export direction the
  whole time; the prose translated it to "quarter turn" and nobody looked at a
  picture. **The bbox measurement was right and the inference from it was not**,
  and the two are easy to conflate because a swapped bbox is exactly what both
  produce.

  Why it reads as a rotation in one frame and a mirror in another, since this
  will come up again: against pystitch's own coordinates `decodeDST` is an
  exact 90° CCW rotation, rms 0. But the model's +y points UP and a raster
  frame's +y points DOWN, so on screen that rotation composes with the flip
  into a reflection. **Both descriptions are true of different frames, and only
  one of them is the customer's.** Name the transform in the frame the person
  reading it is in.

  The permanent guard is a SIGNED AREA, not a bbox: `test/dstimport.test.js`
  takes three non-collinear points off a pystitch-written fixture and asserts
  the sign flips between the two readers. A bbox check passes against both a
  turn and a mirror; the sign of a triangle does not.

  **And a picture is cheap.** Two `pystitch.write_png` calls settled in a
  minute what a year of correct byte measurements had left ambiguous. When a
  claim is about ORIENTATION, render it.
  *(2026-09-07)*

- **Two bugs that cancel look like one feature, and fixing either one alone
  makes a working path break.** With the transposed reader in place, an
  imported third-party `.dst` re-exported as DST came out byte-exact against
  the source (identity, rms 0) — the reader's error and the writer's error
  annihilated. PES, EXP and JEF, which are all correct, faithfully exported the
  mirrored model and came out mirrored. So the ONE format the repo documents as
  broken was the only one that worked here, and the Download step's advice —
  *"PES and EXP are unaffected — use one of those"* — was exactly backwards for
  this project type.

  Measured through the shipped UI, before and after pointing the import lane at
  a standard-convention reader:

  | | before | after |
  |---|---|---|
  | DST | identity, 0 colour changes | mirrored, 0 colour changes |
  | PES | mirrored | **identity, 3 colour changes** |
  | EXP | mirrored | **identity, 3 colour changes** |
  | JEF | mirrored | **identity, 3 colour changes** |

  Three of four go from broken to exact and the fourth joins the DST bug the
  app already warns about — and DST was never the good option anyway, because
  it loses every colour stop to a standard reader. **Count what the customer
  can actually use, not how many cells changed colour.**

  The reader was NOT changed: `decodeDST` still pairs with `dst.js` and its 12
  round-trip tests are untouched. A second entry point, `decodeDSTStandard`,
  reads the other convention, and the product's three import call sites use it.
  When the codec itself is put right the two collapse into one and the extra
  function is deleted. **When a symmetric pair of errors serves two different
  audiences, split the reader before you touch the writer** — the writer is the
  one with files already in the world behind it.
  *(2026-09-07)*

- **A test that passes against the defect it was written for, caught by
  mutation in the same hour it was written.** The new import e2e asserted the
  canvas agreed with the panel using `page.getByText(/40×10 mm/).first()` —
  which matched the PANEL's own line, twice, and never looked at the canvas.
  Reverting `generate.js` to the old reader left it green. The fix is
  `page.locator("span.stats")`: name the element, not the string.

  **`.first()` on a text match is the shape to distrust in a spec that is
  checking two components agree** — it can only ever find whichever one comes
  first in the DOM. The mutation is what found it, which is the argument for
  running one on every new assertion rather than on the ones that feel risky.
  *(2026-09-07)*

- **"It parsed" is not "it is that format", and a size check is not a
  validation.** `decodeDST`'s only gate was `length >= 512 + 3`. Everything
  after it is a walk over 3-byte groups, and arbitrary bytes group into 3s
  perfectly well — so **any** file over 515 bytes decoded into "a design".

  Measured through the shipped UI 2026-09-07 by feeding the import lane a
  Brother `.pes` — the mistake a customer makes when a design site hands them
  the wrong format: **no error, and a design reading 3736 × 7624 mm with
  10,878 colour blocks.** The panel then rendered a thread picker for every
  one of the 10,878.

  The signal that was there all along is the header. A DST's first 512 bytes
  are CR-terminated `XX:value` fields, and the codec was already scanning them
  — for the label, and only the label. Measured over every DST in the repo
  (five commissioned professional files, one written by pystitch, two by
  EMB-Bot's own encoder — **three unrelated writers**): all twelve standard
  tags present in all eight. Every negative tried — PES, JEF, EXP, SVG, PNG,
  two blocks of random bytes, a JSON project file — scores **zero**, and a
  file hand-built out of sixty `ST:` lines scores one. The floor is set at
  three: far below twelve so a sparse writer is not rejected, far above one so
  a coincidence is not admitted.

  **Two things generalise.** First: when a parser accepts anything, look for
  what it is already reading and discarding — the discriminator is usually
  right there. Second: **measure a discriminator's margin on real files of
  both classes before shipping it.** "Twelve versus zero, over three writers"
  is a reason to trust a floor of three; "it worked on the file I tried" is
  not.

  And the message names the way out — the formats a customer is most likely
  holding, and the fact that a `.dst` download of the same design usually
  exists. "Invalid file" would have been the same dead end this repo keeps
  finding.
  *(2026-09-07)*

- **A colour change is a machine stop, and the app was spending one between
  every pair of elements whatever colour they were.** `combineDesigns` spliced
  `trim + color` at each element boundary unconditionally. So the commonest
  real design there is — a two-line name in one thread — carried a stop it
  could not use. On a single-needle home machine that is a full pause with a
  prompt to rethread, and the colour being asked for is the one already
  loaded. Measured 2026-09-07: two black text elements gave
  `colors: [Color 1 (20,20,20), Color 1 (20,20,20)]`, `colorCount: 2`, one
  colour-change record — and the review's thread list and the PDF worksheet
  each listed the same cone twice.

  Adjacent-only, and the trim STAYS. Merging a black/red/black project down to
  two blocks would mean reordering the sew, which changes what lands on top of
  what — a different question and not a free one. And the needle still has to
  travel between two elements without dragging thread across the garment, so
  removing the stop is not removing the cut.

  **Compare the thread, not the label.** Every lettering block is named
  "Color 1" and the import builder numbers its own per element, so two entries
  that sew identically routinely carry different names. `name` is display
  text; r/g/b is the thread.

  Two of `generate.spec.js`'s tests were pinning the old count incidentally —
  one asserted `colorCount === 2` on two default-black elements while its real
  subject was per-element bboxes, and one was called "…into one multi-color
  design" while giving both elements the same default black. **A test that
  gets the right number for the wrong reason still goes green when the reason
  changes**; the second one's premise was made real rather than its
  expectation lowered. *(2026-09-07)*

- **Everything is in localStorage, and a failed write said nothing.**
  `saveProject` has always returned `false` when the write fails;
  `App.persist()` called it and dropped the answer on the floor. There is no
  server, so a failed write is silent data loss — and the work stays on screen
  looking saved, which is worse than an error.

  Measured in the shipped app with the origin's store filled to the byte. Its
  real quota, read by the app rather than assumed: **5,241,856 characters**.
  Upload a logo → it digitizes, the panel reads *"2,253 stitches · 81×16 mm ·
  2 colors"* and the canvas caption 3,818 stitches; the stored record is **842
  characters**, the element saved WITHOUT its baked result; reload → back on
  the quick-start screen, caption 1,565 stitches. The logo is gone, and
  nothing was said at any point. One digitized project measures **~186,600
  characters**, so the store holds about **28** of them.

  **Getting there took four attempts, and the first three "passed" wrongly.**
  Replacing an existing key with a same-or-smaller value succeeds at quota —
  the browser accounts for the replacement — so a `"BEFORE"` → `"AFTER"` edit
  persists with zero bytes free, and so does a moderately longer one. Only a
  write that grows the record past the free space fails. **A quota test that
  edits in place is testing nothing**; it has to grow the record.

  One of those attempts also reported *"the app says something about storage:
  YES"* — from a regex matching the word "full" inside the thin-lettering
  finding's *"already the full width of the placement"*. **A loose regex over
  `document.body.innerText` will find your keyword in someone else's
  sentence.**

  The banner names controls that exist on that screen: My designs holds both
  the export and the delete. And it reports the LAST save rather than latching:
  free space, touch the design, it goes.

  **`saveProject` returns false for two different things** — a failed write and
  an id that is no longer in the registry (the A2/A10 no-op contract, e.g. a
  project deleted out from under an in-flight edit). Only the first is about
  space. Raising a "delete some designs" banner on the second would send the
  customer to fix something unrelated, so the check is `!ok && the id is still
  registered`. **A boolean that means two things needs the caller to
  disambiguate before it can be shown to anyone.** *(2026-09-07)*

- **One design, three encoders, three different sew-outs — because each
  invented its own answer to "this stitch is too long".** A DST record carries
  ±121 units per axis, an EXP record ±127, a PEC record ±2047. All three
  encoders split an oversized move into intermediate records; only the choice
  of WHAT those intermediates are differed, and nobody had compared them.

  Measured 2026-09-07 on a real `manga_impact` "AB" monogram at Full Back
  (304.9 × 146.2 mm, 5,830 stitches), each file decoded with pystitch:

  | | stitches | jumps | longest sewn |
  |---|---|---|---|
  | `.dst` | 5,830 | **3,769** | 16.7 mm |
  | `.exp` | 9,426 | 8 | 18.0 mm |
  | `.pes` | 5,830 | 3 | **51.1 mm** |

  DST turned the thread into **travel** — 3,769 needle-up moves where the
  design said to sew. EXP split into stitches. PES emitted a 51 mm stitch no
  machine can make. `dst.js` now matches `exp.js`: 9,591 stitches, 8 jumps.

  **The chain rule is the part that is easy to get wrong, and I did first.**
  "A stitch splits into stitches" draws a line from the origin across the
  garment, because the move to the FIRST stitch of a run is travel — there is
  nothing to sew between where the needle was and where the design begins. It
  splits as stitches only when the move CONTINUES a sewn run: this record is a
  stitch AND the last emitted one was. A trim, a colour change and the start of
  the file all cut the chain. `test/dstimport.test.js`'s off-origin-centering
  fixture caught the naive version on the first run — **the old unconditional
  "jump" was right for that one case by accident**, which is why nothing had
  ever failed.

  **The safety property is a measurement, not an argument.** The DST of all 85
  shipped fonts at left-chest size hashes
  `e24e181fc8dd89aae12221fe21ab889197a501d0dd3ec59291f8e5d1c591dc9f` both
  before and after: not one of them contains an over-length segment, so the
  split fires only on designs that were already unsewable. **When a change
  touches an encoder, hash the corpus rather than reasoning about blast
  radius.**

  **What is NOT fixed, and is Kent's.** The engine emits those segments in the
  first place. Measured across the 85 shipped fonts at three texts: **18 fonts**
  produce stitches over one DST record, worst **32.8 mm**. The quick starts are
  clean (`YOUR NAME` on a hat: 0 of 2,346; `Your Name`: 0 of 958; `Yours`: 0 of
  1,792) — it starts when letters get big: a **single-letter monogram at
  left-chest size gives 278 of 1,607**, and a two-letter monogram on a Full
  Back gives **1,933 of 5,828, worst 44.9 mm**. A 17.9 mm satin crossing is
  unsewable however it is encoded, and what to do about it — split satin,
  route wide columns to fill, cap the width — is a look-and-fabric decision
  with a sew-out behind it, not an encoder one. *(2026-09-07)*

- **A deferred decision priced on the wrong lane stays deferred for the wrong
  reason.** `encodeDST` does not stop at the terminal `{type:"end"}` sentinel
  the way `exp.js` and `pes.js` both do — one line, `if (st.type === "end")
  break;` — so it writes the sentinel as a real stitch. The 2026-08-04 verdict
  looked at it, called it *"one extra phantom stitch"*, and parked it with the
  axis bug.

  That price is right for LETTERING, where the sentinel sits on the last stitch
  and the extra record is zero-delta — and where `buildLetteringDesign` appends
  none at all. It is wrong for the lane most customers use.
  `buildImportedDesign` puts the sentinel at the **element's offset**, so
  measured 2026-09-07 on a real 95.7 × 58.3 mm logo the DST ends with a stitch
  **0.07 mm from the design's centre and 46.4 mm from the previous one** — a
  stray needle penetration in the middle of the design, with 46 mm of travel to
  reach it. PES and EXP of that same design end where the design ends: 11,274
  stitches against DST's 11,275.

  **The harness had been printing it the whole time.**
  `test/crossval-stitch-formats.test.js`'s DST control reported `decoded 16 /
  expected 15` from the day it was written; the EXP and PES tests assert their
  counts and the DST one never did, because the count was "known bad" and
  nobody wrote down HOW bad. It is asserted now.

  **When you defer something, price it on the lane it actually ships to.** A
  defect measured on the quiet path and parked reads as cosmetic forever.
  Still Kent's — the DST codec is (CLAUDE.md footgun 1) — but it is a one-line
  change now costed against a real logo instead of a fixture. *(2026-09-07)*

## Advice that names a gesture the device does not have (2026-09-07)

The session's recurring defect gained a fifth shape. The first four were a
capability with no control (JEF), a control with no announcement (the shapes
behind right-click), advice with no lever ("size up" at the cap), and a true
warning the case it describes never reaches (the JEF caveat on a dialog that
does not open). The fifth: **advice naming a gesture the device cannot
perform.**

Not a dead end being described — a dead end being *recommended*, by a product
that already knows better. `(any-pointer: fine)` was false on the phone the
whole time.

The check to run on any instruction the product gives: not just "is this
true" and "is the lever reachable", but **"can the person reading this
actually do the thing it names, on the machine they are holding".**

`any-pointer` and not `pointer`, whenever this comes up again. A laptop with
a touchscreen reports `pointer: coarse` when touch is the primary input while
still having a mouse plugged in, and that customer can right-click perfectly
well. The question is whether ANY fine pointer exists.

## A capability read too late is the same as a capability not read (2026-09-07)

Reading a `matchMedia` in `onMount` and letting `paint()` consume it looks
correct and is not: **the first `paint()` runs before onMount's callbacks
do.** A phone would have shown the desktop sentence on first paint and kept
it forever, because nothing repaints an empty canvas.

Mutation-proved rather than reasoned about: moving the read from the
declaration into onMount reddens the phone assertion on its own, with the
rest of the change untouched. Read at declaration; use onMount only for the
listener.

## Two documents about one design must not disagree (2026-09-07)

Three separate defects landed the same day from one root: a fact the app
computes and displays on screen, missing from the document that leaves the
app.

- the worksheet printed the size and the stitch count and dropped the trims
  and the thread metres — two of the four numbers `estimate.js` itself calls
  "the four facts an operator needs before loading a machine";
- the worksheet printed "1375 Dark Charcoal" with no chart, while the screen
  said "Chart: Isacord Polyester 40" one panel away, and all 68 charts number
  independently;
- (this morning) the DST caveat that named a fix rotation cannot perform.

**The screen stays at the desk. The sheet goes to the machine.** Anything the
customer needs while standing at the machine has to be ON the artifact, not
one panel back in an app they closed.

The shape of the fix matters too: compute the fact ONCE and pass it, never
re-derive it at the second site. `exporters.js` calls `sewFacts` and hands
the result to the sheet; `dlWorksheet` takes the codes AND the chart name off
one `loadPalette` object. Re-deriving is how one design starts having two
thread numbers, or one chart's codes under another chart's heading.

## Four working machine formats have no button (2026-09-07 — Kent's call)

`/health` advertises `pec`, `vp3`, `xxx` and `u01` alongside the five the
Studio exposes. Exported a real two-colour design through `/export` in all
nine and decoded each with pystitch: every one carries the same 99 stitches
at 80.0 × 24.0 mm, and `vp3`, `xxx` and `pec` carry the 2-thread colour table
(`dst`, `exp` and `u01` carry none, which is the format, not a fault).

**VP3 is Husqvarna Viking / Pfaff. XXX is Singer.** Two major consumer brands
whose owners cannot use this product today, against a capability that is
already built, already answering, and verified above.

Not shipped, deliberately: this is the same shape as the JEF gap closed the
same morning, but that one was a doc-vs-reality gap — PRODUCT.md item 1
claimed JEF was done while no button existed. Here PRODUCT.md names PES and
JEF and says nothing about the other four, so exposing them is scope, and
scope is Kent's.

Related and also his: PRODUCT.md's launch posture reads "Desktop-only, stated
on the site" and **nothing in the app states it** — every hit for "desktop"
under `app/src/` is a code comment. The lettering lane meanwhile works on a
phone: 1,223 stitches at 102×19 mm, driven with taps and no mouse events. So
the posture is either unstated or untrue, and which one to fix is a product
call with revenue behind it.

## The invisible character: ask what the customer's KEYBOARD types (2026-09-07)

Every defect in this session's family was found by asking what the app says.
The apostrophe one needed a different question: **what does the customer's
device actually produce, as opposed to what they think they typed.**

Phones, Word, Notes and every paste buffer substitute U+2019 for an
apostrophe silently. 26 of 85 shipped fonts had no glyph for it, so the
company's own name sewed as "Fritschs Stitches" — and the note explaining it
named a character indistinguishable from the one they typed, inside
quotation marks made of the same mark, then advised abandoning the font.

That is the sharpest form of the family yet: **a true message about a
difference the customer cannot see, offering a fix that is not the fix.**

The general rule this leaves behind: when text comes from a human, the bytes
are not what they typed. Check the substituted forms — smart quotes, dashes,
non-breaking spaces, the modifier apostrophe — before concluding a font or a
parser is at fault.

**And keep the fold narrow.** NFKD was the tempting answer and is wrong here:
it folds ligatures, fractions AND accented letters, and an accented letter is
a different letter to someone whose name carries it. Only marks whose ASCII
twin is the same mark belong in the map. Measured the same day: accented
names are covered by 33–73 of the 85 fonts and the existing "these fonts can"
message is already good advice there — nothing to fix, and folding would
have broken it.

## Fire a fallback only where the real thing is absent (2026-09-07)

The typographic fold fires ONLY when the font has no glyph for the fancy
form. A font that owns the nicer glyph keeps using it, so no design that
worked before changes — proved, not argued: all 85 fonts laid out with text
free of typographic punctuation hash `d15975c22fbf1d7b…4ad4a230` with the
fold in and with it stubbed out.

The eager version — fold first, then look — is the mutation that reddens the
never-downgrade guards, and it is the version that would have been written
without thinking about it.

## Run-count comparisons prove nothing about glyphs (2026-09-07)

Two of my own assertions passed against the defect they were written for, for
the same reason both times: **two DIFFERENT glyphs routed at one spacing can
land on the same NUMBER of points.** `alchemy`'s straight and curly
apostrophes do exactly that. Compare the full geometry.

That is the second and third time this session a new test passed against its
own subject (the first was an e2e locator matching a panel line instead of
the canvas). Mutation-proving every new assertion is what caught all three —
it is not optional here.

## Rank the fix by severity, not by which branch was written last (2026-09-07)

`letteringNote`'s most severe verdict — the lettering cannot be sewn at all —
was the only one naming no fix, while the milder branch two lines below named
two. Measured: 74 characters at the default left chest gives 1.3 mm letters
against a 4 mm floor and got a bare diagnosis; 18 characters gives 6 mm and
got "already the full width of the placement, so fewer characters or a bigger
placement is what makes them crisper".

The comment justifying it had hardened into doctrine — *"a cap under the
floor already names a height, not an action"* — and a test pinned the string
so the gap looked deliberate. Both were the defect.

**When auditing a family of messages, sort them by how bad the situation is
and check that help does not decrease as severity rises.**

And name the levers only after measuring them: 3 lines 4.8 mm, 6 lines
6.3 mm, 18 characters 6.7 mm, a full-back placement 4.0 mm — all clear the
floor; the same sentence trimmed to 40 characters gives 3.1 mm and does not,
which is why "fewer characters" is named second and line breaks lead.

## A one-way `value={}` stops telling the truth after the user types (2026-09-07)

Svelte only touches the DOM when the bound expression's VALUE changes. Two
identical outcomes in a row therefore leave whatever the customer typed
sitting in a field whose job is to report state.

Measured in SizePanel on Left Chest (101.6 mm placement box), asking in mm:
100 honoured; 105 clamped and the field corrected itself to 102; 110, 115,
120, 125, 127, 130, 150 and 200 all clamped to 102 with the field still
showing what was typed. `checkValidity()` true throughout, no message
anywhere.

The trap is that the FIRST out-of-range entry corrects, so the behaviour
looks right when you try it once. It is the second one that lies.

**Where a control both accepts input and reports state, test it TWICE with
values that produce the same outcome.** One is not a test.

The residual half is recorded rather than fixed: after any edit, a later
reactive change also fails to reach the field (type 90, engine returns its
pull-compensated 90.2, field keeps 90). ~0.2 mm, and the number shown is the
one just typed. An effect re-asserting the DOM on every change was tried and
did not measurably help, so it was reverted rather than shipped
undemonstrated — and the source comment that claimed the field "always"
shows the sewn width was corrected, because it no longer did.

**Confirmed at a SECOND site the same day, and the obvious fix has its own
trap.** The topbar's project-name field is the same `value={projectName}`
shape. Clearing it and tabbing away left the topbar blank while the drawer
one panel over still read "Untitled design" and the export still wrote
`untitled-design.embproj`; typing only spaces did the same. Both normalise
back to the value already rendered, so Svelte left the DOM alone.

The fix is NOT "write the corrected value into the field". Doing that
immediately after normalising reproduced this very defect one layer up: on a
design auto-named HELLO, clearing the field wrote "Untitled design" into the
DOM, a later step in the same handler took the name back to "HELLO" — the
value Svelte had last rendered — and the field then sat there reading
"Untitled design" over a design called HELLO. **A resync must be the LAST
write in the handler, and must read the name that actually survived rather
than the intermediate one the handler computed first.**

## Check the engine before blaming it, and the probe before blaming either (2026-09-07)

The size investigation started from a table showing 60, 80, 100 and 120 mm
requests all sewing 102. Three things were wrong with that reading and none
of them was the app:

1. **The probe reused a stale locator** across a navigation, so only the
   first row's request ever landed. A fresh page per case gave 40, 60, 80 and
   100 honoured exactly.
2. **The "ceiling" was the garment.** left_chest is 4 x 4 in = 101.6 mm, so
   102 was the placement box doing its job — not a bug, and not the hoop.
3. **The engine was innocent.** `buildLetteringDesign` called directly
   honoured 105, 110, 120 and 127 and clamped only above the box.

Only after all three did the real defect show up, and it was two layers away
from where the first table pointed. Two more probe errors the same afternoon:
`/red|crimson|scarlet/i` matched the **Redo** button, and the thread picker's
swatches carry their colour in `aria-label` with EMPTY text content, so
`filter({ hasText })` found nothing.

**Isolate the layer before writing anything down.** A measurement that
crosses the UI, the Studio and the engine at once attributes the fault to
whichever one you were already suspicious of.

## The one failure a customer can fix is the one to word carefully (2026-09-07)

A dead connection made the app say **"Failed to fetch"** — `fetch`'s own
TypeError message, rendered verbatim — and nothing else. No cause, no action,
no retry control. Measured by aborting the font requests in a real browser:
the app does not crash, the page is not blank, there are zero console errors,
and those three words are the entire communication.

Same shape as the digitize panel that printed server paths and worker STDERR,
but worse placed: a network failure is the ONE thing a customer can actually
resolve, and it got the least usable message in the product.

**Two rules from it.**

Name the lever only after checking it works. "Try again" is honest here
because `fontLoader` clears its cached promise on failure on purpose, so any
edit re-runs the load — restored the network, typed one more character, design
back at 1,336 stitches with no reload. Had the loader cached the rejection, the
only honest advice would have been "reload".

And classify at the source, not at the surface. `fontLoader` marks the
transport case; the component picks the wording. Matching on browser message
text would have been fragile (Chrome "Failed to fetch", Firefox
"NetworkError…", Safari "Load failed") and would have wrongly told a customer
hitting a 404 — a bad deploy — to check their connection.

## A stubbed global proves nothing if the code takes the other branch (2026-09-07)

Three unit tests for the fetch classification stubbed `globalThis.fetch` and
all three passed **against the real 85-font manifest read off the filesystem**:
`fontLoader.readBytes` branches on `IS_NODE` and never calls fetch under
vitest. The assertions were about a code path the environment cannot reach.

Fourth time this session a new test passed against its own subject. The
others were a locator matching the wrong element, and twice a run-count
comparison between different glyphs. **Every one was caught by mutation, and
none by reading the test.**

Where the fix only exists in a browser, test it in a browser.

## Where the index IS the data, a swallowed write is a lie (2026-09-07)

`projects.js` keeps a project's NAME and its very membership of the registry
in one localStorage key, `embstudio:index` — there is no second copy in the
project record to fall back on. `renameProject` and `deleteProject` both
ended `writeIndex(idx); return true;`, and `writeIndex` catches its own
quota failure and returns a boolean. So on a full or blocked store both
reported success for a write that never landed: the topbar and the drawer
repainted with the new name, and the old one was back on the next reload
with nothing said.

Found by a storage-failure test written for a NEW function of the same
shape — the sibling-pattern sweep finding the two shipped cases, not the one
being added.

Two rules came out of it, and they pull in different directions, which is
the point:

- **Propagate the failure where the index IS the data** (rename, delete,
  auto-name). The customer's change did not happen.
- **Do NOT propagate it where the index is only metadata.** `saveProject`
  writes the design to its own record first and only then bumps `updatedAt`;
  a record that fit while the index rewrite did not is a SAVED design with a
  stale sort key, and raising "your changes aren't being saved" over it would
  be its own lie. Same file, opposite answer, and the difference is which
  key holds the thing the customer would lose.

`deleteProject` also had its writes in the wrong order — it removed the
record and then wrote the index. A `removeItem` is never quota-blocked, so a
failed index write left a row in the drawer whose design was already gone:
unopenable, and reported as deleted. Index first, record second, which is the
ordering `migrateLegacy` in the same file already documents as
non-negotiable (A1). **When one of two writes cannot fail, do it second.**

## Behaviour hung off a shared write path needs a sweep for the paths that skip it (2026-09-07)

Auto-naming was hung off `App.persist()`, which every edit routes through —
except one. `applyHistorySnapshot()` called `saveProject` directly, so undo and
redo changed `project` without any of persist's tail. Measured within the hour
of shipping it: type HELLO, wait past the 500 ms coalesce window, type GOODBYE,
undo — the design read HELLO while the topbar, the drawer and the stored index
all still read GOODBYE. A brand-new instance of the two-surfaces-disagree
family, created by the change that was fixing that family elsewhere.

The same call site was also swallowing `saveProject`'s return, so an undo on a
full store was silently lost — a third site of the same defect as
`renameProject` and `deleteProject`, and it was not found by the sibling sweep
that found those two, because it is a *caller* of the write rather than another
write.

The fix was to route it through `persist(false)` — the `false` skips the
history record, which is the only reason it had been given its own path in the
first place.

**When you add behaviour to a shared write path, grep for every assignment to
the state that path is supposed to own, not just for calls to the path.** The
bypass will be the one place with a good local reason to be different, and that
reason usually only justifies skipping ONE part of what the path does.

## Test the artifact you ship, not the dev server that stands in for it (2026-09-07)

Every test in this repo — unit, component, e2e, and every hand-drive in this
session — runs against `vite dev`. Nothing had ever exercised `npm run build`
output, and the two are not the same program.

`vite.config.js` sets `base: "./"`. That setting exists for exactly one
purpose: so the bundle works wherever it is served from, and Vite honours it
for everything it owns (`index.html` references `./assets/…`). Five
hand-written asset paths did not: `"/fonts/" + rel` in fontLoader, two
`"/fonts/previews/"` thumbnails, and credits' `binHref` and `licenseHref`.
The config and the code disagreed about a deployment fact, and no test could
see it because the dev server is always at the domain root, where both forms
resolve identically.

Measured on a real build, served two ways:

    domain root   1,356 stitches · 0 failed requests · 0 console errors
    /studio/      no stitches    · 7x 404 /fonts/manifest.json

The customer is not left in silence — the app shows "Font fetch failed:
manifest.json (404)" — but that is a developer's sentence, and it is the whole
lettering lane that is gone.

Two things worth keeping beyond the fix:

- **A `base` setting is a claim, and a claim in config is as testable as one in
  prose.** `./` promised path-independence the code did not deliver, for as
  long as both have existed.
- **`file://` is not the fallback you think it is.** Opening `dist/index.html`
  directly is blocked by CORS for ES modules — a blank page, no app at all. So
  `base: "./"` buys nothing there either; the only deployments that exist are
  "served at a root" and "served under a path".

The guard is source-level (`app/src/lib/assetPaths.spec.js`), because the bug
was one call site not following a rule the others did. The behavioural version
needs a built bundle on a static server, which is what the measurement above
did by hand.

## Look at the artifact. Bytes and extracted text cannot see a page (2026-09-07)

The printed worksheet is the one thing EMB-Bot makes that physically leaves the
screen and goes to a machine. Nobody had ever looked at one. Rendering a real
sheet to an image showed two things at once:

- the single thread row on a ONE-colour design was drawn at y = 11.09 on an
  11.00 in page — off the paper, so the operator's colour sequence was simply
  not on the sheet;
- page two was entirely blank.

Both came from one line: the page-break check ran AFTER drawing each row
instead of before it, which draws a row that does not fit and then adds a page
for content already drawn.

**Three tiers of test passed throughout.** `pdfsheet.spec.js` recorded the
right calls in the right order; `pdfsheet.realpdf.spec.js` built a real PDF and
checked byte size, page objects, and the Pages tree's declared count;
`worksheet-numbers.spec.js` extracted the text and matched it against the
screen. None could see the defect, because **a string is in the content stream
whether it lands on the paper or past its edge.** A recorder that logs
`text(str, x, y)` without which PAGE it landed on cannot answer the question at
all.

`git log` also shows the previous fix that added the trims/thread/chart lines —
mine, earlier the same day — pushed the row from 10.53 to 11.09. Adding a line
to a layout with no fit check is how a latent margin becomes a missing row.

### The worse half: a defect that was noticed and then asserted

The blank second page was already known. `pdfsheet.spec.js` asserted
`pageCount === 2` under this comment:

> "2-color worksheet already spills onto a (mostly blank) second page.
> Confirmed by hand-tracing pdfsheet.js's cursorY math; not something this test
> suite should silently paper over, so it's asserted explicitly rather than
> assumed to be 1."

Someone found it, traced the arithmetic, and refused to paper over it — all
correct instincts. But the artifact they produced was an **assertion**, and an
assertion says the behaviour is right. The test was even named
"correctly-paginated". After that, nobody had a reason to look.

**Noticing a defect and pinning it in a test are not the same act.** If a test
must encode current-but-wrong behaviour, it has to be marked as such — an
xfail, a TODO, a line on the defect list — never a plain assertion, and never
under a name that calls it correct.

## A hand-picked fixture set can straddle the only value that fails (2026-09-07)

The first guard written for the pagination fix swept colour counts
`{1, 2, 8, 40}` and **passed against the very bug it was written for.**

With the render at 5.5 in, the break-after-the-row defect emits a blank
trailing page at exactly **n = 7** — the one count where the final row is also
the row that crosses the margin. The sample straddled it: 2 below, 8 above.

The boundary is not a property of the bug, it is a property of everything
stacked above the list — image height, how many stat lines, whether a chart
label is present. **It moves whenever any of those change**, so no fixture set
chosen by hand stays on top of it.

`Array.from({length: 45}, (_, i) => i + 1)` costs milliseconds here and cannot
straddle anything. **Where the input is a small integer and the run is cheap,
sweep the range instead of guessing which values matter.**

Fifth time this session a new test passed against its own subject, and again it
was mutation that found it, not reading.

## Correction — the `cfg.is_photographic` reachability entry described a world that had moved (2026-09-02/09-07)

Moved verbatim from MASTER_SCOPE's decision queue 2026-09-07 under the
800-line budget. It is a correction, and the skill's rule is that corrections
are kept visible rather than tidied away — so it lives here, where nothing
goes stale, instead of in a queue of things still open.

11. **RESOLVED 2026-09-02 (Kent's call) — the control that helps IS reachable,
   and this entry described the world before that.** It said
   `cfg.is_photographic` "appears **nowhere** in `app/src` (grep, 0 hits)" and
   that the reading row's "It's a photo" correction sent the harsher
   `forced_class="photo_subject"` instead. Both halves moved that day and the
   entry did not: `isPhoto` now sends `is_photographic=true`
   (`digitizer.js:180`; **14** hits in `app/src`), and `forced_class` stays
   reachable only for the OPPOSITE correction — flat art on a misrouted photo.
   Current state and its numbers are defect 15's "UI HALF FIXED" note; the
   08-28 measurement table this entry led with, **26 stops / 0.591 coverage**
   included, is in scope-history 08-28 and is superseded — the forced route
   measures **17** today. Still open is DETECTION, which is defect 15's.
   Both source files had already flagged this staleness in their own comments.
   *(confirmed 2026-09-07 — grep; `digitizer.js`, `DigitizePanel.svelte`)*

## A sew-out settles a physical question. A file format is not one (2026-09-08)

CLAUDE.md's footgun 1, `docs/dst-axis-verdict-2026-07-31.md`, MASTER_SCOPE and
the `dst-codec-axis-discrepancy` memory all said the DST axis fix was gated on
a sew-out and was Kent's call. It sat there for six weeks. **It never needed
one, and a sew-out could not have answered it any faster than what did:**

1. `pystitch.DstWriter.encode_record` — the reference implementation, already
   installed in `digitizer/.venv` — read directly and compared byte for byte.
   With the two weight tables swapped, ours came out **10/10 identical**.
2. `tools/crossval-stitch-formats.mjs`, which already existed and already had
   a word for the answer: `identity`, the same verdict PES and EXP get.
3. A picture: `TEXT=FRITSCH node tools/run-lettering.mjs` → pystitch → PIL.
   The old bytes draw a vertical column of REVERSED letters; the new ones draw
   FRITSCH upright at the design's own 127.2 × 22.6 mm.

**The test to apply.** A sew-out answers *will this thread, at this density, on
this fabric, hold* — questions about the physical world, where the machine is
the only authority. Which nibble carries X is a question about a documented
format with a reference implementation on disk and five sources already in
agreement. Before filing anything behind ROADMAP gate 1, ask which kind it is;
if every source you would consult owns no machine, the gate does not apply.

**The second half, which cost as much: three independent defects were bundled
under one reserved decision.** The colour-change byte (`0x43` vs `0xC3`, so a
standard reader saw a sequin toggle and zero colour stops) and the
`{type:"end"}` sentinel written as a real stitch (a stray needle penetration,
plus a header bounding box a machine reads for hoop fit) were BOTH recorded as
"the DST codec is Kent's". Neither was the axis. Neither moved any geometry.
Both were sitting in the 2026-07-31 verdict's own "bonus finding" the whole
time. **When a reserved call is written down, write down its SCOPE with it** —
footgun 1's stated reason was "it re-orients every DST EMB-Bot has written",
which was never true of either of those two, and nobody re-read the reason.
*(2026-09-08 — #412, #414 and the follow-ups; memory `dst-codec-axis-discrepancy`)*


## A median width along a skeleton is not "thin" (2026-09-08)

`tools/thin_strokes.py` shipped in #425 calling a connected component a thin
stroke when the MEDIAN of the distance transform along its skeleton was
under the detail floor. It printed plausible recalls for two PRs. Then the
photo lane's population finder, built on the same test, read 96.6% of
Fremont's foreground as thin ink — and the biggest "stroke" was the white
GROUND: one component of 1.54 million pixels whose skeleton threads the gaps
between the letters, median full width 1.32 mm, 90th percentile 3.77,
maximum 7.41, "length" 1,758 mm. Sewn, because it is the ground; recalled,
because sewn; and so every design-level recall on Fremont in #425 and #426
was inflated (forced flat 86.1 → 97.3% was really 61.2 → 92.7%). The
per-component counts and the sub-1.0 mm bands were never touched by it.

**The rule.** A structure is thin only if it is thin ALONG ITS WHOLE
SKELETON: test a high percentile of the width (the 90th — a maximum refuses
real strokes at serifs and junctions, where the transform swells for a few
pixels; Fremont's letters read p90 1.04–1.05 against medians 1.03–1.04),
never the median alone. A lettered design's ground, a panel pierced by
holes, a photograph's shadow web all pass a median test. Pin it with a
fixture that has narrow bridges and a wide rim (`tests/test_thin_strokes.py`,
the pierced panel).

**The second half.** An instrument and the engine feature it measures must
share ONE definition of the thing measured, in one place
(`digitizer_core/thin_ink.iter_thin_components`), or the day the feature is
built the two will disagree and nobody will know which one to believe. The
engine caught the instrument here only because they were written apart.
*(2026-09-08 — #427; scope-history's retraction entry has the tables)*


## A sub-pixel vertex makes the polygon inscribed — read the vertices, not the boundary offset (2026-09-09)

`cfg.subpixel_edges` (plan `2026-09-08-subpixel-edges.md` PR 2) moves stage
4's contour vertices from pixel centres onto the anti-alias edge. On the
ladder's 400 px circle the vertex spread fell 0.049 → 0.013 mm and the
boundary offset got WORSE, −0.045 → −0.067 mm. Both are right: with every
vertex on the edge the polygon is inscribed, so each Douglas-Peucker chord
sags inward by the 0.2 mm tolerance, where the staircase used to leave
outer corner pixels for the simplifier to hang chords on. A geometry change
upstream of the simplifier reaches the stitches only through the
simplifier, and its floor is the chord — the same floor the ladder's
baseline found OFF above 15 px/mm. **Judge a vertex change on the
vertices** (`edge_truth_ladder`'s `vertex_*` columns exist for this) and
the chords on the refinement that owns them; a boundary-offset reading
alone would have called this PR a regression.

**Three constructions that were wrong before they were measured, on the
same PR.** (1) The 0.5 crossing of a linearly interpolated profile is
biased ±0.09 px because the coverage ramp's knots sit half a pixel off the
pixel centres; the area integral of the inside fraction is exact for a
straight edge and any symmetric ramp (straight-edge error −0.05..+0.01 px;
16x disc scatter 0.037 px). (2) A rejected vertex left between accepted
neighbours is an inward spike the simplifier must keep — drop it, its
position is unknown and theirs is not. (3) A corner read along one blended
normal is bevelled (a right angle reaches 0.5 of 0.71 px); read each side
and intersect. **Each was found by a fixture the plan did not name**: a
straight edge at four sub-pixel phases, a 16x disc (the 4x fixtures are
only good to an eighth of a pixel — cv2's fill rule at 4x put the disc's
truth 0.1 px from where the generator's docstring says), and the
rectangles nobody thought of as the hard case. When a construction claims
sub-pixel accuracy, build the fixture whose truth is known to better than
that before believing the number it reports on the fixtures you have.
*(2026-09-09 — plan §3's BUILT note and scope-history's entry have the tables)*


## Widening a rescued glyph's polygon does not change how it is sewn (2026-09-09)

`cfg.lettering_min_column_mm` (PR #428) raises a door-1 text cluster's
regularized stroke radius to half a sewn floor less the fabric's pull, on
the plan's premise that stage 5 adds the pull back and the glyph then sews
as a satin column of the floor's width. Measured with `keep_thin_strokes`
on: Fremont widens 10 of 32 cluster members and its satin row is
byte-identical (2,578 columns, median 0.93 mm); the widened glyphs sew as
the same bean runs on a fatter outline; ENTHUSIAST's subline legibility
falls 1.00 → 0.917. **The tier is decided before the width is read.**
`stage7_sequence` routes every auto-tier shape under `min_detail_mm²` to
`run_outline` first, and classifies the rest on the ARTWORK polygon —
deliberately, so a towel's pull does not flip satin to fill. A rescued glyph
is under the area floor by definition, so no artwork width reaches a column.

**The rule.** Anything that means to change WHICH TIER a shape sews in must
be built where the tier is chosen (stage 7's routing and the classifier's
input), not upstream in the geometry the classifier never reads at that
size. A polygon change is measured on `tools/sewn_tiers.py` and
`tools/satin_columns.py`'s satin row before it is called a sewing change;
if those do not move, it was not one.

**Built the same day — and it took FOUR decisions, not the two the
negative named.** Stage 7's routing and classifier input were the two. The
third was stage 5's *"never grow back over a colour that is already
down"*, which clips every shape to the artwork of the layers sewn before
it. A glyph on a ground is a HOLE in that ground at its original width, so
the widened glyph was cut back to its own hole before stage 7 saw it: the
rule passed its test on bars over bare background and sewed nothing new on
Fremont, and only instrumenting the classifier's INPUT (every widened glyph
arrived 0.28 mm wide — the hole, not the 0.6 mm polygon) found the clip.
The fourth was the same clip from the other side, found by the review's
probe, not by any fixture: when the lettering's thread sews BEFORE its
ground (largest-area-first order does that whenever that thread also holds
the biggest shape), the ground grows over the column and is clipped only
by the glyph's ARTWORK — 79% of the column buried, a 0.4 mm slit visible,
and `satin_columns` still reporting a full column because it reads the
glyph's own stitches. The layer unions now carry the sewn column. The
general form: a geometry change reaches the needle only through stage 5's
grown polygon (`PlannedRegion.polygon`) AND through what the layers around
it are clipped against, so measure the grown polygon — and the visible
part of it — before believing a polygon change is a sewing change; test
the fixture the feature is FOR (lettering on a ground), and then the
fixture that reverses its assumption (the ground sewing last).

**And the column has a floor of its own.** A 1.0 mm column in a 1.6 mm
glyph is a smear — ENTHUSIAST's subline sews 76 columns at a 0.63 mm median
with a 0.16 mm p10 and its legibility falls 1.00 → 0.72 — while Fremont's
2.2–2.9 mm letters sew 169 columns at 0.91 mm, the pro's width, and the
crops show even those filling their counters (the ON EST reads "OS"). A
column needs a glyph tall enough to hold it; the floor needs a glyph-height
gate (a new constant — gate 1) before `lettering_min_column_mm` can be on
by default, and that is Kent's. **The instrument's number is not the
verdict when a render is one command away**: routed legibility ROSE 0.551 →
0.577 on Fremont while the pictures got blobbier.
*(2026-09-09 — scope-history's two entries of that date have the tables;
`docs/renders/column-tier-2026-09-09/` the crops)*

## A default that moves every polygon by a pixel finds the mechanisms that were balanced on one (2026-09-09)

`subpixel_edges` ON moves every stage 4 vertex by a fraction of a pixel. Of
the 21 tests the flip turned red, ten were goldens and pins (re-captured in
CI) and the rest were mechanisms DOWNSTREAM of stage 4 that had been sitting
on a raster coincidence. Each was fixed in the mechanism, never by nudging
the polygon back:

- **A skeleton fork can land on a `medial_axis` pinhole.** On
  `enthusiast_logo`'s "N" at 150 mm the diagonal's foot forks symmetrically
  ON; the distance transform peaks on one pixel and `medial_axis` keeps the
  ring of its four orthogonal neighbours instead of the peak. Every ring
  pixel is topologically necessary (it keeps the enclosed pixel's
  background separate from the outside), so its own thinning never removes
  the ring, and **a Zhang-Suen `thin()` pass after it is a no-op — tried,
  219 → 219 pixels, identical edges.** The stub that reaches the ring ends
  on a loop, not a free end; both cap twigs prune as they should, nothing
  extends to the cap, and 13.6 mm² of the foot sewed as bare fabric. OFF,
  the same foot forked one pixel off-centre and kept a 5.6 mm corner branch
  — sewn, by luck. `stage6_satin._collapse_pinholes` sets the peak and drops
  the ring pixel that carries no arm; the pattern is exact (four orthogonal
  skeleton neighbours, four diagonal non-skeleton), so a genuine loop around
  a real hole never matches. Corpus scan: diamonds on 5 becker shapes, 2
  drone, 1–3 enthusiast, 1 gaulke, on both traces — becker's worst bare
  patch 23.8 → 8.2 mm² from that alone. becker's skeletons also carry
  enclosed holes of 2–4 px (loops around two or three pixels); those are
  measured present and NOT touched — nobody has diagnosed one.
- **Taper-zone refinement placed its inserted stations even along the
  SPINE and let the discrete ladder decide where each landed on the rail.**
  On `ribbon_curve`'s head ON, a 1.05 mm interval came out as pieces of
  0.51 / 0.37 / 0.20 mm; the guard pulled the crowded one 0.6 mm and every
  rail-based density read (the pinned test, `tools/audit.py`) saw it as a
  0.82 mm same-rail step. The pull's along-rail component near a tip is
  what makes a 0.6 mm pull read as 0.8: the metric cannot tell a pulled
  point from a gap, and the docstring of that test already said so about
  the body. Now the inserted penetrations are interpolated between the two
  PROVEN penetrations on each rail (even by construction, chord inside the
  artwork on a straight or convex edge, ladder fallback where it is not),
  and the zone refuses to crowd the short rail under the guard unless the
  long rail would otherwise be left wider than two pitches — the definition
  of over-wide every density read here uses. Corpus: crowded same-rail
  steps roughly halve (becker 76 → 53, drone 136 → 75, enthusiast 93 mm
  32 → 16), stitches −1 to −2%, over-wide head/tail readings within ±2 per
  fixture. Flooring the piece count on the SHORT rail instead was tried
  first and left the pre-flip ribbon's long rail its whole 0.85 mm gap.
- **A fault-injection fixture is a coincidence with a shape id.** The
  unguarded-prune test rested on a 19.000 px stem against a 19.477 px bar
  (`_prune_spurs`' own docstring); ON, the stem lands on the other side of
  that bar and the unguarded prune drops nothing the check can see at any
  of 80/93/100/120/150/180 mm. The test pins `subpixel_edges=False`, where
  the same shape still shows the fault at 150 mm; its paired product test
  runs the default.
- **Three pins moved with the polygon and were re-pinned, not loosened:**
  `logo_whitebg`'s vertex totals 62/101/125 → 117/128/141 (the refinement
  keyed to acceptance keeps curve vertices the 1 px floor simplified away;
  growth with size still monotone); the gradient ramp's single-thread
  reading 28.06 → 14.60 because the region's mean colour now picks cone
  3830 (the per-band rows are identical, worst 7.66); the owl's hoist test
  runs on the old trace because ON plans 14 blocks either way — the one
  revisit the argument needs is no longer planned.

- **The grader sampled half a pixel off the footprint, and two blocking
  findings were that half pixel.** `_region_color_errors` truncated mm→px
  while `_region_footprint` rounds; on pixel-centre vertices the two agree
  to a pixel, on fractional ones the whole grader mask sits half a pixel
  down-left of where the shape sews (97.5% agreement, was 99.99%). Rounding
  it moved the thread-match scorecard on two fixtures: gaulke's `1375` block
  rode a 1.03 mm² sliver whose ALIGNED eroded core is 42 scoreable pixels
  (57 misaligned) — under `_MIN_COLOR_PIXELS`, so it is not judged; bridge's
  `0108` block rode a 2.10 mm² shape whose aligned erosion leaves 2 pixels
  where the misaligned one left 0 and took the hairline fallback. Bisected
  by restoring truncation alone: both counts come back. Re-pinned with the
  bisect in the notes; the scorecard moving by exactly those two findings is
  Kent's to keep or revisit. And a spool whose only shapes fall under the
  floor vanished from `loaded` (it was built from the graded rows, not the
  blocks its own comment named), so 3971's finding went back to "buy
  thread" with 1375 on the machine 5.0 dE00 away — `loaded` is the plan's
  sewn blocks now, and a row's spool is always one of them.
- **A crossing is rendered by raster parity, and only one side of it is
  fixed.** The pinhole collapse gives `test_stroke_classify`'s PLUS its two
  bars at 6 px/mm (the diamond was the crossing); at 1.25× the same crossing
  is two 3-way nodes a pixel apart and still decomposes into three strokes.
  Before, both scales read three — equal by the same artefact twice, which
  is what a scale-invariance test cannot tell from correctness. Adjacent
  junction pixels were not clustered anywhere; that was the next mechanism
  in this family, built the same day (the entry below).

**Rule:** when a default flip moves every polygon, treat each downstream
failure as the pixel-fragile mechanism it names — a skeleton, a ladder, a
grader mask, a coincidence — and fix or re-pin THAT, with the probe re-run
and the bisect written down, never the polygon. *(2026-09-09 —
scope-history's flip entry has the footprints;
`tests/test_skeleton_pinholes.py`, `test_satin.py`'s starburst test, the
three thread-match files' notes)*

## A junction is a cluster, not a pixel — and a loop inside it is the pinhole's larger cousin (2026-09-09)

A raster medial axis renders one junction as several branch pixels a few
pixels apart whenever the stroke width is even in pixels or the arms meet
off-centre, and `_merge_through_junctions` paired arms per PIXEL. So a
crossing decomposed into three strokes (a bar and two half-bars) and a
five-way meeting into a chain of welds nobody drew, while the stub between
the pixels was dropped as junction noise only after the pairing had
happened. `stage6_satin._cluster_junctions` contracts every node-to-node
edge under **0.5 half-widths (floor 3 px)** into one junction rooted at the
deepest-DT pixel. The number is read off the corpus, not guessed:
`tools/junction_nodes.py`'s length/half-width histogram has a bump at
0.2–0.4, a trough at 0.4–0.5 and a tail from 0.5 up, and every edge in the
bump is shorter than half the DT at its own ends. It is bounded above by
`_MIN_STROKE_HALFWIDTHS` (1.2): a stub under that was never sewn.

**Junction noise comes in two shapes, and removing one without the other is
worse than neither.** With the stubs contracted alone, enthusiast's emblem
bracket at 150 mm lost 7 mm² at its tab: the tip is a tiny LOOP (two 4–7 px
paths between two nodes a pixel apart plus a self-loop — the pinhole
diamond at sizes 2–4), which made it a five-arm junction instead of a cap,
and the old stub had happened to carry the uncapped stroke 0.74 mm further.
A loop that returns to its own cluster within twice the threshold is
dropped with the stubs; the node is then one arm, and the cap finish runs
it out to the tip.

What it moved (14 fixtures × 2 traces, scope-history's junction entry):
interior over-wide rail readings **948 → 830**, becker's bare total 16.0 →
9.0 mm², enthusiast 150's worst 4.5 → 1.2, at +0.21% stitches; end-zone
readings 107 → 121, which are the terminal crosses of caps that are free
ends now. The K's crotch (7.8 → 9.0) is the junction COVER's problem, not
the graph's — the patch flag, PR 2. **No golden moved**: the flat-lane keys
have no branch node, so a skeleton-graph change is provably byte-identical
there before it is measured anywhere else. *(2026-09-09 — the plan doc's
§4 has each prediction against its result)*

## The band above the satin cap is a decomposition problem wearing a width problem's clothes (2026-09-09)

Built and measured: `cfg.wide_columns` (OFF) raises the satin ceiling to
6.5 mm — the pro's MARINE p99, read off files sewn on garments — as ONE
number threaded from the classifier to the emitter, with the per-station
cap replaced by the bend's radius of curvature (`_fold_caps`). Three
things the measurement settled, each of which changes what to do next:

- **The 2026-09-02 premise has moved.** The coupled route reopened
  logo_alpha's apex to crossing itself; on this tree the apex reads 0
  crossing pairs from 5.0 to 8.0 mm with or without any guard (122
  unbounded, the two legs sharing the blob). Do not cite that entry's 18
  failures as the reason a ceiling cannot move — cite this one: the guard
  that IS load-bearing is on a BEND (Becker at 80 mm, radii ~5 mm under
  5–6 mm columns: coverage_max 7.07 with no guard, 5.08 at 0.7 × R), and
  it moves nothing anywhere else.
- **A p90 of the medial radius over-reads a bold letter by its junctions.**
  Our DT read MARINE's letters at 5.1–8.0 mm; the pro sews their stems at
  4.8–5.0 whole and their serifs as separate columns. Two letters are
  "wide" only because their diagonals meet their stems. A junction-aware
  width statistic is the next thing the classifier needs, not a higher
  number.
- **Admitting the band does not sew it well.** MARINE at 100 mm goes satin
  at −13% stitches and comes out with 251 self-crossing pairs at the feet
  and junctions, 3–5 strokes and 4–7 trims per letter against the pro's
  ~2, and drone's admitted wing leaves 7 mm² bare inside itself. The
  render (`docs/renders/wide-columns-2026-09-09/`) is the argument: the
  columns are the right width and the wrong shapes. **Rule: when a policy
  admits a new population, render what it produces before pricing it —
  the stitch count fell and the letters got worse.** The flag ships OFF
  and the review's item 5 (serifs as columns, junction cover) is what
  makes the band worth flipping. *(2026-09-09 — scope-history's
  wide-column entry; `tools/wide_columns.py`)*
