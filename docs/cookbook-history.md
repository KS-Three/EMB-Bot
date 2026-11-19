# COOKBOOK history

Append-only record of sections retired from [`COOKBOOK.md`](../COOKBOOK.md)
because they had become history rather than current handoff. Each block is
moved verbatim; nothing here is live status, and line numbers, counts and
"still open" claims inside it are as they stood when written. For current
state read COOKBOOK.md, MASTER_SCOPE.md and ROADMAP.md.

## Binary font library — opening paragraph (font counts, legacy registry, standalone page)

*Moved from COOKBOOK.md 2026-11-19.*

The Studio's fonts live in `src/fonts/manifest.json` + `src/fonts/bin/*.embf`
(**85 fonts** as of 2026-08-22; was 55 after the 2026-08-04 licence-audit pulls
and the same-day removal of all 13 ShareAlike fonts (Kent's call — audit §9;
removal made the paid launch independent of the CC-BY-SA question, and the
lawyer brief is the optional restore path), then grew through the 2026-08-21/22
upstream sweeps — this number has drifted twice without the doc being updated,
so don't trust it without recounting `manifest.json`), lazily fetched per font by
`app/src/lib/fontLoader.js`. The
old eager `src/fonts/satin-fonts.js` is OUT of the Studio pipeline and — since
`EMB-Bot.html`'s deletion (2026-08-08) — has no consumer left at all (this line
said "still used by legacy `EMB-Bot.html`, do not delete it" long after that
page was gone); it survives as the audited legacy registry of record, and
removing it is Kent's call, not cleanup. **Its audit ran 2026-08-04**
(`docs/font-license-audit-2026-07-31.md` §10): the 7 license-pulled fonts
(milli_marif_bold, tt_masters + the 5 ShareAlike: aventurina, emilio_20,
emilio_20_bold, geneva_simple, monicha) were removed, 21 → 14 entries, all
remaining OFL-1.1/CC0 and present in the shipping manifest. Do not re-add a
font there unless it is also in the shipping manifest. `EMB-Bot-standalone.html`
(the frozen artifact that inlined the pre-audit 21 fonts) was **deleted
2026-08-04, Kent's call** — no pre-audit font list ships anywhere anymore.

## Binary font library — tier-rule bullet (licence-policy corrections, struck-through legacy note)

*Moved from COOKBOOK.md 2026-11-19.*

- **Tier rule (Kent's decision): only `tier:"verified"` ships.** Unverified =
  internal work queue with a concrete reason per font in `_tiers.json`.
  License policy for NEW fonts: **OFL-1.1 / CC-BY-4.0 / CC0 only** — this line
  read "OFL-1.1 / CC-BY-4.0 / CC-BY-SA-4.0 / CC0" until 2026-08-21 and was
  wrong from 2026-08-04 onward; `ALLOWED_LICENSES` in `build-embf.mjs` is the
  authority, not this doc. **ShareAlike is permanently closed** (Kent,
  2026-08-21: SA may propagate through the compiled `.embf` onto customer
  stitch files — an unbounded liability on the product's core output). Do not
  re-propose it; the `docs/lawyer-brief-cc-by-sa-2026-08-04.md` restore path is
  retired. **NonCommercial and NoDerivatives can never ship** in a paid product
  — `licenseId()` labelled both as plain `CC-BY-4.0` until 2026-08-21
  (`docs/font-expansion-research-2026-08-21.md` §5). `precious` is excluded
  (GPL-3.0). `ondulamarif_XL`
  was demoted by QC (letter glyphs runs-only → 0 stitches). `milli_marif_bold`,
  `tt_directors`, `tt_masters`, and `dejavufont` were PULLED from the build
  2026-08-04 per `docs/font-license-audit-2026-07-31.md` action items 1-3
  (ad-hoc/aggregator-only/mislabeled licenses — see `PULLED` in
  `tools/build-embf.mjs` for the per-font reasoning). ~~They still linger in
  the legacy `src/fonts/satin-fonts.js` / `EMB-Bot.html` pipeline~~ —
  resolved 2026-08-04 by the legacy-registry audit (audit doc §10):
  milli_marif_bold and tt_masters are removed from `satin-fonts.js` along
  with the 5 ShareAlike pulls, so `EMB-Bot.html` no longer ships any pulled
  font — and `EMB-Bot-standalone.html`, the only place that still embedded
  them, is deleted (see the paragraph above).

## Font editing abilities Round 1 — merged 2026-07-27

*Moved from COOKBOOK.md 2026-11-19.*

Rotation, per-letter color, bold/thin weight, slant/italic for text elements.
Was previously sitting unmerged in a worktree (a memory note wrongly called
it "merged" — always verify with `git log`, don't trust prior claims at face
value). Fast-forward merged into `main`, worktree removed, branch deleted.
169/169 engine + 182/182 app tests green on `main` **at that merge
(2026-07-27)** — a historical record of that slice, not current counts; see
"Running things" for those.
Spec/plan: `docs/superpowers/specs/2026-07-27-font-editing-abilities-design.md`
and `docs/superpowers/plans/2026-07-27-font-editing-abilities.md`. Two
abilities were explicitly deferred (condensed/expanded width, mixed
per-letter size) — both risk distorting satin column width unevenly along
curves; prototype before committing.

**As of 2026-08-02, `feat/satin-rails` (56 commits: satin rewrite, chaining,
contour fill, push-comp, appliqué, the fill-axis geometry fix) is
fast-forward merged into `main`.** `feat/stitch-quality` no longer exists as
a branch — folded in along the way. `main` is still ahead of `origin/main`
locally; push is a user-confirm action, not automatic.

## The `preview.js` renderer collision — three broken `main`s in one night (2026-08-25)

*Moved from COOKBOOK.md 2026-11-19.*

Worth reading before touching `app/src/lib/preview.js`, and as the clearest
worked example of the parallel-lane hazard.

#249 and #251 both rewrote the thread draw. They merged with no textual
conflict into a file containing BOTH draw paths and two `const lw` in one
scope — a `SyntaxError`, so the module did not load and the Studio canvas was
dead. Then **two sessions fixed that in opposite directions twenty minutes
apart** (77333cf kept `drawFilament`; 872d950 kept `drawThreads`), both fixes
merged, and git applied **both deletions and neither implementation**. The
union of two self-consistent fixes was worse than the original bug. A third
lane (#254) then proposed a fourth resolution before Kent closed it.

**Settled: `drawThreads` wins** (#256, confirmed by Kent). Not on merit —
`stitchviz.py` and `test_stitchviz.py` grep `preview.js` for
`const LIGHT_X = -0.5547;`, `const LIGHT_Y = -0.8321;` and
`export const THREAD_WIDTH_MM = 0.4;`, all defined only in that section, so
the other resolution leaves the JS↔Python parity test asserting against
symbols that do not exist. **Do not relitigate this.** Ping-pong is what cost
the evening.

## Branches & worktrees — snapshot as of 2026-08-04

*Moved from COOKBOOK.md 2026-11-19.*

**Snapshot as of 2026-08-04 (re-verify, don't trust it):** the 2026-08-03
snapshot's one worktree (`bg-guard` / `fix/bg-existence-guard`) no longer
exists — gone from both `git worktree list` and `git log --all` this pass,
so either merged under a different branch name or abandoned; not
independently confirmed either way. What's actually live now is a large
parallel-lanes fleet under `.claude/worktrees/` (dozens of `agent-*`
worktrees, one per feature slice — this is the normal way work happens
here, not an anomaly), most sitting on already-merged branch tips. Don't
assume any specific one is still in flight without checking; a couple were
observed `locked` (actively in use by another session) during this pass and
were left untouched, per the "never touch worktrees" rule.

## What's next (queue as of 2026-08-03 — historical, with resolutions)

*Moved from COOKBOOK.md 2026-11-19.*

This queue is a dated artifact kept for its rationale trails; each item
carries its outcome inline. **ROADMAP.md owns the live ordering and gates**,
MASTER_SCOPE.md the live status — don't work from this list.

Decision doc: `docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`.
Session handoff with the full context:
`docs/superpowers/handoffs/2026-08-03-gradient-defects-handoff.md`.

1. **The two gradient/enclosed-white regressions** (see Known bugs below).
   The angle-fragmentation half is FIXED (2026-08-03, same-day follow-up
   session). **`BACKGROUND_ENCLOSED` is now FIXED too, later 2026-08-04** —
   pipeline, service contract, and Studio Layers-panel restore UI all
   merged to `main`, and the one caveat that kept it from being real
   end-to-end (an opaque-alpha bug that defeated background detection on
   real Studio uploads) is fixed too, merged PR #22; see
   `docs/scope/1-auto-digitizing-quality.md` for the full breakdown. (The
   live-browser verification this bullet used to flag as missing exists
   now — see the Known bugs entry.) The `fix/bg-existence-guard` branch/worktree
   this bullet used to queue no longer exists anywhere in this checkout
   (confirmed 2026-08-04, see "Branches & worktrees" above) — its content
   appears superseded by PR #22's opaque-alpha fix (same problem class:
   background detection defeated on real uploads), but that wasn't traced
   commit-for-commit, so treat it as closed-by-inference, not
   confirmed-merged.
2. **M0 + M1 of the DT-first migration** — this is the sequencing call that
   is easy to miss: once the regressions close, do **not** go straight to
   photo-digitizing steps 5+. M0 instruments `digitizer/tools/shape_lens.py`
   with distance-transform stats (`max/μ/σ` at skeletal pixels) against the
   current `2·area/perimeter` satin-vs-fill call, on the fixture logo and all
   37 `scratch_corpus/` files — zero engine change, zero golden impact.
   **The instrument existed already (2026-08-02, `70a14e8`) but had never
   been run to completion — done 2026-08-04, unit-fixture + real-art +
   timing + taper legs measured and written up
   (`docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md`). The
   37-file corpus leg is still blocked** — `scratch_corpus/` is gitignored
   and local-only, empty in this remote checkout; Kent needs to run
   `shape_lens.py corpus scratch_corpus/` locally and hand back the output
   before M0 fully closes per the architecture doc's original spec. Key
   finding so far: the shipped rule sews the SAME shape (`logo_alpha.png` vs
   `logo_whitebg.png`, same design, different file encoding) as satin on one
   file and fill on the other, purely from antialiasing noise landing
   `2*area/perimeter` on opposite sides of the 5.0mm cap — every DT arm
   agrees "fill" on both. **M1 is merged** (`bc1e59e`,
   `digitizer_core/shapefield.py` — `ShapeField`: mask, skeleton, exact EDT,
   scale, origin — hoisting one `medial_axis(rng=0)` so skeleton and DT are
   computed together, behind `cfg.extra["shapefield"]` defaulting to today's
   path). The byte-identical requirement is enforced, not just stated:
   `tests/test_shapefield_byte_identical.py` duplicates
   `stage6_satin._rasterize`'s rasterization number-for-number rather than
   reimplementing it, both on `origin/main` now. What's left of this slice:
   M0's corpus leg (above) still waits on Kent; M2/M3 resolved by rejection
   — see item 4. Rationale:
   the satin/fill call is made from `2·area/perimeter`
   (`stage6_satin.py`'s `ribbon_width_mm`, duplicated in `shapefield.py` —
   this bullet's old `stage7_sequence.py:97` pointer is stale, the logic
   lives there now), a statistic the source patent warns against — it
   satins a 20mm disc under a 5mm cap once the edge is serrated — decided,
   when this was queued, without the DT ever being consulted. (No longer
   true: `classify_ribbon` now runs DT gates — `dt_irregular`/`dt_p90_cap`,
   an `explained`-based promotion path, and the photo width floor — on top
   of the width/aspect screen; see item 4's resolution.) Steps 5+ all lean
   harder on that classifier than anything shipped so far. Full
   architecture: `docs/dt-first-architecture-2026-08-01.md` §2 and
   `docs/masters-teardown-2026-08-01.md`.
3. **Photo-digitizing plan steps 5+** (`docs/photo-digitizing-plan-2026-07-31.md`)
   — **rows 6/8/9/10/13 are now built**: direction field (row 6),
   scan-line mono tonal (row 8), meander mono tonal (row 9), streamline
   thread-paint in both its mono and layered-multicolour slices (row 10),
   and chart-restricted weighted k-medoids palette selection (row 13 /
   build-order step 7, `digitizer_core/palette.py` — replaces the photo
   path's per-region nearest-thread snap; the eyes/skin/subject class
   multipliers are FULLY WIRED since 2026-08-05 — eyes/skin off the YuNet
   face priors, subject/background off the rembg mask, both behind the
   `photo_prep` gates, with plain-area degradation when no prior covers a
   region; this bullet said "run at 1.0 until step 3's face priors exist"
   long after they did — see that module's THE CLASS-WEIGHT SEAM) — see
   `docs/scope/1-auto-digitizing-quality.md`
   for the commit-level breakdown. Whatever the plan doc queues past these
   is still open; re-check the plan doc itself rather than trust this
   bullet's row count going forward.
4. **DT-first M2/M3 onward** — the classifier swap itself, the change a
   customer can see. Corpus-gated *and* sew-out-gated, and it needs the
   corpus disagreement table M0 produces before it can be judged.
   **Resolution: the swap as designed was measured and REJECTED**
   (2026-08-11, `docs/dt-first-verdict-2026-08-11.md`): the patented rule as
   printed sends 62/83 clean satins to fill, and every corrected arm loses
   the disagreements it creates — it sits on MASTER_SCOPE's don't-build
   list. What survived instead: the DT consulted as ADDED gates inside
   `classify_ribbon` (`docs/satin-gate-attribution-2026-08-16.md`) and
   Law 31's photo-lane width floor (2026-08-22, see the digitizer section).
   The 37-file corpus leg stays blocked on Kent's local run either way.

A sew-out is still not scheduled — Kent's explicit call: more work first,
don't push for it.

## Known bugs — the defect 55 entry as it stood

*Moved from COOKBOOK.md 2026-11-19.*

- **A hand-drawn shape with an anchor a pixel from the last one sews a spike
  at that corner — the gesture that made them is FIXED 2026-10-03, the offset
  is NOT (MASTER_SCOPE defect 55).** The short edge to such an anchor doubles
  back, and `offsetRing` gives its end the whole mitre clamp, three times the
  pull compensation: on terry a 40 mm box is filled 1.73 mm past the drawn
  ring there, where a clean corner has 0.85. They came from a double-click,
  which is two clicks and then a `dblclick`: the second click was taken as an
  anchor unless it landed within 0.5 canvas px of the first
  (`DUP_POINT_EPS_PX`), and one slip in four was refused as crossing instead,
  so the double-click finished nothing. `ManualPanel.onCanvasClick` now lets
  a click with `detail` 2 go by (the field reads `detail` for its own
  double-click too), so no new shape gets one. **Still open:** a shape saved
  before then keeps its anchor and its spike, and two anchors dragged to one
  hoop corner make another. Curing those means the offset (a bevel past the
  clamp), which moves every sharp corner under a preset: Kent's call, not
  built. It is NOT the closed-ring wedge fixed the same day (that is a point
  said twice to within rounding, and no Studio lane sends one), though it is
  the same function and the same clamp. `node tools/closed-ring-census.mjs`,
  table 4; `app/e2e/manual-double-click.spec.js` drives the gesture in a
  real browser.

## Known bugs — fixed entries (DST axis, gradient fragmentation, BACKGROUND_ENCLOSED, tight-crop flood)

*Moved from COOKBOOK.md 2026-11-19.*

**One open as of 2026-10-03, above (its offset half).** Every entry below this
line is fixed and is kept for its trail. Put a new unresolved bug at the top,
above this line.

- **DST axis transposition — FIXED 2026-09-08, both halves. The phantom end
  stitch is FIXED too (#415).** EMB-Bot's own DST codec was transposed
  against the Tajima/pyembroidery standard in both directions. Four
  independent sources and a clean-room decode confirmed it. It shipped
  undetected because browser DST round-tripped correctly against itself.
  - The importer went standard first, in PR #404.
  - The writer followed in `bca5a504`. `encodeRecord` is now byte-identical
    to `pystitch.DstWriter.encode_record`, and `decodeDSTStandard` is a plain
    alias of `decodeDST`.
  - The phantom end stitch was the `end` record written as a move.
    `src/dst.js` now stops at `if (st.type === "end") break;`.

  **Do not "fix" either half back.** This entry kept saying the writer was
  "still transposed and still Kent's call" for weeks after it was fixed. A
  stale instruction like that is how `crossval-stitch-formats.mjs` came to
  tell its reader to un-fix the axis (memory,
  `stale-diagnostics-and-two-flips-2026-09-13`).

  **One thing stays true:** a `.dst` that EMB-Bot wrote BEFORE the fix is in
  the old dialect and re-imports transposed. Nothing repairs old files. The
  full trail is in CLAUDE.md footgun #1, `dst-codec-axis-discrepancy` in
  memory, and `docs/dst-axis-verdict-2026-07-31.md`.
- **Gradient-class designs fragment before blend treatment** — **FIXED
  2026-08-03**, same-day follow-up session. `gradient` class still segments
  via plain k-means (23 regions on the repro fixture, unchanged), but every
  fragment now sews its fill rows at one shared angle
  (`SourcePixels.design_row_angle_deg`, `stage6_blend.
  detect_design_ramp_angle`) instead of each independently computing its
  own — the "patchwork of differently angled wedges" is closed. Root cause
  was narrower than first suspected: all 23 fragments were hitting
  `blend_fill`'s plain-tatami FALLBACK (post-quantize color bands are
  already near-uniform, so per-fragment ramp detection rarely fires), and
  that fallback's hardcoded `angle_deg=None` was the actual bug. Also:
  fitting lightness alone (as `detect_ramp` does per-region) misses the
  repro fixture's ramp entirely (r2 0.003) because it's a hue rotation, not
  a lightness slope — the design-wide detector fits L/a/b independently and
  takes whichever channel carries it. Fragment count and radial-ramp angle
  sharing are explicit non-goals, left open. Full writeup: the plan doc's
  "Defect 1 update" section.
- **`BACKGROUND_ENCLOSED` drops enclosed white icon linework as a hole**
  even when it survives stage 1's background detection intact — root-caused
  2026-08-04 (same session as this bullet was first written). Corrected
  location: `stage1_prep.py::prep`'s no-alpha color-heuristic branch
  (`enclosed = close & ~border_bg`, folded into `bg` before `fg`), NOT
  `stage3_segment.py` as first suspected — enclosed pixels never reached
  stage 3, or vectorization, or ever got a `shape_id`, which made the
  warning's own "toggle it back on in review" claim false: there was no
  shape for a review edit to name. Repro fixture:
  `digitizer/testdata/photo/repro_gradient_white_icon.png`. Original
  diagnosis:
  `docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`.
  Design: `docs/superpowers/plans/2026-08-04-enclosed-background-restore-design.md`.

  **FIXED, later 2026-08-04 — the full cross-cutting slice landed:**
  `stage1_prep.py` now joins enclosed pixels to `fg`, `stage4_vectorize.
  tag_enclosed_background` tags them post-vectorization, `pipeline.py`
  resolves a `stitched` shape-override defaulting to "not enclosed" and
  excludes only at `plan_stitches`, the service (`digitizer_service/app.py`)
  accepts/validates/exposes the `stitched` key, and the Studio Layers panel
  gained a restore control for it. See
  `docs/scope/1-auto-digitizing-quality.md` for the
  commit-level breakdown. **The one caveat that kept this from working
  end-to-end through the actual UI is fixed too, merged PR #22:** Studio's
  real upload path manufactured an opaque alpha channel that defeated
  background detection entirely; a fully-opaque channel is now discarded
  as information-free. Verified post-merge at the HTTP level (opaque-RGBA
  twin of the repro fixture now matches its RGB original exactly), and the
  live-browser gap this sentence used to flag is closed:
  `app/e2e/digitize-background-enclosed.spec.js` drives the full flow —
  real upload, real service, banner, restore, re-stitch — through the real
  DigitizePanel, and runs in the `studio-e2e` CI job.
- **Background detection flooded the subject out on tight photo crops**
  (the snowy-owl report: white bird on a beige wall, the bird's body
  "recognized as background" and deleted) — **FIXED 2026-08-11**, two
  stage-1 guards, both config-gated:
  1. The background-EXISTENCE guard, hand-ported from the orphaned
     `fix/bg-existence-guard` branch (73e0665 — so "closed-by-inference"
     above was wrong: PR #22 fixed a different problem and this one was
     still live). If the modal border color describes less than
     `cfg.bg_border_agreement_min` (0.75) of the border ring, the art runs
     edge to edge: nothing floods, `BACKGROUND_ABSENT` fires. Re-measured
     under the enclosed-regions semantics: real backgrounds agree 0.925-1.0
     with their own ring, full-bleed art 0.355 and below; bare cloth on the
     gradient repro 27.0% -> 1.1% end to end.
  2. The SUBJECT-DOMINATED-BORDER guard (the owl itself — a tight crop
     passes guard 1 because the subject IS the ring's modal color, 0.827 on
     the committed repro). The tell is a second coherent border color (the
     wall peeking through the crop margins): largest coarse color bin among
     ring pixels the modal mask does not claim, >= `cfg.bg_border_rival_min`
     (0.10; measured 0.000-0.021 on every real-background fixture, 0.173 on
     the repro), with the modal color also failing to hold a majority of
     the frame's corners. Nothing floods; `BACKGROUND_UNCERTAIN` with
     `reason: "subject_dominated_border"` says why. Bare cloth on the owl
     repro 93.4% -> 3.0% (pre-fix, the subject's whole body was deleted).
  `bg_mask` is bit-identical on all nine real-background fixtures; the
  stage-2 photo-lane golden was deliberately re-captured for the two
  full-bleed fixtures the existence guard changes (repro_gradient_white_icon,
  photo_subject_stub). New fixture: `digitizer/testdata/photo/
  tight_crop_pale_subject.png`. Tests that pin the ENCLOSED machinery on the
  repro fixture now disable the guards explicitly (`repro_cfg` in
  `tests/test_enclosed_background.py`).

## Digitizer flags — the ON-since-2026-10-11 and built-OFF enumeration (as it stood through 2026-11-18)

*Moved from COOKBOOK.md 2026-11-19.*

Check the live default before relying on this list —
`grep -n "<flag>: " digitizer/digitizer_core/config.py` — and read the
comment block above it, which carries the measurement and the flip in Kent's
words. **Three registries travel with every flip, and a flip PR touches all
three:** `tests/conftest.py`'s `PRE_FLIP` (the pre-flip value, so a test
pricing one OTHER flag measures against the engine its arms were made on —
the dict's comments are the flip log), `tools/pro_parity/flagcost.py`'s
`FLAGS`, and `tests/test_off_flags_smoke.py`, which enumerates every bool
field that defaults False and runs the pipeline with it True — a flag leaves
that list by itself when it flips. `tools/off_flags_sheet.py` draws the OFF
set.

**Flipped ON since 2026-10-11 (Kent's calls, in order):**

- `two_tone_snap` — ON 2026-10-11 (PR #821; Kent's approval 10-08, "fix the
  roof-line bug, then flip"; defect 58): a black-and-white raster is
  thresholded to its two inks before any region exists.
- `clip_parent_keeps_ink` — ON 2026-10-12 (PR #856, Kent 10-12; half of
  defect 61): after stage 5's clip the shape keeps the piece carrying its
  INK, not the largest. `clip_keep_pieces` (PR #853) stays OFF.
- `lettering_columns` — ON 2026-10-12 (PR #863, Kent's ruling 10-12): the
  Column lane sews lettering as columns. Its guards followed on 10-13:
  `lettering_columns_skip_blobs` + `lettering_columns_ink_link` (PR #890),
  `lettering_columns_icon_guard` (PR #899), `lettering_columns_square_ends` +
  `lettering_columns_inside_connectors` (PR #922). Still OFF in the family:
  `lettering_columns_small_stem` (PR #896), `lettering_columns_fold_cuts` and
  `lettering_words` (below).
- `small_glyph_keep` — ON 2026-10-13 (PR #908; Kent, option A): stage 4 keeps
  a rescued small glyph's counters and its ink under an earlier colour.
- `small_text_true_size` — ON 2026-10-14 (PR #955; Kent, WoK 56 option A):
  small lettering is re-traced at its true size and thin letters sew as bean
  centrelines. **It is a SWITCH, not a flag**: ON, it fills seven other
  fields from `config.SMALL_TEXT_TRUE_SIZE` (`small_text_keep_stray_lines`
  among them — PR #960's THE fix, live only because the switch fills it), and
  `None` on one of the seven no longer means off. Build a fresh
  `PipelineConfig(..., small_text_true_size=False)` for the OFF engine;
  `dataclasses.replace` keeps the filled values. Its counter guard is
  `SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM` 0.45 mm × 40 / `thread_wt`, an unsewn
  gate-1 candidate 0.011 mm above the measured loss
  (`.claude/memory/small-text-true-size-guard-2026-10-15.md`). Measure small
  text on `tools/fremont_triage.run_arm` (the Studio's own `/digitize`
  request), not on `run_stages`: they cluster differently.
- `text_cluster_rescued_ink_link` — ON from its first commit, 2026-10-15 (PR
  #976, on Kent's directive to clear his five red circles; four of the five
  were a stale service on his box): the text tagger's RESCUED round links on
  one ink (CIEDE2000 20 on the job's chart), as round 2 has since 09-03, so
  Fremont's rescued E at 80 mm no longer joins the tan date. Round-1
  partitions identical on 12 of 17 corpus designs; the function's own default
  stays False and the pipeline passes the config's value.
- `bean_letter_counter_hold_mm` = 0.25 and `bean_letter_bay_hold` = 0.2 — ON
  2026-10-15 (PR #977; Kent's "flip both holds ON" over stitching out first):
  needle points held off a small counter (#952) and stations off an open bay
  (#967). Plain defaults, deliberately not switch values, so an explicit
  `None` is OFF everywhere and the sew-out card tools can pin it. Only
  designs with bean letters move, by a few stitches each; both values are
  gate-1 candidates the cards settle.
- `detail_spokes` — built OFF 2026-10-15 (PR #980), ON 2026-10-16 "tightened"
  (PR #983, merged 10-18): a sub-floor detail of another colour enclosed by
  one shape with ≥ `MIN_TIPS` 4 tips sews as one spoked run on top of its
  host (Fremont's Wisconsin star); the spoke floor is
  `machine.DETAIL_SPOKE_MIN_MM` 1.45 × width / 92.6. Its Fremont OFF pin is
  the SIMD-keyed md5 above.
- Earlier than the range but corrected here, because this file had them
  wrong: `blend_fallback_underlay` ON since 2026-10-07 (it said False);
  `satin_slab_serifs` ON since 2026-10-08, together with
  `satin_free_end_square` (it said OFF); `satin_join_square` True, capped by
  `_STRAIGHT_MAX_MOVE_HALVES = 0.6` (a bend is not a corner);
  `letterform_priors_k` 0.75.
- Browser engine, same fortnight: `underlayDirection` ON (PR #836, Kent
  10-11) and `satinZigzag` ON under a width cap (PRs #904 / #930, Kent
  10-13 / 10-14) — "Architecture map", `satin.js` / `satinplay.js`.

**Built OFF since 2026-10-11 and waiting on Kent (the ones a session will
meet):**

- `dark_ink_floor_rescue` (PR #1232, 2026-11-03): a second dark read at `dark_ink_read_floor_mm` (1.0) added to the first, plus a stage-3 protect and a stage-4 crumb drop. Brings back a letter the dark read's `min_detail_mm` kernel closed (Pooh "HUNNY", 54.6 mm). It is a raster read threshold, not a stitch value; reads every dark thin stroke, so a row with no lettering can move. `.claude/memory/dark-ink-floor-rescue-2026-11-03.md`.
- `open_cored_counters` (PR #988, 2026-10-19): a small counter round a
  page-coloured core stays a hole of its letter (golden_tee's O at 4–5 mm).
  Opens the O only a little and makes five false positives on the phone
  screenshot; the PR's own read is "stays OFF until the satin tiers hold off
  the hole and a guard keeps it off non-lettering detail".
- `lettering_columns_fold_cuts` (built OFF 2026-10-13, PRs #887 / #893; cures
  PR #972, 10-15; sewn judge + coverage guard PR #986, 10-19): cuts a
  lowercase shoulder where a column folds. FLIP-READY by its own numbers (no
  glyph sews worse ON at 50 / 80 / 120 mm; lowercase folds 5 → 0 at 80 mm)
  **and costs 2–3.4× the digitize time on lowercase**, because the judge sews
  every candidate cut. Kent's call; the instrument is `tools/lowercase_angle.py`
  plus `outline_cut.sewn_knots`.
- `lettering_words` (built OFF 2026-10-08): the one-word-model lettering
  tagger. MASTER_SCOPE 57 says NOT ripe — a flip would SHRINK the Column lane
  on golden_tee (9 → 6 shapes); judge any flip with
  `tools/script_lowercase_census.py`.
- `thread_wt` (40, a PROFILE, not a flag) and the `hairline` tier (PR #848,
  2026-10-11): thread weight moves satin spacing and the hairline tier's
  admission and run width — deliberately not the minimum stitch, fill row
  spacing or the stage-4 area floor; 60 and 75 are unsewn candidates.
  `hairline` sews a one-thread stroke as one run instead of the three-pass
  bean; every `hairline_*` sibling (`_over_ground`, `_from_lines`,
  `_lines_strand_test`, `_lines_strand_mass`, `_lines_chain`,
  `_lines_gradient`, `_lines_logo_refusal`, `_coverage_guard`) is OFF and
  most are measured negatives — read `config.py` before building a ninth.
- `forbid_gap_mm` (PR #846, 10-11; `None` is OFF): closes sub-threshold gaps
  between colours (defect 47, Law 26); 0.8 is the documented candidate and
  waits on card block 6.
- `small_print_floor` (PRs #873 / #878 / #880, 10-12/13): no Column-lane
  stitch over a letter counter; reaches the run and fill tiers.
- Also OFF: `small_lettering_skeleton` (#913, #936),
  `small_dot_rung_lettering` (#939, #975), `small_letter_ties` (#956),
  `ink_ground_ring_mm` (#958), `bean_letter_passes` (#950),
  `edge_cap_bean_pitch_mm` (#969), `preflight_glyph_metric` (#945),
  `fill_technique="fur"` (#920, API-only), `hair_regions_directional` (#925, a
  measured negative), `subpixel_corner_runs`, `bg_structural`,
  `clip_keep_pieces` (#853). `coverage_edges` is DEPRECATED (Kent 2026-10-12:
  no). `flat_page_fringe_exclude` (2026-11-03, `flat_page_fringe_px`: the
  band's floor; `flat_outline_max_mm`: thin-outline width; the page-edge
  blend and the outline's inner blend leave the flat palette fit and the
  stage-3 chain rescue; `memory/flat-page-fringe-2026-11-03.md`).
  `sliver_prune` (2026-11-10, flat and gradient classes, after the palette
  is fitted so no thread moves: a page-coloured mask at most 1.5 source
  pixels wide on the silhouette is dropped, an off-colour tendril wedged
  between other masks goes to the one it lies in; widths are in SOURCE
  pixels; `digitizer_core/sliver_prune.py`,
  `memory/sliver-prune-2026-11-10.md`).
  `test_off_flags_smoke.py`'s `OFF_FLAGS` is the live list.

## Running things — the `runner_id: 0` outage notice (2026-08-09 → 08-21)

*Moved from COOKBOOK.md 2026-11-19.*

**The `runner_id: 0` outage is OVER — do not merge past a red check on its
account.** From 2026-08-09 this file carried a standing "unresolved"
note: CI checks from PR #106 onward died in ~2-4 seconds with `runner_id:
0`, no runner ever assigned, and Kent was merging past red checks that
matched that signature. That workaround is retired. Runs now get real
runners and execute to completion — run 646 on `main` assigned
`runner_id: 1000001710` and spent 12m47s inside its `Digitizer tests`
step before failing, and runs 649/653/654 the same day were green at
13–18 minutes apiece. **A red check today is a real failure, so read the
job log rather than assuming the old signature.** *(confirmed 2026-08-21 —
GitHub Actions API, runs 32486606246 / 32490814989 / 32493902438 /
32494954449 on `main`)*

## Running things — failure class 1, the remove-and-see check (2026-08-22)

*Moved from COOKBOOK.md 2026-11-19.*

   **The remove-and-see check is no longer unowned — it was run 2026-08-22.**
   On Linux with the digitizer job's exact Python (3.12) and requirements.txt
   pinned exactly, two of the five deselects (`logo_alpha.png` on the flat-lane
   and photo-dispatch goldens) PASS and three FAIL; the same split holds on
   3.13, so it is not version skew. Those two are now removed from the
   workflow, restoring the coverage they were costing, and the list was
   three — two since 2026-10-08, when the towel tuple proved identical on
   three machines, AVX-512 and forced-AVX2 alike, and went back into
   `tests/test_pushcomp.py`'s `GOLDEN_FLAG_OFF`.

Two sentences about the deselect count, cut from the same section in the
same refresh (verbatim):

> It was
> five until 2026-08-22, when the remove-and-see check below was finally run,
> and three until the towel row was re-pinned on 2026-10-08.

> it was five until
> 2026-08-22 and three until the towel `test_pushcomp` row was re-pinned —
> this sentence said "five" for hours after the workflow said three, and
> "three" for twelve days after it said two.
