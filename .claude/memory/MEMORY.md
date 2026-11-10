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

- [Memory archive: through 10-26](MEMORY-archive.md) — NOT auto-loaded: history through 10-15 + standing rulings (fill rows 0.15, DST axis fixed, Ink/Stitch clean-room, Ember teardowns)
- [Opus team architecture](../../docs/superpowers/plans/2026-10-23-opus-team-architecture.md) — the plan a fresh director runs from: method, state, ranked queue L1-L10 / I1-I6, Kent's open decisions, brief template, traps
- [Add hole](add-hole-2026-11-05.md) — PR 3: Add hole draws a polygon in a digitized shape, appended to holes_override; refusal reuses boundaryIssues wording, draft stays open; e2e (h1)-(h6)
- [No Fable agents](agents-cheap-models-2026-11-02.md) — Kent 11-02 "don't release fable agents, we should be saving on usage": every start_session / Agent passes model (Sonnet default, Haiku read-only); a Fable director dispatches, never spawns Fable
- [Apex walk](apex-walk-2026-10-27.md) — apex_cut's walk sews each tip from its point: tip-satin travel <= 0.05 mm, crosses kept; per-job travel > OFF on 5 jobs, foreman's call
- [Bash heredoc Python trap](bash-heredoc-python-repl-trap-2026-11-02.md) — Windows Bash tool `python - <<'E'` lost stdin: Python 3.14 fell into _pyrepl, one core for 26 h (3.68 GB of prompts); a `||` fallback respawned it when killed. Run a script FILE
- [Bean census](bean-census-2026-10-27.md) — reference beans almost nothing: 17 runs / 780 mm / 8 of 1,101 regions, drawn thin lines, 2 passes; ours 137 (111 small letters); `bean_only_lines` ON (Kent 10-27), kappa -0.014 -> 0.129
- [Blend shade median](blend-shade-median-2026-11-09.md) — defect 28: Fremont fixed 11-07 (stale scope line); summit 0111 = mean of a 9-sample speckled end bucket; `blend_shade_median` OFF clears it, 20 entries md5 same
- [Band rings](border-by-size-colour-seams-2026-10-28.md) — Instagram: `border_by_size` satin rings each band, not bean; fix ON 10-28: ring fabric edges only
- [Bridge census](bridge-census-2026-10-27.md) — Bridge hat+LC through 14 pro rules on main 8341d1f7: 2 CONTRADICTS (border_by_size fields, proSized LC), 8 AGREES, 4 N/A; ours' text is a reach gap (folds 2 vs 35), not a rule
- [Cap frames sew 64 mm tall](cap-frame-height-2026-10-26.md) — PHYSICAL, Kent 10-26: his cap frames sew >= 64 mm (2.5 in); hat-height gate 1 settled
- [Cloud wave 11-06](cloud-wave-2026-11-06.md) — Kent 11-06 "10 agents in cloud": yardstick scorer, Euler census, C2 vote, stage-7 speed, nest guard, PR 1284, e2e apt, offsetRing test, dropped-element v2, shards; Remote Control turn cannot start sessions
- [Colour cap on the sewn design](colour-cap-sewn-2026-10-29.md) — census item 3 misnamed the hole: sew-white recolours AFTER the cap + blend bands snap chart-wide; `color_cap_sewn` ON 11-01 re-caps final regions, folds strays on blocks
- [Compare ends on regenerate](compare-ends-on-regenerate-2026-11-08.md) — Kent 11-08 "Keep as is": Compare view (#1345) is an Original sub-mode, a regeneration ends it; don't build survival
- [DADE teardown](dade-app-teardown-2026-11-04.md) — 10 px/mm fixed, tatami, trims OFF; at its 36.7 mm its file read better than ours (flat = blob); at 113.5 ours reads, DADE can't
- [Dark ink bean](dark-ink-bean-2026-10-28.md) — `dark_ink_bean` ON 10-29 (Kent, Pooh): dark read within 50 dE00 of its ground beans along its skeleton, ground sews through; Fremont wordmark (100) stays satin
- [Dark-ink floor rescue](dark-ink-floor-rescue-2026-11-03.md) — `dark_ink_floor_rescue` ON 11-04 (Kent): Pooh's lost letter = dark-read KERNEL (min_detail_mm), not stage 3; 2nd read at 1.0 mm unioned; ON reads every thin stroke
- [Dark read refusal](dark-read-refusal-2026-10-28.md) — `dark_ink_refuse_strays` OFF: edge (4 px) or not-under-ring reads refused; #1172's 10 not-ink rows = the 10 at the frame (its art window stretched)
- [Dark thin strokes](dark-thin-strokes-2026-10-27.md) — HUNNY's ink tracks the pot's shading, no k-means cluster; black-hat on L*, carve AFTER the merge (pre-SEEDS removal moved the palette)
- [Dark thin strokes ON](dark-thin-strokes-flip-2026-10-28.md) — flipped ON (Kent, #1170); OFF pinned in PRE_FLIP/FLIP_2026_10_23; owl 16 reads, patch 14
- [Dropped-element finding](dropped-element-finding-2026-11-01.md) — `ARTWORK_ELEMENT_DROPPED`: preflight reads clipped / unsewn-enclosed / colour-cap-folded / stage-4 drops by AREA; floor 5 mm2, block at 10%; fires on 2 rows Kent graded Good/Great
- [Edge cap re-measured](edge-cap-remeasure-2026-10-29.md) — defect 19: edge 0-4% bare with NO cap (rim + border_by_size); swing gone; default "none" + defect closed (Kent 10-29, #1192)
- [Ember reshape measured](ember-reshape-measured-2026-11-04.md) — Ember's drag moves 1 point, 0.0 px on the rest; accept/reject session; built: exact drag + Done/Discard; open: sparse nodes, insert, smooth toggle
- [Export read-back](export-readback-2026-11-05.md) — every export re-read, download BLOCKED on mismatch (Kent 11-05): service pystitch 500 + headers, browser DST/EXP/PES; skipped checks per format; 20k stitches +7-13 ms browser
- [Download all zip](export-zip-2026-11-05.md) — Kent 11-05 zip only: 7 formats + PDF + PNG + threads.txt via the verified path; any one fails = nothing saved; no PEC/U01; 24k stitches 2.2-2.6 s, 1.08 MB
- [External sourcing 11-06](external-repo-sourcing-2026-11-06.md) — tesserocr 251 -> 5 ms per OCR read, ADOPTED 11-06 (board geometry identical, cc <4 -0.08 = one drone word; 5.5.3 vs CI 5.3.4 open); clipper2-ts on offsetRing trigger; bench filum DST only
- [Seam order flip](fill-seam-order-flip-2026-10-30.md) — fill_seam_order + fill_bridge_cut_exposed ON together (Kent 10-30): ridges 0, exposed travel down, trims up; seam order alone adds exposure
- [Fill-slant sitting](fill-slant-sitting-2026-11-09.md) — Kent blind, 16 live pro pairs: slant ON 0, OFF 7, tie 9 = favours OFF (4 designs, Becker 4 of 7); "Keep OFF, record"; pro-direction kappa gain did not read better
- [Flag stripes](flag-stripes-seam-cap-2026-10-30.md) — equal art sewed 4.53/3.57: rail pull lands after stage 5's clip; `satin_seam_hold` + `satin_cap_skew_inset` OFF; underlay was never missing
- [Flat soft ramp](flat-fringe-soft-ramp-2026-11-06.md) — Bridge flat-lane blue split = 3-src-px JPEG edge at x3.25: page band 5 -> 11 + ramp dissolve (kept-colour chords); both OFF, enlarged only; 4 inks, hat trims 157 -> 23
- [Flat page fringe](flat-page-fringe-2026-11-03.md) — `flat_page_fringe_exclude` OFF: page-edge blend leaves the flat fit + chain rescue; Pooh pale flecks 59 -> 25; band = upscale+1; page = median; + outline INNER blend (B)
- [Flip-proof pins](flip-proof-pins-2026-10-27.md) — `FLAT_GOLDEN_MD5` from the json; `frozen_cfg()` spreads a dated snapshot; test_pins_are_frozen guards new md5 pins
- [Flip sheet wave 5](flip-sheet-wave5-2026-10-27.md) — 4 asked on main ce8cc87d, gate 3 clear; Kent 10-27: bean_ink + part_touching (only together) + italic lean ON, fill_section_travel held; keyline trio inert off MFab
- [Foreman merge/push findings](foreman-merge-push-findings-2026-11-08.md) — 62 PRs 11-07/08: squash branches refuse `branch -d`; test.fail() expected; empty log != green; fix-lane branch needs a finding index
- [Foreman merges, workers bypass](foreman-merges-and-bypass-2026-11-06.md) — Kent 11-06 "i'm not merging anything, you do it": foreman merges CLEAN PRs, arms BLOCKED, never --admin; workers bypassPermissions where settable; overrides CLAUDE.md
- [Free-digitizer follow-ups](free-digitizer-followups-2026-11-05.md) — Kent 11-05 on the 7 untaken ideas: score metrics-only, recount only, zip only, re-read BLOCKS, TSP skip, heatstitch floor row ADD, literature parked
- [Free digitizer survey](free-digitizer-survey-2026-11-04.md) — Kent 11-04: 40+ tools, no free desktop auto-digitizer; bench tier 1 heatstitch (MIT) + openstitch (AGPL, output only) + Nuizu (CLI); Hatch 30-export list approved, Wilcom skipped (hardware)
- [Garment size like the pro](garment-size-like-pro-2026-10-26.md) — pro boxes hat 113.5x64, LC 96x76.5, area 5,800 (Bridge LC, Kent 10-27), beanie 94.5x56; `proSized` default ON (10-26)
- [Golden Tee gap](goldentee-gap-2026-10-27.md) — Kent: no build. The +95% is the pro simplifying: 39% = silver extrusion + red stroke he never sews; faces 22% (G's border_by_size ring 640); fields_fill ON makes it worse
- [heatstitch floor row](heatstitch-floor-row-2026-11-05.md) — `tripwire floor`: ours' sttype kappa beside heatstitch's untuned rule per job, margin, flag < 0.05 (never fails); laptop-only, n/a without scratch_bench files
- [Holes override](holes-override-2026-11-03.md) — contract v1.9 `holes_override` (service half): replaces interior rings, [] = solid, absent = carry-over; Studio half next
- [Holes in the Studio](holes-studio-2026-11-03.md) — holes drawn/edited like the outline, Delete hole, `holes_override` only when a hole was edited; a 3 mm drag shares with a chamfer partner, arrows move one; no add-hole yet
- [Kent's judging rubric](kent-judging-rubric-2026-11-07.md) — his 22 reasons: lettering follows pen strokes, smooth curves, straight uprights, no blobs; first picks noisy; phase B judge FAILED (#1363)
- [Lagging areas top 3](lagging-areas-2026-11-06.md) — Kent 11-06: yardstick / satin-fill 0.387 / trims; 3 Sonnet notes in docs/lagging-areas-2026-11-06: no external repo fixes any, instruments + oracles first; polygon_axis.py already exists
- [Lane reading before the run](lane-reading-before-run-2026-10-28.md) — `POST /classify` replays stage 0 + 1.25 before `/digitize`; Studio reading row above Auto Digitize (owl 2.5 s, golden_tee 32 s); `np.unique` GIL freeze fixed
- [Lettering board](lettering-board-2026-10-25.md) — the ONE board a lettering PR quotes: ours/pro by job and drawn height, five figures, n/a with a reason; `--compare A B` is the delta; baseline docs/scoreboards/
- [Lettering board v2](lettering-board-v2-2026-10-27.md) — baseline on 98603fb4, cc on 39/42 lines (was 16); the 10-25 MFab/Tires had rerouted: a lane has no rembg venv
- [Lettering board v3](lettering-board-v3-2026-10-31.md) — baseline on a8758e96: <4 mm cc +0.92 (Fremont's gain = bean, not pro's satin), Becker in-letter trims 62 -> 21; Drone gap = thread contrast
- [Lettering thread](lettering-thread-2026-11-01.md) — Drone's gap was thread: stray ON 11-02 (Kent), contrast floor OFF (Becker black), AND DRONE 0 -> +1.00, PRECISION +0.58; sewn ground exempt
- [Local lanes fill the disk](local-lanes-fill-disk-2026-11-08.md) — ~25 local lanes (900 MB node_modules each) took C: to 143 MB; remove a lane on merge, stop under 10 GB free
- [Index counts CRs](memory-index-crlf-count-2026-10-26.md) — loader counts the file as stored: CRLF = +1 char/line; notes pinned LF; `git checkout --` won't convert (recipe inside)
- [MFab AND re-check](mfab-and-recheck-2026-11-06.md) — 10-25 brief stale: on main 7ee2d98a the hollow A is gone (0 bean tags, A/N/D satin 126/110/120) since bean_ink_outlined_letters + bean_only_lines ON 10-27; no flag built; keyline art = MFab only
- [MFab photo route](mfab-photo-route-2026-11-04.md) — MFab classes photo_scene at every width (gate 0.298/0.28, veto 0.856/0.90); 60 and 101 mm = photo lane skips the 8 px/mm grid, W+E stay joined (NOT the segmenter, corrected 11-05); `photo_work_grid` OFF
- [Move shape](move-shape-2026-11-05.md) — Kent 11-05: translate one digitized shape (shell, holes, nodes); outline live, stitches follow on commit; one discrete elupdate; ignores the similar tick; e2e (m1)-(m7)
- [Next work comes from main, not handoffs](next-work-from-main-not-handoffs.md) — Kent: don't build on past sessions; "what's next" comes from ROADMAP/PRODUCT/MASTER_SCOPE on main
- [Nightly tripwire](nightly-tripwire-2026-11-02.md) — 18 committed pairs (Becker x5 + the zip's 13) nightly on main vs testdata/tripwire_ledger.json; tolerance = spread of 3 runner passes; wrong-way past it = red; never a PR check
- [No warnings reaches readouts](no-warnings-reaches-readouts.md) — Kent's 10-02 ruling covers always-on info rows too: defect 46 shipped as preflight METRICS only, customer sees nothing
- [Node reshape spec](node-reshape-spec-2026-11-03.md) — "entire spline follows" = pullRing's 2x-drag radius (not a bug); 7 rulings 11-03: 3 mm fixed, Reshape mode both lanes, holes_override, marquee crosses shapes for seams
- [Outline fonts on demand](outline-fonts-on-demand-2026-11-06.md) — Kent 11-06: TTF/OTF fonts sewn by the service via the Column lane (POST /lettering), 21 OFL families, `outline:<key>`; 07-24 ruling = browser trace
- [Outlined bean ink](outlined-bean-ink-2026-10-27.md) — MFab LC's AND read its white keyline as ink, sewed white; `bean_ink_outlined_letters` (ON 10-27) drops reads half outside
- [Photo corpus sxs](photo-corpus-sxs-2026-10-27.md) — #1171: 39 Commons rows, `capture --base` per tree, sxs HTML with Kent's verdicts, `baseline-5ff48c5.json`; stage 0 sent 3 of 18 photos down the photo lane; `design.colors` = BLOCKS
- [Cut-out finds no subject](photo-cutout-no-subject-2026-10-28.md) — rembg keeps 0.01-5.4% of a scene (subjects 27-76%); #1179's `photo_cutout_min_kept` 0.20 refuses; prep-skipped beat prep-kept 4/6; kept frame 373-2,100 s (stage 7) vs Studio's 600 s
- [Photo lane must generalise](photo-lane-generalise-2026-10-27.md) — Kent 10-27: photo tools were tuned on 4 portraits + the owl; 18-genre census broke on scenes/crowds/pale art; read across genres, check tonal first
- [Placement axis sizing](placement-axis-sizing-2026-10-28.md) — size = most that fits WHERE it sits: `PLACEMENTS` table, 3 pro boxes kept, rest `seeded` = Kent's; upload fits the box, typed width stays
- [Pot slot swing](pot-slot-swing-2026-11-03.md) — Pooh pot = one shaded body, chart has no olive; fringe votes + size drag k-means centres (Lloyd decides, not dissolve/cap); Becker mid-tone shares it; nothing built
- [Preflight score](preflight-score-2026-11-05.md) — 0-100 `score` ALREADY existed (grade derives from it; Studio QualityReport.svelte:189 shows it); 11-05 added only the mapping comment, pins, tool columns. Don't build a 2nd
- [Pro renders local only](pro-renders-local-only-2026-10-27.md) — Kent 10-27 "Stop new ones, keep old": pro-file renders go to gitignored `pro_renders/`; `test_no_new_pro_renders` fails on a new `pro` word under docs/
- [Pro-sized lettering sitting](pro-size-lettering-sitting-2026-11-02.md) — pro-lettering-1102, 56 live pairs, 8 one-flag arms; Kent sat 11-03: trims control did NOT replicate, repeats unstable (3 of 4), no flip
- [Questions roll up to the director](questions-roll-up-to-director-2026-10-27.md) — Kent 10-27: a worker never asks Kent; SendMessage the decision (options, cost, catch, pick) to its starter
- [RAG fast path](rag-fast-path-2026-10-27.md) — `fast_skimage.rag_mean_color`: Fremont's graph 41 s -> 0.6 s, same add_edge ORDER replayed; 7 gradient designs md5-identical; next: glyph OCR pool, fill angle search
- [Re-pin tuples](repin-tuples-2026-10-27.md) — `_hexrepr` writes tuple/list/dict digests whole; `ci_repin` moves them, or the whole source literal when a count moved; starts paying on a branch that merged main
- [Reshape mode](reshape-mode-2026-11-03.md) — "Edit points" on both lanes: cross-shape marquee so a seam moves as one gesture; arrows 0.1/1 mm, Delete per ring, one patch + one undo (elupdate.discrete); panel SVG editor retired
- [Satin/fill oracle split](satin-fill-oracle-2026-11-06.md) — C3 bound: cutting our grounds along the pro's 10+ cell blobs lifts mean kappa 0.381 -> 0.482 (5 cells 0.561, 20 cells 0.427): no verdict; reads the pro, a max
- [Satin/fill re-measure](satin-fill-remeasure-2026-10-29.md) — defect 5: kappa 0.387, per-region oracle 0.365 (no router left); pro vs pro 0.5 mm 0.650 = ceiling; shape kappa by AREA; satin_per_stroke a wash
- [Satin-split cuts](satin-split-cuts-2026-10-27.md) — 26 = 16 band loops (chain via #1143) + 2 Drone (pro lifts more) + 8 in letters; slot guard alone +10 mm exposed; per-letter pick (-3 cuts) costed, NOT built
- [Scorecard recapture 11-05](scorecard-recapture-2026-11-05.md) — ruler d000e370 -> 292418a8 via the new `Corpus scorecard` CI button (diff/capture): 9/18/7/6/12 -> 10/20/8/10/4, mean 61.8 -> 71.9 = THREAD_MATCH_POOR quiet (#1200); Fremont F 28/16
- [Seam order's costs](seam-order-costs-2026-10-30.md) — beanie's rise = one knockdown walk (ProSeal the other way); drone's +6 cuts = the chord; `knockdown_shorter_walk`, `fill_seam_order_priced` ON (Kent 10-30): flips 59 -> 2
- [Service timeout cancel](service-timeout-cancel-2026-10-30.md) — a job past JOB_TIMEOUT_S STOPS at the next stage seam (`digitizer_core.deadline`); next upload waited 497.9 s -> 10.5 s; no flag; stage 2 former + rembg/SAM2 still run to their end
- [Sew-out card v8](sewout-card-v8-2026-11-01.md) — cut_every_jump walks Fremont's 148 floats on the white field, cuts ENTHUSIAST's; JS cuts 15; Drone's lever is the halo (0.3: x1.74); 0.01 mm oracle: 1 walk 0.029 mm off
- [Shape memo](shape-memo-2026-10-28.md) — Column lane's rank-only 2nd stage-7 pass was 79 of owl flat's 137 s; `shape_memo` memoizes stitch_shape/satin_shape/rim per job: 137 -> 113 s flat, 123 -> 97 gradient, md5 same
- [Simplify points](simplify-points-2026-11-03.md) — popover row 0.2/0.5/1 mm, closed-ring Douglas-Peucker `simplifyRing`, rides the similar tick in one patch; never automatic; red-disc 64 -> 44 at 0.5 mm
- [Size recount](size-recount-2026-11-05.md) — `POST /recount` + the reading row's "N shapes, M colors at W mm" (Kent 11-05, counts only); own route, stages 0-4 cost 5-60 s; leaves the generation cached; MFab 36.7: 22/2, 113.5: 93/2
- [Sparse smooth nodes](sparse-nodes-spec-2026-11-04.md) — Kent 11-04: Ember-style few smooth/corner nodes on digitized rings, 9 rulings; PR 1 lib `sparseNodes.js`, PR 2 Studio; add-hole in, Knife out
- [Sparse nodes in the Studio](sparse-nodes-studio-2026-11-05.md) — PR 2 shipped: nodes drawn/dragged/inserted/toggled in shapeOverrides; real seeds red-disc 44 smooth, squares 4 corners; PointerEvent.detail is 0 (old dblclick dead)
- [Stacked PR trap](stacked-pr-auto-merge-trap-2026-11-06.md) — #1259 stacked on #1255's head with auto-merge armed merged INTO that branch after #1255 landed (deleteBranchOnMerge off, no retarget); base follow-ups on main, never arm a stacked PR
- [Stage-0 texture gate](stage0-texture-gate-2026-10-28.md) — grain gate missed 15/18 downsampled photos; `texture_frac` >= 0.13 route + two-ink veto ON (`stage0_texture_gate`); 6 "logo" rows are photographs by medium; cut-outs keep the old tree
- [Scene speed](stage7-scene-speed-2026-10-29.md) — kept-frame scenes' 349-2,100 s was 2 procs on a loaded laptop: 64-104 s plan quiet, 2 concurrent = 4.1x EACH, md5 same; stage 2 bincount + stage 6 prepared covers / threaded angle search, exact
- [Stitchist teardown](stitchist-teardown-2026-11-04.md) — server-side engine, $50 Pro; MFab at 36.7: 3,018 st, keyline as tatami, readable; trace re-runs per size
- [Studio no silent fallback](studio-no-silent-fallback-2026-11-02.md) — image + service down: keep art, Retry / Use browser engine; results name engine

- [Nest guard](text-cluster-nest-guard-2026-10-27.md) — `text_cluster_nest_guard` OFF: `_drop_nested` ignores a frame candidate over 6x the median glyph height (Bridge hat wheel nested 8/15 letters); rotation-aware door next
- [Typed lettering floats](text-cut-jumps-2026-10-27.md) — `cutEveryJump` OFF: names float 1-3 mm hops on every DST path; ON buries/walks/cuts (95% cut), trims ~2x
- [Excess on gradient](thread-match-excess-gradient-2026-10-29.md) — defect 28 ON 10-30: F-with-block 14 -> 4, md5s same
- [Trims re-measured 10-29](trim-defects-4-6-2026-10-29.md) — cuts 391 vs pro 409 (3.1x gone), breaks 2.07x (488 uncut floats); fill sections 32 vs 0; `fill_section_cuts_first` OFF: 377 cuts, exposed 723 -> 651
- [Upload full-res](upload-full-res-2026-10-27.md) — SVG/GIF/EXIF JPEG go up as a 2,800-px render, OFF; 250 mm run: geometry tie, ON drops halo colours; text art times out both arms. Kent 10-27: flip held, no EXIF change
- [Eye, 100 pairs](vlm-judge-100-2026-11-06.md) — Opus session, 99 pairs: kappa +0.34 [+0.17, +0.49] above chance; sides +0.65 n 22; proposal only
- [Claude as the eye](vlm-judge-2026-11-04.md) — session judged pro-lettering-1102 blind: kappa +0.36 [+0.16, +0.55] above chance (n 54); sides n 16 no evidence; agreement = shared ties + base picks
- [Vision pre-screen](vlm-prescreen-2026-11-06.md) — threshold 4: settled kappa +0.39 (39/54), +0.29 (67/99), both above chance; row PROPOSAL only; tie label holds 13/29, 18/40 side picks
- [White recipe on every job](white-recipe-every-job-2026-10-27.md) — Kent 10-27 "Every job": recipe switches are PLAIN defaults (a gate would override the Studio's unticked white box); D1-D3 + Becker counter growth fixed first
- [DreamSim yardstick](yardstick-dreamsim-2026-11-08.md) — 11-08: +0.197 on 100 pooled pro pairs, NOT replicated on fresh sitting (+0.099, CI crosses 0) or 1102 hold-out (-0.127); no stand-in for Kent
- [Pro-pair yardstick](yardstick-pro-pair-2026-11-01.md) — 100 pairs at the pro's size: only trims clear chance (hops +0.24, cuts +0.23), "never worse" fails all 6; Kent 11-02 on the 17 trim-disagreement pairs: "My eye stands", exit unmet
