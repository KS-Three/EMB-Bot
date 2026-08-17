# Plans digest — remaining Studio slices, digitizer steps, misc specs

Files read end to end: `plans/2026-07-24-studio-image-slice2.md`,
`plans/2026-07-24-studio-sizing-slice3.md`, `plans/2026-07-25-studio-polish-slice4.md`,
`plans/2026-07-25-studio-elements-slice5.md`, `plans/2026-07-25-studio-textpower-slice6.md`,
`plans/2026-07-25-studio-projects-slice7.md`, `plans/2026-07-26-studio-modern-slice8.md`,
`plans/2026-07-29-digitizer-step1-skeleton.md`, `plans/2026-07-29-digitizer-step3-stitch-planning.md`,
`plans/2026-07-30-digitizer-step4-satin.md`, `plans/2026-07-30-digitizer-step8-service.md`,
`plans/2026-08-05-text-cluster-detection.md`, `specs/2026-08-05-text-cluster-detection-design.md`,
`specs/2026-08-11-sam2-studio-seam-design.md`, `specs/2026-08-11-photo-palette-overflow-design.md`,
`notes/2026-07-27-embf-acceptance.md`, `handoffs/2026-08-03-gradient-defects-handoff.md`.

## Design decisions that still govern

- **No stitch math in `app/`** — all engine calls are `EMB.*`; engine guarded by `node --test`, app free to churn. `slice2 § Global Constraints`, `slice3`.
- **Proven constants copied, never re-derived** (WORK_MAX_PX 480, SIMPLIFY_TOL 1.6, ABSORB/DESPECKLE shares, 60 shapes/color, ALPHA_CUTOFF 128) — known-good output beats retuning. `slice2 § Global Constraints`.
- **Engine changes must be additive/back-compat: opts absent ⇒ byte-identical output.** `slice3 § Task 1`, `slice6 § Global Constraints`.
- **Resize REGENERATES stitches** via the existing fit-scale machinery, so density stays correct; `sizeMm: null` = auto-fit, offsets are design-center-from-hoop-center, +y UP (DST), clamped to hoop. `slice3`.
- **Hoop-space rendering for the field; design-fit path preserved** for FontSelect thumbnails and PNG export. `slice3 § Task 3`, `slice8 § B5`.
- **`renderRealistic`'s return contract is POST-VIEW** (`scale = base*zoom`, `toCanvas` includes pan), so all interaction math needs zero changes; `view` defaults to identity. `slice8 § B1`. One render path shared with the empty state; no hardcoded fabric colors. `slice8 § B4`.
- **Multi-element combine is pure app-side concatenation** — offsets bake hoop-absolute coords into stitches, so `combineDesigns` must never re-center; trim + color record separates elements. `slice5 § Task 2, Notes`.
- **Project model v2 `elements[]` with lossless v1 migration**; `migrateProject` must spread-merge over `defaultProject()` in BOTH branches. `slice5 § Task 1`, `slice8 § B13`.
- **Runtime image data (workImage/flat) is never persisted** — reopening shows "upload again". `slice7 § Global Constraints`.
- **Storage-failure posture:** every localStorage op try/catch; app works unpersisted; a throwing store means hints still SHOW but `dismiss` becomes a no-op. `slice7 § Task 3`.
- **Migration write-order (no data loss ever):** write record → read back and verify → write index/pointer → only then delete the legacy key; any failure leaves the legacy key for next boot. `slice7 § A1`.
- **`saveProject`/`rename`/`delete` on an unknown id are defined no-ops** so autosave can never resurrect a deleted record. `slice7 § A2, A10`.
- **In-flow expansion, never floating popovers** — `.panel-body` clips overflow. `slice7 § A9`, `slice8 § B6`.
- **Templates are presets (project patches), not saved projects.** `slice4 § Global Constraints`.
- **Everything offline:** jspdf and Inter bundled via npm, no CDN; jspdf dynamic-imported so the text path loads instantly. `slice4 § Task 2`, `slice8`.
- **Thread names are generic, no brands** (~56 shades + Custom). `slice8 § Task 4`.
- **Units rule:** px through stage 3; stage 4 emits mm floats, origin design-center, **y-DOWN**; px→mm from `target_width_mm / non-bg bbox width`. `step1 § Stage contracts`.
- **`shape_id` = blake2s of rounded centroid/area/thread** — stable across runs and across classical↔SAM boundary refinement. `step1 § Stage 4`.
- **Determinism is a contract** (seeded k-means, `medial_axis(rng=0)`), pinned by a hash canary. `step1 § Tests`, `step4 § Defect 1`.
- **`Segmenter` ABC** so a `SamSegmenter` drops in without touching stitch code. `step1 § Stage 3`.
- **Full generated Isacord chart, not a stub** — facts-doctrine data is free, and "the chart never changes again" kills the golden-churn worry. `step1 § Deviations`.
- **Warnings are enumerated machine-readable codes from day one.** `step1 § Package layout`.
- **Fail-open for every tagger/heuristic:** ambiguous → untagged, treated exactly as today; a tagger that silently hides a shape is worse than a missed tag. `text-cluster-design § 3.2.5`, `text-cluster-plan § Step 5`.
- **Sew order first, overlap follows it:** threads descending area, ties by thread number; grow a region by `overlap_mm` (0.25) only where it touches a LATER-sewing region — otherwise the grown edge shows. `step3 § Sew order`.
- **Every machine constant named and justified in one module**; `MAX_STITCH_MM` 12.1 is a DST format ceiling, not a preference. `step3 § Machine constraints`.
- **Fabric presets are a straight port of `src/fabrics.js`** so both engines make the same physical choices until sew-outs say otherwise. `step3`.
- **Satin classification runs on the ARTWORK polygon** (sewn on the grown one) so fabric/pull-comp choice can't flip a logo between satin and fill. `step4 § What satin is here`.
- **Smoke-test and read the debug renders BEFORE writing tests** — that order found 5/4/11/5 real defects in steps 1/3/4/8 that test-first would have frozen as correct. `step3 § Method`, `step8 § Verification`.
- **No DST crosses the service→browser boundary**; `/digitize` returns the browser `Design` contract (+y UP, 0.1 mm ints) and the y-flip lives only in `adapter.py`. Do not transpose to reconcile — a sew-out resolves it. `step8 § The axis decision`.
- **Cross-language brand ids are test-asserted equal**; mirrored parsers are not trusted. `step8 § Thread charts`.
- **Service posture:** single-worker executor (CPU-bound; queueing beats thrash), 127.0.0.1 bind, token seam built-but-off, CORS localhost only and never `null`, cache key = sha256(image) + canonical resolved config, 12 MB / 40 MP caps, 32-entry LRU. `step8 § Service shape`.
- **Nothing is ever auto-substituted for detected text:** geometric regularization ships by default and always resembles the source; "Convert to text" is a per-cluster user action with an empty text field and no pre-picked font. `text-cluster-design § 1`.
- **`text_candidate`/`text_cluster_id` are server-computed read-only review fields, not override keys** — re-derived each generation, so no `regions.py` validation, `app.py` mirror or carry-forward. `text-cluster-design § 3.4`.
- **`textConversions` is pure Studio state**, excluded from `canonicalShapeEdits`/`editsKey`, because conversion has client-side effects only. `text-cluster-plan § Step 6`.
- **SAM2 is per-request context, not element params** — a global localStorage flag keeps stale flags out of `.embproj`; absence of UI IS the design; toggling changes the cache key, so A/B costs one digitize. `sam2-studio-seam § Design`.
- **Palette overflow is bounded and conditional:** grow past `max_colors` only for a region whose own floor ≤ `excess_deltae/2`, because "no thread is close" is not fixed by more medoids; `PALETTE_OVERFLOW_K = 3`. `photo-palette-overflow § Design`.

## Deferred and cut work

- **No slant/italic satin in Python** — browser engine has it; "port when lettering integration (step 10) needs it". `step4 § Known limitations`. Still absent from `digitizer_core`.
- **Directional (per-axis) pull comp** — explicitly out of scope; `machine.py` still models pull comp along the stitch direction only. `step3 § Scope`.
- **Poor-match warning when a brand has no close colour** (Madeira Rayon ΔE 12.2 purple) — deferred to step 9 preflight, "worth doing before the brand picker reaches the UI". `step8 § Follow-ups`. The brand picker has since shipped and no such warning exists — **seam still open, gate already crossed.**
- **Per-stage progress reporting** on `/jobs` (queued/running/done only). `step8 § Follow-ups`. No `progress` in `digitizer_service/app.py`.
- **Stitch processor / imported-design re-density** — deferred by `step3`/`step8`; later closed as a permanent non-goal in `PRODUCT.md`.
- **OCR** — deliberately not added; classical-CV heuristic chosen instead. `text-cluster-design § 4`.
- **General shape-primitive recognition** ("snap to clean primitive", stronger satin/fill classifier) fenced off to the DT-first thread. `text-cluster-design § 5`. That thread was later rejected, so this has no live owner.
- **The four `photo_segment_sam2_*` tuning fields stay unexposed**; the service already accepts them, so exposure is one line on the same seam. `sam2-studio-seam § Non-goals`.
- **Font-tier classifier gap: satin-column count is measured per FILE, not per GLYPH** — a font can pass tiering while its letters have no stitchable data (`ondulamarif_XL` → 0 stitches). "If another 0-stitch report appears, check per-glyph `cols` first." `embf-acceptance § Demotion`. Not fixed.
- **The 1%-drift gate over-triggers on low-stitch-count fonts** (`glacial_tiny` 1.07%, kept on visual QC); never changed to absolute delta. `embf-acceptance`.
- **Two implementer's-choice seams left open by design:** collapse the 4-step flow if "create" is redundant (`slice2 § Task 4 Step 3`) — later resolved to Garment/Content/**Review**/Download (`slice8 § B11`); and regenerate-on-move vs pass-offsets-through (`slice3 § Task 4`).
- **Photo fixes #6.2 (`summit_badge`, segmentation-merge chaining) and #6.3 (`repro_gradient_white_icon`, post-vectorization colour/geometry desync) left undesigned.** `photo-palette-overflow § Non-goals`. `MASTER_SCOPE.md` confirms both still open.
- **Chaining tier ships OFF by default** with a measured coverage blind spot (up to 29 mm bare cloth on a real fixture) — real, not blocking. `gradient-defects-handoff § Also true`.
- **`BACKGROUND_ENCLOSED` firing on regions that survived stage 1** was queued needing its own design pass. `gradient-defects-handoff § 2`. Closed later (enclosed-background restore + `docs/enclosed-background-verdict-2026-08-15.md`).
- Text-cluster detection itself is **fully landed**, Studio side included (`digitizer_core/textcluster.py`, `text_candidate`, `textConversions` in `App.svelte`/`DigitizePanel.svelte`), including the regularization geometry pass and its skip flag.

## Rejected alternatives

- **Raising `cfg.max_colors` globally** to fix `drone_render` — one global field feeds every design, so it would change thread-change/machine setup cost on flat art too. `photo-palette-overflow § Problem`.
- **Widening the photo region-former's dispatch to include the gradient class** — fixes fragment count, not the shared fill angle, which is the actual reported defect; fit one whole-image ramp model at stage 2 instead (reuse `stage6_blend.detect_ramp` a stage earlier). `gradient-defects-handoff § 1`.
- **Auto-substituting a font for detected text** — a detector with no matching font must never make a design look worse than doing nothing. `text-cluster-design § 1`.
- **Making the text tag an override key** — server-computed facts don't need the override contract. `text-cluster-design § 3.4`.
- **A bespoke inline text editor in `DigitizePanel`** — reuse `TextStep.svelte` wholesale (verified to render correctly for a seeded/empty element). `text-cluster-plan § Step 6`.
- **A customer-facing SAM2 control or in-app setup guidance, and a per-element SAM2 param** — internal/advanced only. `sam2-studio-seam § Design, Non-goals`.
- **The blueprint's ~20-colour chart stub, and found art as fixtures** — replaced by the generated full chart and deterministic synthetic logos (exact structural assertions, no licensing questions). `step1 § Deviations`.
- **Hand-rolled scanline parity for fill** — shapely intersection instead; robustness matters more than speed here. `step3 § Stage 6`.
- **Transposing service coordinates to match the browser DST codec** — buries a disputed convention one layer deeper. `step8 § The axis decision`.
- **Floating-popover ThreadPicker** — clipped by `.panel-body`; expands in-flow. `slice8 § B6`.
- **`window.confirm` for destructive actions** — two-tap arm/disarm with a 300 ms click guard. `slice7 § Task 2, A5`.

## Sequence claims

- **Stitch planning taken before SAM2**, inverting the blueprint: the `Segmenter` ABC makes `SamSegmenter` a later drop-in, and step 3 is the first output that can be sewn and judged — the milestone-3 sew-out gate. `step3 § Sequencing note`.
- **Step 8 (service) is the seam and was pulled early**: it collapses launch item #1 (harden PES, add JEF) via one pyembroidery adapter and reduces step 10 to wiring by building `adapter.py` here. `step8 § Why this step now`.
- **Step 1 fixes the rest of the order:** preflight → 9, SAM → 2, planning/underlay/pull comp → 3-6, export → 3/8, FastAPI → 8, EMB-Bot UI → 10. `step1 § Non-goals`.
- **Text-cluster ordering:** Steps 0-4 (detection, additive) land first and review independently; Step 5 (regularization) is the only golden-moving step; Steps 6-7 (Studio) parallelize once Step 4's contract is stable; `MASTER_SCOPE.md` updated ONCE at the end, never mid-build. `text-cluster-plan § Sizing, Step 8`.
- **Pipeline ordering inside detection:** `detect_text_clusters` runs immediately after `tag_enclosed_background` ("computed fact, before shape edits"); regularization must precede stage 7's `run_outline` call. `text-cluster-plan § Step 0, Step 3`.
- **Gradient handoff:** close the two regressions → then run **M0+M1 of the DT-first migration before photo steps 5+**, because steps 5+ lean harder on satin-vs-fill classification than anything shipped. `gradient-defects-handoff § Sequencing decision`. **Superseded — see Contradictions.**
- **Studio slices are data-model-ordered:** slice3 sizing needs slice2's generate adapters; slice5's v2 element model must precede slice6 (arc/multi-line) and slice7 (registry migrates v1 OR v2); slice8 re-skins last and assumes stable class names.
- **Font import precedes template wiring** — slice4's template spec validates `fontKey`s against the live registry, so Task 3 changing availability breaks Task 4. `slice4 § Task 4`.

## Contradictions

- **DT-first sequencing is dead.** `gradient-defects-handoff § Sequencing decision` makes DT-first M0+M1 the mandatory next slice, and `text-cluster-design § 5` treats M2/M3 as merely corpus-blocked. `MASTER_SCOPE.md § Measured negatives` lists the DT-first classifier swap as built-measured-**rejected** (the printed rule sends 62/83 clean satins to fill), and area 1's Next is satin-vs-fill routing (ruled 2026-08-14). Do not follow the handoff's ordering.
- **"Zero behaviour change outside that pattern"** (`photo-palette-overflow § Effect on other designs`) vs `MASTER_SCOPE.md § Waiting on Kent`, "Turn `split_tonal_regions` on?" (referenced by name — that queue renumbers): `split_tonal_regions` routinely pushes the palette to the `max_colors + PALETTE_OVERFLOW_K` ceiling, so the overflow path becomes ordinary the moment that flag flips (parked until the sew-out; also listed under § Latent — gated OFF).
- **The palette-overflow acceptance criterion is unmet.** The design predicts `drone_render.png` moves off F/0; `MASTER_SCOPE.md` records the landed fix as algorithm-verified-correct but grade-**unchanged** (a preflight pooled-metric gap). MASTER_SCOPE also corrects `repro_gradient_white_icon.png` from F/0 to D/58 — the grade this doc chain propagated.
- **SAM2 "no customer-facing control anywhere, that IS the design"** (`sam2-studio-seam`) vs `PRODUCT.md § Launch posture`: SAM2 returns post-v1 as an opt-in "enhanced photo mode" download, i.e. a customer-facing control is planned; the localStorage seam is only the internal half.
- **Browser DST's standing.** `step8 § The axis decision` asserts Studio's DST default stays the browser encoder *because it has sew-out evidence behind it*, and that Kent has sewn browser-written DSTs. `MASTER_SCOPE.md § No physical sew-out testing has occurred yet` states zero sew-out testing has ever happened anywhere in this project, and separately flags CLAUDE.md's contrary "browser DST is EMB-Bot-internal only". Both cannot hold, and the axis verdict rests on which does.
- **Font count.** `embf-acceptance § Final shipped library` ships 69 fonts / 30.09 MB; `PRODUCT.md` records 55 shipping fonts (one LICENSE sidecar each) after the 2026-08-04 ShareAlike removal. The 69 figure is superseded.
- **Slice 5's "+ Text / + Image" add-row** is contradicted by later rulings: `PRODUCT.md`/`MASTER_SCOPE.md` record draw shapes as a right-click canvas tool "not an upload tile", and the `.eladd-row` overflow gotcha (a clipped "+ Auto-digitize" read as a dead service) came from exactly that row.
- Noted in passing, not from these files: `PRODUCT.md` calls launch item 4 (preset shapes tool) both ✅ Done and "still not started".
