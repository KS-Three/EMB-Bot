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
standing rulings in [`DOCTRINE.md`](DOCTRINE.md). **The code and instruments it
describes are ON `main`**
— PR #157 merged (`4967ed5`), so `digitizer/tools/pro_parity/` including
`selfconsistency.py` is in a plain checkout.
*(confirmed 2026-08-17 — `git ls-tree origin/main`)*

**Last updated:** 2026-09-02. **This file is current state only, under an
800-line budget.** Its three companions: standing rulings, rejected approaches,
corrections and session-costing traps live in [`DOCTRINE.md`](DOCTRINE.md);
dated snapshots in [`docs/scope-history.md`](docs/scope-history.md); per-area
supporting detail in [`docs/scope/`](docs/scope/). See "How this document works"
at the bottom for the rules that keep them apart.

**Every claim below carries a pointer** in the form
`(verb date — source)`: `confirmed` means checked against code or a passing
test, `measured` means a number was produced, `suspected` means neither. Treat
a claim with no pointer as unverified — and if you find one, either verify it
or move it.

---

**FIRST PHYSICAL STITCH-OUT 2026-09-01 — thread has met cloth.** Kent's
Instagram icon at 80 mm, 6/10; the full measured record is scope-history
2026-09-01 and memory `first-physical-sewout-2026-09-01`. Gate 1 still
stands — constants wait on the sew-out CARD's controlled blocks, not this
icon. Cloth pointers added to defects 3, 6 and 16 below.

## Live defects — believed true right now

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

4. **We trim far more than the professional — 3.1x the trim breaks on a
   like-for-like corpus.** (Absorbs retired defect 3's live concern; a real
   80 mm datum now exists — the 2026-09-01 sew-out icon at 26 trims / 7
   stops, pinned to an actual decoded file rather than to a number nobody
   could reproduce.) Quote the rate or the break count, never a run
   count and never raw `trims`. **Cause: trim policy, not travel** (ours 3.0; gate 1 says cloth settles it) — but **"the pro never cuts under 11.8 mm" stood here and is WRONG**, corrected 2026-09-06: that is `becker_hat_small` alone, while the 23-design 910-move corpus (`.claude/memory/pro-trim-threshold.md`) has **542 cuts, min 1.9 mm** beside 368 floats to 16.1 — heavily overlapping, so **no single threshold reproduces this pro**, which is the real reason not to retune it (our five Becker refs cut all 69 moves, shortest 3.9). `_graph_travel` stays RETRACTED as the cause and was re-measured 2026-09-06: it fails because travel may only cross UNSEWN strokes, "no route" on every call from 45% of a 27-stroke shape on (DOCTRINE). Not blocked: five pro variants sit in `testdata/reference/`.
   *(2026-08-15/18/21, corrected 2026-09-06 — `docs/fragmentation-attribution-2026-08-18.md`, scope-history 09-06)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   The *mix* looked close by AREA; by THREAD it is not (2.2% against 44.3% —
   corrected 2026-09-04, DOCTRINE). **Partly closed, and the
   remainder is NOT the classifier: it is SEGMENTATION.** An oracle knowing
   the pro's per-shape answer scores 76.6% against our 55.4% — our regions
   straddle the pro's satin/fill boundaries. `docs/segmentation-alignment-
   2026-08-17.md` recommends NOT building the region-level fix (the straddle
   is 95.8% grid noise). **The per-stroke rung was BUILT INERT 2026-09-05 and WIRED behind the flag 2026-09-06** (`stage6_satin.classify_strokes` still has no caller; the pipeline consults the same reading via `_stroke_rung_takes` — do not read "inert" as current): at the bare ≥ 0.75 area rule it reproduces the plan's Becker @ 100 mm 274.0 → 1,708.3 mm² exactly — but that rule is NOT what shipped (see the cap veto below, which cuts it to **3 regions, 78.8 mm²**); it adds 5.7 mm² at the corpus's own 80 mm (Becker is ALREADY 88.2% satin there) and +143.8 mm² over 14 fixtures. Becker's 17 regions sit ON the `cv = 0.50` gate — 11 within ±0.10 at 80 mm, 16 at 100 — so its satin share is a segmentation coin flip, not an artwork property (scaling a fixed polygon 1.25× moves cv < 0.02). Its real value is decisiveness (median |cv − 0.50| 0.154 per region vs 0.221 per stroke; knife-edge share 40.9% → 24.7%), and it MUST be promotion-only or it demotes 15 regions incl. one of 638.8 mm² (DOCTRINE). **The flag exists since 2026-09-06 — `cfg.satin_per_stroke`, DEFAULT OFF, byte-identical off** (threaded to all three call sites; the rung sits on the `dt_irregular` branch alone so the machine cap and Law 31's floor stay out of its reach). **The machine cap is a VETO in it, not a vote** — the render caught the first cut leaving 28.0 mm² of bare cloth (a 9.32 mm stroke sewn as capped satin, DOCTRINE's measured negative). ON, measured on the stitches: Becker @ 100 mm goes **B 88 `DENSITY_EXTREME` → A 100 with no findings**, uncovered 0.0 both ways, crossing 2.2 → 4.0%, median column 0.29 → 0.64 mm (**a whole-plan figure and 80% tatami turns** — our SATIN runs there measure 3.82 mm median, p90 4.93, against the pro's 2.52/5.00; read our widths off `satin_columns.py`'s second row, DOCTRINE 09-06), 11,374 → 11,206 stitches, and satin **75.2 → 154.0 mm² — 3.5% → 7.2% of the 2,125.6 mm² that actually SEWS**, which is the only honest denominator here: 1,462 mm² of Becker is `BACKGROUND_ENCLOSED` and never becomes thread, so every "% of region area" quoted for this rung (the plan's 7.6% → 47.6% included) divided by shapes the plan leaves open (DOCTRINE, 2026-09-06). Modest, and honest — but the gap's old diagnosis is WRONG: **the pro's own p90 column is 5.00 mm** on `beckers_logolc.dst`, which is 95.7 × 58.3 mm, i.e. the same artwork at our test size, so the 5 mm cap is not what separates us and raising it is not the path (DOCTRINE 09-06). What differs is how few shapes reach the tier — ONE at 100 mm — and the columns we do sew are already professional width. **Segmentation, full stop.** Separately, and now FIXED behind a flag: **100% of that fixture's `ARTWORK_UNCOVERED` at 80 AND 90 mm is inside SATIN shapes** — the crotch of the K (37.2 mm² at 80, 32.2 at 90) and an R, where arms meet and no cross is placed. **`cfg.satin_patch_junctions`, DEFAULT OFF, byte-identical off** (2026-09-06): sews what the emitted thread missed, as tatami under the shape's own id, and takes uncovered **23.8 → 0.0 mm² at 80 mm and 44.5 → 0.0 at 90, B 76 → B 88**, for +7-8% stitches — and clears the corpus's only other positive too (`photo_scene_stub` 6.5 → 0.0, +2%), i.e. **30.3 → 0.0 mm², 100% of the bare cloth in SATIN shapes**. Corpus A/B at 80 mm: **23 of 26 fixtures byte-cost-identical, +0.25% overall**, with one over-fire (`logo_bridge_bar` +59 st at 0.0 uncovered both ways — this pass is deliberately stricter than the grader). It cannot reach the corpus's two LARGEST uncovered figures — `photo_subject_stub` 956.0 mm² (23.4%, D 58) and `photo_grass_macro` 407.5 (8.9%, B 76) — and does not need to: both are baseline AND the parked thread-paint ruling (`photo_subject` routes to `streamline_fill`; coverage p50 0.49/0.54, inside DOCTRINE's 0.52-0.59 band). Four cross-LENGTH knobs were measured first and none reached it. Flipping it is Kent's — the patch's tatami sheen inside a satin letter is a look question (render: `docs/renders/junction-bare-2026-09-06/`). The p90 gate IS blind to a tail — `promoted_ribbon` admits `Sead76620` at p90 2.67 mm whose width maxes at 7.80, 2.8% of the spine over cap — but that tail is NOT the cause: lifting `_rail_points`' 5 mm ceiling to 99 moved uncovered 23.8 → 22.8 mm² for +13% stitches, and `satin_rails_follow_edge` only to 21.0 (DOCTRINE 09-06, hypothesis refuted the same day). @ 80 mm byte-identical (Becker already reads 54.5%, above the pro). **Flipping it ON is Kent's — render at `docs/renders/satin-per-stroke-2026-09-06/`.** *(measured 2026-08-14/17, 2026-09-05/06 — `docs/satin-gate-attribution-2026-08-16.md` §9; plan §PR 2)*

6. **Satin fragments into many small islands on real logo art — and the trim
   bulk is INSIDE one shape, not between them.** 69% of trims are
   intra-shape. Retire the old framing: the rope border was never one stroke
   the engine shattered — the artwork is ~136 separate chevrons. **And it is
   UNREPRESENTATIVE of client logos**, which carry 1–3 fill shapes that
   essentially never cut. **On cloth 2026-09-01:** the first sew-out's tail
   is exactly this — late satin fragments riding over pre-sewn work, jump-
   chains stepping 8–11.5 mm. *(measured 2026-08-21/22 — area 1; cloth
   2026-09-01 — scope-history)* **Seams, 2026-09-03:** `tools/seam_underlap.py` reads the sewn underlap per colour pair — synthetic logos carry the full pull + 0.25, Hotel Fremont 0.24 mm mean over 1,549 mm of seams (673 mm under 0.25) because a hole held open at the detail floor gets no tongue; card block 6 (0 / 0.25 / 0.5 / 1.0) sets the number on cloth. *(measured 2026-09-03 — scope-history)* **The 69% is now a CORPUS number and `TRIM_HEAVY` finally says it (2026-09-06).** Across 26 fixtures at 80 mm: **866 trims, 456 inside a shape (53%), 410 between (47%)** — and the majority flips per design, in-shape on 11 fixtures and between-shape on 11, from `photo_grass_macro` at 93% in-shape to `logo_alpha` at 100% between. So the finding's one remedy (*"merge or remove the smallest shapes"*) was right about half the time and pointed at the wrong end of the design on the other half. It now emits `in_shape`/`between_shapes`/`shapes` and says which. Becker reproduces the August figure independently — 19 of 28 (68%), the 1-point gap being the file's first cut, which does not exist. `tools/trim_locality.py`, `tests/test_trim_locality.py` (9). *(measured 2026-09-06 — scope-history 09-06)*

15. **An UNDECLARED photograph gets neither depth sequencing nor the palette
    bind, and its region re-snap escapes the selected palette.** `is_photographic`
    gates the fix and is DECLARED, not detected — `owl_kent.jpg` reads LESS
    photographic than two logos, so a photograph left undeclared routes
    gradient and the re-snap sews more spools than the cone list names. **Counted 2026-09-06** (`digitizer/tools/resnap_escape.py`): **34 cones added corpus-wide, 25 outside the selected palette, every escape on the GRADIENT lane** — screenshot 7, drone 5, bridge_bar 5, golden_tee 4, gaulke 3 — while all nine photo-class fixtures add none. The binding works; the lane real logo art routes to never got it. **PRICED, NOT FIXED** (`cfg.bind_resnap_all_classes`, DEFAULT OFF, byte-identical off): binding every class removes **19 colour stops across five designs** (drone 19→14, bridge_bar 18→14, screenshot 16→11, golden_tee 16→13, gaulke 6→4; gaulke also −10.9% stitches, drone +3.1%) and costs **+2 blocks net** — screenshot 10→8, golden_tee 2→5, bridge_bar 3→4. **It is NOT a raw-yardstick artefact:** forcing the excess yardstick (probe, reverted) still gives golden_tee D 52→F 22 and drone D 40→F 28, the latter with no thread block moving, so part of the price is the extra stitches. The escape is the pipeline BUYING colour accuracy with unplanned cones. **I would not flip it on this evidence** — the value is the price tag. *(measured 2026-09-06 — `tests/test_bind_resnap_all_classes.py`, 13)* **A benefit the price tag did not have, added 2026-09-06:** binding also removes a SPOOL REVISIT on real customer artwork. An undeclared cone can only exist because this escape put one there, and nothing rejoins the regions that land on it (defect 18's third mechanism) — `screenshot_phone_ui_golke` goes **17 blocks / 16 distinct with `3971` sewn twice, to 11 / 11 with no duplicate**. That belongs on the credit side of this trade. *(measured 2026-09-06 — scope-history 09-06)*
    **UI HALF FIXED 2026-09-02 (Kent's call):** the reading row's "It's a
    photo" correction now sends `is_photographic` instead of
    `forced_class="photo_subject"`. It was answering the wrong question —
    forcing the FILL TIER rather than declaring content — and measurably
    hurt: owl_kent @ 80 mm goes 13 stops → **17** forced, vs **11 on 12
    cones** (from 14) declared, for ~6% more stitches. The flat-art override
    is untouched; only the photo direction moved. **Still open:** detection
    itself — gate 2 bars inferring it, so an undeclared photo is still
    undeclared until a human says so. *(measured 2026-09-02; the earlier
    26-stop figure for the forced route predates the rehome, borders-last
    and the cone fold — 17 is current, the ordering it was cited for is not)*

18. **Duplicate quantize-time declarations put one cone in two layers — the
    second spool-revisit mechanism, untouched by defect 16's fix.** Stage 2
    quantizes to COLOURS, so two can snap to one cone: `drone_render` 80 mm
    declares 21 slots holding 17 threads, the smaller sewing late over
    finished work. **FIXED, DEFAULT ON** (Kent, 2026-09-01):
    `cfg.merge_duplicate_cones` folds each into the FIRST layer declaring its
    cone, upstream of stage 5 so coverage/seams derive from the merged order.
    Blocks 19→17, revisits 2→0, needle-up 1295→1237 mm, no golden moved.
    *(2026-09-01 — `test_duplicate_cone_layers.py`, 13)* **A THIRD mechanism is open, found 2026-09-06 by `COLOR_STOPS_HEAVY`'s new `repeated_cones` field: 4 of the corpus's 52 design/garment combos still sew a cone in more than one block WITH this fold ON**, by two routes it cannot see — `region_blobs` sews `0182` in two blocks that are each a gradient BLEND BAND from a different parent (`Sb971b1c2-blend2`, `S0ad9734d-blend4`; a band is not a layer declaration), and `screenshot_phone_ui_golke` sews `3971` in two blocks of plain regions that all carry `thread_resnapped_de00` in layers 2 and 8 — i.e. the duplicate is created by `revalidate_threads`, not by stage 2's quantize, which is the only thing this fold addresses. Each costs a real machine stop and each merge is FREE (the cone is already loaded). Recorded, not fixed: extending the fold to bands and to re-snap output is a sequencing change owed its own measured work. The finding now names it to the operator. *(measured 2026-09-06 — scope-history 09-06)* **SPLIT AND HALF-CLOSED the same day.** The re-snap half needs no new code: `rehome_resnapped_regions` refuses a cone no layer declares (its docstring: *"there is no 'home' to send it to"*) and this fold works on that same quantize-time list, so an invented cone is invisible to both — verified, `3971` is declared by none of `screenshot`'s 13 layers. `cfg.bind_resnap_all_classes` (defect 15) removes it outright, so fixing the rehome would add a SECOND switch for a cause the first already prices. **Still open: the blend-band half** — `region_blobs` sews `0182` in two bands of different parents, built in stage 6 long after this fold, and unchanged with the bind ON. One synthetic fixture; any fix is a sequencing change. *(measured 2026-09-06)* **PRICED 2026-09-06 (`tools/cone_revisits.py`), and "each merge is FREE" is true of THREAD cost only:** across 26 fixtures × 2 garments the four duplicates sit at block gaps of **7 and 11 — NOT ONE is adjacent**, so every remaining fold is a reorder through `covered_by`, which `cone_merge_survey.py` already measured as the expensive across-layer case. Both halves re-confirmed by re-running with the flag rather than on the record: `screenshot` 17 blocks → **11 with the duplicate gone**, `region_blobs` 16 → 16 with it intact. So the open half is **one GENERATED fixture** (`make_photo_region_fixture.py` — three Gaussian blobs) at an 11-block reorder, against a flag already built that closes the other half and buys `screenshot` six blocks. That is the case against building the band fold, in numbers. `tests/test_cone_revisits.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

19. **The design's own outer edge is uncapped — every fill row ends in open
    air.** The other sew-out edge finding, and one no per-shape border can
    reach: the silhouette is the union of several shapes' edges, so the
    design/fabric boundary is nobody's. On Kent's icon, **100% of the 293.2 mm
    outer silhouette uncovered at 1.0 mm** vs 0.0% on the glyph edge he rated
    flawless. **FIX BUILT, default OFF, both styles opt-in:** `cfg.edge_cap` —
    `"bean"` traces it, `"satin"` lays a column just inside, one design-level
    block after all artwork in a thread already loaded. No new constant (gate 1
    clean); Studio exposes **Design edge**.
    Icon: bean +12.6%, satin +15.3%. KNOWN LIMIT: cost scales with silhouette
    FRAGMENTATION, not size — `drone_render` caps 38 parts / 78 holes for
    **+56.9%**, a whisker off DOCTRINE's blanket-border negative, and there
    satin (+34.9%) is cheaper. Bills every run as `EDGE_CAP_APPLIED`.
    **A sew-out settles which cap, if either.**
    *(built 2026-09-01 — `tests/test_edge_cap.py`, 18 passing)*

20. **Photo tonal splitting stacks thread past the pucker ceiling.** The bill
    for the ratified spec-decision-2 flip (`d3f3c547`), found only because the
    stale baseline remembered the before. `photo_scene_stub` `coverage_max`
    **4.40 → 6.44** on that commit, **7.18** today against a 3.5-layer ceiling
    — a `DENSITY_STACKED` **block** on a fixture that scored 64. Lane-wide:
    `photo_dof_meadow` 3.45 → 5.04, `same_hole_fraction` up **4–7x** — the
    needle-breakage signal. ~~No off switch for photo classes~~ — stale when written; it landed 2026-09-01 (PR #316), so **the other half is measured: the tier costs −22,352 st / −16.4% of the photo lane and with it OFF four of nine score HIGHER, none lower** (B 88, B 88, A 100, A 100), coverage_max falling wherever it moves. **A yardstick finding, not a flip** — nothing in the scorecard scores tonal gradation, and Kent ratified the tier (spec decision 2). Detail: `docs/scope/1-auto-digitizing-quality.md`. *(2026-09-06 — `digitizer/tools/tonal_split_ab.py`; 2026-09-02 bisect, [notes](docs/scorecard-baseline-attribution-2026-09-02.md))* **Numbers above are in the pre-2026-09-03 coverage base** (one 0.40 fill = 1.0); since the fill row moved to 0.15 the same stack reads 8.0 against a 9.33 block / 6.67 warn, i.e. a warn — the thread is unchanged, the ruler is in fill layers now (scope-history 2026-09-03). **The re-base left old-base numbers in the PROSE, and four were found and fixed 2026-09-06** — `preflight`'s module docstring said "1.0 is one full covering layer" (it is one 0.40 mm ribbon; a fill lays 2.67), `_coverage_findings` named `COVERAGE_WARN_UNITS`/`COVERAGE_BLOCK_UNITS` and gave their values as "2.5 and 3.5" when they evaluate to **6.67 and 9.33**, and two `test_preflight.py` docstrings quoted 3.00 and 3.5 beside assertions computing 8.00 and 9.33. **And the check has never fired on real artwork:** swept over all 26 fixtures, `DENSITY_STACKED` fires on **0 of 52 combos** — six carry a peak over the warn level (`photo_dof_meadow` 7.97 the highest, still under the 9.33 block ceiling) and every one yields **0.0 mm² of qualifying patch**, so `_COVERAGE_MIN_PATCH_MM2` is doing all the work and the synthetic `_stacked(n)` plans are the ONLY exercise a block-severity check gets. It now emits `patches`/`worst_patch_mm2`/`worst_patch_at_mm` — the "where" its own message always asked for and discarded. `tests/test_stacked_where.py` (6). **And the SAME row change silently recalibrated a second check**: `SAME_HOLE_HEAVY` scores repeat points over total penetrations, so the 0.15 mm row grew its denominator — A/B'd at both pitches, penetrations **×1.17–2.30**, repeat points ×0.98–1.15 (28 vs 28 on `logo_whitebg`), rate **×0.43–0.83**, and `max_strikes` **identical on all four fixtures**. Its docstring's "our benchmark is 9.8%" is old-base and now reads ~2.7%; the corpus runs 0.001–0.103 and it fires on **0 of 26** against a threshold set as "far above" 9.8%. Gate 4 in miniature. `SAME_HOLE_RATE_MAX` deliberately NOT retuned (its baseline is pro files at their own pitch); fixed by emitting the density-invariant half — `max_strikes`, `points_3plus`, `worst_at_mm`. `tests/test_same_hole_depth.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

21. **Fill travel is laid OVER columns already sewn — FIXED, DEFAULT ON (Kent's flip
    2026-09-03)** (`cfg.fill_travel_under_cover`, PR #323): the column order prefers a next
    column reachable over unsewn ground (`_reorder_for_cover`, cuts × 25 + travel + exposed × 2,
    never worse) and an exposed bridge routes through unsewn ground. Fill-phase exposed travel
    Fremont **286 → 90 mm** (trims 47 → 52), gaulke 204 → 8, drone 546 → 89, sunset 711 → 344
    (**53 → 42**), meadow 691 → 324; OFF md5-identical; +7–11% time on logos, +49–67% on the 263-run photo fill. *(measured 2026-09-03 — `docs/fill-travel-under-cover-2026-09-03.md`)* **Residual, not zero:** with the flag ON the three review logos still lay 32–39% of their fill-phase travel over sewn fill (Becker 55.8 of 148 mm, Bridge Bar 75.8 of 194, Fremont 59.6 of 185 — `fill_exposure.exposure(plan)` at the Studio configs); the run across Becker's N is one of them. *(measured 2026-09-03 — `docs/kent-review-2026-09-03.md`)*

22. **Small curves sew as polygons — FIXED, DEFAULT ON (Kent's flip, 2026-09-03)** (`curve_turn_deg` = 15; None/0 = the old polygon): a turn-per-vertex bound re-reads each Douglas-Peucker edge against its raw arc, split at the midpoint, floored at one pixel; near-floor lettering exempt per ring. Fremont's counter **9 → 33 vertices, 47° → 17°**, inner rail σ 0.038 → 0.026 mm, trims 52 → 45. **Gated to 20 px/mm** (`_CURVE_MIN_PX_PER_MM`; four pixels of tolerance at 0.2 mm): below it the 1-px floor read raster texture as arcs — every 10–16 px/mm fixture got rougher (sunset 16.1 → 16.5, meadow 15.2 → 16.5) and two borderline ribbons changed tier through the DT classifier's skeleton — so a 600–1200 px web logo at 80 mm is byte-identical and every golden stays pinned — but 1200 px art at ≤ 60 mm (2000 px at ≤ 100 mm) is over the line and refines, and the line is a cliff (60 → 61 mm changes every curve's polygon; Kent's to accept); `tools/curve_tiers.py` is the per-shape tier diff. *(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

23. **Rail dents — FIXED (Kent, 2026-09-03), diagnosis corrected.** `place` stepped an overshooting rail in by 15% however small the overshoot (250–1000 placements per design, 70–90% under one pixel) and now puts it on the artwork edge along its own normal, with a micron of containment tolerance; taper zones and caps keep the ladder. Rail jitter p50 **halves on every fixture** (Fremont 0.012 → 0.0045 mm), same-rail holes 11 → 5, median rail 0.02–0.08 mm further out, nothing further outside the art. The "one whole rail 15% short in every golden" was the synthetic bar, not the goldens (the micron alone moved 4 stitches on Fremont); the 8–24% of rail points > 0.1 mm inside on real art turned out to be the short-stitch guard, corridor caps and corners, not the rail model — the honest coverage number is BARE SATIN AREA, and each rail reaching its own edge (`satin_rails_follow_edge`, **BUILT, DEFAULT OFF, Kent's flip**) takes it Becker 8.6 → 5.8%, ENTHUSIAST 5.7 → 4.4%, drone 6.1 → 4.6% for +10–17% thread, +50% rail jitter and more guard retractions; the pull comp was tuned with the far rail short — a sew-out question. Goldens re-pinned in #329: alpha, ribbon ×3. *(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md`)*

24. **Hairline columns (< 0.6 mm) — the MECHANISM is fixed, the tier is not.** A hairline STRETCH of a stroke (crosses under the 0.5 mm floor, ≥ three bean stations of spine) now sews as a 3-pass bean along its spine in both engines, only where the uncompensated art is wider than `simplify_tol_mm` (pull comp grew a 0.04 mm needle into a tick); Fremont's 2.6 mm "THE" reads. Whether a 0.5 mm bean reads better on cloth than a dropped bar is card block 5's question — `pending sew-out`. *(fixed 2026-09-03 — `docs/design-review-fine-lettering-2026-09-03.md`)*

25. **Fill stitches HALVED by float dust at the stitch-length threshold — FIXED (Kent, 2026-09-03).**
    `split_long_moves` split a 3.0000000000000004 mm grid step into two 1.5s; a micron of tolerance
    (`stitches.SPLIT_TOLERANCE_MM`) removes them: whitebg 2162 → **1982** st, Fremont 6365 → **5789**, sunset 11614 → **10416**, no row or trim moves. Goldens re-pinned (whitebg, alpha; pre-change tree). `tools/fill_dust.py`. *(fixed 2026-09-03 — same doc)*

26. **Satin/fill classifier flips borderline shapes under boundary detail — MEASURED NEGATIVE on eight cures, intrinsic to the thresholds (2026-09-03).** 5 of 219 DT-judged verdicts flip when only the polygon's detail changes (4 on a threshold edge: cv 0.5, aspect 3, `explained` 0.80); spur pruning ×3, the sewing spur rule, a hybrid, raster smoothing ×2 and a regularity band leave 3–12 flips and change 2–48 shipped verdicts, so nothing ships; the mitigation is `_CURVE_MIN_PX_PER_MM`. Open only as a different construction (a margin with memory, or a polygon-native width profile) — Kent's call. `tools/ribbon_stability.py`. *(measured 2026-09-03 — `docs/classifier-stability-2026-09-03.md`)*

27. **Compression halos become their own cones — and the flat lane has dissolved them all along.** `stage2_quantize._quantize_population` runs "majority filter, then phantom-blend dissolve" and its comment records the bill without it ("two extra pale threads, plus ~30 sliver regions"); `Prep.bg_edge_rgb`'s docstring says it again. **The SLIC+RAG lane never got that pass** — so the defect is a missing PORT, not a missing idea. `logo_bridge_bar.jpg` (400 px JPEG, four ink colours) pays it in six grey cones — Cobblestone, Whale, Skylight, Saturn Grey, Silver, Umber — sewing the ringing around its black spokes. **FIXED, DEFAULT OFF** (`cfg.dissolve_phantom_blends`, `stage2_photo_segment.dissolve_phantom_blends`): a merged label that is more than half boundary AND a Lab interpolation of its own two adjacent sides folds into the side it is nearer, the page included, so the rebuilt edge lands at the step's midpoint instead of growing every shape by the halo stack. Bridge Bar 74 → **32** regions, 14,607 → 11,524 st, **114 → 64 trims**, silhouette −4.2%. Read the cone count (13 → 11) LAST: five of six greys go, all four real cones survive, and three NEW cones arrive on artwork the palette could not afford — what changed is what the cones SEW, measured by the palette's worst excess, **20.76 → 3.68** dE00. Residual: 0111 Whale survives as 12 shards, 0.7% of the design, cause not established. `tools/halo_spools.py` bills it — 44 halo regions before, 2 after — and across eleven fixtures finds halo cones on bridge (4), golden_tee (1) and gaulke (1) and NONE on the other eight, Becker (1.5 px/mm PNG, many thin features, no compression) included: the test is specific to compression, not to thin features. Corpus A/B, PRE-FIX and superseded: *"ten of fifteen fixtures byte-identical, gaulke a second clear win (blocks 4→3, trims 30→18), two mild negatives (golke +2 trims, tires +1)"* — the gaulke win was the lettering being deleted. **Post-fix, 26 fixtures, 2026-09-07: 22 byte-identical and FOUR move** — bridge_bar (14,338→11,506 st, **125→62 trims**, 18→12 blocks and cones), screenshot (71→**66** trims, 17→15 blocks — the "+2 trims" negative reversed), golden_tee (+24 st, trims flat), tires (+1 trim). **gaulke is byte-identical now**; it is no longer on this flag's credit side at all. **Kent has SEEN the render and ruled: leave it OFF and bank it** (2026-09-04) — not pending his eyes any more, deliberately parked. **That gaulke grade is RETRACTED as evidence (2026-09-06).** It read **F 0 → C 64 … the difference between "do not sew" and a usable design**; measured on the cones rather than the grade, the C 64 is a design that DROPPED ITS LETTERING: gaulke is black text on a white label, `off` loads `1375 Dark Charcoal` (L* 15.9, 288 st), and the flag leaves `0015`/`4071`/`0145` — **nothing darker than L* 85.7 on a white ground**. The only arm that loads real Black (`bind_resnap_all_classes`, `0020`) grades **F 16**. `THREAD_MATCH_POOR` grades per thread on its worst patch, so deleting the dark cone deletes the badly-scoring thread — the metric rewards not sewing the hard part (flip sheet). **That last conclusion is itself RETRACTED (2026-09-07)**: it shipped as yardstick-disagreements row 7, and it was the bug's artifact, not the metric's preference. Post-fix every gaulke arm loading real `0020 Black` grades HIGHER (F 16) than every arm that does not (F 4), and across seven arms × 26 fixtures **ten (arm, fixture) pairs remove a cone and not one scores higher** — all ten on fixtures at exactly 0, where the floor (defect 28) makes the question unanswerable on this corpus. What survives is the RULE that caught the bug: on a fixture where a flag removes a cone, read the cone list, not the grade. **CAUSE FOUND AND FIXED 2026-09-06 — one line, and the regression is gone.** `valid` inside the pass is `base_valid`, which already has the ENCLOSED pixels removed, so `~valid` is NOT the page: it also covers donut holes, letter counters and the inside of a label. Gaulke is black lettering on a white label on a black canvas, so reading `~valid` as the page told every letter it bordered the near-black background — its colour genuinely lies between that and the label's L* 98.8 ground — and the page endpoint DELETES rather than recolours: **12,961 px, 50.3 mm², the 21.0 mm² wordmark included, dropped to background.** The pass now takes stage 1's real background (`page_mask`). **Costs the flag nothing:** bridge_bar keeps 125 → 62 trims and 18 → 12 blocks, screenshot still 71 → 66 trims, gaulke byte-identical, and no grade moves either way. (An intermediate note here retracted the fold as the cause; that retraction was wrong — the probe behind it counted only relabelled pixels and a page-dropped label keeps its label. `tests/test_phantom_blend_photo.py::test_an_INTERIOR_band_is_never_sent_to_the_page` pins both directions.) The flip is a one-line default plus a 26-fixture scorecard recapture, to be decided alongside other gradient-lane work; his stated reasons for not flipping on the day were the two mild negatives and the five-of-six residual. *(measured 2026-09-04 — scope-history 09-04; `tests/test_phantom_blend_photo.py`; `docs/renders/halo-dissolve-2026-09-04/`)*

28. **The largest quality wall in the corpus is three problems wearing one code — and one of them is two floors set 4× apart.** `THREAD_MATCH_POOR:block` grades **7 of 26 fixtures F 0** (14 of 52 matrix entries), all `gradient`, which is where real logo art goes. Decomposed 2026-09-06: **(1) the raw yardstick, 4 of 7** — `golden_tee`, `drone_render`, `region_blobs`, `summit_badge` clear every block once scored on EXCESS over the loaded spools (the photo route's 2026-08-24 rescoring, which the gradient lane never got). **REPRODUCIBLE as of 2026-09-07** (`tools/spool_remedy.py --yardstick`, no patch — excess is reported on every route, so forcing `_is_photo_class` and its confounds is unnecessary): it names those same four and no others. Nothing had reproduced this claim before, and its neighbour turned out to be a bug's artifact. **The offender set moves with the yardstick** — a thread's worst RAW patch can have a close loaded alternative while its second-worst does not, so 6 of the 24 findings block on a row raw scoring never looks at; a probe that keeps the raw top and reports its excess gets this wrong; **(2) halo cones, 1 of 7 — RETRACTED 2026-09-07, the category is EMPTY** (it read *"`gaulke_roofing`, defect 27's flag alone, F 0 → C 64"*; on the fixed tree that flag is byte-identical to `off` on gaulke on BOTH garments — F 4, raw 4, 2 blocking, worst ΔE **63.6 unchanged** — so the wall decomposes 4 + 0 + 2 and **gaulke is the seventh, unexplained**; its 63.6 names `1375`, a spool the design already loads, which points at category 1, unmeasured); **(3) survives EXCESS too — 3 of 7, not 2 (2026-09-07).** `screenshot` (`0111 Whale` excess 32.4, `2776 Black Chrome` 16.3), `bridge_bar` (`6156 Olive` 10.3) and now **`gaulke_roofing`**, which category (2) used to hold: it goes 2 raw blocks → **1** under excess, and the survivor is real — `3971 Silver` at raw 63.6, **excess 58.6**. So the wall decomposes **4 + 0 + 3**. **ROOT-CAUSED 2026-09-07: the MASK GAP accounts for TWO of the three, and it needs the small-shape floor to finish either** (`tools/spool_remedy.py --masks`). **(a) `gaulke` — the mask gap, newly named.** `revalidate_threads` and `_region_color_errors` claim the same estimator and have it (both take the median of the per-pixel CIEDE2000), but they do NOT share a MASK: preflight erodes the polygon raster one pixel and drops `p.bg_mask` (*"to keep anti-alias halo pixels from dragging a flat color toward the background"*), while `_region_footprint` is a bare `cv2.fillPoly` and does neither. On `Se6eddd27` (0.58 mm² at 16.1 px/mm) stage 4 scores **247 px** — 4.6× preflight's — and that set is BIMODAL, **103 near-black + 65 near-white**, so its median-of-per-pixel-dE makes `3971 Silver` the argmin **over the whole chart at 11.4 dE00**; preflight's eroded, background-excluded **54 px** read **[45,45,45]** and score that same Silver **63.6**. A **52.2 dE00 gap on one polygon.** Stage 4 is behaving correctly on the pixels it is given; the pixels are wrong. The RAW footprint is not held back by the small-shape floor — 247 px is above `THREAD_REVALIDATE_MIN_PX = 200`, `revalidate_small_shapes` alone leaves the region byte-identical, and an earlier draft of this entry had that backwards. (The MASKED footprint is a different matter — see the matched pair below.) **(b) `bridge_bar` — ALSO the mask.** A first version of this entry said "neither, still open" on the grounds that the two masks agree to 1.3 dE00 on `S880e5dff`. **That compared the wrong quantity** — the re-snap's gate reads the improvement over the best LOADED spool, not the assigned thread's score, and there the two masks read **1.8 against 10.3**, on opposite sides of `THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = 3.0`. So the raw footprint declines a re-snap the grader's mask would take. **(c) `screenshot` — the floor, and only the floor**: both footprints reach the same decision (`0015` best loaded either way, gain 31.3 vs 32.4) and both fail the pixel floor at 177/114 px; `revalidate_small_shapes` fixes it 32.7 → 1.4. **The mask and the floor are a matched pair**, which is the operational point: masking OUT the halo shrinks the footprint, so a shape the raw raster floated over the 200-px floor drops under it — gaulke 247 → 54, bridge_bar 240 → 156. `resnap_mask_matches_grader` alone therefore cannot re-snap either region; measured, bridge_bar needs **mask + `revalidate_small_shapes`**, which does move it (`6156` → `5866`, 21.3 → **16.2**) at the cost of one more block on that fixture, so it is improved rather than solved. On gaulke that pair is byte-identical to the mask alone, because the mask collapses the palette and `1375 Dark Charcoal` is no longer loaded for the small-shape rule to offer. **FIXED, DEFAULT OFF** (`cfg.resnap_mask_matches_grader`): the re-snap applies preflight's two operations — erode one pixel, drop `p.bg_mask`, hairline fallback included — and the pixel floor then counts the MASKED set, which also feeds the small-shape restriction. Masks agree to **99.99% IoU** on gaulke and 100% on `logo_alpha` (the residual is `_region_footprint` rounding mm→px where `_region_color_errors` truncates; aligning the rasteriser would touch `tag_enclosed_background`, so it is deliberately left). **Corpus A/B, 26 fixtures: 19 byte-identical, −1,715 stitches, −5 blocks, −4 cones, +2 trims, and `logo_gaulke_roofing` F 4 → D 46 — no grade moves down anywhere.** **The effect is bigger than the one shape:** gaulke's cone list goes 6 → 3 and its plan palette 4 → 2, because the re-snap was reaching `1375` and `3971` *for halo pixels* — **a SECOND cause of defect 15's resnap escape**, distinct from the missing palette binding `bind_resnap_all_classes` treats (that one restricts WHERE the argmin may land; this one fixes WHY it goes wrong). **Residual, named:** `Se6eddd27` improves 63.6 → **16.7**, not to zero — with the halo gone the re-snap DECLINES the region and it keeps stage 2's `4174`, and `1375 Dark Charcoal` (5.0 dE00 from this artwork) is no longer loaded for the small-shape rule to offer; `revalidate_small_shapes` is byte-identical on top of this flag for that reason. Flipping it is Kent's — it moves the flat and gradient goldens the phase-4 spec pins. *(measured 2026-09-07 — `tools/spool_remedy.py --yardstick` and `--masks`; `tests/test_resnap_mask_matches_grader.py`, 10)* The mechanism under two of the three: **`revalidate_threads` refuses the shapes preflight condemns.** Stage 4 already re-snaps threads that drift off their colour during simplification (fix #6.3) — 46 of 153 shapes on `screenshot_phone_ui` wear a re-snapped thread — but `THREAD_REVALIDATE_MIN_PX = 200` against `preflight._MIN_COLOR_PIXELS = 50`, so **every shape of 50–199 px can be blocked and never corrected.** 12 refusals on `screenshot` (all in-band), 7 would change answer, worst `S43831dcd` at **177 px**: `0111 Whale` 32.7 ΔE → `0015 White` **1.4**. Corpus agrees with the split — refusals are 0/0/0/7/4 on the five other F fixtures against **63 (`bridge_bar`) and 12 (`screenshot`)**. **FIXED, DEFAULT OFF** (`cfg.revalidate_small_shapes`): ON, the re-ask uses `THREAD_REVALIDATE_MIN_PX_SMALL = 50` — preflight's own floor — and a shape admitted only by it may take only a cone the design already carried at pass entry. `screenshot_phone_ui_golke`'s worst thread ΔE00 **33.0 → 21.2** (`S43831dcd`, 177 px, `0111 Whale` 32.7 → `0015 White` **1.4**), **21 of 26 fixtures byte-identical**, and **no grade or block count moves anywhere** — `THREAD_MATCH_POOR` blocks per thread on its worst patch, so fixing six of a thread's shards is invisible while a seventh is bad. It fixes SEWN COLOUR that the scorecard cannot see, which is a phase-1 datum; the render is at `docs/renders/small-shape-resnap-2026-09-06/`. Two constructions rejected with measurements: the unrestricted chart argmin (buys `screenshot` 10 → 9 blocks but costs `drone_render` 4 → **5** and takes `bridge_bar` to **22** cones) and restriction to the stage-2 palette (13 spools against the design's 16, so it forbids moves onto cones already on the machine — no regression and no win). Residual, measured not guessed: `drone_render` 19 → **20** cones because a shard lands on `0674`, which the shipped pass otherwise VACATES. Flipping it ON is Kent's. `THREAD_MATCH_POOR` also has **no area floor at all** (worst shapes: min 0.58 mm², p50 3.17, max 1,648.5 — 12 of 23 under 5 mm²) while every sibling check has one. **It no longer judges `enclosed_background` regions** (2026-09-06): unstitched by default, their colour is the background's, and `revalidate_threads` already refuses that category error. Worth ONE finding across the whole matrix — `logo_gaulke_roofing` drops `4174` (24.5 ΔE00 on 6.16 mm²), F 0 → F 4, blocks 3 → 2, no grade letter moves. A hardening, not a rescue. Two rejected constructions are recorded with it: a plan-derived denominator (breaks ten deliberate `test_preflight.py` cases that pass a synthetic plan) and, before that, an instrument filtering `run.jump` — which is how the needle ARRIVED, not travel, and falsely made this look like eleven findings (DOCTRINE gotcha 2026-09-06). *(measured 2026-09-06 — `digitizer/tools/revalidate_floor.py`; scope-history 09-06)* **And the check knew which cone to use and did not say — FIXED 2026-09-06:** `_best_loaded_spool_error` ran on the photo route only, so off it the remedy read "pick a closer thread" without consulting the design's own cone list, and **5 of the F-wall's 24 blocking findings name a spool the design ALREADY LOADS** (gaulke 63.6 → `1375` loaded and 58.6 closer; screenshot 33.0 → `0015` loaded and 32.4 closer; bridge_bar 21.3 → 10.3; screenshot 17.3 → 5.0; drone 12.8 → 9.0) — the first two being this defect's own headline numbers. Reported on every route now, with `yardstick` in `extra` naming which one judged the severity (its ABSENCE used to carry that signal, a contract a test caught — DOCTRINE), and **no severity or grade moves anywhere**, measured over ten fixtures. Whether the gradient lane should be JUDGED on excess is still Kent's. `tools/spool_remedy.py`, `tests/test_thread_match_better_spool.py` (11). **And the F wall has a DEPTH nobody had measured (2026-09-06, `tools/floor_depth.py`):** the score is `max(0, ...)`, so **12 of the corpus's 52 design/garment combos sit on exactly 0 with unclamped scores from −272 to −38 — a 234-point spread behind one printed value.** `screenshot_phone_ui_golke` must clear **312 points, ~11 blocking findings**, before its grade moves one letter; `drone_render` 228 (~8); the shallowest, `summit_badge` and `bridge_bar`, 78 (~3). That is the missing half of why a real thread fix here moves nothing — the check aggregates per thread AND the design is hundreds of points under water — and why `gaulke_roofing` is the one that moves (F 4, shallow, not floored). Un-clamping re-bases every grade, so it is a product call. *(measured 2026-09-06 — yardstick-disagreements row 6)*

29. **The panel printed the SERVER's filesystem path to the customer — FIXED 2026-09-07, and it was a FAMILY of three.** `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE` (9 of 26 fixtures, and not a corpus artefact — `cfg.photo_prep_background_removal` defaults True), `PHOTO_FACE_PRIORS_UNAVAILABLE` and `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` each interpolated a diagnostic — an absolute venv path, a YuNet model path, the last line of a worker's STDERR — into an untranslated message the panel renders verbatim. All three route through `pipeline._environment_warning` now; the diagnostic goes to `reason=` alone, which already carried it. Fixing only the measured site would have left two siblings — the missing-port shape defect 27 is made of. `tests/test_environment_warnings.py` (7) carries an AST tripwire rejecting any `warn()` message f-string that interpolates a `*_reason` name. **And the other ten are CLOSED too, 2026-09-07** — Kent's saleability call resolved the product question the measurement deferred. Eight are now translated in `WARNING_TEXT`; the two engine-telemetry codes (20 of 26 fixtures each: *"982 superpixels, 32 after merging"*, *"chart-restricted weighted k-medoids"*) plus the internal `PALETTE_THREAD_MISMATCH` and the dev-only SAM2 note go in `SILENT_WARNINGS` and never reach the rendered list, while `warningLines` keeps every code so the flat-art nudge and classification readout still branch on them; `SHAPES_LEFT_UNSEWN` returns "" when every unsewn shape is enclosed background, which is all 10 of the 10 fixtures that emit it. Guarded by a jargon blocklist over every translation (`digitizer.spec.js`, mutation-proved) and by two new `test_code_wires.py` cases: a silenced code must be a live wire value, and nothing silenced may also be branched on. **And the same defect lived on the FAILURE path — FIXED 2026-09-07.** `jobs.py` set `job.error` to `f"{type(exc).__name__}: {exc}"` and `digitizer.js` throws it at the user, so a 1×1 upload (and any artwork whose subject the background detector eats) read *"ValueError: no foreground pixels — the whole image reads as background"* three lines after the upload gate's own well-written rejections. `digitizer_service/errors.py` maps the artwork-caused failures to sentences and puts the raw form in `job.detail` beside the traceback. **The first cut replaced EVERY unmatched exception with a generic and three service tests caught it**: a bad `boundary_override` and a non-adjacent `merge_shape_ids` fail with messages naming the caller's own edit, which is the only thing that lets it be undone — so the map is an ALLOWLIST and anything unmatched passes through unchanged. `tests/test_job_errors.py` (9). *(measured and fixed 2026-09-07 — `digitizer/tools/warning_coverage.py`; DOCTRINE; scope-history 09-07)*

30. **The review screen's per-layer cone list names threads its layer does not sew — REAL, TRACKED, and currently HARMLESS.** `PALETTE_THREAD_MISMATCH` fires on **6 of 26** fixtures (34 shapes; `tools/palette_mismatch.py`) and appeared in NO document until now, though the code has described it since 2026-08-14. `result.palette` is per LAYER and `revalidate_threads` re-snaps individual shapes; `rehome_resnapped_regions` (2026-08-31) moves a re-snapped region to the layer declaring its new cone, so what survives is the re-snap whose target NO layer declares — and on **all six** fixtures the thread those shapes sew is on no review layer at all. **Three things bound it, each read off a contract rather than measured** (DOCTRINE): the OPERATOR's list is `plan.palette`, per BLOCK, verified consistent **26 of 26**; a layer legitimately sewing several shades is the blend tier, not this; and every Studio consumer is already hardened — `reviewFromJob` resolves a shape's colour with a `stats.blocks` fallback keyed by its own `sew_block`, and `QualityReport.svelte` refuses the layer palette outright. **Nothing renders the layer list as a cone list, so the customer-visible impact today is nil.** Kept as a regression detector for the day a consumer reads `review.palette` positionally; do not spend a session on it before then. *(measured 2026-09-07 — `digitizer/tools/palette_mismatch.py`; scope-history 09-07)*

31. **"Colors (max 6)" is not enforced on the lane real customer logos take — FIXED BEHIND A FLAG 2026-09-07.** Thread count is the cost driver: every distinct cone is a spool to buy and, on a single-needle machine, a manual re-thread mid-job, so the slider is a pricing promise. `stage2_quantize` caps the FLAT lane hard (largest populations kept, the rest merged into their closest match, `COLOR_CAP_APPLIED` emitted); the SLIC+RAG lane passes `max_k=cfg.max_colors` into k-medoids, which is a clustering parameter and **not a cap**, and the re-snap can add spools on top. **Stage 0 routes six of seven real customer logos to GRADIENT**, so the control was enforced on the artwork type customers do not have. Measured at the Studio's shipped default of 6 (`tools/color_cap.py`): **6 of 26 designs sew more cones than the slider promises and all six are gradient** — flat 0/6, photo_scene 0/7, photo_subject 0/2 — worst `drone_render` at **22 cones and 21 colour stops** against a promised 6, with `COLOR_CAP_APPLIED` never firing. Found by driving the shipped app, not by a test. **FIXED, DEFAULT OFF** (`cfg.enforce_color_cap`, `stage4_vectorize.enforce_color_cap`): ranks threads by SEWN area (enclosed-background regions buy no slot but are still remapped), keeps `max_colors`, merges the rest into their nearest kept cone by CIEDE2000, and emits the flat lane's own `COLOR_CAP_APPLIED` sentence so no new customer copy is needed. ON: **6 of 26 over → 1 of 26**; `drone_render` 22 → 6 cones and 21 → 9 stops, `screenshot_phone_ui` 15 → 6 and 14 → 6, `logo_golden_tee` 14 → 6, `logo_bridge_bar` 13 → 6 and 12 → 5, `summit_badge` 12 → 6; the 20 designs already inside their budget are untouched; +1.1% stitches on drone. **The residual is a different mechanism and is named, not hidden**: `region_blobs` has only 4 REGION threads (so the cap correctly does nothing) and **12 of its 15 sewn cones are built after it, in stage 6 blend bands** — defect 16's open half, on a GENERATED fixture no client artwork produces. A shade-band cap would have to run in stage 6/7. Byte-identical off. Render: `docs/renders/color-cap-2026-09-07/` — 24 shapes move on bridge_bar, all 0.38–7.21 mm², and the design reads the same. Flipping it ON is Kent's. `tests/test_color_cap.py` (11). *(found and fixed 2026-09-07 — `digitizer/tools/color_cap.py`; scope-history 09-07)*

32. **The low-resolution warning could not fire, and the Studio was wired to show it.** `stage1_prep` tested the resolution AFTER its own capped Lanczos upscale — and with `upscale_cap` and `min_px_per_mm` both **4.0**, any source at or above 1.0 px/mm lands exactly ON the floor, so the condition was false for every design a customer could send. `INPUT_LOW_RESOLUTION` has been in the Studio's `ATTENTION_WARNINGS` and had a `WARNING_TEXT` sentence the whole time; neither had ever been shown. **FIXED, no flag** (2026-09-07): it fires on `Prep.input_px_per_mm`, what the FILE supplied, and reports that plus `upscaled_to` and the floor — the old `px_per_mm` extra was the post-upscale value, i.e. the constant 4.0 dressed as a measurement. The customer sentence now carries the number and the multiple ("1.4 pixels per millimetre at this size and needs 4 … about 2.8x wider"), because "low resolution" says there is a problem and not what fixes it. **Precise, not noisy: exactly 2 of the scorecard's 26 fixtures arrive under the floor** — `becker_marine_logo` 1.81 px/mm and `logo_bridge_bar` 3.49 at 80 mm — and they are two of the three renders `docs/kent-review-2026-09-03.md` reports as settled before the engine ran ("a higher-resolution Becker source would change this render more than any engine change"). Both were silent. *(measured 2026-09-07 — `tests/test_input_resolution_warning.py`, `app/src/lib/digitizer.spec.js`)*

33. **The shopping list renamed the customer's threads — FIXED 2026-09-07.** The Download step's chart selector defaults to `loadPreferredPaletteId()`, which returned **"studio"** — Studio's 56 generic shade names — for anyone who had never chosen one, i.e. every first-time customer. A digitized design's cones are real spools the engine picked out of a 398-colour catalog, so the list re-derived *nearest generic names* and threw the actual numbers away. Measured on real logos at 80 mm: **`logo_bridge_bar`'s 13 distinct cones collapsed to 9 NAMES** — `0501 Sun`, `0713 Lemon` and `6031 Limelight` all printing *"Lemon"*; `0182 Saturn Grey`, `3971 Silver` and `0145 Skylight` all *"Silver Grey"* — so a customer buys nine spools for a thirteen-cone design and the machine stops on a colour they do not have. **And the names were wrong, not merely coarse**: on `logo_golden_tee` the engine's `0670 Cream` printed as *"Natural White"* while its `0630 Buttercup` printed as *"Cream"* — two adjacent rows naming each other's colours — and `0465 Umber` (brown) printed as *"Olive"* (green). **FIXED, DEFAULT ON**: `loadPreferredPaletteId(fallback)` now takes the design's own `review.brandId` and only falls back to `"studio"` when there is none (a lettering-only project) or the id is one this build cannot load. **A SAVED preference still wins**, so anyone who deliberately chose generic shade names keeps them, and the selector is unchanged. Verified in the running app: the list now reads 13 distinct Isacord numbers, the cones the file actually sews. Found by driving the Download step, which no test covers end to end. `threads.spec.js` (4 new). *(found and fixed 2026-09-07 — scope-history 09-07)*

34. **The size the app reported was the box the design was fit to, not the thread — FIXED 2026-09-07.** `buildLetteringDesign` and `buildQualityDesign` both returned `fitScale`'s target — the glyph outline (or the traced polygons) scaled to the garment's placement box — as `widthMM`/`heightMM`. That box is the INPUT to routing: pull compensation and the weight preset then push the satin rails outward, so the thread lands outside the number describing it. Swept over **7,470 lettering designs** (10 garments x 85 shipped fonts x 3 texts x 3 weights): **4,898 — 65.6% — sew outside the placement box they were just fit to**, worst +9.6 mm (`manga_impact` "Sam" on full_back), and **4 tell the hoop CEILING check "fits" when the thread needs the hoop rotated** (hat_front at the suggested 5x7). Image path too: `enthusiast_logo` at hat_front reported 127.0x25.4 mm and sews 128.6x25.2 — it runs both ways, the height reads 0.2 mm SMALL because the fill never reaches the outermost traced point. **Three consumers read the box as thread**: the field caption, the hoop ceiling check that gates `DownloadStep`'s oversize-export confirm, and the printed worksheet. **And SizePanel already showed the honest number** (`combine.js bboxMmFromStitches`), so one design displayed two widths at once — caption "127x13 mm" beside a W field reading 5.05 in = 128.3 mm whose own `max` was 5.00, which the browser reports as `rangeOverflow: true, valid: false` on the FIRST screen of the "Name on a hat" quick start. **FIXED, no flag**: `designExtentMm` (digitize.js) measures the emitted records, same rule as `combine.js`, and SizePanel stops putting a REQUEST bound on a field that displays a SEWN size (the clamp in `onWidthChange` is untouched). **The Python engine was already right** — `adapter.design_bbox_units` has always measured its own stitches — so this was the two engines disagreeing with the browser holding the wrong answer; their two record sets (JS stitch+jump+trim, Python sewn-only) are now pinned as agreeing, 0 disagreements over 249 designs, worst gap 0.000 mm. Exactly one geometry-free number moved in the suites, and the e2e guard was proved to fail on the pre-fix engine. `test/digitize.test.js` (5), `generate.spec.js` (2), `wizard-smoke.spec.js` (1). *(found by driving the app and measured 2026-09-07 — DOCTRINE; scope-history 09-07)*

35. **Two upload defects, both found by dropping a file on the panel — FIXED 2026-09-07.** (a) **The error message could not render in the case that needed it.** `DigitizePanel`'s `{#if error}` sat inside the `{:else}` arm of `{#if !element.sourcePng}`, so it only ever displayed once artwork had ALREADY loaded — and a file that fails to decode never sets `sourcePng`. Measured by dropping a `.txt` on a fresh panel: `onFile` set the message, the screen did not change. The one case where the customer has nothing to look at and no reason to think the app is working was the one case that stayed silent; a failed REPLACE, where their artwork is still on screen, was the only case that spoke. (b) **A vector logo was rasterised at the browser's default size.** All three upload panels (`DigitizePanel`, `ImagePanel`, `TraceImportPanel`) held byte-identical copies of `loadImage` and of `Math.min(1, MAX / longestSide)` — right for a raster (you cannot invent pixels a camera never recorded), wrong for a vector, whose "natural" size is a Chrome default. A `viewBox`-only SVG (what SVGO and most hand-written exports produce) loads at 300 px, so an 80 mm design got **3.1 px/mm** and the customer was told *"Enlarging it can't add detail that isn't in the file"* — false for a vector, and `INPUT_LOW_RESOLUTION` (defect 32) firing on a format that cannot be low-resolution. **FIXED, no flag**: `app/src/lib/rasterize.js` is now the one `loadImage` and the one work-size rule, and a vector renders AT the budget in either direction; Chrome re-rasterises an SVG at whatever destination size `drawImage` is given (measured on a 0.25-unit stripe in a 200-unit viewBox: darkest pixel **160 → 0**), so no SVG parsing is needed. **Same fixture, before and after, in the shipped app: 3,445 stitches in 4 colours with two warnings → 3,424 in 2 colours with none.** The two extra "colours" were anti-alias fringe — two spools to buy and two machine stops the artwork never called for. The unreadable-file message now names what works (PNG, JPEG, WebP, GIF, BMP and SVG all decode here; PDF does not) instead of only the verdict. `rasterize.spec.js` (6), `DigitizePanel.spec.js` (2, mutation-proved), e2e (1). *(found by driving the app 2026-09-07 — DOCTRINE; scope-history 09-07)*

36. **"This font can't stitch «Р», «у», «с». Try a different font" was a dead end — FIXED 2026-09-07.** Measured across all 85 shipped `.embf`: **3 fonts cover Cyrillic** (`cyrillic` alone carries 271 glyphs), **3 cover Greek**, **2 cover Hebrew**, and **none covers Japanese, Korean or Arabic**. Finding the three meant opening up to 85 fonts by hand; for the other three scripts the advice was to keep looking for something that is not there. This repo's own convention — a finding NAMES the fix — is already applied five times over in preflight (`THREAD_MATCH_POOR` names a loaded better spool, `COLOR_STOPS_HEAVY` the cheapest merge, `STITCHES_TOO_SHORT` the shapes); the lettering path was the one that stated a problem and stopped. **FIXED, no flag**: `tools/build-font-coverage.mjs` derives an EXACT per-font code-point index from the shipped binaries (16 KB, 3.4 KB gzipped — exact rather than a per-script summary, because a font with some Greek and not the letters typed is a worse answer than none); `lib/fontCoverage.js` is pure, `fontLoader.loadCoverage()` owns the lazy fetch, and a design that stitches never fetches it. **Asked about the WHOLE text, not the characters that failed** — `hebrew_font_large` has 29 glyphs and no ASCII, so on "Shalom שלום" it covers exactly the failures and none of the rest, and suggesting it would move the dead end rather than clear it (the app correctly answers "no font in this library can" there). Live: *"This font can't stitch «И», «в», «а» and «н» — Кирилиця, Egyptian and Egyptian Small can. Switch fonts and it will stitch."* **The index is named `manifest-coverage.json` for a reason:** `src/fonts/*.json` is enumerated as font SOURCES by both `build-embf.mjs` and `embf-guard.test.js` (whose stated invariant is "static JSON here ⇒ shipped"), excluding only a `manifest` prefix — a first cut called it `coverage.json` and broke four tests plus the font build. The guard's failure message now names that fix. `test/font-coverage.test.js` (3, re-derived independently of the builder), `fontCoverage.spec.js` (7), e2e (1). *(found by typing a Russian name 2026-09-07 — DOCTRINE; scope-history 09-07)*

37. **Two launch-scope features sat behind an unannounced right-click — FIXED 2026-09-07 (one sentence).** The basic shapes tool (PRODUCT.md launch item 4, ✅ Done: *"all four kinds verified digitizing live 2026-08-11"*) and the manual draw lane are reachable ONLY from the canvas's context menu — Kent's placement call 2026-08-13, *"keep them, but as a right-click tool rather than an upload button"* — and **nothing anywhere in the UI said so.** The Content step offers three tiles (Text / Artwork / Design file); right-click on a canvas is a power-user idiom a first-time customer has no reason to try. Verified working end to end from that menu (Draw shapes / Basic shape → Circle, Rectangle, Heart, Star → 3,918 stitches at 51×51 mm), so this was discoverability alone, not a broken lane. **The obvious place to say it is the wrong one:** the drag hint is gated on `stitchCount > 0` (`hints.js` condition A8), so it appears only once a design exists — after the question has stopped being asked. The empty-canvas line is what a customer is looking at while wondering what to do, and it now reads *"Your embroidery appears here as you add content. Right-click the canvas for drawing tools."* Kent's placement is untouched; reverting is one string. e2e pins the sentence AND that the gesture it names reaches both tools and produces real stitches. *(found by listing the Content step's buttons 2026-09-07)*

38. **The simulator counted in a different unit from the caption right under it — FIXED 2026-09-07.** The stitch simulator is driven by STRANDS (the segment between two consecutive stitches, which is what actually paints), and its counter showed that raw index: **"1289 stitches · 102×12 mm" under the canvas and "1280 / 1280" in the simulator bar**, both visible at once, nine apart on a design with nine runs. Both numbers were correct measurements of different things and only one carried a unit — the same family as defect 34, one screen over. **FIXED**: `strandStitchOrdinals` (strands.js) maps each strand to the stitch number it ends at, computed once per run, so the counter reads *"1289 / 1289 stitches"*. The animation still runs on strands. **The total is the LAST ORDINAL, not `design.stitchCount`** — a run of a single stitch paints no segment, so the simulator must never claim to have drawn it; the fixture has 0 such runs, and the tests cover one that does. `strands.spec.js` (5), e2e (1, plus the format pin in `field-chrome.spec.js` updated with its reason). *(found by watching the simulator run 2026-09-07)*

39. **"Exceeds your 8x8 in hoop" pointed at a fix that does not exist, on 40% of the garment picker — FIXED 2026-09-07.** Auto-fit targets the garment's PLACEMENT BOX, and **four of the ten shipped boxes are larger than the biggest hoop the app offers** (8x8 in = 200 mm): `full_back` 304.8x304.8, `jacket_back` 304.8x254.0, `blanket` 254.0x203.2, `tote` 203.2x203.2 mm. So every design on those four is oversize by construction, on every run — and the message named the chosen hoop as though a bigger one would help. It would not; there isn't one. `hoopFitNote` now distinguishes the three genuinely different fixes: rotate (unchanged), **a named bigger preset** (*"Exceeds your 4x4 in hoop — a 5x7 in hoop fits it"*, which the app already knew and made the customer work out), and **nothing fits** (*"Exceeds your 8x8 in hoop, and every hoop this app offers — make it smaller under Size"*). Message only. **Whether auto-fit should CAP to the hoop is the open question area 3 already carries and is Kent's** — capping would silently shrink every back-of-jacket design. The four impossible garments are asserted as a SET, so adding a garment or a bigger preset shows up in the tests rather than silently changing what 40% of the picker says. `hoop.spec.js` (3). *(measured 2026-09-07)*

40. **"Size up for crisp letters" was advice the DEFAULT design cannot take — FIXED 2026-09-07.** Lettering is fit by WIDTH, so for a fixed character count the cap height is proportional to the design width: measured with `medium_font` on left_chest's 101.6 mm placement box, every design at that same width, *"WIDE DESIGN TEXT HERE"* gives a **4.33 mm** cap, *"SHORTER TEXT"* **7.16**, *"ABC"* **30.03**. An auto-fit design (`sizeMm` null — the default, and what every quick start produces) is ALREADY at that box, so "size up" is the one thing the customer cannot do, and the levers that remain — fewer characters, a bolder font, a bigger placement — went unnamed. `letteringNote` now takes `atWidthCap` and swaps only the advice clause: at the cap the thin-lettering finding reads *"…already the full width of the placement, so fewer characters or a bigger placement is what makes them crisper"* and the hairline finding keeps "bolder font" (still true) and drops "size up". Below the cap both are unchanged — "size up" IS the fix there, verified in the app at W 2.60 in. **Read off the REQUEST (`sizeMm`), not the sewn width**: since defect 34 the sewn extent is slightly past the box by construction, so comparing it to the box would read "capped" for every design. The two findings that are not about size (cap under the floor; a lone hairline span, which reports what the engine DID) are untouched, and that is asserted. `generate.spec.js` (3). *(measured 2026-09-07)*

41. **The review screen quoted the cost of a sew-out on one lane and nothing at all on the other — FIXED 2026-09-07.** An auto-digitized design comes back with `preflight`/`stats` and `QualityReport` prints the four facts an operator needs before loading a machine (stitches, thread changes, trims, metres). A lettering, hand-drawn, shape or imported-DST design never reaches the service, so the same screen showed the garment, the hoop, the content, the font — **and not one number**; measured by walking Review with a text design, `section.quality` absent and no mention of thread, metres or trims anywhere on the page. `lib/estimate.js` computes them in the browser from the design already in hand, **only when the service has said nothing**, so one design never gets two answers. **The basis is the service's**: path length on `designToStrands`'s chain-break rule (= Python's `StitchRun.length_mm`) times `machine.THREAD_LENGTH_FACTOR` **1.35**, hand-ported into the engine and guarded against drift by `test/digitize.test.js` — the third constant to take that treatment after `FILL_ROW_MM` and `SATIN_SPACING_MM`. **Measured, and it does NOT agree exactly with the service on the same geometry: 4.95 m against 4.87, 1.6% high**, because `plan_to_design` emits a run the machine reaches without travelling as plain consecutive stitches, so the design records carry no marker for that boundary and the walk joins two runs. Irreducible from the browser, and the reason for the gate. The browser lane's own designs do not have it — `buildLetteringDesign` SEWS its short travel. **Two self-inflicted defects caught while building it**: `EMB.THREAD_LENGTH_FACTOR || 1` quoted a path length as thread (1.5 m for a design needing 2.1) against a stale `app/public/engine/` copy — now no factor, no row; and the field caption was the ONE stitch count in the app printing a bare `1289` where everything else says `1,289`. `estimate.spec.js` (7). *(measured 2026-09-07)*

### Closed — kept numbered, because ten other docs cite them by number

Full text moved to [`docs/scope-history.md`](docs/scope-history.md) 2026-08-27; these are pointers, not status.

1. shade-thread collapse (`_shade_blocks`) — RESOLVED 2026-08-19.
3. 14 jump-trims on an 80mm design — RETIRED 2026-09-01 (Kent's call) as UNREPRODUCIBLE: the entry never named the design and its pointer carried none, so the number was never checkable. A 2026-08-31 repro (two fixtures x three fill variants, three trim readings each) found nothing near 14 and nothing variant-invariant. Do NOT read those readings as a regression — without the design or the metric they are not comparable to 14, which is the mistake this line exists to prevent. The live concern moved to defect 4, which supports it independently and now carries a real 80 mm datum.
7. satin dropped a bracket's tab on `enthusiast_logo` (`_prune_spurs`) — RESOLVED 2026-08-21.
8. build-font dropped SVG transforms on four fonts — RESOLVED 2026-08-22.
9. the photo route escaped its own palette, both halves — RESOLVED 2026-08-24 (PR #217 + the 08-24 `shade_palette_bind` flip, default ON per Kent's 32-job-sheet ruling).
10. three photo-route robustness defects the first real photos found — RESOLVED 2026-08-23 (#214 OOM, #218 `select_palette` loop, #216 preflight).
11. the memory ceiling was per-region full-frame masks — RESOLVED 2026-08-24 (PR #230).
12. preflight graded every photo job F — RESOLVED 2026-08-24 (PR #229).
13. the detail layer sewed the background a cutout had just removed — RESOLVED 2026-08-24. **Its lesson stands: no acceptance arm had EVER set that flag**, which is the blind spot the evaluation-harness section exists to close.
14. half the cloth bare inside each shape is the THREAD-PAINT TIER, not a density bug — ANSWERED 2026-08-25 (streamline covers 0.55-0.59 of its footprint vs the filled tier's 0.99; Kent's filled-for-high-contrast ruling, and the face exception, are in Standing rulings).
16. one spool revisited across other colours, THE RE-SNAP MECHANISM — RESOLVED 2026-08-31 (`rehome_resnapped_regions`: a pipeline re-snap joins its cone's layer upstream of stage 5, so the coverage plan sees the order actually sewn; a review recolor was never a source, `apply_shape_edits` already moves the layer. Owl: every spool exactly once on BOTH routes, 17 → 14 blocks default; #291/#293 merge/hoist stay as the net for other sources. On cloth 2026-09-01: a 229-st cone re-entered the lens interior at 76%, a 104-st cone at 99.4% — the pattern this removes from the repro. Sweep: scope-history 08-31. **The SYMPTOM is not fully gone — defect 18 is a second mechanism.**)
17. sew order had no craft layering, BORDER SATIN OPENED THE DESIGN — FIXED, DEFAULT ON 2026-09-01 (Kent's flip ruling, PR #302). `cfg.borders_last`: satin-dominated layers sew after fill-dominated ones (`borders_last_layers`, upstream of stage 5 so coverage/underlap/ties derive from the sewn order) and satin-tier shapes wait for their group's fills; review-screen pins still win. Repro ring 0.0% → 54.5%, stitch count unchanged. Found on cloth by the first sew-out. Of eight golden keys one moves — the one already deselected in CI for platform numerics; its ubuntu re-capture is the standing follow-up. `tests/test_borders_last.py`.

---

## Latent — gated OFF, DO NOT FLIP without rebuilding its instrument

Safe only because it ships off. **A green suite is not evidence** — on chaining
one concealed it; entry 2 is a flag that LEFT this list unnoticed for two weeks.

1. **`chain_links` — sews needle-down thread on bare fabric.** 16.15 mm exposed
   over 17 links, stock preset, green suite. Both shipped instruments were
   blind three ways; all closed 2026-08-18 (four fixtures at **0.00 mm** added
   bare thread, **9.82 → 4.06** trims/1k). The replacement then erred the other
   way — a jump read as thread, **39.8 → 9.0 mm** phantom link, fixed
   2026-09-02, residual is a `-shadeN` id. **Still DO NOT FLIP, permanently:**
   gate 1 names link cover tolerance and the sew-out is accepted as-is. Largest
   lever on defects 4 and 6. *(`docs/hardening-closeout-2026-08-02.md`;
   [2026-09-02](docs/scorecard-baseline-attribution-2026-09-02.md))*
2. ~~`split_tonal_regions`~~ — **NOT LATENT: ON for photo classes since
   2026-08-19** (`d3f3c547`, spec decision 2); this said otherwise for two
   weeks. `effective_split_tonal` returns `bool(flag) or class_ in
   PHOTO_CLASSES` — the field only turns it ON. The old "confirmed OFF —
   `config.py`" read the FIELD, which stopped deciding two days later: **a
   per-class default cannot be confirmed from a dataclass line.** Ratified
   2026-09-02, left gate 3; cost is defect 20. *(`pipeline.effective_split_tonal`)*

*(added 2026-08-17 — `docs/project-review-2026-08-16.md` §1.6: chaining was absent
here, so a good-faith flip would have shipped bare-fabric thread unwarned.)*

---

## Doctrine — moved to [`DOCTRINE.md`](DOCTRINE.md)

**Standing rulings, Measured negatives, Corrections and Gotchas now live in [`DOCTRINE.md`](DOCTRINE.md)** (split 2026-08-28). Read it before proposing work, the same way you read this file for status.

The split is not filing. Those four sections answer *"has this already been
decided, tried, disproved, or paid for?"* — which does not go stale and only ever
accumulates. This file answers *"where does the project stand today?"* — current
state only, under a line budget. They were competing for one budget and the
standing content was winning: this file ran 268 lines over before the split, and two compaction passes could not close it without deleting things that still govern decisions.

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
   (standing rulings, [`DOCTRINE.md`](DOCTRINE.md)), so this needs its own call on
its own merits.
   Re-orienting the table changes every DST EMB-Bot has written. See "DST codec
   axis bug".
3. **RESOLVED 2026-08-19, ratified 2026-09-02 — `split_tonal_regions` is ON for photo
   classes** (`effective_split_tonal`); this said "default-OFF, parked until the sew-out" until today. Cost: defect 20.
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
7. **26 glyphs that sew nothing, in 6 shipped fonts — SPLIT IN TWO 2026-08-28,
   diagnosed from the shipped `.embf` binaries alone** (user-facing half
   already closed — the Studio says "This font can't stitch …"). 20 are
   `stripRunParamsIfSatin` taking runs-only glyphs' params; 6 are a GATE 1
   refusal (no authored run length upstream — defaulting one is refused by
   `test/run-fonts.test.js:44`). Full per-font diagnosis: area 2 doc,
   "stripRunParamsIfSatin". **Still open, one grep not a session:** count
   `running_stitch_length_mm` in `<ink-stitch>/src/roaring_twenties_KOR/
   ltr.svg`. **It has to be a LOCAL session** — that path is inside
   `scratch_ink/`, which is gitignored and absent from a cloud checkout
   (confirmed 2026-09-06), the same way item 6 blocks the corpus legs. **>0** → the narrow fix (scope the strip to glyphs WITH columns)
   revives the 20 — Kent's call, since inking those glyphs changes the bbox
   auto-scaling of any text containing `+ - / < = > \ _ ¯ °`. **0** → all 26
   are the same gate-1 case and this closes permanently.
   *(measured 2026-08-28 — `.embf` decode; detail: area 2)*
10. **RESOLVED 2026-08-25 — Studio typography: "tighter and more editorial."**
   Kent's direction, given when asked. It settled the three items the earlier
   type work left alone (irregular scale ratios, `h3` at body size, untokenised
   weights) and it is a STANDING one — new UI is set to it, not re-litigated.
   What it means in practice is in the area doc. *(2026-08-25)*

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
8. **Font lawyer consult — optional.** Only gates RESTORING the 13 pulled
   ShareAlike fonts; the brief is written and ready to send. Nothing waits
   on it. See the font-licence entry.

12. **Merge a tiny cone into an ADJACENT SHADE — a colour call, and the
   COMMITTED corpus can now pose it.** The sew-out's b4/b7 class: cutting such
   a cone further means sewing its patches in a neighbouring shade's thread —
   a colour step for a stop, quality not gate-1 physics. `sequence_census.py`
   reports colour since 2026-09-02, and committed art carries defensible
   pairs — ΔE **1.41** (`screenshot_phone_ui_golke`, 62st → 79st), **1.78**
   (`logo_bridge_bar`, 197st → 444st), **2.65** (`drone_render`, 338st →
   1560st); the repro had none (closest cones 33.4 ΔE) until 2026-09-04, when its sweep became five shade bands 5–6 ΔE apart by design — adjacent shades of one ramp, not candidates. Real artwork runs
   15–18 cones, so the population is not rare.
   **TABLED — Kent, 2026-09-02:** *"I'm honestly not concerned about the
   hopping idea, we can table this one for a further discussion."* Do not
   build the shade-merge or further hopping polish until he reopens it; the
   08-31 mechanical fixes (`start_near`, the re-snap rehome) are merged and
   unaffected. *(measured 2026-09-02 — `sequence_census.py`, 26 fixtures; tabled 2026-09-02 — Kent)*

13. **RESOLVED 2026-09-03 — the stitch-angle rule is ADOPTED (cap 30°), pass 1 BUILT:**
    fading lean, cap, spacing / cos(lean); bisector deleted; stems = the family square to the
    line of text. Leaned-column thread pitch 0.152 → 0.20 mm; ENTHUSIAST benchmark 4.62 → 4.09/1k.
    **Flag FLIPPED ON by Kent; the Goldman join (pass 2) BUILT: trims flat, benchmark 3.81/1k, bare fabric drone 2.8 → 2.2%.** *(2026-09-03 — area 1)*

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec axis bug

EMB-Bot's browser DST codec (`src/dst.js` / `src/dstimport.js`) disagrees with the
Tajima/pyembroidery standard — confirmed, wrong in **both directions**, and it round-trips
against itself so the pair's own tests never saw it. **The WORD was wrong until 2026-09-07: it
is a MIRROR, not a quarter turn.** A bbox swap fits both equally, nobody had looked at the
canvas, and the Studio told customers to "use Rotate to stand it up" — which no rotation can
do, and the app has no mirror control. **The IMPORT half is FIXED 2026-09-07**
(`EMB.decodeDSTStandard`; `decodeDST` and its 12 round-trip tests untouched): a becker logo
lands `96×58 mm` reading forwards, and PES/EXP/JEF re-export **identity, rms 0** against the
source file where all three were mirrored. **Not only orientation:** `dst.js` writes the
colour-change byte `0x43` not `0xC3`, read as a spurious sequin toggle, so a two-colour design
decodes with ZERO colour changes elsewhere — which is why DST was never the good option here
even while it was the only correctly-oriented one. **A SECOND deferred DST call was priced on the wrong lane, re-measured 2026-09-07.** `encodeDST` does not stop at the terminal `{type:"end"}` sentinel the way `exp.js` and `pes.js` both do (one line: `if (st.type === "end") break;`), so it writes it as a real stitch. The 2026-08-04 verdict deferred that as "one extra phantom stitch", true of LETTERING — where the sentinel sits on the last stitch and the record is zero-delta, and where `buildLetteringDesign` in fact appends none at all. On the imported/digitized lane `buildImportedDesign` puts the sentinel at the ELEMENT'S OFFSET: measured on a real 95.7×58.3 mm logo, the DST ends with a stitch **0.07 mm from the design's centre, 46.4 mm from the previous one** — a stray needle penetration mid-design with 46 mm of travel to reach it, on **every** single-element imported, digitized, shape or manual project. PES and EXP of that same design end where the design ends (11,274 stitches against DST's 11,275). Pinned in `test/crossval-stitch-formats.test.js`'s DST control, which had shown `decoded 16 / expected 15` since the day it was written without anyone asserting it. Still Kent's. *(2026-09-07)* The EXPORT half is still Kent's, and it now
owns the leftover: EMB-Bot's own `.dst` read back in is the file that comes in mirrored (named
in DesignPanel; the lever is My designs). `dst-codec-axis-discrepancy` in memory.
*(export 2026-08-22; import measured and fixed 2026-09-07)*

**Not a conflict:** CLAUDE.md's "browser DST is EMB-Bot-internal only" is about
orientation elsewhere; `digitizer/README.md`'s "browser DST stays the default"
is about which encoder Studio picks.

**RE-OPENED and FIXED 2026-09-07 — the 2026-08-17 "CLOSED" was a CODE READ, and the code was
right while the product was not.** `isPurelyDigitized` required EVERY element to be `digitized`
and `defaultProject()` seeds an empty text one a logo customer never removes, so `/export`
never fired and **every** DST left by the browser codec. The resolution path's third-party read
is DONE, from the shipped UI via pystitch: browser **16.3×80.5 mm, 0 COLOR_CHANGE, 1
SEQUIN_MODE + 10 SEQUIN_EJECT**; service 80.5×16.3, 1 COLOR_CHANGE. The gate now counts only
elements that SEW. `dstimport.js`'s `decodeDST` stays as it is (it pairs with `dst.js`), but
the import LANE moved off it the same day — see the mirror correction above. *(2026-09-07)*

**The LETTERING half is now measured too, and the fix needs no codec change — KENT'S CALL 2026-09-07.** Lettering/manual designs still download through the browser encoder by the standing scope ruling ("the one with actual sew evidence behind it"). Measured stitch-for-stitch on ONE browser-built lettering design (`manga_impact` "Lp", 61.7×31.7 mm landscape, 906 stitches), both encoders fed the SAME design object: the service's `/export` DST reads back **61.7×31.7 mm** with the file's x equal to the design's x on **906/906**; the browser's `encodeDST` reads back **31.7×61.7 mm** — a quarter turn — with the file's x equal to the design's **y** on **906/906**. The service path is spec-correct for browser-built lettering as well, so routing lettering there is available today with `src/dst.js` untouched. **What the ruling is actually protecting is the sew evidence, and that evidence is evidence of a TRANSPOSED file sewing** — which is the thing to weigh. Not flipped: the routing ruling and the codec are both Kent's. *(2026-09-07)*

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
2-core, so `-n auto` gets two workers and OpenCV's threading competes with them. Parallel-safety is verified, not assumed.
**`--durations` has now been run (2026-09-06), and the lever it named was a mirage:** its top five entries were one `lru_cache` bill split across workers — the suite does **20 real pipeline runs for 8 distinct cases**, because the cache is per-process and xdist is not — so deleting them saved **13s of a predicted 380**. The real win was caching the suites themselves, **18m38s → 14m00s** (#369). `--dist loadfile` measures **5.8%** at CI's own two workers (23m53s → 22m27s, 1889 passed both ways) but floors wall-clock at the slowest single FILE: an option with its trade named, not taken. **And the job's own duration is not what anything here documented** — measured 2026-09-06 over the last 220 completed `digitizer` jobs from the Actions API: **10 to 42 minutes**, daily median walking 15.0 → 16.5 → 17.6 → 18.7 → 20.7 and then jumping to **29.6 on 2026-09-06** (max 41.8). CLAUDE.md's "12–18" was true when written and now holds for half. **Cause not settled, but bounded:** it is entirely in the test step (`Install` is 0.27 min on fast and slow runs alike), it is NOT concurrency (the 41.8-minute worst case ran with ZERO other digitizer jobs, and the most-contended jobs are the fastest — hypothesis refuted), and suite growth alone cannot carry it: the SAME test count lands 19.6–34.5 min (1,851 tests) and 17.9–33.7 (1,968), a **1.9× spread on identical work**, with seconds-per-test running 0.54–1.32. **The runner's CORE COUNT is refuted too, by the diagnostic on its first run** (2026-09-07): `nproc: 4`, 16 GB, on a **27m59s** job of 1,984 tests — `-n auto` had four workers, and this box does the same suite in ~15 min on four. Four hypotheses, four eliminated; what remains is per-core throughput or hypervisor contention, which one reading cannot separate. Every run now records its own `nproc`. *(measured 2026-09-06/07 — scope-history 09-06, 09-07)*
*(measured 2026-08-14, 2026-09-06 — DOCTRINE, scope-history 09-06)*

### No physical sew-out testing has occurred yet

Zero sew-out testing anywhere in this project — confirmed across three
independent research passes. `docs/hardening-closeout-2026-08-02.md`: "Nothing
was sewn. Every number above... is geometry." It is the single biggest
confidence ceiling here — fabric presets, real stitch quality, the DST axis
question all wait on it — and that doc already specifies four hoopings that
would settle nine open geometric questions at once. **Kent accepted this as-is
2026-08-21:** not a queued action; scores under it read `pending sew-out`
permanently. Do not re-raise it as the highest-leverage next action.
One specific question is now queued behind it with the code change already
measured both ways: whether a split, underlaid 5.3 mm satin column is sound —
see DOCTRINE, "Raising `SATIN_MAX_WIDTH_MM`". *(2026-09-02 — reverted branch)*

### Evaluation corpus & harness — real gap, newly tracked here

**The gap: no repeatable automated quality signal**, so every serious quality
question queues behind a corpus nobody has or a sew-out nobody has scheduled. A
labelled corpus plus a scoring harness would let a classifier change be judged
against *something* before either arrives.

**Seven measured cases where the harness disagrees with the sewn result — one of them since retracted:** [`docs/yardstick-disagreements-2026-09-06.md`](docs/yardstick-disagreements-2026-09-06.md) — phase 1's exit condition is a claim about disagreements and nothing was gathering them. Two are load-bearing: a 32.7 → 1.4 ΔE00 thread fix that moves no grade or block (the metric moves; the verdict does not), and four photo fixtures that score HIGHER with a ratified quality tier off. Append; do not curate — **row 7 held for one day and is kept, marked, because the retraction is the finding**: it was measured on a tree with the `~base_valid` bug in it, and fixing that bug reversed its direction (2026-09-07). *(assembled 2026-09-06)*

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture`/`diff`
over 26 fixtures x 2, aggregating preflight's score. REPORTING, not a CI gate;
detail: [area 1](docs/scope/1-auto-digitizing-quality.md). **The 2026-08-12
baseline was SOUND — 38/38 rows re-scored exactly on its own commit, so every
mover was real**, and all were attributed before the 2026-09-02 recapture,
which also drops the duplicate fixture and stamps its commit.
*(2026-08-21; 2026-09-02 — [notes](docs/scorecard-baseline-attribution-2026-09-02.md))*

**Corpus half — the real-artwork entries keep contradicting the synthetics.**
Seven distinct real customer logos ship in `FIXTURES`: **stage 0 routes six of
seven to GRADIENT**, because real logo art carries JPEG ringing and anti-aliased
edges the synthetics lack, so a "flat spot-colour art" claim tuned only on
synthetics is untested against real input.
`logo_script_tires.png` classifies `photo_scene` outright — a misroute kept so
the bug has a fixture. **Real PHOTOGRAPHS go further: all four of Kent's
portraits classify `gradient` with the LOWEST `unique_color_mass` in the corpus,
below every gradient logo** — the measurement behind `cfg.is_photographic`
being declared rather than detected.
*(2026-08-15 / 08-25 — `corpus_scorecard.py:FIXTURES`; scope-history 08-25)*

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
Gotcha in [`DOCTRINE.md`](DOCTRINE.md) before comparing to any earlier number.
*(confirmed — PR #151)*

**Half that corpus is in the repo; the half that matters is not.** The tracked
`Embroidery Files.zip` carries all 23 pro STITCH files, so `prep_all.py`'s recon
lane runs from a fresh checkout. It carries **zero customer artwork**, so
`prep_both.py`'s real lane — the one behind the 42.5 baseline — still needs the
Drive copy. *(corrected 2026-08-18 — prep_both from the zip fails 0/15)*

**Area 1 is deliberately NOT split into "image analysis" + "stitch planning"**, and
the four gaps an external review named have owners in code — [area 1](docs/scope/1-auto-digitizing-quality.md). *(moved 2026-08-21 — rule 5)*

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
#241/#243/#245; scope-history 08-25 evening)* **Gradient lane, 2026-09-04 (Kent's ruling): a design whose ramp fits is ONE sweep.** `design_ramp.py` (trimmed + consensus plane gate: r² ≥ 0.4, ≥ 60% riding, sigma ≤ 4; colour as a profile along the sweep) flattens stage 2's merge and gives stage 6 one shade scheme per design, and a riding region never takes the satin rung: the icon repro at 80 mm goes 10 → 8 regions and its three ramp pieces decompose into five shades along the diagonal where they sewed flat or as one-thread satin; drone/summit/blobs/owl are refused and untouched (angle included). Two tier defects fixed on the way: blend bands had sewn at n× the row since the tier's first commit (a quarter of a fill; #339's preflight exemption for it withdrawn), and `_band_clip` shifted a linear ramp's bands by the region's own centre — the committed engine never sewed **46%** of `gradient_ramp_linear` at 80 mm, suite green. **Blend regions sew stage 5's compensated outline since 2026-09-04 (Kent's pick):** stage 7 had handed `blend_fill` the ARTWORK polygon, so every region of a gradient-class design — bands and tatami fallback alike — sewed with no pull comp and no seam tongue while `tools/seam_underlap.py`, which reads the plan, showed the tongue present; `tools/sewn_compensation.py` reads the stitches: repro strips 29% → 100% covered, blobs 36% → 100%; repro 22,087 stitches, 26 trims. **The machine's cone list is on the wire since 2026-09-04** (`stats.blocks`, one per sewn block with the review shapes it sews): the download's thread list always read `design.colors` and was right; the Sequencer header, its rows and the quality report's metres now read the blocks too, and `reviewFromJob` no longer indexes the per-layer palette by `sew_block`. **The satin raster ate every counter's edge until 2026-09-04:** `fillPoly` paints boundary pixels, so a hole painted in 0 lost half a pixel of material all round while the exterior gained one; the medial axis moved outward and the hole-side rail (the NEARER hit) stopped 0.18 mm short of the compensated outline on the repro's frame and ring while the exterior rail sat within 0.006 mm. Holes are painted half a pixel smaller in both rasterisers (`shapefield.hole_px`; `_rasterize` and `rasterize_polygon` are twins by test — the boundary-redraw form closed small counters and was measured out): frame strip 57 → 66% covered, ring 47 → 59%, against the instrument's ~80% ceiling for a perfect satin; the rest is the smoothed width profile at corners, which `rails_follow_edge` (sew-out gated) recovers. Hole-free shapes byte-identical. **Band seams feathered the same night (Kent's call on the render):** a 1.5 mm zone per seam sewn by both shades on one row lattice, alternating row by row, where rows run along the seam; repro 22 trims, 20,820 stitches. **Radial sweeps ride too (2026-09-04):** `design_ramp.py` fits a radial model (Gauss-Newton centre from the centroid, trimmed-then-consensus line in radius, colour profile along radius) gated at r² ≥ 0.6, ≥ 15 of 17 radius knots at consensus and the centre inside the stitched foreground, winning only when it beats the plane; `gradient_ramp_radial` at 80 mm 2 → **1** region, 5 shades (its 4,069 mm² outer ring had sewn flat), summit refused on knots, the owl on r², the linear fixture and the repro on the centre; linear designs byte-identical; a non-riding region on a radial design sews level. Ring seams keep the hard seam + underlap (rows cross rings; a stitch-level dither is a later item). **The blend tier takes the density stage 7 resolved since 2026-09-04** — it read `machine.FILL_ROW_MM` directly, so neither a per-job `fill_row_mm` nor a fabric's `density_adjust` reached a gradient: on a towel (0.85, pile needs TIGHTER rows) every band sewed 0.150 against the design's own 0.128, the repro 23,375 → 26,561 stitches. Invisible on the corpus scorecard, whose two garments both sit at 1.0. **The `-blend` suffix made four instruments blind until 2026-09-04** — preflight's bare-fabric check examined 0.0 mm² of a one-region sweep and a fifth of the repro (1,091 of 5,729.5 mm²), its thread match scored five cones as one, and the service filed a gradient's sew order and block ids under names no review shape has; `preflight._owning_region_id` is the one rule (a prefix test is not a substitute — region ids are not prefix-free). A fifth defect fell out of the same reading and is not an id bug NOR gradient-only: every region filled into ONE shared mask, so a ring's hole erased the artwork a nested region claims — the repro's shared mask claimed 136,341 px where the union claims 802,474, and the flat `logo_bridge_bar` (77 regions, no derived ids) rises 551.0 → 1,381.2 mm² examined. Scores fall where they were false: repro A 100 → D 58 on a band wearing a cone 13 ΔE off. Satin as SEWN is measurable since 2026-09-04** (`tools/satin_columns.py`, calibrated on two committed professional files in CI): a cross is sign alternation about the chord, not a turn angle, because a fixed angle gate is blind to columns under ~0.69 mm. Pro Becker **44.3%** of penetrations in columns at a 2.52 mm median; ours on the same logo **2.2%** of penetrations — the biggest measured gap to a professional file. **The width half of that line was contaminated and is corrected (2026-09-06):** "0.29 mm, 84% of columns under 0.7" is the WHOLE-PLAN row, 80% of it tatami turns; our SATIN runs there measure **3.82 mm median, p90 4.93, 23% under 1.0** against the pro's 2.52 / 5.00 / 7%. Read our widths off `satin_columns.py`'s second row (DOCTRINE 09-06). The share gap is real; the width gap was not (plan: `docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`). **No physical tests until Kent says — the render is the judge.** *(measured 2026-09-04 — scope-history; DOCTRINE)*
**Kent's own verdict, 2026-08-27: these are 60% of the way to Ember parity.** First per-design feedback in his words on all fourteen designs. `artfidelity_self` averages **83.7** and `preflight` **80.0** on the same set, agreeing with each other at only **rho = 0.405** — so **never quote ARTFID as a quality percentage**: it is a fidelity score, blind to craft, which is most of his missing 40%. He named the split himself — *"Shapes are accurate but smoothness is not."* Two themes, equally weighted by him: smoothness (8 of 14) and whole elements missing (7 of 14; both his "out of place" marks lost an element). **Bears on ROADMAP phase 1's exit condition** — a fidelity-only metric may not be able to agree with a partly craft-driven ranking at all.
**`ARTWORK_UNCOVERED` cannot see a dropped element**: fired on 1 of those 7,
`0.0 mm²` on the rest with `uncovered_checked: True`, because it is scoped to
shapes the design already sews. `tools/dropped_elements.py` measures it from the
artwork's side — 99.1% lost on the logo Kent called "5% completed at most".
**Both halves of the smoothness complaint now have instruments, and they are not the same measurement** (Spearman 0.028, n = 12 — rules out redundancy, not dependence). `tools/edge_smoothness.py` owns edge noise; `tools/curve_fidelity.py` owns the curve half, read from `plan.iter_runs()` because **curve fidelity is not readable from a raster**. Read **`roughness_deg`** per design; `turn_gini` is substantially a COMPLEXITY statistic (Pearson −0.763 vs log trace count), valid only on the ladder or a paired arm; the floor is **stitch length**. On Kent's four Becker artworks the two SPARSE ones measure roughest — complexity, not size (an earlier "small placements sew rougher" reading is withdrawn). *(measured 2026-08-27/28 — PR #281; `docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`)*
**Two engine defects open, unfixed:** `summit_badge`'s half-removed background, and `stage1_prep.py:254-266` answering a structural question (`BACKGROUND_ABSENT`) through a colour threshold (`bg_tolerance_lab`). *(measured 2026-08-27 — `docs/kent-review-2026-08-27.md`; memory `kent-eye-vs-instruments-2026-08-27`. PR #276's body claims the engine is correct on `summit_badge` — that sentence is wrong, its instrument fix stands.)* **Satin extremity drop — FIXED 2026-08-21.** `_prune_spurs` re-measured a stem its OWN first pass had un-branched, one raster pixel deciding a 3.3 mm tab. **The blind spot that hid it stays fixed:** `preflight`'s `ARTWORK_UNCOVERED`, 5.0 mm² threshold still provisional. *(fixed 2026-08-21 — PR #186)* **Lettering quality — the STITCH-ANGLE mechanism is FIXED 2026-08-27. Three others remain open.** Kent on two sewn logos: *"lettering should be smooth"*, *"ROOKIE MISTAKE"*, and *"Why is the 'N' running Vertically?"*

**Fixed: a word's letters now share one house angle.** `stage6_satin` grew
`satin_shape(angle_deg=...)` on 2026-08-26 — held loosely by `_clamp_to_span`,
which rotates the house angle only where a stroke cannot span it — but nothing
ever SET it, so the sewn output did not change. PR #282 added the derivation
(length-weighted, aggregated in `directionfield`'s doubled-angle space) and PR
#283 made it fire. Measured on the Becker Marine logo: satin and fill strokes
within ±20° of the modal direction go **29% → 51%** against a 22% chance
baseline, with **total thread −2.4%**, trims and jumps unchanged.

Three thresholds had to be corrected to get there, each applied to a population
it was not calibrated on — **gate 4 in miniature** (the confidence gate became
Rayleigh's test, chance-corrected; the ring half of its 10x-vs-1.2x figure is a
degenerate fixture, 2026-09-02). All three: [area 1](docs/scope/1-auto-digitizing-quality.md), moved verbatim.
*(fixed 2026-08-27 — PRs #282/#283, mutation-checked; renders in the #283 body)*
**And it was NOT FIRING on slab-serif lettering — a FOURTH miscalibrated threshold; fix BUILT
(PR #321), the angle rule's pass 1 and the Goldman join on top (2026-09-03).** Fremont's capitals
cancel in doubled-angle space (nR² 4.7 vs 6.9). `satin_house_fourfold` (DEFAULT ON, Kent's flip)
admits two orthogonal families and sets the STEMS' perpendicular (the family square to the line of
text; bisector deleted); a bar takes its own perpendicular with the lean fading to zero, a diagonal
leans ≤ 30°, stations spread by cos(lean); ≥ 45° corners butt-join inside one stroke. Thread pitch
Fremont **0.152 → 0.198 mm**, ENTHUSIAST 0.152 → 0.200; benchmark **4.62 → 3.81/1k**; bare fabric
drone 2.8 → 2.2%, Becker 6.0 → 5.5%; crosses past 45° off perpendicular drone 26 → 17%. Capitals
measured, lowercase not. *(measured 2026-09-03 — area 1)*

**Mechanisms 2 and 4 — prototyped/costed and half-closed respectively — moved to [area 1 detail](docs/scope/1-auto-digitizing-quality.md) 2026-09-07 to keep this file inside its own 800-line budget.** Kent held the exterior-notch guard 2026-08-28 (reds the chaining benchmark 3.8 → 6.4 trims/1k); the letterform instrument reports the WORST medial-axis stroke and is **still blind to TILT**. *(moved 2026-09-07 — no content changed)*

**Still open and unfixed:** `_prune_spurs` drops a 3-way node to 2-way so
the walker welds the N's diagonal to its stem through a 108° fold — the same
function PR #186 fixed, one consequence on. Prototyped twice, NOT shippable
as written (propagates the H defect to every square-capped bar; two
prototypes measured −18.3% and +20.5% off one baseline); needs a cap-arm
classifier. *(measured 2026-08-26 — `.claude/memory/letterform-fidelity-2026-08-26.md`)*

**Confidence limit on the fix:** two real lettering groups from ONE logo; real-artwork validation needs Kent's box.

**Text clusters see ordinary lettering (third attempt, 2026-09-03).** Two doors clustered in two ROUNDS — rescued first with unchanged code, so every cluster that regularizes is computed as before — then ordinary glyphs at the house-angle height ratio with a one-ink CIEDE2000 link (ΔE ≤ 20; the shield star is 34.2 from ENTHUSIAST, within-word quantization needs ≤ 16.4). Becker 0 → 11 tagged, drone 0 → 21, enthusiast keeps its subline cluster id. Cost measured quiet: enthusiast +0.9 s; the 60 s service test at 12.4 s idle and 12.1 s under three CPU hogs once the tesseract child is pinned to one OpenMP thread (32.7 s before — the likeliest root cause of `10ae9cc`'s CI timeout). No satin underlay under a 5 mm shape (`SATIN_UNDERLAY_MIN_EXTENT_MM`, the JS rung; Kent's call). *(measured 2026-09-03 — same doc)*

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
**Size guards (2026-09-03):** the 0.5 mm cross floor on the fabric (was 0.3 design pixels), hairline stretches as bean runs, and a per-element note of cap height and the share under 1.0 / 0.5 mm — warn only, no clamp; at 50 mm four hairline-authored fonts move > 5%. **Bold no longer closes counters:** its 0.3 mm is held per rail where a rail faces another across a gap the cross floor cannot spare (0.72 mm eye: 0.50 guarded vs 0.42; 0.36 mm: untouched vs 0.06); pull comp and normal/thin untouched; 60 of 83 fonts hold somewhere at 25 mm. **Short stitches (Law 53)** on the inside of bends, the Python guard mirrored and width-gated by the cross floor: geneva "S" 43% → 0% of same-rail advances under 0.3 mm, stitch counts identical, faces at the floor left alone. *(measured 2026-09-03 — commit `0a67171`, area doc §"Bold counter guard", §"Short stitches")* **And the LARGE end has no guard at all — NEEDS KENT (2026-09-07).** Measured over all 85 fonts at three texts: **18 fonts emit stitch segments longer than one DST record (121 units), worst 32.8 mm.** The quick starts are clean (`YOUR NAME` on a hat 0/2,346; `Your Name` 0/958; `Yours` 0/1,792) — it starts when letters get big: a **single-letter monogram at left-chest size gives 278 of 1,607, worst 17.9 mm**, and `AB` on a Full Back gives **1,933 of 5,828, worst 44.9 mm**. No machine sews a 17.9 mm stitch, so the three encoders each invented an answer — `.dst` travelled it (3,769 jumps), `.exp` split it, `.pes` wrote a 51.1 mm stitch. `dst.js` now splits like `exp.js` (byte-identical for every design that had no over-length segment — the 85-font corpus hashes the same before and after), but the ENGINE still emits them. What to do about a wide satin crossing — split satin, route to fill, cap the width — is a look-and-fabric call with a sew-out behind it. *(2026-09-07 — DOCTRINE, scope-history)*
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

**The two engines' fabric tables agree again, and a test keeps them so (2026-09-07).**
Corpus law 26 (`edge_lattice` → `edge_run` under a knit fill) landed in Python only, so the
browser ran an extra crosshatch pass on left_chest/beanie/sleeve for a month (+1.4–5.7%
stitches). `test_fabric_wire.py` compares both tables field-for-field and asserts AGREEMENT
only — the numbers stay gate 1. *(2026-09-07 — DOCTRINE)*

**A Studio change is not verified until it has been *looked at* in a browser.**
A 2026-08-25 sweep found a white-on-white CTA and a silent canvas menu; 2026-09-07,
"Ready to stitch" over an empty design, an auto-digitized logo recapped as
`Content: Text — ""`, two widths for one design (defect 34), and an upload error
the template could not render (defect 35). Six, none seen by a green suite. *(DOCTRINE "Gotchas")*

**Uploading artwork is the whole interaction — the panel no longer asks the
user to classify it first.** The run starts on upload and the panel STATES what
the art was read as ("Read as flat art" / "as a photo" / "as shaded artwork" /
"couldn't tell"), with the override recast as a one-click correction to that
sentence. `detail_layer` sits on that row too (Kent 2026-08-30) and appears only
where the art is actually on a tonal lane, by reading or by override. Nothing
changed in what gets sent, so area 1's photo-control numbers are untouched, and
the engine's routing is unchanged — ROADMAP gate 2 bars recalibrating stage 0,
and phase-4 v1 works around it with exactly this override.
*(confirmed 2026-08-30 — driven in a real browser against the real service, every state of the row clicked through and looked at; pinned by e2e `digitize-auto-start.spec.js`; numbers in scope-history 08-30)*

**The hoop you picked is now DRAWN, and the export gate uses it.** `preview.js`
had one box — the garment's PLACEMENT box — and called it the hoop, so choosing a
hoop changed nothing on screen. `hoopTransform` returns both and fits to the
larger; `DownloadStep` warns before a stitch export that will not fit (confirm,
not block; PNG and PDF worksheet ungated — not machine files). **Live: the stock
Tote / Full Back preset is 203.2 mm against a 200 mm max hoop**, so it fires on a
shipped preset — whether auto-fit should CAP is open, and it is now measured: **four of ten garments (full_back, jacket_back, blanket, tote) have placement boxes larger than the 200 mm biggest hoop**, so 40% of the picker is oversize on every design (defect 39). *(2026-09-02 — PR #317;
`preview.spec.js`, `DownloadStep.spec.js`, e2e)* **What that gate is fed changed 2026-09-07**: it used the box the design was fit to, which 65.6% of designs sew outside of (defect 34), so it now reads the thread's own extent.

**The digitize panel states what CHANGED and offers the fix.** Shape list behind
an "Edit shapes (N)" disclosure, closed by default; a re-digitize reads as a
delta against `priorRun`; `COLOR_STOPS_HEAVY`, `LETTERING_TOO_SMALL` and
`STITCHES_TOO_SHORT` render as one-click adjustment chips offered AFTER the run
(Kent's call — an adjustment, not a pre-run form). `QualityReport` surfaces
trims. *(2026-09-02 — PRs #317/#318)* **Both "Make it bigger" chips offer a PARTIAL remedy, and the comment justifying them misquoted the finding it cited** — it read `LETTERING_TOO_SMALL`'s message as ending *"Enlarging helps"* when on that same commit it already ended *"...but does not fully clear it ... Remove or simplify the smallest lettering"*. Corrected in place with the history; the buttons are LEFT for Kent, since whether a partial remedy earns one is his call. `STITCHES_TOO_SHORT` no longer recommends enlarging at all and now names the shapes carrying the short steps — it and `LETTERING_TOO_SMALL` measure the same quantity at the same threshold (`MIN_COLUMN_MM` **is** `machine.MIN_STITCH_MM`) and it never fired alone over the corpus at 80 mm (the only width swept), but only **66%** of its short steps sit in a shape lettering named: the rest are sewable columns (1.1–3.2 mm median) with a narrow waist. **And the button itself is now measured: ONE PRESS CLEARS THE FINDING ON 1 OF 10** corpus fixtures (two presses on 4 of 10) and makes it **worse on 3** — `photo_dof_meadow` 0.36 → 0.58 → 0.71 — while the satin shape count rises on every fixture (2 → 9, 42 → 71), which is "the smallest shapes regenerate at any size" from the other side. No grade claim is drawn from that sweep: several checks move with size and 5 of the 10 are on the clamped floor. *(measured 2026-09-06 — `tools/short_satin_overlap.py`, `tools/enlarge_cure.py`, `tests/test_short_satin_shapes.py` (14); DOCTRINE)*

**`cfg.border` could never reach its own default — the Studio always sent one.**
`project.js` seeded `border: "off"` and `digitizer.js` sent the key
unconditionally. Now `null` = unset, key omitted when unset, panel says
"automatic" — `fill_angle_deg`'s sentinel shape. *(2026-09-02 — PR #318)*

**Preview thread width is PHYSICAL — neither widened nor narrowed.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 2.67 against the
ruled 0.15 mm fill row (rows overlap, as the professional's do) and 1.0 against
the 0.4 mm satin spacing; a fill at the ruled row looks solid because it IS. The
PDF sheet (`src/render.js`) and the SVG export draw the same width since
2026-09-04 — the sheet had drawn 1 px hairlines at any scale. Caveat: `lw` has a
1.2 px floor (1 px on the sheet), so the property holds zoomed in, not on a
thumbnail. Pinned on the literal 0.4 and both ratios. *(2026-09-04 — `preview.spec.js`)*

**Thread lighting is unverified against real thread** — eye-tuned, no sew-out to compare against. Treat the look as a preference, not a calibration. *(suspected 2026-08-25)*

**Typographic punctuation folds to its ASCII twin where a font lacks it.** A customer's phone substitutes U+2019 for an apostrophe silently and 26 of the 85 fonts have no glyph for it, so "Fritsch's Stitches" sewed as "Fritschs Stitches" (1,326 stitches against 1,354) under a note naming a character that looks identical to the one they typed. `satinfont.js TYPOGRAPHIC_FOLD` stitches the twin ONLY where the fancy form is missing — 367 font x character combinations rescued, and all 85 fonts hash identically on text that never needed it. Not NFKD: accented letters are different letters and stay unfolded (33–73 fonts cover the common ones, and the "these fonts can" message is good advice there). *(fixed 2026-09-07 — DOCTRINE; scope-history 09-07)*

**Lettering under the cap floor now names a way out.** The one verdict meaning "cannot be sewn" was the only one with no fix while the milder branch named two — 74 characters at the default left chest reads 1.3 mm against a 4 mm floor. Levers measured before being named: 3 lines 4.8 mm, 6 lines 6.3 mm, 18 characters 6.7 mm, full back 4.0 mm; 40 characters is still 3.1 mm, so line breaks lead and "fewer characters" is second. "Size up" is withheld at the width cap, the rule the hairline branch already followed. *(fixed 2026-09-07 — scope-history 09-07)*

### 4. Export formats — [detail](docs/scope/4-export-formats.md)

**Implemented (all six) · Confidence varies by format, not one score.**
DST, EXP, PES, **JEF**, SVG and the PDF worksheet, via both the browser encoders and the
service's `/export` route. One reachability caveat: `/export` is only reachable
from the product for purely-digitized designs — anything containing lettering
or manual shapes downloads through the browser encoders — **except JEF, which
the browser cannot write at all** and which therefore always goes through the
service, on every project type.

**Four more machine formats work and have no button (Kent's call).** `/health` also advertises `pec`, `vp3`, `xxx`, `u01`; one two-colour design exported in all nine and decoded with pystitch gives the same 99 stitches at 80.0 x 24.0 mm each, vp3/xxx/pec carrying the 2-thread colour table. **VP3 is Husqvarna Viking / Pfaff, XXX is Singer** — two major consumer brands whose owners cannot use the product today. Scope, not a doc-vs-reality gap like JEF: PRODUCT.md item 1 names PES and JEF and is silent on these four. *(measured 2026-09-07 — DOCTRINE; scope-history 09-07)*

**The printed worksheet now carries what the screen carries.** It stated size and stitch count, dropped trims and thread metres (two of the four numbers estimate.js calls what an operator needs before loading a machine), and printed a spool code without naming which of the 68 charts numbers it. Both fixed; the facts are computed once and passed, never re-derived at the sheet, and an e2e reads the screen and the real PDF bytes and requires them to agree verbatim. *(fixed 2026-09-07 — scope-history 09-07)*

- **DST — split by path.** Browser DST is Medium as Studio's sewn-and-shipping
  default, Low if treated as verified-correct-orientation in the abstract; that
  is the cross-cutting axis bug, same defect. Python `/export` DST is
  Medium-High by spec, not itself sew-verified.
- **EXP — Medium-High.** The 2-byte trim record (fatal to pyembroidery-convention
  readers at the first trim) and the phantom terminal end-stitch are both fixed.
  *(confirmed 2026-08-06 — PR #58)*
- **JEF (Janome) — SHIPPED 2026-09-07, and it had been counted as shipped since 2026-08-11 without a button.** PRODUCT.md launch item 1 ("PES hardened to byte-verified + JEF export") was marked Done on the evidence that `digitizer_service/formats.py` can write JEF. It can; the Download step offered DST/PES/EXP only, so **a Janome owner could not export anything from this product**. Same defect shape as the DST section below: the module was right and the product did not expose it. Now a button, disabled with a reason when the service is down (no browser JEF encoder exists). Verified by decoding `/export`'s bytes with `pystitch`, not by the writer existing: a logo the app reported as 80.5×16.6 mm, 2 colours, 2459 stitches reads back **2459 sewn, 80.5×16.6 mm, 1 colour change, 2 threads**. Medium-High, same ceiling as PES: pyembroidery cross-validation, not a verified Janome load. **Not shipped, but measured the same day:** VP3 (Husqvarna/Pfaff) 80.4×16.6, XXX (Singer) and PEC both 80.5×16.6, all 1 colour change and 2 threads — correct, and adding one is one line in `exporters.js`'s `SERVICE_ONLY_FORMATS` plus a button. **U01 (Barudan) is the one that needs work first: ZERO colour changes on a two-colour design.** Which machines this product supports is Kent's scope call, and PRODUCT.md's is DST/PES/JEF (+EXP). **Header defect found the same day, pinned rather than worked around: the JEF file DECLARES a hoop it does not fit.** `pystitch.JefWriter.get_jef_hoop_size` reads the design bbox correctly and then falls off the end of its own ladder to `HOOP_110X110` — the second smallest of its five codes — for anything ≥ 200 mm in either axis. Read off `/export`'s bytes: 199 mm → code 4 (200×200, fits); 201 mm → code 0 (110×110, does not). Reachable well past the four oversize garments: a **140 × 200 mm design fits the app's LARGEST hoop** and 150 × 240 fits the 6×10, so `hoopFitNote` is silent and the file is stamped 110×110 anyway — which is why the Studio's caveat is a persistent note beside the JEF button, not a line in the hoop-exceeds dialog (DOCTRINE). What a Janome does with the mismatch is gate 1 (no machine here), so the note says "may refuse" and names the two levers that are measured: under 200 mm the header is correct, and DST/EXP carry no hoop header at all (only `JefWriter` and `PesWriter` write one — PES deliberately not named). Rewriting the byte to code 4 is a live option for Kent, not shipped: it is still wrong for a 250 mm design and the case for it is a firmware claim. Pinned by `digitizer/tests/test_jef_hoop_code.py` (10 tests); if it goes red pystitch fixed it — drop the test and this note. *(2026-09-07)*
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

**Convert-to-text reaches ordinary lettering (2026-09-03)** — the badge and the per-cluster bar now appear on real wordmarks, one cluster per line in one ink; the e2e contract asserts per cluster instead of page-wide, the reason the first widening was reverted. *(fixed 2026-09-03 — area 1, area doc)*

**Right-click places a curved node, left-click a straight one**, coloured green
and indigo respectively. Ember's gesture and colour vocabulary, matched
deliberately. The default bow takes its side from the turn the path is making,
so a run of curved nodes arcs instead of scalloping. Backspace mid-draft takes
back the last node. *(confirmed 2026-08-25 — `curvedNodeThrough` tests + browser)*

**Detail moved to the area doc (2026-08-27, rule 5):** the copy/paste, Duplicate
and Dim-slider defects; the 2026-08-26 browser session (a canvas opening below
the fold, a raw file picker); and PR #269's eight-defect sweep. Two invariants
from them still govern and stay here: **the flat and realistic views must
produce the SAME block sequence** (a recurring colour is its own block in both),
and **manual/preset shapes sew in draw order** — `darkOnTop: false` on those
branches only, image mode keeps the heuristic because nothing in a raster says
which colour the artist meant on top. The sweep's reusable lesson: pin RULES,
not call sites — three of PR #264's nine defects existed because a fix was never
applied to its siblings. *(fixed 2026-08-26 — PR #269, mutation-checked;
[detail](docs/scope/5-review-manual-editing.md))*

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
   neither. **Name the SYMBOL, not a line number.** Swept 2026-09-07: this file
   and DOCTRINE carry only eight `file.ext:NNN` references between them —
   because the convention is already to cite a backticked function — and **two
   of the eight had drifted**, `stage6_blend.py:295-299` by forty lines onto a
   different function and `pipeline.py:92` onto the blank line above its own.
   Both claims were still true; only the pointers had moved, which is the worst
   kind of stale because the reader lands somewhere plausible. A claim with no pointer is unverified by definition. This exists
   because two suspicions in this document hardened into stated defects as they
   were copied forward, and both were later disproved by measurement; see
   Corrections in [`DOCTRINE.md`](DOCTRINE.md), kept precisely so that pattern
   stays visible.
4. **Budget: 800 lines.** Over it, compact before adding. The number has teeth
   on purpose — a skill already told agents to keep this file current, and it
   reached 5,400 lines anyway, one reasonable paragraph at a time.
   *(ruled 2026-08-14 — Kent, after the split measured 655 actual; the ~145
   lines of slack are deliberate, so a normal week of legitimate additions
   lands without forcing a compaction pass every time)*
   **The 2026-08-28 doctrine split landed at 657 — within two lines of that
   original 655.** The budget was never wrong; what it could not absorb was
   standing content, which does not go stale and so only ever grows. That is
   now `DOCTRINE.md`'s problem, and it has no budget by design.
5. **Overflow goes somewhere, never to the bin.** Three destinations, in order
   of preference: anything "was true then" to
   [`docs/scope-history.md`](docs/scope-history.md); anything still in force but
   not current STATUS — a ruling, a rejected approach, a correction, a trap — to
   [`DOCTRINE.md`](DOCTRINE.md); per-area supporting detail to
   [`docs/scope/`](docs/scope/), leaving the verdict and a link.
   **Nobody should ever have to delete something load-bearing to satisfy
   rule 4** — if that looks like the only option, say so rather than cutting.
6. **No test counts in prose.** They are stale within a day, nothing reads
   them, and every one the fact-check sampled was wrong.
