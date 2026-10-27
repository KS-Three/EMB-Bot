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

- [Memory archive: through 10-04](MEMORY-archive.md) — NOT auto-loaded: history through 10-04 + standing rulings (fill rows 0.15, DST axis fixed, Ink/Stitch clean-room, Ember teardowns)
- [Opus team architecture](../../docs/superpowers/plans/2026-10-23-opus-team-architecture.md) — the plan a fresh director runs from: method, state, ranked queue L1-L10 / I1-I6, Kent's open decisions, brief template, traps
- [Apex cut](apex-cut-2026-10-25.md) — acute tips (M's V, W, MFab N, PROSEAL A): pro cuts along the cross, tip one level-crossed piece; `lettering_columns_apex_cut` OFF; corner_fold refuses them (long_way)
- [Apex walk](apex-walk-2026-10-27.md) — apex_cut's walk sews each tip from its point: tip-satin travel <= 0.05 mm, crosses kept; per-job travel > OFF on 5 jobs, foreman's call
- [Bean holds ON](bean-holds-on-2026-10-15.md) — Kent flipped counter hold 0.25 + bay hold 0.2 as PLAIN defaults (None stays OFF); the three sew-out cards pin None explicitly
- [Beanie knockdown ON](beanie-knockdown-2026-10-21.md) — Kent flipped it unsewn: garment-coloured fill under design
- [Big-letter construction](big-letter-construction-2026-10-24.md) — MARINE's 163-vs-77 is 35 patches + a sheared top slab, no length cap; cuts buy cross direction only — `text_lean` (OFF) gives it, don't copy the count
- [Border by size](border-by-size-2026-10-23.md) — `border_by_size` OFF: at 6 mm+ the separator is STROKE vs satin ceiling; letters are the population; fills a coin flip
- [Border census](border-census-2026-10-23.md) — small rings = edge cap + run tier; pro borders by SIZE (>= 4 mm)
- [Border from outline](border-from-outline-2026-10-24.md) — pro borders what the ART outlines (kappa 0.76, n 588), not size/stroke; `border_from_outline` OFF: loop per body at his width, bodies fill
- [Outline line-art guard](border-from-outline-line-art-guard-2026-10-25.md) — Bridge bowl = hairline drawing; guard (Kent ON 10-25): hairline AND leaves strokes. Thin alone kills Machine's frame (pro widens it)
- [Bridge census](bridge-census-2026-10-27.md) — Bridge hat+LC through 14 pro rules on main 8341d1f7: 2 CONTRADICTS (border_by_size fields, proSized LC), 8 AGREES, 4 N/A; ours' text is a reach gap (folds 2 vs 35), not a rule
- [Build what was priced](build-what-was-priced.md) — SNAPSHOT: after Kent picks a priced option, build exactly that
- [Buried walk between pieces](buried-walk-2026-10-26.md) — W4-03 FALSE: bury rule exists at the pro's p90; 0 of our 176 between-shape cuts have ANY route under later thread; his Drone metre = layering + colour revisits
- [Cap frames sew 64 mm tall](cap-frame-height-2026-10-26.md) — PHYSICAL, Kent 10-26: his cap frames sew >= 64 mm (2.5 in); hat-height gate 1 settled
- [Card v4 sew-out: pro raises small text](card-v4-sewout-letter-size-2026-10-20.md) — pro lifts small words to ~4 mm and satins them; ours traces art size; measure by colour
- [CI pin hygiene](ci-pin-hygiene-2026-10-25.md) — hex `==` prints whole; `tools.ci_repin` re-pins from a run id (dry run unless --apply); shard map max/mean 1.28 → 1.00; advisory default-path-diff job
- [Corner folds in the Column lane](column-corner-folds-2026-10-23.md) — pro FOLDS one column round every L corner (57 read), cuts only T junctions; `lettering_columns_corner_fold` OFF
- [Column lane memo](column-lane-memo-2026-10-26.md) — lane rebuilt identical columns (779/2,825) and rail pairings (941/1,413); per-letter `_MEMO` on exact keys: stages 5-7 CPU -12% (MFab hat -20%), 7 DSTs byte-identical
- [Column rail fit: measured false](column-rail-fit-negative-2026-10-25.md) — 7 pairs: rails read 0.000-0.04 on RUN windows; per-letter wobble is real corners, a fit can't move it. Quote `rail_run`, don't plan a rail fit
- [Column reach census](column-reach-census-2026-10-25.md) — 257/296 reach on main; misses = white faces + split/script letters, not the tagger; ratio rescues fail held-out
- [Cross underlay presets](cross-underlay-presets-2026-10-21.md) — `fill_underlay_cross` OFF (hat/LC/beanie); MFab/Becker "BARE" fills were SATIN the tool misread — list run kinds first
- [Cut after bury](cut-after-bury-2026-10-23.md) — Fremont's 150 extra cuts were letter hops ON the field; the pro walks those: bury, walk on work, cut bare. 187 -> 44 (pro 20)
- [Cut every jump](cut-every-jump-2026-10-21.md) — `cut_every_jump` OFF: uncut 285 -> 0, but trims 434 -> 674 (pro 246); bury first
- [Detail spokes ON](detail-spokes-on-2026-10-18.md) — Kent: ON tightened (MIN_TIPS 4, floor 1.45 x width/92.6); Fremont OFF md5 follows OpenCV's Intel IPP path; test env capped OPENCV_IPP=avx2
- [Digitize speed](digitize-speed-2026-10-26.md) — tesseract reads batched 4 at a time (preflight 2.3-2.8x, byte-identical); a loaded laptop inflates process_time ~2.6x; Studio 300 s poll vs service 600 s
- [Download stale guard](download-stale-guard-2026-10-25.md) — Kent 10-25 "block until re-digitized": machine-file buttons disabled while stitches trail size/garment/settings; one rule (staleness.js); run button lit; no text
- [Browser fill lane state](embot-browser-fill-lane-state.md) — SNAPSHOT 10-03: #606/#609/#611 built OFF, flips Kent's; island fix #613 merged PRE-audit, cures in #620; cleanup only Kent can run
- [Closed-ring lane](embot-closed-ring-lane.md) — SNAPSHOT: #621 `offsetRing` on a repeated point, #625 stacked on it; defect 55's offset half is Kent's call
- [Handover numbers and stacked branches](embot-handover-numbers-and-stacked-branches.md) — SNAPSHOT: reproduce a handed-over number with its own script
- [Star-walk lane](embot-star-walk-lane.md) — SNAPSHOT: #624 ends `skeletonEdges`' endless walk; defect 57's cure order waits on Kent
- [Sub-unit stitches lane](embot-sub-unit-stitches-lane.md) — SNAPSHOT 10-04: `dedupeHoles` built OFF (#623), Kent's "new flag, every run"
- [Enclosed white like the pro](enclosed-white-like-pro-2026-10-23.md) — pro sews bodies/bands, leaves letter counters: flag matches 32/34 (Tires loops xfail); MFab 1.45x is band CONSTRUCTION
- [fillColumns float pictures](fill-columns-float-pictures-2026-10-08.md) — STANDING: next 10 digitized images shown to Kent carry the off/on float sheet; count 1/10
- [Fill turn slant](fill-turn-slant-2026-10-21.md) — `fill_turn_slant` OFF (#1036): turns 0.7 mm along the row; Kent holds OFF until the next sew-out card's OFF/ON swatch
- [Fine bars satin](fine-bars-satin-2026-10-25.md) — `fine_bars_satin` ON 10-26: pro satins every free thin ink bar (5/5); STEM_MIN_ASPECT or < 1 cross, not 2.5 (rope); 37/38 cure, region kappa 0.905
- [Flip eight 2026-10-23](flip-eight-2026-10-23.md) — Kent: "flip the eight ON, hold two" + small_bold; judged by NUMBERS vs the pro; `FLIP_2026_10_23` pins the OFF arm
- [Flip-proof pins](flip-proof-pins-2026-10-27.md) — `FLAT_GOLDEN_MD5` from the json; `frozen_cfg()` spreads a dated snapshot; test_pins_are_frozen guards new md5 pins
- [Flip sheet: layout flags OFF | ON | pro](flip-sheet-2026-10-23.md) — `tools/flip_sheet_renders.py`; diff is a MULTISET (locks sit on stations); x-ray tiles
- [Flip sheet, inlined](flip-sheet-inline-2026-10-24.md) — `report --inline` = ONE HTML (data URIs; app viewer breaks relative paths); a flag with a `base` diffs against its own OFF
- [Flip sheet wave 2](flip-sheet-wave2-2026-10-24.md) — four flags OFF|ON|pro; per-flag fixtures, shared base OFF arms, MFab art fallback; Tires monoline invisible at viewing size (trims 9 → 32)
- [Flip sheet wave 3](flip-sheet-wave3-2026-10-26.md) — 12 OFF flags since 10-24 by flag + kind; monoline INERT on Tires, fill_section_travel / bay_mouth near-inert; OFF cells keyed per-cell by HEAD sha
- [Flip sheet wave 5](flip-sheet-wave5-2026-10-27.md) — 4 asked on main ce8cc87d, gate 3 clear; Kent 10-27: bean_ink + part_touching (only together) + italic lean ON, fill_section_travel held; keyline trio inert off MFab
- [Flip two](flip-two-2026-10-23.md) — border_by_size + enclosed_alpha_hole_parts + corner_fold ON (Kent 10-23); Becker untouched; local goldens red on Windows with flags OFF too
- [Garment size like the pro](garment-size-like-pro-2026-10-26.md) — pro boxes hat 113.5x64, LC 96x76.5, area 5,800 (Bridge LC, Kent 10-27), beanie 94.5x56; `proSized` default ON (10-26)
- [Golden Tee gap](goldentee-gap-2026-10-27.md) — Kent: no build. The +95% is the pro simplifying: 39% = silver extrusion + red stroke he never sews; faces 22% (G's border_by_size ring 640); fields_fill ON makes it worse
- [Cuts inside one piece](in-piece-cuts-2026-10-25.md) — ours 109 vs pro 25: fill sections 35 (pro 0), satin split 40; `fill_section_travel` OFF routes underlay ring hops (Fremont 51 -> 41); fill-order gains all cost exposure
- [Inside stagger at pivots](inside-stagger-2026-10-23.md) — pro ALSO alternates; ours piled the full ends in one hole (16-79 vs 2-5) at 35% depth vs his 20%; `lettering_columns_inside_stagger` OFF
- [Isolated pieces](isolated-pieces-2026-10-25.md) — +33 = MFab white fragments + block accounting (compare ENTRIES); `absorb_fragments` OFF: MFab white-ON 77 -> 60
- [Italic bars](italic-bars-2026-10-25.md) — pro crosses italic BARS along the slant; `lettering_columns_italic_lean` (ON 10-27) moves straight bars (hat 0.31 -> 0.46, pro 0.54), not bowls; read per cross (`italic_cross.py`), never by piece axis
- [Keyline band](keyline-band-2026-10-23.md) — `enclosed_white_keyline` OFF: satin loop per letter on the ARTWORK polygon; MFab 25,512 → 19,214 (pro 17,568); seam-close the reach
- [Keyline loop chain](keyline-loop-chain-2026-10-26.md) — MFab gate only (Kent 10-27): loop hops walked under later white; white-loop cuts 11→5 (pro 5/6)
- [Lane census](lane-census-2026-10-25.md) — Kent 10-26: 6b NOT built, the button stays. 4 of 14 pro jobs reach flat (all Becker), 8 gradient, 2 photo_scene; 6b as written = the button's file; kappas a wash
- [Lane cleanup 10-20](lane-cleanup-2026-10-20.md) — SNAPSHOT: a dirty lane's flip was one Kent REVERSED; read the parent's LAST turns before carrying stranded work; lanes LEFT (Kent)
- [Lane triage 10-11](lane-triage-2026-10-11.md) — SNAPSHOT: lane HEAD = merged PR head means landed (squash); `manual-columns` stranded at task 5; a `-b X origin/main` lane pushes to main
- [Layering census](layering-census-2026-10-26.md) — W4-06 FALSE: pro sews every contained piece ON its ground (162/162) = `silhouette_underfill`; 80 of 176 cuts cross their own ground (sews first), 5 a sibling
- [Layout is judged in the preview](layout-judged-in-preview-2026-10-22.md) — Kent 10-22: stitch LAYOUT flips from renders, no sew-out
- [Letter separation](letter-separation-2026-10-25.md) — W3-07: our 6 touching 5-10 mm pairs are PULL COMP (traced 0.60-0.87 apart, rails 0.29 out), not construction; pro keeps >= 0.10 mm, tips only
- [Letterform priors lane](letterform-priors-lane-2026-10-06.md) — "something new" on lettering was yesterday's lane (outline-cut); check sibling lanes before proposing new
- [10 mm and up lettering band](lettering-10mm-up-band-2026-10-23.md) — only MARINE compares (white faces unsewn); the pro crosses diagonals like stems; `lettering_columns_text_lean` OFF
- [5-10 mm lettering band](lettering-5-10mm-band-2026-10-23.md) — gap is corners (pro folds, we butt); Drone O sewn SHUT by a split alpha counter; `enclosed_alpha_hole_parts` OFF
- [Lettering architecture R&D](lettering-architecture-2026-10-07.md) — five failures by letter size; pros put rails on the OUTLINE; Column lane OFF
- [Lettering board](lettering-board-2026-10-25.md) — the ONE board a lettering PR quotes: ours/pro by job and drawn height, five figures, n/a with a reason; `--compare A B` is the delta; baseline docs/scoreboards/
- [Fremont letters are not thicker than the pro's](lettering-thickness-fremont-2026-10-06.md) — file width = pro's (1.23 vs 1.40 scaled)
- [MARINE stem rails](marine-stem-rails-2026-10-25.md) — #1052's "stem wobble" FALSE: refit stems straight, rails on them; jitter > 0.15 = corners 318 / strays 49 / straight stems 0; pro's 0.03 = cuts at notches; `rail_jitter_cause.py`
- [Index split into live + archive](memory-index-archive-split-2026-10-23.md) — pre-09-15 lines in MEMORY-archive.md (not auto-loaded); new entries go at the BOTTOM, one line per PR
- [Index counts CRs](memory-index-crlf-count-2026-10-26.md) — loader counts the file as stored: CRLF = +1 char/line; notes pinned LF; `git checkout --` won't convert (recipe inside)
- [Memory outside the repo](memory-outside-the-repo.md) — sessions rooted in `.claude-work` write memory to a folder this repo never sees; seven notes snapshotted here by 10-04
- [MFab recipe trims](mfab-recipe-trims-2026-10-26.md) — the cuts were keyline slivers behind a dark hairline; `keyline_fold_slivers` (OFF) folds them in: hat 41→27, LC 54→29 on #1057's base; hat on-thread exposed travel 23→43 mm
- [MFab under-fill panels](mfab-underfill-panels-2026-10-25.md) — Kent's MFab "chaos" = flip of under-fill + white + keyline + `silhouette_underfill_panels` (OFF): pro layering; under-fill alone dropped keyline-held bodies
- [Monoline script satin](monoline-script-satin-2026-10-24.md) — Tires "ires" sewed FILL on dt_p90_cap alone; `monoline_script_satin` OFF; pro hides ALL in-word travel under later satin: trims 24 -> 8 (pro 10)
- [N fan cure](n-fan-cure-2026-10-08.md) — `satin_tip_corner_gate` OFF: tip = convex corner; ≈ tip caps off; degree gate refuted
- [Narrow columns like the pro](narrow-columns-2026-10-23.md) — small_bold: serifs absorbed into the stroke, chord-read junctions, no chamfer mitre; 74→55 columns; `column_harness.py`
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [Outline loop pivot](outline-loop-pivot-2026-10-25.md) — corner spikes are SPARSE far ends, not a missing mitre (pro's arc is round); `outline_loop_mitre` ON 10-26
- [Outlined bean ink](outlined-bean-ink-2026-10-27.md) — MFab LC's AND read its white keyline as ink, sewed white; `bean_ink_outlined_letters` (ON 10-27) drops reads half outside
- [Parallel agent with the embot](parallel-agent-with-embot.md) — SNAPSHOT: audit before a PR is OPEN, not just before arming; never `git stash` in a lane; a stacked PR targets main and says so
- [Pro intake](pro-intake-2026-10-25.md) — `python -m tools.pro_intake`: new job -> registered pair + census; registry gitignored (client names); preview vs art by content AND name; tesseract confirms lettering
- [Pro measured values](pro-measured-values-2026-10-23.md) — `pro_measured_values` OFF: fill 3.49, satin 0.37/0.35, bean 0.95 on hat/LC/beanie; Kent flips after sew-out
- [Pro renders local only](pro-renders-local-only-2026-10-27.md) — Kent 10-27 "Stop new ones, keep old": pro-file renders go to gitignored `pro_renders/`; `test_no_new_pro_renders` fails on a new `pro` word under docs/ (211 allowlisted)
- [Pro rules across all jobs](pro-rules-across-jobs-2026-10-21.md) — small text raised to ~4 mm on every job; beanie knockdown 5/5; white interiors sewn; trims from DST, never PES
- [ProSeal bubble borders](proseal-bubble-borders-2026-10-22.md) — the "border" is the bean edge cap + run tier on small shapes; the pro fills bubbles bare
- [Pull comp by stroke](pull-comp-by-stroke-2026-10-22.md) — pro's hat pull FALLS with width: +0.58 at 0.85 mm, +0.42 at 2.6, 0 at 4; `pull_comp_by_stroke` OFF; small text stays small_bold's
- [Questions roll up to the director](questions-roll-up-to-director-2026-10-27.md) — Kent 10-27: a worker never asks Kent; SendMessage the decision (options, cost, catch, pick) to its starter
- [Re-pin tuples](repin-tuples-2026-10-27.md) — `_hexrepr` writes tuple/list/dict digests whole; `ci_repin` moves them, or the whole source literal when a count moved; starts paying on a branch that merged main
- [Request contract + engine stamp](request-contract-and-engine-stamp-2026-10-25.md) — Studio request fixture; /health engine stamp; launcher replaces a stale idle service
- [Re-set bays: keep the mouth](reset-bay-mouth-2026-10-25.md) — pro's bay letters NOT wider; he keeps a 0.51 mm mouth (n 18); `small_text_bay_mouth` (cfg.extra, OFF) cuts back the terminal that shuts it
- [Re-set grows away](reset-grow-away-2026-10-26.md) — `small_text_reset_grow_away` ON (Kent 10-26): traced-stroke widening + hold the edge facing a near neighbour; beanie x1.15→1.56
- [Re-set room and floor](reset-room-floor-2026-10-25.md) — ProSeal under 0.85: re-set widens RETRACED letters by a stale stroke tag (small_text.py:764); pro grows away from the near neighbour; tag fix alone: beanie no_room
- [Satin small shapes](satin-small-shapes-2026-10-20.md) — `satinSmallShapes` OFF (#994): cap, smallest column, junction zone; 5-point stars ARE satin on main; OFF md5 pins
- [Script strokes](script-strokes-2026-10-26.md) — `script_strokes` ON (Kent 10-26): one column per pen stroke, path on the art's INK, crosses turn with the pen; `script_strokes_drawn_width` OFF: crowded sides end at drawn width; Bridge overlap 24.9 → 19.3%
- [Sequence like the pro: order is not the gap](sequence-like-pro-2026-10-25.md) — L10 FALSE, not built: pro sews the cap rule and it costs him; ours passes over a reachable piece 18 of 145 extra cuts; gap is cuts inside a piece
- [Session ended mid-suite](session-ended-mid-suite-2026-10-20.md) — a ruled flip sat uncommitted in a lane behind a hung pytest; sweep lanes' TRACKED dirt and the newest session's last turn
- [Sew white areas](sew-white-areas-2026-10-21.md) — R11 built OFF as a Studio option; counter = untagged white in a text-cluster letter; Machine field doubles trims (stage 5)
- [Sew-out card v7](sewout-card-v7-2026-10-24.md) — only pull-by-stroke + pro values wait on fabric; BASE = ruled-unmerged flips; pull is a Fremont no-op, on MARINE it turns split satin plain like the pro
- [Short column underlay](short-column-underlay-2026-10-22.md) — `satin_underlay_short_columns` OFF: pro centre-walks 83-97% of columns at EVERY width; no 3.5 mm pitch; zigzag unsettled
- [Silhouette under-fill](silhouette-underfill-2026-10-24.md) — "pro fills it" was LAYERING, not tier (kappa 0.170 vs 0.198): ring outline filled under in the majority colour; `silhouette_underfill` OFF
- [Small bold columns](small-bold-columns-2026-10-21.md) — `lettering_columns_small_bold` OFF: 4 mm letters at 0.85 mm satin; counters closed UPSTREAM by growth
- [Small-text floor](small-text-floor-2026-10-24.md) — pro re-sets every line under ~3.2 mm to 4-4.6 mm satin, never runs/drops; #1029 missed ProSeal (design-edge halo); `small_text_cap_reach_edges` OFF
- [Small text re-set](small-text-reset-2026-10-21.md) — OFF: columns were already the pro's, SPACING was wrong; later stages undid the layout five ways; 5/S bays still close
- [True-size guard below 81 mm](small-text-true-size-guard-2026-10-15.md) — 65 mm loss = strays bug + ink-ground bug + per-glyph OCR noise; guard 0.45 x 40/wt, unsewn; ink ring OFF
- [Stage-0 flake](stage0-flake-output-alignment-2026-10-25.md) — W3-13: `cv2.magnitude` (IPP AVX2) answered by its OUTPUT buffer's alignment, not float32 box/mean/threads; `_magnitude` in float64. Hash each op under IPP paths first
- [Studio waits 600 s](studio-wait-600-2026-10-26.md) — Kent 10-26: poll waits as long as the service (from first "running" + 30 s); "Still digitizing" past 5 min; timeout says it stopped WAITING; rembg 60 -> 120 s
- [Text tagger: touches and overshoots](text-cluster-part-touching-2026-10-25.md) — Fremont OTE is a SEWN touch (gate 1); MFab IN/AND N are the misses; `text_cluster_part_touching` ON 10-27
- [Typed lettering floats](text-cut-jumps-2026-10-27.md) — `cutEveryJump` OFF: names float 1-3 mm hops on every DST path; ON buries/walks/cuts (95% cut), trims ~2x
- [The 80 mm ink link](the-80mm-ink-link-2026-10-15.md) — red circles were a STALE SERVICE; THE at 80 = rescued round linked across inks; measure at the width the Studio SENDS

- [Tie-in off](tie-in-off-2026-10-22.md) — `tie_in_off` OFF: ours already ties only at cuts; pro locks no start (1 of 68); saved ~230 stitches
- [Golden Tee TM](tm-mark-golden-tee-2026-10-26.md) — Kent: NO build. Pro re-sets the 0.94 mm TM as a 4.3x2 mm double run; we drop it in stage 2 (thin_ink 3 px floor, its strokes 2 px); only mark in 19 arts / 27 pro files; a future TM/(R) drops silently
- [Trim economy](trim-economy-2026-10-21.md) — only under-later cuts are policy (pro 9, ours 43): `trim_bury_under_later` OFF; bare gap is R11 white-as-fabric
- [Under-fill knock-outs](underfill-knockouts-2026-10-26.md) — Fremont star: a covered host-colour mark never merges; Becker: letter host stops inside the loops; Gaulke is sew_enclosed_white
- [Under-fill outer rim](underfill-outer-rim-2026-10-25.md) — a self-hosting ring: pro rims its whole edge in the fill colour; `silhouette_underfill_rim` OFF, on the SEWN edge
- [Underlay under fills](underlay-under-fills-2026-10-05.md) — gradient fills sewed with ZERO underlay; pro sews a crossing pass, built as `cross_tatami`, in no preset; preview cannot show underlay
- [Upload full-res](upload-full-res-2026-10-27.md) — SVG/GIF/EXIF JPEG go up as a 2,800-px render, OFF; 250 mm run: geometry tie, ON drops halo colours; text art times out both arms. Kent 10-27: flip held, no EXIF change
- [Wave-3 flips](wave3-flips-2026-10-26.md) — bay mouth + sew_enclosed_white ON (Kent "ship both"); bare thread rose only in ProSeal's knockdown 0.20-0.25 mm band; Studio box ticked, sends false
- [White counters open](white-counters-open-2026-10-26.md) — holes <= 1.5 holder strokes stay open
- [White faces fill](white-faces-fill-2026-10-25.md) — sew_enclosed_white made Becker 8.4x slower (white faces sewed as Column letters); `sew_enclosed_white_fields_fill` OFF fills them at 22°; house angle hides in fill_angle_deg
- [White-keyline art gate](white-keyline-art-gate-2026-10-26.md) — Kent: recipe ON only on MFab-type art (2 of 22 jobs); + fold/skip/absorb (hat 40→30, LC 52→25); absorb bared counters till rider holes kept
- [White re-rule packet](white-rerule-packet-2026-10-25.md) — under border_from_outline, white ALONE fills Becker's faces (0°) at ≤1.39x CPU; fields_fill costs up to 5.6x (MFab lc); keyline inert; census 29/31
- [Wide letters: MFab's W](wide-letters-mfab-w-2026-10-23.md) — W never reached the lane: tagger aspect 1.4 (W+E touch, 2.55; W alone 1.58); `text_cluster_wide_letters` OFF; measure MFab with main's rembg
- [Word legibility instrument](word-legibility-instrument-2026-10-24.md) — `tools/word_legibility.py`: per word, ours vs pro, chance-corrected cc; n/loc is never 0; its two holes are closed in the reach note
- [Word legibility reach](word-legibility-reach-2026-10-25.md) — all 17 words located in both files; `reach` moves where cc saturates; crop neighbours hid the pro's small words
- [L1 one tagger](word-tagger-l1-2026-10-08.md) — BUILT OFF `cfg.lettering_words`; kappa 0.907 vs text cluster 0.881 (in-sample); Kent: AFTER better under the Column lane (10-08)
