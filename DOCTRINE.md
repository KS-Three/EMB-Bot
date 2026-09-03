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

---

## Gotchas — cost someone a session once

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
