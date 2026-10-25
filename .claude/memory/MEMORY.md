# Memory Index

One line per memory: `- [Title](file.md) — hook`; the hook only helps you decide
whether to open the file. **Keep every line under 260 chars and this file under
24,986 CHARACTERS** (not bytes); `digitizer/tests/test_memory_budget.py` enforces
both. Past the ceiling the loader drops entries from the BOTTOM with no error:
the newest memories stop existing (2026-09-15: 16 of 57 invisible).

**Insert each new entry at its ALPHABETICAL place, by link filename** (one line
per PR; the archive pointer stays first). Not at the bottom: two PRs appending
there always collided. `python -m tools.memory_budget --sort` puts them in
order. Every note file is indexed in exactly one of this file and
`MEMORY-archive.md` (not auto-loaded; the test checks). Near the ceiling, move
the OLDEST lines whole to the archive.

- [Memory archive: pre-09-15](MEMORY-archive.md) — NOT auto-loaded: pre-09-15 history + standing rulings (fill rows 0.15, DST axis fixed, Ink/Stitch clean-room, Ember teardowns)
- [Junction construction plan](../../docs/superpowers/plans/2026-09-19-junction-construction.md) — folds are welds through 30-60° corners; `satin_junction_stack` ON refuses them (R 311→0)
- [Lettering construction plan](../../docs/superpowers/plans/2026-09-19-lettering-construction.md) — Kent: trace + font-engine rules; all built, ON but 3b (skeleton RULED, owes sew-out)
- [Opus team architecture](../../docs/superpowers/plans/2026-10-23-opus-team-architecture.md) — the plan a fresh director runs from: method, state, ranked queue L1-L10 / I1-I6, Kent's open decisions, brief template, traps
- [Bean holds ON](bean-holds-on-2026-10-15.md) — Kent flipped counter hold 0.25 + bay hold 0.2 as PLAIN defaults (None stays OFF); the three sew-out cards pin None explicitly
- [Beanie knockdown ON](beanie-knockdown-2026-10-21.md) — Kent flipped it unsewn: garment-coloured fill under design
- [Big-letter construction](big-letter-construction-2026-10-24.md) — MARINE's 163-vs-77 is 35 patches + a sheared top slab, no length cap; cuts buy cross direction only — `text_lean` (OFF) gives it, don't copy the count
- [Border by size](border-by-size-2026-10-23.md) — `border_by_size` OFF: at 6 mm+ the separator is STROKE vs satin ceiling; letters are the population; fills a coin flip
- [Border census](border-census-2026-10-23.md) — small rings = edge cap + run tier; pro borders by SIZE (>= 4 mm)
- [Border from outline](border-from-outline-2026-10-24.md) — pro borders what the ART outlines (kappa 0.76, n 588), not size/stroke; `border_from_outline` OFF: loop per body at his width, bodies fill
- [Outline line-art guard](border-from-outline-line-art-guard-2026-10-25.md) — Bridge bowl = hairline drawing; guard OFF: hairline AND leaves strokes. Thin alone kills Machine's frame (pro widens it); pro's Bridge art had no drawing
- [bridge: border and script](bridge-border-and-script-2026-09-30.md) — on/off border = JPEG halo (the dissolve folds it); script is not text; Kent's lever `SATIN_GAPS_TIGHT`
- [Build what was priced](build-what-was-priced.md) — SNAPSHOT: after Kent picks a priced option, build exactly that
- [The built-OFF sitting](built-off-sitting-2026-10-03.md) — `patch_junctions` had shipped already: render vs shipped first. Kent: `cap_recentre` ON, `bean_letters` OFF
- [Cap order, and a pair experiment](cap-order-and-the-pair-experiment-2026-09-19.md) — `cap_center_out` parked OFF: the pro's cap/LC pairs of one artwork (a controlled experiment) back bottom-up
- [Card v4 sew-out: pro raises small text](card-v4-sewout-letter-size-2026-10-20.md) — pro lifts small words to ~4 mm and satins them; ours traces art size; measure by colour
- [Check what shipped before building it](check-shipped-before-building-2026-09-29.md) — Kent asked for a manual digitizer that had shipped; grep MASTER_SCOPE/PRODUCT, offer "show me", drive it
- [Corner folds in the Column lane](column-corner-folds-2026-10-23.md) — pro FOLDS one column round every L corner (57 read), cuts only T junctions; `lettering_columns_corner_fold` OFF
- [Column width on resize](column-width-on-resize-2026-10-01.md) — ruling 12: drawn width scales, pull comp fixed; store `widthPx`, mm is a view; no clamp
- [A concurrent session designed the same tool](concurrent-session-designed-the-same-tool-2026-09-17.md) — check branches + live sessions FIRST
- [Cross underlay presets](cross-underlay-presets-2026-10-21.md) — `fill_underlay_cross` OFF (hat/LC/beanie); MFab/Becker "BARE" fills were SATIN the tool misread — list run kinds first
- [Cut after bury](cut-after-bury-2026-10-23.md) — Fremont's 150 extra cuts were letter hops ON the field; the pro walks those: bury, walk on work, cut bare. 187 -> 44 (pro 20)
- [Cut every jump](cut-every-jump-2026-10-21.md) — `cut_every_jump` OFF: uncut 285 -> 0, but trims 434 -> 674 (pro 246); bury first
- [Detail spokes ON](detail-spokes-on-2026-10-18.md) — Kent: ON tightened (MIN_TIPS 4, floor 1.45 x width/92.6); Fremont OFF md5 follows OpenCV's Intel IPP path; test env capped OPENCV_IPP=avx2
- [The display revamp, and a fleet that outran its budget](display-revamp-and-a-fleet-that-outran-its-budget-2026-09-16.md) — `kind` is an OPEN set of eight
- [The Studio never sent the file](../../DOCTRINE.md) — 1,200-px canvas re-encode rewrote RGB under alpha (Becker 59→175 trims); FIXED 09-20; `alpha_edge_extend` ON
- [Edge wobble is satin rails](edge-wobble-is-satin-rails-2026-09-19.md) — "right shapes, bad edges": outline clean (0.011 mm), SATIN RAILS wobble ~0.10 mm; run `edge_wobble.py` first
- [Browser fill lane state](embot-browser-fill-lane-state.md) — SNAPSHOT 10-03: #606/#609/#611 built OFF, flips Kent's; island fix #613 merged PRE-audit, cures in #620; cleanup only Kent can run
- [Closed-ring lane](embot-closed-ring-lane.md) — SNAPSHOT: #621 `offsetRing` on a repeated point, #625 stacked on it; defect 55's offset half is Kent's call
- [Handover numbers and stacked branches](embot-handover-numbers-and-stacked-branches.md) — SNAPSHOT: reproduce a handed-over number with its own script
- [Star-walk lane](embot-star-walk-lane.md) — SNAPSHOT: #624 ends `skeletonEdges`' endless walk; defect 57's cure order waits on Kent
- [Sub-unit stitches lane](embot-sub-unit-stitches-lane.md) — SNAPSHOT 10-04: `dedupeHoles` built OFF (#623), Kent's "new flag, every run"
- [Enclosed white like the pro](enclosed-white-like-pro-2026-10-23.md) — pro sews bodies/bands, leaves letter counters: flag matches 32/34 (Tires loops xfail); MFab 1.45x is band CONSTRUCTION
- [Envelope junction escapes](envelope-junction-escapes-2026-09-30.md) — Kent's "fill a void": escapes refused, teeth dropped; the pro flows: BACK STITCHING; holes = the comb split
- [Exposed travel is the fill tier's](exposed-travel-is-the-fill-tier-2026-09-19.md) — `travel_cover`'s 245 mm is defect 21, not gate 3 (fill bridges, 0.0 on fabric); `fill_bridge_cut` ON (Kent)
- [The foundation review and the eye-pairs build](eye-pairs-build-2026-09-17.md) — Kent picked F4; `tools/eye_pairs` built in one session; `uncovered_wanted_mm2` is a DENOMINATOR; spike first
- [Eye pairs, the follow-up](eye-pairs-followup-2026-09-18.md) — "merged" was OPEN and red; a test red only where tesseract EXISTS; the MERGE REF alone broke a word budget
- [Fill columns: thread across holes](fill-columns-2026-10-03.md) — JS fill floated across every hole, unseen by its test; `fillColumns` built OFF, unsewn. Audit BEFORE arming
- [fillColumns float pictures](fill-columns-float-pictures-2026-10-08.md) — STANDING: next 10 digitized images shown to Kent carry the off/on float sheet; count 1/10
- [Row stagger for the browser fill](fill-stagger-2026-10-03.md) — JS fill holes lined up 94%; `fillStagger` built OFF (Kent's flip), +7% stitches. A channel is 3 rows, not 2
- [Fill turn slant](fill-turn-slant-2026-10-21.md) — `fill_turn_slant` OFF (#1036): turns 0.7 mm along the row; Kent holds OFF until the next sew-out card's OFF/ON swatch
- [Fine detail and the work grid](fine-detail-work-grid-2026-09-30.md) — "RESTAURANT" was lost to the tracer's 4 px/mm grid, not the file; `work_px_per_mm` ON at 8 (Kent 10-01)
- [Flag Before After: the labelled page, found and finished](flag-before-after-2026-09-18.md) — the scratch copy is `--labelled` now; re-read the db just before a SAME-URL republish
- [Flip sheet: layout flags OFF | ON | pro](flip-sheet-2026-10-23.md) — `tools/flip_sheet_renders.py`; diff is a MULTISET (locks sit on stations); x-ray tiles
- [Flip sheet, inlined](flip-sheet-inline-2026-10-24.md) — `report --inline` = ONE HTML (data URIs; app viewer breaks relative paths); a flag with a `base` diffs against its own OFF
- [Flip sheet wave 2](flip-sheet-wave2-2026-10-24.md) — four flags OFF|ON|pro; per-flag fixtures, shared base OFF arms, MFab art fallback; Tires monoline invisible at viewing size (trims 9 → 32)
- [Inside stagger at pivots](inside-stagger-2026-10-23.md) — pro ALSO alternates; ours piled the full ends in one hole (16-79 vs 2-5) at 35% depth vs his 20%; `lettering_columns_inside_stagger` OFF
- [Instagram: gradient lane, not classifier](instagram-gradient-lane-edges-2026-09-30.md) — real IG file classifies gradient CORRECTLY; the SLIC lane's edges were the defect, snap ON. Render first
- [Keyline band](keyline-band-2026-10-23.md) — `enclosed_white_keyline` OFF: satin loop per letter on the ARTWORK polygon; MFab 25,512 → 19,214 (pro 17,568); seam-close the reach
- [Lane cleanup 10-20](lane-cleanup-2026-10-20.md) — SNAPSHOT: a dirty lane's flip was one Kent REVERSED; read the parent's LAST turns before carrying stranded work; lanes LEFT (Kent)
- [Lane triage 10-11](lane-triage-2026-10-11.md) — SNAPSHOT: lane HEAD = merged PR head means landed (squash); `manual-columns` stranded at task 5; a `-b X origin/main` lane pushes to main
- [Layout is judged in the preview](layout-judged-in-preview-2026-10-22.md) — Kent 10-22: stitch LAYOUT flips from renders, no sew-out
- [Letter separation](letter-separation-2026-10-25.md) — W3-07: our 6 touching 5-10 mm pairs are PULL COMP (traced 0.60-0.87 apart, rails 0.29 out), not construction; pro keeps >= 0.10 mm, tips only
- [Letterform priors lane](letterform-priors-lane-2026-10-06.md) — "something new" on lettering was yesterday's lane (outline-cut); check sibling lanes before proposing new
- [10 mm and up lettering band](lettering-10mm-up-band-2026-10-23.md) — only MARINE compares (white faces unsewn); the pro crosses diagonals like stems; `lettering_columns_text_lean` OFF
- [5-10 mm lettering band](lettering-5-10mm-band-2026-10-23.md) — gap is corners (pro folds, we butt); Drone O sewn SHUT by a split alpha counter; `enclosed_alpha_hole_parts` OFF
- [Lettering architecture R&D](lettering-architecture-2026-10-07.md) — five failures by letter size; pros put rails on the OUTLINE; Column lane OFF
- [Lettering board](lettering-board-2026-10-25.md) — the ONE board a lettering PR quotes: ours/pro by job and drawn height, five figures, n/a with a reason; `--compare A B` is the delta; baseline docs/scoreboards/
- [Lettering route review](../../docs/lettering-route-review-2026-09-19.md) — trace-as-shape stays: font ID is dead (IoU 0.9 = a WRONG font); the gap is CONSTRUCTION (41 vs 3 trims)
- [Fremont letters are not thicker than the pro's](lettering-thickness-fremont-2026-10-06.md) — file width = pro's (1.23 vs 1.40 scaled)
- [Lock stitches, both JS builders](lock-stitches-2026-10-03.md) — `ties` built OFF for shapes too; the 09-14 lettering lock leg was 0.8 PIXELS. Assert lengths in OUTPUT units
- [lost_frac is two metrics](lost-frac-is-two-metrics-2026-09-20.md) — `lost_frac` sums two OPPOSITE defects; enthusiast is 100% overshoot, no ink lost. Never quote its MAGNITUDE
- [MARINE stem rails](marine-stem-rails-2026-10-25.md) — #1052's "stem wobble" FALSE: refit stems straight, rails on them; jitter > 0.15 = corners 318 / strays 49 / straight stems 0; pro's 0.03 = cuts at notches; `rail_jitter_cause.py`
- [Index split into live + archive](memory-index-archive-split-2026-10-23.md) — pre-09-15 lines in MEMORY-archive.md (not auto-loaded); new entries go at the BOTTOM, one line per PR
- [The index that stopped loading its newest entries](memory-index-overflow-2026-09-15.md) — 24,986-CHAR ceiling drops the NEWEST entries; reclaim HOOKS, never entries
- [Memory outside the repo](memory-outside-the-repo.md) — sessions rooted in `.claude-work` write memory to a folder this repo never sees; seven notes snapshotted here by 10-04
- [N fan cure](n-fan-cure-2026-10-08.md) — `satin_tip_corner_gate` OFF: tip = convex corner; ≈ tip caps off; degree gate refuted
- [Narrow columns like the pro](narrow-columns-2026-10-23.md) — small_bold: serifs absorbed into the stroke, chord-read junctions, no chamfer mitre; 74→55 columns; `column_harness.py`
- [The staircase on low-res uploads](native-ramp-edge-read-2026-09-18.md) — 0.68 mm stairs: NEAREST-upscaled alpha; `subpixel_edges_upscaled` ON (Kent); byte-identity is an EXPRESSION
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [The orphan-lane sweep](orphan-lane-sweep-2026-09-30.md) — `pro-overlay-diff` PARKED (Kent); squash merges blind `main..lane`, count added lines; Developer Mode ON
- [Parallel agent with the embot](parallel-agent-with-embot.md) — SNAPSHOT: audit before a PR is OPEN, not just before arming; never `git stash` in a lane; a stacked PR targets main and says so
- [Photo edit tail 2026-09-17](photo-edit-tail-2026-09-17.md) — `fill_travel_under_cover` is ~58% of a photo edit tail; the reorder memo is exact ONLY while both stay pure
- [Preview vs the file it hands over](preview-vs-file-split-dogleg-2026-09-20.md) — preview matches the .dst exactly; the split walked an L on diagonals (FIXED); axis-aligned fixtures hid it
- [Pro intake](pro-intake-2026-10-25.md) — `python -m tools.pro_intake`: new job -> registered pair + census; registry gitignored (client names); preview vs art by content AND name; tesseract confirms lettering
- [Pro measured values](pro-measured-values-2026-10-23.md) — `pro_measured_values` OFF: fill 3.49, satin 0.37/0.35, bean 0.95 on hat/LC/beanie; Kent flips after sew-out
- [Pro rules across all jobs](pro-rules-across-jobs-2026-10-21.md) — small text raised to ~4 mm on every job; beanie knockdown 5/5; white interiors sewn; trims from DST, never PES
- [ProSeal bubble borders](proseal-bubble-borders-2026-10-22.md) — the "border" is the bean edge cap + run tier on small shapes; the pro fills bubbles bare
- [Pull comp by stroke](pull-comp-by-stroke-2026-10-22.md) — pro's hat pull FALLS with width: +0.58 at 0.85 mm, +0.42 at 2.6, 0 at 4; `pull_comp_by_stroke` OFF; small text stays small_bold's
- [Rail wobble is the model's floor](rail-wobble-is-the-models-floor-2026-09-21.md) — satin 0.089 mm is the rail model's FLOOR; do not tune its six defences. Mean OUTWARD, tail inward
- [Run-button commands need absolute paths](run-button-commands-need-absolute-paths.md) — Run buttons share ONE PowerShell whose cwd persists; `cd digitizer` works once — give an absolute cd
- [Satin small shapes](satin-small-shapes-2026-10-20.md) — `satinSmallShapes` OFF (#994): cap, smallest column, junction zone; 5-point stars ARE satin on main; OFF md5 pins
- [Second sitting: eleven flags and the 08-27 engine](second-sitting-eleven-flags-2026-09-28.md) — Kent: "VERY hard to tell"; today beats 08-27 on 7 of 9; `rail_comp` ON 09-29, envelope ON 09-30
- [SEEDS unservable request, and the worktree blind spot](seeds-request-and-the-worktree-blind-spot-2026-09-22.md) — a worktree lacks the rembg venv (DIFFERENT pipeline)
- [Sequence like the pro: order is not the gap](sequence-like-pro-2026-10-25.md) — L10 FALSE, not built: pro sews the cap rule and it costs him; ours passes over a reachable piece 18 of 145 extra cuts; gap is cuts inside a piece
- [Session ended mid-suite](session-ended-mid-suite-2026-10-20.md) — a ruled flip sat uncommitted in a lane behind a hung pytest; sweep lanes' TRACKED dirt and the newest session's last turn
- [Sew white areas](sew-white-areas-2026-10-21.md) — R11 built OFF as a Studio option; counter = untagged white in a text-cluster letter; Machine field doubles trims (stage 5)
- [Sew-out card v7](sewout-card-v7-2026-10-24.md) — only pull-by-stroke + pro values wait on fabric; BASE = ruled-unmerged flips; pull is a Fremont no-op, on MARINE it turns split satin plain like the pro
- [Short column underlay](short-column-underlay-2026-10-22.md) — `satin_underlay_short_columns` OFF: pro centre-walks 83-97% of columns at EVERY width; no 3.5 mm pitch; zigzag unsettled
- [Silhouette under-fill](silhouette-underfill-2026-10-24.md) — "pro fills it" was LAYERING, not tier (kappa 0.170 vs 0.198): ring outline filled under in the majority colour; `silhouette_underfill` OFF
- [Six pending flags, invisible at viewing size](six-flags-invisible-at-viewing-size-2026-09-18.md) — Kent: 29 of 34 pairs "no difference"; all six stay OFF, not the Ember-gap lever
- [Small bold columns](small-bold-columns-2026-10-21.md) — `lettering_columns_small_bold` OFF: 4 mm letters at 0.85 mm satin; counters closed UPSTREAM by growth
- [Small-text floor](small-text-floor-2026-10-24.md) — pro re-sets every line under ~3.2 mm to 4-4.6 mm satin, never runs/drops; #1029 missed ProSeal (design-edge halo); `small_text_cap_reach_edges` OFF
- [Small text re-set](small-text-reset-2026-10-21.md) — OFF: columns were already the pro's, SPACING was wrong; later stages undid the layout five ways; 5/S bays still close
- [True-size guard below 81 mm](small-text-true-size-guard-2026-10-15.md) — 65 mm loss = strays bug + ink-ground bug + per-glyph OCR noise; guard 0.45 x 40/wt, unsewn; ink ring OFF
- [Split comb per column](split-comb-2026-09-30.md) — per-leg comb flickered on Becker's letters; `_comb_thresholds` 122 → 37; raising 5.0 is a sew-out (gate 1)
- [Studio configurator redesign](studio-configurator-pr1-2026-09-30.md) — wizard → Tesla panel: all four PRs built; PR 3 = Advanced fold (hidden, not removed); Original view still open
- [The 80 mm ink link](the-80mm-ink-link-2026-10-15.md) — red circles were a STALE SERVICE; THE at 80 = rescued round linked across inks; measure at the width the Studio SENDS
- [Tie-in off](tie-in-off-2026-10-22.md) — `tie_in_off` OFF: ours already ties only at cuts; pro locks no start (1 of 68); saved ~230 stitches
- [Trim economy](trim-economy-2026-10-21.md) — only under-later cuts are policy (pro 9, ours 43): `trim_bury_under_later` OFF; bare gap is R11 white-as-fabric
- [Underlay under fills](underlay-under-fills-2026-10-05.md) — gradient fills sewed with ZERO underlay; pro sews a crossing pass, built as `cross_tatami`, in no preset; preview cannot show underlay

- [WITHDRAWN: warn sooner on small files](warn-sooner-small-files-handoff-2026-10-01.md) — Kent 10-02: no warnings, the engine takes the path; replaced by bean letters, built OFF in PR #601
- [White faces fill](white-faces-fill-2026-10-25.md) — sew_enclosed_white made Becker 8.4x slower (white faces sewed as Column letters); `sew_enclosed_white_fields_fill` OFF fills them at 22°; house angle hides in fill_angle_deg
- [Wide letters: MFab's W](wide-letters-mfab-w-2026-10-23.md) — W never reached the lane: tagger aspect 1.4 (W+E touch, 2.55; W alone 1.58); `text_cluster_wide_letters` OFF; measure MFab with main's rembg
- [Word legibility instrument](word-legibility-instrument-2026-10-24.md) — `tools/word_legibility.py`: per word, ours vs pro, chance-corrected cc; MFab + pro small words not locatable (n/loc, never 0); coarse, saturates at 1.00
- [L1 one tagger](word-tagger-l1-2026-10-08.md) — BUILT OFF `cfg.lettering_words`; kappa 0.907 vs text cluster 0.881 (in-sample); Kent: AFTER better under the Column lane (10-08)
- [Worktree guard judges targets](worktree-guard-judges-targets-2026-10-04.md) — rm/mv guard judges the resolved TARGET; own-lane deletes allowed (Kent 10-04)
- [Worktree session: the harness guard](worktree-session-harness-guard-2026-09-17.md) — `digitizer` spells `git`: quotes, `cd` chains refused; venv by 8.3 `CLAUDE~4`; preview_start reads MAIN
- [Wrong-root sessions, global guards](wrong-root-sessions-and-global-guards-2026-10-04.md) — sessions rooted outside the repo ran with no project hooks; `embot-guards-global.js` covers them
