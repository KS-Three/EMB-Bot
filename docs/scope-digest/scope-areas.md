# Scope-area digest — areas 1-5 + research backlog

Sources: the six files in `docs/scope/`, cross-checked against `MASTER_SCOPE.md`.
Cited as `1-auto`, `2-font`, `3-studio`, `4-export`, `5-review`, `backlog`, `MASTER`.

## Still in force

- Satin/fill misrouting is a PLACEMENT defect, not a threshold — retuning `satin_max` cannot fix it in either direction. `1-auto:36-57`
- `is_satin_candidate` (`stage6_satin.py:185`) is three *rejection* gates; `_dt_regular_and_within_cap` is a pure tightening (satin→fill only). `1-auto:66-76`
- The DT check runs on ALL design classes; the `design_class=="flat": return True` exemption is deleted. `1-auto:1031-1036`
- Compensation must never flip a shape's tier — both tier call sites thread `design_class`. `1-auto:946-951`
- Thread re-validation after vectorization is THREADS ONLY, never geometry. `1-auto:165`
- Score a region by MEDIAN OF PER-PIXEL dE00, never mean Lab — the mean lands on a colour almost no pixel carries. Trap has caught this codebase twice. `1-auto:170-182`
- A warning that makes a large loss sound routine is itself a defect (`DROPPED_SMALL_SHAPES` hid a 2,787 mm² drop as "detail"). `1-auto:147-155`
- Every new fill technique ships OPT-IN only; `fill_technique` stays `"tatami"`. Flipping contour's default is Kent's call, not geometry. `1-auto:546-550`, `1-auto:910-913`
- A tier-vocabulary addition touches five mirrors: `regions._TIER_VALUES`, service copy, `digitizer.js` `SHAPE_TIERS`, `DigitizePanel.svelte` select, `config.py` docstring. `1-auto:485-490`
- `manual.py`'s `VALID_TECHNIQUES` stays `{satin,fill,run}` — no raster there, so tonal techniques crash or silently no-op. `1-auto:419-423`
- Uncertainty resolves to NO behaviour change (untagged cluster, fallback polygon, `None` OCR fields). `1-auto:1521`, `1-auto:1704`
- `fontKey` is NEVER auto-picked downstream of OCR at any confidence; OCR gives characters, never a typeface. `1-auto:1727-1730`
- Cluster OCR confidence is MIN across members, not mean; the gate lives in Studio (`OCR_SUGGESTION_MIN_CONFIDENCE=55`), the service takes no position. `5-review:653-667`
- Font additions are license-gated: zero ShareAlike, texts shipped three ways, guard tests pin it. `2-font:20`, `2-font:38-42`
- Ink/Stitch (GPL-3.0) and Ember: concept-level clean-room only, no near-verbatim translation. `pystitch` (MIT) is the one usable runtime dependency. `backlog:8-11`, `backlog:203-210`
- Competitor-parity work is a STANDING PRIORITY RULE, not a gate: picked up only when nothing trust/quality-related is open, and only for independently-flagged gaps. A one-time gate was explicitly rejected. `backlog:57-68`
- Requirement 5 (drag a whole shape) is OUT OF SCOPE — `regions._raw_id` buckets centroid+thread, so translation destroys `shape_id`, which is what makes edits survive re-digitize. `5-review:215-232`
- A boundary drag's pull is weighted by ARC LENGTH, never vertex index, and capped at ¼ ring perimeter specifically to keep requirement 5 out. `5-review:150-162`
- The per-shape ✎ editor stays one-vertex (precision tool); the canvas is the direct-manipulation surface. Both write `boundary_override`. `5-review:207-213`
- Merge/split mint new ids hashed from the OPERATION's inputs, never geometry. `5-review:384-404`
- A rejected shape edit is always a clean `ValueError`→400/job error — never a crash, never silently repaired geometry; service validates, core re-validates. `5-review:307-317`
- Convert-to-text creates an EMPTY text element — nothing auto-filled that could be silently wrong. `5-review:597-608`
- `/export` is reachable only for purely-digitized designs; `src/dst.js` deliberately untouched by the PES/EXP fix. `4-export:20-24`, `4-export:121-129`
- Fabric presets are starting points; no physical validation has occurred anywhere in the project. `3-studio:167-170`

## Blockers

- DT-first classifier M2/M3 cannot proceed until the 37-file `scratch_corpus/` run happens (gitignored — empty in cloud checkouts, present on Kent's machine; runnable in a local session). `1-auto:926-929`, `1-auto:999-1006`
- Defending or refuting SAM2's quality cannot proceed until a real-photo corpus fixture exists — the only photo fixtures are synthetic stubs. `1-auto:86-91`
- `chain_links` cannot default ON until a sew-out validates `LINK_COVER_TOL_MM` (a thread spec, not a measurement). `1-auto:690-694`
- `FILL_ROW_MM` cannot move off 0.40 until a sew-out settles the law-19 two-population finding. `1-auto:1100-1103`
- PES/EXP cannot rise above Medium-High until a real Brother load or PE-Design open. `4-export:53-55`, `4-export:130-133`
- The DST axis question cannot settle until a third-party sew-out/read; the codec fix is additionally gated on Kent, since it re-orients every DST ever written. `4-export:135-137`
- Restitch-after-edit on Review/Create/Download cannot work until the digitize runner is lifted from `DigitizePanel` into `App.svelte`. `5-review:200-206`
- Hole-crossing boundary edits cannot degrade gracefully until a product call on what a hole means under a hand edit. `5-review:167-178`
- A live successful-MERGE proof cannot happen until `apply_shape_merges` gains bridging/convex-hull semantics — product decision, changes merge for everyone. `5-review:569-576`
- Appliqué `e_stitch` cover cannot be built until a spec for its comb stitch ORDER exists. `1-auto:1424-1434`
- Restoring the 13 pulled ShareAlike fonts cannot proceed until the (optional) lawyer consult. `2-font:38-42`

## Do not rebuild

- **Fix #6.2, capping the RAG merge on region-internal Lab spread.** Built, swept, reverted: tightening only defers a merge and substitutes worse ones; with a hard refusal the ceiling is SEEDS granularity, not the merge; and the usable window is empty (low caps blow through the 20-80 accept band, high caps are inert). `1-auto:204-222`
- **Wholesale DT/`VP90` satin-classifier swap.** Rejected — its "pure tightening, cannot get worse" safety claim was proven logically INVERTED (turns true positives into false negatives, the expensive error). `1-auto:914-930`
- **The flat-lane DT exemption.** Its premise (clean vector art carries no segmentation noise) was disproved on the repo's own benchmark logo: the exempted rule satin-stitched a wordmark "A" and a 4-point star into literal starbursts. `1-auto:1008-1036`
- **MSER for text detection.** Zero regions on the benchmark at every swept param — flat art has 2-3 unique grey values and MSER needs an intensity landscape. Structural to the domain, not one bad fixture. `1-auto:1647-1667`
- **Wholesale Catmull-Rom curve smoothing** (from `kent746/shape-tracer`): reintroduces the exact corner overshoot `fitCurvesForRing` was built to avoid. No change made. `3-studio:110-122`
- **Size-proportional `simplify_tol_mm`.** Measured: not like-for-like (Ember's "size" is pixels, ours is real mm), their floor coarser than our whole default. Investigation CLOSED, not open. `backlog:128-191`
- **A medial-axis-derived tangent field for streamline fill.** Rejected as a materially different unbuilt algorithm; `directionfield.py` reused unchanged. `1-auto:392-423`
- **Wiring `APPLIQUE_OVERLAP_ALLOWANCE_FRAC` into `_cover_layer`.** Wrong constant — it is Mode B batching's number and Mode B is not built. `1-auto:1352-1361`
- **"Recolor a shape to match, then merge."** `run_stages` applies merges BEFORE overrides every pass, so a merge always sees stage-4 original threads. `5-review:518-526`
- **A fixture yielding two touching same-thread shapes.** Falsified by a gap sweep: below ~10px they fuse to one region; at ≥12px they separate already ≥0.7mm apart — orders past `simplify_tol_mm`. No intermediate regime exists. `5-review:541-568`
- **Unconditional text-cluster regularization.** A real render showed the always-on skeleton buffer made a clean subline read LESS legibly and could never represent a letter counter. Now selective + OCR-gated. `1-auto:1549-1573`
- **`logo_alpha.png` as the chaining demo fixture** — the satin/fill fix made chain-on vs chain-off byte-identical there. Moved to `photo/enthusiast_logo.png`. `1-auto:697-717`
- **`EMB-Bot-standalone.html`** (pre-audit font registry) and **`EMB-Bot.html`/`src/app.js`** (read as a second competing app) — both deleted. `2-font:44-48`, `3-studio:105-108`
- Rejected only in MASTER, same weight: `blend_tonal_bands`, subject-relative streamline `d_sep`, SAM model swap, FastSAM/EdgeSAM (license), rebasing `feat/svg-import-shapes`. `MASTER § Measured negatives`

## Open gaps

- **Fill row spacing (law 19)** — two-population finding unresolved: refuted as a satin-rail artifact for one population, still alive on 43 commissioned cap logos. `1-auto:1100-1103`
- **Satin contour underlay confirmed ABSENT** (not merely unverified): `Fabric.satin_underlay` only ever takes `center_run`/`zigzag`, zero hits for contour. Cheap on existing rails. `backlog:225-240`
- **`CONTOUR_ENTRY_SOFT`/`HARD` (1.5/2.05) provenance** exactly matches Ink/Stitch's thresholds with no source cited in our own plan doc. `backlog:272-286`
- **Appliqué `e_stitch`** is an accepted config value producing byte-identical satin geometry. `1-auto:1424-1434`
- **The 8mm pre-cut scissors floor** is gated and tested but traced to no stated vendor constraint. `1-auto:1416-1420`
- **Studio's Download button has no path-selection logic** — `exporters.js` always uses browser encoders, so the "trustworthy" `/export` path is unreachable from the product. Fix exists, needs Kent. `MASTER § DST`
- **OCR suite cost** — `ocr_suggest_text` runs unconditionally per tagged member; local suite roughly doubled. Per-request latency never measured. Candidate for a `cfg.extra` opt-in. `1-auto:1716-1727`
- **`pystitch` adoption** — verdict Adopt, checked against `digitizer_service/formats.py`; area 4 says in progress. `4-export:139-145`
- **Top bar has no narrow-width handling** — at ≤375px the title collides with "My designs" and the page overflows horizontally. Found in QA, not fixed. `3-studio:98-103`
- **Promoted Ember items with independent justification:** expose streamline as a general manual fill; boustrophedon decomposition at arbitrary sweep angle; a color-block sequencer UI (cross-color sequencing today has zero geometric-adjacency signal). Fill patterns as DATA (`[{rowOffsetMm,rowPatternMm}]`) is the shape that makes new patterns table entries, not new algorithms. `backlog:70-97`, `backlog:35-48`
- **Ink/Stitch capabilities confirmed absent:** meander/stipple, tartan, ripple, circular fill + Fermat spiral, satin e/s-stitch point variants, bean-stitch per-position variable repeat. `backlog:242-250`
- **Condensed/expanded width and mixed per-letter size** deferred in font editing (uneven satin distortion risk). `2-font:48-51`
- **Stage 0-4 cache** measured, not started: logo art ~7.3s→~1.4s but a photo only ~14s→~6.6s, because nearly half a photo's cost is the stitch planning a boundary edit invalidates by definition. `5-review:185-199`

## Contradictions

- **`MERGE_DELTAE00_THRESH`.** `1-auto:749` says PR #45 retuned it 10.0→20.0; `MASTER § Standing rulings` says leave it at **26.0**. MASTER is more recent AND cites code (`stage2_photo_segment.py:452-496`) — trust MASTER.
- **Satin/fill promotion path.** `1-auto:66-76` states flatly no path promotes a rejected shape back to satin; MASTER live defect 5 says a promotion path on `explained` LANDED 2026-08-16 and that the residue is a SEGMENTATION problem, not the classifier. MASTER newer — but its code is in PR #157, not `main`.
- **Sub-millimetre satin.** Area 1 is silent; MASTER live defect 2 says the proposed `2·p90<1.0mm→run` reroute is DISPROVED for flat art and must be gated to the photo lane. MASTER is the only current statement.
- **"Flat spot-colour art is the good case"** — `1-auto:654-660` rests the whole Medium rating on it, but `MASTER § Evaluation corpus` (2026-08-15) found stage 0 routes six of seven REAL customer logos to the GRADIENT lane and one to `photo_scene`. Flat-lane tuning measured only on synthetics is untested against real input. MASTER is newer and cites the fixture list.
- **`match_shape_ids`.** `5-review:386-388` says it "is not wired into `pipeline.run_stages` at all today", while the same file repeatedly claims overrides are carried across re-digitize *via* `match_shape_ids` (`5-review:270-272`, `5-review:317-318`). Self-contradiction; the carry-forward claim needs re-verification in code. The "not wired" claim is the one that cites a check.
- **`repro_gradient_white_icon.png`'s grade** reads D/58 at `1-auto:355` and F/0→B/76 at `1-auto:192`; the later entry (per-region instrument) supersedes, and MASTER records the same correction.
- **`pystitch`** — `4-export:139-145` "in progress"; `MASTER § Research backlog` "has since been adopted". MASTER newer.
- **Browser DST's standing** — `4-export:25-31` treats it as the shipping default with sewn evidence; CLAUDE.md says treat it as EMB-Bot-internal only. `MASTER § DST` flags both readings as needing Kent rather than reconciling them.
- **Area 5's own corrected paragraph** is on the record as a self-contradiction: it once read "nothing today can move a node or a line" while the same file said boundary reshaping CLOSED 2026-08-05. The CLOSED entry is correct. `5-review:98-108`

## Sequence claims

- **Merge/split are applied BEFORE `apply_shape_edits`** in `run_stages` — ids minted against the full stage-4 generation before deletions/overrides consume any. This ordering is why recolor-then-merge can never work. `5-review:369-373`, `5-review:518-526`
- **`depth_sort_layers` runs after `compact_layers`** (so stage 5's underlap model follows the same order) **and before `apply_layer_overrides`/`sew_order`** (so review-screen overrides still win). `1-auto:611-620`
- **Fixed text-pipeline order:** `tag_enclosed_background` → `detect_text_clusters` → `regularize_text_clusters` → `ocr_suggest_text`, so OCR reads whichever polygon will actually sew. `1-auto:1507-1512`, `1-auto:1684-1689`
- **`revalidate_threads` runs right after `tag_enclosed_background`** — i.e. after stage 4 has moved the outline. `1-auto:158-168`
- **Border seam tie-break is SEW ORDER**, chosen because it needs no lookahead or second pass: causally, a shape either yields to an already-committed border or has none to yield to. `1-auto:1114-1136`, `1-auto:1174-1181`
- **Per-shape tier overrides must sit ahead of scanline/meander/gradient/contour** in `stitch_one`'s elif chain, or a design-wide tonal technique beats the per-shape override. `1-auto:381-391`, `1-auto:556-559`
- **Fix #6.3 could not be measured until its prerequisite landed** — per-region `THREAD_MATCH_POOR` scoring (`619e9ad`) replaced the pooled median; the earlier "does not move the grade, do not tune against it" ruling was an artifact of the old instrument. `1-auto:183-202`
- **M1 (`ShapeField` hoist) is merged and is the prerequisite for M2/M3**, which have not started and are corpus-gated. `1-auto:1458-1466`
- **Row 12 (sketch tier) was predicted to fall out of rows 8-11 "nearly free, a config preset, not a new engine" — and did.** All photo-plan rows 0-15 built. `1-auto:630-652`, `1-auto:1484`
- **The icon system's 11 follow-up files depended on the foundation PR merging first**, and the shared inventory test had to be reconciled after the parallel fan-out. `3-studio:138-165`
- **True instance-level depth needs photo-plan step 3's segmentation** — left as a documented seam in `depth_sort_layers`, not faked. `1-auto:622-625`
- **MASTER-side ordering that binds this slice:** option A (tatami + shade bands) requires the design written BEFORE the code; satin-vs-fill routing was taken AHEAD of option A (Kent, 2026-08-14); `split_tonal_regions` stays default-OFF until the sew-out. `MASTER § Standing rulings`, `MASTER § Waiting on Kent`
