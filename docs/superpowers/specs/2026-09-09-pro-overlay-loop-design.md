# The pro overlay loop — design

**Date:** 2026-09-09. **Status:** design approved by Kent in chat (approach 1
of 3, then the eight-section design as written); this file is the spec for
`writing-plans`. **Lane:** `claude/pro-overlay-loop`.

Kent, 2026-09-09, when asked what "photo recognition improvements" meant:

> Take the professionally digitized .dst files we have, take the logo/image
> from that same file, put it into emb-bot, digitize it and THEN overlay it
> on top of the professionally digitized logo. From here, you can compare
> the differences, see what's different and replicate the output in emb-bot
> by modifying the respective code.

**Kent's ruling on WHAT to replicate (same day, first question):** craft
only. Auto-target HOW the pro lays thread — satin-vs-fill per element,
column width, stitch direction, row pitch, underlay recipe, sew order and
trims, cone count. WHAT is sewn where the pro departed from the artwork
(BECKER's filled hollow letters, Gaulke's re-composed layout, MFab's bolder
keyline — `docs/pro-parity-real-art-2026-08-15.md` §3) is catalogued per
design and put to him, never copied.

---

## 0. What already governs this — read before changing the design

- **The scorecard already IS "match the pro", and it is anti-correlated
  with visual quality** (`docs/pro-parity-real-art-2026-08-15.md` §5:
  real-art output looked better and scored 12.8 lower). Its `coverage`
  component pays for every decision that differs from this one digitizer.
  This loop therefore emits NO score and NO ranking. It emits pictures and
  a table of measured properties. ROADMAP gate 4 (no quality claim on a raw
  agreement number) is satisfied by construction: nothing here is an
  agreement number.
- **A pro scores 75–84 against a pro** (`selfconsistency.py`, §11 of the
  same doc). The pro's file is evidence of a sewable answer, not the only
  one. That is why shape decisions are Kent's and why the catalogue reports
  the pro's value beside ours instead of a target.
- **`direction` and `sttype` sit near chance on real artwork** (§5 —
  `direction` is 0.00 on 11 of 15 designs). Those two are exactly the craft
  half. The loop's first rows will be there.
- **Measure in a git worktree, never a shared checkout** (DOCTRINE; three
  baselines invalidated by commits landing mid-run). Prep runs happen in a
  worktree pinned to a ref; the scratchpad worktree used on 2026-09-09 is
  the pattern.
- **`study_pro.classify` refuses columns whose stitches are under 0.7 mm by
  design** and would call our hairline satin "other" (its own NOTE,
  2026-09-04). It reads the PRO's file only. Our tier comes from the plan.
  `satin_columns.py` is the scale-free instrument for widths on both sides.
- **The Studio's renderer is the judge, not a sew-out** (Kent, 2026-09-04:
  no physical tests until he says). Overlay renders go through
  `digitizer_core/stitchviz.render_design`, the same lit-filament model
  `preview.js` draws — so what Kent compares is what the product shows.
- **Renders that carry a finding are committed under `docs/renders/<topic>-<date>/`**
  (the 2026-09-09 junction and rail-comp PRs set the pattern). The prep
  dirs themselves are not committed; they are large and reproducible.
- **`git log --all` lies on stale remotes; `git fetch --all` first**
  (CLAUDE.md footgun 8). Done on 2026-09-09 before this was written: seven
  PRs (#433–#439) landed while the brainstorm was paused, none of them this
  loop; `pro_layers.py` (#436) is the nearest thing and is reused below.

## 1. Goal, and what this is not

**Goal.** For one design at a time, put EMB-Bot's stitches and the pro's on
one registered canvas, and beside it one table that says, per element, how
each side laid its thread — so a session (or Kent) can point at a row, build
the mechanism behind a flag, and re-overlay in one command.

**Success looks like:** three designs (Becker LC large, Becker hat large,
Fremont patch) each with an overlay sheet and a catalogue on `main`; Kent
picks a craft row; the mechanism for it lands behind a `cfg.*` flag with the
overlay before/after in `docs/renders/`. Then the next row.

**Not in scope (deliberately):**

- No score, no cross-design number, no reweighting of `scorecard.py`. It
  stays as it is.
- No engine change in this lane. The loop produces the case for one.
- No Studio viewer. If the PNG flicker pair is not enough for Kent's review
  passes, a Studio overlay over the same registration is the follow-up
  (approach 2 of the brainstorm, declined for now).
- No new physical constant. Any number the loop surfaces that fabric would
  have to settle (a widen-to width, an underlay inset) is reported with
  the pro's value and gate 1 named, not adopted.

## 2. Inputs and the corpus

**Unit of work:** one design slug from `prep_both.DESIGNS`, prepped into a
per-design directory by `tools/pro_parity/prep_both.py <slug>` (the `real`
lane: the customer's actual artwork). The directory already holds everything
the loop reads:

| file | written by | used for |
|---|---|---|
| `art.png`, `art_meta.json` | `real_art.prepare` | the ink mask (shape rows), re-digitizing under a `--flag` |
| `pro_stitches.csv` (`block,run,trim,jump,x_mm,y_mm`), `pro_blocks.json` | `prep_all.decode` | the pro side, in its native hoop frame, **y-up** |
| `ours_stitches.csv`, `ours_blocks.json`, `ours_meta.json` | `prep_all.run_ours` | our side, bbox-centred, **y-down** (plan frame) |
| `ours_regions.json` (`shape_id, area_mm2, thread, tier, bounds, wkt`) | `prep_all.run_ours` | the per-element frame of the catalogue |
| `manifest.json` (parent dir) | `prep_both` | the pro source path, for `pro_trims_from_source` |

**Corpus resolution — one harness change.** `prep_all.find_file` resolves
art by the Drive's file names (`Becker Marine/Becker Marine Logo.png`,
`Hotel Fremont/Hotel Fremont Logo.webp`), and the Drive is not mounted on
Kent's machine as of 2026-09-09 (`G:/` absent; `prep_both` failed 0/3 on
`FileNotFoundError` for the art while decoding every pro file fine). The
same artwork is committed:

| slug prefix | committed art |
|---|---|
| `becker_*` | `digitizer/testdata/becker_marine_logo.png` |
| `hotel_fremont_*` | `digitizer/testdata/photo/logo_hotel_fremont.webp` |
| `gaulke_roofing_*` | `digitizer/testdata/photo/logo_gaulke_roofing.png` |
| `precision_drone` | `digitizer/testdata/photo/drone_render.png` |
| `tires_hat_3d` | `digitizer/testdata/logo_script_tires.png` |
| `bridge_*` | `digitizer/testdata/photo/logo_bridge_bar.jpg` |

`prep_both` gets an `ART_FALLBACK: dict[slug, Path]` consulted when
`find_file(art_rel)` returns `None`, and the manifest records which source
was used (`art_prep.art_source` already carries the path). MFab has no
committed art and stays Drive-only. Pro files resolve from
`PRO_PARITY_ROOT`, which on this machine is `scratch_kent/Embroidery Files`
(gitignored, present — 14 of the 15 designs). **Bridge Bar's pro PES is on
no local path and not in `Embroidery Files.zip`** (0 entries); it is
requested from Kent via the `pull-corpus` skill when its turn comes, not
blocked on.

**Runtime.** One design, one lane, is one `digitize()` call plus decoding —
minutes, not the hours of the full 15×2 run. The loop never runs the full
corpus.

## 3. Registration

Ours onto the pro, in the pro's frame:

1. **Axis.** Our CSV is y-down (plan frame); the pro's is y-up (hoop
   frame). `scorecard.load_side` already flips; the loop uses the same
   loader so both tools see one convention. A synthetic test pins it (§7),
   because a flipped overlay of a symmetric logo looks registered.
2. **Scale.** One uniform factor: the pro's ink-bbox width over ours, from
   the stitch extents (`pro_layers.py` does box-to-box per axis; this loop
   uses ONE factor so aspect is never silently corrected — an aspect
   mismatch is a finding, not noise). Reported as `scale` in every output.
3. **Shift.** `scorecard.register()` as it stands: solid-IoU hill-climb
   from two seeds, 1.0 mm down to 0.25 mm, 40 mm cap.
4. **Residual.** The registered solid IoU is printed on every sheet and
   written to `diff.json` as `registration.iou`. Below 0.5 the sheet says so
   in its title and the catalogue's shape rows are marked unreliable;
   Gaulke (re-composed, aspect 2.79:1 vs 2.35:1, search pinned at the
   boundary on 2026-08-15) is the known case and the reason there is no
   rotation or per-axis term: a registration that could absorb a redesign
   would hide the redesign.

## 4. `tools/pro_parity/overlay.py`

**Input:** a prep design dir (`--dir <out>/real/<slug>`), or `--slug` with
`PRO_PARITY_OUT` set. **Output**, into `<dir>/overlay/`:

| file | what |
|---|---|
| `overlay.png` | both sides on white at 12 px/mm, pro tinted magenta, ours cyan, overlap reads dark (multiply). Title line: slug, mm, `iou`, `scale`, stitch/trim/cone counts both sides |
| `pro_only.png`, `ours_only.png` | the two halves of the disagreement mask, each over a faint grey of the other side for context |
| `flicker_pro.png`, `flicker_ours.png` | the two sides rendered in their true thread colours, same frame, same crop, same size — for flipping between in any viewer |
| `crop_<name>.png` | with `--crop x0 y0 x1 y1` (mm, pro frame) at 36 px/mm, the four files above for that window; repeatable |
| `by_thread/<k>.png` | with `--by-thread`: one overlay per pro block, ours drawn from the block whose thread is nearest in CIEDE2000 (`preflight`'s ΔE00 helper), unmatched blocks listed in the title |

**Rendering.** Both sides become a `stitchviz` design dict
(`{"stitches": [{x, y, type}], "colors": [...]}` in 0.1 mm units) — ours via
`adapter.plan_to_design` when re-digitized, or from `ours_stitches.csv` +
`ours_blocks.json` when read from the prep dir; the pro via a small
`pattern_to_design(pattern)` added to `adapter.py` beside `design_to_pattern`
(its inverse; the 2026-09-03 review built the same thing inline and did not
keep it). Both are rendered with `render_design(..., fabric_bgr=white,
lit=True)`; the tint is applied to the rendered thread's luminance so the
filament shading survives and a satin column still reads as a column.

**Masks** come from the same renders (thread pixel ≠ fabric), so the overlay
and the diff masks agree by construction. The 0.125 mm `scorecard.raster`
is NOT reused here: it is an opacity-gated solid-area model built for
scoring; the overlay must show thread where thread is.

**`--flag NAME[=VALUE]`** (repeatable; `thin_strokes.parse_flags`): re-digitize
ours in-process from `art.png` at the pro's width with that `PipelineConfig`
override, cache the plan under `<dir>/flags/<hash>/`, and write the overlay
set with `_<flagname>` suffixed. `--against <hash>` overlays two of OUR
arms instead of ours-vs-pro (before/after of a mechanism, the render pair
the 09-09 PRs committed by hand).

## 5. `tools/pro_parity/diff.py`

**Principle:** one set of readers, pointed at two files. Prep already writes
our plan to `<dir>/ours.dst` (`prep_all.machine_meta`, through
`export.write_dst` — the `/export` path, standard axis since 2026-09-08),
and a `--flag` arm writes its own under `<dir>/flags/<hash>/ours.dst`, so
`satin_columns.passes_from_file`,
`row_pitch_union.segments_from_pattern`, `census_pro._elements/_phases`,
`border_pro` and `design_direction --pro` (#440, merged 2026-09-09) read
ours exactly as they read the pro. The one
exception is stated in §0: `study_pro.classify` reads the pro only; our
tier is the plan's (`ours_regions.json` `tier`, refined per run by
`plan.iter_runs()` kinds when re-digitized).

**Frame of the catalogue:** our regions (`ours_regions.json` polygons,
registered into the pro frame by §3). A pro run is assigned to the region
containing ≥ 60% of its points after buffering the polygon by 0.3 mm (pull
comp plus half a thread); a run assigned nowhere is pro-only residual. Our
runs are assigned by `shape_id`.

**Per-region rows (craft):**

| column | ours | pro | reader |
|---|---|---|---|
| tier | plan kind by thread length majority | `classify`/`_phases` token majority by length | plan / `study_pro`, `census_pro` |
| column width p50 / p90, share of penetrations in columns | `satin_columns.measure` on passes inside | same | `satin_columns` |
| dominant direction, spread R | 2 mm cells inside the region | same | `design_direction` (its `--pro` reader; #440) |
| fill pitch (union of passes) | `union_pitch` on fill segments inside | same | `row_pitch_union` |
| underlay recipe | run kinds in sew order (`underlay_*` then top) | `_phases` tokens, e.g. `R.Z.S` | plan / `census_pro` |
| layers p50 / p95 | `_coverage_map` inside the polygon | same, pro in our frame | `pro_layers` |
| density (thread mm / mm²), stitches, trims landing inside | counted | counted | plan / CSV — density is reported, never flagged: `FILL_ROW_MM` is ruled |

A row is **flagged** when the two sides disagree on tier, or a numeric
column differs by more than a stated tolerance (width ±0.3 mm or 25%,
direction ±15°, pitch ±25%, layers ±1): the tolerance is per column,
written in `diff.py` next to its reader, and is a display threshold, not a
score. Flagged rows sort first.

**Design-level rows:** stitches, jumps, trims, blocks, cones (distinct
threads; the count the machine bills), sew order as the block sequence with
the dominant region of each block, `max_colors` vs delivered.

**Shape rows — three tags, because Kent's ruling has two sides.** The
disagreement masks from §4 are split by the art's ink (`art.png`, the same
test `real_art.prepare` uses: alpha where it exists, else near-white):

| where | art has ink | tag | meaning |
|---|---|---|---|
| pro sews, we don't | yes | `dropped` | we lost an element — OUR defect (the "elements missing" theme) |
| pro sews, we don't | no | `redesign` | the pro added thread the art does not carry — Kent's call |
| we sew, pro doesn't | no | `dropped`-mirror, reported as `background` | we sewed ground — our defect |
| we sew, pro doesn't | yes | `redesign` | the pro left art unsewn or merged it — Kent's call |

Components under 2 mm² are summed into one "dust" line per tag rather than
listed. Each listed component carries area, centre (mm, pro frame), nearest
our region, and the crop command that shows it.

**Outputs:** `<dir>/diff.json` (every row, machine-readable, with
`registration`), `<dir>/catalogue.md` (flagged rows first, then the rest,
then shape rows under a heading that says *Kent's call*), and one line on
stdout per flagged row so a session reading a run sees the list without
opening files.

## 6. The loop, end to end

```
prep_both.py <slug>                       # once per design (minutes)
overlay.py --dir <out>/real/<slug>        # overlay set + iou/scale
diff.py    --dir <out>/real/<slug>        # catalogue.md, diff.json
  → pick a flagged craft row
  → build the mechanism behind cfg.<flag> (its own lane, TDD, instrument first)
overlay.py --dir ... --flag <flag>        # ours-after vs pro
overlay.py --dir ... --flag <flag> --against <baseline-hash>   # ours before/after
diff.py    --dir ... --flag <flag>        # the row moved, or it did not
```

Everything after the arrow is outside this lane. This lane ships the three
tools and their first three catalogues.

## 7. Tests

`digitizer/tests/test_pro_overlay.py` and `test_pro_diff.py`, synthetic
unless stated, all under a second each:

1. **Identity.** Ours vs a copy of ours shifted 7.3 mm, scaled 0.95 and
   flipped to y-up: registers to IoU ≥ 0.98, `scale` within 1% of 1/0.95,
   catalogue has zero flagged rows and zero shape rows over dust.
2. **Axis.** The same pair WITHOUT the y flip must NOT register above 0.6 on
   an asymmetric fixture (an L-shaped satin + one fill) — the test that
   makes a silent flip visible.
3. **Tier.** Two synthetic regions, one sewn satin on both sides, one satin
   ours / tatami pro (built with `stage6_fill` on the same polygon): exactly
   one flagged row, column `tier`.
4. **Width.** Same column drawn at 2.0 mm vs 2.6 mm: flagged on width, not
   on tier.
5. **Shape tags.** A pro-only rectangle over ink → `dropped`; a pro-only
   rectangle over bare art → `redesign`; an ours-only rectangle over bare
   art → `background`.
6. **Readers agree.** Our plan written to DST and read back through
   `passes_from_file` measures the same column p50 as `passes_from_plan`
   within 0.05 mm (guards the export path the diff rests on).
7. **Smoke on committed data.** `testdata/reference/becker_hat_polo_large_beckers_logolc.dst`
   as the pro and `testdata/becker_marine_logo.png` as the art at 95.7 mm:
   the loop runs end to end, writes every file in §4/§5, registration IoU
   above 0.5. This is the CI-runnable case (no corpus needed), and is
   deselected from `-n auto` only if it exceeds 60 s — measure, do not
   assume.
8. **Fallback map.** `find_file` miss → `ART_FALLBACK` hit → manifest
   records the committed path.

Every test is watched go red first (the 2026-08-25 rule: a regression test
proves nothing until it has failed).

## 8. First run, and how it is read

Becker LC large (95.7 mm, `left_chest`), Becker hat large (101.9 mm,
`hat_front`), Fremont patch (92.5 mm, `patch`). Overlay sheets and
catalogues go to `docs/renders/pro-overlay-<date of the run>/` and the
catalogue tables into `docs/pro-overlay-first-run-<date of the run>.md`,
with the exact commands. The doc ranks nothing; it lists the flagged craft
rows per design with both sides' values, and the shape rows under *Kent's
call*.

Prep already ran on 2026-09-09 for these three (real lane, `main` at
`53f0643`, scratch worktree): pro / ours stitches 12,356 / 24,406 (hat),
11,274 / 20,354 (LC), 15,458 / 17,378 (Fremont); 44 s, 44 s and 174 s.
The unregistered renders of Becker LC already show the two headline rows:
the pro fills BECKER's bodies (a `redesign` row) and sews MARINE as
per-stroke satin where ours is tatami on every letter but the I (a `tier`
row). Ours at roughly twice the pro's stitch count on Becker is the
0.15 mm fill row (`FILL_ROW_MM`, Kent's 2026-09-03 ruling) doing what it
was ruled to do, and a `density` column will say so rather than flag it.

Expectations the record already sets, stated so the first run can confirm
or refute them rather than rediscover them: MARINE tier (our tatami, pro
satin 5–7 mm columns — `docs/quality-review-2026-09-08.md` §2b, now
`cfg.wide_columns` #434); satin share of penetrations (2.2% vs 44.3%,
MASTER_SCOPE area 1); one fill angle (pro 20.5° at every size, ours spread
— #440 unmerged); Fremont lettering column width (pro 0.82–0.90 mm, ours
bean runs — `docs/kent-review-2026-09-03.md`); trims (Becker 29 vs 12);
Becker letter bodies (`redesign`, 40.8% of the design).

## 9. Risks and open questions

- **Registration on redesigned layouts.** By design it fails loudly
  (IoU < 0.5). If Kent wants Gaulke in the first run anyway, the catalogue
  still works per region where local overlap exists; the sheet says the
  frame is unreliable.
- **Pro runs that span two of our regions** (the pro sews BECKER as one
  outline where we have several) go to the region holding ≥ 60% or become
  residual. Residual mass is reported per design so a large number is
  visible, not silently dropped.
- **Runtime of `--by-thread` and crops** is render-bound, seconds each.
  The `--flag` re-digitize is the only slow step and is cached.
- **The venv is Python 3.14.6 on Kent's machine**, not the 3.12 CLAUDE.md
  describes; everything here ran under it on 2026-09-09. Noted for the
  plan, not a blocker.

## 10. Staging (for `writing-plans`)

1. Harness: `ART_FALLBACK` + test 8; `adapter.pattern_to_design` + a
   round-trip test. Small, no engine change.
2. `overlay.py` with tests 1, 2, 7 (smoke, overlay half).
3. `diff.py` with tests 3–6 and the smoke's diff half.
4. First run on the three designs; renders and the first-run doc;
   MASTER_SCOPE "Evaluation corpus & harness" entry and DOCTRINE line for
   the three-tag rule; COOKBOOK pointer.

Each PR ready-for-review with auto-merge armed, per CLAUDE.md.
