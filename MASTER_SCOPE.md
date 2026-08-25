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
`selfconsistency.py` is in a plain checkout. This pointer said "in PR #157, not
on `main`" until 2026-08-17. *(confirmed 2026-08-17 — `git ls-tree origin/main`)*

**Last updated:** 2026-08-22. Dated history lives in
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
   DISPROVED for flat art.** 19 of 162 corpus regions, all photo-family, sew
   sub-mm satin (Law 31), but 61/64 sub-1.0 mm satins on real customer logos are
   ground the pro ALSO satined — so `classify_ribbon`'s `photo_width_floor`
   reroutes earned sub-1.0 mm satin to the outline run on photo classes ONLY
   (1.0 mm is Law 31 verbatim, never tuned — gate 1). 58 verdicts / **29
   emitted-stitch reroutes**, 0.23–0.97 mm; flat/gradient byte-identical by
   suite and audit. Open: default routing sends drone/summit to GRADIENT, barred
   there — needs stage-0 discrimination (phase 2). *(measured 2026-08-11 —
   `docs/dt-first-verdict-2026-08-11.md`; disproved 2026-08-16 —
   `docs/satin-gate-attribution-2026-08-16.md` §7; landed 2026-08-22 —
   `docs/tonal-eng-measurements-2026-08-22.md`)*

3. **14 jump-trims on an 80mm design,** every fill variant measured. Not
   started. *(measured 2026-08-12 — scope-history)*

4. **We trim far more than the professional: 8.49 trims/1,000 stitches against
   the pro's 1.27** — same logo, same size, double the 4.1 ceiling this repo's
   own chaining test treats as the limit. Unambiguously a defect, unlike the
   stitch-count gap beside it. Like-for-like over 23 designs, same decoder both
   sides: **1,715 `trim` breaks against 555 — 3.1x. Quote that or the rate;
   never a run count** (the old "129 vs 15" counted plan OBJECTS against THREAD
   PATHS) and never raw `trims` (~2 TRIM per real cut on the pro's files, 1 on
   ours). **Cause:** trim policy, not travel — the pro never cuts under
   11.8 mm, ours is 3.0, gate 1 says cloth settles that; the `_graph_travel`
   half of that attribution is RETRACTED (~4 of 250 left at HEAD). **Not
   blocked** — five pro variants sit in `digitizer/testdata/reference/`.
   *(measured 2026-08-18/21; detail + disproved claims in
   `docs/fragmentation-attribution-2026-08-18.md` and scope-history)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   The *mix* nearly matches the pro's, so the cap is not simply too high or too
   low, while per-place agreement is barely above chance — about a third of the
   pro's satin ground is filled and a third of its fill is satined, two designs
   below their own chance floor. Retuning `satin_max` cannot fix a
   wrong-shapes-picked failure; it only moves the mix that is already right.
   *(measured 2026-08-14 — confusion matrix over the pro-parity corpus;
   per-design detail in area 1)*
   **Partly closed, and the remainder is NOT the classifier.** The DT regularity
   term accounts for 63.6% of the pro-satin ground we fill; loosening its limit
   is confirmed not to work, while a promotion path reopening it moves the
   corpus 45.8 → 48.1. The gain is real — corrected kappa `parts["sttype"]`
   rose 0.167 → 0.193 against a chance floor that itself rose, so it is not the
   floor-moving artifact §4 warns about. **What is left is segmentation:** an
   oracle knowing the pro's per-shape answer scores 76.6% against our 55.4%,
   and 48% of graded cells sit in shapes under 75% one type — our regions
   straddle the pro's satin/fill boundaries. Note
   `docs/segmentation-alignment-2026-08-17.md` recommends NOT building the
   region-level fix: the straddle is 95.8% `speckle`, i.e. grid noise.
   *(measured 2026-08-17 — `kappacheck.py`; detail in
   `docs/satin-gate-attribution-2026-08-16.md` §9)*

6. **Satin fragments into many small islands on real logo art — and the trim
   bulk is INSIDE one shape, not between them.** `logo_hotel_fremont.webp` at
   92.5 mm/patch: 135 trims, 12.60/1,000 by the repo's shared decoder against
   the five committed pro references at 0.95/1,000 — a **13x** gap. Retire the
   framing this was filed under: the rope border is **not** one continuous
   stroke the engine shattered — the artwork is ~136 separate chevrons and the
   pipeline consolidates them to 21. Merging every fragment on every thread
   still leaves 98 trims. **69% of trims are intra-shape**, 56 of them inside
   one 2,095 mm² white field with 46 holes whose tatami breaks into 280 runs.
   Stage 2 also splits one flat colour across two threads; the cut survives
   `revalidate_threads`. **UNREPRESENTATIVE of client logos** — theirs carry
   1–3 fill shapes that essentially never cut. *(measured 2026-08-21/22)*

7. **RESOLVED 2026-08-21 — satin silently dropped a bracket's tab** on
   `enthusiast_logo.png` (7.8 mm² bare, D/52 → C/64). *(`_prune_spurs`)*

8. **RESOLVED 2026-08-22 — build-font dropped SVG transforms on most fonts.**
   `mimosa_large` "D": 6,193 stitches into 40.0 x **0.0 mm**. Four fonts, one
   fix. *(`tools/build-font.mjs`, `test/font-transforms.test.js`)*

9. **RESOLVED 2026-08-24 — the photo route escaped its own palette; both
   halves closed.** Region half (#217): `revalidate_threads` masked to the
   palette, out-of-palette → **0**, flat+gradient byte-identical. Shade half:
   the per-shade snap still spent 28/33/38/8 unnamed spools, invisible in the
   UI (that count reads shape `thread_index` — palette-bound; the sewing
   blocks are not). `shade_palette_bind` closes it, **default ON** per
   Kent's 32-job-sheet ruling: cones 43/45/50/14 → **12/12/15/6** (== each
   palette), stops 78→47, 68→45, 75→54, 25→16; (b) declined (+1 cone on face).
   Pinned edge: a one-spool design flattens tone, 5→1. *(PR #217 + 08-24 flip)*

10. **RESOLVED 2026-08-23 — three photo-route robustness defects, every one
    found by the first real photos, none reachable by a committed fixture:** a
    7.4 MP OOM (#214), an infinite loop in `select_palette` (#218), preflight
    condemning correct thread-paint as too loose (#216).

11. **RESOLVED 2026-08-24 — the memory ceiling was per-region full-frame
    masks.** Each of 1,455 components on a 2800x2100 frame carried its own
    (H, W) bool — 8.56 GB at once, ~102 surviving. Cropped to bboxes:
    **8,509 → 1,014 MB** (2,767 → 677 on a real portrait), same region counts,
    19–29% faster, MB/MP now FALLING with size (260→172) where it climbed
    (643→1,705). Correction: the 12.4 GB OOM was contention with a 10.5 GB
    script, **not one job** — a service plateaus at ~2.8 GB. *(PR #230)*

12. **RESOLVED 2026-08-24 — preflight graded every photo job F.**
    `THREAD_MATCH_POOR` fired 256 times at `block` across the sheet: a capped
    cone list guarantees per-thread distance. Now scores EXCESS over the best
    already-loaded spool on the photo route (raw elsewhere, byte-identical) —
    258 of 330 offending regions become 3, and real mis-assignments still
    block. *(PR #229)*

13. **RESOLVED 2026-08-24 — the detail layer sewed the background a subject cutout
    had just removed.** FDoG reads the whole raster, so
    `photo_prep_background_removal` never reached it: on `baby_deck_laugh`,
    **91.4% of the detail block and 72.2% of every stitch in the design** sewed
    removed background. Regions were clean. `SourcePixels.subject_mask` now
    confines the line map — 10,813 → **537**, all inside the silhouette slack.
    Invisible until now because **no acceptance arm had EVER set that flag**; the
    `subject_cutout` arm lands here too — a third default-OFF flag missing from the
    section below, the gap it exists to close. *(measured 2026-08-24 — [area 1](docs/scope/1-auto-digitizing-quality.md))*

14. **OPEN — the photo route leaves half the cloth bare INSIDE each shape.**
    Kent's front as of 2026-08-25, and the first item here about fill QUALITY
    rather than region identification. `stitchviz.coverage`: streamline
    thread-paint covers **0.55–0.59** of its footprint, the blend tier **0.99**.
    Not diagnosed; do not assume the fix is density. *(measured 2026-08-24 — PR #234; [area 1](docs/scope/1-auto-digitizing-quality.md))*

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

- **A photo sews FILLED (~0.99 cov), not as thread-paint (~0.52–0.55).** Lane A,
  answered on renders of both products: *"the left image is WAAAAAAAAYYYY
  BETTER"*. Held on 4 fixtures, mean luminance 0.32–0.60; 3 were run to
  overturn the first and did not. **Not yet acted on:** `auto_photo_tier` still
  routes `photo_subject` to streamline, against this ruling.
  *(ruled 2026-08-25 — Kent; `docs/superpowers/plans/2026-08-25-fill-coverage-team-brief.md`)*
- **Satin borders go on shapes significant AND smooth, never blanket.** *"if
  it's abrupt, it probably doesn't require a border, or is wrong."* On
  `owl_kent`, blanket `border="auto"` spends **+60% stitches to worsen the
  silhouette**; the selective rule takes 4 shapes of 35 for **+4%** at 80 mm.
  Shipped `border="significant"`. Abruptness is the ONLY live gate: measured
  per RING (a thin smooth ring is not abrupt) and it tracks MACRO SPRAWL, not
  edge noise — bordered shapes run 2.09–3.39, refused ones 3.91–12.22, 3.5
  sits in that gap. **The area-share half is disabled (0.0)** — it was inert
  at the 80 mm it was tuned on and at 160 mm deleted 8 of 9 borders at
  4.2–62.3 mm², iris/nostril scale. A fixed share INVERTS with size (bigger
  design → more regions → smaller shares → stricter gate), so re-tuning it
  cannot work; significance is tested downstream by `border_runs` against the
  corpus-measured `BORDER_WIDTH_MM`.
  *(ruled 2026-08-25 — Kent; measured same day — PR #241, corrected #243)*

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
  tree (verified), so tests are honest — but from any other cwd the same
  interpreter imports `.venv/Lib/site-packages/digitizer_core/`, whose files
  differ from both the working tree and `HEAD`. So a service or script launched
  from elsewhere can run code that is not in the repo. Reinstall (`pip install
  -e digitizer`) before trusting any out-of-tree run. *(confirmed 2026-08-17)*
- **Stage 0's `photo_subject` gate is bimodal** — textured subjects on smooth
  backdrops can't reach `photo_subject`. Pinned in the routing test's docstring.
  *(confirmed 2026-08-12 — scope-history)*
- **`stage0_classify._load` treats raw ndarrays as BGR** — A/B probes must
  convert first. *(confirmed 2026-08-12 — scope-history)*
- **A UI affordance that gates on service health fails indistinguishably from
  the service itself.** `.eladd-row` overflow hid "+ Auto-digitize" by 111px, so
  a clipped button read as a dead service and silently routed photo work through
  the browser engine, which emits no pipeline warnings — a full SAM2 on/off
  comparison was run and two result sets published that never touched SAM2.
  Closed for the upload path; remember the *class*. *(confirmed 2026-08-13 — PR #122, PR #138)*
- **Pro-parity scores from before 2026-08-14 are on a different scale and do
  not compare.** `direction` and `sttype` were bounded agreement measures with
  a floor near 0.5, so ~21 of their combined 40 points were paid out for a
  wrong answer; both are now chance-corrected. Any score, table or doc quoting
  a pro-parity number from before that date is reading ~16 points high at the
  corpus level. `score_raw`/`parts_raw` in `score.json` carry the old scale
  when the two genuinely need lining up — reach for those rather than
  re-deriving. *(measured 2026-08-14 — PR #151,
  `tools/pro_parity/scorecard.py`)*
- **Every pro-parity number before 2026-08-15 was measured on artwork
  RECONSTRUCTED from the pro's own stitches, and was flattered by 11.3 points.**
  Honest baseline on Kent's 7 real artworks (15 designs): **42.5**.
  *(measured 2026-08-15 — `docs/pro-parity-real-art-2026-08-15.md`)*
- **The pro-parity 95 target is above the metric's own ceiling. Do not read
  `score/95` as an engine deficit** — and any plan quoting "we need to get to 95"
  is quoting an unreachable number. Two of the PRO's own files for one logo,
  scored against each other on the same scorecard, give **75-84**. The scorecard
  is not broken: on pairs that are one job saved twice it correctly returns
  96-100. But `direction` ceilings at **0.11 on one pair and 0.85 on another**
  from one digitizer on one logo, against a 20-point weight — it measures a
  choice, not a standard, and is the least defensible weight in the scorecard;
  `density`/`underlay`/`travel` ceiling at 0.89-1.00, so those are sound.
  **Deliberately NOT revised yet: n=2.** Growing n needs scale-normalised
  registration in `scorecard.py` (it registers by translation only, and every
  other same-logo PES pair is 4-17% apart in width).
  *(measured 2026-08-15 — `tools/pro_parity/selfconsistency.py`,
  `docs/pro-parity-real-art-2026-08-15.md` §11)*
- **The golden divergence is PER-FIXTURE, not per-platform.** This ruling used
  to say the goldens "fail on Windows and pass in CI, which is where they were
  captured." False for `logo_alpha`. Truth is three-way — rows are
  `flat_lane_byte_identical` and `stage2_photo_segment` unless named:

  | fixture | Windows | CI |
  |---|---|---|
  | `pushcomp[logo_whitebg.png-towel]` | fails | fails (deselected) |
  | both, `[logo_alpha.png]` | **passes** | **passes** (deselect removed) |
  | both, `[photo/enthusiast_logo.png]` | fails | fails (deselected) |

  CI deselects THREE by name, not five: the two `logo_alpha` rows were removed
  2026-08-22 after the remove-and-see check finally ran, and CI went green
  without them. **Consequence:** an `enthusiast_logo` failure locally is
  expected; a `logo_alpha` failure anywhere is a genuine regression.
  Per-platform reasoning gets that backwards. **Still binding: never re-capture
  a golden from a Windows run.** Judge a change by "same failure set before and
  after", using the table as that set. Cause and the deselect rationale:
  `docs/pro-parity-real-art-2026-08-15.md` §0b and the CI workflow's own
  comment. *(measured 2026-08-22 — CI column from a green run at `db0e642` on
  ubuntu-latest; Windows column re-run 2026-08-17 and not since)*
- **OCR tests skip, not fail, without the `tesseract` binary — and never skip
  on CI.** The five real-read tests carry `requires_tesseract`
  (`tests/conftest.py`), which skips only when the binary is missing AND `CI`
  is unset, so a workflow refactor losing the install fails loud instead of
  going dark. The TOTAL skip count is environment-dependent — tesseract, and
  whether `rembg_isolated/venv` is built — so judge it by the per-class
  accounting in COOKBOOK "Running things", never by the total.
  *(measured 2026-08-17; accounting refreshed 2026-08-24)*
- **Breaking a guard on purpose does not prove it is not blind — ask what
  fraction of its population it measures, and assert that.** The stunted-glyph
  guard passed that ritual and was still measuring nothing in **21 of the 85**
  fonts it iterated, and was blind to the exact zero-height case it is named
  for; `qc-font.mjs` had both holes, in the tool that gates new fonts. Full
  account, including why the channels must not be merged, in
  `.claude/memory/font-pipeline-silent-failures.md`. *(measured 2026-08-22 —
  test/font-stunted.test.js, verified against the pre-fix tool)*
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
  work.** What has already been built, measured and rejected here is the
  most expensive knowledge in this repo; phase numbers in any other doc are
  historical — this file is the map. *(moved from ROADMAP 2026-08-19 —
  60-line budget, decision by Kent)*

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art |
| 2. Font library & lettering | Implemented — 85 fonts, satin + bean/running + cross-stitch, LTR + Hebrew RTL | High (tech) / High (compliance). Zero stunted glyphs since the 2026-08-22 transform fix; the guards now assert their own coverage |
| 3. Studio app / guided wizard | Implemented | Medium (fabric-preset accuracy: **pending sew-out** — unchanged, no sew-out has happened). The photo-tier gap PR #123 closed stays fixed; the canvas gained a shape editor and auto-restitch 2026-08-13 |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented — Kent's direct-manipulation request is **complete** (2026-08-13) | High. Every surviving requirement of the 2026-08-12 request ships: outlines+nodes on the canvas, the pulse cue, select-then-edit, node drag, line drag, add node, delete. Requirement 5 (whole-shape drag) was withdrawn by Kent. Geometry is unit-tested and every interaction was driven in a real browser against a live service |

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
changes elsewhere. Both re-measured against pystitch 2026-08-22; PES and EXP are
identity-clean. See `dst-codec-axis-discrepancy` in memory.

**A nuance, reconciled 2026-08-17:** CLAUDE.md's "browser DST is
EMB-Bot-internal only" and `digitizer/README.md`'s "browser DST stays the
default, it has the sewn evidence" are not in conflict — the first is about
orientation elsewhere, the second about which encoder Studio picks.

**CLOSED — the "unreachable from the real product" claim was already false
when written.** Both halves ship: auto-digitized designs leave by pyembroidery
`/export`, lettering/manual stays on the browser codec (the sew-evidenced
combination), and the download step warns before every browser-DST download.
The 2026-08-11 audit's interim mitigation is DONE, four days before
`docs/project-review-2026-08-16.md` §1.1 called it outstanding.
*(confirmed 2026-08-17 — code read, commits dated)*

**Resolution path:** a sew-out or third-party read of a browser-encoded DST;
fixing the codec is Kent's — every existing EMB-Bot DST is affected by a fix.

**The cross-validation harness is ALIVE again — revived 2026-08-21**, its PES
finding (a missing initial positioning jump) fixed in `ef1262b`. It reproduced
the DST transposition exactly (rms 0.0) and caught the broken browser PES/EXP
encoders (PR #58); the 2026-08-11 pystitch swap silently starved it (pass 0 of 6,
green in CI). CI now fails loud when the pins cannot run (`227a9cb`).
*(confirmed 2026-08-22 — engine green, 0 skips)*

**Fifth independent corroboration, 2026-08-10:** Ink/Stitch's `pystitch` —
the format library behind a 20,000+-user tool — uses the identical
low-nibble=X/high-nibble=Y convention, verified against source
(`docs/inkstitch-research-2026-08-10.md` §6). Does not change the verdict or
the fix; a stronger citation, nothing more.

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
question queues behind either a corpus nobody has or a sew-out nobody has
scheduled. Not a reframing of the sew-out gap — a labelled corpus plus a scoring
harness would let a classifier change be judged against *something* before
either arrives. M2/M3 has been blocked on it since 2026-08-01, and the
corpus-law recalibrations needed one-off hand validation for the same reason.

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture`/`diff`
over 14 fixtures × 2 configs, aggregating preflight's existing score rather than
inventing a metric. Deliberately a REPORTING tool, not a CI gate. Build detail,
verification and scope limits: [area 1](docs/scope/1-auto-digitizing-quality.md)
("The two evaluation harnesses"). *(confirmed 2026-08-21 — area 1)*

**Still open: `summit_badge.png` (#6.2) alone** — F/0 at both configs and
SATURATED, so judge any fix on `thread_worst_delta_e`, never score.
*(measured 2026-08-21 — area 1)*

**The corpus half is no longer empty (2026-08-15).** Eight files of real
customer artwork ship in `FIXTURES` — the first entries neither synthetic nor
hand-picked. They contradicted the synthetic set at once: **stage 0 routes six
of the seven logos to the GRADIENT lane**, because real logo art carries JPEG
ringing, anti-aliased edges and soft shading the synthetic fixtures lack — so
any "flat spot-colour art" claim tuned only on synthetics is untested against
real input. `logo_script_tires.png` (a clean two-colour wordmark on white)
classifies `photo_scene` outright — a misroute kept so the bug has a fixture.
*(measured 2026-08-15 — `tools/corpus_scorecard.py:FIXTURES`)*
This does **not** close `scratch_corpus/`: cloud sessions still can't reach those
37 files (Waiting on Kent #7). **Kent's four real portraits (2026-08-23) are the
first tonal entries** — gitignored, machine-bound, invisible to CI.

**A second harness exists: `tools/pro_parity/`** — how close our output is to
the PROFESSIONAL digitization of the same design, 23 designs, six weighted
components. **Its scale changed 2026-08-14** (chance-corrected floors); see the
Gotcha above before comparing to any earlier number. *(confirmed — PR #151)*

**Half the corpus is in the repo; the half that matters is not.** The tracked
`Embroidery Files.zip` carries all 23 pro STITCH files, so `prep_all.py`'s
recon lane runs from a fresh checkout (extract outside the tree, set
`PRO_PARITY_ROOT`). It carries **zero customer artwork**, so `prep_both.py`'s
real lane — the one behind the 42.5 baseline — still needs the Drive copy.
*(corrected 2026-08-18 — prep_both from the zip fails 0/15 on
FileNotFoundError; an earlier edit that day claimed the whole corpus was
reachable and was wrong)*

**Area 1 is deliberately NOT split into "image analysis" + "stitch
planning",** and the four capability gaps an external review named
(quantization, segmentation/vectorization, background removal, small-detail
culling) all have owners in code. Both arguments live in [area
1](docs/scope/1-auto-digitizing-quality.md) ("Why this area is not split in
two"). *(moved 2026-08-21 — rule 5)*

### Research backlog — competitive and open-source leads

Two capability sweeps produced backlog items rather than status changes:
Ember Design (`emberdesign.net`, a browser-based competitor) and Ink/Stitch
(the open-source Inkscape extension). Both catalogues, plus the closed
`simplify_tol_mm` investigation they generated, now live in
[`docs/scope/research-backlog.md`](docs/scope/research-backlog.md).

Nothing in there is a commitment or a defect. Two things from it that DO bind:

- **Ink/Stitch is GPL-3.0** — concept-level clean-room reimplementation only,
  no literal copying or near-verbatim translation. The exception is
  `pystitch`, its MIT-licensed pyembroidery fork, which is usable as a real
  runtime dependency and has since been adopted.
  *(confirmed 2026-08-10 — `docs/inkstitch-research-2026-08-10.md` §0)*
- **A sixth independent source corroborates the DST axis bug.** pystitch was
  fifth; TurtleStitch's `encodeTajimaStitch()` — unaffiliated with the
  pyembroidery/Ink/Stitch lineage — is sixth. No verdict change.
  *(confirmed 2026-08-14 — `docs/turtlestitch-stitch-appearance-research-2026-08-14.md`)*

---

## Capability areas

One verdict per area. **The supporting detail lives in
[`docs/scope/`](docs/scope/)** — one file per area, linked below. Status and
Confidence here must agree with the At-a-glance table above; if they ever
diverge, fix both rather than picking one.

### 1. Auto-digitizing quality (image → stitches) — [detail](docs/scope/1-auto-digitizing-quality.md)

**In progress · Low confidence beyond flat spot-color art.**
Covers both implementations as one capability: the browser JS engine (complete
but frozen — retired in favour of "feed it clean flat art", not because it is
broken) and the Python pipeline, which is the active target. Stages 1–7, fill +
satin, the service, preflight scoring and the review UI are all built. SAM2 is
merged and reachable from Studio via the `embstudio:sam2` dev seam, still
`photo_segment_sam2=False` by default.
**The corpus constraint is half lifted 2026-08-23.** Kent's four real
portraits ran the five-arm sheet and found four defects no fixture had (see
defect 8). They stay gitignored (spec decision 6) — evidence is machine-bound
and committed `photo_*` fixtures are still synthetic stubs, so SAM2's quality
remains undefended by anything a CI run can see. *(ran 2026-08-23 — sheet)*
**Satin extremity drop — FIXED 2026-08-21.** `_prune_spurs` re-measured a stem
its OWN first pass had un-branched, one raster pixel deciding a 3.3 mm tab;
fixed by exempting a dead end the function itself created, D/52 → C/64. Same
cascade was mangling block letters in `textcluster.py`. **The blind spot that
hid it stays fixed:** `preflight`'s `ARTWORK_UNCOVERED` (`polygon ∩ ink`),
5.0 mm² threshold still provisional. *(fixed 2026-08-21 — PR #186)*
**Next:** NEEDS KENT. The fragmentation work finished 2026-08-22 and measures
**0% on real client logos** — PR #205 is byte-identical on all six (they are
satin-dominated, 1–3 fill shapes, no cutting fills). The one large real-artwork
lever is **`chain_links`: −33% trims AND fewer stitches**, gate-1 frozen; every
gate-clear alternative measures ≤9%. *(measured 2026-08-22 — area 1 detail)*

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
content path, and four export formats.
**What holds it at Medium:** fabric-preset accuracy is sew-out-gated, and no
sew-out has happened. See Cross-cutting issues.

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
