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

**START HERE for the real-artwork parity work:**
[`docs/handoff-2026-08-16.md`](docs/handoff-2026-08-16.md) — the honest baseline
(**42.5**, not the older ~70) and the metric's own **75-84** pro-vs-pro ceiling.
Its code and instruments are ON `main`. *(confirmed 2026-08-17 — `git ls-tree`)*

**Last updated:** 2026-10-20 (fifteenth pass, after PR #994, merged 2026-10-20: defect 57 and item 26 carry `satinSmallShapes`, built OFF, and the flip question). **This file is current state only, under a
27,000-word budget** (rule 4 below — Kent replaced the old line budget with it
on 2026-09-14). Its three companions: standing rulings, rejected approaches,
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
   **An open assumption under the whole 3.1x (2026-09-13):** the corpus was decoded from the pro's FILES, so it records what the file says, not what the MACHINE did; ten machine-side trim-threshold claims went to adversarial vote and all ten were refuted, and vendors publish no distance rule, so *"no single threshold reproduces this pro"* is the published model's expected shape. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(`docs/trade-knowledge-2026-09-13.md` §1, §6)*    *(2026-08-15/18/21, corrected 2026-09-06 — `docs/fragmentation-attribution-2026-08-18.md`, scope-history 09-06)*

5. **Satin-vs-fill routing sits at chance, and misroutes in BOTH directions.**
   The *mix* looked close by AREA; by THREAD it is not (2.2% against 44.3% —
   corrected 2026-09-04, DOCTRINE). **Partly closed, and the
   remainder is NOT the classifier: it is SEGMENTATION.** An oracle knowing
   the pro's per-shape answer scores 76.6% against our 55.4% — our regions
   straddle the pro's satin/fill boundaries. `docs/segmentation-alignment-
   2026-08-17.md` recommends NOT building the region-level fix (the straddle
is 95.8% grid noise). **The per-stroke rung was BUILT INERT 2026-09-05 and WIRED behind the flag 2026-09-06** — `classify_strokes` has no caller, but the pipeline consults the same reading via `_stroke_rung_takes`, so do NOT read "inert" as current. At the bare ≥ 0.75 area rule it reproduces Becker @ 100 mm 274.0 → 1,708.3 mm² exactly; the cap veto that shipped cuts that to **3 regions, 78.8 mm²**, and @ 80 mm it is byte-identical (Becker already reads 54.5%, above the pro). **Flipping it ON is Kent's** — render at `docs/renders/satin-per-stroke-2026-09-06/`. Full measurement: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-08-14/17, 2026-09-05/06 — `docs/satin-gate-attribution-2026-08-16.md` §9)*

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
    gates the fix and was DECLARED, not detected, until 2026-09-30 (the Studio
    now asks for detection on every job and declares nothing) — `owl_kent.jpg` reads LESS
    photographic than two logos, so a photograph left undeclared routes
gradient and the re-snap sews more spools than the cone list names. **Counted 2026-09-06** (`tools/resnap_escape.py`): **34 cones added corpus-wide, 25 outside the selected palette, every escape on the GRADIENT lane** — while all nine photo-class fixtures add none. The binding works; the lane real logo art routes to never got it. **FIXED, DEFAULT ON since 2026-09-10** (`cfg.bind_resnap_all_classes`, Kent's colour-bundle ruling; False is the pre-flip engine). It also closes half of defect 18's third mechanism — `screenshot` goes 17 blocks / 16 distinct with `3971` sewn twice, to 11 / 11 with no duplicate. Full trade: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-09-06 — scope-history 09-06)*
    **UI HALF FIXED 2026-09-02 (Kent's call), REMOVED 2026-09-30 (Kent's
    call — the Studio no longer carries any per-design class override; it
    sends `detect_photographic=true` and `faces_route_flat=true` instead, see
    area 3 and DOCTRINE 2026-09-30 "A face sews FLAT"):** the reading
    row's "It's a photo" correction sent `is_photographic` instead of
    `forced_class="photo_subject"`. It was answering the wrong question —
    forcing the FILL TIER rather than declaring content — and measurably
    hurt: owl_kent @ 80 mm goes 13 stops → **17** forced, vs **11 on 12
    cones** (from 14) declared, for ~6% more stitches. The flat-art override
was untouched that day; both went 09-30; flat returned that evening (DOCTRINE). **DETECTION BUILT 2026-09-11, DEFAULT OFF** (`cfg.detect_photographic`, stage 1.25): EXIF camera then the shipped YuNet detector; a hit fills `is_photographic` True — never False, never over a declaration — so it can only ADD photographs. **It changes nothing on this repo's artwork** (all 22 fixtures identical on and off; 0 false positives across 14 logos), which is both why it is safe and why it is unproven here; `owl_kent` is the real photograph BOTH signals miss, so the declaration stays the fallback. The value is on real uploads.
    also why it is unproven here. *(measured 2026-09-11 — `digitizer/tools/photo_signals.py`; `tests/test_photo_detection.py`, 28)* *(measured 2026-09-02; the earlier
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
*(2026-09-01 — `test_duplicate_cone_layers.py`, 13)* **A THIRD mechanism, found 2026-09-06 by `COLOR_STOPS_HEAVY`'s `repeated_cones` field, is EMPTY on its band route: 0 of 52 design/garment combos.** The 09-06 "4 of 52" was two band and two resnap cases; the resnap pair closed with `bind_resnap_all_classes` (ON since 09-10, defect 15) and the band pair (`region_blobs`, cone 0182) no longer reproduces; six gradient fixtures at 50 and 120 mm add none. A band fold was built (PR #827), measured INERT (0 of 52 combos change) and REMOVED on Kent's ruling (PR #835); `tools/cone_revisits` still flags a real band case as `band`. **What still repeats is not a band:** `repeated_cones` > 0 on 43 of 52 combos is almost all the `edge_cap` route (the cap sewn in a cone the artwork already loaded; `edge_cap_fold_into_colour`, PR #714, built OFF); the artwork repeats left are resnap (drone 0134/3574, bridge 0108) and plain (drone 1102/1305, golden_tee 0532) — the next target if this gets more work. `tests/test_cone_revisits.py` (8). *(measured 2026-10-11 — PR #827; removed 2026-10-11 — PR #835)*

19. **The design's own outer edge is uncapped — every fill row ends in open
    air.** The other sew-out edge finding, and one no per-shape border can reach: the silhouette is the union of several shapes' edges, so the
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
**MEASURED 2026-09-11, and GATED** (`tools/pro_silhouette.py`): ours, `edge_cap` off, **5.9–100.0% of the sewn silhouette carries no linear stitch** (Fremont 100.0, whitebg 82.6, gaulke 76.7, enthusiast 5.9); the pro carries a certified border on **at least 19.1–26.1%** of his fill edge, never in the fill's own colour block. Read differently ON PURPOSE — a stitch file has no run kinds, so his is a LOWER bound. Per-fixture tables, and the `unary_union` slowdown fixed 2026-09-12: [area 1](docs/scope/1-auto-digitizing-quality.md).
    *(built 2026-09-01 — `tests/test_edge_cap.py`, 18 passing)*
    **Rang hairline CRACKS as edges — FIXED 2026-09-08.** 20 sub-0.1 mm cracks
    in the silhouette union, owned by no region, cleared the loop gate's
    PERIMETER floor; `_fill_cracks` fills any interior the column cannot stand
    in — on an ABSOLUTE ruler while the feature scales, so one hole can get
    opposite verdicts at two sizes. *(2026-09-08 —
    `tests/test_edge_cap.py`)*
    **THE BILL OSCILLATES WITH SIZE, and the flip's `+5.9–26.3%` was a
    ONE-WIDTH reading** (80 mm): becker bills **+58.7% at 88 mm**, and a 0.3 mm
    larger design is 34% cheaper — the `omit` gate loses its input when the
    shape carrying most of the linear cover flips satin/fill on
    `_PROMOTE_EXPLAINED_MIN`, which is not monotone in design size. **COST
    CAPPED 2026-09-12** (Kent: cap the cost, leave `classify_ribbon` alone):
    `EDGE_CAP_BUDGET_PCT` 40.0, `"warn"` by default, so no stitch moves. The
    `edges` field reports silhouette rings now, having FALLEN as the bill rose.
    **The cause is NOT fixed**; `classify_ribbon`'s stability is the open
    project.
    *(measured 2026-09-12 — `docs/edge-cap-cliff-2026-09-12.md`;
    `tests/test_edge_cap_budget.py`)*

20. **Photo tonal splitting stacks thread past the pucker ceiling.** The bill
    for the ratified spec-decision-2 flip (`d3f3c547`), found only because the
    stale baseline remembered the before. `photo_scene_stub` `coverage_max`
    **4.40 → 6.44** on that commit, **7.18** today against a 3.5-layer ceiling
    — a `DENSITY_STACKED` **block** on a fixture that scored 64. Lane-wide:
    `photo_dof_meadow` 3.45 → 5.04, `same_hole_fraction` up **4–7x** — the
needle-breakage signal. ~~No off switch for photo classes~~ — stale when written; it landed 2026-09-01 (PR #316), so **the other half is measured: the tier costs −22,352 st / −16.4% of the photo lane, and with it OFF four of nine score HIGHER, none lower**, `coverage_max` falling wherever it moves. **A yardstick finding, not a flip** — nothing in the scorecard scores tonal gradation, and Kent ratified the tier (spec decision 2). `SAME_HOLE_RATE_MAX` is deliberately NOT retuned: its baseline is pro files at their own pitch, and the density-invariant half (`max_strikes`, `points_3plus`, `worst_at_mm`) is what got emitted instead. Full bill: [area 1](docs/scope/1-auto-digitizing-quality.md). `tests/test_same_hole_depth.py` (8). *(measured 2026-09-06 — scope-history 09-06)* **An instrument and a per-region cap are BUILT, the cap OFF (PR #867):** `layer_density.layer_stats` reads fill layers per 1 mm cell on preflight's own coverage map; `cfg.tonal_split_layer_cap` re-runs keeping whole each split parent within 1.5 mm of a cell past 3.5 layers. On today's fixtures it is all-or-nothing: where it acts (scene stub max 5.25 → 2.44 layers, owl_kent forced 9.57 → 4.00) it vetoes every split parent and equals the split-off arm; 8 of 10 tonal fixtures do not change. It reaches `pipeline.digitize` only, not the Studio service (nor does `tonal_split_ceiling`). Flip and service wiring are Kent's (gate 3); the missing evidence is a real tonal image where the cap is partial. *(measured 2026-10-13 — PR #867, `tools/layer_density.py`, `tests/test_tonal_layer_cap.py`)*

26. **Satin/fill classifier flips borderline shapes under boundary detail — MEASURED NEGATIVE on eight cures, intrinsic to the thresholds (2026-09-03).** 5 of 219 DT-judged verdicts flip when only the polygon's detail changes (4 on a threshold edge: cv 0.5, aspect 3, `explained` 0.80); spur pruning ×3, the sewing spur rule, a hybrid, raster smoothing ×2 and a regularity band leave 3–12 flips and change 2–48 shipped verdicts, so nothing ships; the mitigation is `_CURVE_MIN_PX_PER_MM`. Open only as a different construction (a margin with memory, or a polygon-native width profile) — Kent's call. `tools/ribbon_stability.py`. *(measured 2026-09-03 — `docs/classifier-stability-2026-09-03.md`)*

27. **Compression halos become their own cones — and the flat lane has dissolved them all along.** `stage2_quantize._quantize_population` runs "majority filter, then phantom-blend dissolve"; **the SLIC+RAG lane never got that pass**, so this is a missing PORT, not a missing idea. `logo_bridge_bar.jpg` pays it in six grey cones sewing the ringing around its black spokes. **FIXED, DEFAULT ON since 2026-10-20 (Kent, item 46)** (`cfg.dissolve_phantom_blends`): a merged label that is more than half boundary AND a Lab interpolation of its own two sides folds into the side it is nearer. Bridge Bar 74 → **32** regions, 14,607 → 11,524 st, **114 → 64** trims, silhouette −4.2%. **The fold's one wrong turn fixed 2026-09-30 (Kent's pick):** a member folded into the endpoint's LABEL rather than the instance of its colour it touches became a detached region, re-read from the source as grey and snapped to teal — nine specks on the ring; folded into the black it borders, bridge reads 80 → **20** regions, 16,179 → 11,385 st, **101 → 43** trims on the shipped engine, the other five gradient logos untouched by the redirect (`docs/eye-pairs-2026-09-30/`, on the page for his flip). **Read the cone count (13 → 11) LAST** — five of six greys go, all four real cones survive, and three NEW cones arrive on artwork the palette could not afford; what changed is what the cones SEW, by the palette's worst excess **20.76 → 3.68** dE00. Residual: `0111` Whale survives as 12 shards, cause not established. **Kent did not flip it on the day**, citing two mild negatives and the five-of-six residual; the flip is a one-line default plus a 26-fixture scorecard recapture, to be decided alongside other gradient-lane work. The eleven-fixture bill and the page-label direction tests: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-09-04 — scope-history 09-04; `tests/test_phantom_blend_photo.py`)* **Same lane, 2026-09-30: `snap_region_edges` ON (Kent, on renders)** — region edges follow pixels, not SEEDS superpixels; his Instagram icon 44 → 28 trims, drone's `THREAD_MATCH_POOR` blocks 5 → 3. *(scope-history 2026-10-01)*

28. **The largest quality wall in the corpus is three problems wearing one code — and one of them is two floors set 4× apart.** `THREAD_MATCH_POOR:block` grades **7 of 26 fixtures F 0** (14 of 52 matrix entries), all `gradient`, which is where real logo art goes. Decomposed 2026-09-06, re-read 09-07: **(1) the raw yardstick, 4 of 7** — `golden_tee`, `drone_render`, `region_blobs`, `summit_badge` clear every block once scored on EXCESS over the loaded spools, the photo route's 2026-08-24 rescoring that the gradient lane never got; reproducible with `tools/spool_remedy.py --yardstick`. **The offender set MOVES WITH THE YARDSTICK**, so a probe that keeps the raw top and reports its excess gets this wrong. **(2) halo cones — RETRACTED 2026-09-07, the category is EMPTY**: on the fixed tree defect 27's flag is byte-identical on gaulke, so the wall decomposes 4 + 0 + 2 and **gaulke is the seventh, unexplained** (worst ΔE 63.6). **(3) the clamp floor:** the score clamps at 0, and a floored design sits hundreds of points under water — `golden_tee` needs ~312 points and ~11 blocking findings before its grade moves one letter — which is why a real thread fix here moves nothing. Un-clamping re-bases every grade, so it is a product call, Kent's. Full decomposition: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-09-06/07 — yardstick-disagreements rows 3 and 6)*

47. **`overlap_mm` is one scalar at 0.25 mm, against a law that wants 1.0–2.0 — its ANGLE half is BUILT OFF since 2026-10-08 (PR #700), unrecorded here until 10-11.** Law 26 asks 1.0 mm where parallel stitch directions meet on wovens, 1.5–2.0 on knits/fleece and ~0 near-perpendicular. `cfg.overlap_by_angle`, DEFAULT OFF: an earlier plain-tatami fill underlaps a later one by `overlap_mm + (OVERLAP_FABRIC_FACTOR · overlap_parallel_mm − overlap_mm) · |cos Δθ|`, Δθ between the two fills' ROW directions — 1.0 mm parallel, today's 0.25 perpendicular (never thinner than today, after Kent's black-at-seams finding); satin, bean and other techniques keep the scalar. Read through `seam_underlap.measure`: drone's parallel seams 0.371 → 0.636 mm mean, 453.5 → 31.2 mm of them under 0.5, for +1.2% stitches; Fremont has no parallel fill→fill seam, so it barely moves (its shortfall is the held-hole tongue, defect 6). `stage5_overlap.OVERLAP_FABRIC_FACTOR` 1.0 is the gate-1 placeholder for the knit figure (PR #823). **Card block 6 owns** the flip, the knit factor and the perpendicular floor. [Backlog](docs/scope/machine-physics-backlog.md) row 9: Gated. *(measured 2026-10-11 — PR #823, `tools/overlap_by_angle.py`, `tests/test_overlap_by_angle.py`)* **The FORBID-GAP half is BUILT OFF since 2026-10-12 (PR #846):** `cfg.forbid_gap_mm`, None by default (0.8 mm is the gate-1 candidate, card block 6). Set, stage 5 closes a bare strip under the threshold between two stitched colours by handing it to the colour sewn FIRST, so the later colour keeps its artwork edge (Kent's 09-09 seam ruling); never widens a gap, leaves a third colour's fill and same-thread pairs alone. Read on the cloth by `seam_underlap.narrow_gaps`: drone 27 → 2 open gaps (+12 trims), bridge 14 → 1, Fremont and Becker have none; OFF byte-identical on three fixtures. A failed weld now plans on the artwork, never the strip (PR #857; 0 of 88 corpus strips fail). **What still stands before a flip is "Waiting on Kent" 44.** *(measured 2026-10-11/12 — PRs #846, #857, `tools/forbid_gap.py`, `tests/test_forbid_gap.py`)* The same lane found defect 61.

49. **A letter's tapered apex sews BARE under `satin_rail_comp` — CLOSED 2026-09-30 behind `cfg.satin_crown_cover`, ON BY DEFAULT since Kent's flip 2026-10-02.** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-49-moved-from-the-live-list-as-it-stood-after-pr-968). *(measured 2026-09-30 — `tests/test_apex_is_real.py`, `tests/test_crown_cover.py`; scope-history 09-30)*
50. **`satin_lettering_split` leaves holes at the crowns of curved letters — CLOSED behind `cfg.satin_crown_cover`, built OFF 2026-09-30, ON BY DEFAULT since Kent's flip 2026-10-02.** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-50-moved-from-the-live-list-as-it-stood-after-pr-968). *(measured 2026-09-30 — `tests/test_crown_cover.py`; scope-history 09-30)*
51. **Low-resolution line art lost its fine detail at the TRACER'S GRID, not in the file — FIXED, `cfg.work_px_per_mm` ON at 8.0 (Kent's flip 2026-10-01, on renders; None = the engine before it).** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-51-moved-from-the-live-list-as-it-stood-after-pr-968). *(measured 2026-10-01 — `tools/lowres_detail.py`; `tests/test_work_grid.py`)*
52. **A fill in the BROWSER engine carries thread across every hole and every notch — CLOSED in all three Studio lanes by `fillColumns` (manual 2026-10-07, shapes and image 2026-10-08, Kent's calls).** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-52-moved-from-the-live-list-as-it-stood-after-pr-968). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`; `test/fill.test.js`, `test/digitize.test.js`; flipped 2026-10-07/08 — `generate.js`)*

55. **A hand-drawn shape with an anchor a pixel from the last one sews a spike at that corner, under every preset — THE GESTURE THAT MADE THEM IS CURED 2026-10-03 (Kent's pick); the offset is not, so saved shapes keep theirs.** Found by the audit of defect 54's fix. A double-click is two clicks and a `dblclick`, and `ManualPanel.onCanvasClick` took the second as an anchor unless it landed within 0.5 canvas px of the first (`DUP_POINT_EPS_PX`): a slip of a pixel left an anchor a pixel from the last. The short edge to it doubles back, and the BROWSER builder's `offsetRing` gives its end the whole mitre clamp, three times the pull compensation: defect 54's wedge, from a NEAR repeat, which 54's cure (1e-9 px, rounding) does not reach and should not. A 40 mm box whose second click was 1 px off: fill **1.73 mm past the drawn ring on terry, where a clean corner has 0.85**; cap 1.13 against 0.57; pique 0.73 against 0.42. Of 80 slips of 0.6 to 3 px, 20 were refused as crossing (the double-click finished nothing) and 60 kept; on terry 30 of the 60 sew over 0.15 mm further out than a clean corner, at worst 1.81 mm. **Cured at the gesture:** the second click of a double-click (`detail` 2) is no click of its own, however far the pointer slipped. In a real browser three slips of four went wrong before and none does now. **Still open:** a shape saved before the cure keeps its anchor and its spike, and two anchors dragged to one hoop corner make another (the audit's measure, not re-run here). Curing those means the offset (a bevel past the clamp), which moves every sharp corner under a preset: not built, and Kent's call. *(measured 2026-10-03 — `tools/closed-ring-census.mjs` table 4; `app/src/ui/ManualPanel.spec.js`, `app/e2e/manual-double-click.spec.js`; scope-history 10-03)*

57. **The BROWSER's medial satin: its skeleton, its walk and its ends CURED (PR #817, merged 2026-10-11 on Kent's arming: "Waiting on Kent" 26); its remainder — a star's centre, a round end's last cross, small squares and dots — BUILT OFF behind `satinSmallShapes` (PR #994, merged 2026-10-20), the flip Kent's (item 26).** **Cured by #817** (a bar's "skeleton" was an L along the grid's edge and the tracer walked strokes twice): one spare cell, one pixel to one edge, a free end run out to the outline. No satin bar has a stitch over 9.1 mm (was 100.6); of 320 hand-drawn satin arcs none has thread over open ground (167 had). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). **What ships (OFF):** a round end's last cross stands up to 0.46 mm outside it; a square or dot up to 6 mm takes the outline-split fallback, 12% in from each end; a satin star's longest stitch is a median 21 mm, cast arm to arm across a centre sewn once per arm. **ON (`satinSmallShapes: true` on `buildQualityDesign`), no new mm constant:** a cross's end outside the drawn shape is pulled onto the outline (a round end's last cross becomes a chord of the cap); a shape with no stroke at `ringToSpines`' floor is sewn as the smallest column along the ring's principal axis; a junction of three or more arms (a star's centre, a T) is cut at its inscribed disc and sewn once as one zone. OFF is byte-identical (six md5 pins, `test/satin-small-shapes.test.js`). Left chest, OFF → ON: 10 mm five-point star longest stitch 8.02 → 4.60 mm, centre sewn once not five times, cover 99.7% → 96.9% (tips capped, plan extent 9.6 mm); 10 × 2 mm round-ended stroke needle outside 0.35 → 0.20 mm (0.15 is pull comp), sewn 9.4 mm; 1 mm dot cover 67.5% → 100%; T set to satin 10.40 → 2.53 mm. **Costs:** a sharp tip is capped like a round end (0.2 mm shorter a tip in the plan), round ends sew 0.3 mm short, and ON reaches every junction of every satin letter in the image lane, not drawn. Sheet and table: [`docs/renders/browser-satin-small-shapes/`](docs/renders/browser-satin-small-shapes/README.md). **Reach:** every browser satin shape; no fill, no lettering. The star's tier is a separate open item (26). Not sewn. *(measured 2026-10-03, built 2026-10-04 — `tools/satin-walk-census.mjs`; measured 2026-10-20 — PR #994, `tools/satin-small-shapes.mjs`)*

58. **Black-and-white logos sewed in four to six cones — anti-alias grey on thin strokes. FIXED: `cfg.two_tone_snap` is DEFAULT ON since 2026-10-11 (PR #821, Kent's approval of 10-08; False is the pre-flip engine).** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-58-moved-from-the-live-list-as-it-stood-after-pr-968). *(measured 2026-10-11 — PR #821, `tools/two_tone_probe.py`; renders `docs/renders/two-tone-lines-2026-10-08/`)*

59. **The skeleton satin tier fans a sharp lettering junction — Becker's N, M and E under `letterform_priors` (ON 2026-10-07); DIAGNOSED, moot on the default path since `lettering_columns` went ON (Kent, 2026-10-12, PR #863); OPEN only where a caller sets the lane OFF.** Kent: *the "N" was better before - everything else was better after* *(ruled 2026-10-07 — `docs/eye-pairs-2026-10-07/kent-notes.json`)*. Mechanism: three of the refit N's five junction ends read as tapered TIPS (the neighbour's far edge 4.56–4.81 mm along the end tangent, reach 4.84) where the trace's five read as meetings; `satin_tip_caps` caps each and `_extend_to_cap` runs it through the other stroke: 45 of 213 crosses over 1.6 W (22 pull-aware; the trace 1) *(measured 2026-10-07 — `docs/n-fan-2026-10-07.md`)*. Corpus, pull-aware: becker 56 over-long (M 17, N 22, E 16), drone 9, the rest ≤ 2; `satin_join_square` 56 → 56; `lettering_columns` 56 → 0, drone 9 → 0 *(measured 2026-10-07 — `tools/fan_census.py`)*. Unfixed; the gate is the node's degree. Not sewn.

60. **The join-corner cut read ENTHUSIAST's S bowls as corners and `satin_join_square` pulled both members' ends off the apex — FIXED 2026-10-07 by the bend cap.** Detail moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#defect-60-moved-from-the-live-list-as-it-stood-after-pr-968). *(confirmed 2026-10-15 — moved verbatim, area 1)*

61. **Stage 5's clip cuts a shape in pieces and keeps one — HALF FIXED: the parent keeps its INK by default since 2026-10-12 (Kent, PR #856); the cut-off pieces still drop, OFF behind `cfg.clip_keep_pieces`.** Where a shape's artwork overlaps an earlier colour's, the clip can split it, and `_largest_polygon` kept the piece largest by SEWN area — which can be underlap tongue carrying no ink while the ink is the piece thrown away. **Worst case `logo_gaulke_roofing`:** the black roof line `Se9512992` (18.10 mm² of ink) sewed its 24.30 mm² tongue under the white and none of the line. **`ARTWORK_UNCOVERED` is blind to it** (thin stroke, read as rim), so no grade ever showed it. Corpus: a split carrying ink on **6 of 23 fixtures** (drone, gaulke, golden_tee, bridge, chrome, sunset). **ON (`clip_parent_keeps_ink`, default True):** the parent keeps the piece with the most artwork; four fixtures change (drone, gaulke, bridge −0.5% stitches, chrome — its `ARTWORK_UNCOVERED:info` clears), no grade falls; False is the engine before it. Render: [`docs/renders/clip-parent-ink-2026-10-12/`](docs/renders/clip-parent-ink-2026-10-12/gaulke_roof_line.png). **Still OFF, Kent's (item 46):** `clip_keep_pieces` keeps every other piece over the stage-4 floor as `<parent>-clip<k>` and counts sub-floor slivers in `CLIP_DROPPED_SLIVER` (silent in the Studio); it restores drone's 8.36 mm² and golden_tee's 9.12 mm², but bridge pays **+5.1% stitches, +4/+6 trims** sewing more of its grey JPEG halo. **The scorecard baseline was NOT recaptured** for the flip (cloud Linux only; attribute drone, gaulke, bridge and chrome to #856 at the next capture). **Twins (PRs #855, #857, #861):** stage 4's `max(outers)` is latent (0 of 7,106 masks have a second island, tripwire test); the forbid-gap weld's twin is fixed; the hairline twin is latent (0 of 52 corpus rows lose ink). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). Not sewn. *(measured 2026-10-12 — PRs #853, #855, #856, #861; `tools/clip_keep_pieces.py`, `tests/test_clip_keep_pieces.py`, `tests/test_stage4_contours.py`)*

### Closed — kept numbered, because ten other docs cite them by number

Full text: [`docs/scope-history.md`](docs/scope-history.md). Pointers, not status. **One entry per line — `scope_budget.py` parses
these, and ten other docs cite the numbers.** Caveats on 3, 16 and 17 moved to
DOCTRINE 2026-09-14.

1. shade-thread collapse (`_shade_blocks`) — RESOLVED 2026-08-19.
29. the panel printed the SERVER's filesystem path to the customer, a FAMILY of three unavailability warnings — FIXED 2026-09-07. Lesson kept: a warning written for an operator reaches a buyer. Full text: scope-history 09-30.
31. "Colors (max 6)" was not enforced on the lane real customer logos take — FIXED BEHIND A FLAG 2026-09-07 (`enforce_color_cap`, ON since 2026-09-10). The slider is a pricing promise: every cone is a spool and a re-thread. Full text: scope-history 09-30.
33. the shopping list renamed the customer's threads — FIXED 2026-09-07. `loadPreferredPaletteId()` defaulted to Studio's 56 generic shade names for every first-time customer, over the real spools the design was digitized to. Full text: scope-history 09-30.
34. the size the app reported was the BOX the design was fit to, not the thread — FIXED 2026-09-07. 65.6% of designs sew outside that box; the export gate now reads the thread's own extent. Full text: scope-history 09-30.
35. two upload defects, both found by dropping a file on the panel — FIXED 2026-09-07: the error message could not render in the case that needed it, and a rejected file left the panel in a half-state. Full text: scope-history 09-30.
36. "This font can't stitch «Р», «у», «с». Try a different font" was a dead end — FIXED 2026-09-07. Measured over all 85 `.embf`: 3 fonts cover Cyrillic, 3 Greek, 2 Hebrew, none Japanese/Korean/Arabic; the message now names one that can. Full text: scope-history 09-30.
38. the simulator counted STRANDS while the caption under it counted stitches, nine apart on one screen — FIXED 2026-09-07 (`strandStitchOrdinals`; the total is the LAST ORDINAL, not `design.stitchCount`). Full text: scope-history 10-07.
40. "size up for crisp letters" was advice the DEFAULT (auto-fit) design cannot take — FIXED 2026-09-07 (`letteringNote` reads the REQUEST `sizeMm` and swaps only the advice clause). Full text: scope-history 10-07.
44. satin borders sat a median 1.4–1.9 mm INSIDE every abutting colour (14 of 17 bordered shapes on the 80 mm icon) — FIXED 2026-09-09 on Kent's ruling that the colour sewn on top owns a shared seam (`_owned_by_later`, `border_runs(omit=…)`; 33,292 → 30,420 st, trims 34 → 30). Standing ruling: DOCTRINE. Full text: scope-history 09-29.
45. no preset declared its assumed stabilizer; backing was guessed from stitch count — RESOLVED 2026-09-20 (`Fabric.assumed_backing` / `needs_topper`, both engines; the worksheet prints both). Playbook law 33.
46. the smoothness scores existed only offline and preflight could not see them — BUILT 2026-10-03 AS METRICS, both halves: Law 37's direction-change score (`curve_roughness_deg`, read with `curve_turn_gini`, `curve_vertices`, `curve_corner_vertices`, `curve_traces`) and edge deviation per tier (`edge_wobble_{satin,border,fill,line}_{p95,std,max}_mm`). No finding, no deduction, nothing in the Studio, so the GRADE stays blind to both on purpose: Law 37 forbids a cutoff, and Kent ruled 2026-10-02 that the tool does not warn the customer about what it should fix. Baseline recaptured 2026-10-04 at `6e0cb943`, every row carrying all 17 keys, so `corpus_scorecard.diff` reports their drift from the next change on. Still true: neither number has met Kent's eye; roughness cannot read intent, so it compares a design with itself and is never a grade; `edge_smoothness` stays offline. Not `curve_turn_deg`, which an earlier read scored as this. Playbook law 37; `tests/test_curve_roughness_metrics.py`, `tests/test_edge_wobble_metrics.py`; scope-history 10-03.
48. no machine-time model, so nothing quoted a runtime — RESOLVED 2026-09-20 (`machine.PLAN_SPM` 650, `TRIM_COST_STITCHES` 120; the worksheet prints "Run time ~N min … incl. trims"). Playbook laws 36/38.
53. a ring inside a hole of its own shape (an ISLAND, carried in `holes`) was a second hole to the BROWSER builder — FIXED 2026-10-03 (`islandsAmong`, `digitize.js`). Nested rings whose areas summed to the outline's sewed NOTHING (a 40 mm box, rings 4 and 8 mm in); a preset's pull compensation SHRANK an island (terry: its fill 0.6 mm small a side, the underlay showing round it). An island now grows as the outline does, or is sewn as drawn where growing would bring it against the ring beside it or across itself; a ring thinner than one needle step (0.1 mm) is no island. **Exported stitches change for island shapes and no others**; neither lane the Studio builds through makes one (`groupRingsIntoShapes` and direct callers do). Older than `fillColumns`, the same with it off or on. Independently audited, four passes; what a thin moat costs is in the full text. `test/digitize.test.js`. Full text: scope-history 10-03.
56. a walk in the BROWSER's skeleton tracer never ended, and the satin emitter sewed what only its guard had stopped — FIXED 2026-10-03 (in `skeletonEdges`, `satin.js`; its rule was replaced 10-04 by one pixel to one edge, defect 57). A 20 mm star off the shape tool sewed 48,645 stitches; exported stitches change only where a walk reached the guard, and no fill moves. **Its cost:** the knot had been covering small round shapes, and a 2 mm one now sews four stitches (small dots are in defect 57's remainder). `test/satin-walk.test.js`. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#fifteenth-pass-overflow-moved-from-master_scope-2026-10-20); scope-history 10-03.
41. the review screen quoted a sew-out's cost on one lane and nothing on the other — FIXED 2026-09-07 (`lib/estimate.js`, browser-side only when the service said nothing). Full text: scope-history 09-20.
42. five buyer-visible Studio-screen defects, all found by driving the app — ALL FIXED 2026-09-08 (#416/#417/#418). Full text: scope-history 09-20. Still the evidence for At-a-glance area 3's "driving, not reading" note.
54. a ring that says a point TWICE running (handed over CLOSED) got a WEDGE from the BROWSER builder's `offsetRing` — FIXED 2026-10-03 (`distinctCorners`, `digitize.js`). A 40 mm box on terry was filled 1.8 mm outside the drawing at its first corner, where 0.6 is right. **Exported stitches change for a ring that says a point twice, under a preset or with `fillColumns`, and for no other** (4,536 outputs on rings that do not: identical). No Studio lane hands over an EXACT repeat; a NEAR repeat is defect 55 (gesture cured, offset open). `tools/closed-ring-census.mjs`, `test/digitize.test.js`. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass); scope-history 10-03.
3. 14 jump-trims on an 80mm design — RETIRED 2026-09-01 (Kent) as UNREPRODUCIBLE. Do NOT read the 08-31 repro as a regression (DOCTRINE 09-14). Live concern: defect 4.
7. satin dropped a bracket's tab on `enthusiast_logo` (`_prune_spurs`) — RESOLVED 2026-08-21.
8. build-font dropped SVG transforms on four fonts — RESOLVED 2026-08-22.
9. the photo route escaped its own palette, both halves — RESOLVED 2026-08-24 (PR #217 + the 08-24 `shade_palette_bind` flip, default ON per Kent's 32-job-sheet ruling).
10. three photo-route robustness defects the first real photos found — RESOLVED 2026-08-23 (#214 OOM, #218 `select_palette` loop, #216 preflight).
11. the memory ceiling was per-region full-frame masks — RESOLVED 2026-08-24 (PR #230).
12. preflight graded every photo job F — RESOLVED 2026-08-24 (PR #229).
13. the detail layer sewed the background a cutout had just removed — RESOLVED 2026-08-24. **Its lesson stands: no acceptance arm had EVER set that flag**, which is the blind spot the evaluation-harness section exists to close.
14. half the cloth bare inside each shape is the THREAD-PAINT TIER, not a density bug — ANSWERED 2026-08-25 (streamline covers 0.55-0.59 of its footprint vs the filled tier's 0.99; Kent's filled-for-high-contrast ruling, and the face exception, are in Standing rulings).
16. one spool revisited across other colours, THE RE-SNAP MECHANISM — RESOLVED 2026-08-31 (`rehome_resnapped_regions`; owl 17 → 14 blocks). **The SYMPTOM is not gone — defect 18 is a second mechanism.** scope-history 08-31; DOCTRINE 09-14.
17. sew order had no craft layering, BORDER SATIN OPENED THE DESIGN — FIXED, DEFAULT ON 2026-09-01 (Kent, PR #302). Repro ring 0.0% → 54.5%, stitches unchanged; found on cloth. Owed golden re-capture: DOCTRINE 09-14. `tests/test_borders_last.py`.
21. fill travel laid OVER sewn columns — FIXED, DEFAULT ON 2026-09-03 (Kent, `fill_travel_under_cover`, PR #323), with `fill_bridge_cut` ON since 2026-09-19. The residual bridges are the column ORDER's, not routing's (88% have no unsewn corridor; four fixes priced out, DOCTRINE). Full text: area 1, "Defects 21–25 in full".
22. small curves sewed as polygons — FIXED, DEFAULT ON 2026-09-03 (Kent, `curve_turn_deg` 15, gated to 20 px/mm by `_CURVE_MIN_PX_PER_MM`; the 60 → 61 mm cliff is his to accept). Full text: area 1.
23. rail dents — FIXED 2026-09-03 (Kent); `satin_rails_follow_edge=True` stays parked, `"envelope"` ON since 2026-09-30. Its cost is overshoot, not bare art (`lost_frac` ships split, 2026-09-20). Full text: area 1.
24. hairline columns (< 0.6 mm) — the MECHANISM FIXED 2026-09-03: a 3-pass bean along the spine in both engines; whether it reads better on cloth than a dropped bar is card block 5's, `pending sew-out`. The thread-weight hairline tier of 2026-10-12 is area 1's. Full text: area 1.
25. fill stitches halved by float dust at the stitch-length threshold — FIXED 2026-09-03 (Kent, `stitches.SPLIT_TOLERANCE_MM`; `tools/fill_dust.py`). Full text: area 1.
30. the review screen's per-layer cone list named threads its layer does not sew — FIXED, DEFAULT ON since 2026-09-13 (`layer_palette_from_regions`; review-only, stitches identical off vs on, 26/26). Kent's accepted price: duplicate review ROWS (0 → 13 at 6 colours); folding them is the open follow-up and moves sew order. Full text: area 1, "Defects 30 and 32 in full".
32. the low-resolution warning could not fire — it tested the resolution after stage 1's own upscale — FIXED 2026-09-07, no flag: `INPUT_LOW_RESOLUTION` reads `Prep.input_px_per_mm` and names the number and the multiple; 2 of 26 fixtures arrive under the floor (becker, bridge). The warning's line and the tracer's grid are two numbers since 2026-09-30 (defect 51). Full text: area 1.
37. two launch-scope tools sat behind an unannounced right-click — FIXED 2026-09-07 (one sentence on the empty canvas; Kent's right-click placement untouched). Full text: area 3 doc.
39. "Exceeds your 8x8 in hoop" named a fix that does not exist on four of ten garments — FIXED 2026-09-07 (`hoopFitNote`, message only); the open half CLOSED 2026-10-13 — auto-fit caps to the largest hoop (Kent's ruling, PR #865; area 3). Full text: area 3 doc.
43. the numbers chain (caption, recap, PDF, pystitch-read DST, simulator) agrees end to end — MEASURED 2026-09-08 by driving each link, not by a shared code path. Full text: area 3 doc.

---

## Latent — gated OFF, DO NOT FLIP without rebuilding its instrument

Safe only because it ships off. **A green suite is not evidence** — on chaining
one concealed it; entry 2 is a flag that LEFT this list unnoticed for two weeks.

1. **`chain_links` — sews needle-down thread on bare fabric.** 16.15 mm exposed
   over 17 links, stock preset, green suite. Both shipped instruments were
   blind; the replacement then erred the other way and was fixed 2026-09-02
   (residual: a `-shadeN` id) — the numbers are in the pointers below. **A third
   blind spot (2026-10-13, PR #895) — FIXED 2026-10-14 (PR #937):**
   `tests/test_chaining.py::_thread_bare_mm` counted the walk-in after a trimmed
   jump as thread; it now reads `tools.hairline_travel.scan`. See "Waiting on Kent" 45.
   **Still DO NOT FLIP, permanently:**
   gate 1 names link cover tolerance and the sew-out is accepted as-is. Largest
   lever on defects 4 and 6. **The tolerance now has a published rival
   (Embird's 2-3 mm), and card block 7 — the sew-out that answers it — is
   DRAFTED, NOT BUILT:** `tools/sewout_card.py` emits blocks 1-6.
   *(`docs/trade-knowledge-2026-09-13.md` §2a)*
   *(`docs/hardening-closeout-2026-08-02.md`;
   [2026-09-02](docs/scorecard-baseline-attribution-2026-09-02.md))*
2. ~~`split_tonal_regions`~~ — **NOT LATENT: ON for photo classes since
   2026-08-19**, and this list said otherwise for two weeks. Ratified
   2026-09-02, left gate 3; cost is defect 20. Why the old read was wrong,
   and the rule it cost — **a per-class default cannot be confirmed from a
   dataclass line** — is DOCTRINE. *(`pipeline.effective_split_tonal`)*
3. **`strip_letterbox` — ON by default since 2026-09-14**, and its shadow-strip half since 09-15 (`letterbox.detect_edge_strips`, trimming only once bars are found). A phone screenshot's black bars read as ink and inverted the design: ground sewn in white thread, the logo left as negative space. OFF stays the pre-flip engine byte for byte. Why it was held OFF first, and what the shadow strips cost: DOCTRINE "A fixture's PATHOLOGY can be load-bearing"; scope-history 09-14/15.

4. **`cap_center_out` — cap sew order, built OFF.** The Python lane never
   read `garment_id` for ORDER; the browser engine did. **DO NOT FLIP:**
   only the cost is measured, and it is heavy. *(measured 2026-09-19 — DOCTRINE)*

5. **`satin_cap_recentre` — ON since 2026-10-03 (Kent's flip, on his labelled
   sitting); it left this list and keeps its number.** A free end whose spine
   tail is a surviving CAP FORK is cut at the kink and rebuilt square, where
   on a stem with one edge leaning three degrees the column tapered to a point
   at one corner and left the other bare. The cause-side twin of
   `satin_rails_follow_edge`. Small by its own record, and a wash on the flat
   end of a curved column. False is the pre-flip engine, byte for byte.
   *(flipped 2026-10-03 — `docs/eye-pairs-2026-10-03/README.md`; numbers DOCTRINE 2026-09-19)*

*(added 2026-08-17 — `docs/project-review-2026-08-16.md` §1.6: chaining was absent
here, so a good-faith flip would have shipped bare-fabric thread unwarned.)*

---

## Doctrine — moved to [`DOCTRINE.md`](DOCTRINE.md)

**Standing rulings, Measured negatives, Corrections and Gotchas live in [`DOCTRINE.md`](DOCTRINE.md)** (split 2026-08-28). Read it before proposing work, the same way you read this file for status: it answers what has already been decided, tried, disproved or paid for, which never goes stale, while this file answers where the project stands today, under a word budget.

---

## At a glance

| Area | Status | Confidence |
|---|---|---|
| 1. Auto-digitizing quality (image → stitches) | In progress | **Low** beyond flat spot-color art; human faces TABLED pending a more capable tier *(Kent, 2026-08-25)* |
| 2. Font library & lettering | Implemented — 85 fonts, satin + bean/running + cross-stitch, LTR + Hebrew RTL | High (tech) / High (compliance). Zero stunted glyphs since the 2026-08-22 transform fix; the guards now assert their own coverage |
| 3. Studio app / configurator | Implemented | Medium (fabric-preset accuracy: **pending sew-out** — the 2026-09-01 icon was uncontrolled, so the card still gates this). Held at Medium by that gate alone. **The wizard is gone (2026-09-30, PR #585)** — one panel, a summary bar, a Download sheet; spec `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`. **All four configurator PRs are merged** — PR 4's theme (white page, 13 px type, WCAG-AA text held by `theme-contrast.spec.js`; detail moved to the area doc) and **PR 3's progressive disclosure (PR #845): each editor opens on spec §5's Visible column, the rest behind one `Advanced ›` fold, closed on load and remembered for the session only; the fold sits under each editor's essentials, which Kent kept and §2.2 now says (2026-10-12, PR #852)** *(built and driven 2026-10-01, 2026-10-11 — `theme-contrast.spec.js`, `Advanced.spec.js`, `ContentStep.advanced.spec.js`)*. **PR 2 (#586): a Polo/Hat/Tee garment row, and an Original view registered only for browser-traced art (open: the service must return the art's content box)** *(built and driven 2026-09-30 — `GarmentPicker.spec.js`, `configurator-smoke.spec.js`)*. **Every display-layer defect this area has had came from DRIVING the app, none from reading it** — three sweeps, detail in the area doc and defect 42. The preview renders thread as a lit cylinder at physical width, eye-tuned not sew-verified; the customer can crop to the logo before the run *(2026-09-28)* |
| 4. Export formats | Implemented | Varies by format — see below |
| 5. Stitch-out review & manual editing tools | Implemented — Kent's direct-manipulation request is **complete** (2026-08-13) | High. Every surviving requirement of the 2026-08-12 request ships: outlines+nodes on the canvas, the pulse cue, select-then-edit, node drag, line drag, add node, delete. Requirement 5 (whole-shape drag) was withdrawn by Kent. Every interaction was driven in a real browser against a live service. Manual draw mode traces over the uploaded artwork; right-click places a curved node |

---

## Waiting on Kent

The decision queue. Everything OPEN here is blocked on a call only Kent can
make, not on engineering effort; a resolved entry keeps its number rather than
being deleted, same as the defect list. Detail stays in its own section rather
than duplicated here, so this list can go stale about WHAT IS OPEN but never
about the facts.

1. **RESOLVED 2026-08-22 — the stage 0-4 cache is funded and built**, split at the review-edit seam. *(tests/test_generation_cache.py)*

9. **RESOLVED 2026-08-24 — tonal v1: shade escape closed, `bound_shade` ships ON** as the photo-route default. *(area 1)*

**Also open, same category — so this queue is not a half-truth. All predate
2026-08-14 except where noted:**

0. **RESOLVED 2026-10-02 — Kent flipped `satin_crown_cover` ON** (scope-history 10-02; the question as it stood: scope-history 2026-10-06). Defect 50.

2. **RESOLVED 2026-09-08 — the DST codec is fixed, both directions**, and never needed the call; retired from gate 1 the same day. *(DOCTRINE 2026-09-07/08; ROADMAP gate 1)*
3. **RESOLVED 2026-08-19, ratified 2026-09-02 — `split_tonal_regions` is ON for photo classes** (`effective_split_tonal`). Cost: defect 20.
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
7. **RESOLVED 2026-09-15 — of the 26 glyphs that sewed nothing, the 20
   `roaring_twenties_KOR`/`_small` ones sew again; 6 stay a GATE 1 refusal.**
   Detail: scope-history 2026-10-07.
   *(resolved 2026-09-15 — `test/font-dead-glyphs.test.js`; detail: area 2)*
10. **RESOLVED 2026-08-25 — Studio typography: "tighter and more editorial."** Kent's standing direction; new UI is set to it, not re-litigated. *(area doc)*

11. **RESOLVED 2026-09-02 (Kent's call) — `cfg.is_photographic` is reachable from the UI.** Detection remains open as defect 15. *(confirmed 2026-09-07; correction in DOCTRINE)*

8. **Font lawyer consult — optional.** Only gates RESTORING the 13 pulled
   ShareAlike fonts; the brief is written and ready to send. Nothing waits
   on it. See the font-licence entry.

12. **Merge a tiny cone into an ADJACENT SHADE — TABLED, Kent 2026-09-02:**
   *"I'm honestly not concerned about the hopping idea, we can table this one
   for a further discussion."* Do not build the shade-merge or further hopping
   polish until he reopens it; the 08-31 mechanical fixes are merged and
   unaffected. Defensible adjacent-shade pairs and their ΔE:
   [area 1](docs/scope/1-auto-digitizing-quality.md). *(tabled 2026-09-02 — Kent)*

13. **RESOLVED 2026-09-03 — the stitch-angle rule is ADOPTED (cap 30°)**, both passes built and flipped ON by Kent. *(area 1)*

14. **RESOLVED 2026-09-12 for XXX and VP3 — Kent's scope call.** `SERVICE_ONLY_FORMATS` is `{jef, xxx, vp3}`, both with buttons; PEC and U01 stay OUT. Two rulings that still govern: **U01 is held for want of a surviving thread palette and a real Barudan reader, NOT for the two hold-reasons once recorded — both were measured wrong**, and VP3's 0.1 mm quantisation is deliberately not surfaced to the customer. Evidence is a committed harness; run it rather than re-derive it. *(`digitizer/tools/format_roundtrip.py`; PRODUCT.md item 1)*

15. **RESOLVED 2026-09-12 — the wizard's steps are browser history entries** Detail: scope-history 2026-10-07 (moved for the word budget). *(resolved 2026-09-12)*
17. **RESOLVED 2026-09-17 (Kent) — clearing a stale BORDER recovers on ONE click**, a stale BOUNDARY on two. Kept: "Clear them" is an explicit click, so nothing is dropped behind the user's back — what "recovery is explicit" protects. Do NOT gate recovery out of the fast lane to tidy this. *(`e2e/digitize-stale-edits.spec.js`)*

18. **RESOLVED 2026-10-13 — "Faster photo reorder" (Kent): both steps merged, no flag** (PRs #868, #871): `owl_kent` 148 → 114 s with byte-identical
   stitches, no coverage lost. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-13 — PRs #868, #871, [`docs/photo-cold-profile-2026-10-13.md`](docs/photo-cold-profile-2026-10-13.md); renders `docs/renders/photo-reorder-fast-2026-10-13/`)*

19. **RESOLVED 2026-10-03 — `satin_cap_recentre` is ON** (Kent's ruling in chat,
   on his sitting: after on becker and tires, before on none; Latent 5).
   `satin_patch_junctions = "satin"` was never waiting — the junction stack's
   part C since 2026-09-19 — and `satin_walk_cursor_reach_mm` stays parked for
   cloth (Kent 2026-09-20). *(flipped 2026-10-03 — `docs/eye-pairs-2026-10-03/README.md`)*

20. **Paired ground truth costs money or it does not exist.** No free source
   ships artwork PLUS a professional's stitch file of the same design, and the
   licence chain fails even where a licence exists. The free route's ceiling
   was taken: cutting the artwork panel out of vendors' two-panel previews grew
   the corpus **5 artwork fixtures over 5 clients → 11 over 8**, at zero cost.
   Anything past it is the ~$400 the organic review proposed spending on
   commercial digitizers — Kent's. *(measured 2026-09-28 —
   [`docs/paired-ground-truth-sourcing-2026-09-28.md`](docs/paired-ground-truth-sourcing-2026-09-28.md))*

16. **RESOLVED 2026-10-11 — a hand-set sew order now reaches the file (Kent chose option A, PR #830).** `moveBlock`/`moveShape` pin every sewable
   shape's layer, so a later tier change no longer gets the borders-last move; the engine half (option B, not taken) stays pinned red-on-fix by
   `test_a_partial_pin_is_still_lost_by_the_engine`. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(confirmed 2026-10-11 — `digitizer/tests/test_manual_sew_order.py`; `DigitizePanel.spec.js`, `digitizer.spec.js`)*

21. **`bean_letter_max_stroke_mm` at 1.0 — JUDGED 2026-10-03, stays OFF.** Small traced lettering as bean runs along the skeleton of its SOURCE INK.
   Kent put today's satin ahead on five of six logos and called bridge both bad; his reason is the line's WEIGHT (*"little worms"*, *"to skinny"*) while
   granting fremont's path reads cleaner. His: a heavier line on the same path, or drop it. "Too thin" is `suspected` (the render draws three passes as
   one thread); gate 1 holds a 3-pass bean on knit as `pending sew-out`. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(judged 2026-10-03 — `docs/eye-pairs-2026-10-03/kent-notes.json`)*
22. **RESOLVED 2026-10-08 — `fillColumns` ON in all three browser lanes** (manual 10-07; shapes and image lane 10-08, Kent's call with the price in
   front of him). Image lane: floats off the fill 188,952 → 484, stitches **+10.4%**. **Kent's standing ask:** the next ten digitized images shown to him carry
   the off/on float picture (`tools/fill-columns-image-sheet.mjs`). None of it is sewn. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-08 — PR #697, `docs/renders/fill-columns-lanes-2026-10-08/price.md`)*
23. **Flip `ties` on for the browser lanes — NEW 2026-10-03, built OFF in both builders.** Every
   trim in a browser-lane file leaves two unlocked ends; the Python lane locks every one. One rule for both builders, at
   0.8 mm: lettering +3% to +8% stitches, shapes about +1%, no cut added; on shapes one lock in five lands on a stitch
   under 0.3 mm. **Not sewn** (a candidate for the sew-out card). A flip is `ties: true` at `generate.js`'s four call sites
   and a re-pin of every snapshot. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(measured 2026-10-03 — [`docs/lock-stitches-2026-10-03.md`](docs/lock-stitches-2026-10-03.md))*
24. **Flip `fillStagger` on for the browser shape lanes — NEW 2026-10-03, built OFF.** The shape builder's
   needle holes line up row to row (94%; 86% head three in a line); the flag moves them onto the Python fill's shifted
   grid for +7% stitches and leaves a line of dashes about 2 mm inside a straight edge. **Not sewn from this lane:** flip
   now, or sew one square and look. A flip is `fillStagger: true` at `generate.js`'s three shape call sites and a
   re-pin. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(measured 2026-10-03 — [`docs/renders/fill-stagger-2026-10-03/`](docs/renders/fill-stagger-2026-10-03/README.md))*
25. **Flip `dedupeHoles` on for the browser shape lanes — NEW 2026-10-03, built OFF.** Rounding to the file's
   0.1 mm puts the needle twice in one hole about twice a design in what ships; the flag lays the first only. **Not
   sewn.** A flip is `dedupeHoles: true` at three call sites and a re-pin; lettering has its own and no flag yet.
   Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   *(measured 2026-10-03 — [`docs/sub-unit-stitches-2026-10-03.md`](docs/sub-unit-stitches-2026-10-03.md))*
26. **Defect 57's cure — ARMED by Kent 2026-10-11 on the port's sheets (PR #817); its remainder BUILT OFF behind `satinSmallShapes` (PR #994, merged 2026-10-20), and the flip is his.**
   #817 moves every browser satin shape and no fill; its underlay direction is ON (item 40). #994 cures round ends, small
   squares and dots and a star's centre with no new constant (mechanism and numbers: defect 57; sheet: [`docs/renders/browser-satin-small-shapes/`](docs/renders/browser-satin-small-shapes/README.md)).
   **Three options:** (a) flip it whole (the engine default, as #1000 did for `dedupeHoles`, plus a re-pin): every sharp tip and round end sews 0.2–0.3 mm short in the plan; (b) flip it with a
   sharp-tip exemption (an angle or a tier; NOT built, gate 1); (c) leave it OFF: 8 mm star stitches, a centre sewn five times, 0.3 mm of round-end overshoot. **The star's tier is still a
   separate open item**, untouched by #994: a whole-rung branch guard (the whole rung inside the shape, not its midpoint) would send most satin stars to fill, which nothing has sewn.
   Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#fifteenth-pass-overflow-moved-from-master_scope-2026-10-20).
   *(ruled 2026-10-11 — defect 57; built 2026-10-20 — PR #994, `test/satin-small-shapes.test.js`)*
27. **Underlay under fills.** `blend_fallback_underlay` flipped ON
   *(ruled 2026-10-07 — scope-history 10-07)*; `cross_tatami` is a picker
   choice. The knit presets stay yours. **Not sewn.**
   *(measured 2026-10-05 — [`docs/underlay-audit-2026-10-05.md`](docs/underlay-audit-2026-10-05.md))*
28. **`cutFloats` — ON for the manual and basic-shape lanes 2026-10-08, after 22**
   (manual #672, basic shapes #682); the image lane passes nothing. A float a DST machine reads as a
   cut gets a `trim`; no stitch moves. Manual, with `fillColumns`: 4,264 →
   0 such cuts on 5,400 designs, trims +0.79 a design, which EXP and PES
   gain as unlocked cuts while `ties` (23) is off. **Not sewn.**
   *(measured 2026-10-08 — [`docs/cut-floats-manual-2026-10-08.md`](docs/cut-floats-manual-2026-10-08.md); `generate.spec.js`)*
29. **RESOLVED 2026-10-07 — Kent flipped `letterform_priors_k` ON at 0.75** on the
   labelled thread pairs (becker "after", bridge "both bad"); the N is defect 59.
   *(ruled 2026-10-07 — `docs/eye-pairs-2026-10-07/kent-notes.json`; [`docs/letterform-priors-2026-10-06.md`](docs/letterform-priors-2026-10-06.md))*
30. **RESOLVED 2026-10-07 — `satin_join_square` ON again with the bend cap**
   after its guards held Kent's 10-06 flip for one lost ENTHUSIAST element
   (defect 60, fixed the same day). *(measured 2026-10-07 — PR #663, the flip PR; DOCTRINE 2026-10-07)*

31. **RESOLVED 2026-10-12 — Kent ruled `lettering_columns` ON by default** (PR #863);
   the 10-07 sitting's pitch question is history (scope-history 10-13). Item 37.

32. **Four default-OFF flags on one contact sheet — NEW 2026-10-08 (PR #786).** OFF beside ON on real art, nothing sewn. Two have
   since flipped (`two_tone_snap` ON 2026-10-11, PR #821; `lettering_columns` ON 2026-10-12, PR #863); `lettering_words` stays OFF
   (item 37). Still open: `satin_tip_corner_gate` (defect 59, #677; Becker trims 60 → 59, shifts junction ends on every logo) and the
   image lane's cuts-vs-stitches patch (#697 candidate C: summit_badge −4% stitches for 38 → 1,219 cuts; only a sew-out prices a cut
   against a stitch). *(measured 2026-10-08 — PR #786, `docs/renders/off-flags-2026-10-08/`; `digitizer/tools/off_flags_sheet.py`)*
33. **Satin pull compensation: per rail or total? — gate 1, OPEN.** The browser's
   `pullCompMm` is the total (a 2.5 mm column sews 2.8 mm); the digitizer's
   `pull_comp_mm` is per rail (3.1 mm). A physical constant, so a sew-out
   settles it. Ruling relayed by the foreman 2026-10-08: leave both until it
   becomes a real problem; pinned as-is by `test/engine-service-parity.test.js`,
   which also pins defect 57's 30.3 mm bar stitch as `todo`.
   *(measured 2026-10-08 — PR #768)*
34. **RESOLVED 2026-10-08 — Kent ruled the twelve unrecorded logos cleared to keep**
   (`digitizer/testdata/art/`'s six; script tires, hotel fremont, bridge bar,
   golden tee, gaulke roofing, the golke phone screenshot). Manifest rows now
   `client-cleared-by-kent`, review flag dropped; the derived `docs/renders/`
   rows keep theirs. A new fixture fails CI without a manifest row.
   *(ruled 2026-10-08 — `docs/asset-provenance.json`, `test/asset-provenance.test.js`; PR #717)*
35. **RESOLVED 2026-10-08 — Kent flipped `satin_free_end_square` and
   `satin_slab_serifs` ON** on the four-arm render: a free end lands square, a
   foot or T slab sews as its own short column. *(ruled 2026-10-08 — PR #679)*
36. **RESOLVED 2026-10-11 — `blend_bands_share_cone` REMOVED** (Kent; PR #835):
   built in #827 for defect 18's band route, inert on all 52 combos.
37. **RESOLVED 2026-10-12 — the Column lane is ON by default (Kent's ruling, PR #863; renders PR #869).** `lettering_columns` True, `lettering_words`
   False: with words OFF the lane reads the two old taggers. Blockers closed: rails at the satin tier's reach (#837), the slanted fan (#844), sew order
   (#859). ON vs OFF, real `digitize()`: `lost_frac` lower at all six fixture-widths (golden_tee 50 0.6700 → 0.6103, fremont 0.0302 → 0.0184, becker
   0.0236 → 0.0186), no new colour change, trims never up; wrong-colour rises a little on golden_tee, the sew-order price. **Still open:**
   - **Letter reach, gate 1:** fremont's and golden_tee's letters stand 0.06–0.07 mm inside shipped's reach, every fanned slant face 0.19 mm outside
     its traced edge; card v2 block H ([`docs/sewout/card-v2-2026-10-13/`](docs/sewout/card-v2-2026-10-13/)) sews the pair. Not sewn.
   - **The word tagger misses glyphs at 50 mm (#889, #900), no dominant rule.** 58 of 190 expected glyphs sit in no word at 50 mm (15 at 100 mm); `nested` (18) is a MEASURED NEGATIVE: five nesting policies each gain 8–28 glyphs only with 8–29 new strays, and what separates bridge's line is the word's SHAPE, not containment. Nothing shipped, no flag. Fix before any `lettering_words` flip. `tools/word_tagger_trace.py`. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   - **Non-letter capture — all three guards ON.** `lettering_columns_skip_blobs` and `lettering_columns_ink_link` (Kent, option A, PR #890) and
     `lettering_columns_icon_guard` (**Kent, 2026-10-13, PR #899**): skeleton nodes ≥ 24 refuse screenshot's three white truck-drawing pieces and none of 130
     hand-labelled letters; the other eleven measured fixtures identical. The 24-node, 1.0 mm and 0.40/0.95 cuts are candidate shape ratios from one corpus,
     not cloth constants. Scorecard baseline NOT recaptured (the screenshot row moves). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass).
   - **Lowercase (#887, #896):** a lowercase station cross folds past 45° 1.4% of the time against 0.0% for capitals (u, b, g, m);
     `lettering_columns_fold_cuts` (OFF) is NOT flip-ready (item 50). The 80 mm synthetic i stem (2.124 mm²) sews a RUN: stage 7's small-shape rescue
     (`routes_to_run`, under `min_detail_mm`² 2.25) fires before the lane is asked; `lettering_columns_small_stem` (OFF, item 52) keeps it for the lane.
     The i DOT (0.446 mm²) is dropped separately, by `RUN_MIN_LOOP_MM` 2.2 (a cloth value, gate 1).
     **#921 (merged, `fold_cuts` still OFF):** the 80 mm e's ring is opened at its bar (e stations past 45° 1 → 0; lowercase share 1.37% OFF → 0.00%; the 18 capitals unchanged by it); `fold_cuts` ON at **50 mm already moves capital G, 1 of 144 stations past 45° (0.00% → 0.69%)** — pre-existing from #887/#893, look before any flip. **That G is cured by #972 (MERGED 2026-10-15, flag still OFF): at 50 mm it sews exactly as OFF, 0 of 139 capital stations past 45°; item 50.** *(measured 2026-10-14/15 — PRs #921, #972, `tools/lowercase_angle.py`)*
   *(measured 2026-10-12/13 — PRs #859, #863, #869, #877, #881, #885, #887, #889, #890, #891, #896, #899, #900, [`docs/renders/lettering-columns-on/`](docs/renders/lettering-columns-on/),
   `tests/test_column_capture.py`, `tests/test_lowercase_angle.py`, `tests/test_word_tagger_trace.py`; confirmed 2026-10-13 — `config.py`; full prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-13-fourth-pass))*
38. **RESOLVED 2026-10-12 — `coverage_edges` is a NO (Kent).** `cfg.coverage_edges` is
   DEPRECATED: still readable, default False, OFF path untouched; setting it True
   warns once, naming the ruling. Evidence it rested on: PRs #818, #824, #841
   (`tools/counter_slots.py` stays). *(confirmed 2026-10-12 — PR #852,
   `tests/test_coverage_edges.py`)*
39. **`bg_structural` flip — waits on real tonal art, NEW 2026-10-11.** Area 1's two stage-1 background defects, fixed OFF. Before any flip:
   `photo_chrome_specular` changes verdict ABSENT → background (read as a fix) and `test_preflight` uses it as the full-bleed guard, so that guard moves to
   another fixture first; its three constants were chosen on mostly synthetic fixtures, and ON can change `px_per_mm` (summit traced on 949 px, not 900).
   Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-11 — PR #825, `tests/test_bg_structural.py`)*
40. **RESOLVED 2026-10-11 — `underlayDirection` ON by default** (Kent; PR #836;
   `underlayDirection: false` restores the old order). Two logos: needle-up
   −3.9% (hotel_fremont) and −3.0% (logo_whitebg), three-jump runs 157 → 152
   and 8 → 6, trims and stitches unchanged; lettering
   (`buildLetteringDesign`) is still not covered. Not sewn. *(measured
   2026-10-11 — PR #836, `tools/underlay-direction-logo-sheet.mjs`)*
41. **`subpixel_edges_min_px_per_mm` — LEFT UNSET (Kent 2026-10-11); open: the corner-run flip.** A floor under the native edge read clears Becker's outline
   reversals at 1.8 px/mm (7.1 → 0.0 per 100 mm) but returns the 0.68 mm source-pixel staircase the 09-18 flip fixed (right-angle turns 26.5 → 81.3 per 100 mm).
   The reversals' own cure is BUILT OFF as `subpixel_corner_runs` (PR #834: 7.1 → 0.9 per 100 mm, turns 26.5 → 20.1, area 1); flipping it is his.
   Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-11 — PRs #826, #834, [`docs/subpixel-res-gate-2026-10-11.md`](docs/subpixel-res-gate-2026-10-11.md))*
42. **A fresh BLINDED sitting — Kent RULED 2026-10-13: source 4+ flat lettering logos FIRST, then rebuild to 48–60 pairs and sit.** The art is his to
   supply. PR #886 built the machinery and a 27-pair kit from the six logos that qualify (pre-registered; `analyse` prints kappa with 95% bootstrap CIs and n,
   never a raw agreement). Three of its six arms pass the manipulation check; at about 27 pairs a sides-only kappa interval is near ±0.5, so the kit alone
   licenses nothing. **Rulings: no `mfab_lc` / `toat_beanie` extras (the same designs at another crop), no satin-density knob.** Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass).
   *(ruled 2026-10-13 — PRs #847, #886, [`docs/eye-pairs-2026-10-13/wok42/README.md`](docs/eye-pairs-2026-10-13/wok42/README.md))*
43. **RESOLVED 2026-10-12 — the `Advanced ›` fold stays under each editor's
   essentials (Kent);** spec §2.2 amended to match #845. Still not built: a
   "sewn colours" row for digitized art, and a fold on the multi-select group
   panel. *(confirmed 2026-10-12 —
   PR #852, `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`)*
44. **`forbid_gap_mm` flip — Kent RULED 2026-10-13: sew-out first (card v2 block G; card v3's G is the same block, #910); the flip waits on it.** Defect 47's
   forbid-gap half, built OFF. Priced (PR #874, measure and render only): at 0.8 mm over the 26 scorecard fixtures, bare cloth under 0.8 mm between colours
   126.6 → 6.2 mm² (−95%), stitches +0.41% (bridge +3.7%), trims −14, 0 failed welds. 0.8 mm is a physical constant (gate 1), so candidates only. Full text:
   [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-12/13 — PRs #846, #857, #874, #877, `docs/wok44-forbid-gap-bill-2026-10-12.md`)*
45. **The hairline tier — built OFF; the flip waits on a sew-out (gate 1).** Thread weight, the tier (PR #848), ground under strands (#850), the per-strand
   gate (#851), a drop guard (#879, no flag; **Kent RULED 2026-10-13 (via the director): keep the 2% share rule, not literal "any dropped strand"**), a
   coverage guard (#888, `hairline_coverage_guard`), the lines route (#882, `hairline_from_lines`, photo lanes) and a strand test (#897,
   `hairline_lines_strand_test`) are in, every flag OFF. Card v1: [`docs/sewout/hairline-card-2026-10-12/`](docs/sewout/hairline-card-2026-10-12/README.md)
   (blocks A–E, 40 and 60 wt). Flipping `hairline`, `hairline_over_ground`, every 60/75 wt value and the 1.5 mm stitch wait on sewing it. With both guards bare
   fabric stays within 0.3–1.5 mm² of OFF on four logos, but gaulke's 7.06 mm² ground gap is not cured (#892: rim; the one lever left is `hairline_run_width_mm`,
   gate 1). The strand test (#897) halves owl_kent's barring (31 → 15) and keeps the 5 bristles but drops the head-outline wisps (37 → 7), so it stays OFF; **#973's mass exemption (below) is the named fix for the stack-of-hair half.**
   **Hairline travel (#895, MEASURED NEGATIVE):** the rise in thread over bare fabric is trimmed FLIGHTS, not thread. **INSTRUMENT BLIND SPOT — FIXED 2026-10-14 (PR #937, merged, instrument only):**
   `tests/test_chaining.py::_thread_bare_mm` now reads `tools.hairline_travel.scan`: a trimmed jump is a flight, not walk-in thread
   (the old reading kept as `_thread_bare_mm_untrimmed`). golden_tee 80 mm / 40 wt hairline OFF / ON 19.65 / 93.96 → **0.94 / 0.45 mm** (hairline adds no thread over
   bare fabric); full_back 93 mm chain OFF / ON 7.75 / 6.53 → 2.54 / 1.31; benchmark 93 mm chain OFF already lays 3.31 mm over bare fabric and chaining cuts it to 2.25.
   Sampling noise ~0.1 mm per stretch: do not read single-digit `exposed` counts. **Hair reach (#915) and chaining (#917):** the Studio sends `owl_kent` down `gradient`, which the line route excludes; forced there it sews 52 strands (4 in the bristle box) and +36 trims. **RULED 2026-10-14, 12:15 CDT (VP relay of Kent): `hairline_lines_chain` stays OFF until a sew-out;** card v3.2 block O (#949, merged) carries it, and its 8 mm cap is untested above 3.14 mm. **`cfg.hairline_lines_gradient` (#942, merged, OFF):** the line route as a supplement on the gradient lane; owl_kent via the Studio route +18 trims, but 3 of 9 logos move (drone +17, screenshot +8, golden_tee +3), so a flip adds 3% to 13% trims there; the flip is Kent's, after card v1. **`cfg.hairline_lines_logo_refusal` (#971, MERGED 2026-10-15, OFF; read only when the supplement runs, so inert without `hairline_lines_gradient` and its three prerequisite flags):** a third refusal for rendered-logo line detail, in three keys: `refused_logo_edge` (at least 0.6 of a line's length within 0.15 mm of a shape's boundary), `refused_logo_flat` (at least 0.15 of the band's pixels with a 3×3 L* std under 1.0) and `refused_logo_pattern` (median 3×3 L* std at least 14). With it ON, **all 9 corpus logos are byte-identical to supplement OFF, including the three #942 moved** (drone 148 → 131 trims, screenshot 73 → 65, golden_tee 53 → 50; 0.0 mm² bare); `hair_strands` and `hair_fine` unchanged. **owl_kent keeps its 4 bristle-box strands, but 4 is exactly the floor (no margin), and 4 of its 20 supplement strands are refused, all outside the box (3 breast, 1 elsewhere), taking 4 trims back (295 → 291).** Constants fitted in-sample on three logos and owl_kent, all gate-1 candidates; stage 0 neither read nor changed. `hairline_lines_gradient` itself stays OFF. **`cfg.hairline_lines_strand_mass` (#973, MERGED 2026-10-15, OFF; inert unless `hairline`, `hairline_from_lines` and `hairline_lines_strand_test` are all on):** the mass exemption #897 named. A line the strand test would refuse as a bar is kept when at least 0.95 of the same-polarity lines its stacked stations' rays cross pass the ridge test themselves, or at least 0.75 do and the median distance to the nearest is within 3 thread widths (1.2 mm at 40 wt). A drawn mane (28 strands about 1.0 mm apart) goes from **4 of 34 dark strands sewn with the test to 33 of 34** (the route with no test sews all 34); #882's 8-strand synthetic keeps 8 of 8 with a plan byte-identical to test OFF; the six-thin-bar synthetic of #897 now reads as hair. owl_kent: breast barring held at **15 of 31 by a strand-share margin of only about 0.03** (no breast strand taken back), bristles 5 of 5, fringe 7 → 12 of 37 (light wisps on the left of the head); cost 5 strands, 30 stitches, +1 trim (402 → 403). The 9 logos and the drawn-hair fixtures are byte-identical. **Limits:** "dense" is in thread widths of the design, so the same mane drawn a third larger (1.34 mm apart) keeps only 21 of 32 (66%); a uniform stack of thin lines reads as hair whatever drew it (pinned by a test); constants fitted in-sample on owl_kent and two synthetics, no real fur or hair photograph in the corpus (C10, Kent's). All three constants are gate-1 candidates. **Fur regions (#925) MEASURED NEGATIVE** (all 28 corpus rows byte-identical; item 58). **`detail_layer` vs `hairline_from_lines` (#928) RULED 2026-10-14 (Kent, via the VP): KEEP BOTH.** **`detail_layer_stitch` (#940, merged, OFF, default `"bean"`):** `"run"` takes owl_kent's stitches under 1 mm from 5,267 to 0. **Hair reach vs design size (#961, merged, measure only):** the fall in owl_kent's bristle-box strands (4 / 2 / 1 at 127 / 180 / 250 mm) is the ridge test's side offset, held in mm on a raster whose pixel is fixed; FDoG finds the same ~540 lines at every size and the ridge test keeps 84 / 27 / 7. Holding the side sample in source pixels restores the population (strands 52 / 53 / 47) but lifts the bristle box 4 / 7 / 7 and brings back the eye-ring outline, beak strands and breast barring: false positives, nothing counted against ground truth. `cfg.hairline_lines_side_in_source_px` (OFF) is a proposal, UNBUILT; it needs a false-positive guard first (the strand test's `_STACK_*` mm constants were not probed), and every value is a gate-1 candidate. Full text of this paragraph (#895 to #942), moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#ninth-pass-overflow-moved-from-master_scope-2026-10-15). *(measured 2026-10-15 — PR #961, `tools/hair_reach.py size`, `docs/renders/hair-reach-size-proof/`)*
   *(measured 2026-10-12/14 — PRs #872, #876, #879, #882, #888, #892, #895, #897, #915, #925, #928, #937, #940, #942, #949, #971, #973, `tools/hairline_logo_refusal.py`, `tools/hairline_strand_mass.py`, `docs/renders/hairline-lines-logo-refusal/`, `docs/renders/strand-mass-exemption/`, `tools/hair_reach.py`, `tools/hairline_lines_gradient.py`, `tools/detail_vs_lines.py`, `tools/hairline_logo_bill.py`, `tools/hairline_coverage.py`,
   `tests/test_hairline_travel.py`, `docs/hairline-photo-trial-2026-10-12.md`)*
47. **`small_print_floor` flip — waits on card v2 block F (gate 1).** PRs #873, #878, #880, #923; flag OFF, OFF byte-identical (md5 pins). At 3–4 mm caps a
   counter sewn shut is the worst defect, so the flag keeps counters stage 4 drops and holds penetrations half a laid width off them (Column lane, run and fill
   tiers). Measured (40 wt render, not cloth): BOARD at 3 mm counters shut 8/10 → 2/10; Fremont's tagline 0/4 shut at 3–5 mm; costs +25–52 stitches.
   **#923 (merged) cured three causes inside it:** the synthetic 0's counters beside the slash 0.29 / 0.39 → 0.74 / 0.79 open (BOARD 3 mm 2/10 → 0/10 shut), golden_tee's
   O 0.42 → 0.62; costs at 3 mm +39 stitches, +1 trim, covered 0.981 → 0.973. Still shut: golden_tee's O at 4 and 5 mm. **Residue (PR #988, merged 2026-10-20; Kent 2026-10-19: "Leave OFF for now"):** the gradient lane's stage 3 absorbs the counter's bands into the O at 5 mm (3.33 → 5.95 mm²) and rescues the keyline as a Silver disc at 4 mm. `cfg.open_cored_counters` (`stage3_segment.cored_counters`), built OFF, carries it as a hole (0.90 mm² at 4 mm, 0.77 at 5), but the satin tiers still cross it: open 0.00 → 0.14 at 5 mm with the floor ON, 0.15 → 0.20 at 4 mm; the phone screenshot gains five false positives (−69 stitches, −2 trims); 16 of 17 corpus designs byte-identical. Stays OFF until a satin hold-off of the traced hole and a lettering-only guard exist (a session is building both behind that flag). *(measured 2026-10-19/20 — PR #988)* **60 wt (#919, census, n = 1 trace per cell):** 60 wt alone does not open counters at 3 mm (BOARD OFF 8/10 shut at both weights, open 0.31 vs 0.34); the
   floor ON does the work at both; 60 wt costs +9 to +13% stitches. **Look before any flip: ON narrows the narrowest column to 0.43–0.48 mm and lays crosses to 0.35 mm,
   under `SATIN_MIN_CROSS_MM` 0.5** (BOARD 4 mm: 0.64 → 0.43 at 40 wt; Fremont 60 wt 2.5 mm: 0.48) — whether such a cross sews is a card question. **Card v3.1's F3 arm 2
   drifts after #923 (+1 stitch, at most 0.1 mm; the committed DST sews the pre-#923 floor): RULED 2026-10-14 (via the VP) ACCEPTED — no re-cut, noted in the card README
   on the next card lane.** **At Kent's 81 mm hat replay it does the opposite (#905): all four tagline counters shut** (bare share 0.10–0.24 each; +150 stitches, +2 trims;
   the A's are item 54's case); it is a counter flag, not a tier flag, and at 92.5 mm it keeps the three A's open. Counter floor (one laid width) and hold are
   candidates; block F sews BOARD at 4 and 3 mm, OFF/ON. Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). *(measured 2026-10-13/14 — PRs #873, #878, #880, #877, #919, #923, #905,
   `tools/small_print.py`, `tools/small_print_census.py`, `tests/test_small_print.py`)*
48. **RESOLVED 2026-10-13 — `lettering_columns_skip_blobs` and `lettering_columns_ink_link` are ON (Kent,
   option A, PR #890).** Detail: the Column lane entry (37). *(ruled 2026-10-13 — PR #890;
   confirmed 2026-10-13 — `config.py`)*
49. **RESOLVED 2026-10-13 — Kent ruled `lettering_columns_icon_guard` ON (PR #899, option A).** Numbers and the
   candidate-constant caveat: item 37. *(ruled 2026-10-13 — PR #899; confirmed 2026-10-13 — `config.py`,
   `tests/test_column_capture.py`)*
50. **`lettering_columns_fold_cuts` — built OFF, now FLIP-READY (Kent's call): the sewn judge plus a coverage guard (PR #986, MERGED 2026-10-19) cure the 120 mm p and the 80 mm crossed legs; earlier: the 50 mm G and the u/b knot (PR #972, 2026-10-15).** #986 (all behind `fold_cuts`, OFF plans byte-identical to main at three cells): each candidate cut is sewn through `column_runs` and read with `outline_cut.sewn_knots`, and `COVER_SLACK` 0.5 W² refuses a candidate that leaves more bare. No glyph sews worse ON than OFF on any count; 80 mm lowercase folds 5 → 0, crossed legs 75 → 46; 120 mm folds 13 → 2, crossed legs 97 → 64; capitals sew as OFF. **Cost: ON digitizes the word 2 to 3.4 times slower than main ON** (80 mm 150 → 368 s, 120 mm 185 → 353 s, 50 mm 52 → 178 s, laptop under load). Gate 1: `COVER_SLACK`, `SEWN_FOLD_DEG`, `SEWN_SHORT_FRAC`, `STALL_FRAC`, `FOLD_DEG`, `FOLD_MIN`, `STUB_WIDTHS`, `TURN_MAX_DEG` are shape ratios from one synthetic word, nothing sewn. *(measured 2026-10-19 — PR #986, `docs/renders/fold-cuts-p-crossed/`)* **The PR #972/#887 record below is the superseded detail; its "Open before any flip" list is now cured.** The u and b junctions traded a
   fold for a knot of short crosses; #921 cured the 80 mm e. **#972, all behind `fold_cuts` (OFF path byte-identical, construction pin passes):** (1) the 50 mm G takes OFF's cut when the stub refusal and the ring pairs find no other cure, so it sews exactly as OFF (capital stations past 45°: 0 of 139, as OFF; main ON had its crossed legs at 6 against 2); (2) the fold look judges the mitred columns that are finally sewn (120 mm b, folds / short / crossed legs: main ON 14 / 3 / 95, OFF 3 / 0 / 7, now 1 / 0 / 4); (3) `_drop_stalls` drops the next station of a CURVED column whose end lies on a fold-look cut when a rail end has moved under `STALL_FRAC` 0.3 of the pitch (fires once in the word, the 120 mm b's foot; 0.5 also caught ordinary half-pitch bowl steps and raised the 80 mm g's crossed legs by 2). Short legs at u and b: 0 against OFF's 0 at 80 and 120 mm (the u sews no satin at 50 mm). At shipped defaults (`small_text_true_size` ON) 50 mm ON is byte-identical to OFF. **Open before any flip:** crossed legs at 80 mm sit above OFF (b 10 vs 5, g 15 vs 10; unchanged from main ON); the 120 mm p reads 2 / 2 / 9 against OFF 0 / 0 / 4 (main ON 10 / 1 / 51), short legs and folds still above OFF, and it is not in the lane's DONE list; the 120 mm b's construction is fragile (a 1e-4 mm polygon difference flips which ring pair wins; the cure holds on both). `STALL_FRAC`, `FOLD_DEG`, `FOLD_MIN`, `STUB_WIDTHS` and `TURN_MAX_DEG` are gate-1 candidates, nothing sewn. Nothing is queued for him until the p and the crossed legs are looked at. See item 37. *(measured 2026-10-13/15 — PRs #887, #921, #972, `tools/lowercase_angle.py`, `tests/test_lowercase_angle.py`, `tests/test_outline_cut_units.py`, `docs/renders/fold-cuts-g-ub/`)*
46. **Defect 61's other half — keep the cut-off pieces (`clip_keep_pieces`),
   NEW 2026-10-12.** The parent-keeps-ink half is ON (Kent). Whole-flag ON
   restores drone's and golden_tee's dropped ink but costs bridge +5.1%
   stitches and +4/+6 trims sewing its grey JPEG halo; the honest order is the
   halo at its own lever first, then this flip. His call. *(measured 2026-10-12
   — PRs #853, #856)*
51. **RESOLVED 2026-10-14 — `cfg.small_glyph_keep` is ON (Kent, option A, 2026-10-13: flip now, the sew-out block follows; PR #908 merged,
   `config.py` default True).** Keeps a rescued small shape's holes down to 0.16 mm² (stage 4) and plans a wholly clipped one on its artwork
   (stage 5). Fremont 81 mm Hat: "1895" back, 15,306 → 15,611 stitches, trims 44 → 46. **The price:** it does not make the tagline legible — the
   A counters are in the plan and the 0.4 mm thread sews over them, so 3 of 4 tagline counters bare-unplanned → 0 of 4, all shut (none stays open
   at 92.5 mm). The tagline needs `small_lettering_skeleton` (item 54). Both floors it moves are candidates (gate 1); card v3 block N sews OFF
   against ON. Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass).
   *(ruled 2026-10-13 — PRs #902, #908; measured 2026-10-13/14 — #905, #908, `tests/test_small_glyph_keep.py`)*
52. **`lettering_columns_small_stem` — built OFF (PR #896); the flip and the i dot are his.** The Column lane never sees a
   lettering stem under 2.25 mm² (stage 7's small-shape rescue runs first): the 80 mm synthetic i stem sews a run, 2.124 mm²
   against a 2.25 threshold. The flag sends a stem (long side ≥ 1.5 mm, short ≥ 0.5, aspect ≥ 6.0) to the lane; one synthetic
   fixture changes (stem run 37 pts → satin 22 pts, 2,656 → 2,643 stitches), the corpus identical. `STEM_MIN_ASPECT` and the 0.5/1.5
   limits are candidates from one synthetic face and one screenshot, not settled constants. **Larger, not fixed:** the i DOT (0.446
   mm², 0.75 mm across) is dropped with no warning by `RUN_MIN_LOOP_MM` 2.2, a cloth value (gate 1), on every small i and j;
   a 1.0 floor brings it back. Lower the floor or give a dot its own rung: his call. *(measured 2026-10-13 — PR #896,
   `tools/stem_trace.py`, `tests/test_small_stem.py`)* **`cfg.small_dot_rung` (PR #939, merged 2026-10-14, built OFF; `RUN_MIN_LOOP_MM` 2.2 untouched, gate 1):** the dot never reaches stage 7. Stage 3's perimeter proxy 2·max(w, h) reads the 80 mm dot as 1.5 mm against 2.2 and drops it though its real ring (2.49 mm) is over the floor. The rung admits it at stage 3 (the isoperimetric bound; a part nine-tenths ringed by small regions is a counter and is refused), stage 4 (ring floor 1.35 mm) and stage 7 (an outer ring of 1.35 to 2.2 mm sews as a 0.45 mm × 3-pass tack ring); three NEW candidate constants `DOT_RUNG_STITCH_MM` 0.45, `DOT_RUNG_PASSES` 3, `DOT_RUNG_MIN_LOOP_MM` 1.35. The synthetic i dot goes 0/1 → 1/1 sewn at 80 and 60 mm and "hijlij" 0/4 → 4/4. **The catch for his call: it cannot tell a dot from a photo speck** (26-fixture census, 16 byte-identical; photo_sunset_backlit +78 shapes, +4.4% stitches, +23 trims; dof_meadow +20 shapes); **the lettering-only scope, `cfg.small_dot_rung_lettering` (OFF; read only when the rung is ON), is MERGED (PR #975, 2026-10-15), OFF by default:** it admits a part only when a region of the same colour (the layers' CIELAB, or the raster's mean, within `merge_delta_e`) stands below it as a stem (top within 1.5 dot heights under the dot, at least three dot heights tall, no wider than 2 dots, a stroke of steady width), so a photo speck, which has no stem, is not admitted; stages 4 and 7 extend the rung only to a stem-admitted dot. The ratios are classification candidates, the rung's own numbers and `RUN_MIN_LOOP_MM` untouched. Scoped ON it reads the OFF md5 on photo_sunset_backlit (45 / 89 / 26,056), dof_meadow and every census fixture, and keeps the synthetic i dots 1/1 and "hijlij" 4/4; the ratios were tuned on those same photos (in-sample) and no corpus fixture puts a real i/j dot in the rung's band. The `small_dot_rung` flip stays Kent's. *(measured 2026-10-15 — PR #975 body, `tools/small_dot_rung.py`, `tests/test_dot_rung_lettering.py`)* **Fremont's 8 counter is a SEPARATE defect, not the loop floor (ruled 2026-10-14, VP relay of Kent):** sewing the 8's 2.05 mm ring shuts that counter; the one it loses is a 0.413 mm² hole whose ring the 0.73 mm bean sews on its own, 0.2 mm from the outline run (item 54). *(measured 2026-10-14 — PR #939, `tools/small_dot_rung.py`, `tests/test_small_dot_rung.py`)*
53. **RESOLVED 2026-10-14 — ruled, built (PR #930, merged): `satinZigzag` stays ON only under a column-width cap, `SATIN_ZIGZAG_MAX_WIDTH_MM` 5.0 (= `SPLIT_SATIN_ABOVE_MM`).**
   Kent's ruling asked for "about 8 mm, the wide-column split point"; the split point is 5.0 mm and no 8 mm constant exists, so the cap reuses it (VP ruling 09:12 CDT).
   It is a config constant Kent tunes after a sew-out: one line in `src/satinfont.js`, and `satinZigzagMaxMm` overrides it per call (`false` or 0 removes it). Measured,
   manga_impact "AB" (stitches, pre-#904 / no cap / cap 5.0): 198 mm 12,492 / 21,070 / **12,492**; Full Back 305 mm 27,033 / 48,079 / **27,033** (byte-identical to
   `satinZigzag: false`); 50 mm 1,432 / 1,779 / 1,431; 5 mm 112 in all three. Small text is byte-identical to before: 9 pinned cells and 249 cells over 83 fonts at 3, 4.5 and 6 mm
   caps, 0 changed (at 12 mm 4 fonts change). A cap of 8.0 leaves two 5 to 8 mm columns zigzagging at 198 mm (12,524). 5.0 is a candidate; sew-out owed (gate 1).
   *(ruled 2026-10-14 — VP relay of Kent, 09:12 CDT; measured 2026-10-14 — PR #930, `tools/satin-zigzag-cap.mjs`, `test/satin-zigzag-cap.test.js`)*
54. **`small_lettering_skeleton` — built OFF (PR #913, extended by #936); the flip and the floors are his, after the card v3.1 sew-out (gate 1).**
   Small lettering at or under one laid thread wide sews as ONE run down each letter's middle instead of a bean outline (#913: 11 of the tagline's 13 glyphs at floor 0.73, 6 at 1.0;
   ON leaves becker, bridge, golden_tee and drone identical). **#936 (merged) adds a small-glyph second try:** a glyph under 2.0 × `MIN_STITCH_MM` (2.0 mm) that the first
   try declines on its ROUTE (`empty` / `counter` / `shape`, never `width`) is sewn again at `small_lettering_skeleton_small_floor_mm` **0.5** (a NEW candidate = `TINY_STITCH_MM`; `None` turns it off)
   with `trim_stubs`. Fremont 81 mm Hat: **EST and 1895 now take the run, 7 of 7 glyphs, 0.41–0.43 mm wide (main 0.43–0.71)**; stitches 15,625 → 15,228, trims 47; 1895
   legibility 0.551 → 0.772. **Two DONE items NOT met:** EST legibility 0.967 → 0.941 (a neighbour's stray thread read against a thinner T: the instrument's denominator), and the **8's
   counters 1 open → 0 by #905's 50%-bare rule** (the 8 is squared, the 1 loses its flag and feet, the S is angular). **Fremont's 8 counter is a separate defect from the loop floor
   (ruled 2026-10-14):** main's "open" counter is open only because no ring is sewn round it; a 0.40 mm thread on a 0.22 mm stroke round a 0.52–0.58 mm counter cannot leave half of it bare;
   the fix is `bean_letter_counter_hold_mm` (PR #952, ON at 0.25 since PR #977, item 59), which holds each needle point off the counter inside the ink. Corpus 80 mm: becker, bridge, golden_tee, drone md5-identical;
   enthusiast's "ENTERPRISES INC" 13 of 14 letters one run (2,447 → 2,038 stitches; #913 sewed 11 at 0.73). 0.73, 1.0, 0.5 and the 10% tolerance are candidates. Card v3.1 blocks S and E2
   (PR #916; E2's committed DST was cut before #936, so a re-cut would differ) sew it. Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-seventh-pass).
   *(measured 2026-10-13/14 — PRs #913, #936, `tools/small_lettering_skeleton.py`, `tests/test_small_lettering_skeleton.py`)*
55. **RESOLVED 2026-10-14 — `lettering_columns_square_ends` + `lettering_columns_inside_connectors` are ON (Kent's ruling 2026-10-13; flip PR #922 merged).**
   Every Column-lane fixture's ends past their face go to 0 (fremont 81 Hat 36 → 0, worst stub 0.41 → 0.048 mm; becker 15 → 0). **Costs standing:** Becker trims
   22 → 25 (the pro's file cuts 12), +1 fremont 81, +1 enthusiast, +2 summit; bare outline up on drone (+0.31 mm²), summit (+0.17), fremont 92.5 (+0.11); 45°, the
   8°/45° mitre bounds, 10° and 0.10 mm are candidates (gate 1). Card v3.1 blocks X and B check it on cloth. The scorecard baseline is NOT recaptured (every
   Column-lane row moves). Prior text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-sixth-pass). **Kent's four ticks on the HOTEL FREMONT wordmark (81 mm Hat; his marked screenshot reads 15,129 stitches and is not in the repo) are already cured by this flip (PR #954, merged, measure only, no flag).** Today's main (15,625 / 47) shows none of the four by any instrument: the furthest dark needle point past the ink is 0.29–0.30 mm (the Column lane's pull floor) and excess thread is 0.00 mm² at three ticks (0.10 mm² at the R's foot is the neighbouring E's stem scallop, not the foot); `ends_off` (both flags False, 15,611 / 46) reproduces what he saw (the R's foot 0.41 mm past, the M's V connector 1.65 mm over the notch). **The faint long lines near L F and the final T are WHITE thread — the white ground fill's own underlay and fill-bridge travel, covered by 1 to 32 later fill runs each; `hairline_travel.scan` reads 0.00 mm over bare fabric on the whole plan in both arms.** If he marked something else, a fresh screenshot from today's build is the next read. *(measured 2026-10-14 — PR #954, `tools/wordmark_ticks.py`, `tests/test_wordmark_ticks.py`)* *(ruled 2026-10-13, flipped 2026-10-14 — PRs #907, #912, #922, `tools/column_ends.py`)*
56. **True-size small lettering: RULED 2026-10-14, option A (Kent). `small_text_true_size` is ON by default since PR #955 (MERGED 2026-10-15), behind a 0.45 mm counter guard; the drone residue and the 65 mm tagline residue are accepted.** #909 `small_text_cap_mm` was KEPT (Kent) but stays OFF and is not the route: Kent, *"you can't change the font size for the final product"*. The route is `small_text_restore_mm` + `bean_letter_stitch_mm` (#911) and `bean_letter_serif_mm` (#914) behind `cfg.small_text_true_size` (#943; six values filled when unset; #946 `bean_letter_corner_deg` 50; #948 `beanletters.INK_SHAPE_MAX_RATIO` 3.0 drone gate; #960 `small_text_keep_stray_lines`, which the switch fills True: 65 mm THE OCR 1/3 → 3/3). **The guard replaced Kent's 1.6 mm cap-height guard**, which could not separate the 81 mm dates (cap 1.65, better ON) from the 65 mm tagline (cap 1.72, worse ON): `cfg.small_text_true_size_min_counter_mm` = `config.SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM` 0.45, scaled × 40 / thread weight (0.30 at 60 wt, `config.counter_floor_mm`). A line acts only if its smallest SOURCE counter (`small_text.line_min_counter_mm`: twice the largest distance-transform value at 40 px/mm) is at least the floor; no counter passes; a hole under 0.003 mm² or narrower than max(0.1 mm, 5% of cap height) is tracer dust; it is read only on lines the switch would act on; a guarded cluster stays whole. **The counter census (#964, measure only; 42 lines over the 17-design corpus plus Fremont Hat 65 and 72 mm; `tools/counter_census.py`) set it:** the 65 mm tagline reads 0.44 (LOSS, held), the 72 mm tagline 0.47 (WIN, OCR 9/11 → 10/11; a 0.5 floor would hold it), 72 mm 1895 0.50, the 81 mm lines 0.55, 92.5 mm 1895 0.65; every line with no counter wins or ties. **0.45 is a gate-1 CANDIDATE, unsewn, with a thin margin (0.011 mm above the loss, 0.02 below the nearest win, about one raster step): a 65 mm and 72 mm tagline sew-out settles it.** **65 mm tagline residue ACCEPTED (VP, 04:35, 2026-10-15):** the guard bites on the tagline only; the tagline is held (legibility 0.893, counters 3 of 4, both equal to main) but the date line in its colour block acts, which moves the tagline's outline start points (+4 stitches, +1 trim in its box; OCR 10/11 → 8/11, Wilson intervals overlap). Also accepted: drone (+0.44 mm² bare), THE at 92.5 mm 1.000 → 0.667 (the E's bay; the bay hold, ON since PR #977, item 59(f), cures it), screenshot +5 trims and +2.69 mm² bare, small print +0.9 to +1.6 mm² bare. The Fremont Hat main → default stitch and trim counts at 65, 72, 81 and 92.5 mm are in [area 1](docs/scope/1-auto-digitizing-quality.md#item-56-true-size-small-lettering-the-fremont-hat-beforeafter-and-accepted-cost-sentences-as-they-stood-after-pr-968). Corpus: 11 of 17 designs move, 6 are byte-identical (becker, tires, bridge, golden_tee, gaulke, sp_synthetic_4), `ARTWORK_UNCOVERED` rises nowhere. PRE_FLIP pins: `small_text_true_size` False, `small_text_true_size_min_counter_mm` None, `small_text_keep_stray_lines` None. One unrepresentative logo, no sew-out; every value behind the switch is a gate-1 candidate. `ink_ground_ring_mm` (#958, OFF, candidate 0.8 mm) stays a separate Kent flip. **PR #976 (MERGED 2026-10-15) `text_cluster_rescued_ink_link` is ON:** Kent's five red circles on Fremont 80 mm Hat were four stale-service artefacts (his service predated #922 and #955) and one real defect, THE garbled at 80 mm and clean at 81 (the E, 2.19 mm² against the 2.25 mm² small-shape floor, entered the text tagger by the rescued door, linked on size alone to the tan 1895 and was stripped); the rescued round now carries the one-ink link round 2 had. 80 mm 14,897 / 46 → 14,812 / 43; 81 and 92.5 mm byte-identical; corpus 12 of 17 partitions identical, screenshot 8,511 / 63 → 8,502 / 62. *(measured 2026-10-15 — PR #976, `docs/renders/the-80mm-ink-link/`)* **#958's note that it is "inert under the guard" is STALE (measured 2026-10-15 — scout relay via the director, not re-run in this lane):** under the 0.45 counter guard the ring is no longer inert at 65 mm — 65 mm Fremont 1895 OCR 1/4 → 2/4, but glyph legibility 0.769 → 0.641 (a trade, not a win); 72 mm is byte-identical. The note was written against the 1.6 mm cap guard, which the counter guard replaced. Prior text, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#tenth-pass-overflow-moved-from-master_scope-2026-10-15-second-refresh). *(ruled 2026-10-14/15 — VP relay of Kent; measured 2026-10-15 — PRs #955, #964, `tests/test_small_text_counter_guard.py`, `tools/counter_census.py`, `docs/counter-census-2026-10-15.md`)*
57. **`lettering_words` + `lettering_word_tiers` — NOT ripe for a flip.** The only existing answer to Fremont's THE: the hat
   preset's 0.4 mm pull on a 0.40 mm stroke sews H and E at 2.38× and 2.06× their drawn width (the T, a run, at 1.07×), with 1.5×
   the artwork's area in thread outside it; the word tier sews three run outlines at about 1.05× for +69 stitches and +4 trims.
   Card v3 block T (#910) sews it against today. Not ripe until that card is sewn or a legibility score shows it, and #906's
   score does not (it ranks the pro's own THE as a failure). The word tagger's 50 mm misses: item 37. *(measured 2026-10-13 —
   PRs #905, #906, #910)*
   **#927 census (measure only):** script never reaches the Column lane: a script word is one or two wide regions (aspect 2.6 to 3.8) against every tagger's ceiling (1.4 to 2.0), and the lane needs three or more similar glyphs. **A `lettering_words` flip would SHRINK the lane on golden_tee, 9 → 6 shapes**: judge a flip with it. Do not force script in. No decision for Kent. *(measured 2026-10-14 — PR #927, `tools/script_lowercase_census.py`)* **Pull-aware read (#935, instrument only; `tools/glyph_legibility.py --pull-mm MM|auto`, default 0 unchanged):** erodes the thread mask by the pull before any glyph is read; `auto` ESTIMATES one number per design (0.25 to 0.32 mm Fremont), a way to read a render as if the cloth had pulled, not a measurement of any cloth (gate 1). It repairs the headline `legib` inversion in part (AUC 0.462 → 0.769 [0.48, 1.0], p 0.061). **PARTIAL: the pro's THE still sits under our median**, because its E sews its bays shut and the word reads anyway, so `space` and `counters` bill a closed bay a human reads past. No flip proposed. Full text of both, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#tenth-pass-overflow-moved-from-master_scope-2026-10-15-second-refresh). *(measured 2026-10-14 — PRs #927, #935, `tests/test_glyph_legibility.py`)*

58. **Fur: `fill_technique="fur"` (PR #920) is built OFF, API-only, candidates; fur REGIONS on streamline (PR #925) is a measured negative.** Fur tatami is tatami
   with a seeded random row offset and stitch length per row (`short` 4.0 mm / r 0.50 / offset 0.5; `long` 5.0 mm / r 0.80 / offset 1.0; the PR's reading of Elliott via
   #843, gate 1, unsewn). Nothing routes to it by default and the Studio tier menu does not offer it (exposing it is a product call); other techniques are byte-identical
   (30 md5 pins); fur_ramp 40 mm 2,914 tatami → 2,721 short / 2,675 long stitches. Fur regions (`cfg.hair_regions_directional`, OFF): item 45. A fur block on the next
   card is proposed (tatami / short / long, underlay on and off). **Fur TEXTURE (PR #947, census only) is a MEASURED NEGATIVE too:** ten texture signals and the shipped ridge density were read on 63 logo regions of nine logos, and none separates the owl body (4,233 mm²) from every logo region: it sits under the logo maximum on all of them (1.5× on the coherence signals, 4.5× on `gabor_pm`, 6–10× on `orient_rms`, `gabor_amp`, `grad_rms`), and the AUC of plumage over logo regions is BELOW 0.5 on every signal (0.18–0.33 on the seven whose CI stays under 0.5); ridge density is no better, 0.49 [0.32, 0.67]. On regions 3 mm or wider only 9 logo regions remain, six of them Becker's flat black: no power. One bird (two segmentations of one photograph) and the lowest-contrast fur there is, so it is a negative about THIS fixture, not about fur, and no threshold candidate exists. **C10 (a fur gate) waits on Kent's real fur or hair photographs** — two or three at normal contrast (a dark-furred dog or horse), new customer-class art and his to supply (gate 2, public repo); the first measurement then is `st_gcoh` joined to `gabor_amp` on photo-lane regions 3 mm or wider. *(measured 2026-10-14 — PR #947, `tools/fur_texture_census.py`, `tests/test_fur_texture_census.py`)* *(measured 2026-10-14 — PRs #920, #925, `tests/test_fur_fill.py`, `tests/test_fur_regions.py`)*

59. **Small-lettering follow-ons (2026-10-14/15): (a) and (f) ON since PR #977, five built OFF and outside the switch, one instrument, one trace. Fremont is UNREPRESENTATIVE: it reproduces defects, it sizes nothing; every value is a gate-1 candidate and nothing is sewn.** Full numbers: [area 1](docs/scope/1-auto-digitizing-quality.md#eighth-pass-the-small-lettering-follow-ons-pr-945-956); the paragraph as it stood after PR #968: [area 1](docs/scope/1-auto-digitizing-quality.md#item-59-small-lettering-follow-ons-the-paragraph-as-it-stood-after-pr-968). **(a) `bean_letter_counter_hold_mm` (PR #952; ON at 0.25 as a PLAIN default since PR #977, Kent 2026-10-15; None stays OFF, the three sew-out card tools pin None; unsewn):** a 0.25 hold opens both of the 8's counters and the tagline's 1 of 4 → 4 of 4; a held letter sews up to about 0.1 mm wider outside. **(b) `bean_letter_passes` (PR #950, OFF):** passes per spine, `None` = 3, byte-identical. **(c) `small_letter_ties` (PR #956, merged, OFF):** lock thread piled on the ink of bean and skeleton runs −65% at 81 mm, −64% at 92.5 mm, trims unchanged, 6 of 9 logos byte-identical; still owed on cloth are the same 3 mm cap letter, bounce lock vs ties, and tails pulled by hand after a wash. **(d) Trace (PR #953, measure only):** 0 needle points off the ink in all six readings, so the 1's OCR miss is the instrument's window, not the engine; single-glyph OCR is unstable, so judge structurally (bays at the 50% rule, no thread hole, needle points on ink). **(e) `cfg.preflight_glyph_metric` (PR #945, merged, OFF):** per-glyph legibility and `counters_shut` as preflight metrics, no finding or grade change (Kent 2026-10-02); 2.6 to 2.8 s per job, over the 2 s target, hence OFF. **Card v3's `small_glyph_keep` OFF pin is stale** (ON since #908): its N block is still a valid A/B, its F3 and T 'today' arms are not. **(f) `cfg.bean_letter_bay_hold` (PR #967; ON at 0.2 as a PLAIN default since PR #977, Kent 2026-10-15 chose the flip over sewing first; unsewn, block B of the card below settles it):** each bean station within the hold of a BAY (a 0.45 mm closing of the letter's ink with its counters filled, minus the ink, at least 0.05 mm²) moves to the least crowded point of its own spine's ink; a station between a bay and a counter is never pushed into the counter, and satin runs are md5-identical OFF vs ON in all 17 designs. With the switch ON plus a 0.2 mm hold: the 5's upper bay at 81 mm Hat goes 0.36 → 0.53 bare (open by #905's 50% rule, a thin margin), THE's E at 92.5 mm goes 1 false counter → 0 and THE 0.667 → 1.000, the 92.5 mm tagline S (never a closed loop: 0 thread holes in every arm) reads S instead of 8, and 1895 legibility and OCR do not move. **Cost:** a held letter sews up to about 0.1 mm wider outside (EST at 92.5 mm 0.984 → 0.964 at 0.2, 0.930 at 0.25); 7 of 17 designs move, only in bean letters, `ARTWORK_UNCOVERED` rises nowhere. 0.2 is the corpus arm and 0.25 the alternative, both candidates. DOCTRINE 2026-09-30 (no same-shape notch guard) is about the satin rail push, which this does not touch. **(g) `cfg.edge_cap_bean_pitch_mm` (PR #969, MERGED 2026-10-15, OFF, not in the switch):** None sews the BEAN edge cap at 0.73 mm byte for byte (md5-pinned on three flat goldens and two default-config plans); a number re-spaces the silhouette cap's stations only, while the run tier (7,679 short or stacked stitches at every pitch), bean letters, the border's bean fallback and the satin cap keep 0.73. It is the census's option A ("Speed is the operator's", area 4). On the 11 census designs at 80 mm, short-or-stacked penetrations 55,906 → 52,204 / 51,034 / 50,913 (**−6.6 / −8.7 / −8.9%**) at 1.0 / 1.2 / 1.5 mm; penetrations −1.4 / −2.0 / −2.6%; stacking barely moves (−0.4% at most: the three passes return to the same holes); thread flat, trims move by at most 1. **1.2 mm is the measured knee** (the cap's own short or stacked 5,487 → 621; 1.5 buys 0.2 points more). **The cost is edge cover:** share of the outer silhouette with no linear stitching within the host margin (median / max over the 11) 0.40 / 3.33% OFF → 0.37 / 4.59 at 1.0, 0.47 / 4.73 at 1.2, 0.70 / 5.49 at 1.5; worst chord excursion 0.19 → 0.28 / 0.30 / 0.40 mm; Hotel Fremont 0.75 → 2.34% and the Golke screenshot 3.33 → 5.49% at 1.5, and the ~4 mm ® disc turns into a visible decagon there. `ARTWORK_UNCOVERED` barely moves (Becker 12.4 → 13.8 mm²). 1.0, 1.2 and 1.5 are gate-1 candidates; the pitch is picked from cloth only (block P of the card below). **(h) Sew-out card, bay hold and edge-cap pitch (PR #970, MERGED 2026-10-15; UNSEWN, with Kent):** a SEPARATE small card (VP ruling 2026-10-14: not a v3.x revision; card v3.2 stays unsewn), `docs/sewout/card-bayhold-edgecap-2026-10-15/`, one 4×4 in hoop, 40 wt, Hat, one colour, 6,128 stitches, 34 trims, 64.8 × 73.0 mm. **Block B** is `bean_letter_bay_hold` OFF / 0.2 / 0.25 on 1895 at 81 mm and THE and STAY at 92.5 mm (switch ON in every arm; the whole-design md5s reproduce #967's cells); **block P** is `edge_cap_bean_pitch_mm` OFF / 1.0 / 1.2 / 1.5 on a synthetic 14 × 9 mm tatami plate with a square corner, an R3 mm corner and a 4 mm disc. Every arm comes through the real pipeline with the knob set, no hand-edited stitches. What settles each, Kent's call: the hold, if the 5 reads 5, THE's E shows its slit, the S reads S AND the ~0.1 mm widening does not read worse than a filled bay at arm's length; the pitch, the largest whose edge stays closed with a curve and disc that do not read polygonal and no extra thread break. `tools/stitchviz` draws a 3-pass bean as one thread width, so the renders under-draw every bean letter and cap. **Card (#959, merged, with Kent, NOT sewn):** a separate 4×4 card, 20 arms, 40 wt, Hat, the switch ON in every arm; block A is hold OFF vs 0.25, B1/B2 are ties OFF vs ON at 81 and 92.5 mm; C (passes) stays on `card-passes-2026-10-14`. **PR #977 price (both holds explicit, measured 2026-10-15):** Fremont Hat 80 mm 14,812 / 43 → 14,824 / 43; 81 mm 15,330 → 15,340 / 41; 92.5 mm 18,675 → 18,706 / 54; the corpus moves only where bean letters sew, no trim gained or lost. *(measured 2026-10-14/15 — PRs #945, #950, #952, #953, #956, #959, #967, #969, #977, `tests/test_bean_bay_hold.py`, `tests/test_bean_counter_hold.py`, `tests/test_small_letter_ties.py`, `tests/test_bean_glyph_trace.py`, `tests/test_edge_cap_bean_pitch.py`, `docs/renders/edge-cap-bean-pitch/`; confirmed 2026-10-15 — PR #970, `tests/test_sewout_card_bayhold_edgecap.py`, its committed read-back)*

62. **FIXED and ON (2026-10-18) — the white star inside the black Wisconsin shape at 80 mm now sews as the pro's asterisk.** Stage 3 used to drop it as `DROPPED_SMALL_SHAPES` (0.227 mm², 0.80 × 0.74 mm, 0.37 mm inscribed); the pro's Hat and Patch files sew it as a white five-spoke asterisk on top of the black (5 spokes × ~1.45 mm out-and-back, ~2.9 mm span, ~3× the art's star). PR #980 built `cfg.detail_spokes` OFF: a sub-floor enclosed detail of another colour with at least `MIN_TIPS` tips sews as a spoke run on its host. PR #983 flipped it ON on 2026-10-18 at Kent's "ON, tightened": `MIN_TIPS` 3 → 4 and the spoke floor `machine.DETAIL_SPOKE_MIN_MM` 1.45 × width / `machine.DETAIL_SPOKE_REF_WIDTH_MM` 92.6 (1.25 mm at 80 mm). Fremont Hat 80 mm 14,824 st / 43 trims → 14,843 / 44, one new shape, every other shape byte-identical, no colour change; the screenshot's tyre-tread speck (3 tips, a false positive at `MIN_TIPS` 3) is refused at 4; 14 of 17 corpus designs byte-identical ON. Still unsewn: 1.45 mm at 92.6 mm is a gate-1 candidate from the pro's file and the scaled 1.25 mm at 80 mm is unsewn too; a mark whose host is its own thread, and a detail enclosed by two shapes, stay as before (sews last / absorbed). *(measured 2026-10-18 — PRs #980, #983)*

## Cross-cutting issues

Things that don't respect one capability area's boundary. Referenced from the
area they drag down, documented once here.

### DST codec — FIXED, both directions (2026-09-08)

X and Y were in the wrong nibbles of every record byte, and it round-tripped
against itself so the pair's own tests never saw it. Both encoders now match
`pystitch.DstWriter.encode_record` bit-for-bit and the crossval DST control
reads `identity`; the colour-change byte and the terminal `end` sentinel closed
the same week. **The cross-validation harness is ALIVE** and CI fails loud when
its pins cannot run. *(fixed 2026-09-08 — `test/dst.test.js` byte pins)*

**Still true, and the only live part:** a `.dst` written BEFORE the fix is in
the old dialect and re-imports mirrored. Old files are not repaired, so
DesignPanel's note stays, scoped to pre-fix files and the scoping asserted.

How it was diagnosed (a MIRROR, not a quarter turn — a bbox swap fits both),
the superseded lettering-routing measurement, and the full teardown:
[area 4](docs/scope/4-export-formats.md), DOCTRINE 09-07/08,
`docs/dst-axis-verdict-2026-07-31.md`, scope-history 09-08,
`dst-codec-axis-discrepancy` in memory.

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

**Four required jobs; one dominates.** Re-measured 2026-09-14, last 70 runs,
successful only: `digitizer` **min 31.2 / p50 51.0 / max 59.0**; `studio-e2e`
5.5; `studio` 0.9; `engine` 0.5. A fifth, `art-fidelity-baseline`, is
push-to-`main`-only and gates nothing.

**`digitizer` is SHARDED since PR #669 (2026-10-08)** — six `digitizer shard k/6` jobs under one aggregator, so the figures above and below are the single job's history (CLAUDE.md footgun 7 has the sharded budget). Durations refreshed 2026-10-11 from a green main run: slowest shard 12.0 → 11.5 min, spread 4.7 → 3.8 against a predicted under 3 — within a shard, a long file sets the floor, so another refresh will not tighten it. *(measured 2026-10-11 — PR #838, `tests/.shard_durations.json`)*

**Budget eighty minutes per PR, and read a 75-minute `digitizer` job as
normal.** The record is 75.9 minutes, green, on #575 (2026-09-30); CLAUDE.md
footgun 7 carries the trail. Medians keep climbing, so treat every number
here as drifting and spend one `curl` on
`/actions/runs/<id>/jobs` before calling a job stuck. Superseded figures and
the climb: scope-history.

**Tuning levers are spent — do not re-run this search.** `-n auto` is pinned;
caching won 18m38s → 14m00s (#369); `--dist loadfile` buys 5.8% but floors at
the slowest file. Four drift causes proposed, all four eliminated. Trail:
scope-history 09-06, 09-07, 09-14.
*(measured 2026-08-14, 2026-09-06/07, 2026-09-14)*

**Wiring tests that count calls on a module-global can read another test's thread (2026-10-14).** `test_fill_bridge_cut` read `[True] * 4` in shard 5 because the service pool's background job fed its patched `stitch_shape`; #925 records only the test's own thread. **Swept 2026-10-14 (PR #932, merged, tests only, no behaviour change):** `tests/conftest.py::own_thread_only(fake, real)` runs the fake for the installing thread and the original for every other, applied at ~40 patch sites in 39 test files, tripwires included; 643 passed locally on the touched files, and CI's sharded `digitizer` job is the rest of the evidence. *(confirmed 2026-10-14 — PRs #925, #932, `tests/test_fill_bridge_cut.py`)*

**The Fremont 80 mm OFF stream's bytes follow Intel IPP's code path inside the OpenCV wheel — not test order, platform, numpy's SIMD, OpenCV's own kernels or OpenBLAS (2026-10-19/20, PRs #987, #1006).** IPP's AVX2 path (l9) reads md5 `75f44f90` (Kent's Ryzen 7 4700U, CI's EPYC 7763); its full AVX-512 path reads `027d14e6` (CI's EPYC 9V45 / 9V74, a Sapphire Rapids Xeon); its base AVX-512 set reads `050452` (a Cascade Lake Xeon); counts 14,824 st / 43 trims on all. Settled on one AVX-512 Xeon with CI's wheels: `OPENCV_IPP=avx2` reproduced `75f44f90` and `OPENCV_IPP=avx512` reproduced `050452` byte-for-byte; numpy, OpenCV's `AVX512-SKX` kernels and OpenBLAS, each forced down, moved nothing. **Kent's call 2026-10-20: `tests/conftest.py` caps the test environment at `OPENCV_IPP=avx2`** (read lazily); the pin is one md5, `test_test_environment_caps_ipp_at_avx2` is the tripwire, and every shard's `junit.xml` records `host_cpu` (with IPP's path) and `stream_md5`. The shipped service is not capped; it is not a product defect. **The two deselected enthusiast goldens are NOT this cause:** capped at Kent's path on that Xeon, a full run still failed exactly those two (2 failed / 5,235 passed), so their key is engine-stale as the workflow says. CI's two post-cap draws (runs 3218, 3227) landed on an AVX2 EPYC 7763; an AMD AVX-512 draw is still owed, and the tripwire names the host. *(measured 2026-10-20 — PR #1006; detail in COOKBOOK "Reading a golden or md5 mismatch" and scope-history 10-20)*

**`--help` on every tool is cheap and checked (2026-10-15, PR #965, merged, test health only).** Measured over 205 tools: only `stem_trace.py` took over 5 s (25.85 s, over 120 s on a busy laptop). Four hand-parsed tools (`stem_trace`, `fill_score_agreement`, `satin_islands`, `trim_census`) read `--help` as data and ran their full work, or printed an empty table, and `test_tools_help.py` passed on exit 0 alone. Each now prints its docstring first; the test's subprocess timeout fell 120 → 30 s (6× the slowest honest answer, 4.75 s loaded), and a new test requires stdout to equal the docstring. After: slowest 2.96 s, median 2.14 s; the rest of every tool's time is `import digitizer_core`, about 2 s, left alone. No stitch output moved. *(measured 2026-10-15 — PR #965, `tests/test_tools_help.py`)*

### No CONTROLLED sew-out card has been sewn — one uncontrolled icon has

**Corrected 2026-09-14** — this read "Zero sew-out testing" while line 35
recorded the stitch-out, the file contradicting itself about the event phase 5
exits on. Its pointer was **2026-08-21**, eleven days earlier. *(gap audit §3)*

**True:** thread has met cloth once — Kent's icon, 2026-09-01, 6/10, 80.5 mm,
8 cones, 18,959 stitches, via the Python service. *(scope-history 09-01; memory
`first-physical-sewout-2026-09-01`)*

**What it does not settle:** random operator threading (never grade colour from
it), one fabric, one size, no controlled blocks. The CARD (`docs/sewout-card-2026-07-31.md`) is the instrument
and has not been sewn; nor has the hairline card generated 2026-10-12
(`docs/sewout/hairline-card-2026-10-12/`, "Waiting on Kent" 45) or card v2
(`docs/sewout/card-v2-2026-10-13/`, PR #877: small print F, forbid gap G,
column reach H — "Waiting on Kent" 44, 47), card v3
(`docs/sewout/card-v3-2026-10-13/`, PR #910: Fremont small lettering F3 / THE / 1895 plus v2's block G, one 40 wt DST — 44, 47, 51, 57),
or v3.1 (PR #916: one 40 wt DST, 93.8 x 92.8 mm, 91 trims, 19 arms; skeleton arms S and E2, ends checks X and B — 54, 55; built and handed to Kent; its F3 arm 2 drifts +1 stitch, at most 0.1 mm, after #923: accepted 2026-10-14, no re-cut — 47); card v3.2 is to carry the chaining block (Kent, 2026-10-14, "Waiting on Kent" 45). **Three cards are built, committed and UNSEWN, all Kent's to sew:** v3.2, the lettering-arms card (#959: hold and ties, 20 arms) and the bay-hold / edge-cap card (#970, `docs/sewout/card-bayhold-edgecap-2026-10-15/`: block B `bean_letter_bay_hold`, block P `edge_cap_bean_pitch_mm`; item 59(h)). The gate-1 values they test (`bean_letter_counter_hold_mm`, `small_letter_ties`, `bean_letter_bay_hold`, `edge_cap_bean_pitch_mm`, the 0.45 counter guard) are candidates until cloth says otherwise; no session flips them. **Gate 1
stands**; scores stay `pending sew-out`.

**Kent's 2026-08-21 ruling is unchanged by the icon:** accepted as-is, not a
queued action, not to be re-raised as the highest-leverage next action. One
question waits behind it, measured both ways — DOCTRINE,
"Raising `SATIN_MAX_WIDTH_MM`". *(ruling 08-21; sew-out 09-01; fixed 09-14)*

### Evaluation corpus & harness — real gap, newly tracked here

**The gap: no repeatable automated quality signal**; a labelled corpus plus a
scoring harness would let a classifier change be judged before a corpus or a
sew-out arrives.

**Seven measured cases where the harness disagrees with the sewn result — one of them since retracted:** [`docs/yardstick-disagreements-2026-09-06.md`](docs/yardstick-disagreements-2026-09-06.md) — phase 1's exit condition is a claim about disagreements and nothing was gathering them. Two are load-bearing: a 32.7 → 1.4 ΔE00 thread fix that moves no grade or block (the metric moves; the verdict does not), and four photo fixtures that score HIGHER with a ratified quality tier off. Append; do not curate — **row 7 is kept, marked: the retraction is the finding** (measured with the `~base_valid` bug in the tree; the fix reversed its direction, 2026-09-07). *(assembled 2026-09-06)*

**Phase 1's exit condition is NOT MET (2026-10-12), and no phase advance is proposed.** Pooled over every labelled eye-pairs sitting on main (nine sittings, 09-18 → 10-08; 115 pairs in scope, Kent chose a side on 49), **no fidelity instrument clears chance** against his picks: only 26 pairs carry a fidelity reading the scorecard accepts (it refuses the gradient-route logos), every fidelity kappa's interval spans zero, and his pick scores worse on 3–10 pairs per instrument, so the second clause fails as well. **Only trims clear chance** (ties in, weighted: +0.28 [+0.12, +0.43], n = 90) — a price column, not part of the fidelity score. *(measured 2026-10-11 — PR #842, [`docs/yardstick-vs-kents-eye-2026-10-11.md`](docs/yardstick-vs-kents-eye-2026-10-11.md); `digitizer/tools/eye_pairs/pooled.py`)* **A density/flow instrument coded from his own notes finds no new signal (PR #847):** the one candidate clearing chance on both statistics, `jumps_per_1000`, restates trims; he picks the side with FEWER stitches over 4 mm. Its fresh blinded sitting waits on logos Kent supplies ("Waiting on Kent" 42). Full text: [area 1](docs/scope/1-auto-digitizing-quality.md#overflow-moved-from-master_scope-2026-10-14-fifth-pass). *(measured 2026-10-12 — PR #847, [`docs/density-flow-instrument-2026-10-12.md`](docs/density-flow-instrument-2026-10-12.md))* **The instruments:** `digitizer/tools/eye_pairs` (built 2026-09-17, PR #506; each labelled sitting's findings are in [area 1](docs/scope/1-auto-digitizing-quality.md)) and `digitizer/tools/artfid_eye_rank.py`, a blind rank harness whose pre-registered primary was **null and underpowered by construction** (tau-b +0.048, n=7). Its load-bearing result stands — **ARTFID scores are NOT comparable across routes**, and "preflight grade beats ARTFID" is a confound for `route == flat`: do not pool ARTFID over mixed routes and read the ordering as quality. Also live: `colour` reads exactly 1.000 on 11 of 14 fixtures while carrying 25% of the composite. DOCTRINE "ARTFID is not comparable ACROSS routes". *(measured 2026-09-11 — [`docs/artfid-eye-agreement-2026-09-11.md`](docs/artfid-eye-agreement-2026-09-11.md))*

**Harness half: BUILT — `digitizer/tools/corpus_scorecard.py`.** `capture`/`diff`
over 26 fixtures x 2, aggregating preflight's score. REPORTING, not a CI gate;
detail: [area 1](docs/scope/1-auto-digitizing-quality.md). **The 2026-08-12
baseline was SOUND — 38/38 rows re-scored exactly, every mover real** and
attributed before the 2026-09-02 recapture (duplicate fixture dropped, commit
stamped). **Recaptured 2026-10-04 at `6e0cb943`** on cloud Linux after 50
pipeline commits: 48 of 52 rows moved, five fell a band, every mover attributed
by bisection over the 51 trees; the step that crosses a band line is a new
preflight check on all five falls (#572, #573), not a stitch
([notes](docs/scorecard-baseline-attribution-2026-10-04.md), scope-history 10-04).
**Recaptured again 2026-10-05 at `d000e370`** after Kent made both checks
`info` (#630): 21 rows moved, every one of them those two findings, 12 rose a
band, no other leaf moved (scope-history 10-05). **Not recaptured since:**
PR #856 moved drone, gaulke, bridge and chrome on the default path (no grade
fell); attribute them to it at the next cloud-Linux capture (defect 61), and
the phone-screenshot row to #899 (icon guard ON; "Waiting on Kent" 37).
*(2026-08-21; 2026-09-02 — [notes](docs/scorecard-baseline-attribution-2026-09-02.md); 2026-10-04 — [notes](docs/scorecard-baseline-attribution-2026-10-04.md); 2026-10-05 — scope-history)*

**The corpus is half-present, and its real-artwork half keeps contradicting the
synthetics** — six of seven real customer logos route to GRADIENT at stage 0, so
a "flat spot-colour art" claim tuned on synthetics is untested against real
input. **Stage 0's scale defect is two (2026-09-20):** `flat` → `gradient` on
downscale is the pixel-absolute windows on every fixture; the `photo_*`
misroutes on downscaled alpha cutouts were RGB under the alpha, gone since
stage 0 reads the whole-image extension (Kent). *(scope-history, DOCTRINE)* **A second harness, `tools/pro_parity/`, measures distance from the
PROFESSIONAL digitization** of the same 23 designs; its scale changed
2026-08-14, so read the Gotcha in [`DOCTRINE.md`](DOCTRINE.md) before comparing
to any earlier number. Which fixtures misroute, and which half of the corpus a
fresh checkout actually has: [area 1](docs/scope/1-auto-digitizing-quality.md).
*(2026-08-15 / 08-18 / 08-25; detail moved 2026-09-07 — rule 5)*

**The tonal corpus is machine-bound and does not survive a session.** Kent's
portraits live in the gitignored `testdata/photo/acceptance/` (spec decision 6 —
public repo, never publish), so they are invisible to CI and must be re-attached
to chat each session. Drive cannot carry them: the pull-corpus skill's own
measurement shows binary corrupts silently in transit, and these are 3-8 MB.
`scratch_corpus/`'s 37 files remain unreachable from a cloud session (Waiting on
Kent #7). **Consequence: every threshold validated on faces today is validated
by evidence CI cannot see.** *(confirmed 2026-08-25)*

**INSTRUMENT FLAW — `stitchviz` draws a 3-pass bean as ONE thread width (confirmed 2026-10-14 — PRs #955, #956; DOCTRINE, "The renderer draws three bean passes as one thread").** Every bean-letter render under-draws the sewn weight, and four legs on one gap draw the same as one, so a lock PILE cannot be seen at all: read a bean before/after PNG with that in mind. 'Too thin' on the page is not yet separated from the picture of a bean; the passes card (#950, item 59) asks the cloth, and until it is sewn a 0.001 legibility delta can be paint order (#956) rather than a thread that moved.

**Area 1 is deliberately NOT split into "image analysis" + "stitch planning"**, and
the four gaps an external review named have owners in code — [area 1](docs/scope/1-auto-digitizing-quality.md). *(moved 2026-08-21 — rule 5)*

### Research backlog — competitive and open-source leads

Two capability sweeps (Ember Design, Ink/Stitch), the closed `simplify_tol_mm`
investigation and a sixth independent DST-axis corroboration live in
[`docs/scope/research-backlog.md`](docs/scope/research-backlog.md). Nothing in
there is a commitment or a defect. The two items that bind how work may be done
— Ink/Stitch's GPL-3.0 clean-room rule (`pystitch` excepted) and Ember's editor
toolset — moved to [`DOCTRINE.md`](DOCTRINE.md) 2026-09-08, since they are
constraints rather than status.
Kent's 18-item "what no embroidery tool does" list, set against the tree with what blocks each hard item: [`docs/feature-landscape-2026-10-01.md`](docs/feature-landscape-2026-10-01.md). *(read 2026-10-01 — code and docs, nothing run)*

### Machine-physics change list — audited, and no longer orphaned

No status doc pointed at the machine-physics playbook until 2026-09-20: three
research docs cite its LAWS, nothing tracked its 17-row engine change list.
Audited row by row against `main` in
[`docs/scope/machine-physics-backlog.md`](docs/scope/machine-physics-backlog.md):
**2 built, 2 built-but-gated, 8 partial, 5 not built.** Of the 5 not-built rows
only **row 2** (the pull-comp mm table) is blocked by gate 1; the other four the
playbook itself marks desk-safe. Rows 7 and 8 are gated behind
`cfg.directional_comp` on purpose — gate 1, do not flip.
**Kent's call 2026-09-20: promote four, list the rest.** Rows 3, 17, 9 and 6
became defects **45–48**; the remaining desk-safe gaps stay in the backlog doc
with their buildability column intact. **Two closed the same day** — 45 (row 3,
`assumed_backing`) and 48 (row 6, `PLAN_SPM`/`TRIM_COST_STITCHES`) shipped in
the operator bundle, which also closed Part 3's backing, topper and runtime
lines. **46 closed 2026-10-03** (row 17, as preflight metrics); **47's angle
half is built OFF** (row 9 now Gated, PR #700), its flip and knit value
card block 6's; its forbid-gap half is built OFF too (PR #846). Standing
tally: 5 built, 3 gated, 6 partial, 3 not built.
*(audited 2026-09-20 — code read, `origin/main` 1ac731cd; 46 built 2026-10-03; row 9 re-read 2026-10-11 — PRs #823, #846)*

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
via the `embstudio:sam2` dev seam, still `photo_segment_sam2=False` — and
**REFUTED as a region former for LOGO art**: 0–8 masks at the shipped
`points_per_side=12` against the shipped former's 17–164, either finding
essentially nothing or segmenting the BACKGROUND as the object, at
`predicted_iou` 0.88–0.99 throughout. *(measured 2026-09-22 —
[`docs/sam2-on-logo-art-2026-09-22.md`](docs/sam2-on-logo-art-2026-09-22.md))*
**Tonal work has a shape now (2026-08-25).** Filled beats thread-paint on
high-contrast subjects and loses badly on faces; the satin-border rule, the
GeometryCollection crash, the per-ring abruptness gate and `cfg.is_photographic`
all landed and all validated against four real portraits. **What none of it has
is CI cover** — the tonal evidence is gitignored and machine-bound, so every
threshold shipped is defended only by an owl. *(measured 2026-08-25 — PRs
#241/#243/#245; scope-history 08-25 evening)* **Gradient lane (Kent's ruling 2026-09-04): a design whose ramp fits, linear or radial, sews as ONE sweep** (`design_ramp.py`), on stage 5's compensated outline at the density stage 7 resolved, band seams feathered, ring seams hard; satin holes rasterise half a pixel smaller (`shapefield.hole_px`); the cone list reads `stats.blocks`; `preflight._owning_region_id` is the one rule for derived region ids. **Satin as SEWN** (`tools/satin_columns.py`): the pro's Becker sews **44.3%** of penetrations in columns, ours **2.2%** — the biggest measured gap to a professional file; read our widths off its second row (DOCTRINE 09-06). **No physical tests until Kent says — the render is the judge.** *(measured 2026-09-04 — scope-history; DOCTRINE; evidence: [area 1](docs/scope/1-auto-digitizing-quality.md#area-1-lanes-in-full--moved-from-master_scope-2026-10-08))*
**Kent's own verdict, 2026-08-27: these are 60% of the way to Ember parity.** First per-design feedback in his words on all fourteen designs. `artfidelity_self` averages **83.7** and `preflight` **80.0** on the same set, agreeing with each other at only **rho = 0.405** — so **never quote ARTFID as a quality percentage**: it is a fidelity score, blind to craft, which is most of his missing 40%. He named the split himself — *"Shapes are accurate but smoothness is not."* Two themes, equally weighted by him: smoothness (8 of 14) and whole elements missing (7 of 14; both his "out of place" marks lost an element). **Bears on ROADMAP phase 1's exit condition** — a fidelity-only metric may not be able to agree with a partly craft-driven ranking at all.
**`ARTWORK_UNCOVERED` cannot see a dropped element**: fired on 1 of those 7,
`0.0 mm²` on the rest with `uncovered_checked: True`, because it is scoped to
shapes the design already sews. `tools/dropped_elements.py` measures it from the
artwork's side — 99.1% lost on the logo Kent called "5% completed at most".
**And it could not see a HOLE either, until 2026-09-30 (Kent's pick).** Its
5.0 mm² patch floor sat above the largest patch it could resolve anywhere on
the corpus (1.90 mm², swept over six erosion × cell settings) — a check that
could not fire on any real logo and had not for weeks. The floor was not even
the binding constraint: the 0.4 mm erosion and the 0.5 mm cell were, and the
erosion had a cliff exactly at its shipped value (ENTHUSIAST's apex 0.80 mm²
at erosions 0.1–0.3, **0.00 at 0.4**). Now cell **0.25 mm**, erosion **0.0**,
floor **1.0 mm²**, behind a thickness test (`_UNCOVERED_MIN_HALF_MM` 0.30)
and a compactness test (`_UNCOVERED_MIN_FILL` 0.15) that refuse the rim by
what it is rather than by shaving every shape. Corpus: **438 patches → 20
holes on 3 of 9 logos** (becker 17, ENTHUSIAST 2 including defect 49's apex,
drone 1); golden_tee's six area-qualifying patches are all seams and all
refused. Every firing patch was rendered through the real thread path before
the numbers were chosen. Still a `warn`, never a block; the margins are
1.5–2x, so treat it as adjudicated-on-nine, not settled.
*(measured 2026-09-30 — `tools/uncovered_floor.py --corpus`;
[`docs/renders/uncovered-floor-2026-09-30/`](docs/renders/uncovered-floor-2026-09-30/);
`tests/test_preflight.py`)*
**Both halves of the smoothness complaint now have instruments, and they are not the same measurement** (Spearman 0.028). `tools/edge_smoothness.py` owns edge noise; `tools/curve_fidelity.py` owns the curve half, read from `plan.iter_runs()` because **curve fidelity is not readable from a raster**. Read **`roughness_deg`** per design; `turn_gini` is substantially a COMPLEXITY statistic (Pearson −0.763 vs log trace count), valid only on the ladder or a paired arm; the floor is **stitch length**. *(measured 2026-08-27/28 — PR #281; `docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`)*
**Wobble attributed (2026-09-19): SATIN RAILS, not the outline** — `tools/edge_wobble.py`: satin std 0.09–0.11 mm on real logos, 0.038 synthetic; outline 0.011. **Cause DIAGNOSED 2026-09-21, and it is the rail MODEL rather than a step inside it:** the rail sits where a width-profile ray puts it, and that ray cannot tell "the shape is wider here" from "the ray escaped into the next arm"; the offset is settled and OUTWARD (+0.24 to +0.25 mm), the width-filter hypothesis is refuted, and the ablation found no mechanism to switch off. Closing it means placing satin rails on boundary geometry the way `line` (std 0.000) and `fill` (0.010) already are — a large build in the most caveated file in the repo, and **not one to start before the sew-out**: nothing ties 0.089 mm to Kent's eye on cloth, and closing it does not move `lost_frac` on ENTHUSIAST. *(measured 2026-09-21 — [`docs/rail-wobble-cause-2026-09-21.md`](docs/rail-wobble-cause-2026-09-21.md))*
**Low-resolution outlines (2026-10-10/11): the hard stair-stepped mask, not the pixel count, is the limit.** An off-the-shelf tracer (vtracer, nine settings) is not closer than stage 4 (closer in 5 of 26 cases, stage 4 in 13). `cfg.coverage_edges` (PR #818, outlines from the source alpha's half-coverage contour) is **DEPRECATED — Kent: no, 2026-10-12** (item 38, PR #852): it halved median edge error on golden_tee and Fremont but worsened a sharp corner (0.03 → 0.22 mm) and narrowed three Becker slots below one thread. The reversals come from `subpixel_edges_upscaled`'s read at 1.8 px/mm; a resolution floor under it is built unset and left so (Kent, item 41). **The reversals' own cure is BUILT OFF — `cfg.subpixel_corner_runs` (PR #834):** one fit per corner run, an unread vertex takes its read neighbours' offset, a vertex landing behind its predecessor drops; Becker at 1.8 px/mm reversals **7.1 → 0.9** per 100 mm, right-angle turns 26.5 → 20.1, worst median edge-error change +0.0028 mm over four cases × three rungs; 16 reversal vertices remain, and at 3 and 5 px/mm Becker reads 1.3 and 1.4. Nothing sewn. *(measured 2026-10-10/11 — PRs #818, #824, #826, #834; `docs/low-res-outline-sparknotes-2026-10-10.md`, `docs/native-read-corners-2026-10-11.md`)*
**Thread weight and a hairline tier (2026-10-12) — `cfg.hairline`, `cfg.hairline_over_ground`, `cfg.hairline_from_lines` and `cfg.hairline_coverage_guard` DEFAULT OFF, thread weight 40 by default (PRs #848, #850, #851, #876, #879, #882, #888).** Kent: *"Thread is extremely thin, we should be able to embroider hair!"* The floor is the NEEDLE, not the thread (Melco run ≥ 1.5 mm, satin ≥ 1.0 mm). `stage6_hairline` sews each skeleton BRANCH under 1.5 × the laid width as one Euler-walked run; the ground runs under strands; a per-strand gate and (from 2026-10-13) a drop guard, a line test and a coverage guard hold it back where it would erase letters or sew blur. On drawn hair it works; on logos and the one real photo it is not ready — status, bills and the flip queue are "Waiting on Kent" 45. Every 60/75 wt value and the 1.5 mm stitch wait on the hairline card. Renders only. **Streamline row spacing follows thread weight (#924, merged; 40 wt byte-identical):** the dark end is two laid widths (0.8 / 0.64 / 0.52 mm at 40 / 60 / 75 wt), the light end (3.2 mm) unchanged; the 60/75 values are unsewn candidates (gate 1). owl_kent 127 mm, 40 → 60 wt: 34,703 → 39,437 stitches (60 wt also moves satin spacing and hairline widths, so not streamline alone). *(measured 2026-10-14 — PR #924, `tests/test_streamline_thread_wt.py`)* Full paragraph: [area 1](docs/scope/1-auto-digitizing-quality.md#hairline-tier-paragraph-moved-from-master_scope-2026-10-13). *(measured 2026-10-12/13 — PRs #848, #850, #851, #876, #879, #882; `docs/hairline-prototype-2026-10-12.md`, `docs/hairline-ground-2026-10-12.md`, `docs/hairline-strand-gate-2026-10-12.md`)*
**Two stage-1 background defects, both reproduced on main 2026-10-11 and both fixed behind `cfg.bg_structural`, DEFAULT OFF:** `summit_badge`'s half-removed background (0.383 of the true background removed at the shipped `bg_tolerance_lab` 6.0; ON **0.9995**, no badge pixel lost), and `BACKGROUND_ABSENT` answering a structural question through a colour threshold (summit flips between 4.5 and 4.8, `logo_toat_beanie` at 3.0). ON, stage 1 reads the background as one paint under smooth shading — a quadratic field over the border ring at a fixed 5.0 ΔE for existence, a degree-4 field for reach — and both fixtures read "background" at every tolerance 3.0–8.0; one other verdict changes. Flip: "Waiting on Kent" 39. *(measured 2026-10-11 — PR #825, `docs/renders/bg-structural-2026-10-11/`; first found 2026-08-27 — `docs/kent-review-2026-08-27.md`. PR #276's body claims the engine is correct on `summit_badge` — that sentence is wrong, its instrument fix stands.)* **Satin extremity drop — FIXED 2026-08-21.** `_prune_spurs` re-measured a stem its OWN first pass had un-branched, one raster pixel deciding a 3.3 mm tab. **The blind spot that hid it stays fixed:** `preflight`'s `ARTWORK_UNCOVERED`, 5.0 mm² threshold still provisional. *(fixed 2026-08-21 — PR #186)* **Lettering quality — the STITCH-ANGLE mechanism is FIXED 2026-08-27. Three others remain open.** Kent on two sewn logos: *"lettering should be smooth"*, *"ROOKIE MISTAKE"*, and *"Why is the 'N' running Vertically?"*

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
measured 2026-09-03, lowercase 2026-10-13 (item 37). *(measured 2026-09-03 — area 1)*

**Mechanisms 2 and 4 — prototyped/costed and half-closed respectively — moved to [area 1 detail](docs/scope/1-auto-digitizing-quality.md) 2026-09-07 to keep this file inside its own 800-line budget.** Kent held the exterior-notch guard 2026-08-28 (reds the chaining benchmark 3.8 → 6.4 trims/1k); the letterform instrument reports the WORST medial-axis stroke and is **still blind to TILT**. *(moved 2026-09-07 — no content changed)*

**Still open and unfixed:** `_prune_spurs` drops a 3-way node to 2-way so
the walker welds the N's diagonal to its stem through a 108° fold — the same
function PR #186 fixed, one consequence on. Prototyped twice, NOT shippable
as written (propagates the H defect to every square-capped bar; two
prototypes measured −18.3% and +20.5% off one baseline); needs a cap-arm
classifier. *(measured 2026-08-26 — `.claude/memory/letterform-fidelity-2026-08-26.md`)*

**Confidence limit on the fix:** two real lettering groups from ONE logo; real-artwork validation needs Kent's box.

**Text clusters see ordinary lettering (third attempt, 2026-09-03).** Two doors clustered in two ROUNDS — rescued first with unchanged code, so every cluster that regularizes is computed as before — then ordinary glyphs at the house-angle height ratio with a one-ink CIEDE2000 link (ΔE ≤ 20; the shield star is 34.2 from ENTHUSIAST, within-word quantization needs ≤ 16.4). Becker 0 → 11 tagged, drone 0 → 21, enthusiast keeps its subline cluster id. Cost measured quiet: enthusiast +0.9 s; the 60 s service test at 12.4 s idle and 12.1 s under three CPU hogs once the tesseract child is pinned to one OpenMP thread (32.7 s before — the likeliest root cause of `10ae9cc`'s CI timeout). No satin underlay under a 5 mm shape (`SATIN_UNDERLAY_MIN_EXTENT_MM`, the JS rung; Kent's call). *(measured 2026-09-03 — same doc)*

**Per-shape stitch width (2026-09-29, `digitizer_core/stitchwidth.py`).** Every column reports its width and word; review override `stitch_width_mm` (contract v1.8) offsets the polygon, counters held. **Evening a word out is OPT-IN (`stitch_width_auto`):** Gaulke's 35 letters run 0.77 → 1.33 mm as a smooth chain, so a median is nobody's width. Off, byte-identical; floor None (gate 1). *(measured 2026-09-29 — `tests/test_stitch_width.py`; COOKBOOK "Per-shape stitch width")*

**A tapered tip is a CAP, not a junction — `cfg.satin_tip_caps`, ON since 2026-09-30 (Kent).** Under `satin_rail_comp` the artwork's sharp tips stay sharp, so a tip one stroke ran through on the grown polygon becomes a node where two arms END: `_extend_to_cap` never runs and the junction trim pulls both back. ENTHUSIAST's A stopped **1.63 mm** short of its apex against 0.08 mm off the rails. Kent's construction — both arms cap and overlap — needed no new discriminator, only the gate to stop EXCLUDING arms that tuck under each other (`_corner_forks` names a partner both ways there). Bare artwork and end bare fall on **all nine** corpus logos (becker 182.07 → 160.69 mm², screenshot's worst component 1.94 → 0.91) for **+4.2%** stitches. **It does NOT close defect 49** — ENTHUSIAST's apex is unchanged at 3.61 mm², because both its arms tuck under each other and the gate never reaches them; the widened construction that does close it was RETRACTED the same day on `lost_frac`. Three discriminators were measured and refuted first, and an area test cannot separate a tip from a corner — DOCTRINE. **The corpus figures above are `bare_anatomy`'s satin-only reading, an upper bound on cloth a customer sees by a per-fixture 1.1–39x** (DOCTRINE 09-30); the flip's direction is unaffected, its magnitudes overstate. *(measured 2026-09-30 — `tools/bare_anatomy.py --corpus`; `tests/test_satin_tip_caps.py`)*

**Next:** NEEDS KENT. Fragmentation work measures **0% on real client logos**
(they are satin-dominated, 1–3 fill shapes, no cutting fills). The one large
real-artwork lever is **`chain_links`: −33% trims AND fewer stitches**, gate-1
frozen; every gate-clear alternative measures ≤9%. *(measured 2026-08-22)*

**Quality review 2026-09-08 and the lettering construction chain: current state, detail moved.** Review: [`docs/quality-review-2026-09-08.md`](docs/quality-review-2026-09-08.md). ON by Kent (`digitizer_core/config.py` defaults): the lettering construction flags (`satin_house_from_line`, `satin_house_anchor`, `satin_stroke_order="euler"`, `satin_corner_twigs`, `satin_lettering_split`, `satin_junction_stack`, `edge_cap_skip_lettering`), `satin_rail_comp` (since 2026-09-28, sew-out owed) with `satin_rails_follow_edge="envelope"` (2026-09-30), `keep_thin_strokes` (2026-09-13), `subpixel_edges`, `subpixel_edges_upscaled`, `alpha_edge_extend`, the four colour flags, `robust_region_colour`, `enclosed_by_garment`, `legibility_check` (warns under 0.5, never blocks, RULED), and the Column lane (`lettering_columns`, #863) with its two ends flags (since 2026-10-14; "Waiting on Kent" 37, 55). OFF: `satin_walk_cursor_reach_mm` (sew-out), `design_angle`, `wide_columns`, `lettering_min_column_mm` (a glyph-height gate is the open question, Kent's call), `lettering_words` (the L1 tagger; its flip is Kent's, item 37). The Studio sends the uploaded file, not a canvas re-encode (fixed 2026-09-20). Item 1's PR 5 stage-0 signal is measured and the blocker is unchanged: one real tonal artwork labelled where the spec asks four (`docs/stage0-signal-decision-2026-09-11.md`). Connected script is outside the construction (preflight `SATIN_GAPS_TIGHT`, `LETTERING_TOO_SMALL` and `LETTERING_ILLEGIBLE` carry it). Full text of this paragraph, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#tenth-pass-overflow-moved-from-master_scope-2026-10-15-second-refresh). *(confirmed 2026-10-13 — `digitizer_core/config.py` defaults; measured 2026-09-08 to 2026-10-08 — review doc, scope-history, area 1)*

**Kent's Fremont 81 mm Hat report: "1895" dropped out of his Studio run (2026-10-13/14, PRs #898, #902, #905–#914, #916).** Replayed with the Studio's own request (`tools/fremont_triage.py studio_request()`) it reproduces his job (15,306 stitches against his 15,129). Causes: stage 4's hole floor fills the 8's and 9's counters and the white ground's hole where the "1" sits, after which stage 5's clip removes the whole "1"; stage 7's small-shape rescue bean-outlines every glyph under `min_detail_mm`² (134 of 161 shapes); the tagline's A's lose counters at stage 4. **`ARTWORK_UNCOVERED` is silent in every arm: coverage cannot see illegibility.** Fremont is UNREPRESENTATIVE (it reproduces defects, it sizes nothing). `tools/glyph_legibility.py` (#906) is an instrument, NOT a gate: AUC 0.885 [0.692, 1.0] once the pro's own THE counts as legible, and its `legibility` headline ranks the red boxes the wrong way round (AUC 0.10, never quote it). The levers built since are "Waiting on Kent" 52 and 54 to 57 and 59; the cards are v3 (#910), v3.1 (#916, with Kent), v3.2 (#949), the passes card (#950) and the lettering-arms card (#959). Full text, moved verbatim: [area 1](docs/scope/1-auto-digitizing-quality.md#tenth-pass-overflow-moved-from-master_scope-2026-10-15-second-refresh). *(measured 2026-10-13 — PRs #898, #902, #905, #906, `tools/fremont_triage.py`, `tests/test_glyph_legibility.py`)*

### 2. Font library & lettering — [detail](docs/scope/2-font-library-lettering.md)

**Implemented · High (tech) / High (compliance).**
**85 fonts** in the sellable build, the EMBF binary codec, browser UI, and the
add-font QC/tier pipeline. The lettering path stitches three types — satin,
bean/running, cross-stitch fill — where before 2026-08-21 it was satin-only. A
second `--personal` build (125 fonts) carries what cannot be sold; for licences
"Font license compliance" above is the single source. Same tech score as before
on a different basis (see the area doc); known debt is the 26 glyphs that sew
nothing, in "Waiting on Kent". *(confirmed 2026-08-22 — manifest, engine suite)*
**Size guards (2026-09-03):** the 0.5 mm cross floor on the fabric (was 0.3 design pixels), hairline stretches as bean runs, and a per-element note of cap height and the share under 1.0 / 0.5 mm — warn only, no clamp; at 50 mm four hairline-authored fonts move > 5%. **Bold no longer closes counters:** its 0.3 mm is held per rail where a rail faces another across a gap the cross floor cannot spare (0.72 mm eye: 0.50 guarded vs 0.42; 0.36 mm: untouched vs 0.06); pull comp and normal/thin untouched; 60 of 83 fonts hold somewhere at 25 mm. **Short stitches (Law 53)** on the inside of bends, the Python guard mirrored and width-gated by the cross floor: geneva "S" 43% → 0% of same-rail advances under 0.3 mm, stitch counts identical, faces at the floor left alone. *(measured 2026-09-03 — commit `0a67171`, area doc §"Bold counter guard", §"Short stitches")* **Long stitches at the large end — split at the machine record.** Satin crossings past one DST record (121 units per axis) went with two units fixes and `splitSatin` (Kent 2026-09-11: ON; `wideColumnFill` off), leaving only cross-stitch fonts, whose X arm grows with the letter. **Kent ruled 2026-10-13 "Split at machine limit":** `crossFill`'s `maxSegPx` cuts an arm whose per-axis delta passes 12.1 mm into collinear pieces; arms within the record are byte-identical (9 fonts at 25 and 60 mm), and the census's worst per-axis delta falls 21.9 → 11.0 mm. A 14.4 mm arm (10.2 mm per axis) still sews as one stitch: how long a cross may float before it snags is a fabric constant, gate 1. The census (PR #864) also shows the 31.0 mm rows need a ~254–285 mm cap on a Full Back; whether the Studio should place text that tall is a product question for Kent. *(measured 2026-09-11 — `tools/long-stitch-census.mjs`; 2026-10-13 — PRs #864, #870, [`docs/crossstitch-arm-census-2026-10-13.md`](docs/crossstitch-arm-census-2026-10-13.md), `test/crossfill-split.test.js`; the 09-07/09-11 paragraph, moved verbatim: [area 2](docs/scope/2-font-library-lettering.md#long-stitches-at-the-large-end--moved-from-master_scope-2026-10-13))*
**Small caps: every font but three is a candidate-unsafe under 4 mm, and all under 3 mm (PR #862, measurement only).** `Hamburgefonstiv 0123` through the Studio's text path at 2.5–6 mm caps against a 12 mm control: only `mimosa_medium`, `mimosa_large` and `jaquarda_bastarda_9` stay clean from 3 mm; 43 of 83 scored fonts are clean at no cap up to 6 mm, 27 of them with hairline spans at 6 mm. Candidates only (gate 1, nothing sewn). *(measured 2026-10-12 — `tools/small-cap-census.mjs`, [`docs/small-cap-census-2026-10-12.md`](docs/small-cap-census-2026-10-12.md))*
**Studio text satin laid half the thread across a column that the Python satin does — CURED by `satinZigzag`, ON by default since 2026-10-14 (Kent's ruling 2026-10-13, PR #904; built OFF in #901) and CAPPED at a 5.0 mm column width since PR #930.** `satinplay.emitZigzag` alternated its leading rail (A1,B1,B2,A2,A3,B3) from the file's first commit (2026-07-24), so one stitch crosses and the next steps one spacing along a rail: a lone "l" stem had **2.5 threads across per mm against 5 in the Python order and 6.7 in Ember's export**. `buildLetteringDesign({ satinZigzag: false })` gives the old stream; `layoutText` and `emitZigzag` still default off. Small text ("Hotel Rag", four fonts, 3.3–6.2 mm caps): same stitch count, thread +10 to +28%, short stitches fall (alchemy 3 mm under 0.5 mm: 199 → 18; montecarlo 6 mm: 376 → 188). **Big text pays:** where split satin fires the return leg is a full cross with its own split penetrations, so `manga_impact` "AB" went 12,492 → 21,070 stitches at 198 mm and 27,033 → 48,079 on a Full Back; the cap (`SATIN_ZIGZAG_MAX_WIDTH_MM` 5.0, "Waiting on Kent" 53, PR #930) gives both back. Not looked at: the comb on wide split columns with the flag on, and whether browser-digitized shapes reach this emitter. A render shows open ladders off and closed columns on, but is not fabric: sew-out owed (gate 1). *(measured 2026-10-13/14 — PRs #901, #904, `test/satinplay.test.js`, `test/satinfont.test.js`)*
**Next:** **upstream is exhausted; no external supply** — measured, not
assumed (area doc, "Supply"). Terminus closed. Growth means commissioning.

**Bean letters (2026-10-02), built OFF behind `cfg.bean_letter_max_stroke_mm`:** a text cluster whose INK strokes are under the line sews as 3-pass bean runs along the skeleton of the source ink (`ink_path.py`, `beanletters.py`, `stage6_beanletter.py`); the ground it stands on sews through under it (stage 5), and the engine reports `SMALL_LETTERING_AS_BEAN`, a Studio note that asks for nothing. `text_cluster_stroke_mm` is NOT a stroke width (0.38 for Fremont's 0.67 mm strokes) — read `meta["ink_stroke_mm"]`. Flip is Kent's: "Waiting on Kent" 21. *(built 2026-10-02 — `tests/test_bean_letters_pipeline.py`, `tests/test_ink_path.py`, `tests/test_bean_letter.py`)*

### 3. Studio app / configurator — [detail](docs/scope/3-studio-app-wizard.md)

**Implemented · Medium.**
The Svelte configurator (one panel: design → garment, summary bar, Download sheet), saved projects,
the Layers panel, and fabric/garment presets. Logic coverage is broad —
nearly every `app/src/lib/*.js` module has a paired spec — with UI-behaviour
coverage riding on live-browser e2e specs across several garments, the image
content path, four export formats, and the embroidery field's own chrome.
**Detail moved to the area doc (2026-10-14, eighth pass).** The Studio's hooping card, quote settings (`embstudio:quote`), the upload crop box (`PipelineConfig.crop`, `DOMINANT_SHARE_MIN` 0.75), the 2026-09-30 design review, closed-loop calibration (default OFF, simulated accuracy only), the upload-only panel, the Shapes row's shades, the hoop gate, the delta-and-fix panel, the thread-from-photo match, the SVG-import warning, project naming and the library filters are all in
[area 3, eighth-pass overflow](docs/scope/3-studio-app-wizard.md#overflow-moved-from-master_scope-2026-10-14-eighth-pass), verbatim. Status is unchanged: Implemented, Medium. *(moved, confirmed 2026-10-14 - `docs/scope/3-studio-app-wizard.md`; the claims inside keep their own pointers)*

**Re-digitize no longer strands on a poll blip (2026-10-16, PR #981, Studio-only).** `pollJob` used to throw on the first poll that missed the service, abandoning a job still computing (an 80 mm photo is ~4 min, polled every 500 ms) and leaving the element on the previous result and delta. It now retries a fetch reject, truncated body or 5xx up to `maxTransientFailures` 20 (about 10 s), resets on a clean read, and still surfaces a job error, a 4xx or the overall timeout at once; a finished re-digitize with unchanged settings lands the new stitches and recomputed delta. `app` vitest 1874 passed. **`run-emb-bot` smoke (2026-10-17, PR #982):** the driver refuses the pre-click caption as the new result and clears `localStorage` before lane 2; the two lanes read different captions (1,245 st · 102×12 mm text; 2,414 st · 80×17 mm artwork). *(measured 2026-10-16/17 — PRs #981, #982)*

**What holds it at Medium:** fabric-preset accuracy is gated on the controlled
sew-out CARD, which has not been sewn — the one physical out so far (2026-09-01)
was a single uncontrolled icon. See Cross-cutting issues.

**The two engines' fabric and machine tables are wire-tested to agree**
(`test_fabric_wire.py`, `test_machine_wire.py`) — [area doc](docs/scope/3-studio-app-wizard.md).

**A Studio change is not verified until it has been *looked at* in a browser.**
Six buyer-visible defects across the 2026-08-25 and 09-07 sweeps, none seen by a
green suite. The list: DOCTRINE "Gotchas".

### 4. Export formats — [detail](docs/scope/4-export-formats.md)

**Implemented (all six) · Confidence varies by format, not one score.**
DST, EXP, PES, **JEF**, SVG and the PDF worksheet, via both the browser encoders and the
service's `/export` route. One reachability caveat: `/export` is only reachable
from the product for purely-digitized designs — anything containing lettering
or manual shapes downloads through the browser encoders — **except JEF, which
the browser cannot write at all** and which therefore always goes through the
service, on every project type. **The DST caveat now names JEF as a way out (2026-09-08).** It said only "PES and EXP are unaffected" — written before JEF had a button and never revisited when #403 gave it one — so a Janome owner hitting the warning was steered to two formats their machine may not read, away from the one it does. Conditional on `jefAvailable` in both directions, and deliberately NOT named in the service-unreachable branch, since JEF needs that same service. `DownloadStep.spec.js` pins both.

**Two more machine formats work and have no button (Kent's call).** `/health` also advertises `pec` and `u01`; one two-colour design exported in all nine and decoded with pystitch gives the same 99 stitches at 80.0 x 24.0 mm each. **VP3 (Husqvarna/Pfaff) and XXX (Singer) shipped 2026-09-12** — resolved item 14, which also carries why PEC and U01 are held. *(measured 2026-09-07, revised 09-12)*

**Speed is the operator's — Kent RULED 2026-10-14, 20:20 CDT: no speed feature (PR #951, measure only).** Asked 'do we adjust embroidery speeds for more challenging stitches?': no format EMB-Bot writes can carry a speed (DST, EXP, PES and the JS codecs cannot; only pystitch's Barudan U01 writer can, and `plan_to_pattern` adds no SLOW/FAST); 28 pro DSTs and 2 Barudan DSBs carry none, and the 19 Wilcom worksheets have no speed or time field. The census (`tools/stitch_difficulty_census.py`, OFF-path, imported by neither engine nor service) found a geometry lead instead: sub-1 mm stitches are 33.8% of ours against 10.6% of the pro's, and 31% of penetrations land within 0.5 mm of an earlier hole against 13%. None of the three priced options (a counts line on the worksheet, U01-only SLOW/FAST behind an OFF flag, splitting short and stacked stitches by source) was chosen; candidate speeds are gate-1, unsewn, and the ruling is in DOCTRINE. Review: `docs/speed-advisory-review-2026-10-14.md`. *(ruled 2026-10-14 — VP relay of Kent, 20:20 CDT; measured 2026-10-14 — PR #951, `tests/test_stitch_difficulty_census.py`)*

**Short-stitch sources (PR #966, merged 2026-10-15, measure only; the pre-#955 engine, 11 corpus designs against 28 pro DSTs).** 51.0% of our penetrations (56,081 of 109,987) are short or stacked against 23.9% of the pro's: ratio **2.13, 95% CI 1.56 to 3.05** (bootstrap over 11 customers). By count the biggest source is tatami fill (39.2%, the 0.15 mm row turn Kent's row pitch dictates; its stacking is 1.29× the pro's, CI 1.03 to 2.06), so fill is where the count is, not where the excess is. **The worst per stitch is `stage6_border.run_outline`**, the bean emitter behind the run tier and the edge cap: 12.6% of penetrations, 24.4% of the short/stacked, 99 to 100% of its own stitches, and 47% of the short stitches in chains (a class 4.2× the pro's, CI 2.95 to 6.33). Satin columns under 1 mm are the one source breaking a floor the engine states (`MIN_STITCH_MM` 1.0, law 18): 7,461 sub-1 mm stitches. Priced on four designs, nothing sewn: bean pitch 0.73 → 1.5 mm −4.0% stitches / −14.1% short-or-stacked / +1 trim; no edge cap −7.4% / −15.9% / −17 trims (Kent's 2026-09-11 ruling, priced not proposed); satin cross floor 0.5 → 1.0 mm −3.3% / −7.2% / +8 trims. Every constant is a gate-1 candidate; no option is chosen. The first is built OFF as `edge_cap_bean_pitch_mm` (PR #969, MERGED 2026-10-15): on the 11 census designs bean pitch 1.0 / 1.2 / 1.5 mm on the silhouette cap alone takes short-or-stacked −6.6 / −8.7 / −8.9%, with 1.2 the knee and the edge cover as the price (item 59(g)); about 60% of option A's −14.1%, which also re-spaced the run tier. Its sew-out is block P of the #970 card (item 59(h)). `enthusiast_logo` and `logo_bridge_bar` can read differently after #955. *(measured 2026-10-15 — PR #966, `tools/short_stitch_sources.py`, `tests/test_short_stitch_sources.py`, `docs/short-stitch-sources-2026-10-15.md`)*

**The printed worksheet now carries what the screen carries.** It stated size and stitch count, dropped trims and thread metres (two of the four numbers estimate.js calls what an operator needs before loading a machine), and printed a spool code without naming which of the 68 charts numbers it. Both fixed; the facts are computed once and passed, never re-derived at the sheet, and an e2e reads the screen and the real PDF bytes and requires them to agree verbatim. *(fixed 2026-09-07 — scope-history 09-07)*

**The worksheet's thread list was not on the paper.** The page break ran after
each row instead of before it, so on a one-colour design the single row was
drawn at y = 11.09 in on an 11.00 in page — off the sheet — with a blank second
page after it. Three tiers of test passed throughout: a string is in the
content stream whether or not it lands on the paper. The render is capped at
5.5 in so an ordinary design prints on one page, and the sheet now states
whether the design fits the hoop it names (its picture is the GARMENT placement
box, not the hoop, so a 305 mm design looked like it fitted an 8x8). **All seven
downloadable outputs are verified by PICTURE, not bytes** — PES, EXP, JEF, SVG,
PNG, the sheet, and DST, which stopped being the exception on 2026-09-20.
*(fixed 2026-09-07 — area 4; DOCTRINE)*

- **DST — Medium, and the picture is now checked against the file.** Browser
  DST is the Studio's sewn-and-shipping default; the axis and colour-change
  defects that used to hold it below that closed 2026-09-08 (cross-cutting
  section). Python `/export` DST is Medium-High by spec, neither sew-verified.
  **What the previewer draws and what a standard reader sews are compared
  directly** by `tools/preview-vs-dst.mjs` — pystitch's read of the encoded
  bytes against the previewer's own `designToStrands` — pinned by
  `test/preview-vs-dst.test.js` over three fixtures × DST/EXP/PES, with a guard
  that the fixtures still reach the split path. It found and closed one defect
  in all three encoders the day it was built: an over-length move was divided
  by clamping each axis independently, so the file walked an L across a
  diagonal the preview drew straight, with every coordinate, count and extent
  still correct. *(measured 2026-09-20 — DOCTRINE 09-20; scope-history 09-20)*
- **DST header and writer, 2026-10-08.** The header's `ST` now counts every
  body record, END included, as pystitch does (#742); the writer is ~40x faster
  at 50k stitches, bytes identical (#726). The two merged together broke every
  browser DST export (`ReferenceError`) for about half an hour, until #793 —
  `ST` is now `(off - 512) / 3`. *(confirmed 2026-10-08 — `test/dst.test.js`
  green on main; PRs #742, #726, #793)*
- **Export audit, 2026-10-08:** all 11 encoder routes on 12 real designs, read
  back by pystitch; four fixes (service long stitches split, browser PES black no
  longer green, service PES and JEF keep cuts) (#696). Service PES/PEC/JEF now
  name each colour's CIEDE2000-nearest cone, so both PES routes ask for Black
  for near-black (Kent's ruling, #792). *(measured 2026-10-08 — `tools/export-audit.mjs`)*
- **Out-of-range input is refused, not wrapped (2026-10-12).** The browser
  writers throw a `RangeError` on a DST header extent past 99999 units (it
  kept the last five digits), PES/PEC extents or points past int16, and a PES
  with more than 256 colours; `tatamiFill` refuses a row spacing ≤ 0 (it hung
  or exhausted the heap); an empty outer ring sizes 0 × 0 mm, not NaN. The
  Download step already shows a thrown export error; ordinary designs are
  byte-identical. *(confirmed 2026-10-12 — PR #860, `test/engine-edge-cases.test.js`, `test/export-edge-designs.test.js`)*
- **EXP — Medium-High.** The 2-byte trim record (fatal to pyembroidery-convention
  readers at the first trim) and the phantom terminal end-stitch are both fixed.
  *(confirmed 2026-08-06 — PR #58)*
- **JEF (Janome) — SHIPPED 2026-09-07, and it had been counted as shipped since 2026-08-11 without a button.** PRODUCT.md launch item 1 ("PES hardened to byte-verified + JEF export") was marked Done on the evidence that `digitizer_service/formats.py` can write JEF. It can; the Download step offered DST/PES/EXP only, so **a Janome owner could not export anything from this product**. Same defect shape as the DST section below: the module was right and the product did not expose it. Now a button, disabled with a reason when the service is down (no browser JEF encoder exists). Verified by decoding `/export`'s bytes with `pystitch`, not by the writer existing: a logo the app reported as 80.5×16.6 mm, 2 colours, 2459 stitches reads back **2459 sewn, 80.5×16.6 mm, 1 colour change, 2 threads**. Medium-High, same ceiling as PES: pyembroidery cross-validation, not a verified Janome load. **Measured the same day:** VP3 80.4×16.6, XXX and PEC both 80.5×16.6, all 1 colour change and 2 threads; VP3 and XXX shipped 2026-09-12. **U01's "ZERO colour changes" here was WRONG** — re-measured 2026-09-13, it writes `NEEDLE_SET` rather than `COLOR_CHANGE`, so the stop survives; see resolved item 14. **Header defect, pinned rather than worked around: the JEF file DECLARES a hoop it does not fit** — `pystitch.JefWriter` stamps `HOOP_110X110` on anything ≥ 200 mm in either axis, which a 140 × 200 mm design reaches while fitting the app's largest hoop, so `hoopFitNote` stays silent. Hence a persistent note beside the JEF button rather than a line in the hoop dialog; what a Janome does with the mismatch is gate 1. Teardown, the two measured levers and the un-taken rewrite option: [area 4](docs/scope/4-export-formats.md). Pinned by `digitizer/tests/test_jef_hoop_code.py`; if it goes red pystitch fixed it — drop the test and this note. *(2026-09-07)*
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

**Stitch width is a per-shape control (2026-09-29):** an input per measured column in Edit shapes, Auto reset, "whole word" scope (one undo step); the design-width param is now **Design width**. *(confirmed 2026-09-29 — `digitizer.spec.js`)*

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
back the last node. *(confirmed 2026-08-25 — `curvedNodeThrough` tests + browser)* **The border is on the canvas too:** right-click a recognised shape for **Add border** / **Remove border**; it sews on the next run. *(confirmed 2026-09-09/2026-10-05 — `borderMenu.spec.js`, `e2e/field-border-menu.spec.js`; detail in the area doc)*

**Click a shape, edit it there — both lanes (2026-09-29, Kent's ask).** A click on an auto-digitized shape opens `ShapePopover` with its Layers-row controls; on a hand-drawn shape, Fill/Satin, colour, angle and Delete; on a preset, its colour. A hand-drawn shape's anchors and curve handles edit on the field too; the side canvas only draws. *(confirmed 2026-09-29 — `e2e/field-shape-popover.spec.js`, `e2e/field-node-edit.spec.js`; detail in the area doc)* **A canvas edit always has its run button in front (2026-10-11):** the area doc's old "restitch only on the Content step" was the wizard's and is stale — nothing restitches on its own (Kent's 10-05 ruling) and an edit selects its element; the one real gap, a right-click edit under a multi-selection, now collapses the selection to the edited element. *(confirmed 2026-10-11 — PR #839, `e2e/digitize-restitch-trigger.spec.js`)*

**Hand-drawn shapes can have holes (2026-10-01, ruling 11).** Any shape can be marked **Cut out** — in its popover, its assign box, or by drawing it in the side canvas's **Hole** mode; it sews nothing and cuts the smallest shape that contains it, or says it cuts nothing. A node drag that would break that containment holds at the last good position. *(fixed 2026-10-01 — `fieldNodeEdit.spec.js`, `e2e/manual-cutout.spec.js` (d))* Flipping Cut out on the hoop moves nothing else — marking a stray shape Cut out used to make the rest re-fit, 81×39 → 81×91 mm; the side panel's switch still re-fits, as adding or deleting a shape always has. *(fixed 2026-10-01 — `fieldNodeEdit.spec.js` real-engine pair, `e2e/manual-cutout.spec.js` (f))* Needed one engine fix: a three-point hole was silently dropped (4,678 / 4,678 / 4,456 on one square). *(fixed 2026-10-01 — `test/digitize.test.js`, `e2e/manual-cutout.spec.js` mutation-checked; area doc)* **Trace import keeps holes** as cut-outs instead of dropping them with a warning. *(fixed 2026-10-01 — `e2e/manual-trace-import.spec.js`)* **Hand-drawn satin columns (plan 2) are built** — a **Column** mode in the side canvas draws an open spine at a width in mm, sewn between its own rails (`sewAs: { kind: "column" }`, `satinFromRails`); the popover states the sewn width per fabric and warns past 6.5 mm (ruling 5), the drawn width scales with the design and pull comp stays fixed on top (ruling 12); a design with no column is byte-identical. **Plan 3 — open runs — merged 2026-10-12 (PR #840):** a `Line` mode sewing `fill.runAlongPath` (single run or a true 3-pass bean at 0.73 mm, nothing under 2.2 mm), and run ↔ column conversion; read back by pystitch, its worst stitch 0.058 mm off the path *(measured 2026-10-11 — PR #840 body, `test/manualrun-dst.test.js`)*. Taper is not built; auto-splitting a wide column is gate 1. Not sewn. *(confirmed 2026-10-11 — PR #831, `e2e/manual-column.spec.js`, `test/digitize.test.js`; spec `2026-09-30-manual-digitizing-gaps-design.md`)* **A cut-out is clear of thread too, since 2026-10-07:** every fill row floated or stitched across it until `fillColumns` was flipped for this lane (defect 52, Waiting on Kent 22). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`; flipped 2026-10-07 — `app/src/lib/generate.js`)*

**A review edit on a photograph is 44% faster, byte-identically (2026-09-17).** `_reorder_for_cover` was the pipeline's largest single bill — **41.67 s of owl_kent's 72.42 s edit tail** — and almost all of it already-done work: **80 of 82 shapes do byte-identical fill work across a border toggle**. Both fill reorders are pure functions of ONE shape's own inputs, so a content-keyed memo is exact (79.34 → **44.61 s**, checked against the same edit computed cold). **That purity IS the safety property — re-check it if either reorder is edited**, or this becomes silent corruption rather than a failure. *(measured 2026-09-17 — `tests/test_fill_reorder_memo.py`, 5 mutation-verified; area doc)*

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
  an explicit **pending sew-out** flag instead of a guessed score, because the
  controlled sew-out card that would settle them has not been sewn (the one
  physical out, 2026-09-01, was an uncontrolled icon).
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
4. **Budget: 27,000 WORDS** — measured with
   `awk '{n+=NF} END{print n}' MASTER_SCOPE.md`, never `wc -w`, which is
   locale-dependent here and answers 908 words lower where `LANG` is unset.
   Over it, compact before adding. The number has teeth on purpose: a skill
   already told agents to keep this file current and it reached 5,400 lines
   anyway, one paragraph at a time.
   *(ruled 2026-09-14 by Kent, replacing the 800-LINE budget of 2026-08-14,
   which could not see this file's content in either direction — reasoning and
   the locale trap: DOCTRINE, "A budget that cannot see its own file")*

4b. **And 400 WORDS PER ENTRY** — no numbered defect may exceed it; overflow
   goes to its area doc with the verdict left behind. Guarded by
   `tests/test_scope_budget.py`, not advisory.
   *(ruled 2026-09-30 by Kent, on the measurement that the total-only budget
   was being met by ARITHMETIC: four commits across two weeks landed within
   three words of 27,000 — 26,996 / 26,995 / 26,998 / 26,997 — because a lane
   trims whatever is cheapest that day, never the expensive thing. **400, not
   the 250 first proposed:** that recommendation rested on a median of 113
   words measured with a regex that only matched SINGLE-LINE entries; the
   file's own parser says **214**, so 250 would have sat 17% above typical and
   put every ordinary edit straight back into trimming. 400 is about twice the
   median and bites the tail only — 5 entries of 25. What it surfaced first
   was six defects marked FIXED still sitting in the LIVE list with their full
   narrative. Landing it took the file 26,482 → ~20,000 and bought the merge
   headroom whose absence overflowed the budget on 2026-09-20 and again on
   2026-09-29, when two separately-legal lanes met.)*

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
