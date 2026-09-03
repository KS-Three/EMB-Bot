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
   essentially never cut. **On cloth 2026-09-01:** the first sew-out's tail
   is exactly this — late satin fragments riding over pre-sewn work, jump-
   chains stepping 8–11.5 mm. *(measured 2026-08-21/22 — area 1; cloth
   2026-09-01 — scope-history)*

15. **An UNDECLARED photograph gets neither depth sequencing nor the palette
    bind, and its region re-snap escapes the selected palette.** `is_photographic`
    gates the fix and is DECLARED, not detected — `owl_kent.jpg` reads LESS
    photographic than two logos, so a photograph left undeclared routes
    gradient and the re-snap sews more spools than the cone list names.
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
    *(2026-09-01 — `test_duplicate_cone_layers.py`, 13)*

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
    needle-breakage signal. **No off switch for photo classes**
    (`effective_split_tonal` ORs flag with class). *(2026-09-02 — bisect on
    `coverage_max`; [notes](docs/scorecard-baseline-attribution-2026-09-02.md))*

21. **Fill travel is laid OVER columns already sewn — FIXED, DEFAULT ON (Kent's flip
    2026-09-03)** (`cfg.fill_travel_under_cover`, PR #323): the column order prefers a next
    column reachable over unsewn ground (`_reorder_for_cover`, cuts × 25 + travel + exposed × 2,
    never worse) and an exposed bridge routes through unsewn ground. Fill-phase exposed travel
    Fremont **286 → 90 mm** (trims 47 → 52), gaulke 204 → 8, drone 546 → 89, sunset 711 → 344
    (**53 → 42**), meadow 691 → 324; OFF md5-identical; +7–11% time on logos, +49–67% on the 263-run photo fill. *(measured 2026-09-03 — `docs/fill-travel-under-cover-2026-09-03.md`)*

22. **Small curves sew as polygons — FIXED, DEFAULT ON (Kent's flip, 2026-09-03)** (`curve_turn_deg` = 15; None/0 = the old polygon): a turn-per-vertex bound re-reads each Douglas-Peucker edge against its raw arc, split at the midpoint, floored at one pixel; near-floor lettering exempt per ring. Fremont's counter **9 → 33 vertices, 47° → 17°**, inner rail σ 0.038 → 0.026 mm, trims 52 → 45. **Gated to four pixels of tolerance** (`_CURVE_MIN_EPS_PX`; ≥ 20 px/mm at 0.2 mm): below it the 1-px floor read raster texture as arcs — every 10–16 px/mm fixture got rougher (sunset 16.1 → 16.5, meadow 15.2 → 16.5) and two borderline ribbons changed tier through the DT classifier's skeleton — so a 600–1200 px web logo is byte-identical and every golden stays pinned; `tools/curve_tiers.py` is the per-shape tier diff. *(measured 2026-09-03 — `docs/round-curves-2026-09-03.md`, "The flip")*

23. **Rail dents — FIXED (Kent, 2026-09-03), diagnosis corrected.** `place` stepped an overshooting rail in by 15% however small the overshoot (250–1000 placements per design, 70–90% under one pixel) and now puts it on the artwork edge along its own normal, with a micron of containment tolerance; taper zones and caps keep the ladder. Rail jitter p50 **halves on every fixture** (Fremont 0.012 → 0.0045 mm), same-rail holes 11 → 5, median rail 0.02–0.08 mm further out, nothing further outside the art. The "one whole rail 15% short in every golden" was the synthetic bar, not the goldens (the micron alone moved 4 stitches on Fremont); the 8–24% of rail points > 0.1 mm inside on real art are the symmetric-offset rail model — open, Kent's call. Goldens re-pinned: alpha, ribbon ×3. *(measured 2026-09-03 — `docs/rail-dents-2026-09-03.md`)*

24. **Hairline columns (< 0.6 mm) — the MECHANISM is fixed, the tier is not.** A hairline STRETCH of a stroke (crosses under the 0.5 mm floor, ≥ three bean stations of spine) now sews as a 3-pass bean along its spine in both engines, only where the uncompensated art is wider than `simplify_tol_mm` (pull comp grew a 0.04 mm needle into a tick); Fremont's 2.6 mm "THE" reads. Whether a 0.5 mm bean reads better on cloth than a dropped bar is card block 5's question — `pending sew-out`. *(fixed 2026-09-03 — `docs/design-review-fine-lettering-2026-09-03.md`)*

25. **Fill stitches HALVED by float dust at the stitch-length threshold — FIXED (Kent, 2026-09-03).**
    `split_long_moves` split a 3.0000000000000004 mm grid step into two 1.5s; a micron of tolerance
    (`stitches.SPLIT_TOLERANCE_MM`) removes them: whitebg 2162 → **1982** st, Fremont 6365 → **5789**, sunset 11614 → **10416**, no row or trim moves. Goldens re-pinned (whitebg, alpha; pre-change tree). `tools/fill_dust.py`. *(fixed 2026-09-03 — same doc)*

### Closed — kept numbered, because ten other docs cite them by number

Full text moved to [`docs/scope-history.md`](docs/scope-history.md) 2026-08-27;
these are pointers, not status.

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
   2026-09-02, left gate 3; cost is defect 20. *(`pipeline.py:92`)*

*(added 2026-08-17 — `docs/project-review-2026-08-16.md` §1.6: chaining was absent
here, so a good-faith flip would have shipped bare-fabric thread unwarned.)*

---

## Doctrine — moved to [`DOCTRINE.md`](DOCTRINE.md)

**Standing rulings, Measured negatives, Corrections and Gotchas now live in
[`DOCTRINE.md`](DOCTRINE.md)** (split 2026-08-28). Read it before proposing work,
the same way you read this file for status.

The split is not filing. Those four sections answer *"has this already been
decided, tried, disproved, or paid for?"* — which does not go stale and only ever
accumulates. This file answers *"where does the project stand today?"* — current
state only, under a line budget. They were competing for one budget and the
standing content was winning: this file ran 268 lines over before the split, and
two compaction passes could not close it without deleting things that still
govern decisions.

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
7. **26 glyphs that sew nothing, in 6 shipped fonts — SPLIT IN TWO 2026-08-28,
   diagnosed from the shipped `.embf` binaries alone** (user-facing half
   already closed — the Studio says "This font can't stitch …"). 20 are
   `stripRunParamsIfSatin` taking runs-only glyphs' params; 6 are a GATE 1
   refusal (no authored run length upstream — defaulting one is refused by
   `test/run-fonts.test.js:44`). Full per-font diagnosis: area 2 doc,
   "stripRunParamsIfSatin". **Still open, one grep not a session:** count
   `running_stitch_length_mm` in `<ink-stitch>/src/roaring_twenties_KOR/
   ltr.svg`. **>0** → the narrow fix (scope the strip to glyphs WITH columns)
   revives the 20 — Kent's call, since inking those glyphs changes the bbox
   auto-scaling of any text containing `+ - / < = > \ _ ¯ °`. **0** → all 26
   are the same gate-1 case and this closes permanently.
   *(measured 2026-08-28 — `.embf` decode; detail: area 2)*
10. **RESOLVED 2026-08-25 — Studio typography: "tighter and more editorial."**
   Kent's direction, given when asked. It settled the three items the earlier
   type work left alone (irregular scale ratios, `h3` at body size, untokenised
   weights) and it is a STANDING one — new UI is set to it, not re-litigated.
   What it means in practice is in the area doc. *(2026-08-25)*

11. **The setting that helps a misrouted photograph has no UI, and the
   control that looks like it is a different, harsher one.**
   (That control is now the reading row's "It's a photo" correction; it was
   a "This is a photo" checkbox until 2026-08-30. Renamed and moved out of
   the params list — what it SENDS is unchanged, so every number below still
   stands.)
   CORRECTED 2026-08-28 — the first draft of this entry said an unticked
   "This is a photo" costs the palette bind and depth sequencing, implying
   ticking it is a free win. It is not, and the error was mine.
   `cfg.is_photographic` — the declaration that turns on the bind and depth
   sequencing while the fill tier stays FILLED — appears **nowhere** in
   `app/src` (grep, 0 hits). The checkbox sends something else entirely:
   `digitizer.js:144` sets `forced_class="photo_subject"`, which also fires
   `auto_photo_tier` → streamline. Measured on `owl_kent.jpg` at 100 mm:
   16 stops / 0.992 coverage undeclared, 12 / 0.990 with `is_photographic`
   (2026-08-31: the rehome shrinks these to 13 and 11 — the ordering holds),
   and **26 stops / 0.591 coverage** through the checkbox — 0.591 being the
   thread-paint number Kent's own 2026-08-25 filled-beats-thread-paint ruling
   already records. So the one control the Studio offers makes his artwork
   worse on every axis, and the one that helps cannot be reached.
   The product call is what to expose, not whether to nag: surface
   `is_photographic` on its own, split the checkbox into declaration vs tier,
   or leave both alone. See defect 15. *(measured 2026-08-28 —
   scope-history 08-28)*

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
   1560st); the repro has none (closest cones 33.4 ΔE). Real artwork runs
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
One specific question is now queued behind it with the code change already
measured both ways: whether a split, underlaid 5.3 mm satin column is sound —
see DOCTRINE, "Raising `SATIN_MAX_WIDTH_MM`". *(2026-09-02 — reverted branch)*

### Evaluation corpus & harness — real gap, newly tracked here

**The gap: no repeatable automated quality signal**, so every serious quality
question queues behind a corpus nobody has or a sew-out nobody has scheduled. A
labelled corpus plus a scoring harness would let a classifier change be judged
against *something* before either arrives.

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
**Both halves of the smoothness complaint now have instruments, and they are not
the same measurement** (Spearman 0.028, n = 12 — rules out redundancy, not
dependence). `tools/edge_smoothness.py` owns edge noise; `tools/curve_fidelity.py`
owns the curve half, read from `plan.iter_runs()` because **curve fidelity is
not readable from a raster**. Read **`roughness_deg`** per design; `turn_gini` is
substantially a COMPLEXITY statistic (Pearson −0.763 vs log trace count), valid
only on the ladder or a paired arm; the floor is **stitch length**. On Kent's
four Becker artworks the two SPARSE ones measure roughest — complexity, not
size (an earlier "small placements sew rougher" reading is withdrawn).
*(measured 2026-08-27/28 — PR #281; `docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`)*
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

**Mechanism 2 — pull comp's min-feature guard scoped to `poly.interiors` —
PROTOTYPED AND COSTED, not shipped.** An exterior-pocket branch holds 15 real
slots at 0.528–0.920 mm and reds the chaining benchmark (3.8 → 6.4 trims/1k vs
4.1; +2 trims at the shipped `chain_links=False`). **Kent's call 2026-08-28:
hold it.** `docs/exterior-notch-guard-2026-08-28.md`. *(prototyped 2026-08-28)*

**Mechanism 4 — the instrument that hid all of it — is HALF CLOSED
2026-08-28.** Coverage and IoU average, and deformation is local, so
`stroke_coverage.py` reports the WORST medial-axis stroke (DRONE's E: 58.3%
worst vs 72.7% mean). **Still blind to TILT**; the obvious tilt metric was
built and REJECTED (ranks a good O worse than the deformed H). Detail in
`tools/letterform_fidelity/README.md`. *(2026-08-28)*

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
**Size guards (2026-09-03):** the 0.5 mm cross floor on the fabric (was 0.3 design pixels), hairline stretches as bean runs, and a per-element note of cap height and the share under 1.0 / 0.5 mm — warn only, no clamp; at 50 mm four hairline-authored fonts move > 5%. **Bold no longer closes counters:** its 0.3 mm is held per rail where a rail faces another across a gap the cross floor cannot spare (0.72 mm eye: 0.50 guarded vs 0.42; 0.36 mm: untouched vs 0.06); pull comp and normal/thin untouched; 60 of 83 fonts hold somewhere at 25 mm. **Short stitches (Law 53)** on the inside of bends, the Python guard mirrored and width-gated by the cross floor: geneva "S" 43% → 0% of same-rail advances under 0.3 mm, stitch counts identical, faces at the floor left alone. *(measured 2026-09-03 — commit `0a67171`, area doc §"Bold counter guard", §"Short stitches")*
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

**A Studio change is not verified until it has been *looked at* in a browser.**
A 2026-08-25 sweep found a primary CTA rendering white-on-white on every wizard
step and a canvas menu creating elements with no feedback — both shipped, both
invisible to a green suite. *(confirmed 2026-08-25 — area doc)*

**Uploading artwork is the whole interaction — the panel no longer asks the
user to classify it first.** The run starts on upload and the panel STATES what
the art was read as ("Read as flat art" / "as a photo" / "as shaded artwork" /
"couldn't tell"), with the override recast as a one-click correction to that
sentence. `detail_layer` sits on that row too (Kent 2026-08-30) and appears only
where the art is actually on a tonal lane, by reading or by override. Nothing
changed in what gets sent, so area 1's photo-control numbers are untouched, and
the engine's routing is unchanged — ROADMAP gate 2 bars recalibrating stage 0,
and phase-4 v1 works around it with exactly this override.
*(confirmed 2026-08-30 — driven in a real browser against the
real service, every state of the row clicked through and looked at; pinned by
e2e `digitize-auto-start.spec.js`; numbers in scope-history 08-30)*

**The hoop you picked is now DRAWN, and the export gate uses it.** `preview.js`
had one box — the garment's PLACEMENT box — and called it the hoop, so choosing a
hoop changed nothing on screen. `hoopTransform` returns both and fits to the
larger; `DownloadStep` warns before a stitch export that will not fit (confirm,
not block; PNG and PDF worksheet ungated — not machine files). **Live: the stock
Tote / Full Back preset is 203.2 mm against a 200 mm max hoop**, so it fires on a
shipped preset — whether auto-fit should CAP is open. *(2026-09-02 — PR #317;
`preview.spec.js`, `DownloadStep.spec.js`, e2e)*

**The digitize panel states what CHANGED and offers the fix.** Shape list behind
an "Edit shapes (N)" disclosure, closed by default; a re-digitize reads as a
delta against `priorRun`; `COLOR_STOPS_HEAVY`, `LETTERING_TOO_SMALL` and
`STITCHES_TOO_SHORT` render as one-click adjustment chips offered AFTER the run
(Kent's call — an adjustment, not a pre-run form). `QualityReport` surfaces
trims. *(2026-09-02 — PRs #317/#318)*

**`cfg.border` could never reach its own default — the Studio always sent one.**
`project.js` seeded `border: "off"` and `digitizer.js` sent the key
unconditionally. Now `null` = unset, key omitted when unset, panel says
"automatic" — `fill_angle_deg`'s sentinel shape. *(2026-09-02 — PR #318)*

**Preview thread width is PHYSICAL, and must not be widened.**
`preview.js`'s `THREAD_WIDTH_MM` (0.4, nominal 40wt) is coverage 1.0 against the
engine's 0.40 mm fill rows, so a fill that is too open LOOKS too open. Widening
it to make fills look solid would be the display layer prejudging row spacing —
a two-population question standing *pending sew-out* — which is ROADMAP gate 1.
Caveat: `lw` has a 1.2 px floor, so the property holds zoomed in, not on a
thumbnail. Pinned by a test on the literal 0.4.
*(confirmed 2026-08-25 — `preview.js`, `preview.spec.js`)*

**Thread lighting is unverified against real thread** — eye-tuned, no sew-out to
compare against. Treat the look as a preference, not a calibration.
*(suspected 2026-08-25)*

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
   neither. A claim with no pointer is unverified by definition. This exists
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
