# scope-history digest — decisions, reversals, ordering

Source for every item: `docs/scope-history.md`, cited as `[sh · <dated entry>]`. No status, counts or measurements carried forward — that file's numbers are dated snapshots by design.

## Kent's rulings

- **2026-08-14 (evening)** — rescale the pro-parity scorecard to chance-corrected NOW, accepting that every historical number moves, so the satin-vs-fill routing work is measured on an honest scale from the start instead of needing a re-baseline mid-flight. `[sh · 2026-08-14 (evening)]`
- **2026-08-13 (evening)** — "remove all of the unnecessary upload buttons": the Content step is three tiles (Text · Artwork · Design file); his own amendment keeps Draw-shapes as a right-click canvas menu rather than a tile. `[sh · 2026-08-13 (evening)]`
- **2026-08-12** — multi-thread shading gets fixed **upstream**: split tonally-diverse regions at segmentation time so the existing one-thread-per-region model carries them. Rejected teaching stage 5/7 that one region owns several thread stops — blast radius, and new downstream machinery. `[sh · 2026-08-12 (late)]`
- **2026-08-12** — "option A": a darkness-based fallback at `stage6_blend.blend_fill`'s `model is None` branch so a ramp-less region still decomposes into 3–5 tatami-filled shades. Option B (subject-relative streamline `d_sep`) rejected — not actually cheaper, lower ceiling. `[sh · 2026-08-12 (evening)]`
- **2026-08-12** — the real photo's provenance is not a concern; `owl_kent.jpg` is cleared to land as a corpus fixture. `[sh · 2026-08-12 (evening)]`
- **2026-08-11 (late)** — engine quality is a **parallel investment, not a launch gate**; SAM2 ships post-v1 as an opt-in download. `[sh · 2026-08-11 (late)]`
- **2026-08-07** — do **not** auto-restore large enclosed backgrounds by default (it risks silently filling a genuinely intended hole); keep the safe per-shape default and make restoring fast and obvious instead. `[sh · 2026-08-07 (Instagram icon)]`
- **2026-08-06** — chose satin entry/exit selection by corpus laws 27–29 over the two alternatives also offered (border seam-sharing, appliqué cover pull-comp). `[sh · 2026-08-06 (satin entry/exit)]`
- **2026-08-04** — pull all 13 ShareAlike fonts rather than wait on the lawyer consult (consult becomes optional, brief kept as the restore path); also delete `EMB-Bot-standalone.html` outright. `[sh · Resolved cross-cutting: Font license compliance gap]`
- **Standing, deferred to Kent** — `COVERAGE_BLOCK_UNITS` stays untouched: sew-out-gated, not desk-safe, pending his physical stacked-fill-ladder test. `[sh · 2026-08-05 (laws 23/26 landed)]`

## Reversals and disproved conclusions

- **`blend_tonal_bands` — BUILT, MEASURED, REMOVED.** Fill-tier banding decomposed the geometry correctly and changed nothing visible, because the shades still shared one thread. Recorded explicitly "so nobody rebuilds it." `[sh · 2026-08-12 (late)]`
- **"The shade machinery is fine, the gate is the problem" (PR #125) — RESET.** `stage7_sequence` never reads `shade_thread_idx`/`shade_rgb`; a block's thread is the region's one thread, so removing the r² gate buys no shading at all. `[sh · 2026-08-12 (late)]`
- **`streamline_mode: "layered"` row-pitch bug — DISPROVED.** Layered is consistently *denser* than streamline-mono; the "sparser" reading came from comparing it against **tatami**, a different tier class. "No fix needed; do not go looking for one." `[sh · 2026-08-12 (late), closed 2026-08-13]`
- **`_speckle_ratio` "scale-broken" — WITHDRAWN.** It is an unnormalised Laplacian-gain ratio, not a 0–1 ratio, and discriminates correctly at the shipped threshold. Kept struck through as the second case of a hedged observation hardening into a "defect" through re-copying. `[sh · 2026-08-14]`
- **The "thread drift defect" — NOT an independent defect.** A region's own internal colour spread sets the error floor; `stage4_vectorize`'s re-snap has almost nothing left to win. "Do not spend time on the re-snap code itself." `[sh · 2026-08-12 (evening)]`
- **Three photo hypotheses disproven**, all extrapolated from a synthetic near-featureless blob fixture: palette collapse merging subject into background; `max_colors` being the binding constraint; `MERGE_DELTAE00_THRESH` needing a retune — **leave 26.0 alone**, a global change costs more than it gains. `[sh · 2026-08-12 (evening)]`
- **Photo-quality fix #6.2 — REFUTED on measurement and NOT built.** `[sh · 2026-08-11 (evening)]`
- **DT-first classifier architecture swap — measured NEGATIVE.** The patented rule as printed routes most clean satins to fill; corrected arms lose every disagreement they create. `[sh · 2026-08-12 (small hours)]`
- **SAM2 `max_side_px` 1024 → 512 — TRIED, REJECTED.** Not the same masks (region count drops reproducibly) and the wall-clock saving sits inside this box's timing noise. Stays 1024. `[sh · 2026-08-11 (later same day)]`
- **Don't swap the SAM model.** In automatic-mask mode the encoder is a small share of per-image cost and the `points_per_side²` decode loop nearly all of it, while every lightweight SAM variant optimizes the encoder; SAM 1 is heavier. FastSAM is AGPL-3.0 despite its README, EdgeSAM non-commercial — both disqualified, same category as the `bria-rmbg` rejection (those license reads were never independently re-verified). `[sh · 2026-08-11 (later same day)]`
- **Forcing the flat lane on textured logo art makes it WORSE** — k-means shatters texture; the gap needs an edge-preserving flatten instead. `[sh · 2026-08-13 (evening)]`
- **The SEEDS/`summit_badge` root cause was WRONG, and the `AREA_RATIO_*` constant family is the wrong tool.** The complex dies in one big-into-big merge, not a chain of diluted small edges; area-ratio protection is blind to that by construction and no value of it decouples protection from ordinary band consolidation — every re-derivation either did nothing or broke already-validated fixtures. Fixed instead by a boundary-contrast measure. A third discriminator (per-region internal Lab spread) worked equally well and was **rejected and recorded** in the constant's docstring so it is not re-derived. `[sh · 2026-08-07 (seeds-boundary-contrast-fix)]`
- **The "E missing its corner" defect was NOT in the junction/cap machinery.** `_extend_to_cap`, `_retract_cap_corner` and `_merge_through_junctions` all traced innocent; the cause was `_short_stitch_guard`'s pull-toward-middle dragging a near-floor cross under `SATIN_MIN_CROSS_MM`. The companion "N reads short" symptom was confirmed **not present**. `[sh · 2026-08-07 (E corner FIXED)]`
- **The "A" missing its counter was NOT a text-cluster bug** — those letters never enter `textcluster.py`; the cause was `stage3_segment.resolve_small_regions` absorbing a real enclosed hole. Separately, `regularize_text_clusters`' unconditional skeleton-buffer redraw was itself the bug (crude redraw over already-good letterforms, structurally cannot reproduce an interior hole), and the old test asserting "every member regularizes" was rewritten. `[sh · 2026-08-06 (5 letterform defects)]`
- **MSER investigated and deliberately NOT built** — it returns zero regions on flat few-colour vector art, which structurally lacks the intensity gradient its stability sweep needs. `[sh · 2026-08-07 (textcluster strengthening)]`
- **`jersey_tee` `center_run` fill underlay — DECLINED after measurement.** A centre line sits as far from off-axis interior points as a perimeter walk; only a lattice pass closes the gap, and law 26 is exactly why lattice was removed as this fabric's default. `edge_run` stays; the interior gap is inherent to sparse running-line underlay, not a preset defect. `[sh · 2026-08-06 (jersey_tee follow-up)]`
- **Satin self-overlap: two hypotheses tried and disproven** — "junction merged-footprint DT", and the local-neighbourhood-outlier cap built on it (zero effect, because a genuine continuous taper has no isolated station). Fixed by a flat per-station ceiling reusing `SATIN_MAX_WIDTH_MM`. `[sh · 2026-08-05 (satin self-overlap FIXED)]`
- **Per-station narrowing of the oversize-satin underlay skip — IMPLEMENTED, then REVERTED before landing.** PR #60's classifier-level DT check already resolved the fixture that motivated it, so the narrowing was moot; the simpler whole-stroke skip is the final state. `[sh · 2026-08-05 (follow-up correction)]`
- **Corpus laws 23 and 26 — APPLIED, fully REVERTED, then landed later.** `pique_knit` is the default fabric, so the first attempt moved hard byte-identical goldens across three test files and silenced a real customer-facing stabilizer warning. They landed only once `COVERAGE_WARN_UNITS`' **methodology** was re-derived off non-circular sources — the value never moved, only its provenance. `[sh · 2026-08-04 (two corpus-law fixes reverted) → 2026-08-05 (laws landed)]`
- **The satin/fill classifier's flat-art exemption was DELETED** — the premise "flat art's boundaries are clean" was empirically false on the repo's own benchmark (the exempted rule satin-stitched two real shapes into a starburst). The DT check now runs unconditionally. `[sh · 2026-08-06 (classifier extended to flat)]`
- **`feat/svg-import-shapes` evaluated and NOT resumed.** Only its tokenizer task is complete; its bezier flattening genuinely fails its own tolerance. Reconciling ~277 commits of drift against known-broken code is closer to a fresh build than a resume — treat as a fresh plan if the need returns. Branch left in place; deleting it is Kent's call. `[sh · 2026-08-07 (backlog cleanup item 2)]`
- **Splitting area 1 into separate "image analysis" / "stitch planning" areas — considered and explicitly rejected**; they are pipeline stages of one system, not separately shippable products. `[sh · 2026-08-05 (text-cluster pass)]`
- **A whole SAM2 on/off comparison was published that never touched SAM2** — a clipped `.eladd-row` hid "+ Auto-digitize" and the work silently ran through the browser engine. Recorded as a bug *class*: a UI affordance that gates on service health fails indistinguishably from the service itself. `[sh · 2026-08-12 (evening)]`
- **Not a defect, recorded so it isn't re-found:** the speckle-named blend fallback test never reaches the speckle gate — r² is tested first and random noise fails it. `[sh · 2026-08-12 (late)]`

## Sequence claims

- The scorecard rescale was done **before** the satin-vs-fill routing work, deliberately, so routing would not need a re-baseline halfway through. `[sh · 2026-08-14 (evening)]`
- Gate removal and threads-reaching-the-machine: **both halves have to land before either is visible**. `[sh · 2026-08-12 (late)]`
- Option A's darkness-field → per-shade-geometry step: **write the design before the code** — this is where a wrong choice gets expensive; a named-fixture corpus run plus a before/after is the acceptance bar. `[sh · 2026-08-12 (evening)]`
- Closing the auto-digitize-vs-pro gap needs an **edge-preserving flatten BEFORE region forming**, plus the pro-file side-by-side. `[sh · 2026-08-13 (evening)]`
- Border seam-sharing **cannot be built until a design sign-off decides which shape wins a shared edge**. `[sh · 2026-08-06 (satin entry/exit)]`
- The SEEDS superpixel swap was gated: **do not raise its confidence and do not merge the branch until the `summit_badge` regression is resolved with real numbers.** `[sh · 2026-08-07 (SEEDS draft PR)]`
- Laws 23/26 were blocked on the coverage-budget calibration being re-derived first. `[sh · 2026-08-05 (laws 23/26 landed)]`
- The OCR-confidence gate branch was **stacked on** the selective-regularization branch and could not collapse to its own diff until that one merged. `[sh · 2026-08-07 (OCR gate, "Not yet merged")]`
- The eyes/skin class multipliers ran at a flat 1.0 **until step 3's face priors existed**; real YuNet detection unblocked them. `[sh · 2026-08-04 (CI + photo-plan wave)]`
- Photo-plan row 1 (rembg background removal) was blocked on a `numba`-vs-`numpy` pin and shipped only via an isolated-venv subprocess seam, not by touching the shared venv. `[sh · 2026-08-04 (PR #43)]`
- **From the day CI existed, every PR is gated on its Actions run going green before merge** — not on local suite passes. `[sh · 2026-08-04 (CI now exists)]`
- `chain_links` stays default False **pending the sew-out**; `detail_layer` and `split_tonal_regions` promotion to default each **want a corpus run first**; the stage-7 sub-millimetre-satin reroute is gated on a threshold sweep **plus** the sew-out. `[sh · 2026-08-11 (late), 2026-08-12 (evening / late / small hours)]`
- The `points_per_side=12` A/B harness exists and is **waiting on the image file only**. `[sh · 2026-08-11 (evening)]`
- Remaining launch work after the hoop picker and shapes tool: the starter design pack (needs licensed designs) and the billing session. `[sh · 2026-08-11 (late)]`

## Still-open threads

- **Option A itself** — tatami + shade bands at the `model is None` branch: scoped in detail, deliberately not started, flagged "START A FRESH SESSION HERE". `[sh · 2026-08-12 (evening)]`
- `split_tonal_regions` exists but is **left OFF**, pending a corpus run and Kent's read on the stitch-count trade; its dominant cost is structural (scattered tonal buckets → more regions → more perimeter), not an untuned parameter. `[sh · 2026-08-12 (late)]`
- Jump-trims on an 80 mm design — "still open, not started", present in every variant measured. `[sh · 2026-08-12 (evening)]`
- The `becker logo.png` auto-vs-pro side-by-side — **waiting on Kent for the source art and the pro DST/PES**. `[sh · 2026-08-13 (evening)]`
- SAM2's second risk: `points_per_side=12` validated only against a synthetic stub, never against the real photo that justified keeping SAM2. `[sh · 2026-08-11 (evening)]`
- No **width floor under satin** in the stage-7 ladder; sub-millimetre satin is being emitted and the reroute is proposed, not built. `[sh · 2026-08-12 (small hours)]`
- Ramp-angle detection declines on full-bleed gradient prep at the new defaults; needs a no-flood design-mask path — logged as a follow-up. `[sh · 2026-08-12 (small hours)]`
- Two accepted residuals of the background-flood guards: a tighter crop where the subject owns all four corners still floods **silently**, and edge-bleed flat art can false-positive into stitch-everything-plus-warn. `[sh · 2026-08-11 (late)]`
- Stage-5-dropped split-shape pieces still count as areal cover — verifier finding, logged for follow-up. `[sh · 2026-08-11 (late)]`
- SVG import is in the engine but its **Studio UI wiring** (ImagePanel accept path, shape-pack picker) is not done; a true SVG-file import — preserving an existing vector file's exact paths, as distinct from hand-drawing — remains an uncovered use case. `[sh · 2026-08-11 (late), 2026-08-07 (backlog item 2)]`
- **Physical sew-out testing: still zero** — and several decisions are explicitly gated on it (`COVERAGE_BLOCK_UNITS`, `chain_links`, the satin width-floor reroute). `[sh · 2026-08-04 (verification pass)]`
- Corpus law 28's finer end-CLASS ordering (cap > tee > corner ≈ butt) not implemented — `Stroke` carries only the binary free/not-free distinction. `[sh · 2026-08-06 (satin entry/exit)]`
- Border seam-sharing and appliqué cover pull-comp: both still open, not chosen. `[sh · 2026-08-06 (satin entry/exit)]`
- Shape **splitting and merging** untouched — the boundary editor closed only half the original shape-recognition gap. `[sh · 2026-08-05 (boundary-editor slice)]`
- `pystitch` flagged as a concrete but **not-yet-evaluated** `pyembroidery` replacement candidate; the satin `contour` underlay style gap is confirmed and unfilled. `[sh · 2026-08-10 (Ink/Stitch teardown)]`
- The bluenesia permission screenshots remain parked for Kent. `[sh · Resolved cross-cutting: Font license compliance gap]`
