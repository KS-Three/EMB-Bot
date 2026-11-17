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
**A PR that ADDS index characters must leave 2,500 under the ceiling** (`GROW_HEADROOM`, tested against the merge base); if it fails, archive the oldest lines.

- [Memory archive: through 10-26](MEMORY-archive.md) — NOT auto-loaded: history through 10-15 + standing rulings (fill rows 0.15, DST axis fixed, Ink/Stitch clean-room, Ember teardowns)
- [Opus team architecture](../../docs/superpowers/plans/2026-10-23-opus-team-architecture.md) — the plan a fresh director runs from: method, state, ranked queue L1-L10 / I1-I6, Kent's open decisions, brief template, traps
- [No Fable agents](agents-cheap-models-2026-11-02.md) — Kent 11-02 "don't release fable agents, we should be saving on usage": every start_session / Agent passes model (Sonnet default, Haiku read-only); a Fable director dispatches, never spawns Fable
- [Apex-cut guard](apex-guard-2026-11-14.md) — `apex_guard` OFF: losing tips = hairline or a cut slid to >= 0.9 of the limit; Kent 11-14 withdrew the flip: "I want it exactly like the pros", apex_cut + guard stay OFF
- [Apex like the pro](apex-pro-2026-11-14.md) — `lettering_columns_apex_pro` OFF: down V = right leg owns the point, level crosses from it up; left leg fans to a split on that leg's edge + stem top; `tools/apex_pro.py measure` angle err + seam
- [Arc re-set, not shipped](arc-reset-2026-11-14.md) — the pro's x1.2 on Bridge came from redrawing the band and anchor, not from raising arc text (ours 3.875 mm vs cap 4.0); grunge ring 4.84 mm, lineart 8.4 mm; respine read worse; report shipped OFF
- [Bevel and ring fold](bevel-ring-fold-2026-11-13.md) — `bevel_ring_fold` OFF: Golden Tee GOLF one gold (shadow -> page, ramp -> one thread, <= 0.8 mm bands -> body), Drone ring arcs -> black; keylines kept; design change, Kent picks the default
- [Big-size speed](big-size-speed-2026-11-11.md) — 300 mm: hoist 320 -> 26 s (STRtree over parts), build fns 241 -> 51 s; 198 mm plan 539 -> 431 s (angle scan in numpy, bridge memo); md5 same; no exact cut over 25 s left
- [Blend band thread](blend-band-2026-11-14.md) — flat_blend_band_any_scale ON (Kent 11-14 "Flip ON"): JPEG blend rim sewed as a thread on rasters not enlarged; 2 px band, Lab or RGB chord, band pixels to nearest non-band pixel
- [Blend shade median](blend-shade-median-2026-11-09.md) — defect 28: Fremont fixed 11-07 (stale scope line); summit 0111 = mean of a 9-sample speckled end bucket; `blend_shade_median` ON (Kent 11-09) clears it, 20 entries md5 same
- [Border colour change](border-colour-change-2026-11-11.md) — low_poly pin 2: a drawn black line re-snapped to grey, not a border; pro borders per patch; both fixes (`resnap_hairline_never_lightens`, fix B) ruled OFF by Kent 11-11
- [Bridge anchor limbs](bridge-anchor-wave-weld-2026-11-10.md) — "extra arms/legs" = the waves welded to the anchor in the 400 px JPEG (gaps < 1 px), one black component from stage 2; Kent 11-10: keep as manual edit, no build
- [Compare ends on regenerate](compare-ends-on-regenerate-2026-11-08.md) — Kent 11-08 "Keep as is": Compare view (#1345) is an Original sub-mode, a regeneration ends it; don't build survival
- [Connector edge-walk](connector-edge-walk-2026-11-14.md) — `connectors_edge_walk` ON 11-14 (Kent "Flip ON"): the walk ordered so the next stroke covers each join; 28 designs 268/44/32 mm, trims 589/639/596
- [Connectors on top](connectors-on-top-2026-11-14.md) — Becker #14/#15 = Column-lane hops across finished satin; `lettering_columns_connectors_buried` OFF: 268 -> 44 mm, +50 trims; MFab #2 = photo border lightened to a bean loop
- [Corner-fold kappa](corner-fold-kappa-2026-11-15.md) — Becker hat kappa drop 0.337->0.289 = scorecard REGISTRATION (0.1 mm moves the 2 mm grid), not the fold: one frame +0.006/-0.008; tripwire frame pin ON 11-15 (Kent "Flip ON now")
- [Corner turn](corner-turn-2026-11-14.md) — `corner_fold_apex_side` ON 11-14 (Kent "Flip ON"): the fold takes a pointed-slot E, one column round both corners; only the 5 Becker jobs move, trims 589->584
- [Counter fan](counter-fan-2026-11-14.md) — MFab's A counter as one fanned satin, 29.9 -> 7.1 deg off the pro at 90 mm; 5.0 mm cap refuses it from ~94 mm; Kent 11-15 "Both ON, keep 5.0", flip pending
- [Curve facets](curve-facets-2026-11-14.md) — lettering chords = the Column lane's W/16 simplify, not stage 4; `curve_chord_mm` + `curve_chord_stage4` OFF; Tires #0 cured (stage 4), lettering pins not measurable; next = satin end jitter
- [Dark-ink bean by width](dark-ink-bean-by-width-2026-11-16.md) — `dark_ink_bean_by_width` ON 11-16 (Kent "Flip ON"): bean vs satin by group median width (0.75 mm), not contrast 50; NOAA 0.46 mm lost strokes, EPA 0.91 mm sewed bean; 8 of 16 move
- [Dark-ink ground gaps](dark-ink-ground-gaps-2026-11-17.md) — `dark_ink_refuse_ground_gaps` OFF: field between light letters read as pen strokes; Forest Service 3 -> 2 threads
- [Defect-marks sitting 2](defect-marks-sitting-2-2026-11-11.md) — 21 Commons logos, 115 pins, hold-out for the letter reader: frozen rule found pins on 1 logo (26/30 vs 0.13) = no verdict; his words moved to extra in-fill, inconsistency, missing, flow
- [Defect-marks sitting](defect-marks-sitting-2026-11-10.md) — why eye != yardstick; `tools/defect_marks.py` asks where + what (pins); SAT 11-10: 15 items, 95 pins, smooth edges + closed/merged letters lead, 4 photos Terrible; docs/defect-marks-2026-11-10
- [Digitize time bar](digitize-speed-2026-11-16.md) — Kent 11-16: 15-25 s OK, over a minute not; that was the laptop at 1.4 GHz: idle, 9 jobs 6-38 s; exact cuts -14%, md5 same; more cores 7%, not built; PARKED ("Park speed"); read the clock
- [Digitized image study](digitized-image-study-2026-11-13.md) — Kent 11-13: 108 pro pictures read by eye, 18 rules; rules 7, 12 MEASURED: pro stacks under ~5.2 mm, adds no outline the art lacks, same as us; no gap found
- [Director night 11-13](director-night-2026-11-13.md) — no single switch; eye-first gave 11 PRs; agent eye PARTIAL (0.35), now gross-fault judge (Kent 11-14); repeats/fatter disproved; Kent 11-14: 5 flips, edge-walk, apex_cut guard
- [Edge-fault reader](edge-fault-reader-2026-11-10.md) — edge_wobble flag locations vs Kent's 20 smooth-edge pins: 0.60 vs chance 0.49 at 3 mm, CI crosses 0 = not shown; harness `fault_reader_harness.py` reusable; next reader closed/merged letters
- [External sourcing 11-06](external-repo-sourcing-2026-11-06.md) — tesserocr 251 -> 5 ms per OCR read, ADOPTED 11-06 (board geometry identical, cc <4 -0.08 = one drone word; 5.5.3 vs CI 5.3.4 open); clipper2-ts on offsetRing trigger; bench filum DST only
- [Eye-first diagnosis](eye-first-diagnosis-2026-11-13.md) — Kent 11-13: trace a bad render by eye beside the ORIGINAL first
- [Fat-ink ledger](fat-ink-ledger-2026-11-14.md) — width ledger, 7 designs: our thread area = the pro's on Becker/Bridge; width enters at stage-5 fill/column pull + stage-6 satin rails; `pull_comp_along_stitch_only`, `growth_keeps_gaps` built OFF
- [Fill-slant sitting](fill-slant-sitting-2026-11-09.md) — Kent blind, 16 live pro pairs: slant ON 0, OFF 7, tie 9 = favours OFF (4 designs, Becker 4 of 7); "Keep OFF, record"; pro-direction kappa gain did not read better
- [Fine bars whole](fine-bar-survive-2026-11-14.md) — `fine_bar_survive` OFF: To a T bars split (stages 2-4), kinked (AA sliver), lost at stage 5 (white under-fill covers them); broken bar redrawn from art, kept at stage 5; 5/5 pins fixed by eye
- [Flag under-fill](flag-stripe-underfill-2026-11-12.md) — Kent 11-12, OFF: `stripe_underfill` white fill under red satin (3.86/3.96 vs 4.67/3.14), +32%; `satin_free_end_chord_aim` squares ends
- [Flat ends, pro's construction](flat-ends-pro-2026-11-14.md) — pro edge = cross ends on the line / last cross ON a flat face; text_lean undid the mitre; `lean_flat_ends` (extra, OFF); Becker #10/#11 flat
- [Flat soft ramp](flat-fringe-soft-ramp-2026-11-06.md) — Bridge flat-lane blue split = 3-src-px JPEG edge at x3.25: page band 5 -> 11 + ramp dissolve (kept-colour chords); both OFF, enlarged only; 4 inks, hat trims 157 -> 23
- [Flip candidates 11-14](flip-candidates-2026-11-14.md) — inshape_piece_lift ON (Kent 11-14 "Flip ON"): Becker/MFab 13.7-60.6 mm stitches gone, +1-2 trims; apex_cut corpus 25 of 43 moved: 10 better, 4 worse, wants a guard
- [Flip run 11-15/16](flip-run-2026-11-16.md) — Kent 11-15: 19 of 20 ruled flags ON (#1565-#1599); lean_flat_ends held OFF; 8 built OFF for Kent; nightly tripwire red, re-capture in CI; flat-lane rules reach photos; combined check first
- [Foreman merge/push findings](foreman-merge-push-findings-2026-11-08.md) — 62 PRs 11-07/08: squash branches refuse `branch -d`; test.fail() expected; empty log != green; fix-lane branch needs a finding index
- [Foreman merges, workers bypass](foreman-merges-and-bypass-2026-11-06.md) — Kent 11-06 "i'm not merging anything, you do it": foreman merges CLEAN PRs, arms BLOCKED, never --admin; workers bypassPermissions where settable; overrides CLAUDE.md
- [Foreman wake-up](foreman-wakeup-while-wave-out-2026-11-12.md) — Kent 11-12 "stale for 10 hours": 7 cloud sessions merged while the foreman idled; a wave out = set a wake-up (CronCreate sweep / gh run watch) before ending the turn, delete when empty
- [Free-digitizer follow-ups](free-digitizer-followups-2026-11-05.md) — Kent 11-05 on the 7 untaken ideas: score metrics-only, recount only, zip only, re-read BLOCKS, TSP skip, heatstitch floor row ADD, literature parked
- [Fremont room](fremont-room-2026-11-14.md) — EST 1895 `no_room`: its own white field (0.48 of hull) read as obstacle; `small_text_reset_ground_ring` + `_bean_follows` (spines read at drawn size) OFF: date reads clean at 2x; pro 2.4x
- [Group consistency](group-consistency-2026-11-13.md) — "like things differ" pins: 2 tier straddles, 2 thread, 2 fill angle, 2 fixed; all 4 ON 11-14, body+thread with guards (Kent); decide by ink; tone = row order
- [Hairline keyline bean](hairline-keyline-bean-2026-11-13.md) — `border_from_outline_hairline_run` OFF: 0.4 mm keyline sewed 1.5 mm satin; ON = corner-exact bean
- [Inconsistency reader](inconsistency-fault-reader-2026-11-12.md) — unlike siblings: -0.04 vs pick, CI [-0.42,+0.42] = not shown; "colour" feet = fill direction lit
- [In-fill fault reader](infill-fault-reader-2026-11-11.md) — thread in art-empty spaces (sew_enclosed_white) vs Kent's 36 in-fill pins: per note 0.29 vs candidate-pick null 0.27, CI [-0.31,+0.28] = not shown; finds the region, not which spaces
- [Jag source](jag-source-2026-11-13.md) — 49 smooth pins by stage: chord facets 18, source px 10, satin construction 21 (ends 14); `outline_redraw_k` 0.75 (Kent 11-14 "Set 0.75", upscaled only)
- [Kent's judging rubric](kent-judging-rubric-2026-11-07.md) — his 22 reasons: lettering follows pen strokes, smooth curves, straight uprights, no blobs; first picks noisy; phase B judge FAILED (#1363)
- [Lagging areas top 3](lagging-areas-2026-11-06.md) — Kent 11-06: yardstick / satin-fill 0.387 / trims; 3 Sonnet notes in docs/lagging-areas-2026-11-06: no external repo fixes any, instruments + oracles first; polygon_axis.py already exists
- [Launch not near](launch-not-near-rulings-2026-11-12.md) — Kent 11-12 "not ready for going live": no billing/licence/signing/hosting/legal until he says; show him the build first; "Decide later" on installer name; defect 28 close it
- [Letter-fault reader](letter-fault-reader-2026-11-11.md) — per-colour topology (counter lost/join/bay) vs Kent's 14 merged-letter pins: 0.64 vs chance 0.24 at 3 mm, CI [+0.08,+0.57] = shown; leave-one-out loses it on 3 of 6, replicate first
- [Letter-reader replication](letter-reader-replication-2026-11-12.md) — #1389 reader pre-registered; Kent sat 9 logos 11-13: letter pins on 2 items (needs 5) = no verdict, not replicated
- [Ribbon hand-back](lettering-ribbon-handback-2026-11-16.md) — `lettering_columns_ribbon_handback` OFF: fill-verdict lane members to the ladder; fixes Texaco wedges + Adidas bar, but 31 of 39 are real bold letters (Becker, Visa, Canon); Kent's flip
- [Line chain, one thread](line-chain-one-thread-2026-11-11.md) — fix B `line_chain_one_thread`: Kent 11-11 "Keep off, very little improvements were made, if any"; stays OFF, no flip, no retune; 4 of 21 rows move
- [Local lanes fill the disk](local-lanes-fill-disk-2026-11-08.md) — ~25 local lanes (900 MB node_modules each) took C: to 143 MB; remove a lane on merge, stop under 10 GB free
- [Logo batch 11-16](logo-batch-2026-11-16.md) — 10 Commons logos, final before/after only (Kent); rim fabric-edges + group size-ring ON (Kent 11-16); 6 of 22 pro jobs move, none worse; arc text NOT fixed
- [Lone glyphs](lone-glyphs-2026-11-14.md) — cursive i-dot drops at stage 3, `lone_glyph_keep` keeps it (ruled ON 11-15, pending); Jakarta's a at 70.9 = re-set no_room; Ahora's teeth stay under the ring
- [MFab AND re-check](mfab-and-recheck-2026-11-06.md) — 10-25 brief stale: on main 7ee2d98a the hollow A is gone (0 bean tags, A/N/D satin 126/110/120) since bean_ink_outlined_letters + bean_only_lines ON 10-27; no flag built; keyline art = MFab only
- [MFab counter ring room](mfab-counter-ring-room-2026-11-14.md) — "random stitch" = photo-lane significant border on the A's 3.35 mm counter lightened to a bean loop inside its fill; `border_significant_ring_room` OFF drops it; our satin tier there was worse
- [Monarch size cliff](monarch-size-cliff-2026-11-13.md) — wing cell lost at 90.50/91.75 mm; hand-back OFF by Kent 11-14: don't flip, don't re-narrow; lane branch-drop is the real fix ("the & was better on": his eye favoured ON)
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [Outline-body guard](outline-body-guard-2026-11-14.md) — group_consistent_outline_body (ON 11-14): width tie-break needs > MARGIN; redraw had tipped MFab 113.5's small line to bodies on 3.4% (riders 12 -> 0); AHORA decided by ink, kept
- [Outline fonts on demand](outline-fonts-on-demand-2026-11-06.md) — Kent 11-06: TTF/OTF fonts sewn by the service via the Column lane (POST /lettering), 21 OFL families, `outline:<key>`; 07-24 ruling = browser trace
- [Outline frame guard](outline-frame-guard-2026-11-14.md) — k_line's red box is a field, not an outline: holder/holes area 1.0x+ keeps it a field; ticked ON 11-15 with a combined-check STOP, pending
- [Outline inlets kept](outline-inlets-2026-11-14.md) — 'shape detail lost' 18 pins: 9 satin ends (apex/flat-ends lanes), 3 an outline inlet the polygon keeps and thread sews over (gear teeth, beak, notch); `outline_inlets_kept` OFF
- [Pen stroke](pen-stroke-2026-11-13.md) — drag draws a Column/Line; Join tick built OFF (Kent 11-13): touching Columns sew as one path, own touch rule not the glyph's; same-colour shapes still stop
- [Point-touch split](point-touch-split-2026-11-14.md) — NSYNC's star touching the N at one point made one region and a satin fan; split under 0.15 mm into bodies; ticked ON 11-15, pending
- [Preflight score](preflight-score-2026-11-05.md) — 0-100 `score` ALREADY existed (grade derives from it; Studio QualityReport.svelte:189 shows it); 11-05 added only the mapping comment, pins, tool columns. Don't build a 2nd
- [Proof-read](proofread-2026-11-13.md) — `cfg.proofread` OFF metrics: thread vs art per colour in mm, tag-attributed; 20/34 pins vs 0.38; census of 34 kit items; guard `proofread_guard_clipped` OFF (qr squares back); kanji claim retracted 11-14
- [ProSeal size faults](proseal-size-2026-11-14.md) — 109.6 mm tagline 4.01 mm >= 0.9 cap: skipped, raw trace (teal sliver, A, T); 85.7 re-set reads; blend band no factor; near-cap re-set still no_room
- [Regular structure](regular-structure-2026-11-13.md) — `regular_structure` OFF: Bridge's 8 handles 0.18 -> 0.006 mm apart; census of 11: only Bridge is geometry, rest of the "alike" family = angle/tag/pull/text; group tag for later stages
- [Re-set on one baseline](reset-one-baseline-2026-11-13.md) — Jakarta/Bukit 'letters jumped': re-set grew a lowercase line's x-height and ascender clusters as 2 lines; `small_text_reset_one_baseline` + `text_cluster_solid_guard` ON (Kent 11-14)
- [Tight word space](reset-tight-word-space-2026-11-16.md) — USAID "THEAMERICAN": gap 0.484 cap < 0.5 floor; `small_text_reset_tight_word_space` OFF reads 0.35; 114 gaps, only that one moves, 7/8 jobs identical; flip Kent's
- [Robust-PC sweep](robust-pc-sweep-2026-11-13.md) — 77 images both photo lanes: cutout runs on 14, changes all 14; CI lane = no rembg venv; THREAD_MATCH_POOR false blocks (#1460); tone pass OFF; faulthandler crash = the tool; SAM2 GPU no gain per job
- [Satin/fill oracle split](satin-fill-oracle-2026-11-06.md) — C3 bound: cutting our grounds along the pro's 10+ cell blobs lifts mean kappa 0.381 -> 0.482 (5 cells 0.561, 20 cells 0.427): no verdict; reads the pro, a max
- [Satin push keeps gaps](satin-push-keeps-gaps-2026-11-14.md) — 23 merged-letter groups traced; rail push held counters not bays/neighbours; `satin_push_keeps_gaps` OFF: Gaulke E 0.10 -> 0.36 at floor 0.5 = pro; floor Kent's pick
- [Scorecard recapture 11-12](scorecard-recapture-2026-11-12.md) — ruler 292418a8 -> ffefc3b1, run 43253187536: 10/20/8/10/4 -> 8/20/6/10/8, mean 71.9 -> 68.7 FELL; flag-off CI arms name #1301, #1263, #1329, #1378; 1 row part unattributed
- [Second digitize timing](second-digitize-timing-2026-11-13.md) — 11-12's 44 s = laptop contention (same run 19 -> 55 s as load moved); Cancel held the worker 1.4-5.5 s: seams added in neck splits, letterform priors, keyline -> 0.2 s
- [Shaped outline gear](shaped-outline-gear-2026-11-13.md) — `border_from_outline_follow_shape` ON (Kent 11-16): gear laid out from its OUTER edge, ring read off a chord
- [Sliver prune](sliver-prune-2026-11-10.md) — `sliver_prune` OFF: Pooh 54 mm white edge runs = page-halo masks, red arm spike = shirt tendril on a crease; enlarged x1.25+ only; 80 mm sheet 20/20 same; his on-screen run was gradient, not flat
- [Small bowls](small-bowls-2026-11-14.md) — Bukit's beyondcoal bowls lost in the cross floor; `lettering_columns_ring_floor` widens a ring's thin crosses (o 0.70 -> 1.00 cover); ticked ON 11-15, pending
- [Small marks](small-marks-2026-11-14.md) — Bukit's 0.5 mm dots (stage 3) and neon (R) gaps (stage 1); pro's smallest block 1.0 mm = gate 1; tiny_detail_keep stays OFF, tiny run marks not built (Kent 11-15)
- [Small-text hand-over](small-text-handover-2026-11-14.md) — ProSeal's 4.01 mm cap line fell between restore and re-set; retrace 0.9-1.25 caps at true size; Kent 11-15 "Flip both ON", pending
- [Space fault reader](space-fault-reader-2026-11-12.md) — bays/gaps filled vs 44 letter pins: +0.32 over pick, CI [+0.22,+0.47] = shown, not a hold-out; 1112 replication = no verdict (2 of 9 items pinned)
- [Speck prune](speck-prune-2026-11-14.md) — missing/invented pins traced: kanji in-fill (29) cured on main; low_poly 7 black dots = stage-3 rescue keeping hairline crossings; `speck_prune` OFF cures 7/7
- [Stacked PR trap](stacked-pr-auto-merge-trap-2026-11-06.md) — #1259 stacked on #1255's head with auto-merge armed merged INTO that branch after #1255 landed (deleteBranchOnMerge off, no retarget); base follow-ups on main, never arm a stacked PR
- [Starter pack sourcing](starter-pack-sourcing-2026-11-10.md) — Kent 11-10: 12 designs, strict CC0/PD-mark art digitized by EMB-Bot itself; no open stitch files, commission or CC-BY; no logos; provenance per design
- [Starter weak spots](starter-weak-spots-2026-11-12.md) — baseball flat + monarch borders_last off SHIPPED 11-12; "drift" was a width slip: re-digitize at the original target, not manifest width_mm

- [Stroke bridge keep](stroke-bridge-keep-2026-11-14.md) — arabic stems = stage-3 absorb of same-ink crumbs; keep a chain bridging two hosts; pin 2 cured, pin 3 not; ticked ON 11-15, pending
- [Subject loss](subject-loss-2026-11-14.md) — toadstool B 76: "lettering" note now keyed on text tags; `subject_edge_recall` metric-only; photo sitting 11-15: 14/14 LOST, 0 Good = no verdict; Kent "Park it, metric only"
- [Thread guard](thread-guard-2026-11-14.md) — group_consistent_thread (ON 11-14): a lone letter takes its word's thread only if it matches its own art no worse; Drone refused 7.27 -> 13.17 (grade kept D), Bridge U moves 15.29 -> 14.11
- [Defect 28 leftovers](thread-match-leftovers-2026-11-10.md) — bridge_bar 3, screenshot 1, stub 0722 = CHART LIMITS: best of 398 spools still 10.6-29.4 dE00 per pixel; nothing built; excess-over-chart yardstick priced only
- [Transparent white in-fill](transparent-white-infill-2026-11-11.md) — `enclosed_white_skip_transparent` ON (Kent 11-11 "Flip ON"): transparent enclosed areas open unless a hollow letter body; kanji 39 open, Becker kept; moves Drone tripwire + logo_alpha
- [Under-fill ground guard](underfill-ground-guard-2026-11-16.md) — ON (Kent 11-16): a ring on the ground it would jump reads no ring; NASA orbit + stars back
- [Eye, 100 pairs](vlm-judge-100-2026-11-06.md) — Opus session, 99 pairs: kappa +0.34 [+0.17, +0.49] above chance; sides +0.65 n 22; proposal only
- [Vision pre-screen](vlm-prescreen-2026-11-06.md) — threshold 4: settled kappa +0.39 (39/54), +0.29 (67/99), both above chance; row PROPOSAL only; tie label holds 13/29, 18/40 side picks
- [DreamSim yardstick](yardstick-dreamsim-2026-11-08.md) — 11-08: +0.197 on 100 pooled pro pairs, NOT replicated on fresh sitting (+0.099, CI crosses 0) or 1102 hold-out (-0.127); no stand-in for Kent
- [Z joints, rail-pair bars](z-joints-rail-pair-2026-11-14.md) — and_pizza Z fanned at one joint: its top bar read CURVED (coherence 0.46, spine bent); `rail_pair_bars` (extra, OFF) reads two long parallel rails as a bar; guard still refuses Z tips
