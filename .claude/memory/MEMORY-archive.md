# Memory Index — Archive (through 2026-10-06)

Same one-line format as `MEMORY.md`: `- [Title](file.md) — hook`. These are the
index lines for every note dated through 2026-10-04 (filename date, else the date
the note file was first committed), moved out of the live index on 2026-10-23 (and
again on 2026-10-26, through 2026-09-21, and on 2026-10-27, through 2026-10-04 and then 2026-10-06,
oldest filename date first) because it sat at its 24,986-character
ceiling and every PR that added a note conflicted with every other. **This file is NOT auto-loaded** — open it when you
need history or a standing ruling (fill row spacing 0.15, DST axis fixed,
Ink/Stitch clean-room, the Ember teardowns). The notes themselves have no budget.

Rules: each line stays under 260 chars; every note file in `.claude/memory/` is
indexed in exactly one of this file and `MEMORY.md`
(`digitizer/tests/test_memory_budget.py` enforces both). Order is kept from the
live index; new archive lines go at the bottom.

- [Browser fill lane state](embot-browser-fill-lane-state.md) — SNAPSHOT 10-03: #606/#609/#611 built OFF, flips Kent's; island fix #613 merged PRE-audit, cures in #620; cleanup only Kent can run
- [Closed-ring lane](embot-closed-ring-lane.md) — SNAPSHOT: #621 `offsetRing` on a repeated point, #625 stacked on it; defect 55's offset half is Kent's call
- [Handover numbers and stacked branches](embot-handover-numbers-and-stacked-branches.md) — SNAPSHOT: reproduce a handed-over number with its own script
- [Star-walk lane](embot-star-walk-lane.md) — SNAPSHOT: #624 ends `skeletonEdges`' endless walk; defect 57's cure order waits on Kent
- [Sub-unit stitches lane](embot-sub-unit-stitches-lane.md) — SNAPSHOT 10-04: `dedupeHoles` built OFF (#623), Kent's "new flag, every run"
- [Fritsch's Stitches](fritschs-stitches.md) — Kent's company is an embroidery business; assume that domain, ignore wheel/tire context
- [EMB Bot Digitizer](emb-bot-digitizer.md) — history/decisions/gotchas, NOT live state (MASTER_SCOPE is); standing “flat art in, pro out” rule
- [Ember architecture](ember-architecture.md) — competitor teardown: 2 Next.js apps + iframe, PixiJS/MobX/WASM; no ML in auto-digitize — our opening
- [Ember feature teardown](ember-feature-teardown.md) — manual/pricing teardown; the fill-pattern library and the Bridge app are the biggest gaps
- [Fill density convention](fill-density-convention.md) — Law 19 SETTLED: pro density is between same-direction rows; 0.40 tatami sewed half coverage; satin correct
- [DST codec axis discrepancy](dst-codec-axis-discrepancy.md) — RESOLVED 2026-09-08 with no sew-out: JS DST nibble table was transposed; pre-fix `.dst` re-imports mirrored
- [Ink/Stitch research](inkstitch-research.md) — GPL-3.0: port Ink/Stitch concepts clean-room, never code; `pystitch` (MIT) is copy-safe; read the doc first
- [Letterform priors lane](letterform-priors-lane-2026-10-06.md) — "something new" on lettering was yesterday's lane (outline-cut); check sibling lanes before proposing new
- [Fremont letters are not thicker than the pro's](lettering-thickness-fremont-2026-10-06.md) — file width = pro's (1.23 vs 1.40 scaled)
- [Pro trim threshold](pro-trim-threshold.md) — CORRECTED 10-21: the "16.1 mm floats" were needle-DOWN hops; the pro cuts every jump, we leave 1-3 mm ones
- [Real-artwork parity](real-artwork-parity.md) — honest baseline 42.5; a pro scores only 75-84 vs a pro, so 95 is above the ceiling; synthetic refs flatter
- [Satin gate attribution](satin-gate-attribution.md) — DT regularity loses pro satin ground; `explained` promotion 45.8 → 48.1; flat-art sub-1mm floor DISPROVED
- [Underlay under fills](underlay-under-fills-2026-10-05.md) — gradient fills sewed with ZERO underlay; pro sews a crossing pass, built as `cross_tatami`, in no preset; preview cannot show underlay
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
- [A concurrent session designed the same tool](concurrent-session-designed-the-same-tool-2026-09-17.md) — check branches + live sessions FIRST
- [The foundation review and the eye-pairs build](eye-pairs-build-2026-09-17.md) — Kent picked F4; `tools/eye_pairs` built in one session; `uncovered_wanted_mm2` is a DENOMINATOR; spike first
- [Photo edit tail 2026-09-17](photo-edit-tail-2026-09-17.md) — `fill_travel_under_cover` is ~58% of a photo edit tail; the reorder memo is exact ONLY while both stay pure
- [Worktree session: the harness guard](worktree-session-harness-guard-2026-09-17.md) — `digitizer` spells `git`: quotes, `cd` chains refused; venv by 8.3 `CLAUDE~4`; preview_start reads MAIN
- [Eye pairs, the follow-up](eye-pairs-followup-2026-09-18.md) — "merged" was OPEN and red; a test red only where tesseract EXISTS; the MERGE REF alone broke a word budget
- [Flag Before After: the labelled page, found and finished](flag-before-after-2026-09-18.md) — the scratch copy is `--labelled` now; re-read the db just before a SAME-URL republish
- [The staircase on low-res uploads](native-ramp-edge-read-2026-09-18.md) — 0.68 mm stairs: NEAREST-upscaled alpha; `subpixel_edges_upscaled` ON (Kent); byte-identity is an EXPRESSION
- [Six pending flags, invisible at viewing size](six-flags-invisible-at-viewing-size-2026-09-18.md) — Kent: 29 of 34 pairs "no difference"; all six stay OFF, not the Ember-gap lever
- [The Studio never sent the file](../../DOCTRINE.md) — 1,200-px canvas re-encode rewrote RGB under alpha (Becker 59→175 trims); FIXED 09-20; `alpha_edge_extend` ON
- [Run-button commands need absolute paths](run-button-commands-need-absolute-paths.md) — Run buttons share ONE PowerShell whose cwd persists; `cd digitizer` works once — give an absolute cd
- [Lettering route review](../../docs/lettering-route-review-2026-09-19.md) — trace-as-shape stays: font ID is dead (IoU 0.9 = a WRONG font); the gap is CONSTRUCTION (41 vs 3 trims)
- [Junction construction plan](../../docs/superpowers/plans/2026-09-19-junction-construction.md) — folds are welds through 30-60° corners; `satin_junction_stack` ON refuses them (R 311→0)
- [Lettering construction plan](../../docs/superpowers/plans/2026-09-19-lettering-construction.md) — Kent: trace + font-engine rules; all built, ON but 3b (skeleton RULED, owes sew-out)
- [Cap order, and a pair experiment](cap-order-and-the-pair-experiment-2026-09-19.md) — `cap_center_out` parked OFF: the pro's cap/LC pairs of one artwork (a controlled experiment) back bottom-up
- [Edge wobble is satin rails](edge-wobble-is-satin-rails-2026-09-19.md) — "right shapes, bad edges": outline clean (0.011 mm), SATIN RAILS wobble ~0.10 mm; run `edge_wobble.py` first
- [Exposed travel is the fill tier's](exposed-travel-is-the-fill-tier-2026-09-19.md) — `travel_cover`'s 245 mm is defect 21, not gate 3 (fill bridges, 0.0 on fabric); `fill_bridge_cut` ON (Kent)
- [lost_frac is two metrics](lost-frac-is-two-metrics-2026-09-20.md) — `lost_frac` sums two OPPOSITE defects; enthusiast is 100% overshoot, no ink lost. Never quote its MAGNITUDE
- [Preview vs the file it hands over](preview-vs-file-split-dogleg-2026-09-20.md) — preview matches the .dst exactly; the split walked an L on diagonals (FIXED); axis-aligned fixtures hid it
- [Rail wobble is the model's floor](rail-wobble-is-the-models-floor-2026-09-21.md) — satin 0.089 mm is the rail model's FLOOR; do not tune its six defences. Mean OUTWARD, tail inward
- [bridge: border and script](bridge-border-and-script-2026-09-30.md) — on/off border = JPEG halo (the dissolve folds it); script is not text; Kent's lever `SATIN_GAPS_TIGHT`
- [The built-OFF sitting](built-off-sitting-2026-10-03.md) — `patch_junctions` had shipped already: render vs shipped first. Kent: `cap_recentre` ON, `bean_letters` OFF
- [Check what shipped before building it](check-shipped-before-building-2026-09-29.md) — Kent asked for a manual digitizer that had shipped; grep MASTER_SCOPE/PRODUCT, offer "show me", drive it
- [Column width on resize](column-width-on-resize-2026-10-01.md) — ruling 12: drawn width scales, pull comp fixed; store `widthPx`, mm is a view; no clamp
- [Envelope junction escapes](envelope-junction-escapes-2026-09-30.md) — Kent's "fill a void": escapes refused, teeth dropped; the pro flows: BACK STITCHING; holes = the comb split
- [Fill columns: thread across holes](fill-columns-2026-10-03.md) — JS fill floated across every hole, unseen by its test; `fillColumns` built OFF, unsewn. Audit BEFORE arming
- [Row stagger for the browser fill](fill-stagger-2026-10-03.md) — JS fill holes lined up 94%; `fillStagger` built OFF (Kent's flip), +7% stitches. A channel is 3 rows, not 2
- [Fine detail and the work grid](fine-detail-work-grid-2026-09-30.md) — "RESTAURANT" was lost to the tracer's 4 px/mm grid, not the file; `work_px_per_mm` ON at 8 (Kent 10-01)
- [Instagram: gradient lane, not classifier](instagram-gradient-lane-edges-2026-09-30.md) — real IG file classifies gradient CORRECTLY; the SLIC lane's edges were the defect, snap ON. Render first
- [Lock stitches, both JS builders](lock-stitches-2026-10-03.md) — `ties` built OFF for shapes too; the 09-14 lettering lock leg was 0.8 PIXELS. Assert lengths in OUTPUT units
- [The orphan-lane sweep](orphan-lane-sweep-2026-09-30.md) — `pro-overlay-diff` PARKED (Kent); squash merges blind `main..lane`, count added lines; Developer Mode ON
- [Second sitting: eleven flags and the 08-27 engine](second-sitting-eleven-flags-2026-09-28.md) — Kent: "VERY hard to tell"; today beats 08-27 on 7 of 9; `rail_comp` ON 09-29, envelope ON 09-30
- [SEEDS unservable request, and the worktree blind spot](seeds-request-and-the-worktree-blind-spot-2026-09-22.md) — a worktree lacks the rembg venv (DIFFERENT pipeline)
- [Split comb per column](split-comb-2026-09-30.md) — per-leg comb flickered on Becker's letters; `_comb_thresholds` 122 → 37; raising 5.0 is a sew-out (gate 1)
- [Studio configurator redesign](studio-configurator-pr1-2026-09-30.md) — wizard → Tesla panel: all four PRs built; PR 3 = Advanced fold (hidden, not removed); Original view still open
- [WITHDRAWN: warn sooner on small files](warn-sooner-small-files-handoff-2026-10-01.md) — Kent 10-02: no warnings, the engine takes the path; replaced by bean letters, built OFF in PR #601
- [Worktree guard judges targets](worktree-guard-judges-targets-2026-10-04.md) — rm/mv guard judges the resolved TARGET; own-lane deletes allowed (Kent 10-04)
- [Wrong-root sessions, global guards](wrong-root-sessions-and-global-guards-2026-10-04.md) — sessions rooted outside the repo ran with no project hooks; `embot-guards-global.js` covers them
- [Build what was priced](build-what-was-priced.md) — SNAPSHOT: after Kent picks a priced option, build exactly that
- [Parallel agent with the embot](parallel-agent-with-embot.md) — SNAPSHOT: audit before a PR is OPEN, not just before arming; never `git stash` in a lane; a stacked PR targets main and says so
