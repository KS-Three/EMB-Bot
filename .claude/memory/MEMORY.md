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
- [Add hole](add-hole-2026-11-05.md) — PR 3: Add hole draws a polygon in a digitized shape, appended to holes_override; refusal reuses boundaryIssues wording, draft stays open; e2e (h1)-(h6)
- [No Fable agents](agents-cheap-models-2026-11-02.md) — Kent 11-02 "don't release fable agents, we should be saving on usage": every start_session / Agent passes model (Sonnet default, Haiku read-only); a Fable director dispatches, never spawns Fable
- [Bash heredoc Python trap](bash-heredoc-python-repl-trap-2026-11-02.md) — Windows Bash tool `python - <<'E'` lost stdin: Python 3.14 fell into _pyrepl, one core for 26 h (3.68 GB of prompts); a `||` fallback respawned it when killed. Run a script FILE
- [Big-size speed](big-size-speed-2026-11-11.md) — 300 mm: hoist 320 -> 26 s (STRtree over parts), build fns 241 -> 51 s; 198 mm plan 539 -> 431 s (angle scan in numpy, bridge memo); md5 same; no exact cut over 25 s left
- [Blend shade median](blend-shade-median-2026-11-09.md) — defect 28: Fremont fixed 11-07 (stale scope line); summit 0111 = mean of a 9-sample speckled end bucket; `blend_shade_median` ON (Kent 11-09) clears it, 20 entries md5 same
- [Border colour change](border-colour-change-2026-11-11.md) — low_poly pin 2: a drawn black line re-snapped to grey, not a border; pro borders per patch; both fixes (`resnap_hairline_never_lightens`, fix B) ruled OFF by Kent 11-11
- [Bridge anchor limbs](bridge-anchor-wave-weld-2026-11-10.md) — "extra arms/legs" = the waves welded to the anchor in the 400 px JPEG (gaps < 1 px), one black component from stage 2; Kent 11-10: keep as manual edit, no build
- [Cloud wave 11-06](cloud-wave-2026-11-06.md) — Kent 11-06 "10 agents in cloud": yardstick scorer, Euler census, C2 vote, stage-7 speed, nest guard, PR 1284, e2e apt, offsetRing test, dropped-element v2, shards; Remote Control turn cannot start sessions
- [Colour cap on the sewn design](colour-cap-sewn-2026-10-29.md) — census item 3 misnamed the hole: sew-white recolours AFTER the cap + blend bands snap chart-wide; `color_cap_sewn` ON 11-01 re-caps final regions, folds strays on blocks
- [Compare ends on regenerate](compare-ends-on-regenerate-2026-11-08.md) — Kent 11-08 "Keep as is": Compare view (#1345) is an Original sub-mode, a regeneration ends it; don't build survival
- [DADE teardown](dade-app-teardown-2026-11-04.md) — 10 px/mm fixed, tatami, trims OFF; at its 36.7 mm its file read better than ours (flat = blob); at 113.5 ours reads, DADE can't
- [Dark ink bean](dark-ink-bean-2026-10-28.md) — `dark_ink_bean` ON 10-29 (Kent, Pooh): dark read within 50 dE00 of its ground beans along its skeleton, ground sews through; Fremont wordmark (100) stays satin
- [Dark-ink floor rescue](dark-ink-floor-rescue-2026-11-03.md) — `dark_ink_floor_rescue` ON 11-04 (Kent): Pooh's lost letter = dark-read KERNEL (min_detail_mm), not stage 3; 2nd read at 1.0 mm unioned; ON reads every thin stroke
- [Dark read refusal](dark-read-refusal-2026-10-28.md) — `dark_ink_refuse_strays` OFF: edge (4 px) or not-under-ring reads refused; #1172's 10 not-ink rows = the 10 at the frame (its art window stretched)
- [Defect-marks sitting 2](defect-marks-sitting-2-2026-11-11.md) — 21 Commons logos, 115 pins, hold-out for the letter reader: frozen rule found pins on 1 logo (26/30 vs 0.13) = no verdict; his words moved to extra in-fill, inconsistency, missing, flow
- [Defect-marks sitting](defect-marks-sitting-2026-11-10.md) — why eye != yardstick; `tools/defect_marks.py` asks where + what (pins); SAT 11-10: 15 items, 95 pins, smooth edges + closed/merged letters lead, 4 photos Terrible; docs/defect-marks-2026-11-10
- [Digitized image study](digitized-image-study-2026-11-13.md) — Kent 11-13: 108 pro pictures read by eye, 18 rules; rule 7 MEASURED: pro stacks under ~5.2 mm, we stack too (not on photo classes); real gap = no contrast halo
- [Dropped-element finding](dropped-element-finding-2026-11-01.md) — `ARTWORK_ELEMENT_DROPPED`: preflight reads clipped / unsewn-enclosed / colour-cap-folded / stage-4 drops by AREA; floor 5 mm2, block at 10%; fires on 2 rows Kent graded Good/Great
- [Edge cap re-measured](edge-cap-remeasure-2026-10-29.md) — defect 19: edge 0-4% bare with NO cap (rim + border_by_size); swing gone; default "none" + defect closed (Kent 10-29, #1192)
- [Edge-fault reader](edge-fault-reader-2026-11-10.md) — edge_wobble flag locations vs Kent's 20 smooth-edge pins: 0.60 vs chance 0.49 at 3 mm, CI crosses 0 = not shown; harness `fault_reader_harness.py` reusable; next reader closed/merged letters
- [Ember reshape measured](ember-reshape-measured-2026-11-04.md) — Ember's drag moves 1 point, 0.0 px on the rest; accept/reject session; built: exact drag + Done/Discard; open: sparse nodes, insert, smooth toggle
- [Export read-back](export-readback-2026-11-05.md) — every export re-read, download BLOCKED on mismatch (Kent 11-05): service pystitch 500 + headers, browser DST/EXP/PES; skipped checks per format; 20k stitches +7-13 ms browser
- [Download all zip](export-zip-2026-11-05.md) — Kent 11-05 zip only: 7 formats + PDF + PNG + threads.txt via the verified path; any one fails = nothing saved; no PEC/U01; 24k stitches 2.2-2.6 s, 1.08 MB
- [External sourcing 11-06](external-repo-sourcing-2026-11-06.md) — tesserocr 251 -> 5 ms per OCR read, ADOPTED 11-06 (board geometry identical, cc <4 -0.08 = one drone word; 5.5.3 vs CI 5.3.4 open); clipper2-ts on offsetRing trigger; bench filum DST only
- [Eye-first diagnosis](eye-first-diagnosis-2026-11-13.md) — Kent 11-13: trace a bad render by eye beside the ORIGINAL first
- [Seam order flip](fill-seam-order-flip-2026-10-30.md) — fill_seam_order + fill_bridge_cut_exposed ON together (Kent 10-30): ridges 0, exposed travel down, trims up; seam order alone adds exposure
- [Fill-slant sitting](fill-slant-sitting-2026-11-09.md) — Kent blind, 16 live pro pairs: slant ON 0, OFF 7, tie 9 = favours OFF (4 designs, Becker 4 of 7); "Keep OFF, record"; pro-direction kappa gain did not read better
- [Flag under-fill](flag-stripe-underfill-2026-11-12.md) — Kent 11-12, OFF: `stripe_underfill` white fill under red satin (3.86/3.96 vs 4.67/3.14), +32%; `satin_free_end_chord_aim` squares ends
- [Flag stripes](flag-stripes-seam-cap-2026-10-30.md) — equal art sewed 4.53/3.57: rail pull lands after stage 5's clip; `satin_seam_hold` + `satin_cap_skew_inset` OFF; underlay was never missing
- [Flat soft ramp](flat-fringe-soft-ramp-2026-11-06.md) — Bridge flat-lane blue split = 3-src-px JPEG edge at x3.25: page band 5 -> 11 + ramp dissolve (kept-colour chords); both OFF, enlarged only; 4 inks, hat trims 157 -> 23
- [Flat page fringe](flat-page-fringe-2026-11-03.md) — `flat_page_fringe_exclude` OFF: page-edge blend leaves the flat fit + chain rescue; Pooh pale flecks 59 -> 25; band = upscale+1; page = median; + outline INNER blend (B)
- [Foreman merge/push findings](foreman-merge-push-findings-2026-11-08.md) — 62 PRs 11-07/08: squash branches refuse `branch -d`; test.fail() expected; empty log != green; fix-lane branch needs a finding index
- [Foreman merges, workers bypass](foreman-merges-and-bypass-2026-11-06.md) — Kent 11-06 "i'm not merging anything, you do it": foreman merges CLEAN PRs, arms BLOCKED, never --admin; workers bypassPermissions where settable; overrides CLAUDE.md
- [Foreman wake-up](foreman-wakeup-while-wave-out-2026-11-12.md) — Kent 11-12 "stale for 10 hours": 7 cloud sessions merged while the foreman idled; a wave out = set a wake-up (CronCreate sweep / gh run watch) before ending the turn, delete when empty
- [Free-digitizer follow-ups](free-digitizer-followups-2026-11-05.md) — Kent 11-05 on the 7 untaken ideas: score metrics-only, recount only, zip only, re-read BLOCKS, TSP skip, heatstitch floor row ADD, literature parked
- [Free digitizer survey](free-digitizer-survey-2026-11-04.md) — Kent 11-04: 40+ tools, no free desktop auto-digitizer; bench tier 1 heatstitch (MIT) + openstitch (AGPL, output only) + Nuizu (CLI); Hatch 30-export list approved, Wilcom skipped (hardware)
- [Hairline keyline bean](hairline-keyline-bean-2026-11-13.md) — `border_from_outline_hairline_run` OFF: 0.4 mm keyline sewed 1.5 mm satin; ON = corner-exact bean
- [heatstitch floor row](heatstitch-floor-row-2026-11-05.md) — `tripwire floor`: ours' sttype kappa beside heatstitch's untuned rule per job, margin, flag < 0.05 (never fails); laptop-only, n/a without scratch_bench files
- [Holes override](holes-override-2026-11-03.md) — contract v1.9 `holes_override` (service half): replaces interior rings, [] = solid, absent = carry-over; Studio half next
- [Holes in the Studio](holes-studio-2026-11-03.md) — holes drawn/edited like the outline, Delete hole, `holes_override` only when a hole was edited; a 3 mm drag shares with a chamfer partner, arrows move one; no add-hole yet
- [Inconsistency reader](inconsistency-fault-reader-2026-11-12.md) — unlike siblings: -0.04 vs pick, CI [-0.42,+0.42] = not shown; "colour" feet = fill direction lit
- [In-fill fault reader](infill-fault-reader-2026-11-11.md) — thread in art-empty spaces (sew_enclosed_white) vs Kent's 36 in-fill pins: per note 0.29 vs candidate-pick null 0.27, CI [-0.31,+0.28] = not shown; finds the region, not which spaces
- [Kent's judging rubric](kent-judging-rubric-2026-11-07.md) — his 22 reasons: lettering follows pen strokes, smooth curves, straight uprights, no blobs; first picks noisy; phase B judge FAILED (#1363)
- [Lagging areas top 3](lagging-areas-2026-11-06.md) — Kent 11-06: yardstick / satin-fill 0.387 / trims; 3 Sonnet notes in docs/lagging-areas-2026-11-06: no external repo fixes any, instruments + oracles first; polygon_axis.py already exists
- [Lane reading before the run](lane-reading-before-run-2026-10-28.md) — `POST /classify` replays stage 0 + 1.25 before `/digitize`; Studio reading row above Auto Digitize (owl 2.5 s, golden_tee 32 s); `np.unique` GIL freeze fixed
- [Launch not near](launch-not-near-rulings-2026-11-12.md) — Kent 11-12 "not ready for going live": no billing/licence/signing/hosting/legal until he says; show him the build first; "Decide later" on installer name; defect 28 close it
- [Letter-fault reader](letter-fault-reader-2026-11-11.md) — per-colour topology (counter lost/join/bay) vs Kent's 14 merged-letter pins: 0.64 vs chance 0.24 at 3 mm, CI [+0.08,+0.57] = shown; leave-one-out loses it on 3 of 6, replicate first
- [Letter-reader replication](letter-reader-replication-2026-11-12.md) — #1389 reader pre-registered; Kent sat 9 logos 11-13: letter pins on 2 items (needs 5) = no verdict, not replicated
- [Lettering board v3](lettering-board-v3-2026-10-31.md) — baseline on a8758e96: <4 mm cc +0.92 (Fremont's gain = bean, not pro's satin), Becker in-letter trims 62 -> 21; Drone gap = thread contrast
- [Lettering thread](lettering-thread-2026-11-01.md) — Drone's gap was thread: stray ON 11-02 (Kent), contrast floor OFF (Becker black), AND DRONE 0 -> +1.00, PRECISION +0.58; sewn ground exempt
- [Line chain, one thread](line-chain-one-thread-2026-11-11.md) — fix B `line_chain_one_thread`: Kent 11-11 "Keep off, very little improvements were made, if any"; stays OFF, no flip, no retune; 4 of 21 rows move
- [Local lanes fill the disk](local-lanes-fill-disk-2026-11-08.md) — ~25 local lanes (900 MB node_modules each) took C: to 143 MB; remove a lane on merge, stop under 10 GB free
- [MFab AND re-check](mfab-and-recheck-2026-11-06.md) — 10-25 brief stale: on main 7ee2d98a the hollow A is gone (0 bean tags, A/N/D satin 126/110/120) since bean_ink_outlined_letters + bean_only_lines ON 10-27; no flag built; keyline art = MFab only
- [MFab photo route](mfab-photo-route-2026-11-04.md) — MFab classes photo_scene at every width (gate 0.298/0.28, veto 0.856/0.90); 60 and 101 mm = photo lane skips the 8 px/mm grid, W+E stay joined (NOT the segmenter, corrected 11-05); `photo_work_grid` OFF
- [Monarch size cliff](monarch-size-cliff-2026-11-13.md) — wing cell lost only at 90.50/91.75 mm: stroke CV jitters under LETTER_STROKE_CV_MAX 0.55, wings tag as text, Column lane sews a V as one arm; owl same; lighthouse crashes 25.125
- [Move shape](move-shape-2026-11-05.md) — Kent 11-05: translate one digitized shape (shell, holes, nodes); outline live, stitches follow on commit; one discrete elupdate; ignores the similar tick; e2e (m1)-(m7)
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [Nightly tripwire](nightly-tripwire-2026-11-02.md) — 18 committed pairs (Becker x5 + the zip's 13) nightly on main vs testdata/tripwire_ledger.json; tolerance = spread of 3 runner passes; wrong-way past it = red; never a PR check
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [Node reshape spec](node-reshape-spec-2026-11-03.md) — "entire spline follows" = pullRing's 2x-drag radius (not a bug); 7 rulings 11-03: 3 mm fixed, Reshape mode both lanes, holes_override, marquee crosses shapes for seams
- [Outline fonts on demand](outline-fonts-on-demand-2026-11-06.md) — Kent 11-06: TTF/OTF fonts sewn by the service via the Column lane (POST /lettering), 21 OFL families, `outline:<key>`; 07-24 ruling = browser trace
- [Cut-out finds no subject](photo-cutout-no-subject-2026-10-28.md) — rembg keeps 0.01-5.4% of a scene (subjects 27-76%); #1179's `photo_cutout_min_kept` 0.20 refuses; prep-skipped beat prep-kept 4/6; kept frame 373-2,100 s (stage 7) vs Studio's 600 s
- [Placement axis sizing](placement-axis-sizing-2026-10-28.md) — size = most that fits WHERE it sits: `PLACEMENTS` table, 3 pro boxes kept, rest `seeded` = Kent's; upload fits the box, typed width stays
- [Pot slot swing](pot-slot-swing-2026-11-03.md) — Pooh pot = one shaded body, chart has no olive; fringe votes + size drag k-means centres (Lloyd decides, not dissolve/cap); Becker mid-tone shares it; nothing built
- [Preflight score](preflight-score-2026-11-05.md) — 0-100 `score` ALREADY existed (grade derives from it; Studio QualityReport.svelte:189 shows it); 11-05 added only the mapping comment, pins, tool columns. Don't build a 2nd
- [Pro-sized lettering sitting](pro-size-lettering-sitting-2026-11-02.md) — pro-lettering-1102, 56 live pairs, 8 one-flag arms; Kent sat 11-03: trims control did NOT replicate, repeats unstable (3 of 4), no flip
- [Questions roll up to the director](questions-roll-up-to-director-2026-10-27.md) — Kent 10-27: a worker never asks Kent; SendMessage the decision (options, cost, catch, pick) to its starter
- [Reshape mode](reshape-mode-2026-11-03.md) — "Edit points" on both lanes: cross-shape marquee so a seam moves as one gesture; arrows 0.1/1 mm, Delete per ring, one patch + one undo (elupdate.discrete); panel SVG editor retired
- [Satin/fill oracle split](satin-fill-oracle-2026-11-06.md) — C3 bound: cutting our grounds along the pro's 10+ cell blobs lifts mean kappa 0.381 -> 0.482 (5 cells 0.561, 20 cells 0.427): no verdict; reads the pro, a max
- [Satin/fill re-measure](satin-fill-remeasure-2026-10-29.md) — defect 5: kappa 0.387, per-region oracle 0.365 (no router left); pro vs pro 0.5 mm 0.650 = ceiling; shape kappa by AREA; satin_per_stroke a wash
- [Scorecard recapture 11-05](scorecard-recapture-2026-11-05.md) — ruler d000e370 -> 292418a8 via the new `Corpus scorecard` CI button (diff/capture): 9/18/7/6/12 -> 10/20/8/10/4, mean 61.8 -> 71.9 = THREAD_MATCH_POOR quiet (#1200); Fremont F 28/16
- [Scorecard recapture 11-12](scorecard-recapture-2026-11-12.md) — ruler 292418a8 -> ffefc3b1, run 43253187536: 10/20/8/10/4 -> 8/20/6/10/8, mean 71.9 -> 68.7 FELL; flag-off CI arms name #1301, #1263, #1329, #1378; 1 row part unattributed
- [Seam order's costs](seam-order-costs-2026-10-30.md) — beanie's rise = one knockdown walk (ProSeal the other way); drone's +6 cuts = the chord; `knockdown_shorter_walk`, `fill_seam_order_priced` ON (Kent 10-30): flips 59 -> 2
- [Service timeout cancel](service-timeout-cancel-2026-10-30.md) — a job past JOB_TIMEOUT_S STOPS at the next stage seam (`digitizer_core.deadline`); next upload waited 497.9 s -> 10.5 s; no flag; stage 2 former + rembg/SAM2 still run to their end
- [Sew-out card v8](sewout-card-v8-2026-11-01.md) — cut_every_jump walks Fremont's 148 floats on the white field, cuts ENTHUSIAST's; JS cuts 15; Drone's lever is the halo (0.3: x1.74); 0.01 mm oracle: 1 walk 0.029 mm off
- [Shape memo](shape-memo-2026-10-28.md) — Column lane's rank-only 2nd stage-7 pass was 79 of owl flat's 137 s; `shape_memo` memoizes stitch_shape/satin_shape/rim per job: 137 -> 113 s flat, 123 -> 97 gradient, md5 same
- [Simplify points](simplify-points-2026-11-03.md) — popover row 0.2/0.5/1 mm, closed-ring Douglas-Peucker `simplifyRing`, rides the similar tick in one patch; never automatic; red-disc 64 -> 44 at 0.5 mm
- [Size recount](size-recount-2026-11-05.md) — `POST /recount` + the reading row's "N shapes, M colors at W mm" (Kent 11-05, counts only); own route, stages 0-4 cost 5-60 s; leaves the generation cached; MFab 36.7: 22/2, 113.5: 93/2
- [Sliver prune](sliver-prune-2026-11-10.md) — `sliver_prune` OFF: Pooh 54 mm white edge runs = page-halo masks, red arm spike = shirt tendril on a crease; enlarged x1.25+ only; 80 mm sheet 20/20 same; his on-screen run was gradient, not flat
- [Space fault reader](space-fault-reader-2026-11-12.md) — bays/gaps filled vs 44 letter pins: +0.32 over pick, CI [+0.22,+0.47] = shown, not a hold-out; 1112 replication = no verdict (2 of 9 items pinned)
- [Sparse smooth nodes](sparse-nodes-spec-2026-11-04.md) — Kent 11-04: Ember-style few smooth/corner nodes on digitized rings, 9 rulings; PR 1 lib `sparseNodes.js`, PR 2 Studio; add-hole in, Knife out
- [Sparse nodes in the Studio](sparse-nodes-studio-2026-11-05.md) — PR 2 shipped: nodes drawn/dragged/inserted/toggled in shapeOverrides; real seeds red-disc 44 smooth, squares 4 corners; PointerEvent.detail is 0 (old dblclick dead)
- [Stacked PR trap](stacked-pr-auto-merge-trap-2026-11-06.md) — #1259 stacked on #1255's head with auto-merge armed merged INTO that branch after #1255 landed (deleteBranchOnMerge off, no retarget); base follow-ups on main, never arm a stacked PR
- [Stage-0 texture gate](stage0-texture-gate-2026-10-28.md) — grain gate missed 15/18 downsampled photos; `texture_frac` >= 0.13 route + two-ink veto ON (`stage0_texture_gate`); 6 "logo" rows are photographs by medium; cut-outs keep the old tree
- [Scene speed](stage7-scene-speed-2026-10-29.md) — kept-frame scenes' 349-2,100 s was 2 procs on a loaded laptop: 64-104 s plan quiet, 2 concurrent = 4.1x EACH, md5 same; stage 2 bincount + stage 6 prepared covers / threaded angle search, exact
- [Starter pack sourcing](starter-pack-sourcing-2026-11-10.md) — Kent 11-10: 12 designs, strict CC0/PD-mark art digitized by EMB-Bot itself; no open stitch files, commission or CC-BY; no logos; provenance per design
- [Starter weak spots](starter-weak-spots-2026-11-12.md) — baseball flat + monarch borders_last off SHIPPED 11-12; "drift" was a width slip: re-digitize at the original target, not manifest width_mm
- [Stitchist teardown](stitchist-teardown-2026-11-04.md) — server-side engine, $50 Pro; MFab at 36.7: 3,018 st, keyline as tatami, readable; trace re-runs per size
- [Studio no silent fallback](studio-no-silent-fallback-2026-11-02.md) — image + service down: keep art, Retry / Use browser engine; results name engine

- [Excess on gradient](thread-match-excess-gradient-2026-10-29.md) — defect 28 ON 10-30: F-with-block 14 -> 4, md5s same
- [Defect 28 leftovers](thread-match-leftovers-2026-11-10.md) — bridge_bar 3, screenshot 1, stub 0722 = CHART LIMITS: best of 398 spools still 10.6-29.4 dE00 per pixel; nothing built; excess-over-chart yardstick priced only
- [Transparent white in-fill](transparent-white-infill-2026-11-11.md) — `enclosed_white_skip_transparent` ON (Kent 11-11 "Flip ON"): transparent enclosed areas open unless a hollow letter body; kanji 39 open, Becker kept; moves Drone tripwire + logo_alpha
- [Trims re-measured 10-29](trim-defects-4-6-2026-10-29.md) — cuts 391 vs pro 409 (3.1x gone), breaks 2.07x (488 uncut floats); fill sections 32 vs 0; `fill_section_cuts_first` OFF: 377 cuts, exposed 723 -> 651
- [Eye, 100 pairs](vlm-judge-100-2026-11-06.md) — Opus session, 99 pairs: kappa +0.34 [+0.17, +0.49] above chance; sides +0.65 n 22; proposal only
- [Claude as the eye](vlm-judge-2026-11-04.md) — session judged pro-lettering-1102 blind: kappa +0.36 [+0.16, +0.55] above chance (n 54); sides n 16 no evidence; agreement = shared ties + base picks
- [Vision pre-screen](vlm-prescreen-2026-11-06.md) — threshold 4: settled kappa +0.39 (39/54), +0.29 (67/99), both above chance; row PROPOSAL only; tie label holds 13/29, 18/40 side picks
- [DreamSim yardstick](yardstick-dreamsim-2026-11-08.md) — 11-08: +0.197 on 100 pooled pro pairs, NOT replicated on fresh sitting (+0.099, CI crosses 0) or 1102 hold-out (-0.127); no stand-in for Kent
- [Pro-pair yardstick](yardstick-pro-pair-2026-11-01.md) — 100 pairs at the pro's size: only trims clear chance (hops +0.24, cuts +0.23), "never worse" fails all 6; Kent 11-02 on the 17 trim-disagreement pairs: "My eye stands", exit unmet
