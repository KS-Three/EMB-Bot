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

**Last updated:** 2026-10-03. **This file is current state only, under a
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
   **An open assumption under the whole 3.1x (2026-09-13):** the corpus was decoded from the pro's FILES, so it records what the file says; whether it records what the MACHINE did is unestablished — ten machine-side trim-threshold claims went to adversarial vote and **all ten were refuted**, and a machine trims only connectors longer than its own setting whatever the file requests. Not assumed either way. In our favour: **vendors publish no distance rule** (Hatch's coverage rule; a three-state override whose Off/Always bypass the mm value; Embird, sew ORDER only), so *"no single threshold reproduces this pro"* is the published model's expected shape, not an anomaly — though those rules govern needle-DOWN runs and this corpus is needle-UP. *(`docs/trade-knowledge-2026-09-13.md` §1, §6)*    *(2026-08-15/18/21, corrected 2026-09-06 — `docs/fragmentation-attribution-2026-08-18.md`, scope-history 09-06)*

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
*(2026-09-01 — `test_duplicate_cone_layers.py`, 13)* **A THIRD mechanism is open, found 2026-09-06 by `COLOR_STOPS_HEAVY`'s `repeated_cones` field: 4 of 52 design/garment combos still sew a cone in more than one block WITH this fold ON**, by two routes it cannot see — gradient BLEND BANDS from different parents (a band is not a layer declaration), and plain regions that re-snapped to the same cone from different layers. The second route is closed by `bind_resnap_all_classes` (defect 15), which buys `screenshot` six blocks; the first would need a band fold priced at an 11-block reorder. Full numbers and the case against building it: [area 1](docs/scope/1-auto-digitizing-quality.md). `tests/test_cone_revisits.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

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
needle-breakage signal. ~~No off switch for photo classes~~ — stale when written; it landed 2026-09-01 (PR #316), so **the other half is measured: the tier costs −22,352 st / −16.4% of the photo lane, and with it OFF four of nine score HIGHER, none lower**, `coverage_max` falling wherever it moves. **A yardstick finding, not a flip** — nothing in the scorecard scores tonal gradation, and Kent ratified the tier (spec decision 2). `SAME_HOLE_RATE_MAX` is deliberately NOT retuned: its baseline is pro files at their own pitch, and the density-invariant half (`max_strikes`, `points_3plus`, `worst_at_mm`) is what got emitted instead. Full bill: [area 1](docs/scope/1-auto-digitizing-quality.md). `tests/test_same_hole_depth.py` (8). *(measured 2026-09-06 — scope-history 09-06)*

21. **Fill travel is laid OVER columns already sewn — FIXED, DEFAULT ON (Kent's flip
    2026-09-03)** (`cfg.fill_travel_under_cover`, PR #323): the column order prefers a next
    column reachable over unsewn ground (`_reorder_for_cover`, cuts × 25 + travel + exposed × 2,
    never worse) and an exposed bridge routes through unsewn ground. Fill-phase exposed travel
    Fremont **286 → 90 mm** (trims 47 → 52), drone 546 → 89 — 09-03 figures, STALE; OFF md5-identical; +7–11% time on logos, +49–67% on the 263-run photo fill. *(measured 2026-09-03 — `docs/fill-travel-under-cover-2026-09-03.md`)* **Residual:** 2026-09-11, 80 mm, Becker **29.6 of 76.7 mm**, Bridge Bar 114.2 of 275.4, Fremont 23.9 of 123.5. **The CAUSE is now established and it disqualifies all three fixes review item 12 proposed** (`digitizer/tools/fill_bridges.py`, 9 fixtures / 92 bridges / 912.6 mm): **88% (801 mm) have NO unsewn corridor touching both ends** — no routing rule reaches them, the column ORDER made them — 6% a corridor the router cannot use, 4% the detour cap, 2% already buried by a later cone. Priced out (DOCTRINE): routing under the covering colour (the 2%), lifting bridges under `trim_at` (26 mm, none on the four review designs), a raised detour cap (BUILT, a **perfect no-op on all nine**). A fourth arm (prefer a next column still sharing unsewn ground) is WORSE on six of nine (gaulke 3.1 → 84.0 mm): `_score` buys its fewer CUTS at 25 : 2, and a per-shape ratchet did not stop it because `_order_cost` and `emit` can disagree (`route_cache`). Both reverted (DOCTRINE). Left: Kent's exchange rate, scorer/emitter agreement, the greedy itself.
    *(measured 2026-09-11 — `docs/superpowers/plans/2026-09-11-fill-travel-bridges.md`; `tests/test_fill_bridges.py`, 4)* **`travel_cover.py`'s 245 mm on the nine logos IS this residual:** 97.7% `stage6_fill`'s `emit`, all on the shape's own finished fill, **0.0 mm on bare fabric** — not gate 3's letter; its grid under-reads (375 mm exact). **`cfg.fill_bridge_cut`, DEFAULT ON (Kent's flip 2026-09-19, over thread renders, not yet cloth):** lift a bridge costing more than the cut at 25 : 2, single-pass fills only — exposed 248.6 → 140.9 mm, trims 458 → 464, uncovered unchanged, OFF md5-identical ×9; Fremont's new `LETTERING_ILLEGIBLE` is the OCR judge (tagline runs byte-identical). *(measured 2026-09-19 — `digitizer/tools/travel_legs.py`, `tests/test_fill_bridge_cut.py`, 15; scope-history, "the exposed travel legs")*

22. **Small curves sew as polygons — FIXED, DEFAULT ON (Kent's flip, 2026-09-03)** (`curve_turn_deg` = 15; None/0 = the old polygon): a turn-per-vertex bound re-reads each Douglas-Peucker edge against its raw arc, split at the midpoint, floored at one pixel; near-floor lettering exempt per ring. Fremont's counter **9 → 33 vertices, 47° → 17°**, inner rail σ 0.038 → 0.026 mm, trims 52 → 45. **Gated to 20 px/mm** (`_CURVE_MIN_PX_PER_MM`; four pixels of tolerance at 0.2 mm): below it the 1-px floor read raster texture as arcs — every 10–16 px/mm fixture got rougher (sunset 16.1 → 16.5, meadow 15.2 → 16.5) and two borderline ribbons changed tier through the DT classifier's skeleton — so a 600–1200 px web logo at 80 mm is byte-identical and every golden stays pinned — but 1200 px art at ≤ 60 mm (2000 px at ≤ 100 mm) is over the line and refines, and the line is a cliff (60 → 61 mm changes every curve's polygon; Kent's to accept); `tools/curve_tiers.py` is the per-shape tier diff. *(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

23. **Rail dents — FIXED (Kent, 2026-09-03), diagnosis corrected.** `place` stepped an overshooting rail in by 15% however small the overshoot (250–1000 placements per design, 70–90% under one pixel) and now puts it on the artwork edge along its own normal, with a micron of containment tolerance; taper zones and caps keep the ladder. Rail jitter p50 **halves on every fixture** (Fremont 0.012 → 0.0045 mm), same-rail holes 11 → 5, median rail 0.02–0.08 mm further out, nothing further outside the art. The "one whole rail 15% short in every golden" was the synthetic bar, not the goldens (the micron alone moved 4 stitches on Fremont); the 8–24% of rail points > 0.1 mm inside on real art turned out to be the short-stitch guard, corridor caps and corners, not the rail model — the honest coverage number is BARE SATIN AREA, and each rail reaching its own edge (`satin_rails_follow_edge`, **BUILT, DEFAULT OFF, Kent's flip**) takes it Becker 8.6 → 5.8%, ENTHUSIAST 5.7 → 4.4%, drone 6.1 → 4.6% for +10–17% thread, +50% rail jitter and more guard retractions; the pull comp was tuned with the far rail short — a sew-out question. Goldens re-pinned in #329: alpha, ribbon ×3. *(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md`)* **Its cost is OVERSHOOT, not bare art (2026-09-20):** measured colour-free, `enthusiast` leaves **0.90% of its ink unthreaded, nothing over 1 mm²** — no lost element — while thread covers 1.51× the ink. `lost_frac` ships SPLIT. *(measured 2026-09-20 — PR #536; DOCTRINE)*

24. **Hairline columns (< 0.6 mm) — the MECHANISM is fixed, the tier is not.** A hairline STRETCH of a stroke (crosses under the 0.5 mm floor, ≥ three bean stations of spine) now sews as a 3-pass bean along its spine in both engines, only where the uncompensated art is wider than `simplify_tol_mm` (pull comp grew a 0.04 mm needle into a tick); Fremont's 2.6 mm "THE" reads. Whether a 0.5 mm bean reads better on cloth than a dropped bar is card block 5's question — `pending sew-out`. *(fixed 2026-09-03 — `docs/design-review-fine-lettering-2026-09-03.md`)*

25. **Fill stitches HALVED by float dust at the stitch-length threshold — FIXED (Kent, 2026-09-03).**
    `split_long_moves` split a 3.0000000000000004 mm grid step into two 1.5s; a micron of tolerance
    (`stitches.SPLIT_TOLERANCE_MM`) removes them: whitebg 2162 → **1982** st, Fremont 6365 → **5789**, sunset 11614 → **10416**, no row or trim moves. Goldens re-pinned (whitebg, alpha; pre-change tree). `tools/fill_dust.py`. *(fixed 2026-09-03 — same doc)*

26. **Satin/fill classifier flips borderline shapes under boundary detail — MEASURED NEGATIVE on eight cures, intrinsic to the thresholds (2026-09-03).** 5 of 219 DT-judged verdicts flip when only the polygon's detail changes (4 on a threshold edge: cv 0.5, aspect 3, `explained` 0.80); spur pruning ×3, the sewing spur rule, a hybrid, raster smoothing ×2 and a regularity band leave 3–12 flips and change 2–48 shipped verdicts, so nothing ships; the mitigation is `_CURVE_MIN_PX_PER_MM`. Open only as a different construction (a margin with memory, or a polygon-native width profile) — Kent's call. `tools/ribbon_stability.py`. *(measured 2026-09-03 — `docs/classifier-stability-2026-09-03.md`)*

27. **Compression halos become their own cones — and the flat lane has dissolved them all along.** `stage2_quantize._quantize_population` runs "majority filter, then phantom-blend dissolve"; **the SLIC+RAG lane never got that pass**, so this is a missing PORT, not a missing idea. `logo_bridge_bar.jpg` pays it in six grey cones sewing the ringing around its black spokes. **FIXED, DEFAULT OFF** (`cfg.dissolve_phantom_blends`): a merged label that is more than half boundary AND a Lab interpolation of its own two sides folds into the side it is nearer. Bridge Bar 74 → **32** regions, 14,607 → 11,524 st, **114 → 64** trims, silhouette −4.2%. **The fold's one wrong turn fixed 2026-09-30 (Kent's pick):** a member folded into the endpoint's LABEL rather than the instance of its colour it touches became a detached region, re-read from the source as grey and snapped to teal — nine specks on the ring; folded into the black it borders, bridge reads 80 → **20** regions, 16,179 → 11,385 st, **101 → 43** trims on the shipped engine, the other five gradient logos untouched by the redirect (`docs/eye-pairs-2026-09-30/`, on the page for his flip). **Read the cone count (13 → 11) LAST** — five of six greys go, all four real cones survive, and three NEW cones arrive on artwork the palette could not afford; what changed is what the cones SEW, by the palette's worst excess **20.76 → 3.68** dE00. Residual: `0111` Whale survives as 12 shards, cause not established. **Kent did not flip it on the day**, citing two mild negatives and the five-of-six residual; the flip is a one-line default plus a 26-fixture scorecard recapture, to be decided alongside other gradient-lane work. The eleven-fixture bill and the page-label direction tests: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-09-04 — scope-history 09-04; `tests/test_phantom_blend_photo.py`)* **Same lane, 2026-09-30: `snap_region_edges` ON (Kent, on renders)** — region edges follow pixels, not SEEDS superpixels; his Instagram icon 44 → 28 trims, drone's `THREAD_MATCH_POOR` blocks 5 → 3. *(scope-history 2026-10-01)*

28. **The largest quality wall in the corpus is three problems wearing one code — and one of them is two floors set 4× apart.** `THREAD_MATCH_POOR:block` grades **7 of 26 fixtures F 0** (14 of 52 matrix entries), all `gradient`, which is where real logo art goes. Decomposed 2026-09-06, re-read 09-07: **(1) the raw yardstick, 4 of 7** — `golden_tee`, `drone_render`, `region_blobs`, `summit_badge` clear every block once scored on EXCESS over the loaded spools, the photo route's 2026-08-24 rescoring that the gradient lane never got; reproducible with `tools/spool_remedy.py --yardstick`. **The offender set MOVES WITH THE YARDSTICK**, so a probe that keeps the raw top and reports its excess gets this wrong. **(2) halo cones — RETRACTED 2026-09-07, the category is EMPTY**: on the fixed tree defect 27's flag is byte-identical on gaulke, so the wall decomposes 4 + 0 + 2 and **gaulke is the seventh, unexplained** (worst ΔE 63.6). **(3) the clamp floor:** the score clamps at 0, and a floored design sits hundreds of points under water — `golden_tee` needs ~312 points and ~11 blocking findings before its grade moves one letter — which is why a real thread fix here moves nothing. Un-clamping re-bases every grade, so it is a product call, Kent's. Full decomposition: [area 1](docs/scope/1-auto-digitizing-quality.md). *(measured 2026-09-06/07 — yardstick-disagreements rows 3 and 6)*


30. **The review screen's per-layer cone list named threads its layer does not sew — FIXED, DEFAULT ON since 2026-09-13** (`cfg.layer_palette_from_regions`, `stage3_segment.layer_palette_threads`). `palette[i]` answered *what stage 2 CALLED layer i*, not *what its shapes sew* — `compact_layers` drops slots and never re-reads a survivor's thread. ON, each layer's cone is elected from its own regions, pinning `palette[i].number in {r.thread_number for r in layer i}` — **not** `palette ⊆ block cones`, which the blend tier breaks. **Every number this entry used to carry was wrong** — count, direction and mechanism — and the corrections are tabled in the doc below, including that at the Studio's shipped `max_colors=6` the defect ran **5× its published size**.
    **Flip cost:** mislabelled layers 7 → 0 at 12 and 13 → 0 at 6, with the plan digest, every stitch coordinate, `design.colors` and `thread_mm_by_color` **identical off vs on, 26/26, both settings** — *review-only* is a measurement now, not a call-graph argument. **Accepted price** (Kent's, knowingly): duplicate review ROWS, 0 → 13 at 6, because `merge_duplicate_cone_layers` folds on the DECLARED cone upstream of the election; folding them is the open follow-up and moves sew order. *(measured 2026-09-12 — `docs/palette-mismatch-2026-09-12.md`, `docs/palette-flip-corpus-2026-09-12.md`; `tests/test_layer_palette.py`)*


32. **The low-resolution warning could not fire, and the Studio was wired to show it.** `stage1_prep` tested the resolution AFTER its own capped Lanczos upscale — and with `upscale_cap` and `min_px_per_mm` both **4.0**, any source at or above 1.0 px/mm lands exactly ON the floor, so the condition was false for every design a customer could send. `INPUT_LOW_RESOLUTION` has been in the Studio's `ATTENTION_WARNINGS` and had a `WARNING_TEXT` sentence the whole time; neither had ever been shown. **FIXED, no flag** (2026-09-07): it fires on `Prep.input_px_per_mm`, what the FILE supplied, and reports that plus `upscaled_to` and the floor — the old `px_per_mm` extra was the post-upscale value, i.e. the constant 4.0 dressed as a measurement. The customer sentence now carries the number and the multiple ("1.4 pixels per millimetre at this size and needs 4 … about 2.8x wider"), because "low resolution" says there is a problem and not what fixes it. **Precise, not noisy: exactly 2 of the scorecard's 26 fixtures arrive under the floor** — `becker_marine_logo` 1.81 px/mm and `logo_bridge_bar` 3.49 at 80 mm — and they are two of the three renders `docs/kent-review-2026-09-03.md` reports as settled before the engine ran ("a higher-resolution Becker source would change this render more than any engine change"). Both were silent. *(measured 2026-09-07 — `tests/test_input_resolution_warning.py`, `app/src/lib/digitizer.spec.js`)* **The warning's line and the tracer's grid are two numbers since 2026-09-30** — defect 51; the "settled before the engine ran" reading of bridge was wrong.





37. **Two launch-scope features sat behind an unannounced right-click — FIXED 2026-09-07 (one sentence).** The basic shapes tool (PRODUCT.md launch item 4, ✅ Done: *"all four kinds verified digitizing live 2026-08-11"*) and the manual draw lane are reachable ONLY from the canvas's context menu — Kent's placement call 2026-08-13, *"keep them, but as a right-click tool rather than an upload button"* — and **nothing anywhere in the UI said so.** The Content step offers three tiles (Text / Artwork / Design file); right-click on a canvas is a power-user idiom a first-time customer has no reason to try. Verified working end to end from that menu (Draw shapes / Basic shape → Circle, Rectangle, Heart, Star → 3,918 stitches at 51×51 mm), so this was discoverability alone, not a broken lane. **The obvious place to say it is the wrong one:** the drag hint is gated on `stitchCount > 0` (`hints.js` condition A8), so it appears only once a design exists — after the question has stopped being asked. The empty-canvas line is what a customer is looking at while wondering what to do, and it now reads *"Your embroidery appears here as you add content. Right-click the canvas for drawing tools."* Kent's placement is untouched; reverting is one string. e2e pins the sentence AND that the gesture it names reaches both tools and produces real stitches. *(found by listing the Content step's buttons 2026-09-07)*

38. **The simulator counted in a different unit from the caption right under it — FIXED 2026-09-07.** The stitch simulator is driven by STRANDS (the segment between two consecutive stitches, which is what actually paints), and its counter showed that raw index: **"1289 stitches · 102×12 mm" under the canvas and "1280 / 1280" in the simulator bar**, both visible at once, nine apart on a design with nine runs. Both numbers were correct measurements of different things and only one carried a unit — the same family as defect 34, one screen over. **FIXED**: `strandStitchOrdinals` (strands.js) maps each strand to the stitch number it ends at, computed once per run, so the counter reads *"1289 / 1289 stitches"*. The animation still runs on strands. **The total is the LAST ORDINAL, not `design.stitchCount`** — a run of a single stitch paints no segment, so the simulator must never claim to have drawn it; the fixture has 0 such runs, and the tests cover one that does. `strands.spec.js` (5), e2e (1, plus the format pin in `field-chrome.spec.js` updated with its reason). *(found by watching the simulator run 2026-09-07)*

39. **"Exceeds your 8x8 in hoop" pointed at a fix that does not exist, on 40% of the garment picker — FIXED 2026-09-07.** Auto-fit targets the garment's PLACEMENT BOX, and **four of the ten shipped boxes are larger than the biggest hoop the app offers** (8x8 in = 200 mm): `full_back` 304.8x304.8, `jacket_back` 304.8x254.0, `blanket` 254.0x203.2, `tote` 203.2x203.2 mm. So every design on those four is oversize by construction, on every run — and the message named the chosen hoop as though a bigger one would help. It would not; there isn't one. `hoopFitNote` now distinguishes the three genuinely different fixes: rotate (unchanged), **a named bigger preset** (*"Exceeds your 4x4 in hoop — a 5x7 in hoop fits it"*, which the app already knew and made the customer work out), and **nothing fits** (*"Exceeds your 8x8 in hoop, and every hoop this app offers — make it smaller under Size"*). Message only. **Whether auto-fit should CAP to the hoop is the open question area 3 already carries and is Kent's** — capping would silently shrink every back-of-jacket design. The four impossible garments are asserted as a SET, so adding a garment or a bigger preset shows up in the tests rather than silently changing what 40% of the picker says. `hoop.spec.js` (3). *(measured 2026-09-07)*

40. **"Size up for crisp letters" was advice the DEFAULT design cannot take — FIXED 2026-09-07.** Lettering is fit by WIDTH, so for a fixed character count the cap height is proportional to the design width: measured with `medium_font` on left_chest's 101.6 mm placement box, every design at that same width, *"WIDE DESIGN TEXT HERE"* gives a **4.33 mm** cap, *"SHORTER TEXT"* **7.16**, *"ABC"* **30.03**. An auto-fit design (`sizeMm` null — the default, and what every quick start produces) is ALREADY at that box, so "size up" is the one thing the customer cannot do, and the levers that remain — fewer characters, a bolder font, a bigger placement — went unnamed. `letteringNote` now takes `atWidthCap` and swaps only the advice clause: at the cap the thin-lettering finding reads *"…already the full width of the placement, so fewer characters or a bigger placement is what makes them crisper"* and the hairline finding keeps "bolder font" (still true) and drops "size up". Below the cap both are unchanged — "size up" IS the fix there, verified in the app at W 2.60 in. **Read off the REQUEST (`sizeMm`), not the sewn width**: since defect 34 the sewn extent is slightly past the box by construction, so comparing it to the box would read "capped" for every design. The two findings that are not about size (cap under the floor; a lone hairline span, which reports what the engine DID) are untouched, and that is asserted. `generate.spec.js` (3). *(measured 2026-09-07)*

43. **The numbers chain agrees end to end, and is MEASURED rather than argued.** Canvas caption, review recap, PDF worksheet and the downloaded DST read back by `pystitch` all give one set of figures on a mixed design, and the simulator counter agrees at both ends. It can be stated as fact only because each link was DRIVEN rather than reasoned from a shared code path — which is the part worth keeping. The figures: scope-history 09-08. *(measured 2026-09-08)*

47. **`overlap_mm` is one scalar at 0.25 mm, against a law that wants 1.0–2.0.** Law 26 asks 1.0 mm where parallel stitch directions meet on wovens, 1.5–2.0 on knits/fleece and ~0 near-perpendicular; `config.py:918` is angle-blind, fabric-blind and sits under the law's own 0.8 mm close-up threshold, and no forbid-gap rule exists. Most of it is desk-safe and buildable now — only the knit value is gated. Detail: [backlog](docs/scope/machine-physics-backlog.md). *(confirmed 2026-09-20 — playbook row 9)*


49. **A letter's tapered apex sews BARE under `satin_rail_comp` — CLOSED 2026-09-30 behind `cfg.satin_crown_cover`, ON BY DEFAULT since Kent's flip 2026-10-02.** ENTHUSIAST's A at 80 mm: the column reaches within **0.08 mm** of the artwork's apex with the pull in the polygon and stops **1.63 mm** short with it on the rails. **The hole was settled as real before it was fixed**, because two instruments disagreed: `bare_anatomy` said 3.61 mm² but counts satin crosses only and over-reports 1.7x here (underlay threads 38.4%), while `unsewn_frac` read 0.0 and cannot fire on this fixture at all — its on-ink vote needs a region over 0.5 ink and the largest is 0.33. What survives both corrections is **2.17 mm² carrying no thread of any kind**, 1.72 mm² of it surviving the 0.50 mm opening, confirmed by a raster mask difference sharing no code with either: its largest uncovered component in the whole design, 0.97 mm², sits **0.33 mm** from the apex (next: 0.70 mm², 35 mm away). Drawn from the actual thread path: [`docs/renders/apex-verdict-2026-09-30/`](docs/renders/apex-verdict-2026-09-30/). **Preflight now sees it** (1.56 mm² on the 0.25 mm grid; its 0.4 mm erosion had hidden it entirely), and `satin_crown_cover` covers it for +0.5% stitches at an unchanged `lost_frac`. **Defects 49 and 50 are ONE mechanism** — artwork no stroke reaches — which is why one cover closes both. Still blind: `dropped_elements`' `uncovered_elements` misses it by **0.03 mm²** against `MIN_ELEMENT_MM2` 1.0. **An earlier fix was built and RETRACTED**: widening the tip closed the hole and pushed `lost_frac` 0.2573 → 0.2661 past its 0.26 bar at 100% overshoot — the reason `lost_frac` is the crown cover's gate from its first commit. *(measured 2026-09-30 — `tests/test_apex_is_real.py`, `tests/test_crown_cover.py`; scope-history 09-30)*
50. **`satin_lettering_split` leaves holes at the crowns of curved letters — CLOSED behind `cfg.satin_crown_cover`, built OFF 2026-09-30, ON BY DEFAULT since Kent's flip 2026-10-02.** MARINE 127.4: the split sews the word in 7,168 stitches with **11 holes / 22.9 mm²** where fill leaves none. It is still a NET WIN — `lost_frac` 0.2688 fill against 0.1800 split — so this was never a case for reverting the flip. **The crowns are not in any column:** five rail and pitch arms are refuted (the envelope inert, `follow_edge=True` 2 of 11, the width smoother deleted 0 of 11, pitch halved 1 of 11 for +1,567 stitches) and every arm that moved one made `lost_frac` worse. The strokes' union leaves wedges no stroke claims, 4 of 11 at a node between sub-strokes. **The cure is the junction cover with its junction gate removed and `ARTWORK_UNCOVERED`'s own thresholds** (Kent's ruling, design doc §7: a cover, all satin shapes). ON: MARINE 127 **11 → 1 hole**, 22.9 → 1.5 mm², +2.6% stitches, `lost_frac` 0.1800 → **0.1730**; corpus holes **20 → 10** with `lost_frac` never rising and golden_tee **1.4% cheaper**; the four fixtures with no holes find no wedge at all. **Flip is Kent's.** *(measured 2026-09-30 — `tests/test_crown_cover.py`; scope-history 09-30)*
51. **Low-resolution line art lost its fine detail at the TRACER'S GRID, not in the file — FIXED, `cfg.work_px_per_mm` ON at 8.0 (Kent's flip 2026-10-01, on renders: full-size file best, this grid second, the old grid third on every logo; None = the engine before it).** Kent's ask: bridge's "RESTAURANT" completely missing. A source under `min_px_per_mm` was enlarged to 4 px/mm and traced there; a 0.7–1.4 mm stroke is then 3–5 px, the gradient lane's superpixels hold ink and ground both, and the RAG merge — which compares MEAN colours at 26 dE00 and whose two protections are gated at 1,000 px — swallowed the letters (bridge: 67 of 81 mm² of teal held by SEEDS, **39** after the merge, six blobs sewn). The same file on a 5–10 px/mm grid keeps 64–67. Stage 1 traces line art on the working grid and `min_px_per_mm` keeps only the `INPUT_LOW_RESOLUTION` warning; photo classes keep the source line; a 2,800 px side bounds it. **Not bridge's alone:** real logos downsampled to 5 px/mm and scored against their own full-resolution digitization recover fine ink **0.64 → 0.84** on average (ENTHUSIAST 0.25 → 0.90, its tagline; Fremont's "THE"; Golke's second line), and nothing in the corpus could have shown it — bridge was the only gradient logo under 5 px/mm. **Costs:** trims rise toward the full-resolution file's own count; a blurred synthetic (`logo_whitebg` at 5 px/mm) pays 12 → 21 trims; sources at 6.5 px/mm gain little (two of five logos down). **Still open, and a different defect:** the recovered letters are 3.25–4.5 mm and each sews as ONE satin bar — present, not legible letter by letter; that is `LETTERING_TOO_SMALL`'s size question. **Not robust:** the result moves with small changes to the foreground mask (a smoother mask sent bridge's words to a grey-green cone and cost ENTHUSIAST 0.90 → 0.70), and 43 tests read on the old grid hold it (`conftest.source_line_grid`), a few of them real costs on 6–7 px/mm synthetics (the radial ramp sews 2 regions for 1). **Open, Kent's:** his verdict also says the SOURCE is the bigger lever, and `INPUT_LOW_RESOLUTION` only fires under 4 px/mm — the 5 px/mm files on his page lost to their full-size selves unwarned. Detail: `docs/fine-detail-work-grid-2026-09-30.md`. *(measured 2026-10-01 — `tools/lowres_detail.py`; `tests/test_work_grid.py`)*
52. **A fill in the BROWSER engine carries thread across every hole and every notch — CLOSED behind `fillColumns`, built OFF 2026-10-03 (Kent's flip pending).** The JS tatami walk goes from one span of a split row straight to the next: a float over a long gap, a STITCH over a short one. A 40 mm manual fill with two cut-outs: **76 untrimmed floats across the 12 mm one (912 mm of thread), 20 stitches sewn across the 3 mm one.** **Two things hid it:** the engine's test counts needle points in the hole, and a float has none; the Studio draws jumps only with its Jumps toggle on. (Quality review 2026-09-08 §4; drawable since #591.) **The cure:** rows cut into monotone columns (`fill.js`, a port of the Python `_columns`), and every move of every pass of the shape asked what ground it runs over, the ground being what the FILL covers. On it: unchanged. Off it by no more than a fill row (0.15 mm): sewn, never floated. Deeper: the thread goes ROUND — along the hole's own edge, or in by a strip's far end under that strip's own rows — and is cut only where there is no way round. **Audited** on 9,869 designs (three scales, all seven presets): floats that leave the fill's ground **1,154,992 → 0**; designs with thread deeper than a fill row off it **8,581 → 36**, none of the 36 across a hole. **Cost:** cuts fall from 0.89 a design to 0.25, though 3% of holed shapes keep one and a comb can gain four; stitches +3.3%, at worst +37%; the travel shows, with up to nine lines of thread on a rim's worst millimetre and over 5 mm across sewn rows in one holed fill in six; a forked large fill loses center-out; the edge run of a shape with a hole or an inside corner moves 0.2 mm inside the fill. A shape with neither is untouched, and so are satin shapes. **Not sewn: no sew-out exists.** **Three builds, three independent audits**, each failing the build before it. **Reaches** the fill shapes of every `buildQualityDesign` caller: manual, basic shapes, the image lane. **Not built:** row stagger (tie stitches: "Waiting on Kent" 23). **Flip is Kent's**; the sheet, the cost tables and what was seen but not changed: [`docs/renders/fill-columns-2026-10-03/`](docs/renders/fill-columns-2026-10-03/). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`; `test/fill.test.js`, `test/digitize.test.js`; three independent audits, scope-history 10-03)*

55. **A hand-drawn shape with an anchor a pixel from the last one sews a spike at that corner, under every preset — THE GESTURE THAT MADE THEM IS CURED 2026-10-03 (Kent's pick); the offset is not, so saved shapes keep theirs.** Found by the audit of defect 54's fix. A double-click is two clicks and a `dblclick`, and `ManualPanel.onCanvasClick` took the second as an anchor unless it landed within 0.5 canvas px of the first (`DUP_POINT_EPS_PX`): a slip of a pixel left an anchor a pixel from the last. The short edge to it doubles back, and the BROWSER builder's `offsetRing` gives its end the whole mitre clamp, three times the pull compensation: defect 54's wedge, from a NEAR repeat, which 54's cure (1e-9 px, rounding) does not reach and should not. A 40 mm box whose second click was 1 px off: fill **1.73 mm past the drawn ring on terry, where a clean corner has 0.85**; cap 1.13 against 0.57; pique 0.73 against 0.42. Of 80 slips of 0.6 to 3 px, 20 were refused as crossing (the double-click finished nothing) and 60 kept; on terry 30 of the 60 sew over 0.15 mm further out than a clean corner, at worst 1.81 mm. **Cured at the gesture:** the second click of a double-click (`detail` 2) is no click of its own, however far the pointer slipped. In a real browser three slips of four went wrong before and none does now. **Still open:** a shape saved before the cure keeps its anchor and its spike, and two anchors dragged to one hoop corner make another (the audit's measure, not re-run here). Curing those means the offset (a bevel past the clamp), which moves every sharp corner under a preset: not built, and Kent's call. *(measured 2026-10-03 — `tools/closed-ring-census.mjs` table 4; `app/src/ui/ManualPanel.spec.js`, `app/e2e/manual-double-click.spec.js`; scope-history 10-03)*

57. **The BROWSER's medial satin lays a stitch as long as the shape, and sews strokes twice — MEASURED 2026-10-03 on the Studio's own shapes, NOT fixed (which cure first is "Waiting on Kent" 26).** Found by the sweep that found defect 56, and standing after it. **A star:** every satin star the shape tool makes has a stitch over 3 mm; the longest is a median 21 mm, eight in ten over 12.1 mm (one DST record), up to 98.5 mm, laid from one arm to another across the centre. The branch guard is what sends it there: an even-pointed star splits tip to tip into equal halves whose rung midpoints sit on the axis, so twelve arms pass as ONE column (15,312 of the 145,600 designs swept are satin). **A bar:** 185 of 276 sharp-cornered satin bars on left chest carry a stitch at least nine tenths the bar's length: the spine runs on down the end's edge into a corner and the last crosses turn with it. **Twice:** the edges lay a median 72 pixels too many for every 100 the skeleton has, and the ring scan finds "rings" in shapes with no hole (126 of 1,684 star rings); three stars and 24 round-cornered bars still sew 2 to 3.7 times their neighbours in size, and such a ring is all a 2 mm round shape sews (four stitches, 28% covered, where the 2 mm circle sews 13). Also: a satin star stops a median 1.2 mm short of its tips (up to 10.8 mm; the 20 mm star's "17.1 mm" is this); the emitter keeps 24 edges where 870 of the 1,684 rings have more; and a 5-point star's tier turns on the last bit of a float (the guard's ratio is exactly 1.5 against "over 1.5"). **Reach:** every lane that hands a shape to `medialSatin`: basic shapes (a thin bar, a small or needle star), a drawn shape set to satin, the image lane's thin shapes. The tool's defaults (50 mm) are fills and are not in it. **Why it is not one fix:** three causes and three cures, and a fourth cure that would cover two of them (how long a cross may be) is a number no geometry settles. Not sewn. Pictures: [`docs/renders/star-walk-2026-10-03/`](docs/renders/star-walk-2026-10-03/). *(measured 2026-10-03 — `tools/satin-walk-census.mjs`; scope-history 10-03)*

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
44. satin borders sat a median 1.4–1.9 mm INSIDE every abutting colour (14 of 17 bordered shapes on the 80 mm icon) — FIXED 2026-09-09 on Kent's ruling that the colour sewn on top owns a shared seam (`_owned_by_later`, `border_runs(omit=…)`; 33,292 → 30,420 st, trims 34 → 30). Standing ruling: DOCTRINE. Full text: scope-history 09-29.
45. no preset declared its assumed stabilizer; backing was guessed from stitch count — RESOLVED 2026-09-20 (`Fabric.assumed_backing` / `needs_topper`, both engines; the worksheet prints both). Playbook law 33.
46. the smoothness scores existed only offline and preflight could not see them — BUILT 2026-10-03 AS METRICS, both halves: Law 37's direction-change score (`curve_roughness_deg`, read with `curve_turn_gini`, `curve_vertices`, `curve_corner_vertices`, `curve_traces`) and edge deviation per tier (`edge_wobble_{satin,border,fill,line}_{p95,std,max}_mm`). No finding, no deduction, nothing in the Studio, so the GRADE stays blind to both on purpose: Law 37 forbids a cutoff, and Kent ruled 2026-10-02 that the tool does not warn the customer about what it should fix. Baseline recaptured 2026-10-04 at `6e0cb943`, every row carrying all 17 keys, so `corpus_scorecard.diff` reports their drift from the next change on. Still true: neither number has met Kent's eye; roughness cannot read intent, so it compares a design with itself and is never a grade; `edge_smoothness` stays offline. Not `curve_turn_deg`, which an earlier read scored as this. Playbook law 37; `tests/test_curve_roughness_metrics.py`, `tests/test_edge_wobble_metrics.py`; scope-history 10-03.
48. no machine-time model, so nothing quoted a runtime — RESOLVED 2026-09-20 (`machine.PLAN_SPM` 650, `TRIM_COST_STITCHES` 120; the worksheet prints "Run time ~N min … incl. trims"). Playbook laws 36/38.
53. a ring inside a hole of its own shape (an ISLAND, carried in `holes`) was a second hole to the BROWSER builder — FIXED 2026-10-03 (`islandsAmong`, `digitize.js`). Nested rings whose areas summed to the outline's sewed NOTHING (a 40 mm box, rings 4 and 8 mm in); a preset's pull compensation SHRANK an island (terry: its fill 0.6 mm small a side, the underlay showing round it). An island now grows as the outline does, or is sewn as drawn where growing would bring it against the ring beside it or across itself; a ring thinner than one needle step (0.1 mm) is no island. **Exported stitches change for island shapes and no others**; neither lane the Studio builds through makes one (`groupRingsIntoShapes` and direct callers do). Older than `fillColumns`, the same with it off or on. Independently audited, four passes; what a thin moat costs is in the full text. `test/digitize.test.js`. Full text: scope-history 10-03.
56. a walk in the BROWSER's skeleton tracer never ended, and the satin emitter sewed what only its guard had stopped — FIXED 2026-10-03 (`circling` in `skeletonEdges`, `satin.js`). A 20 mm star off the shape tool sewed 48,645 stitches and a 24 mm one 128,239; a design took up to 12 s to build. Three skeleton pixels that all touch are no node, so a walk went round them for `w * h` steps. **Exported stitches change only where a walk reached the guard**: 4,038 of 145,600 swept stars, 329 of 4,095 bars, 273 of 612 image-lane designs; no fill moves (an independent re-measure on 34,000 designs of its own: none moved without one). **Its cost:** the knot had been covering small round shapes, and a 2 mm one now sews four stitches. What the sweep found standing is defect 57. `test/satin-walk.test.js`. Full text: scope-history 10-03.
41. the review screen quoted a sew-out's cost on one lane and nothing on the other — FIXED 2026-09-07 (`lib/estimate.js`, browser-side only when the service said nothing). Full text: scope-history 09-20.
42. five buyer-visible Studio-screen defects, all found by driving the app — ALL FIXED 2026-09-08 (#416/#417/#418). Full text: scope-history 09-20. Still the evidence for At-a-glance area 3's "driving, not reading" note.
54. a ring that says a point TWICE running (handed over CLOSED: its first point again at the end) got a WEDGE from the BROWSER builder's `offsetRing` — FIXED 2026-10-03 (`distinctCorners`, `digitize.js`: the corners said once are what `offsetRing` moves and what `isConvexRing` reads). The repeat is an edge of no length; its two ends were each moved along one neighbour's normal, the first by three times the distance. Under a preset the fill is sewn to the moved rings, so the wedge was sewn: a 40 mm box on terry was filled 1.8 mm outside the drawing at its first corner, where 0.6 is right; a closed hole and a closed island the same, and with `fillColumns` the edge run. **Exported stitches change for a ring that says a point twice, under a preset or with `fillColumns`, and for no other** (4,536 outputs on rings that do not: identical). **No Studio lane hands over an EXACT repeat**: none in 24,985 rings from basic shapes, the image lane and trace import, and a hand-drawn one is refused as crossing itself. `parseSVG` and `fonts.js` do hand them over, and nothing in the Studio calls either. **A NEAR repeat is another matter and was in the Studio's reach: defect 55 (its gesture cured, its offset open).** Older than every flag. Left: the auto angle, a satin shape's centre run, the edge run drawn toward the centroid and the order of a colour's shapes are read off the POINTS, so a closed ring's underlay still differs. Independently audited: the fix held, five sentences of its record did not and are corrected. `tools/closed-ring-census.mjs`, `test/digitize.test.js`. Full text: scope-history 10-03.
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

---

## Latent — gated OFF, DO NOT FLIP without rebuilding its instrument

Safe only because it ships off. **A green suite is not evidence** — on chaining
one concealed it; entry 2 is a flag that LEFT this list unnoticed for two weeks.

1. **`chain_links` — sews needle-down thread on bare fabric.** 16.15 mm exposed
   over 17 links, stock preset, green suite. Both shipped instruments were
   blind; the replacement then erred the other way and was fixed 2026-09-02
   (residual: a `-shadeN` id) — the numbers are in the pointers below.
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
| 3. Studio app / configurator | Implemented | Medium (fabric-preset accuracy: **pending sew-out** — the 2026-09-01 icon was uncontrolled, so the card still gates this). Held at Medium by that gate alone. **The wizard is gone (2026-09-30, PR #585)** — one panel, a summary bar, a Download sheet; spec `docs/superpowers/specs/2026-09-30-studio-configurator-design.md`, PR 3 (progressive disclosure) is what remains. **PR 4 (theme, branch `claude/configurator-theme`, landed before PR 3 by Kent's call): white page, one `--fill` neutral for controls, 13 px type, a 44 px top bar with an `EMB·BOT` wordmark, plain hovers no longer use accent or tint (at rest accent/tint stay on the CTA, selection, links, focus, the in-flow hint banner, the font-licence badge, the quality grade and the digitize/manual panels' control borders), type is 400/500 with 600 only on the summary bar's figures and the wordmark (base headings and `b`/`strong` are 500); every TEXT NODE in the top bar, the panel (empty and text-design states), the garment menu, the Download sheet and the My designs drawer is held to WCAG AA by a computed-colour spec, 0 failures across ~130 elements (it does not measure field values/placeholders, hover/focus states, the stage, the digitize/image/manual panels, tooltips or popovers), spec §6's sheet slide was not built, so the panel is restyled but still long** *(built and driven 2026-10-01 — `theme.css`, `theme-contrast.spec.js`)*. **PR 2 (#586): the garment tiles are a Polo/Hat/Tee pill row with a More › menu, and Studio gains an Original view that is registered on the stitches only for browser-traced art, NOT yet for the service's digitized lane (open: the service must return the art's content box)** *(built and driven 2026-09-30 — `GarmentPicker.spec.js`, `configurator-smoke.spec.js`)*. **Every display-layer defect this area has had came from DRIVING the app, none from reading it** — three sweeps, detail in the area doc and defect 42. The preview renders thread as a lit cylinder at physical width, eye-tuned not sew-verified; the customer can crop to the logo before the run *(2026-09-28)* |
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

0. **RESOLVED 2026-10-02 — Kent flipped `satin_crown_cover` ON** (scope-history 10-02). What follows is the question as it stood.
   **`satin_lettering_split`'s crowns, NEW 2026-09-30 and the freshest item
   here — RE-FRAMED the same day, downward.** MARINE at 127.4 mm reads 0
   holes as fill and 11 holes / 22.9 mm² as split satin. But `lost_frac`,
   the metric that killed the apex widening, reads **0.2688 fill against
   0.1800 split** — the split is a third better, because fill spills more
   thread outside the artwork than the split leaves bare. So this is NOT a
   case for reverting or gating the flip; it is a case for closing 11 crowns
   without spending that advantage. Neither built rail cure does it (the
   envelope is inert on them, `True` costs `lost_frac`), and the mechanism
   is a DECOMPOSITION gap — the strokes' union leaves wedges no stroke
   claims. The construction is designed and waits on you:
   `docs/superpowers/plans/2026-09-30-crown-cover.md` §7. Defect 50.

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
   The grep came back >0 on all twenty. Kent ruled 2026-09-13 to revive them,
   and `stripRunParamsIfSatin` now strips only glyphs that carry satin
   columns. The rebuild landed 2026-09-15. The other 6 (`western_light`,
   `ondulamarif_*`) have no authored run length upstream, and defaulting one
   is refused by `test/run-fonts.test.js:44`. This item read "still open"
   until 2026-10-02.
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

15. **RESOLVED 2026-09-12 — the wizard's steps are browser history entries** (`lib/stepHistory.js`). The anti-trap rule IS the design and survives here: **the first step REPLACES the entry the browser already has, only a step after it pushes**, so Back from step 1 still leaves the Studio. Not routing — no URL reaches `pushState`. *(`app/src/App.stepHistory.spec.js`, with a source guard against a bare `step = ...`)* **Superseded 2026-09-30:** there are no step entries; the Download sheet is the one history entry, and Back closes it.

17. **RESOLVED 2026-09-17 (Kent) — clearing a stale BORDER recovers on ONE click**, a stale BOUNDARY on two. Kept: "Clear them" is an explicit click, so nothing is dropped behind the user's back — what "recovery is explicit" protects. Do NOT gate recovery out of the fast lane to tidy this. *(`e2e/digitize-stale-edits.spec.js`)*

18. **OPEN: a COLD photo digitize is ~90 s and `fill_travel_under_cover` is ~58% of it.** The 2026-09-17 memo fixed the RE-stitch (79.3 → 44.6 s); the first digitize still pays the flag in full. Three ways out, all Kent's: flip it off (costs stitches, re-exposes the travel it hides), optimise `_reorder_for_cover` (golden-pinned — a win must be byte-identical), or accept it. **Do not re-derive the numbers** — method, noise floor, per-flag table and three INERT flags are in the doc. *(measured 2026-09-17 — `docs/flag-runtime-bills-2026-09-12.md`)*

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

16. **Manual mode does not reproduce auto's sew order once a tiny region exists
   in an early layer.** Auto orders blocks by PALETTE LAYER, manual by AREA.
   Surfaced 2026-09-13 by the `keep_thin_strokes` flip, which adds exactly
   such regions — **the flip exposed this, did not create it**. Untriaged:
   nobody has established which order is right, or whether editing in manual
   mode yields a different file from the one the review screen showed.
   *(found 2026-09-13 — `digitizer/tests/test_manual.py`)*

21. **`bean_letter_max_stroke_mm` at 1.0 — JUDGED 2026-10-03, stays OFF.**
   Small traced lettering sewn as bean runs along the skeleton of its SOURCE
   INK instead of satin blobs. On the labelled page Kent put today's satin
   ahead on five of six logos and called bridge both bad; his reason is the
   line's WEIGHT — *"little worms"*, *"aren't thick enough"*, *"to skinny"* —
   while granting fremont's path reads cleaner. Open, and his: a heavier line
   on the same path, or drop it. The render draws three passes as one thread,
   so "too thin" is not yet separated from the picture (`suspected`); gate 1
   holds a 3-pass bean on knit as `pending sew-out`.
   *(judged 2026-10-03 — `docs/eye-pairs-2026-10-03/kent-notes.json`)*
22. **Flip `fillColumns` on for the browser lanes — NEW 2026-10-03, built OFF.**
   Defect 52: a manual fill lays a float (or a stitch) across every cut-out
   on every row. To see it on a design of your own, turn on **Jumps** in the
   Studio's field (off by default). One sheet, off beside on, thread by
   thread: `docs/renders/fill-columns-2026-10-03/`. What to judge:
   the holes and the U's mouth go from solid red to clear, and cuts fall
   with them (0.89 a design → 0.25; a 36-hole badge 1 → 0); stitches rise 3%
   overall and up to 37%. The price is the travel that replaces the floats:
   up to nine lines of thread on the worst millimetre of a rim (three on
   average, 1.3 today), and in one holed fill in six more than 5 mm of it
   across rows already sewn. A comb can gain cuts (1 → 5). Besides: a forked
   large fill is no longer center-out, and on a shape with a hole or an
   inside corner the edge-run underlay sits 0.2 mm inside the fill with its
   corners kept (the one length named: it is what the shipped engine gives at
   the Studio's own 10 px per mm). **It has not been sewn.** The honest
   choices: flip now; flip for the manual lane only; or sew one holed badge
   first. No gate applies — it is routing — but it moves every browser-lane
   design that has a hole or a notch, so it is a flip and not a fix.
   *(built 2026-10-03 — `fill.js` `opts.columns`, `digitize.js` `fillColumns`)*
23. **Flip `ties` on for the browser lanes — NEW 2026-10-03, built OFF in
   both builders.** Every trim in a lettering or shape file exported from the
   Studio leaves two unlocked ends; the Python lane locks every one and always
   has. The 09-14 question was never queued here, and its lock was wrong: a
   leg of 0.8 pixels, 0.1 to 0.5 mm in practice. Now one rule for both
   builders, at 0.8 mm. Cost: lettering +3% (four letters) to +8% (a line of
   text) stitches; shapes about +1%, by how many pieces a design is in. No
   cut is added. **On shapes one lock in five lands on a stitch under 0.3 mm**
   (a fill's last row at a tip): five penetrations inside 0.3 mm. That is
   Python's rule too, and the audit's advice is to sew one first; lettering,
   under 1%, could flip alone. **Not sewn**, and neither are `machine.py`'s
   0.8 mm and three legs: a candidate for the sew-out card. A flip is
   `ties: true` at `generate.js`'s four call sites and a re-pin of every
   snapshot.
   *(measured 2026-10-03 — [`docs/lock-stitches-2026-10-03.md`](docs/lock-stitches-2026-10-03.md))*
24. **Flip `fillStagger` on for the browser shape lanes — NEW 2026-10-03,
   built OFF.** The shape builder cuts every fill row evenly from its own
   end, so the needle holes of one row stand under the holes of the row
   before: 94% of them, and 86% head three in a line, which is the line light
   runs down (quality review 09-08 §4). One sheet, the holes as dots, as
   shipped beside staggered: `docs/renders/fill-stagger-2026-10-03/`. The
   flag puts the holes on the Python fill's shifted grid instead; 6 holes in
   148,477 still head three in a line. Row for row it is the Python rule
   (51,760 rows in thread order, equal to the bit, after an audit failed the
   first proof). Cost: +7% stitches (+2% on a plain square, +12% on a design
   in small pieces) and stitches down to 1 mm where a row meets the edge
   (2 mm today). No cut, no float and no edge moves. **What it leaves: a
   line of dashes.** A first or last step over a stitch is halved, and the
   half lands by the next row's grid hole: a pair of holes every four rows,
   about 2 mm inside a straight edge, where today there is a solid line every
   4 mm across the fill. Python's fill does the same. **Not sewn from this
   lane**; the honest choices are flip now, or sew one square and look for
   the dashes. A flip is `fillStagger: true` at `generate.js`'s three shape
   call sites and a re-pin of every shape snapshot. Lettering has no fill to
   stagger as shipped: a wide letter's fill (`satinplay.js`) sews only under
   `wideColumnFill`, off since 09-11 (8,500 Studio lettering builds, no fill
   row), and takes the stagger in whatever change flips that.
   *(measured 2026-10-03 — [`docs/renders/fill-stagger-2026-10-03/`](docs/renders/fill-stagger-2026-10-03/README.md))*
25. **Flip `dedupeHoles` on for the browser shape lanes — NEW 2026-10-03,
   built OFF.** The shape builder rounds every point to the file's 0.1 mm,
   so two penetrations nearer than that become two stitch records on one
   point, and the writers keep the record: the needle twice in one hole.
   About two a design in what ships (16,575 on 8,255 designs), at corners,
   tips and the mouths of notches; a slot a hair wider than twice the pull
   compensation makes a line of them, 212 in one design. The flag lays the
   first and not the second, in every run. Each stream is the old one less
   those records: no stitch, cut or order moves. It is the Python stream's
   own rule with the file's grid in place of a length, so no gate applies.
   Machines differ on the record: Barudan, Ricoma, Brother, ZSK and Dahao
   delete it as shipped, Happy keeps it, and no filter was found for Tajima,
   whose manual says to correct the data. **Not sewn.** A flip is
   `dedupeHoles: true` at `generate.js`'s three shape call sites and a re-pin
   of every shape snapshot. Lettering has its own (9,093 on `KENT` across
   the fonts) and no flag yet.
   *(measured 2026-10-03 — [`docs/sub-unit-stitches-2026-10-03.md`](docs/sub-unit-stitches-2026-10-03.md))*
26. **Which cure for defect 57 first — NEW 2026-10-03, nothing built.** The
   browser's satin on a thin bar, a star or a drawn shape set to satin lays
   a stitch as long as the shape and sews strokes twice. Three cures, each
   its own change with its own before and after:
   - **The bar's end.** End the spine where the bar ends instead of in its
     corner, so the last crosses stay across it. The most ordinary shape (an
     underline) and the plainest picture (`standing-bar-30x3.png`). Whether
     it takes a number is not known until it is tried: the trim that exists
     is half the stroke's half-width, and the Python engine drops these
     corner forks by a rule of its own that could be ported.
   - **The star's tier.** Have the branch guard ask whether the whole rung
     stays inside the shape, not its midpoint. No new number. Not built or
     measured: it would send most of the 15,312 satin stars in the sweep to
     fill, trading stitches 20 mm long for fill rows under a millimetre on a
     needle arm, which nothing has sewn. It wants your eye on a render.
   - **One pixel, one edge.** Port the Python tracer's consumed set, so no
     pixel is laid twice and no ring is found in a shape with no hole. No
     new number; it would move most satin designs in all three browser lanes
     (1,407 of the 1,684 star rings have an edge that goes back over itself).
   A limit on how long a cross may be would cover the star and the bar at
   once and is NOT offered: it is a number, and gate 1's.
   *(measured 2026-10-03 — defect 57; [`docs/renders/star-walk-2026-10-03/`](docs/renders/star-walk-2026-10-03/README.md))*

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

### No CONTROLLED sew-out card has been sewn — one uncontrolled icon has

**Corrected 2026-09-14** — this read "Zero sew-out testing" while line 35
recorded the stitch-out, the file contradicting itself about the event phase 5
exits on. Its pointer was **2026-08-21**, eleven days earlier. *(gap audit §3)*

**True:** thread has met cloth once — Kent's icon, 2026-09-01, 6/10, 80.5 mm,
8 cones, 18,959 stitches, via the Python service. *(scope-history 09-01; memory
`first-physical-sewout-2026-09-01`)*

**What it does not settle:** random operator threading (never grade colour from
it), one fabric, one size, no controlled blocks. The CARD (`docs/sewout-card-2026-07-31.md`) is the instrument
and has not been sewn. **Gate 1 stands**; scores stay `pending sew-out`.

**Kent's 2026-08-21 ruling is unchanged by the icon:** accepted as-is, not a
queued action, not to be re-raised as the highest-leverage next action. One
question waits behind it, measured both ways — DOCTRINE,
"Raising `SATIN_MAX_WIDTH_MM`". *(ruling 08-21; sew-out 09-01; fixed 09-14)*

### Evaluation corpus & harness — real gap, newly tracked here

**The gap: no repeatable automated quality signal**; a labelled corpus plus a
scoring harness would let a classifier change be judged before a corpus or a
sew-out arrives.

**Seven measured cases where the harness disagrees with the sewn result — one of them since retracted:** [`docs/yardstick-disagreements-2026-09-06.md`](docs/yardstick-disagreements-2026-09-06.md) — phase 1's exit condition is a claim about disagreements and nothing was gathering them. Two are load-bearing: a 32.7 → 1.4 ΔE00 thread fix that moves no grade or block (the metric moves; the verdict does not), and four photo fixtures that score HIGHER with a ratified quality tier off. Append; do not curate — **row 7 is kept, marked: the retraction is the finding** (measured with the `~base_valid` bug in the tree; the fix reversed its direction, 2026-09-07). *(assembled 2026-09-06)*

**Phase 1's exit condition has TWO instruments: `digitizer/tools/eye_pairs` (its second clause — Kent's picks on same-design A/B pairs; built 2026-09-17, PR #506; no blind sitting — labelled sittings instead: 09-18 and 09-28, all 77 pairs judged (today beats the 08-27 engine 7 of 9, `satin_rail_comp` the only flag leaning better, four logos bad under every setting — `docs/kent-review-2026-09-28.md`); 2026-09-30 the envelope (2 after, 0 before, flipped ON) and, that evening, the day's three lettering changes before | after with a needle-hole map beside every render: 4 no difference, 3 both bad, 1 before on a confounded pair (the ref worktree had no photo-prep venv; fixed in the yardstick), and the dissolve stays OFF on 2 before, 1 after; then, late, the lettering texture sitting: the pro's 7 mm split style read no different from the comb on every judged pair and the symmetric rails lost golden_tee, so both stay as shipped; screenshot ruled off the page; **2026-10-01 the pro's own Becker file beside ours: the pro's flows, and Kent's word is the back stitching — `tools/underlay_cover.py` (one rule on both files' stitches) finds the stems' support already equal (20.7% of the top thread on thread, both) and the difference in the comb: every MARINE stem is 5.5-6.9 mm, over the 5.0 split, 1,413 holes inside the stems against the pro's 304 (246 with the split off), so `split_off` is the next arm; the arch letters' fill is the 146-px source's, not the engine's** (`docs/eye-pairs-2026-09-30/`)) and `digitizer/tools/artfid_eye_rank.py`,** a blind rank harness correlating ARTFID's ordering with a viewer's. First run: the pre-registered primary is **null and underpowered by construction** (tau-b +0.048, n=7 after refusals). The load-bearing result sits behind it — **ARTFID scores are NOT comparable across routes**, and "preflight grade beats ARTFID" is a confound for `route == flat`. Do not pool ARTFID over mixed routes and read the ordering as quality. Also live: `colour` reads exactly 1.000 on 11 of 14 fixtures while carrying 25% of the composite. Full result and two disproved hypotheses: DOCTRINE "ARTFID is not comparable ACROSS routes". *(measured 2026-09-11 — [`docs/artfid-eye-agreement-2026-09-11.md`](docs/artfid-eye-agreement-2026-09-11.md))*

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
*(2026-08-21; 2026-09-02 — [notes](docs/scorecard-baseline-attribution-2026-09-02.md); 2026-10-04 — [notes](docs/scorecard-baseline-attribution-2026-10-04.md))*

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
lines. **46 closed 2026-10-03** (row 17, as preflight metrics); **47 is still
open** and still desk-safe.
*(audited 2026-09-20 — code read, `origin/main` 1ac731cd; 46 built 2026-10-03)*

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
#241/#243/#245; scope-history 08-25 evening)* **Gradient lane, 2026-09-04 (Kent's ruling): a design whose ramp fits is ONE sweep.** `design_ramp.py` (trimmed + consensus plane gate: r² ≥ 0.4, ≥ 60% riding, sigma ≤ 4; colour as a profile along the sweep) flattens stage 2's merge and gives stage 6 one shade scheme per design, and a riding region never takes the satin rung: the icon repro at 80 mm goes 10 → 8 regions and its three ramp pieces decompose into five shades along the diagonal where they sewed flat or as one-thread satin; drone/summit/blobs/owl are refused and untouched (angle included). Two tier defects fixed on the way: blend bands had sewn at n× the row since the tier's first commit (a quarter of a fill; #339's preflight exemption for it withdrawn), and `_band_clip` shifted a linear ramp's bands by the region's own centre — the committed engine never sewed **46%** of `gradient_ramp_linear` at 80 mm, suite green. **Blend regions sew stage 5's compensated outline since 2026-09-04 (Kent's pick):** stage 7 had handed `blend_fill` the ARTWORK polygon, so every region of a gradient-class design — bands and tatami fallback alike — sewed with no pull comp and no seam tongue while `tools/seam_underlap.py`, which reads the plan, showed the tongue present; `tools/sewn_compensation.py` reads the stitches: repro strips 29% → 100% covered, blobs 36% → 100%; repro 22,087 stitches, 26 trims. **The machine's cone list is on the wire since 2026-09-04** (`stats.blocks`, one per sewn block with the review shapes it sews): the download's thread list always read `design.colors` and was right; the Sequencer header, its rows and the quality report's metres now read the blocks too, and `reviewFromJob` no longer indexes the per-layer palette by `sew_block`. **The satin raster ate every counter's edge until 2026-09-04:** `fillPoly` paints boundary pixels, so a hole painted in 0 lost half a pixel of material all round while the exterior gained one; the medial axis moved outward and the hole-side rail (the NEARER hit) stopped 0.18 mm short of the compensated outline on the repro's frame and ring while the exterior rail sat within 0.006 mm. Holes are painted half a pixel smaller in both rasterisers (`shapefield.hole_px`; `_rasterize` and `rasterize_polygon` are twins by test — the boundary-redraw form closed small counters and was measured out): frame strip 57 → 66% covered, ring 47 → 59%, against the instrument's ~80% ceiling for a perfect satin; the rest is the smoothed width profile at corners, which `rails_follow_edge` (sew-out gated) recovers. Hole-free shapes byte-identical. **Band seams feathered the same night (Kent's call on the render):** a 1.5 mm zone per seam sewn by both shades on one row lattice, alternating row by row, where rows run along the seam; repro 22 trims, 20,820 stitches. **Radial sweeps ride too (2026-09-04):** `design_ramp.py` fits a radial model (Gauss-Newton centre from the centroid, trimmed-then-consensus line in radius, colour profile along radius) gated at r² ≥ 0.6, ≥ 15 of 17 radius knots at consensus and the centre inside the stitched foreground, winning only when it beats the plane; `gradient_ramp_radial` at 80 mm 2 → **1** region, 5 shades (its 4,069 mm² outer ring had sewn flat), summit refused on knots, the owl on r², the linear fixture and the repro on the centre; linear designs byte-identical; a non-riding region on a radial design sews level. Ring seams keep the hard seam + underlap (rows cross rings; a stitch-level dither is a later item). **The blend tier takes the density stage 7 resolved since 2026-09-04** — it read `machine.FILL_ROW_MM` directly, so neither a per-job `fill_row_mm` nor a fabric's `density_adjust` reached a gradient: on a towel (0.85, pile needs TIGHTER rows) every band sewed 0.150 against the design's own 0.128, the repro 23,375 → 26,561 stitches. Invisible on the corpus scorecard, whose two garments both sit at 1.0. **The `-blend` suffix made four instruments blind until 2026-09-04** — preflight's bare-fabric check examined 0.0 mm² of a one-region sweep and a fifth of the repro (1,091 of 5,729.5 mm²), its thread match scored five cones as one, and the service filed a gradient's sew order and block ids under names no review shape has; `preflight._owning_region_id` is the one rule (a prefix test is not a substitute — region ids are not prefix-free). A fifth defect fell out of the same reading and is not an id bug NOR gradient-only: every region filled into ONE shared mask, so a ring's hole erased the artwork a nested region claims — the repro's shared mask claimed 136,341 px where the union claims 802,474, and the flat `logo_bridge_bar` (77 regions, no derived ids) rises 551.0 → 1,381.2 mm² examined. Scores fall where they were false: repro A 100 → D 58 on a band wearing a cone 13 ΔE off. Satin as SEWN is measurable since 2026-09-04** (`tools/satin_columns.py`, calibrated on two committed professional files in CI): a cross is sign alternation about the chord, not a turn angle, because a fixed angle gate is blind to columns under ~0.69 mm. Pro Becker **44.3%** of penetrations in columns at a 2.52 mm median; ours on the same logo **2.2%** of penetrations — the biggest measured gap to a professional file. **The width half of that line was contaminated and is corrected (2026-09-06):** "0.29 mm, 84% of columns under 0.7" is the WHOLE-PLAN row, 80% of it tatami turns; our SATIN runs there measure **3.82 mm median, p90 4.93, 23% under 1.0** against the pro's 2.52 / 5.00 / 7%. Read our widths off `satin_columns.py`'s second row (DOCTRINE 09-06). The share gap is real; the width gap was not (plan: `docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`). **No physical tests until Kent says — the render is the judge.** *(measured 2026-09-04 — scope-history; DOCTRINE)*
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

**Per-shape stitch width (2026-09-29, `digitizer_core/stitchwidth.py`).** Every column reports its width and word; review override `stitch_width_mm` (contract v1.8) offsets the polygon, counters held. **Evening a word out is OPT-IN (`stitch_width_auto`):** Gaulke's 35 letters run 0.77 → 1.33 mm as a smooth chain, so a median is nobody's width. Off, byte-identical; floor None (gate 1). *(measured 2026-09-29 — `tests/test_stitch_width.py`; COOKBOOK "Per-shape stitch width")*

**A tapered tip is a CAP, not a junction — `cfg.satin_tip_caps`, ON since 2026-09-30 (Kent).** Under `satin_rail_comp` the artwork's sharp tips stay sharp, so a tip one stroke ran through on the grown polygon becomes a node where two arms END: `_extend_to_cap` never runs and the junction trim pulls both back. ENTHUSIAST's A stopped **1.63 mm** short of its apex against 0.08 mm off the rails. Kent's construction — both arms cap and overlap — needed no new discriminator, only the gate to stop EXCLUDING arms that tuck under each other (`_corner_forks` names a partner both ways there). Bare artwork and end bare fall on **all nine** corpus logos (becker 182.07 → 160.69 mm², screenshot's worst component 1.94 → 0.91) for **+4.2%** stitches. **It does NOT close defect 49** — ENTHUSIAST's apex is unchanged at 3.61 mm², because both its arms tuck under each other and the gate never reaches them; the widened construction that does close it was RETRACTED the same day on `lost_frac`. Three discriminators were measured and refuted first, and an area test cannot separate a tip from a corner — DOCTRINE. **The corpus figures above are `bare_anatomy`'s satin-only reading, an upper bound on cloth a customer sees by a per-fixture 1.1–39x** (DOCTRINE 09-30); the flip's direction is unaffected, its magnitudes overstate. *(measured 2026-09-30 — `tools/bare_anatomy.py --corpus`; `tests/test_satin_tip_caps.py`)*

**Next:** NEEDS KENT. Fragmentation work measures **0% on real client logos**
(they are satin-dominated, 1–3 fill shapes, no cutting fills). The one large
real-artwork lever is **`chain_links`: −33% trims AND fewer stitches**, gate-1
frozen; every gate-clear alternative measures ≤9%. *(measured 2026-08-22)*

**Quality review 2026-09-08 — fourteen ranked changes, three cheap JS-lane defects, and Kent's picks:** [`docs/quality-review-2026-09-08.md`](docs/quality-review-2026-09-08.md). **Lettering construction (Kent's route ruling 2026-09-19, plan `2026-09-19-lettering-construction.md`): step 0 BUILT and FLIPPED ON the same day (Kent) — `satin_house_from_line`**, the house angle's third reading for a word both votes refuse (ENTHUSIAST: cross concentration 0.059 → 0.287); the vote was found size-unstable and diagonal-pulled. **Step 1 ON (Kent) — `satin_house_anchor`**: house = line + stems' slant; drone's self-crossings 496 → 430. **Step 2 ON (Kent) — `satin_stroke_order="euler"`**: one walk per shape; nine logos 592 → 486 trims at −19 stitches. **Step 3a ON (Kent) — `satin_corner_twigs`**: corner twigs kept; nine logos' self-crossings 1,813 → 1,004, Becker's band +725 stitches at 100 mm; 3b `satin_rail_comp`: Fremont IoU 0.68 → 0.84, artwork skeleton ruled, **ON since 2026-09-28** (Kent's flip on the labelled sitting, sew-out still owed — `docs/kent-review-2026-09-28.md`). **Step 4 BUILT OFF — `satin_lettering_split`**: no width ceiling for a text-cluster member; MARINE at 127 mm fill 6 → satin 6 at 9,642 → 7,753 stitches — but all 311 new self-crossings sit in the R's junction ball; ON (Kent) after the stack. **The junction construction is DESIGNED before code** (`docs/superpowers/plans/2026-09-19-junction-construction.md`): the 311 are ONE weld folding through 44°; refusing the 30–60° welds reads 311 → 0. **BUILT as `satin_junction_stack`, OFF (Kent: A + B + C)**: the R 311 → 0 at +10 trims, MARINE 80 103 → 0 at +2, Becker's band uncovered 35.5 → 0.0; ON (Kent). **Step 5 BUILT OFF — `edge_cap_skip_lettering`**: fixture trims 23 → 7, stitches 2,192 → 1,774; ON (Kent). **Trims gap: exit lever ON (Kent), underlay OFF;** fixture 13 → 9. *(2026-09-19)* **Refused walks are mostly not a defect (2026-09-20):** 262 of 343 are a web that does not reach; the relaxable 47 are the needle's distance — `satin_walk_cursor_reach_mm` OFF pending a sew-out (Kent), 491 → 471 trims at +65 mm exposed, worst leg 3.3 mm. *(scope-history)* **The Studio never sent the file (fixed 2026-09-20, Kent):** a 1,200-px canvas re-encode reached the engine — alpha rewritten (Becker 59 → 175 trims), low smoothing (tires 6 → 14); the panel sends the upload, the `.embproj` carries it. **`alpha_edge_extend` ON (Kent), gated on the upscale:** Becker reads 54 trims whatever its alpha hides; nothing else moves. *(measured 2026-09-20 — scope-history, DOCTRINE)* **Item 3's upscaled regime is ON (2026-09-18, Kent, `cfg.subpixel_edges_upscaled`):** low-res sources read their own pixels (ladder Hausdorff 0.26 → 0.03 mm); Becker's 100 mm band then flips fill → satin, the decomposition follow-up. *(scope-history)* **Item 1's PR 5 is MEASURED (2026-09-11, gate-2 clean — it changes nothing): `tools/color_diversity.py` re-reads the 08-15 spec's candidate signal** (3-bit colours covering 90% of foreground) on today's corpus. Two findings. **(a) The foreground definition is load-bearing and was never written down**: the art bbox reproduces the spec's table and separates the classes by 4; counting only what stage 1 digitizes puts `bridge` at 39 above `drone`'s 24, which does not order at all. Quote the bbox reading. **(b) The two real flat logos enrolled since August WIDENED the gap** (2 → 4: `golden_tee` 4, the screenshot 1, both far below `drone`). **The blocker is unchanged: one real tonal artwork labelled** where the spec asks four — the acceptance directory is empty in any clone and the tool refuses a boundary below four. One drag and one command unblocks it (`docs/stage0-signal-decision-2026-09-11.md`). PR 6a (the signal) is supported, not authorised; PR 6b (route by the ramp gate's refusal) needs no boundary and is Kent's ruling. *(measured 2026-09-11 — `tests/test_color_diversity.py`, 18)* Three measurements the ranking rests on: the curve gate reaches **2 of 29** fixtures; MARINE sews tatami at 100 mm, refused by the width cap, not by irregularity; the pro's sewn Becker files carry **7–23%** of satin crosses over the 5.0 mm cap. The browser engine locks no cut as shipped: `ties` is built OFF in both JS builders (lettering 2026-09-14, shapes 2026-10-03; "Waiting on Kent" 23). Its shape fills line their needle holes up from row to row: `fillStagger` is built OFF (2026-10-03; "Waiting on Kent" 24). **The thin-stroke plan's instruments are BUILT** (`digitizer/tools/thin_strokes.py`, `legibility.py`; the width test corrected to the 90th percentile 2026-09-08 after its median admitted Fremont's white ground as a 1,758 mm stroke — the per-band and per-component figures here never depended on it): the two lanes lose DIFFERENT width bands — Fremont routed sews strokes under 0.5 mm at **53%** recall and 0.5–1.0 mm at 90%; forced flat, 26% and **51%** — and `logo_gaulke_roofing` loses **16 of 18** thin strokes on BOTH lanes with lettering legibility **0.32**, because its black frame makes stage 1's background black and every black element inside the card "enclosed background", unstitched by default. **`cfg.keep_thin_strokes` is BUILT on both lanes and **DEFAULT ON since 2026-09-13** (Kent's ruling on `docs/thin-strokes-flip-2026-09-13.md`: *"Flip it — take gaulke and becker as the price"*; False is the pre-flip engine and stays tested)** (PR #426 the flat absorb-by-colour rule, PR #427 the gradient lane's thin population): Fremont forced flat 135 → **3** lost thin strokes (recall 61.2% → 92.7%) for 33 → 165 regions and 71 → 81 trims; Fremont ROUTED 18 → **3** lost (85.2% → 92.5%) at **MORE** stitches and FEWER trims — 18,316 → 19,881 and 103 → 76, re-measured 2026-09-13 on `8a94bfe` (`docs/thin-strokes-flip-2026-09-13.md`). **The "fewer stitches" half of this line was true on 2026-09-08's engine and is false on this one**: the cause is `cfg.subpixel_edges` alone, flipped ON 09-09 — with it off today Fremont reads 18,337 → 16,974 and the saving returns, and putting all seven post-09-08 defaults back reproduces the old pair within 0.4%. Sub-pixel vertices grow polygons 45–155%, and ON there are 110 more regions to grow; drone routed 29 → 2 lost (51% → 96%) for 59 more trims. Photo classes are gated out. Flipping it is Kent's. **`cfg.lettering_min_column_mm` is BUILT with its tier rule, DEFAULT OFF (None)**: the floor widens a rescued glyph's polygon, and (2026-09-09, the PR after #428) stage 7 sews that widened population on its compensated polygon instead of routing it to the run tier on its area, while stage 5 lets it grow over the ground it was vectorized as a hole in (without that, every widened Fremont glyph was clipped back to a 0.28 mm hole and the first measurement read as a negative) and plans the layers around it against its sewn column, so a ground whose thread sews after the lettering no longer buries 79% of it. Fremont ON: 8 of 10 widened glyphs sew **169 satin columns at a 0.91 mm median** (the pro's file: 0.82–0.90), routed legibility 0.551 → 0.577, stitches 16,006 → 15,823 — but the crops (`docs/renders/column-tier-2026-09-09/`) show the 1.0 mm column filling counters at a 2.2 mm cap height; ENTHUSIAST's 1.6 mm subline SMEARS (columns p10 0.16 mm, legibility **1.00 → 0.72**) — a glyph-height gate is the open question before the flag can ship on, Kent's call. **Item 5, PR 2 (2026-09-09): the serif column was NOT built — `digitizer/tools/letterforms.py` read every column end and found no serif in the artwork's feet (146 × 91 px source) and MARINE's 251 "self-crossing pairs" to be 0 within any column and 359 between columns at two Goldman joins, which the pro's own sewn MARINE has 2,593 of (DOCTRINE 09-09). The junction cover half shipped: **`cfg.satin_patch_junctions = "satin"`, DEFAULT OFF** — the grader's patches as satin columns FIRST in the shape under the arms, Becker 80 mm `ARTWORK_UNCOVERED` 9.0 → 0.0, B 76 → B 88 at +122 stitches / +2 trims (the tatami: +297 / +3); Fremont's band under `wide_columns` 128.2 → 13.0 mm² for +10.6%; the over-fire at Becker 100 mm (0.0 both ways, `TRIM_HEAVY` on +2 trims) is the tatami's too. *(measured 2026-09-09 — scope-history's item 5 PR 2 entry; `tests/test_junction_patch_flag.py`)* **Item 5, PR 3 measured out the same day** (`digitizer/tools/junction_blobs.py`, `pro_layers.py`): a 17 mm bold letter is 45–90% junction ball, and the pro's own file stacks MORE layers at every MARINE junction than we do (p95 3.7–7.3 vs 1.8–3.8; +58% thread in the word) — no blob column, no arms-only width statistic. *(measured 2026-09-09 — scope-history's item 5 PR 3 entry)* **Item 6 is BUILT as `cfg.satin_rail_comp`, DEFAULT ON since 2026-09-28** (built OFF 2026-09-09; flipped by Kent on the labelled sitting — after-better on five logos, before-better on none — `docs/kent-review-2026-09-28.md`; the sew-out is still owed; **the flip's price ACCEPTED by Kent 2026-09-29, MARINE's trims a ceiling in `tests/test_rail_comp.py`; the hairline seams of stage 5's on-rails polygon are closed for the whole satin column — skeleton since 2026-09-29, rails, caps and underlay since 2026-09-30 (PR #565); the price, the trim fixes and the seam numbers: [`docs/scope/1-auto-digitizing-quality.md`](docs/scope/1-auto-digitizing-quality.md#rail-comp-the-flips-price-and-the-seams-2026-09-2930); **the far rail's under-reach is cured by `satin_rails_follow_edge="envelope"`, built 2026-09-30 and ON the same night on Kent's eye (2 after / 0 before)**: a rail extends only where its side is short by 0.3 mm, to the running minimum of its own edge over ±3 stations — golden_tee bare 10.35 → 7.20%, Becker 100 8.14 → 7.35, ENTHUSIAST a no-op (`docs/renders/rail-envelope-2026-09-30/`, `docs/eye-pairs-2026-09-30/`); `True` stays parked, the sew-out still owed. **Becker's void-filling texture was the envelope reaching through junctions (fixed 2026-09-30):** at a junction the far ray runs along the meeting arm, so 313 of 459 reached stations over nine logos landed on satin a sibling stroke already sews (78% of the envelope's new thread on Becker's letters); `_in_sibling_ribbon` refuses a reach whose end lies in a sibling's corridor — 23 escapes left, Becker 100 9,563 → 8,932 stitches, the reach kept (Becker 80 bare 9.484 → 9.550%), golden_tee's keylines untouched; the short genuine reaches read as teeth (`docs/renders/envelope-escapes-2026-09-30/`) — **dropped the same day: a reach shorter than the envelope's window is not a reach (`_drop_short_reaches`, no new constant; Becker's 8 single-station teeth gone for 7% of the extension area, reached-station jitter 28.4 → 26.3%, the rest the long reaches' own steps, `docs/renders/envelope-teeth-2026-09-30/`)**; **the letters' split satin no longer flickers (2026-09-30): the split comb is decided per column — hysteresis on `SPLIT_SATIN_ABOVE_MM` with `SPLIT_SEGMENT_MM` as its floor, `_comb_thresholds` — Becker 100 122 → 37 on/off changes at +4.5% stitches, tires 21 → 5, bridge 20 → 5, no leg longer than the threshold; the pro's own Becker files comb nothing (raw to ~7 mm, 1–2% split under 5.5), a house style whose threshold is a sew-out question (`docs/renders/split-comb-2026-09-30/`)**): a satin-tier shape keeps its artwork polygon and each rail is pushed out along its cross by the fabric's pull (the amount untouched, gate 1; caps end at the artwork; a counter guard at `min_detail_mm`). Thread-vs-target IoU ENTHUSIAST 0.876 → **0.897**, drone 0.797 → **0.838**, Fremont 0.675 → **0.836**, Becker 0.887 → 0.884; trims 26 → 22 / 96 → 83 / 46 → 45 / 36 → 40; coverage peaks down on three; thread sewn outside the artwork 147–322 mm² → 0. The grown-polygon skeleton with artwork rails (one line away) takes most of it (drone 0.829, Fremont 0.813) and keeps Becker's decomposition (34 trims, 3 strokes on the A for the artwork's 7) — the artwork skeleton RULED 2026-09-19 (Kent). The build found `_skeleton_edges` stranding chains at junction cliques and L-corner fillers (fixed ON BY DEFAULT; OFF moves drone `S60de6f78` 43 → 45 stitches and ENTHUSIAST's house angle by 0.03°). *(measured 2026-09-09 — scope-history's item 6 entry; `tests/test_rail_comp.py`, `tests/test_skeleton_tracer.py`)* **Item 7 is BUILT as `cfg.design_angle`, DEFAULT OFF (2026-09-09)**: one stitch direction for the design's shapes without a house of their own — the lettering house where its lines agree, else the fewest-columns row direction summed over the fills — read by stage 7 before the per-shape derivation, by satin before the per-stroke tangent (so non-lettering satin gets the lean rule) and by stage 5's comp axis. The pro's three sewn Becker files hold ONE fill angle at every size (20.5° slab, 13–14° small fills), so no per-shape override was built. Becker at the pro's 95.7 mm: spread 0.15 → **0.999**, chance-corrected `direction` **0.0 → 0.289** (raw 0.43 → 0.64), stitches +4.2%, trims 27 → 22; at 76.5 / 101.9 mm `direction` 0.388 → 0.41 / 0.0 → 0.249 at −1.5% / +6.3% stitches. Forced flat, Bridge Bar's 15 fills 0.781 → 1.0 at −2.6%, gaulke +7.5%. The last ~20° to the pro's angle is a house-style number no objective derives — Kent's. Byte-identical off on ten fixtures. *(measured 2026-09-09 — scope-history's item 7 entry; `tests/test_design_angle.py`, 7)* **Item 8 RULED 2026-09-10 (Kent): the four colour flags not already ruled ship ON as ONE set** (`enforce_color_cap`, `resnap_mask_matches_grader`, `revalidate_small_shapes`, `bind_resnap_all_classes`; `dissolve_phantom_blends` stays banked), and **`cfg.robust_region_colour` is ON since the same day** — a SLIC+RAG region hands the palette the modal mean of its Lab pixels, not the mean, after Bridge Bar's disc bound to a spool 7.0 ΔE00 off the artwork. False on each is the pre-flip engine. The 26-fixture flip sheet, the per-budget cone/stop tables and the accepted prices: [area 1](docs/scope/1-auto-digitizing-quality.md), "Item 8's colour bundle". *(measured 2026-09-10 — `tools/flip_sheet.py`; `tests/test_robust_region_colour.py`)* **Item 9 is BUILT as `cfg.enclosed_by_garment`, DEFAULT ON since 2026-09-10 (built OFF that morning, flipped the same day on Kent's ruling over the renders; False is the pre-flip engine; the threshold stays 10 and alpha holes stay with the review toggle, his other two rulings)**: an enclosed background-coloured region whose colour is KNOWN (a border-flood hole, `Prep.bg_rgb`; never an alpha hole) sews by default when the garment the Studio names (`cfg.garment_rgb`, from `project.fabricRgb`) is more than `enclosed_by_garment_de00` = 10 ΔE00 (`DELTA_E_CLEARLY_DIFFERENT`, pinned) from it — one verdict per design, read by the stitched seam and by the colour cap's ranking so a hole that will sew keeps its cone; a review override still wins. At 12 / 80 mm: whitebg and Golden Tee sew their white holes white on Navy and Black (+571 st / 1 cone; +3,027 st / +7 tr / 1 cone) and are byte-identical on White and Natural (6.4 ΔE00 from Natural); gaulke's 46 black bodies sew on any light garment for +3,979 stitches and **+43 trims**, as the fragments the vectorizer kept when they were holes (STEEL ROOFING & SUPPLY reads, GAULKE INDUSTRIES does not — `keep_thin_strokes` is the other half of that lettering). At the Studio's 6 a sewing hole's cone takes a slot from the artwork on a logo already at six: Golden Tee's `1312` Burnt Orange edge merges into Black (35 ΔE00) on Navy — the slider's price, named by `COLOR_CAP_APPLIED`. And gaulke's white ground turns its fill rows from 0° to 45° when its bodies sew — `best_fill_angle_deg`'s fewest-columns argmin on the polygon the ground is now sewn as, not anything this flag does; `cfg.design_angle` (item 7) is the control that would hold it. The threshold, the alpha holes and the flip are Kent's (plan §5). *(measured 2026-09-10 — `docs/renders/enclosed-by-garment-2026-09-10/`; `tests/test_enclosed_by_garment.py`, 12)* **Item 11 is BUILT in three parts (2026-09-10; Kent's pick "Item 11 and 1"): (1) `THREAD_MATCH_POOR` has the sibling patch floor, `_THREAD_MATCH_MIN_PATCH_MM2` = 5.0 mm² (= `_UNCOVERED_MIN_PATCH_MM2`), ON — a graded patch under it cannot judge a thread, sub-floor offenders ride flagged in `regions`; over the scorecard matrix (52 pairs at 80 mm / 12, `tools/thread_match_floor.py`) 40 blocking findings → **26**, gaulke D 46 → **B 76** on both garments (its one block rode a 0.21 mm² patch), drone raw −140 → −80, the screenshot −116 → −38, Golden Tee −92/−104 → −50/−62, Bridge Bar unmoved (its shards judge on 9.5–9.8 mm²), no design leaves the 0 floor; (2) the un-clamped score is READ, not just carried — `raw_score` on the flip sheet's rows and verdicts and on the scorecard's score line, the baseline recaptured 2026-09-10 at `9f3d09c`: 46 of 52 pairs had moved since the 2026-09-04 capture, every mover attributed in the recapture commit — this PR's floor on drone, gaulke, Golden Tee and the screenshot (exact, from the sweep), the flips since 09-04 for the rest, and two grade drops bisected on main's first-parent history to #432 (grass_macro B 76 → D 52, the subpixel flip) and #433 (Becker at hat_front B 88 → 76, junction clustering; left_chest unmoved) and left flagged for a follow-up, not this PR's; on this engine **10 of 52 pairs sit on the clamped 0 with raw −140 .. −26** (2026-09-06: 12, −272 .. −38); (3) **`cfg.legibility_check` is BUILT and DEFAULT ON since 2026-09-10** (built OFF in #449, flipped in the PR after on Kent's ruling A over the OCR crops; False is the pre-flip report byte for byte): `LETTERING_ILLEGIBLE`, preflight reading what the thread SAYS per text cluster (`digitizer_core/legibility.py`, the 09-08 instrument moved into the package, `tools/legibility.py` a CLI over it; `ART_MIN_LETTERS` = 3, unsewn clusters left to the unsewn warnings, ~3.5 s per cluster), `LEGIBILITY_WARN` = 0.5 / `LEGIBILITY_BLOCK` = 0.0 — a warn, never a block, RULED — because the OCR crops show the similarity trustworthy at its ends and noisy between (DRONE 0.22 reads with its E lost, SPOTIFY 0.50 is blobs, HOTEL FREMONT 0.74 is clean): a warn under 0.5 catches every row Kent named (Bridge Bar 0.13, DRONE, the screenshot's 3 mm rows) and is silent on every row that reads. Kent ruled all three the same day (plan §6): option A, ON, and the gradient lane stays on raw distance (row 4 closes). **On the corpus the flip adds the warn to 7 of 52 pairs** — Bridge Bar both garments (0.13), the screenshot both (worst 0.00), summit_badge both (worst 0.00 — "Text on the bottom was dropped out", Kent 08-27) and drone at left_chest (0.36) but NOT at hat_front (0.55: the cap's density changes the RENDER the check reads) — and only Bridge Bar's clamped score moves (16 → 4, 4 → 0); the rest are on the 0 floor and move in `raw_score` alone, which is row 6's mechanism made visible. gaulke reads 0.21–0.29 and does NOT warn (its clusters are unsewn enclosed holes — the `sewn` rule), Becker and Golden Tee have no readable art truth, Fremont at 80 mm reads 0.96–1.00. The two accepted costs: it never blocks, and SPOTIFY at exactly 0.50 is missed. *(measured 2026-09-10 — `docs/superpowers/plans/2026-09-10-legibility-yardstick.md` §4; `docs/renders/legibility-2026-09-10/`; `tests/test_legibility_check.py` (7); `tests/test_thread_match_area_in_message.py`)* OCR on the render is a LOWER bound on loss: Fremont's THE reads 1.00 at confidence 95 on a render that shows T H C, while the thin-stroke instrument reads the E at 74% recall. **The sub-pixel plan's ladder is BUILT too** (`digitizer/tools/edge_truth_ladder.py`, 200–3200 px): below ~15 px/mm the deviation is the pixel and falls with resolution; above it the floor is the **0.2 mm simplification tolerance** and does not fall, so the plan's acceptance criterion was restated before any engine code. **PRs 2–4 of that plan are BUILT and `cfg.subpixel_edges` is DEFAULT ON (Kent's flip 2026-09-09; False is the pre-flip polygon byte for byte)** — stage 4's vertices move onto the anti-alias edge by area conservation (circle vertex spread 0.049 → 0.013 mm at 400 px; the rectangles' Hausdorff 0.12–0.18 → 0.01–0.02), which makes the polygon inscribed, so its boundary offset now reads the simplifier's chord sag until PR 3 keys the refinement to acceptance; sources stage 1 upscaled were declined until item 3's regime. **PR 3 is BUILT the same day** — the refinement keyed to that acceptance (0.25 px floor on accepted chords, the 20 px/mm gate lifted ON): the circle's boundary spread 0.057/0.047/0.035/0.023 → **0.036/0.025/0.024/0.022 mm** at 400–3200 px, the ring's 0.085 → 0.050 at 400; the §5 flip criterion (every rung ≤ OFF's 3200) is met on the circle at 3200 and bounded elsewhere by the 15° turn rule's own sag (0.06 mm on the ring's 7 mm hole). The per-shape tier diff ON flips three drone ribbons and grows vertices 45–155% on real logos (Fremont 1,501 → 2,170; trims 42 → 46). **PR 4 FLIPPED it (2026-09-09, Kent's approval)**: goldens re-captured on ubuntu-latest with the pre-change proof (whitebg 4558 → 4550, alpha 4534 → 4576, ribbon 999 → 991; enthusiast refused, the platform red), and the flip found three mechanisms balanced on a pixel — stage 6's `medial_axis` pinhole diamond (becker's worst bare patch **23.8 → 8.2 mm²**, enthusiast 150's 8.8 → 4.5), the taper zone's crowding (crowded same-rail steps **826 → 459** across the corpus at −0.18% stitches), a fault-injection fixture — each fixed where it lives, never in the polygon (DOCTRINE 2026-09-09). `curve_turn_deg` 15° and the upscaled decline are carried as Kent's. **Item 5's first PR is BUILT (2026-09-09): stage 6 clusters split junctions** — stubs under 0.5 half-widths and the loops inside them, the number read off `tools/junction_nodes.py`'s corpus histogram — so a crossing decomposes into its two bars at every scale; interior over-wide rail readings **948 → 830** across 14 fixtures at +0.21% stitches, Becker's bare total 16.0 → 9.0 mm², enthusiast 150's worst 4.5 → 1.2, no golden moved (the flat-lane keys have no branch node); the K's crotch (7.8 → 9.0) stays the junction cover's problem, PR 2. **Item 4 is BUILT as `cfg.wide_columns`, DEFAULT OFF (2026-09-09)**: a 6.5 mm ceiling read off the pro's sewn MARINE (p99 6.2) threaded as one number from classifier to emitter, with the bend's radius of curvature as the overlap guard (load-bearing on Becker at 80 mm before the corner rule, 7.07 → 5.08; under it the fold is gone, 4.67 unguarded). ON it admits exactly the band and MARINE sews satin at **−13% stitches** with **251 self-crossings** and the drone wing 7 mm² bare: the decomposition, not the width, is the blocker (`docs/renders/wide-columns-2026-09-09/`); Kent's call. **PR 2 of the thin-stroke plan is BUILT and `cfg.keep_thin_strokes` is **DEFAULT ON since 2026-09-13** (byte-identical with it False)** — ON, a sub-floor region is absorbed into its neighbour only when its colour is within `merge_delta_e` of the absorber's, else kept for the run tier (flat lane only until PR 3). Fremont forced flat loses **3 thin strokes instead of 135** (recall 86.1% → 97.3%; the 0.5–1.0 mm band 51% → 88%) for 33 → 165 regions, +25% stitches and 71 → 81 trims at the same three colour blocks; gaulke unmoved. **FLIPPED 2026-09-13 on the render it had never had** — re-measured that day the cost had changed sign (`subpixel_edges`, ON 09-09, grows polygons 45–155%): Fremont +8.5% stitches and 103 → 76 trims, C 64 → B 76; drone's `AND DRONE` goes unsewn → sewn on the render while its scorecard does not move (F 0, raw −68 both ways); gaulke pays 2 → 4 cones for **zero** recall change and becker a second cone on a one-cone design — both accepted prices. Landed with two flat-golden re-captures and 30 tests re-pinned across 18 files. *(measured 2026-09-13 — `docs/thin-strokes-flip-2026-09-13.md`, `docs/renders/thin-strokes-2026-09-13/`)* *(measured 2026-09-08 — review doc; scope-history 09-08, four entries)* **Connected script is outside the construction (measured 2026-09-30):** the letter door's aspect ceiling (1.4) refuses a script word (bridge 2.6, tires 3.8) and a word is a cluster of one; force-tagging bridge's "Bridge" moved its red-on-yellow 39.9 → 40.6 mm² — no shipped rule reads the tag for rails, pull or gaps, and 22 % of the word's gap length is under the 1.0 mm pull + thread close at 80 mm (`docs/renders/bridge-phantom-2026-09-30/script-as-lettering.json`). **The lever Kent picked, built 2026-09-30: preflight `SATIN_GAPS_TIGHT`** — a satin shape whose gaps between its own strokes are under 2 × pull + thread, with the width at which its tightest tenth clears; fires on bridge (3 shapes), golden_tee (3), tires and gaulke (tires A → B, gaulke B → C), one warn per design (scope-history 2026-09-30). **The lettering findings name the artwork's limit (2026-09-30):** under 20 source pixels per letter `LETTERING_TOO_SMALL` and `LETTERING_ILLEGIBLE` say the lettering was lost in tracing, the larger source is the lever, and — for a source under the prep's 4 px/mm floor — the width at which the grid could try (`traced_at_mm`, which the size chip jumps to); bridge's teal words, 3.5 px/mm, 118 mm predicted, back at 140 measured.

### 2. Font library & lettering — [detail](docs/scope/2-font-library-lettering.md)

**Implemented · High (tech) / High (compliance).**
**85 fonts** in the sellable build, the EMBF binary codec, browser UI, and the
add-font QC/tier pipeline. The lettering path stitches three types — satin,
bean/running, cross-stitch fill — where before 2026-08-21 it was satin-only. A
second `--personal` build (125 fonts) carries what cannot be sold; for licences
"Font license compliance" above is the single source. Same tech score as before
on a different basis (see the area doc); known debt is the 26 glyphs that sew
nothing, in "Waiting on Kent". *(confirmed 2026-08-22 — manifest, engine suite)*
**Size guards (2026-09-03):** the 0.5 mm cross floor on the fabric (was 0.3 design pixels), hairline stretches as bean runs, and a per-element note of cap height and the share under 1.0 / 0.5 mm — warn only, no clamp; at 50 mm four hairline-authored fonts move > 5%. **Bold no longer closes counters:** its 0.3 mm is held per rail where a rail faces another across a gap the cross floor cannot spare (0.72 mm eye: 0.50 guarded vs 0.42; 0.36 mm: untouched vs 0.06); pull comp and normal/thin untouched; 60 of 83 fonts hold somewhere at 25 mm. **Short stitches (Law 53)** on the inside of bends, the Python guard mirrored and width-gated by the cross floor: geneva "S" 43% → 0% of same-rail advances under 0.3 mm, stitch counts identical, faces at the floor left alone. *(measured 2026-09-03 — commit `0a67171`, area doc §"Bold counter guard", §"Short stitches")* **And the LARGE end has no guard at all — NEEDS KENT (2026-09-07).** Measured over all 85 fonts at three texts: **18 fonts emit stitch segments longer than one DST record (121 units), worst 32.8 mm.** The quick starts are clean (`YOUR NAME` on a hat 0/2,346; `Your Name` 0/958; `Yours` 0/1,792) — it starts when letters get big: a **single-letter monogram at left-chest size gives 278 of 1,607, worst 17.9 mm**, and `AB` on a Full Back gives **1,933 of 5,828, worst 44.9 mm**. No machine sews a 17.9 mm stitch, so the three encoders each invented an answer — `.dst` travelled it (3,769 jumps), `.exp` split it, `.pes` wrote a 51.1 mm stitch. `dst.js` now splits like `exp.js` (byte-identical for every design that had no over-length segment — the 85-font corpus hashes the same before and after), but the ENGINE still emits them. What to do about a wide satin crossing — split satin, route to fill, cap the width — is a look-and-fabric call with a sew-out behind it. *(2026-09-07 — DOCTRINE, scope-history)* **BUILT AND MEASURED 2026-09-11 (review item 10) — and "18 fonts, worst 32.8 mm" was LOW by four times.** `tools/long-stitch-census.mjs` (validated: it reproduces DOCTRINE's own Full Back row, 1,933 of 5,828 worst 44.9 mm at 304.9×146.2 mm, to the stitch — the counting rule is PER AXIS, ±121 units per axis, and counting by segment LENGTH instead reports 53 more and calls the worst 51.1). Across 85 fonts × three texts, **80 of 85 fonts throw a stitch no machine can sew, worst 98.7 mm**, and it is not a Full Back problem — **one letter at LEFT CHEST breaks 63 of 85**. **Two UNITS bugs fixed unconditionally, no flag** (both are frames, not choices): `routeGlyph`'s Euler-walk underpath stepped 2 mm in the LAYOUT frame while the underlay pitch three lines away was correctly `/fitScale`, and `routeRuns` measured the font's authored `lenMm` there too — `western_light`'s "A" at left chest sewed **92 stitches, 66 past a record, worst 22.5 mm**, and now sews 560, worst 3.0; wrong shrinking too (an authored 1.0 mm run → 0.2 mm at a 0.2 fit, through Law 51's floor). Those two alone take 80 → **66 fonts**; `SATIN_BASELINE` moves +0.00–0.78% and the underpath fix ALONE reproduces all five new numbers byte for byte on the pre-change tree. **Two knobs BUILT and measured OFF, then KENT RULED 2026-09-11: `splitSatin` ON, `wideColumnFill` off** (the fill stays one config value away, for when a sew-out settles the ceiling). `splitSatin` ports `stage6_satin._split_points` with every constant mirrored (3.0 mm segment, 4-station ±0.23 wave, 5.0 mm threshold); `wideColumnFill` adds a WIDE class to `splitByCrossFloor` past the BROWSER's own 3.0 mm ceiling (not Python's 5.0 — `machine.py` calls that divergence "Python-side only until its own sew-out") and tatamis the stretch over its own rails at `fill.pcaAngleDeg`. Both reach **9 of 85, worst 23.6 mm**; split costs **2.47× the stitches and no trims**, fill **5.22× and 68.8×** the trims. They are near-SUBSTITUTES, not complements — with both on the split fires zero times. **THE PORT'S TRAP, pinned by name:** this module alternates the leading rail per station, so splitting in traversal order makes the direction flip cancel the wave's sign flip exactly and every station trenches the same holes (24.6 and 44.6 px on a straight 7.5 mm column); the cross splits in the column's A→B frame and reverses. **The 9 that remain are ALL cross-stitch fonts** and are a separate question: `crossfill.js` states that its lattice is in GLYPH UNITS by design, so an X arm grows with the letter and splitting it changes what a cross-stitch X looks like. **The flip moved FOUR tests.** `SATIN_BASELINE`: only `alchemy` (751 → 786, +4.7%) — the one font of 85 that threw a stitch past a record on the small-text sweep, so the only one of the five with crosses past 5.0 mm at 40 mm. The other three were **measuring the wrong quantity and the split exposed it**: a split cross is the SAME THREAD in more, shorter segments, so a bold column read as a SHORTER average stitch than a thin one (24.537 vs 24.678, inverted) and a sub-mm fit nudge moved 594 penetrations on a slant arm. All three now measure TOTAL SEWN PATH, exactly invariant under splitting because every split point lies on the segment it divides — and the slant claim got TIGHTER in the move (a 15° lean stretches a cross by at most 1/cos 15° = 1.0353; measured 1.0300 in both arms). `stripSplits` is NOT the tool for that on a design: DST-rounded integer coordinates make ordinary rail penetrations collinear and it removes 2,950 of them; it is exact only on the engine's own float geometry. *(measured 2026-09-11 — `docs/superpowers/plans/2026-09-11-wide-columns-in-lettering.md`; `test/wide-columns.test.js`, 18)*
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
**The worksheet states the digitizer's assumptions; both surfaces state run
time.** Backing and topper come off the fabric preset, not a stitch count;
`src/sewtime.js` gives minutes at 650 spm incl. trims. Only what the engine
derives — Kent's ruling left tension off. *(2026-09-20 — DOCTRINE)*
**Hooping advice shows before download, not only on paper.** The Download
sheet's "What to hoop" card states stabilizer, topper and needle for every
design type, from `EMB.hoopingAdvice` — the same function the worksheet
prints, incl. the 25k cutaway escalation. Needle is 75/11, ballpoint on knits
and terry, sharp on other wovens and caps, with its basis beside it; an unknown
garment gets no card. Trade categories, not sew-out constants: nothing reads
them for stitches. *(confirmed 2026-10-01 — `test/fabrics.test.js`,
`app/src/lib/hooping.spec.js`, `e2e/configurator-smoke.spec.js`; DOCTRINE)*

**The review sheet and worksheet quote the job on the operator's own terms.**
"Quote settings" on the Download sheet (`app/src/lib/quote.js`, one
`embstudio:quote` record per browser — Kent's ruling, not per project) holds a
machine, a running speed, a cone price and length, and an hourly rate; every
field is optional and an empty one drops its row. Run time is charged per STOP
(a colour stop the thread was not cut for counts; it cost nothing before), at
the typed speed for the needle and the plan rate for the stops, and names the
machine. Bobbin prints as 3/5 of the top-thread metres — Kent's ruling, after
Madeira's 3 m per 1,000 stitches read 4.0 m beside 2.5 m of top thread on
lettering. One profile ships, the SmartStitch S-1501 (15 needles, 1,200 spm
nameplate used only as a ceiling on the typed speed); its source is a brand
storefront, not a datasheet. Planning figures throughout — nothing here was
timed on a machine, and no maker publishes trim or colour-change seconds, so
a change is costed as a trim. Not built: per-machine re-sequencing, a bobbin
price, needle-count warnings, the service lane's own run time.
*(confirmed 2026-10-01 — `quote.spec.js`, `estimate.spec.js`, `pdfsheet.spec.js`, and the rows read in the running app)*

**What holds it at Medium:** fabric-preset accuracy is gated on the controlled
sew-out CARD, which has not been sewn — the one physical out so far (2026-09-01)
was a single uncontrolled icon. See Cross-cutting issues.

**The customer crops to the logo, and the crop travels as COORDINATES.** A
phone screenshot sewed its own chrome — 47 regions and 1,810 stitches, 24.9% of
`screenshot_phone_ui_golke` at 80 mm — and under that, the art bbox spanned
status bar to home indicator, so a target of 80 mm mapped to the SCREEN and the
design came out **80 × 167.3 mm**. The panel now proposes a rectangle on upload
(`lib/cropProposal.js` — the dominant ink cluster alone when it holds at least
`DOMINANT_SHARE_MIN` **0.75** of the ink, else the bbox of every cluster;
**Kent's ruling 2026-09-28** off a 31-image measurement putting the
screenshot's logo at 0.846 and every genuine multi-part design at ≤ 0.600),
shows it as a draggable box, and sends four normalized fractions.
`PipelineConfig.crop` applies them in BOTH decode paths — stage 0 owns its own
decode, and a crop in only one would have it classify the chrome the crop
exists to remove. **The file's own bytes still go**; a browser re-encode is
what 2026-09-20 paid to remove. No crop and a full-frame crop are both
byte-identical to the pre-crop engine, and a proposal is never applied
silently. *(confirmed 2026-09-29 — `digitizer_core/crop.py`,
`app/src/ui/CropBox.svelte`; spec
[`2026-09-22-upload-crop-design.md`](docs/superpowers/specs/2026-09-22-upload-crop-design.md))*

**The two engines' fabric and machine tables are wire-tested to agree**
(`test_fabric_wire.py`, `test_machine_wire.py`) — [area doc](docs/scope/3-studio-app-wizard.md).

**The 2026-09-30 design review shipped in four parts (Kent's "SpaceX /
Tesla" brief): a dark surround the hoop floats on with a flat garment step
and a scale bar; the Layers list and the canvas pointing at the same shape;
every setting explaining itself on hover (`lib/settingHelp.js`, `use:tip`);
view segments, Download by machine brand, and the digitize panel as three
tabs — Settings / Shapes / Threads, the spool list naming each cone once.**
Each part is written up, with its measurements and tests, in the
[area doc](docs/scope/3-studio-app-wizard.md). *(built and looked at
2026-09-30)*

**Closed-loop sew-out calibration SHIPS end to end, default OFF, on simulated
accuracy only (2026-09-30).** The Garment step's new *Fabric preset* row names
the preset in force and offers *Calibrate for this fabric…* (needs the service):
download card v2 in any of the six machine formats (`GET /calibration/card`,
82 × 103 mm, fits 5×7), sew it, drop a photo, and the reader
(`digitizer_core/calibration/`) hands back a draft **profile** — three
deltas that ADJUST the preset, clamped to the shipped table's span (DOCTRINE
ruling) — which Accept writes to `project.fabricProfile` and both engines sew
under. **Nothing is settled about cloth by this**: the reader recovers planted
pulls to 0.01 mm on a *simulated* photo and no card has been sewn (phase 0
deferred by Kent). Driven in a real browser against the real service
2026-09-30. Brief: `docs/sewout-calibration-brief-2026-09-30.md`.
*(built 2026-09-30 — `tests/test_calibration.py` 10, `test_fabric_profile.py`
14, `CalibratePanel.spec.js` 5; PR #569)*

**A Studio change is not verified until it has been *looked at* in a browser.**
Six buyer-visible defects across the 2026-08-25 and 09-07 sweeps, none seen by a
green suite. The list: DOCTRINE "Gotchas".

**Uploading artwork is the whole interaction — the panel asks NOTHING about what the art is** (the "It's flat art" / "It's a photo" / "Use automatic detection" buttons went 2026-09-30, Kent's call): the Studio sends `detect_photographic` and `faces_route_flat` in place of any per-design override, and a found face sews FLAT; **the flat half came back the same evening (Kent): a tonal reading offers "Sew as flat art" (`forced_class=flat`), and a design set flat offers "Use automatic detection"**; a misroute is still phase 2's to fix; [area doc](docs/scope/3-studio-app-wizard.md), DOCTRINE 2026-09-30. *(confirmed 2026-09-30)*

**The hoop you picked is DRAWN, and the export gate uses it** — four of ten garments have placement boxes larger than the biggest hoop (defect 39); [area doc](docs/scope/3-studio-app-wizard.md). *(2026-09-02 — PR #317; 2026-09-07)*

**The digitize panel states what CHANGED and offers the fix.** Shape list behind
an "Edit shapes (N)" disclosure, closed by default; a re-digitize reads as a
delta against `priorRun`; `COLOR_STOPS_HEAVY`, `LETTERING_TOO_SMALL` and
`STITCHES_TOO_SHORT` render as one-click adjustment chips offered AFTER the run
(Kent's call — an adjustment, not a pre-run form). `QualityReport` surfaces
trims. *(2026-09-02 — PRs #317/#318)* **Both "Make it bigger" chips offer a PARTIAL remedy** — one press clears the finding on 1 of 10 corpus fixtures, two presses on 4, and it worsens 3; the buttons are LEFT for Kent. The measurement, the misquoted comment it corrected and `STITCHES_TOO_SHORT`'s 66% moved to the area file, "Moved from MASTER_SCOPE (2026-09-18)". *(measured 2026-09-06 — `tools/enlarge_cure.py`, `tests/test_short_satin_shapes.py`)*

**The quality report groups thread-break risk and can point at it.** Preflight tags `STITCHES_TOO_SHORT`, `DENSITY_STACKED` and `SAME_HOLE_HEAVY` with `extra.break_risk` and `extra.show_shape_ids` (worst first, shade bands mapped to their region); `QualityReport` renders them under "Thread-break risk" with **Show on design**, which closes the sheet and selects the shape on the canvas. No threshold moved and no finding was added, so no grade changes. **Three limits, all still true:** the stacking check fires on no corpus design and the same-hole rate is diluted by the 0.15 mm row pitch, so in practice the group shows short satin stitches; there is **no sharp-satin-angle check** (no threshold with a source — gate 1; searched for one and found none: no primary source states a corner angle below which thread breaks, and Wilcom's Smart Corners defaults — cap under 20°, mitre under 45°, lap under 110° — are construction settings on a page that makes no break claim, so only a sew-out can supply the number — *confirmed 2026-10-01 — `docs/satin-angle-break-source-research-2026-10-01.md`, open web only*); and a "stitches under 0.5 mm" finding is deliberately absent, because a clean fill's row advance is under 0.5 mm by the row-pitch ruling — it rides out as `tiny_steps` / `tiny_step_fraction` only. Browser-built designs (lettering, shapes, hand-drawn, imported DST) still get no preflight. *(confirmed 2026-10-01 — `tests/test_break_risk.py`, `QualityReport.spec.js`, `DownloadSheet.spec.js`; measured 2026-10-01 — `logo_whitebg` at 80 mm, 573 of 4,129 fill steps under 0.5 mm with zero findings)*

**`cfg.border` reaches its own default now** — `null` = unset, key omitted when
unset, panel says "automatic", `fill_angle_deg`'s sentinel shape. Until
2026-09-02 the Studio seeded `"off"` and always sent it, so the service-side
default was unreachable. *(PR #318)*

**Preview thread width is PHYSICAL — neither widened nor narrowed.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 2.67 against the
ruled 0.15 mm fill row (rows overlap, as the professional's do) and 1.0 against
the 0.4 mm satin spacing; a fill at the ruled row looks solid because it IS. The
PDF sheet (`src/render.js`) and the SVG export draw the same width since
2026-09-04 — the sheet had drawn 1 px hairlines at any scale. Caveat: `lw` has a
1.2 px floor (1 px on the sheet), so the property holds zoomed in, not on a
thumbnail. Pinned on the literal 0.4 and both ratios. *(2026-09-04 — `preview.spec.js`)*

**Thread lighting is unverified against real thread** — eye-tuned, and the one physical out (2026-09-01) cannot settle it: its colours were random operator threading, so DOCTRINE bars grading colour from it at all. Treat the look as a preference, not a calibration. *(suspected 2026-08-25; sharpened 2026-09-14)*
**Uploading artwork is the whole interaction** — the run starts on upload and the panel states what the art was read as, with the override a one-click correction to that sentence; `detail_layer` sits on that row only where the art is tonal. Engine routing unchanged (ROADMAP gate 2). *(confirmed 2026-08-30 — e2e `digitize-auto-start.spec.js`; [area doc](docs/scope/3-studio-app-wizard.md))*

**The hoop you picked is drawn, and the export gate reads the thread's own extent** (`hoopTransform`, `DownloadStep`: confirm, not block; PNG and PDF ungated). **Open:** four of ten garment presets have placement boxes larger than the 200 mm biggest hoop, so the gate fires on shipped presets — whether auto-fit should cap is Kent's. *(measured 2026-09-04/07 — `preview.spec.js`, `DownloadStep.spec.js`; [area doc](docs/scope/3-studio-app-wizard.md))*

**The digitize panel states what changed and offers the fix** — a delta against `priorRun`, and `COLOR_STOPS_HEAVY` / `LETTERING_TOO_SMALL` / `STITCHES_TOO_SHORT` as one-click chips offered AFTER the run (Kent's call). The "Make it bigger" chips are a partial remedy, left for Kent: DOCTRINE. **`SATIN_GAPS_TIGHT`'s chip jumps to the width the finding names (2026-09-30, Kent's pick):** its headline shape's `clear_width_mm`, capped at 400, one button per parameter with the larger target winning over the 25% step — a claim about that shape, never the design. *(confirmed 2026-09-02, chip 2026-09-30; [area doc](docs/scope/3-studio-app-wizard.md))*

**`cfg.border` reaches its own default** — `null` = unset, key omitted, panel says "automatic". *(confirmed 2026-09-02)*

**Preview thread width is PHYSICAL** — `preview.js` `THREAD_WIDTH_MM` 0.4, drawn the same on the PDF sheet and SVG; holds zoomed in, not on a thumbnail. *(confirmed 2026-09-04 — `preview.spec.js`; [area doc](docs/scope/3-studio-app-wizard.md))*

**Thread lighting is unverified against real thread** — eye-tuned; the one physical out cannot settle it (random operator threading, DOCTRINE). `pending sew-out`.

**The thread picker matches a thread from a photo** — "Match from a photo…" in `ThreadPicker`: choose a picture, click a colour, get the chosen chart's five nearest threads with CIEDE2000 beside each; the photo is read on a canvas and never uploaded. `lib/colorMatch.js` is a port of the two skimage functions `digitizer_core/threads.py` snaps with, pinned to values generated from that Python, so both lanes name the same cone. **An approximate starting point, NOT a measurement, and the panel says so:** nothing corrects lighting or white balance (a white-reference click is the named follow-up — Kent's call 2026-10-01: not in this slice), and chart RGB is itself unverified against real thread. The picker's own nearest-name lookup (`nearestInList`) is still Euclidean RGB. *(confirmed 2026-10-01 — `colorMatch.spec.js`, `ThreadFromPhoto.spec.js`; driven in a browser)*

**Typographic punctuation folds to its ASCII twin where a font lacks it** (`satinfont.js TYPOGRAPHIC_FOLD`) — [area doc](docs/scope/3-studio-app-wizard.md). *(fixed 2026-09-07)*

**A design is named after what is in it, and the registry stops swallowing
failed writes.** Every project was "Untitled design"; `renameProject` and
`deleteProject` reported success for index writes that never landed. Both
propagate now, index first. Detail:
[area 3](docs/scope/3-studio-app-wizard.md); DOCTRINE.
*(fixed 2026-09-07)*

**"My designs" filters by what a design is** — name text, stitches up to,
colors (spools) up to, fits a hoop. The facts live on the index entry and are
written from the summary bar's own combined design, so a design saved before
this is unmeasured until it is next opened; a fact filter counts those rather
than hiding them. No content search ("dogs"): that needs tagging. Detail:
[area 3](docs/scope/3-studio-app-wizard.md).
*(built and driven 2026-10-01 — `libraryFacts.spec.js`, `projects.spec.js`, `DesignFilter.spec.js`, `ProjectsDrawer.spec.js`; no e2e spec)*

**The built bundle works wherever it is served** — [area doc](docs/scope/3-studio-app-wizard.md). *(fixed 2026-09-07)*

**Lettering under the cap floor now names a way out.** Line breaks lead, "fewer characters" second, "Size up" withheld at the width cap. Detail: [area 3](docs/scope/3-studio-app-wizard.md); scope-history 09-07. *(fixed 2026-09-07)*

### 4. Export formats — [detail](docs/scope/4-export-formats.md)

**Implemented (all six) · Confidence varies by format, not one score.**
DST, EXP, PES, **JEF**, SVG and the PDF worksheet, via both the browser encoders and the
service's `/export` route. One reachability caveat: `/export` is only reachable
from the product for purely-digitized designs — anything containing lettering
or manual shapes downloads through the browser encoders — **except JEF, which
the browser cannot write at all** and which therefore always goes through the
service, on every project type. **The DST caveat now names JEF as a way out (2026-09-08).** It said only "PES and EXP are unaffected" — written before JEF had a button and never revisited when #403 gave it one — so a Janome owner hitting the warning was steered to two formats their machine may not read, away from the one it does. Conditional on `jefAvailable` in both directions, and deliberately NOT named in the service-unreachable branch, since JEF needs that same service. `DownloadStep.spec.js` pins both.

**Two more machine formats work and have no button (Kent's call).** `/health` also advertises `pec` and `u01`; one two-colour design exported in all nine and decoded with pystitch gives the same 99 stitches at 80.0 x 24.0 mm each. **VP3 (Husqvarna/Pfaff) and XXX (Singer) shipped 2026-09-12** — resolved item 14, which also carries why PEC and U01 are held. *(measured 2026-09-07, revised 09-12)*

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
back the last node. *(confirmed 2026-08-25 — `curvedNodeThrough` tests + browser)* **The border is on the canvas too:** right-click a recognised shape for **Add border** / **Remove border**, and the restitch starts at once. *(confirmed 2026-09-09/2026-09-17 — `borderMenu.spec.js`, `e2e/field-border-menu.spec.js`; detail in the area doc)*

**Click a shape, edit it there — both lanes (2026-09-29, Kent's ask).** A click on an auto-digitized shape opens `ShapePopover` with its Layers-row controls; on a hand-drawn shape, Fill/Satin, colour, angle and Delete; on a preset, its colour. A hand-drawn shape's anchors and curve handles edit on the field too; the side canvas only draws. *(confirmed 2026-09-29 — `e2e/field-shape-popover.spec.js`, `e2e/field-node-edit.spec.js`; detail in the area doc)*

**Hand-drawn shapes can have holes (2026-10-01, ruling 11).** Any shape can be marked **Cut out** — in its popover, its assign box, or by drawing it in the side canvas's **Hole** mode; it sews nothing and cuts the smallest shape that contains it, or says it cuts nothing. A node drag that would break that containment holds at the last good position. *(fixed 2026-10-01 — `fieldNodeEdit.spec.js`, `e2e/manual-cutout.spec.js` (d))* Flipping Cut out on the hoop moves nothing else — marking a stray shape Cut out used to make the rest re-fit, 81×39 → 81×91 mm; the side panel's switch still re-fits, as adding or deleting a shape always has. *(fixed 2026-10-01 — `fieldNodeEdit.spec.js` real-engine pair, `e2e/manual-cutout.spec.js` (f))* Needed one engine fix: a three-point hole was silently dropped (4,678 / 4,678 / 4,456 on one square). *(fixed 2026-10-01 — `test/digitize.test.js`, `e2e/manual-cutout.spec.js` mutation-checked; area doc)* **Trace import keeps holes** as cut-outs instead of dropping them with a warning. *(fixed 2026-10-01 — `e2e/manual-trace-import.spec.js`)* Open runs and satin columns (plans 2 and 3) are not built. *(read 2026-10-01 — spec `2026-09-30-manual-digitizing-gaps-design.md`; plan 1 built per `docs/superpowers/plans/2026-10-01-manual-holes.md`)* **A cut-out is clear of the NEEDLE, not yet of thread:** every fill row floats or stitches across it until `fillColumns` is flipped (defect 52, Waiting on Kent 22). *(measured 2026-10-03 — `tools/fill-columns-sheet.mjs`)*

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
