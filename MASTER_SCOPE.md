# EMB-Bot — Master Scope

**What this is:** a live status dashboard, not a requirements doc. It exists so
Kent and any Claude session can answer "where do we actually stand?" without
re-deriving it from a dozen spec/plan docs each time. It tracks five product
capability areas on two independent axes — **Status** (is it built) and
**Confidence** (do we trust it) — plus cross-cutting issues that don't respect
area boundaries.

**How it's kept current:** updated proactively after PR-sized work lands, and
on demand via the `/update-master-scope` skill. See "How this document works"
at the bottom for the authority model behind the confidence ratings.

**START HERE if you are picking up the real-artwork parity work:**
[`docs/handoff-2026-08-16.md`](docs/handoff-2026-08-16.md) indexes the
2026-08-15/16 session — the honest baseline (**42.5**, not the older ~70), the
metric's own **75-84** pro-vs-pro ceiling, four defects real customer artwork
exposed, and the traps that cost that session time. Four of its findings are
standing rulings below. **The code and instruments it describes are ON `main`**
— PR #157 merged (`4967ed5`), so `digitizer/tools/pro_parity/` including
`selfconsistency.py` is in a plain checkout.
*(confirmed 2026-08-17 — `git ls-tree origin/main`)*

**Last updated:** 2026-08-25. Dated history lives in
[`docs/scope-history.md`](docs/scope-history.md); **this file is current state
only.** See "How this document works" at the bottom for the rules that keep it
that way, including the line budget.

**Every claim below carries a pointer** in the form
`(verb date — source)`: `confirmed` means checked against code or a passing
test, `measured` means a number was produced, `suspected` means neither. Treat
a claim with no pointer as unverified — and if you find one, either verify it
or move it.

---

## Live defects — believed true right now

1. **RESOLVED 2026-08-19 — shade-thread collapse.** Numbered, not deleted: ten
   other docs cite these by number. *(`_shade_blocks`)*

2. **No width floor under satin — PHOTO-LANE HALF CLOSED 2026-08-22; still
   DISPROVED for flat art.** Corpus regions that sew sub-mm satin are all
   photo-family, but 61 of 64 sub-1.0 mm satins on real customer logos are
   ground the pro ALSO satined — so `classify_ribbon`'s `photo_width_floor`
   reroutes earned sub-1.0 mm satin on photo classes ONLY (1.0 mm is Law 31
   verbatim, never tuned — gate 1); flat/gradient byte-identical. **Open:**
   default routing sends drone/summit to GRADIENT, where the floor is barred.
   `cfg.is_photographic` is deliberately NOT wired here — it moves satin
   routing, not palette or grading. *(measured 2026-08-11, landed 2026-08-22
   — `docs/tonal-eng-measurements-2026-08-22.md`)*

3. **14 jump-trims on an 80mm design,** every fill variant measured. Not
   started. *(measured 2026-08-12 — scope-history)*

4. **We trim far more than the professional — 3.1x the trim breaks on a
   like-for-like corpus.** Quote the rate or the break count, never a run
   count and never raw `trims`. **Cause: trim policy, not travel** — the pro
   never cuts under 11.8 mm, ours is 3.0, and gate 1 says cloth settles that.
   The `_graph_travel` half of the old attribution is RETRACTED. Not blocked:
   five pro variants sit in `digitizer/testdata/reference/`.
   *(measured 2026-08-18/21 — `docs/fragmentation-attribution-2026-08-18.md`)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   The *mix* nearly matches the pro's, so retuning `satin_max` cannot fix it —
   it only moves a mix that is already right. **Partly closed, and the
   remainder is NOT the classifier: it is SEGMENTATION.** An oracle knowing
   the pro's per-shape answer scores 76.6% against our 55.4% — our regions
   straddle the pro's satin/fill boundaries. `docs/segmentation-alignment-
   2026-08-17.md` recommends NOT building the region-level fix (the straddle
   is 95.8% grid noise). *(measured 2026-08-14/17 —
   `docs/satin-gate-attribution-2026-08-16.md` §9)*

6. **Satin fragments into many small islands on real logo art — and the trim
   bulk is INSIDE one shape, not between them.** 69% of trims are
   intra-shape. Retire the old framing: the rope border was never one stroke
   the engine shattered — the artwork is ~136 separate chevrons. **And it is
   UNREPRESENTATIVE of client logos**, which carry 1–3 fill shapes that
   essentially never cut. *(measured 2026-08-21/22 — area 1)*

7. **RESOLVED 2026-08-21 — satin silently dropped a bracket's tab** on
   `enthusiast_logo.png` (7.8 mm² bare, D/52 → C/64). *(`_prune_spurs`)*

8. **RESOLVED 2026-08-22 — build-font dropped SVG transforms on most fonts.**
   `mimosa_large` "D": 6,193 stitches into 40.0 x **0.0 mm**. Four fonts, one
   fix. *(`tools/build-font.mjs`, `test/font-transforms.test.js`)*

9. **RESOLVED 2026-08-24 — the photo route escaped its own palette; both
   halves closed.** Region half (#217): `revalidate_threads` masked to the
   palette, flat+gradient byte-identical. Shade half: `shade_palette_bind`,
   **default ON** per Kent's 32-job-sheet ruling — every design's cones now
   equal its palette. Pinned edge: a one-spool design flattens tone.
   *(PR #217 + 08-24 flip)*

10. **RESOLVED 2026-08-23 — three photo-route robustness defects, every one
    found by the first real photos, none reachable by a committed fixture:** a
    7.4 MP OOM (#214), an infinite loop in `select_palette` (#218), preflight
    condemning correct thread-paint as too loose (#216).

11. **RESOLVED 2026-08-24 — the memory ceiling was per-region full-frame
    masks**, now cropped to bboxes: an 8x drop, same region counts, and
    MB/MP falls with size where it used to climb. Correction: the 12.4 GB
    OOM was contention with another script, not one job. *(PR #230)*

12. **RESOLVED 2026-08-24 — preflight graded every photo job F.** A capped
    cone list guarantees per-thread distance, so `THREAD_MATCH_POOR` fired on
    every job; it now scores EXCESS over the best already-loaded spool on the
    photo route (raw elsewhere, byte-identical). *(PR #229)*

13. **RESOLVED 2026-08-24 — the detail layer sewed the background a subject
    cutout had just removed.** FDoG reads the whole raster, so the removal
    never reached it; `SourcePixels.subject_mask` now confines the line map.
    Invisible until then because **no acceptance arm had EVER set that flag**
    — the same blind spot the section below exists to close.
    *(measured 2026-08-24 — [area 1](docs/scope/1-auto-digitizing-quality.md))*

14. **ANSWERED 2026-08-25 — the photo route leaves half the cloth bare inside
    each shape, and that is the THREAD-PAINT TIER, not a density bug.**
    Streamline covers 0.55–0.59 of its footprint against the filled tier's
    0.99. Kent ruled filled for high-contrast subjects; see the standing
    ruling for the face exception. *(measured 2026-08-24/25 — PR #234;
    [area 1](docs/scope/1-auto-digitizing-quality.md))*

---

## Latent — gated OFF, DO NOT FLIP without rebuilding its instrument

Safe today only because these ship off; each becomes a live defect the moment
someone flips a flag that reads like an optimisation. **A green suite is not
evidence for either** — on chaining, a green suite actively concealed it.

1. **`chain_links` — sews needle-down thread on bare fabric.** 16.15 mm exposed
   over 17 links on `full_back`/`fleece_sweatshirt`, stock preset, green suite,
   one point over a millimetre from any thread in the design. The two shipped
   instruments were blind three ways over (one-point links skipped, first/last
   sewn segment never tested, cover measured as polygons not as where thread
   lands) — all three CLOSED 2026-08-18: thread-derived check shipped, four
   fixtures accepting at **0.00 mm** added bare thread, **9.82 → 4.06**
   trims/1k. **Still DO NOT FLIP, now permanently:** gate 1 names link cover
   tolerance, a thread spec, and the sew-out is accepted as-is, so this is
   frozen rather than pending. Largest lever on defects 4 and 6. *(measured
   2026-08-02 — `docs/hardening-closeout-2026-08-02.md`; confirmed 2026-08-18 —
   `config.py:1006-1068`, `preflight.py:1483-1543`)*
2. **`split_tonal_regions`** — the shading fix, merged but off; parked until the
   sew-out. Cost and ceiling under "Waiting on Kent". *(confirmed OFF
   2026-08-17 — `config.py:647`)*

*(section added 2026-08-17 — `docs/project-review-2026-08-16.md` §1.6: chaining
was absent from the live-defect list entirely, so a good-faith flip would have
shipped visible thread on bare fabric with no warning in this dashboard.)*

---

## Standing rulings — decided, do not re-litigate

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

---

## Corrections — suspicions this document itself raised, then disproved

Kept rather than deleted: the shared failure mode — **a hedged observation loses
its hedge as it is copied forward** — is why this file is split.

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

---

## Gotchas — cost someone a session once

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

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art; human faces TABLED pending a more capable tier *(Kent, 2026-08-25)* |
| 2. Font library & lettering | Implemented — 85 fonts, satin + bean/running + cross-stitch, LTR + Hebrew RTL | High (tech) / High (compliance). Zero stunted glyphs since the 2026-08-22 transform fix; the guards now assert their own coverage |
| 3. Studio app / guided wizard | Implemented | Medium (fabric-preset accuracy: **pending sew-out** — unchanged, no sew-out has happened). Held at Medium by that gate alone; the display layer had a defect class that shipped unseen for want of UI-behaviour coverage, and a 2026-08-25 sweep closed the known ones *(confirmed — area doc)*. The preview now renders thread as a lit cylinder at physical width; its lighting is eye-tuned, not sew-verified |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented — Kent's direct-manipulation request is **complete** (2026-08-13) | High. Every surviving requirement of the 2026-08-12 request ships: outlines+nodes on the canvas, the pulse cue, select-then-edit, node drag, line drag, add node, delete. Requirement 5 (whole-shape drag) was withdrawn by Kent. Geometry is unit-tested and every interaction was driven in a real browser against a live service. Manual draw mode now traces over the uploaded artwork, and right-click places a curved node |

---

## Waiting on Kent

The decision queue. Everything OPEN here is blocked on a call only Kent can
make, not on engineering effort; a resolved entry keeps its number rather than
being deleted, same as the defect list. Detail stays in its own section rather
than duplicated here, so this list can go stale about WHAT IS OPEN but never
about the facts.

1. **RESOLVED 2026-08-22 — the stage 0-4 cache is funded and built.** Split at
   the review-edit seam; an edited re-digitize re-runs only the finish,
   byte-identically. *(confirmed — tests/test_generation_cache.py)*

9. **RESOLVED 2026-08-24 — tonal v1: shade escape closed, bind ships ON.**
   2026-08-23 Kent ruled v1 not done at 68–78 stops a portrait; 2026-08-24 he
   took `bound_shade` as the photo-route default, declining (b). *(2026-08-24)*

**Also open, same category — so this queue is not a half-truth. All predate
2026-08-14 except where noted:**

2. **The DST codec fix** — was gated on the sew-out; that gate is now permanent
   (standing rulings), so this needs its own call on its own merits.
   Re-orienting the table changes every DST EMB-Bot has written. See "DST codec
   axis bug".
3. **Turn `split_tonal_regions` on?** Merged but default-OFF. Costs +74%
   stitches and pushes the palette to its `max_colors + PALETTE_OVERFLOW_K`
   ceiling. Parked until the sew-out (2026-08-12) — that parking is now
   indefinite, same as above. See the blend-tier entry and "Latent — gated OFF".
4. **Billing / backend.** Tabled since the pivot; Stripe + an entitlement
   check is the leaning, nothing committed. Needs its own session. See
   `PRODUCT.md`, "Open — not yet decided".
5. **Starter design pack (launch item 3).** The last unstarted item on the
   launch checklist, and it cannot start without a sourcing decision — the
   non-goals rule out a user-upload gallery on copyright grounds. See
   `PRODUCT.md`.
6. **The `scratch_corpus/` 37 files.** Gitignored; cloud checkouts are empty
   but all 37 are present on Kent's machine (confirmed 2026-08-17), so a local
   session can run the corpus legs today. Blocks cloud-side M2/M3 only.
7. **26 glyphs that sew nothing, in 6 shipped fonts** (`roaring_twenties_KOR`
   ×2 have ten symbols each). The user-facing half is closed — the Studio now
   says "This font can't stitch …". The fix needs YOUR MACHINE: the candidate
   cause is `stripRunParamsIfSatin` being font-wide, and telling that from
   "upstream never authored a length" needs the `scratch_ink/` SVG sources. The
   narrow fix regresses nothing but changes auto-scaling. Detail: area 2.
10. **RESOLVED 2026-08-25 — Studio typography: "tighter and more editorial."**
   Kent's direction, given when asked. It settled the three items the earlier
   type work left alone (irregular scale ratios, `h3` at body size, untokenised
   weights) and it is a STANDING one — new UI is set to it, not re-litigated.
   What it means in practice is in the area doc. *(2026-08-25)*

8. **Font lawyer consult — optional.** Only gates RESTORING the 13 pulled
   ShareAlike fonts; the brief is written and ready to send. Nothing waits
   on it. See the font-licence entry.

---

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec axis bug

EMB-Bot's browser DST codec (`src/dst.js` / `src/dstimport.js`) is transposed
vs. the Tajima/pyembroidery standard — confirmed, unresolved. It round-trips
against itself but reads a quarter-turn wrong elsewhere. **Not only
orientation:** `dst.js` writes the colour-change byte as `0x43` not `0xC3`, read
as a spurious sequin toggle, so a two-colour design decodes with ZERO colour
changes elsewhere. PES and EXP are identity-clean. Full evidence trail, and a
fifth independent corroboration from Ink/Stitch's `pystitch`:
`dst-codec-axis-discrepancy` in memory. *(re-measured 2026-08-22)*

**Not a conflict:** CLAUDE.md's "browser DST is EMB-Bot-internal only" is about
orientation elsewhere; `digitizer/README.md`'s "browser DST stays the default"
is about which encoder Studio picks.

**CLOSED — the "unreachable from the real product" claim was false when
written.** Auto-digitized designs leave by pyembroidery `/export`, lettering and
manual stay on the browser codec (the sew-evidenced combination), and the
download step warns before every browser-DST download.
*(confirmed 2026-08-17 — code read, commits dated)*

**Resolution path:** a sew-out or third-party read of a browser-encoded DST.
Fixing the codec is **Kent's call** — every existing EMB-Bot DST is affected.

**The cross-validation harness is ALIVE again — revived 2026-08-21.** It
reproduced the DST transposition exactly (rms 0.0) and caught the broken browser
PES/EXP encoders; the 2026-08-11 pystitch swap had silently starved it to 0 of 6
passes while staying green in CI. CI now fails loud when the pins cannot run.
*(confirmed 2026-08-22 — engine green, 0 skips)*

### Font license compliance — RESOLVED, and kept resolved by construction

ShareAlike was closed by removal rather than by waiting on a legal opinion, and
stays closed: `ALLOWED_LICENSES` gates the sellable build, so an excluded font is
never packaged rather than switched off at runtime. Licence texts ship three ways
(on disk, served, embedded) — load bearing beyond the OFL, since it discharges
`roman_ags`'s LPPL clause-6d obligation. Detail: [area 2](docs/scope/2-font-library-lettering.md). *(confirmed 2026-08-22 — guard tests; `docs/font-license-audit-2026-07-31.md`)*

**Still open, both Kent's:** the optional lawyer consult (gates only the 13
pulled fonts, `docs/lawyer-brief-cc-by-sa-2026-08-04.md`) and the bluenesia
permission screenshots (audit §8).

### CI feedback speed

`-n auto` (pytest-xdist, pinned) roughly halved the digitizer suite. **Do not
re-tune hoping for the 2.5-3x seen locally:** GitHub's standard runners are
2-core, so `-n auto` gets two workers and OpenCV's threading competes with
them. The remaining lever is `--durations`, not parallelism. Parallel-safety is
verified, not assumed. *(measured 2026-08-14 — scope-history)*

### No physical sew-out testing has occurred yet

Zero sew-out testing anywhere in this project — confirmed across three
independent research passes. `docs/hardening-closeout-2026-08-02.md`: "Nothing
was sewn. Every number above... is geometry." It is the single biggest
confidence ceiling here — fabric presets, real stitch quality, the DST axis
question all wait on it — and that doc already specifies four hoopings that
would settle nine open geometric questions at once. **Kent accepted this as-is
2026-08-21:** not a queued action; scores under it read `pending sew-out`
permanently. Do not re-raise it as the highest-leverage next action.

### Evaluation corpus & harness — real gap, newly tracked here

**The gap: no repeatable automated quality signal**, so every serious quality
question queues behind a corpus nobody has or a sew-out nobody has scheduled. A
labelled corpus plus a scoring harness would let a classifier change be judged
against *something* before either arrives.

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture`/`diff`
over 14 fixtures x 2 configs, aggregating preflight's score rather than
inventing a metric. Deliberately a REPORTING tool, not a CI gate. Detail and
scope limits: [area 1](docs/scope/1-auto-digitizing-quality.md). Still open:
`summit_badge.png` (#6.2) is F/0 at both configs and SATURATED, so judge any fix
on `thread_worst_delta_e`, never score. *(confirmed 2026-08-21 — area 1)*

**Corpus half — the real-artwork entries keep contradicting the synthetics.**
Eight files of real customer logo art ship in `FIXTURES`: **stage 0 routes six
of seven to GRADIENT**, because real logo art carries JPEG ringing and
anti-aliased edges the synthetics lack, so any "flat spot-colour art" claim
tuned only on synthetics is untested against real input.
`logo_script_tires.png` classifies `photo_scene` outright — a misroute kept so
the bug has a fixture. **Real PHOTOGRAPHS go further still: all four of Kent's
portraits classify `gradient` with the LOWEST `unique_color_mass` in the whole
corpus — below every gradient logo.** That is the measurement behind
`cfg.is_photographic` being declared rather than detected.
*(measured 2026-08-15 and 2026-08-25 — `tools/corpus_scorecard.py:FIXTURES`;
scope-history 08-25 evening)*

**The tonal corpus is machine-bound and does not survive a session.** Kent's
portraits live in the gitignored `testdata/photo/acceptance/` (spec decision 6 —
public repo, never publish), so they are invisible to CI and must be re-attached
to chat each session. Drive cannot carry them: the pull-corpus skill's own
measurement shows binary corrupts silently in transit, and these are 3-8 MB.
`scratch_corpus/`'s 37 files remain unreachable from a cloud session (Waiting on
Kent #7). **Consequence: every threshold validated on faces today is validated
by evidence CI cannot see.** *(confirmed 2026-08-25)*

**A second harness exists: `tools/pro_parity/`** — how close our output is to
the PROFESSIONAL digitization of the same design, 23 designs, six weighted
components. **Its scale changed 2026-08-14** (chance-corrected floors); see the
Gotcha above before comparing to any earlier number. *(confirmed — PR #151)*

**Half that corpus is in the repo; the half that matters is not.** The tracked
`Embroidery Files.zip` carries all 23 pro STITCH files, so `prep_all.py`'s recon
lane runs from a fresh checkout. It carries **zero customer artwork**, so
`prep_both.py`'s real lane — the one behind the 42.5 baseline — still needs the
Drive copy. *(corrected 2026-08-18 — prep_both from the zip fails 0/15)*

**Area 1 is deliberately NOT split into "image analysis" + "stitch planning"**,
and the four capability gaps an external review named all have owners in code.
Both arguments live in [area 1](docs/scope/1-auto-digitizing-quality.md).
*(moved 2026-08-21 — rule 5)*

### Research backlog — competitive and open-source leads

Two capability sweeps produced backlog items rather than status changes: Ember
Design (a browser-based competitor) and Ink/Stitch. Both catalogues, the closed
`simplify_tol_mm` investigation, and a sixth independent DST-axis corroboration
live in [`docs/scope/research-backlog.md`](docs/scope/research-backlog.md).
Nothing in there is a commitment or a defect. Two things from it bind here:

- **Ink/Stitch is GPL-3.0** — concept-level clean-room reimplementation only,
  no literal copying or near-verbatim translation. The exception is `pystitch`,
  its MIT-licensed pyembroidery fork, usable as a real runtime dependency and
  since adopted. *(confirmed 2026-08-10 — `docs/inkstitch-research-2026-08-10.md` §0)*
- **Ember's own editor toolset is on file** (Pen/node, Closed Shape, Drawing
  Blocks, stitch simulator, realistic-view toggle) — check it before scoping
  manual-digitizing work rather than re-deriving it.
  *(confirmed 2026-08-08 — `docs/ember-technical-teardown-2026-08-08.md`)*

---

## Capability areas

One verdict per area. **The supporting detail lives in
[`docs/scope/`](docs/scope/)** — one file per area, linked below. Status and
Confidence here must agree with the At-a-glance table above; if they ever
diverge, fix both rather than picking one.

### 1. Auto-digitizing quality (image → stitches) — [detail](docs/scope/1-auto-digitizing-quality.md)

**In progress · Low confidence beyond flat spot-color art, and human faces are
now TABLED pending a more capable tier.**
Covers both implementations as one capability: the browser JS engine (complete
but frozen — retired in favour of "feed it clean flat art", not because it is
broken) and the Python pipeline, the active target. Stages 1–7, fill + satin,
the service, preflight and the review UI are built. SAM2 is merged and reachable
via the `embstudio:sam2` dev seam, still `photo_segment_sam2=False`.
**Tonal work has a shape now (2026-08-25).** Filled beats thread-paint on
high-contrast subjects and loses badly on faces; the satin-border rule, the
GeometryCollection crash, the per-ring abruptness gate and `cfg.is_photographic`
all landed and all validated against four real portraits. **What none of it has
is CI cover** — the tonal evidence is gitignored and machine-bound, so every
threshold shipped is defended only by an owl. *(measured 2026-08-25 — PRs
#241/#243/#245; scope-history 08-25 evening)*
**Kent's own verdict, 2026-08-27: these are 60% of the way to Ember parity.**
First per-design feedback in his words on all fourteen designs. `artfidelity_self`
averages **83.7** and `preflight` **80.0** on the same set, agreeing with each
other at only **rho = 0.405** — so **never quote ARTFID as a quality
percentage**: it is a fidelity score, blind to craft, which is most of his
missing 40%. He named the split himself — *"Shapes are accurate but smoothness
is not."* Two themes, equally weighted by him: smoothness (8 of 14) and whole
elements missing (7 of 14; both his "out of place" marks lost an element).
**Bears on ROADMAP phase 1's exit condition** — a fidelity-only metric may not
be able to agree with a partly craft-driven ranking at all.
**`ARTWORK_UNCOVERED` cannot see a dropped element**: fired on 1 of those 7,
`0.0 mm²` on the rest with `uncovered_checked: True`, because it is scoped to
shapes the design already sews. `tools/dropped_elements.py` measures it from the
artwork's side — 99.1% lost on the logo Kent called "5% completed at most".
**Two engine defects open, unfixed:** `summit_badge`'s half-removed background,
and `stage1_prep.py:254-266` answering a structural question (`BACKGROUND_ABSENT`)
through a colour threshold (`bg_tolerance_lab`).
*(measured 2026-08-27 — `docs/kent-review-2026-08-27.md`; memory
`kent-eye-vs-instruments-2026-08-27`. PR #276's body claims the engine is
correct on `summit_badge` — that sentence is wrong, its instrument fix stands.)*
**Satin extremity drop — FIXED 2026-08-21.** `_prune_spurs` re-measured a stem
its OWN first pass had un-branched, one raster pixel deciding a 3.3 mm tab.
**The blind spot that hid it stays fixed:** `preflight`'s `ARTWORK_UNCOVERED`,
5.0 mm² threshold still provisional. *(fixed 2026-08-21 — PR #186)*
**Lettering quality — the STITCH-ANGLE mechanism is FIXED 2026-08-27. Three
others remain open.** Kent on two sewn logos: *"lettering should be smooth"*,
*"ROOKIE MISTAKE"*, and *"Why is the 'N' running Vertically?"*

**Fixed: a word's letters now share one house angle.** `stage6_satin` grew
`satin_shape(angle_deg=...)` on 2026-08-26 — held loosely by `_clamp_to_span`,
which rotates the house angle only where a stroke cannot span it — but nothing
ever SET it, so the sewn output did not change. PR #282 added the derivation
(length-weighted, aggregated in `directionfield`'s doubled-angle space) and PR
#283 made it fire. Measured on the Becker Marine logo: satin and fill strokes
within ±20° of the modal direction go **29% → 51%** against a 22% chance
baseline, with **total thread −2.4%**, trims and jumps unchanged.

Three things had to be corrected to get there, each a threshold applied to a
population it was not calibrated on — the reusable lesson:
- `detect_text_clusters`' candidate set is gated on `rescued_small_shape` and
  on `STROKE_CV_MAX` (0.32). **Zero** of that logo's 17 regions carry the flag,
  and all 17 score CV **0.36–0.68**, so it finds no real lettering at all.
  `_lettering_groups` keeps the tests that transfer and drops those two;
  `detect_text_clusters` itself is untouched.
- The confidence gate was `directionfield.COHERENCE_FALLBACK_MIN` (0.25), which
  grades a per-pixel structure-tensor field. Real lettering sits UNDER it
  (R = 0.197 and 0.203). No raw threshold works: directionless square rings sit
  at 0.167. Replaced with Rayleigh's test — chance-corrected, rings and letters
  separate 10× where raw they separate 1.2×. Gate 4 in miniature.
- **7 of 11 lettering regions sew as FILL**, where the satin angle is not read
  and `best_fill_angle_deg` picks rows per shape by minimising that shape's own
  column count — which put two adjacent near-identical capitals at 22.5° and
  90.0°. That is the half Kent's complaint actually names. The house angle now
  sets `fill_angle_deg` too.
*(fixed 2026-08-27 — PRs #282/#283, mutation-checked; renders in the #283 body)*

**Mechanism 2 — pull comp's min-feature guard scoped to `poly.interiors` —
is PROTOTYPED AND COSTED, deliberately not shipped.** The fix is small and
correct (an exterior-pocket branch asking the identical question the hole loop
asks, patch in `docs/prototypes/`), and on
`logo_drone_thermal_badge.png` it holds 15 real slots at 0.528–0.920 mm while
skipping 82 slivers of median width 0.140 mm. **It reds the chaining trim
benchmark**: `enthusiast_logo.png` @82mm goes 3.8 → 6.4 trims/1k against a 4.1
ceiling, because restoring a notch breaks the gap chaining was bridging.
Shipped default (`chain_links=False`) the cost is +2 trims, 22 → 24.
**Kent's call 2026-08-28: hold it.** It trades a MEASURED trim regression
against an UNMEASURED fidelity gain — the instrument that would price the
other side is mechanism 4 below. Full numbers and both directions:
`docs/exterior-notch-guard-2026-08-28.md`.
*(prototyped 2026-08-28, not merged)*

**Still open and unfixed:** `_prune_spurs` drops a 3-way node to 2-way
so the walker welds the N's diagonal to its stem through a 108° fold — **the
same function PR #186 fixed, a different consequence one layer on**; and **the
instrument that hid all of it**, bare-fabric coverage scoring the visibly
deformed H at "1.9% bare". Shape fidelity reads 0.587 design-wide and is
screening only. *(measured 2026-08-26 — [area
1](docs/scope/1-auto-digitizing-quality.md); `.claude/memory/letterform-fidelity-2026-08-26.md`)*

**Confidence limit on the fix:** two real lettering groups, both from ONE logo.
The honest validation is a run over real client artwork and `scratch_corpus/`,
neither of which reaches a cloud container.

**Next:** NEEDS KENT. Fragmentation work measures **0% on real client logos**
(they are satin-dominated, 1–3 fill shapes, no cutting fills). The one large
real-artwork lever is **`chain_links`: −33% trims AND fewer stitches**, gate-1
frozen; every gate-clear alternative measures ≤9%. *(measured 2026-08-22)*

### 2. Font library & lettering — [detail](docs/scope/2-font-library-lettering.md)

**Implemented · High (tech) / High (compliance).**
**85 fonts** in the sellable build, the EMBF binary codec, browser UI, and the
add-font QC/tier pipeline. The lettering path stitches three types — satin,
bean/running, cross-stitch fill — where before 2026-08-21 it was satin-only. A
second `--personal` build (125 fonts) carries what cannot be sold; for licences
"Font license compliance" above is the single source. Same tech score as before
on a different basis (see the area doc); known debt is the 26 glyphs that sew
nothing, in "Waiting on Kent". *(confirmed 2026-08-22 — manifest, engine suite)*
**Next:** **upstream is exhausted; no external supply** — measured, not
assumed (area doc, "Supply"). Terminus closed. Growth means commissioning.

### 3. Studio app / guided wizard — [detail](docs/scope/3-studio-app-wizard.md)

**Implemented · Medium.**
The Svelte guided flow (garment → content → review → download), saved projects,
the Layers panel, and fabric/garment presets. Logic coverage is broad —
nearly every `app/src/lib/*.js` module has a paired spec — with UI-behaviour
coverage riding on live-browser e2e specs across several garments, the image
content path, four export formats, and the embroidery field's own chrome.
**What holds it at Medium:** fabric-preset accuracy is sew-out-gated, and no
sew-out has happened. See Cross-cutting issues.

**The display layer is a distinct risk surface, and the suite does not speak
for it.** A 2026-08-25 browser sweep found defects a green suite never touched
— a primary CTA rendering white-on-white on every wizard step, and a canvas
menu creating elements with no visible feedback. Both were shipped. **A Studio
change is not verified until it has been *looked at* in a browser.** Two lesser
display defects are deferred, not missed. *(confirmed 2026-08-25 — area doc)*

**A `var(--x, fallback)` whose name is undefined is not a fallback — it is a
silent bespoke value.** Three such names shipped, so the app carried two
warning colours, one bypassing the token system; two more tokens failed WCAG AA
on the app's own non-white grounds while passing on white. Both closed; re-run
the check when a new component lands. *(confirmed 2026-08-25 — theme.css)*

**Preview thread width is PHYSICAL, and must not be widened.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 1.0 against
the engine's 0.40 mm fill rows — rows that just touch — so a fill that is too
open looks too open. **Do not widen it to make fills look solid.** Row spacing
is an unresolved two-population question standing *pending sew-out* (area 1,
"Fill row spacing (law 19)"; `machine.py:45-49`), so widening thread would be
the display layer prejudging a question only cloth can settle — ROADMAP gate 1.
Display-only: it scales pixels, never stitch geometry.
**Caveat:** `lw` has a 1.2 px floor, so below ~3 px/mm the floor sets the drawn
width and coverage reads high. The property holds zoomed in, not on a
thumbnail. Guarded by a test pinning the literal 0.4.
*(confirmed 2026-08-25 — `preview.js`, `preview.spec.js`)*

**Correction (2026-08-25).** The paragraph above first read that widening
thread would "hide the open fill-density item … FILL_ROW_MM running ~2x
light." That overstated a hedge into a defect: the ~0.20 mm figure is a
satin-rail **artifact** for one file population (refuted) and a genuine denser
pitch on 43 commissioned cap logos (still alive) — unresolved, not open-and-
known. It also pointed at Cross-cutting issues, which has never carried such an
item. Imported from the 2026-08-09 Ember teardown without re-checking it was
still live. *(corrected 2026-08-25 — area 1 "Fill row spacing (law 19)")*

**The stitch simulator already exists — do not build a second one.**
`lib/simulate.js` plus EmbroideryField's `simbar`: play/pause, a scrub slider,
speed cycling, close. `renderRealistic`'s `limitStrands` is its drawing
contract. This was nearly rebuilt from scratch on the assumption it was a gap.
*(confirmed 2026-08-25 — driven in a browser)*

**Thread lighting is unverified against real thread.** The light direction,
sheen ceiling and shadow weight are eye-tuned judgement calls. No sew-out has
happened, so there is nothing to compare a render against — treat the look as
a preference setting, not a calibrated one. *(suspected 2026-08-25)*

### 4. Export formats — [detail](docs/scope/4-export-formats.md)

**Implemented (all five) · Confidence varies by format, not one score.**
DST, EXP, PES, SVG and the PDF worksheet, via both the browser encoders and the
service's `/export` route. One reachability caveat: `/export` is only reachable
from the product for purely-digitized designs — anything containing lettering
or manual shapes downloads through the browser encoders.

- **DST — split by path.** Browser DST is Medium as Studio's sewn-and-shipping
  default, Low if treated as verified-correct-orientation in the abstract; that
  is the cross-cutting axis bug, same defect. Python `/export` DST is
  Medium-High by spec, not itself sew-verified.
- **EXP — Medium-High.** The 2-byte trim record (fatal to pyembroidery-convention
  readers at the first trim) and the phantom terminal end-stitch are both fixed.
  *(confirmed 2026-08-06 — PR #58)*
- **PES — Medium-High.** The 5-byte stitch-stream mis-framing, jump records
  flagged as trims, and never-set palette indices are all fixed.
  *(confirmed 2026-08-05 — PR #58)* Held below High because nearest-chart colour
  mapping is lossy by construction (PEC has 64 fixed colours) and this is
  pyembroidery cross-validation, not a verified Brother-machine load.

### 5. Stitch-out review & manual editing tools — [detail](docs/scope/5-review-manual-editing.md)

**Implemented · High. Kent's direct-manipulation request is complete.**
*(confirmed 2026-08-13)*
Every surviving requirement of the 2026-08-12 annotation ships: outlines with
nodes drawn over the result automatically, the pulse cue, select-then-edit, node
drag, line drag, add node, and delete. Requirement 5 (whole-shape drag) was
withdrawn by Kent. Geometry is unit-tested (53 cases in `shapeOverlay.spec.js`)
and every interaction was driven in a real browser against a live service.
**Do not compress the detail file's copy of Kent's request** — it is captured
verbatim there because the sub-requirements *are* the spec.

**Manual draw mode can now trace over the artwork.** An uploaded image paints
under the drawing canvas (fadeable, removable) as soon as it decodes, before
any question of auto-tracing — so hand-digitizing a logo by eye is reachable,
which it was not while the canvas was blank. **The backdrop and any shapes
traced from it must share one fit:** `manualTrace.js`'s `traceFitRect()` is
called by both, and a second implementation would drift into outlines sitting
slightly off the artwork — a bug that reads as an inaccurate *tracer*.
*(confirmed 2026-08-25 — `traceFitRect` test + browser)*

**Right-click places a curved node, left-click a straight one**, coloured green
and indigo respectively. Ember's gesture and colour vocabulary, matched
deliberately. The default bow takes its side from the turn the path is making,
so a run of curved nodes arcs instead of scalloping. Backspace mid-draft takes
back the last node. *(confirmed 2026-08-25 — `curvedNodeThrough` tests + browser)*

**Copy/paste (Ctrl+C/V), Duplicate (Ctrl+D), and a per-shape Dim slider.** The
clipboard holds a shape *snapshot*, not an id, so a paste after the original was
edited or deleted still pastes what was copied. Dim is view-only and never
reaches the stitch plan or the `.embproj`. Both shipped with defects that a
pure-logic test could not see and a later review caught: `duplicateShape`
landed the copy exactly on the original for any shape flush to the canvas edge
(every traced outline, since `traceFitRect` letterboxes to the edges), and the
Dim slider froze at whatever value the shape had when it was selected, because
Svelte's legacy `$:` dependency list only sees what a statement *textually*
names — a read inside a called function is invisible to it. Both fixed, both
now pinned by tests proven to fail against the old code.
*(confirmed 2026-08-26 — `manualShapes.spec.js` + `ManualPanel.spec.js`, mutation-checked)*

**Driven in a real browser 2026-08-26** — right-click curved nodes, the tracing
backdrop, Duplicate, and the Dim slider, all exercised by hand rather than only
by tests. Two things were wrong that no test could see. The drawing canvas
opened mostly below the fold on a short viewport (14% visible at 1280x720, 92%
at 1440x900, 100% at 1080p — which is why it never showed on a desktop); it now
scrolls itself in **only when measurably clipped**, so a tall screen is
untouched. And the trace panel's file picker was a bare `<input type="file">`
rendering as raw OS chrome that read "No file chosen" even after a file loaded
(`onFile` clears the input's value so re-picking the same file still fires);
it now uses the same styled-label pattern as `DigitizePanel`'s `.dgp-upload`.
Confirmed working and NOT broken: the traced outline lands exactly on the
backdrop artwork, and the dropped-hole warning does show — before you accept
the shapes, which is the moment it matters.
*(confirmed 2026-08-26 — Playwright browser session, measured at three viewports)*

**The flat and realistic views now agree about sew order.** A colour that
recurs later in the sequence is its own block in both, not merged back into its
first appearance. The lit path was fixed for this on 2026-08-25; the flat path
kept the bug for another day, on the one view you switch to specifically to
judge coverage. Pinned as an invariant — the two views must produce the *same*
block sequence — rather than as two independent expectations.
*(confirmed 2026-08-26 — `preview.spec.js`, mutation-checked)*

**Eight more defects fixed by sweeping for the bug SHAPES, not the instances.**
PR #264 fixed nine defects in this area, and three of them existed for one
reason: a fix applied to one code path was never applied to its siblings. PR
#269 swept the repo for the shapes instead. What a user would have hit:

- **Manual shapes did not sew in draw order.** `digitize.js` sequences
  light-to-dark by default and the manual branch never opted out, so a cream
  circle drawn on top of a navy rectangle sewed cream-then-navy and the navy
  buried it. `ManualPanel` paints later-over-earlier and hit-tests
  back-to-front to match, and offers no reorder control — the stacking the user
  drew was simply unreachable. Now `darkOnTop: false` on the manual and
  preset-shape branches **only**; image mode keeps the heuristic, correctly,
  because nothing in a raster says which colour the artist meant on top.
  **This changes what already-saved manual designs sew**, which is the point.
- **A thread override landed on the wrong colour and EXPORTED that way.**
  `blockColors` is keyed by palette index, the service re-derives the whole
  palette on every run, and nothing remapped it: set "red → navy", re-digitize
  4 colours down to 3, and the override is now on white. `remapBlockColors`
  matches on the colour the override was chosen *for*, so it follows a thread
  that moved and is dropped with one the palette removed. Storage stays
  index-keyed — no `.embproj` migration.
- **A stale undo button deleted an innocent element.** Element ids are recycled
  (`nextElementId` is `max+1` over the survivors) and `textConversions` kept
  naming a deleted one, so a new element taking the freed id could be destroyed
  by the old cluster bar's "Undo". Pruned in `removeElement`, which every
  removal path funnels through. Monotonic ids were considered and rejected:
  schema change plus a migration for every existing save.
- **A bulk edit looked like it did nothing.** `sharedColor`/`sharedWeight`/
  `sharedFont` named only `multi`, a boolean — once multi-select is entered it
  is `true` and stays `true`, and `safe_not_equal(true, true)` is false, so all
  three readouts froze. The edits really applied; the panel just kept saying
  "mixed".
- **A stale cluster member count** (`{@const}` inside an `each` keyed by a
  string that never changes), and **a new template inheriting the last design's
  artwork** (`pickTemplate` replaced the project but never cleared the
  element-keyed `runtime`; `enterProject` has always cleared it — the unfixed
  sibling again).

Two of the guards pin RULES rather than call sites, which is the actual lesson
of the sweep: `ContentStep.reactivity.spec.js` asserts on compiled Svelte
dependency lists, and `App.projectReplacement.spec.js` asserts that every
whole-project-replacement path clears `runtime`. Twelve mutations were applied
and reverted, including faithful reproductions of each original bug — and one
test was caught passing for the WRONG reason (a `blockColors` fixture that never
actually collided two blocks onto one index) and its fixture corrected until the
mutation killed it. *(fixed 2026-08-26 — PR #269, mutation-checked)*

---

## How this document works

- **Two independent axes per area:** Status (is it built) and Confidence (do
  we trust it) — kept separate on purpose. Something can be fully
  Implemented and still Low confidence (the DST codec is the standing
  example), or In progress and High confidence (on track, just not done).
- **Confidence authority is hybrid.** Claude proposes a score with cited
  evidence (tests, docs, known defects); Kent has override authority.
  Anything whose real confidence depends on physical machine verification —
  fabric presets, real stitch quality, the DST orientation question — gets
  an explicit **pending sew-out** flag instead of a guessed score, because
  no sew-out testing has happened on this project yet.
- **This document is the source of truth for current status.**
  COOKBOOK.md's former "Known limitations" section pointed here instead of
  maintaining a parallel list, to avoid the two drifting out of sync.
- **Updates:** proactively after PR-sized work changes an area's status or
  confidence, plus on demand via `/update-master-scope` for a checkpoint
  whenever Kent wants a fresh read.

### The rules that keep this file current

Added 2026-08-14, after a fact-check found 30 of 56 sampled claims stale and
17 outright false. The root cause was not carelessness — it was that this file
interleaved live status with dated history in one stream, so every historical
measurement read as a current claim.

1. **Classify before you write.** Does this still govern a decision today, or
   was it true at a moment? *Still in force* — rulings, scope calls, known
   defects, invariants, open questions — goes here. *Was true then* — test
   counts, stitch counts, corpus grades, "landed PR #N", "as of today X" —
   goes to [`docs/scope-history.md`](docs/scope-history.md).
   **When in doubt, move it out.** History is recoverable; a stale claim
   presented as live is not.
2. **The cut is by force, not by date.** Kent's rulings are historical in
   origin and current in effect — they stay. An undated measurement is still a
   measurement — it goes.
3. **Every claim carries a pointer:** `(verb date — source)`. The verb is
   load-bearing and is not optional — `confirmed` means checked against code or
   a passing test, `measured` means a number was produced, `suspected` means
   neither. A claim with no pointer is unverified by definition. This exists
   because two suspicions in this document hardened into stated defects as they
   were copied forward, and both were later disproved by measurement; see
   "Corrections" above, which is kept precisely so that pattern stays visible.
4. **Budget: 800 lines.** Over it, compact before adding. The number has teeth
   on purpose — a skill already told agents to keep this file current, and it
   reached 5,400 lines anyway, one reasonable paragraph at a time.
   *(ruled 2026-08-14 — Kent, after the split measured 655 actual; the ~145
   lines of slack are deliberate, so a normal week of legitimate additions
   lands without forcing a compaction pass every time)*
5. **Overflow goes to [`docs/scope/`](docs/scope/), never to the bin.** One
   file per capability area, plus the research backlog. MASTER_SCOPE keeps the
   verdict and a link. Nobody should ever have to delete something load-bearing
   to satisfy rule 4.
6. **No test counts in prose.** They are stale within a day, nothing reads
   them, and every one the fact-check sampled was wrong.
