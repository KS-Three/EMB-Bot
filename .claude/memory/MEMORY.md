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
- [Apex-cut guard](apex-guard-2026-11-14.md) — `apex_guard` OFF: losing tips = hairline or a cut slid to >= 0.9 of the limit; Kent 11-14 withdrew the flip: "I want it exactly like the pros", apex_cut + guard stay OFF
- [Apex like the pro](apex-pro-2026-11-14.md) — apex_pro family ON 11-15, REVERTED OFF 11-17 (Kent: MARINE's slab caps a regression); pro's cap is narrow, inside the letter; show WHOLE WORDS before a lettering flip
- [Arc re-set, not shipped](arc-reset-2026-11-14.md) — the pro's x1.2 on Bridge came from redrawing the band and anchor, not from raising arc text (ours 3.875 mm vs cap 4.0); grunge ring 4.84 mm, lineart 8.4 mm; respine read worse; report shipped OFF
- [Bevel and ring fold](bevel-ring-fold-2026-11-13.md) — `bevel_ring_fold` OFF: Golden Tee GOLF one gold (shadow -> page, ramp -> one thread, <= 0.8 mm bands -> body), Drone ring arcs -> black; keylines kept; design change, Kent picks the default
- [Blend band thread](blend-band-2026-11-14.md) — flat_blend_band_any_scale ON (Kent 11-14 "Flip ON"): JPEG blend rim sewed as a thread on rasters not enlarged; 2 px band, Lab or RGB chord, band pixels to nearest non-band pixel
- [Block butt](block-butt-2026-11-18.md) — Becker MARINE R/N/E fans older than #1583; A counter not filled, R counter half closed; `lettering_columns_block_butt` ON 11-18 (Kent: flip, make MARINE match the pros)
- [Size-ring corner loss](border-by-size-corner-loss-2026-11-17.md) — Intel's 7 mm square = cushion under the 2.1 mm ring; `border_by_size_corner_loss` ON 11-17 (Kent "Flip ON") refuses rounding loss > 0.083 (Intel 0.12, next 0.058); 1 of 44 jobs moves
- [Border colour change](border-colour-change-2026-11-11.md) — low_poly pin 2: a drawn black line re-snapped to grey, not a border; pro borders per patch; both fixes (`resnap_hairline_never_lightens`, fix B) ruled OFF by Kent 11-11
- [Colour cap fuse split tones](color-cap-fuse-split-tones-2026-11-18.md) — Drone THERMAL E/R = two gradient bands the cap folded to one thread; `color_cap_fuse_split_tones` ON 11-18 (Kent "Flip ON"); edge-to-edge only, never a dot in a ring
- [Connector edge-walk](connector-edge-walk-2026-11-14.md) — `connectors_edge_walk` ON 11-14 (Kent "Flip ON"): the walk ordered so the next stroke covers each join; 28 designs 268/44/32 mm, trims 589/639/596
- [Connectors on top](connectors-on-top-2026-11-14.md) — Becker #14/#15 = Column-lane hops across finished satin; `lettering_columns_connectors_buried` OFF: 268 -> 44 mm, +50 trims; MFab #2 = photo border lightened to a bean loop
- [Corner-fold kappa](corner-fold-kappa-2026-11-15.md) — Becker hat kappa drop 0.337->0.289 = scorecard REGISTRATION (0.1 mm moves the 2 mm grid), not the fold: one frame +0.006/-0.008; tripwire frame pin ON 11-15 (Kent "Flip ON now")
- [Corner turn](corner-turn-2026-11-14.md) — `corner_fold_apex_side` ON 11-14 (Kent "Flip ON"): the fold takes a pointed-slot E, one column round both corners; only the 5 Becker jobs move, trims 589->584
- [Counter fan](counter-fan-2026-11-14.md) — MFab's A counter as one fanned satin, 29.9 -> 7.1 deg off the pro at 90 mm; 5.0 mm cap refuses it from ~94 mm; Kent 11-15 "Both ON, keep 5.0", flip pending
- [Cover hops](cover-hops-2026-11-17.md) — Kent 11-17 "Flip ON anyway" OVER gate 1: `lettering_columns_cover_hops` (Toat c-mouth bars); its 0.3/0.1/0.2 mm tolerances untested on cloth; no-tolerance rule dropped
- [Curve facets](curve-facets-2026-11-14.md) — lettering chords = the Column lane's W/16 simplify, not stage 4; `curve_chord_mm` + `curve_chord_stage4` OFF; Tires #0 cured (stage 4), lettering pins not measurable; next = satin end jitter
- [Dark-ink bean by width](dark-ink-bean-by-width-2026-11-16.md) — `dark_ink_bean_by_width` ON 11-16 (Kent "Flip ON"): bean vs satin by group median width (0.75 mm), not contrast 50; NOAA 0.46 mm lost strokes, EPA 0.91 mm sewed bean; 8 of 16 move
- [Dark-ink ground gaps](dark-ink-ground-gaps-2026-11-17.md) — `dark_ink_refuse_ground_gaps` OFF: field between light letters read as pen strokes; Forest Service 3 -> 2 threads
- [Digitize time bar](digitize-speed-2026-11-16.md) — Kent 11-16: 15-25 s OK, over a minute not; that was the laptop at 1.4 GHz: idle, 9 jobs 6-38 s; exact cuts -14%, md5 same; more cores 7%, not built; PARKED ("Park speed"); read the clock
- [Digitized image study](digitized-image-study-2026-11-13.md) — Kent 11-13: 108 pro pictures read by eye, 18 rules; rules 7, 12 MEASURED: pro stacks under ~5.2 mm, adds no outline the art lacks, same as us; no gap found
- [Director night 11-13](director-night-2026-11-13.md) — no single switch; eye-first gave 11 PRs; agent eye PARTIAL (0.35), now gross-fault judge (Kent 11-14); repeats/fatter disproved; Kent 11-14: 5 flips, edge-walk, apex_cut guard
- [Enclosed keeps known colour](enclosed-known-colour-2026-11-17.md) — `enclosed_white_keeps_known_colour` ON (Kent 11-17 "Flip ON"): black letter band stays black under the white sew thread; 1 of 50 census runs moves (lego 29,407 -> 26,739 st)
- [Eye-first diagnosis](eye-first-diagnosis-2026-11-13.md) — Kent 11-13: trace a bad render by eye beside the ORIGINAL first
- [Fat-ink ledger](fat-ink-ledger-2026-11-14.md) — width ledger, 7 designs: our thread area = the pro's on Becker/Bridge; width enters at stage-5 fill/column pull + stage-6 satin rails; `pull_comp_along_stitch_only`, `growth_keeps_gaps` built OFF
- [Fine bars whole](fine-bar-survive-2026-11-14.md) — `fine_bar_survive` OFF: To a T bars split (stages 2-4), kinked (AA sliver), lost at stage 5 (white under-fill covers them); broken bar redrawn from art, kept at stage 5; 5/5 pins fixed by eye
- [Flag under-fill](flag-stripe-underfill-2026-11-12.md) — flag ends/seam trio ON 11-17 (Kent); `stripe_underfill` stays OFF (ragged red, +32%); built OFF = not delivered, ask the flip
- [Flat ends, pro's construction](flat-ends-pro-2026-11-14.md) — pro edge = cross ends on the line / last cross ON a flat face; text_lean undid the mitre; `lean_flat_ends` (extra, OFF); Becker #10/#11 flat
- [Flip candidates 11-14](flip-candidates-2026-11-14.md) — inshape_piece_lift ON (Kent 11-14 "Flip ON"): Becker/MFab 13.7-60.6 mm stitches gone, +1-2 trims; apex_cut corpus 25 of 43 moved: 10 better, 4 worse, wants a guard
- [Flip run 11-15/16](flip-run-2026-11-16.md) — Kent 11-15: 19 of 20 ruled flags ON (#1565-#1599); lean_flat_ends held OFF; 8 built OFF for Kent; nightly tripwire red, re-capture in CI; flat-lane rules reach photos; combined check first
- [Foreman wake-up](foreman-wakeup-while-wave-out-2026-11-12.md) — Kent 11-12 "stale for 10 hours": 7 cloud sessions merged while the foreman idled; a wave out = set a wake-up (CronCreate sweep / gh run watch) before ending the turn, delete when empty
- [Fremont room](fremont-room-2026-11-14.md) — EST 1895 `no_room`: its own white field (0.48 of hull) read as obstacle; `small_text_reset_ground_ring` + `_bean_follows` (spines read at drawn size) OFF: date reads clean at 2x; pro 2.4x
- [Golden Tee swoosh hairline](goldentee-swoosh-hairline-2026-11-18.md) — pin (10,8): pro sews the outer hairline as ~1.0 mm satin too (ours 1.33); saw teeth = satin end caps; docs only, no flag
- [GOLF layer and shadow](golf-layer-shadow-2026-11-18.md) — Golden Tee: cap-merged teal sewed over the gold, grey fringe = blur; `cap_merged_layer_home` + `shadow_to_page` ON 11-18 (Kent 'Flip both ON'); TM = thread limit
- [Group consistency](group-consistency-2026-11-13.md) — "like things differ" pins: 2 tier straddles, 2 thread, 2 fill angle, 2 fixed; all 4 ON 11-14, body+thread with guards (Kent); decide by ink; tone = row order
- [Hairline keyline bean](hairline-keyline-bean-2026-11-13.md) — `border_from_outline_hairline_run` OFF: 0.4 mm keyline sewed 1.5 mm satin; ON = corner-exact bean
- [Inconsistency reader](inconsistency-fault-reader-2026-11-12.md) — unlike siblings: -0.04 vs pick, CI [-0.42,+0.42] = not shown; "colour" feet = fill direction lit
- [In-fill fault reader](infill-fault-reader-2026-11-11.md) — thread in art-empty spaces (sew_enclosed_white) vs Kent's 36 in-fill pins: per note 0.29 vs candidate-pick null 0.27, CI [-0.31,+0.28] = not shown; finds the region, not which spaces
- [Jag source](jag-source-2026-11-13.md) — 49 smooth pins by stage: chord facets 18, source px 10, satin construction 21 (ends 14); `outline_redraw_k` 0.75 (Kent 11-14 "Set 0.75", upscaled only)
- [K3 batch 4](k3-batch4-2026-11-17.md) — 10 more Commons logos: LEGO flag ON; parked: Mastercard ring by design, FROH no measure, no-ring-on-sharp vs pro census (26 of 46 ringed), pro corner 0.47 mm; 4 WIP branches on origin
- [K3 logo trial](k3-logo-trial-2026-11-16.md) — 30 Commons logos, Sonnet workers + foreman's eye; parked with numbers: dark-ink carve (#1610), Texaco star (one-spine satin, cover check blind), (R) blobs, USAID FROH
- [Keyline fragments](keyline-fragment-2026-11-17.md) — Drone's P/R/C dark bars = hairline remnants; `keyline_fragment_drop` 4 conditions, ON 11-17 (Kent "Flip ON"); 2 of 35 runs; 3 px bound = 3 examples
- [Launch not near](launch-not-near-rulings-2026-11-12.md) — Kent 11-12 "not ready for going live": no billing/licence/signing/hosting/legal until he says; show him the build first; "Decide later" on installer name; defect 28 close it
- [Letter-fault reader](letter-fault-reader-2026-11-11.md) — per-colour topology (counter lost/join/bay) vs Kent's 14 merged-letter pins: 0.64 vs chance 0.24 at 3 mm, CI [+0.08,+0.57] = shown; leave-one-out loses it on 3 of 6, replicate first
- [Letter-reader replication](letter-reader-replication-2026-11-12.md) — #1389 reader pre-registered; Kent sat 9 logos 11-13: letter pins on 2 items (needs 5) = no verdict, not replicated
- [Ribbon hand-back](lettering-ribbon-handback-2026-11-16.md) — `lettering_columns_ribbon_handback` ON 11-16 (Kent "Flip ON"): lane member >= 1.6x its cluster's dt_p90 median AND fill verdict goes to the ladder; moves Adidas' bar only
- [Line chain, one thread](line-chain-one-thread-2026-11-11.md) — fix B `line_chain_one_thread`: Kent 11-11 "Keep off, very little improvements were made, if any"; stays OFF, no flip, no retune; 4 of 21 rows move
- [Logo batch 2](logo-batch-2-2026-11-17.md) — 10 more Commons logos at 90 mm; CDC tagline cropped (transparent band read as a bar), fixed ON; SBA, HHS text faults seen
- [Logo batch 11-16](logo-batch-2026-11-16.md) — 10 Commons logos, final before/after only (Kent); rim fabric-edges + group size-ring ON (Kent 11-16); 6 of 22 pro jobs move, none worse; arc text NOT fixed
- [Logo batch 3](logo-batch-3-2026-11-17.md) — Coast Guard ring text buried; `dark_ink_ground_innermost` OFF; FTC 549 -> 135 s
- [Logo batch 4](logo-batch-4-2026-11-18.md) — Commerce ring text; `thin_letters_after_ground` OFF
- [Logo batch 5](logo-batch-5-2026-11-18.md) — Peace Corps R; `lettering_columns_sew_dropped_branch` OFF
- [Logo batch 6](logo-batch-6-2026-11-18.md) — overview only; lines half bold, half thin
- [Logo batch 7](logo-batch-7-2026-11-18.md) — overview only; ATF ring text lost
- [Lone glyphs](lone-glyphs-2026-11-14.md) — cursive i-dot drops at stage 3, `lone_glyph_keep` keeps it (ruled ON 11-15, pending); Jakarta's a at 70.9 = re-set no_room; Ahora's teeth stay under the ring
- [MARINE match](marine-match-2026-11-18.md) — pro construction per letter in numbers; four built-OFF flags (r_bowl, block_butt_small, a_bar, block_lean); R counter needs the pull (sew-out row 14)
- [MFab counter ring room](mfab-counter-ring-room-2026-11-14.md) — "random stitch" = photo-lane significant border on the A's 3.35 mm counter lightened to a bean loop inside its fill; `border_significant_ring_room` OFF drops it; our satin tier there was worse
- [Monarch size cliff](monarch-size-cliff-2026-11-13.md) — wing cell lost at 90.50/91.75 mm; hand-back OFF by Kent 11-14: don't flip, don't re-narrow; lane branch-drop is the real fix ("the & was better on": his eye favoured ON)
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [Off-line mark](off-line-mark-2026-11-18.md) — MFab's mark at the M's inner V (tagged into AND) sewed as crossing lane satin; `lettering_columns_off_line_mark` ON 11-18 (Kent "Flip ON"): a stacked, close, off-line member sews fill; 1 of 35 moves
- [Outline-body guard](outline-body-guard-2026-11-14.md) — group_consistent_outline_body (ON 11-14): width tie-break needs > MARGIN; redraw had tipped MFab 113.5's small line to bodies on 3.4% (riders 12 -> 0); AHORA decided by ink, kept
- [Outline frame guard](outline-frame-guard-2026-11-14.md) — k_line's red box is a field, not an outline: holder/holes area 1.0x+ keeps it a field; ticked ON 11-15 with a combined-check STOP, pending
- [Outline inlets kept](outline-inlets-2026-11-14.md) — 'shape detail lost' 18 pins: 9 satin ends (apex/flat-ends lanes), 3 an outline inlet the polygon keeps and thread sews over (gear teeth, beak, notch); `outline_inlets_kept` OFF
- [Outline loop split shared](outline-loop-split-shared-2026-11-18.md) — Becker B/E stem covered by two face loops; `outline_loop_split_shared` OFF cuts crosses at the shared line; 3 of 35 move, none worse; top V still a fan
- [Outline one band](outline-one-band-2026-11-18.md) — Becker border as the pro sews it: stem columns + ONE outer loop; `outline_one_band` OFF; 2 of 35 move; trims +12, two guard figures
- [Outline strip column](outline-strip-column-2026-11-19.md) — MFab white = keyline loops; pro: one full-width column per strip + outer loop; `outline_strip_column` OFF, stays OFF (F arm one block; word not clearly better, +4 trims)
- [Page line](page-line-open-2026-11-17.md) — Kent 11-17: `page_line_open` ON, the art's thin white line stays bare fabric as in the pro's one-thread DST; only Gaulke moves; hairline thinner than pro's (pull comp)
- [Pen stroke](pen-stroke-2026-11-13.md) — drag draws a Column/Line; Join tick built OFF (Kent 11-13): touching Columns sew as one path, own touch rule not the glyph's; same-colour shapes still stop
- [Point-touch split](point-touch-split-2026-11-14.md) — NSYNC's star touching the N at one point made one region and a satin fan; split under 0.15 mm into bodies; ticked ON 11-15, pending
- [Prime grader](prime-grader-2026-11-17.md) — Kent 11-17: session eye is the grader (tools/prime_grader.py, nightly); first run weak vs old pins (kappa 0.29 n 6); `color_cap_least_loss` ON (Drone blue)
- [Proof-read](proofread-2026-11-13.md) — `cfg.proofread` OFF metrics: thread vs art per colour in mm, tag-attributed; 20/34 pins vs 0.38; census of 34 kit items; guard `proofread_guard_clipped` OFF (qr squares back); kanji claim retracted 11-14
- [ProSeal size faults](proseal-size-2026-11-14.md) — 109.6 mm tagline 4.01 mm >= 0.9 cap: skipped, raw trace (teal sliver, A, T); 85.7 re-set reads; blend band no factor; near-cap re-set still no_room
- [Regular structure](regular-structure-2026-11-13.md) — `regular_structure` OFF: Bridge's 8 handles 0.18 -> 0.006 mm apart; census of 11: only Bridge is geometry, rest of the "alike" family = angle/tag/pull/text; group tag for later stages
- [Re-set on one baseline](reset-one-baseline-2026-11-13.md) — Jakarta/Bukit 'letters jumped': re-set grew a lowercase line's x-height and ascender clusters as 2 lines; `small_text_reset_one_baseline` + `text_cluster_solid_guard` ON (Kent 11-14)
- [Tight word space](reset-tight-word-space-2026-11-16.md) — USAID "THEAMERICAN": gap 0.484 cap < 0.5 floor; `small_text_reset_tight_word_space` reads 0.35; ON 11-16 (Kent "Flip ON"); 114 gaps, only that one moves, 7/8 jobs identical
- [Robust-PC sweep](robust-pc-sweep-2026-11-13.md) — 77 images both photo lanes: cutout runs on 14, changes all 14; CI lane = no rembg venv; THREAD_MATCH_POOR false blocks (#1460); tone pass OFF; faulthandler crash = the tool; SAM2 GPU no gain per job
- [Rope as one band](rope-band-2026-11-17.md) — Fremont rope = ~100 sub-floor blobs each a run loop; pro sews one satin band; `rope_band` ON 11-17 (Kent "Flip ON"); 2 of 35 runs move (Fremont only)
- [Round dot ring](round-dot-ring-2026-11-18.md) — Tires i dot faceted (tatami ends); `round_dot_ring` ON 11-18 rings round dots from 4 mm; 1 of 35 moves; stroke end (21.5,37) NOT cured, 3 fixes failed
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
- [Starter pack sourcing](starter-pack-sourcing-2026-11-10.md) — Kent 11-10: 12 designs, strict CC0/PD-mark art digitized by EMB-Bot itself; no open stitch files, commission or CC-BY; no logos; provenance per design
- [Starter weak spots](starter-weak-spots-2026-11-12.md) — baseball flat + monarch borders_last off SHIPPED 11-12; "drift" was a width slip: re-digitize at the original target, not manifest width_mm
- [Stroke bridge keep](stroke-bridge-keep-2026-11-14.md) — arabic stems = stage-3 absorb of same-ink crumbs; keep a chain bridging two hosts; pin 2 cured, pin 3 not; ticked ON 11-15, pending
- [Subject loss](subject-loss-2026-11-14.md) — toadstool B 76: "lettering" note now keyed on text tags; `subject_edge_recall` metric-only; photo sitting 11-15: 14/14 LOST, 0 Good = no verdict; Kent "Park it, metric only"
- [Text cluster mixed caps](text-cluster-mixed-caps-2026-11-17.md) — TOAT small A = 3 patches (T,o,A,T never tags); `text_cluster_mixed_caps` + normal pair + one line (0.5) ON 11-18 (Kent "Flip ON"); unbounded 11-17 tagged a gradient icon
- [Thin arm stop](thin-arm-stop-2026-11-17.md) — Toat Machine's M sewed a fan over each stem top where the hairline joins (stack reach-in + tip cap); `satin_thin_arm_stop` ON 11-17 (Kent "Flip ON"); 15 of 35 runs move, 2 slightly worse; a judge guards MARINE
- [Thread guard](thread-guard-2026-11-14.md) — group_consistent_thread (ON 11-14): a lone letter takes its word's thread only if it matches its own art no worse; Drone refused 7.27 -> 13.17 (grade kept D), Bridge U moves 15.29 -> 14.11
- [Transparent white in-fill](transparent-white-infill-2026-11-11.md) — `enclosed_white_skip_transparent` ON (Kent 11-11 "Flip ON"): transparent enclosed areas open unless a hollow letter body; kanji 39 open, Becker kept; moves Drone tripwire + logo_alpha
- [Under-fill ground guard](underfill-ground-guard-2026-11-16.md) — ON (Kent 11-16): a ring on the ground it would jump reads no ring; NASA orbit + stars back

- [Wedge cap](wedge-cap-2026-11-18.md) — Toat Machine h stem steps + seam: the Column lane sews a junction wedge into the stem; `lettering_columns_stem_wedge_cap` ON 11-18 (Kent "Flip ON"), hairline bound 0.6, only the hat moves of 44
- [Z joints, rail-pair bars](z-joints-rail-pair-2026-11-14.md) — and_pizza Z fanned at one joint: its top bar read CURVED (coherence 0.46, spine bent); `rail_pair_bars` (extra, OFF) reads two long parallel rails as a bar; guard still refuses Z tips