# Memory Index — Archive (before 2026-09-15)

Same one-line format as `MEMORY.md`: `- [Title](file.md) — hook`. These are the
index lines for every note dated before 2026-09-15 (filename date, else the date
the note file was first committed), moved out of the live index on 2026-10-23
because it sat at its 24,986-character ceiling and every PR that added a note
conflicted with every other. **This file is NOT auto-loaded** — open it when you
need history or a standing ruling (fill row spacing 0.15, DST axis fixed,
Ink/Stitch clean-room, the Ember teardowns). The notes themselves have no budget.

Rules: each line stays under 260 chars; every note file in `.claude/memory/` is
indexed in exactly one of this file and `MEMORY.md`
(`digitizer/tests/test_memory_budget.py` enforces both). Order is kept from the
live index; new archive lines go at the bottom.

- [Fritsch's Stitches](fritschs-stitches.md) — Kent's company is an embroidery business; assume that domain, ignore wheel/tire context
- [EMB Bot Digitizer](emb-bot-digitizer.md) — history/decisions/gotchas, NOT live state (MASTER_SCOPE is); standing “flat art in, pro out” rule
- [Ember architecture](ember-architecture.md) — competitor teardown: 2 Next.js apps + iframe, PixiJS/MobX/WASM; no ML in auto-digitize — our opening
- [Ember feature teardown](ember-feature-teardown.md) — manual/pricing teardown; the fill-pattern library and the Bridge app are the biggest gaps
- [Fill density convention](fill-density-convention.md) — Law 19 SETTLED: pro density is between same-direction rows; 0.40 tatami sewed half coverage; satin correct
- [DST codec axis discrepancy](dst-codec-axis-discrepancy.md) — RESOLVED 2026-09-08 with no sew-out: JS DST nibble table was transposed; pre-fix `.dst` re-imports mirrored
- [Ink/Stitch research](inkstitch-research.md) — GPL-3.0: port Ink/Stitch concepts clean-room, never code; `pystitch` (MIT) is copy-safe; read the doc first
- [Pro trim threshold](pro-trim-threshold.md) — CORRECTED 10-21: the "16.1 mm floats" were needle-DOWN hops; the pro cuts every jump, we leave 1-3 mm ones
- [Real-artwork parity](real-artwork-parity.md) — honest baseline 42.5; a pro scores only 75-84 vs a pro, so 95 is above the ceiling; synthetic refs flatter
- [Satin gate attribution](satin-gate-attribution.md) — DT regularity loses pro satin ground; `explained` promotion 45.8 → 48.1; flat-art sub-1mm floor DISPROVED
- [Windows goldens fail locally](windows-goldens-fail-locally.md) — golden set MOVES per-fixture; CORRECTED 2026-08-22: Linux fails CI's three; never re-capture on Windows
- [Digitizer local env](digitizer-local-env.md) — Kent's box: no tesseract so OCR tests skip; rembg venv EXISTS per-checkout, inert outside photo classes
- [Satin extremity drop and coverage check](satin-extremity-drop-and-coverage-check.md) — FIXED 2026-08-21: `_prune_spurs` cascade silently dropped satin tabs; `ARTWORK_UNCOVERED` catches it
- [Real-artwork trim truth](real-artwork-trim-truth.md) — read before any trim work: `chain_links` -33% is the one large lever; "real logos rarely cut" is TAINTED
- [Sew-out accepted as-is](sew-out-accepted-as-is.md) — Kent ruled the sew-out accepted as-is, NOT a to-do; gate 1 is a STANDING refusal; `split_tonal_regions` open
- [Hotel Fremont pro-parity findings](hotel-fremont-pro-parity-findings.md) — UNREPRESENTATIVE fixture: reproduce defects, never size fixes; `forced_class=flat` makes it WORSE
- [Font pipeline silent failures](font-pipeline-silent-failures.md) — font defects report healthy numbers; RENDER AND LOOK finds what tests miss; a guard must assert its reach
- [Cache seam, photo floor, environment betrayals](cache-seam-photo-floor-2026-08-22.md) — Drive photo channel MEASURED BROKEN; proxied downloads lie, check Content-Length
- [The first real photographs](first-real-photos-2026-08-23.md) — four family photos: four defects no fixture could reach; 3 FIXED, `_shade_layers` palette escape left OPEN
- [The renderer that made the real defect visible](thread-render-and-background-stitches-2026-08-24.md) — sheets were VECTOR PROOFS hiding 72% background sewing (FIXED)
- [Faces overturn the fill ruling](faces-overturn-the-fill-ruling-2026-08-25.md) — filled quantizes a face to one skin field — faces TABLED; Kent chose EXIF-or-face AUTO-DETECT
- [The Studio's display layer](studio-display-layer-2026-08-25.md) — 787 green specs missed a white-on-white primary CTA. Drive the real app and read COMPUTED styles
- [Why the letters are botched](letterform-fidelity-2026-08-26.md) — NO single root cause — four measured mechanisms; coverage and IoU cannot see a wrong-angle letter
- [Art-fidelity self instrument, rebuilt from its artifact](artfidelity-self-rebuild-2026-08-27.md) — cloud container: UNPUSHED IS DELETED. Weights solved by least squares
- [Curve fidelity from the stitch path](curve-fidelity-from-stitch-path-2026-08-27.md) — the raster IS a polygon — read curves from `plan.iter_runs()`; `roughness_deg` is the per-design number
- [Four thresholds on the wrong population](thresholds-on-the-wrong-population-2026-08-28.md) — a threshold calibrated on one population, applied to another, four times. Tell: a gate finds NOTHING
- [Kent's eye vs the instruments](kent-eye-vs-instruments-2026-08-27.md) — Kent: 60% of Ember parity; instruments 83.7/80.0. ARTFID is a FIDELITY score, never a quality percentage
- [Does the yardstick agree with Kent's eye?](../../docs/yardstick-vs-kents-eye-2026-08-28.md) — phase-1 exit question, NOT settled (n = 6). Element COUNT matches his judgement, AREA does not
- [The first physical stitch-out](first-physical-sewout-2026-09-01.md) — Instagram icon sewn, 6/10. Density UNSETTLED — two readings disagree 2x; quote only `tools/fill_pitch.py`
- [Worktree add with empty var wipes cwd](worktree-add-empty-var-wipes-cwd.md) — `git worktree add` with an EMPTY path var, run inside a lane, wipes the checkout; commits survive
- [Worktree venv and baselines](worktree-venv-and-baselines.md) — worktrees have NO `.venv` — run main's python, cwd in the worktree; main is NEVER a baseline
- [The baseline was sound, and a shallow clone said otherwise](baseline-attribution-and-studio-ui-2026-09-02.md) — RETRACTED: a SHALLOW clone misattributed the capture
- [Hotel Fremont fine details](hotel-fremont-fine-details-2026-09-02.md) — house angle NOT FIRING: slab serifs cancel in doubled-angle space, the 4th wrong-population case; fix is four-fold
- [Round curves](round-curves-2026-09-03.md) — defect 22 `curve_turn_deg` ON at `_CURVE_MIN_EPS_PX` 4; defect 25 under it: float dust halving fills, FIXED
- [Classifier stability](classifier-stability-2026-09-03.md) — MEASURED NEGATIVE, no engine change: 5 of 219 verdicts flip under boundary detail; eight cures all fail
- [Rail dents](rail-dents-2026-09-03.md) — defect 23 FIXED; open half `satin_rails_follow_edge` OFF (Kent). “In every golden” was a bar artefact
- [Stitch-angle convention](stitch-angle-convention-2026-09-03.md) — ADOPTED by Kent, built: lean cap 30 deg, spacing/cos, stems square to the LINE OF TEXT, Goldman join; four-fold ON
- [Fill travel under cover](fill-travel-under-cover-2026-09-03.md) — defect 21 FIXED, ON by Kent's flip: routing alone moved NOTHING — column ORDER decides exposure
- [Fine-lettering design review](fine-lettering-design-review-2026-09-03.md) — “Embroidery 101” IS Laws 45-58, gaps were enforcement; defect 24 FIXED in both engines; bold guard kept
- [The pro's files refute the scale-limit story](pro-files-refute-scale-limit-2026-09-03.md) — the pro sews Fremont's tagline legibly at 92.5 mm — “too small to sew” REFUTED
- [The five sew-out findings, density read as rows](sewout-five-points-2026-09-03.md) — Pro fills as ROWS: 0.14-0.17 mm pitch; per-pass `fill_pitch.py` over-reads a pro ~2.7x — never quote it
- [Fill row spacing settled at 0.15](fill-row-ruling-2026-09-03.md) — Kent RULED `FILL_ROW_MM` 0.40 to 0.15; older coverage numbers read 2.67x smaller; rings held at 0.40
- [Seams: instrument, card block 6, blend underlap](seams-2026-09-03.md) — `tools/seam_underlap.py` reads sewn seam depth; Fremont falls short — hole-held shapes get no tongue
- [The satin raster ate every counter's edge](satin-hole-raster-2026-09-04.md) — `cv2.fillPoly` paints boundary pixels: holes lost half a pixel, rails 0.18 mm short — FIXED (`hole_px`)
- [The gradient ruling: one region when the design ramp fits](gradient-ruling-2026-09-04.md) — RULING: one region when `design_ramp.py`'s plane gate passes — never gate on the colour profile
- [The day the instruments were the defect](instruments-that-underreport-2026-09-06.md) — The score SATURATES at 0; a floored grade is no evidence either way. Read before quoting a grade
- [The seam nothing guards, and what it says to customers](code-seam-and-customer-voice-2026-09-07.md) — a SWEEP is judged on yield, a TRIPWIRE on failure cost; `test_code_wires.py`
- [A warning that read like a ruined job, bounded to nil](palette-mismatch-bounded-2026-09-07.md) — blast radius NIL; a warning's severity is set by its CONSUMERS
- [Run the app — the screenshot found what reading did not](run-the-app-color-cap-2026-09-07.md) — slider max 6 vs caption 13 colors: run the app before judging by reading
- [Eight PRs: the DST axis, and a number the app asserted](slider-vs-design-and-the-axis-fix-2026-09-08.md) — DST axis FIXED both halves; for an ORIENTATION claim render it
- [Quality review 2026-09-08](quality-review-2026-09-08.md) — Fourteen ranked changes and build log; item 1 BLOCKED on Kent's tonal art. Read before digitizing work
- [Border seam ownership](border-seam-ownership-2026-09-09.md) — Kent RULED the colour sewn ON TOP owns a shared seam; the shape beneath skips it as open arcs
- [The border on the canvas](canvas-border-menu-2026-09-09.md) — Right-click Add/Remove border on the canvas over the per-shape `border` override; satin tier never borders
- [Wide columns in the lettering engine](wide-columns-lettering-2026-09-11.md) — 80 of 85 fonts broke a DST record; Kent RULED `splitSatin` ON, `wideColumnFill` off — 9 cross-stitch remain
- [Stale diagnostics, two flips, and a bill that oscillates](stale-diagnostics-and-two-flips-2026-09-13.md) — A diagnostic on today's defaults goes stale once its fix ships — pin to `PRE_FLIP`
- [Tooling research, and a chaining gate already met](tooling-research-and-the-chaining-gate-2026-09-13.md) — No repo/MCP/plugin helps (don't re-search); vendors publish NO trim rule
- [The gap audit and the sourcing sweep](gap-audit-and-external-sourcing-2026-09-12.md) — 73 agents, 2 real defects the self-comparing suite missed; agents must RUN things; verify dies first
- [The display revamp, and a fleet that outran its budget](display-revamp-and-a-fleet-that-outran-its-budget-2026-09-16.md) — `kind` is an OPEN set of eight
- [The index that stopped loading its newest entries](memory-index-overflow-2026-09-15.md) — 24,986-CHAR ceiling drops the NEWEST entries; reclaim HOOKS, never entries
- [The foundation review and the eye-pairs build](eye-pairs-build-2026-09-17.md) — Kent picked F4; `tools/eye_pairs` built in one session; `uncovered_wanted_mm2` is a DENOMINATOR; spike first
- [Photo edit tail 2026-09-17](photo-edit-tail-2026-09-17.md) — `fill_travel_under_cover` is ~58% of a photo edit tail; the reorder memo is exact ONLY while both stay pure
