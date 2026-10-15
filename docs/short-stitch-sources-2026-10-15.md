# Short-stitch sources census — 2026-10-15

Follow-up to `docs/speed-advisory-review-2026-10-14.md` §5/§6(c). That review
found EMB-Bot's sub-1 mm and stacked stitches at 2-3x the pro's rate and asked
which part of the engine emits them. This answers it. **Measure only: no
engine change, no flag, no new artwork, no stitch output moved.**

**Answer.** Of 109,987 penetrations in the 11-design corpus, 56,081 (51.0%) are
short or stacked, against 23.9% in 28 pro DSTs (ratio 2.13, 95% CI 1.56 to
3.05 over pro customers). Two readings of "worst source" disagree, and the
disagreement is the finding:

- **Biggest by count: tatami fill** (`stage6_fill.emit`), 39.2% of all short or
  stacked penetrations. But it makes them in proportion to its size (45.4% of
  penetrations, concentration 0.86), its short stitches are the 0.15 mm row
  turn that Kent's 0.15 mm row pitch dictates, and where the same test finds
  tatami on both sides its stacking is 1.3x the pro's (CI 1.03 to 2.06).
  Fill is where the count is, not where the excess is.
- **Worst per stitch: `stage6_border.run_outline`**, the bean emitter. It is
  12.6% of penetrations and 24.4% of short or stacked (concentration 1.94);
  every stitch of its two outputs is short or stacked (99% and 100%). It is the
  largest single source (47%) of short stitches *in chains*, the class that is
  4.2x the pro's (CI 2.95 to 6.33), and 30% of stacking on a neighbouring pass
  (2.95x, CI 2.08 to 4.40; fill has 40%). **That is the worst source, and §6
  prices the fixes for it.** Its larger half by penetrations is the run tier
  (small shapes sewn as an outline); the other is the design-silhouette **edge
  cap**, which sews on every design.

The engine's own floors say which are accidents and which are technique. The
bean pitch (0.73 mm, a pro median), the 0.8 mm lock leg and the 0.15 mm row
turn are chosen numbers. A satin column under 1 mm wide (`stage6_satin`, 7,461
sub-1 mm stitches) is the one source breaking a floor the engine itself
states (`MIN_STITCH_MM` = 1.0, playbook law 18). It is the second-priced fix.

## 1. What was measured

- **EMB-Bot side.** `python -m tools.short_stitch_sources corpus` digitizes the
  census tool's 11 fixtures at 80 mm, left chest, at **main `7b88b2f2`**
  (2026-10-15; #955 `small_text_true_size` ON was still open, so it is OFF here).
  The fixtures: `becker_marine_logo`, `logo_script_tires`, `logo_bridge_bar`,
  `logo_gaulke_roofing`, `logo_golden_tee`, `logo_hotel_fremont`,
  `screenshot_phone_ui_golke`, `logo_alpha`, `logo_whitebg`, `enthusiast_logo`,
  `owl_kent`. *The brief said 17 designs. The tool's corpus is 11; 17 is
  #951's count of machine test files, which are not part of it.* The totals
  reconcile to #951 (109,144 sewn stitches; 324,020 on the pro side).
- **Pro side.** The same 28 pro DSTs as #951: the 44 DSTs under
  `scratch_kent/Embroidery Files/` minus the 15 in `Test Files/` and the one
  satin-width sewout. They are labelled `p01..p28` and grouped into 11 customers
  (`c01..c11`); the tool prints no customer name.
- **Short stitch.** A sewn stitch under 1 mm (`<0.5` plus `0.5-1`), the
  census's bins. **Stacked.** A penetration within 0.5 mm of one of the
  3rd..20th before it (`near_hole`). Every figure below is per 1000
  penetrations (the machine's stitch count), which differs from #951's
  per-sewn-stitch bin shares by under 1%.
- **Attribution.** Each short or stacked stitch is charged to its *arrival*
  point's source. The tool reads the plan's provenance from a stream that is
  checked entry for entry against `export.plan_to_pattern` (a mismatch raises),
  and re-derives the census's own bins and `near_hole` before counting. Sources:
  the run's `kind` and `role`; **folded locks** (`apply_ties` puts the lock
  inside the host run, so the tool records the points each call added: `tie_in`,
  `tie_off`); the **link** stitch between two runs with no jump; and the
  **function that built the run**, taken from the call stack when each
  `StitchRun` is constructed.
- **Statistics.** A ratio is the pooled rate over designs, with a 95% percentile
  bootstrap (10,000 draws; 4,000 for the per-source tables; seed 20261015) that
  resamples EMB-Bot designs and, in the last column, **pro customers** rather
  than files: several pro files are variants of one customer's artwork
  (`p09`/`p10` differ by one short stitch, `p04`/`p14` by none). The customer CI
  is the one to read. **n is 11 and 11, so the intervals are wide.**

## 2. Against the pro

| metric (per 1000 penetrations) | EMB-Bot pooled | EMB-Bot p50 / p95 | pro pooled | pro p50 / p95 | ratio | 95% CI (designs) | 95% CI (pro by customer) |
|---|---|---|---|---|---|---|---|
| <0.5 mm | 103.3 | 94.8 / 132.5 | 23.6 | 19.2 / 53.6 | 4.38 | 2.99 - 6.46 | 2.86 - 7.71 |
| 0.5-1 mm | 232.1 | 230.3 / 422.9 | 82.0 | 85.3 / 138.5 | 2.83 | 2.19 - 3.76 | 2.08 - 4.03 |
| stacked | 323.9 | 307.2 / 446.0 | 169.2 | 136.1 / 304.2 | 1.91 | 1.45 - 2.60 | 1.31 - 3.05 |
| short or stacked | 509.9 | 502.1 / 723.7 | 239.1 | 204.1 / 406.6 | 2.13 | 1.71 - 2.74 | 1.56 - 3.05 |

The pro's spread is wide and one file is an outlier. `p23` (a TIRES logo) reads
938 per 1000, 929 of it stacked and almost none short; the other 27 files run
117-407. EMB-Bot's 11 designs run 377-724, so the lowest of ours (377) is just
under the pro's p95 (407). **Same customer, same logo** (the pairs where the pro digitized an
artwork a fixture is also made from):

| artwork | pro files | pro short or stacked | EMB-Bot | ratio |
|---|---|---|---|---|
| Becker Marine | 5 | 141 | 403 | 2.9 |
| Hotel Fremont | 2 | 181 | 502 | 2.8 |
| Golden Tee | 1 | 204 | 448 | 2.2 |
| Gaulke Roofing | 4 | 243 | 458 | 1.9 |
| tires logo | 1 | 938 | 377 | 0.4 (the `p23` outlier) |

On Becker the gap is mostly stacking (pro 93 per 1000, ours 307) rather than
short stitches (pro 65, ours 127).

## 3. By source

`share` is the source's share of all short-or-stacked penetrations. `rate` is
per 1000 of the whole design's penetrations (the rates add to the 509.9).
`within` is the fraction of the source's own penetrations that are short or
stacked. The pro has no provenance, so `vs pro` is the source's rate over the
pro's *whole* rate (239.1): how much of the pro's entire budget this one source
spends. It is not a like-for-like ratio.

| source | penetrations | <0.5 | 0.5-1 | stacked | short or stacked | share | rate /1000 | within | vs pro (95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| fill | 43,972 | 7,195 | 682 | 16,344 | 18,793 | 33.5% | 170.9 | 43% | 0.71 (0.41 - 1.09) |
| satin | 35,291 | 93 | 7,368 | 7,531 | 13,084 | 23.3% | 119.0 | 37% | 0.50 (0.30 - 0.87) |
| run (small-shape rescue) | 7,138 | 669 | 6,297 | 5,440 | 7,091 | 12.6% | 64.5 | 99% | 0.27 (0.10 - 0.56) |
| run / edge cap | 5,490 | 18 | 5,469 | 591 | 5,487 | 9.8% | 49.9 | 100% | 0.21 (0.10 - 0.43) |
| underlay | 6,650 | 1,351 | 173 | 2,132 | 3,581 | 6.4% | 32.6 | 54% | 0.14 (0.06 - 0.29) |
| run link (no jump between runs) | 3,118 | 1,180 | 820 | 1,092 | 2,203 | 3.9% | 20.0 | 71% | 0.08 (0.04 - 0.13) |
| tie off (folded lock) | 1,996 | 196 | 1,800 | 1,511 | 1,996 | 3.6% | 18.1 | 100% | 0.08 (0.05 - 0.11) |
| tie in (folded lock) | 2,375 | 112 | 1,788 | 563 | 1,916 | 3.4% | 17.4 | 81% | 0.07 (0.05 - 0.11) |
| travel | 3,881 | 546 | 1,126 | 376 | 1,889 | 3.4% | 17.2 | 49% | 0.07 (0.03 - 0.12) |
| border | 76 | 0 | 0 | 41 | 41 | 0.1% | 0.4 | 54% | 0.00 |

**By the function that built the run** (its locks and links folded back in).
`concentration` is the share of short-or-stacked over the share of
penetrations; above 1, the function emits more than its size predicts.

| function | short or stacked | share of short/stacked | share of penetrations | concentration |
|---|---|---|---|---|
| `stage6_fill.emit` | 21,998 | 39.2% | 45.4% | 0.86 |
| `stage6_border.run_outline` | 13,679 | 24.4% | 12.6% | **1.94** |
| `stage6_satin.satin_shape` | 9,215 | 16.4% | 24.1% | 0.68 |
| `columns.column_runs` | 7,442 | 13.3% | 13.1% | 1.01 |
| `stage6_satin._stroke_underlay` | 3,632 | 6.5% | 4.6% | 1.40 |

`run_outline` builds the run tier (a small shape's outline as a bean run: 7,138
penetrations) and the silhouette edge cap (`role=edge_cap`: 5,490). Both sew
beans at `BEAN_STITCH_MM` = 0.73 over `BEAN_PASSES` = 3, so a station gap is a
0.5-1 mm stitch and the next pass lands back in the same holes.

### What each source's stitches look like

Source-agnostic classes, so the pro can be split the same way. A short stitch is
**iso** when both neighbours are >= 1 mm (a row turn or a lone connector),
**chain** when a neighbour is short too (a bean pitch, a thin satin, a lock),
**edge** at a run boundary. A stacked penetration is **g5** when the earlier
hole is 3-5 penetrations back (a retrace or lock), **g10** 6-10 back, **g20**
11-20 back (a neighbouring pass).

| class (per 1000) | EMB-Bot | pro | ratio | 95% CI (pro by customer) |
|---|---|---|---|---|
| short, iso | 86.7 | 46.5 | 1.87 | 1.33 - 2.77 |
| short, chain | 235.2 | 56.2 | **4.18** | 2.95 - 6.33 |
| short, edge | 13.4 | 2.9 | 4.65 | 2.86 - 8.15 |
| stacked g5 | 99.8 | 62.3 | 1.60 | 1.03 - 2.90 |
| stacked g10 | 91.9 | 62.1 | 1.48 | 0.88 - 2.76 |
| stacked g20 | 132.2 | 44.7 | **2.95** | 2.08 - 4.40 |

| source | short iso | short chain | short edge | stacked g5 | stacked g10 | stacked g20 |
|---|---|---|---|---|---|---|
| fill | 6,565 | 1,214 | 98 | 4,319 | 6,223 | 5,802 |
| satin | 506 | 6,908 | 47 | 3,053 | 1,554 | 2,924 |
| run | 0 | 6,627 | 339 | 510 | 940 | 3,990 |
| run / edge cap | 0 | 5,481 | 6 | 94 | 170 | 327 |
| underlay | 1,392 | 130 | 2 | 1,565 | 284 | 283 |
| run link | 1,022 | 978 | 0 | 251 | 356 | 485 |
| tie off | 0 | 1,508 | 488 | 584 | 422 | 505 |
| tie in | 0 | 1,425 | 475 | 499 | 37 | 27 |
| travel | 56 | 1,598 | 18 | 83 | 104 | 189 |

- **Chain shorts are the largest gap (4.2x).** Their sources are satin 27%,
  run 26%, edge cap 21%, locks 11%, travel 6%, fill 5%. The beans and the thin
  satin are the whole story; fill contributes almost none.
- **Fill's shorts are isos.** 6,565 of its 7,877 short stitches are row turns
  (one row pitch, 0.15 mm, between two long stitches). The pro's *whole* iso
  rate is 46.5 per 1000 and fill alone is 59.7 per 1000 of ours: close, as
  expected of a pitch Kent ruled equal to the pro's.
- **Stacked g20 is the second gap (2.95x)**, 40% fill (adjacent rows) and 27%
  run (a three-pass bean ring of 11-20 stations returns to its own holes).

### Is fill's stacking the excess?

A penetration is **tatami-like** when two or more row turns (a stitch <= 0.5 mm
between two stitches >= 1 mm that reverse) lie within 12 entries. The same test
runs on both sides. On EMB-Bot's own provenance it flags 77.9% of fill
penetrations (recall) and 85.6% of what it flags is fill (precision); the pro's
recall is unknown, because a pro fill may turn differently.

| population | EMB-Bot | pro | ratio | 95% CI (pro by customer) |
|---|---|---|---|---|
| share of penetrations tatami-like | 36.4% | 8.7% | | |
| stacked, within tatami-like | 44.4% | 34.3% | 1.29 | 1.03 - 2.06 |
| stacked, within the rest | 25.5% | 15.3% | 1.67 | 1.11 - 2.67 |

EMB-Bot's stacking is 32.4% of penetrations against the pro's 16.9%, a gap of
15.5 points. Putting the pro's two rates on EMB-Bot's mix gives 22.2%, so the
gap splits **5.3 points composition** (we are 36% tatami, they are 9%, on
different designs), **3.7 points tatami rate** and **6.5 points the rest of the
design** (satin, run, underlay, locks). Most of the *rate* excess is outside the
fill.

## 4. Per design

| design | class | penetrations | <0.5 | 0.5-1 | stacked | short or stacked | tatami-like | two largest sources |
|---|---|---|---|---|---|---|---|---|
| becker_marine_logo | flat | 6,150 | 62 | 65 | 307 | 403 | 13% | satin 55%, underlay 23% |
| logo_script_tires | photo_scene | 2,732 | 95 | 38 | 266 | 377 | 24% | underlay 48%, satin 33% |
| logo_bridge_bar | gradient | 17,651 | 132 | 233 | 376 | 581 | 40% | fill 35%, satin 30% |
| logo_gaulke_roofing | gradient | 4,893 | 65 | 217 | 268 | 458 | 18% | satin 45%, fill 19% |
| logo_golden_tee | gradient | 8,361 | 38 | 305 | 193 | 448 | 5% | satin 59%, underlay 13% |
| logo_hotel_fremont | gradient | 14,456 | 84 | 301 | 346 | 502 | 30% | run 42%, fill 29% |
| screenshot_phone_ui_golke | gradient | 8,428 | 130 | 423 | 446 | 724 | 33% | fill 28%, satin 27% |
| logo_alpha | flat | 5,854 | 106 | 230 | 294 | 530 | 72% | fill 54%, run/edge_cap 37% |
| logo_whitebg | flat | 5,824 | 106 | 229 | 296 | 532 | 71% | fill 54%, run/edge_cap 37% |
| enthusiast_logo | flat | 2,447 | 93 | 261 | 347 | 503 | 13% | run 40%, satin 15% |
| owl_kent | gradient | 33,191 | 119 | 182 | 313 | 468 | 44% | fill 47%, satin 17% |

The worst source changes with the design: satin on the three satin-heavy logos
(Becker, Golden Tee, Gaulke), fill on the photo and the flat logos, `run` on the
two lettering-dominated ones (Fremont, enthusiast). The rate columns are per
1000 penetrations. The pro per-file range: <0.5 mm 0-58, 0.5-1 mm 14-145,
stacked 58-929, short or stacked 117-938.

## 5. Reading it

1. **The bean family is the over-represented source.** `run_outline` and its
   locks emit 24.4% of the short or stacked stitches from 12.6% of the
   penetrations, and none of what it emits is long or fresh. The pitch is a
   measured pro figure (BEAN_STITCH_MM 0.73, "14 found": median 0.73, p90 1.87),
   so the pro sews beans too; but the pro's *entire* chain-short budget is 56 per
   1000 and the edge cap and run tier alone are 110 per 1000 of ours.
2. **Fill is large and near parity.** Its stacking per tatami penetration is
   1.3x (CI 1.03 to 2.06) and its short stitches are the ruled row turn. Do not
   spend a session shortening fill stitches: §6 measures `fill_stitch_mm` 4.0
   and it moves short-or-stacked by 1.0%.
3. **Satin under 1 mm** is the only source that breaks a floor the engine states
   (`MIN_STITCH_MM` 1.0, playbook law 18 "satin >= 1.0 mm", and the preflight's
   own sub-minimum check). Its 7,461 sub-1 mm stitches are 6.8% of all
   penetrations. `SATIN_MIN_CROSS_MM` (0.5) lets a 0.5-1.0 mm column sew as
   satin.
4. **Locks are short by construction and cannot be bought off cheaply.** Both
   ends of every trimmed run are 4 legs of 0.8 mm, returning to the anchor: 7.0%
   of short or stacked, 81-100% of the locks' own penetrations. Lengthening the leg to 1.5 mm removes 460
   short stitches of 7,005 (4 designs) and adds 0.7% thread.

## 6. The worst source: `stage6_border.run_outline`, priced

**What-if method.** Each option re-digitizes four designs (`becker_marine_logo`,
`logo_golden_tee`, `logo_alpha`, `logo_gaulke_roofing`; 25,258 penetrations, 109
trims, 57,133 mm of thread at main `7b88b2f2`) with one thing changed. Config
knobs are used where one exists; otherwise `digitizer_core.machine` is patched in
a scratch script for one run and restored. **Nothing in the engine changed, and
nothing here was sewn.** Percentages are against the same four designs'
baseline.

| option | what it changes | stitches | short or stacked | short / stacked | trims | thread |
|---|---|---|---|---|---|---|
| **A. A longer bean pitch, 1.5 mm** (`BEAN_STITCH_MM` 0.73 to 1.5, law 18's walk floor) | every bean station is twice as far apart; the edge cap's short-or-stacked falls 1,689 to 198 and the run tier's 261 to 109 | **-4.0%** (-1,000) | **-14.1%** (-1,634) | -27.3% / -1.9% | +1 (109 to 110) | -0.02% |
| **B. No edge cap** (`edge_cap="none"`) | the design-silhouette cap is not sewn | -7.4% (-1,861) | -15.9% (-1,843) | -26.3% / -4.9% | **-17 (-15.6%)** | -3.1% |
| **C. Satin cross floor 1.0 mm** (`SATIN_MIN_CROSS_MM` 0.5 to 1.0) | 0.5-1.0 mm columns sew as a bean run, not satin | -3.3% (-830) | -7.2% (-832) | -12.9% / -0.1% | +8 (+7.3%) | -1.4% |
| *not recommended* | | | | | | |
| D. Lock leg 1.5 mm (`TIE_STITCH_MM`) | lock legs twice as long | 0 | -2.0% (-227) | -6.6% / +0.8% | 0 | +0.7% |
| E. Fill stitch 4.0 mm (`fill_stitch_mm`) | longer tatami stitches, same rows | -3.2% (-815) | -1.0% (-120) | 0 / -0.4% | 0 | 0 |

**A is the cheapest fix for the worst source.** It removes the same number of
short stitches as dropping the cap (about 1,900 of 7,005) for 4% fewer stitches
instead of 7.4%, one extra trim instead of 17 fewer, and no thread. *Catches:*
(1) it was run on **both** tiers, because the pitch is a machine constant; the
edge cap tolerates a coarse line (a drawn border at the design's silhouette), but
the run tier sews small *lettering* outlines, where a 1.5 mm chord on a tight
curve is a visible polygon (sagitta 0.09 mm at a 3 mm radius, worse below), so a
shippable version is a **new default-OFF knob that sets the pitch for
`role=edge_cap` only**, about half a session with an OFF-path md5 pin; (2) it
barely touches stacking (-1.9%), because the three passes still return to the
same holes; (3) **ROADMAP gate 1**: 0.73 is a pro-measured median and 1.5 is
law 18's walk floor, so any pitch here is a *candidate* until the sew-out card
runs it, not a setting.

**B is the biggest single lever and the wrong one to pull.** The cap is Kent's
2026-09-11 ruling ("gate it, then flip"), it is what the pro does at an edge,
and it bills +5.9-26.3% stitches there on purpose. Listed because it prices what
the cap costs: 7.4% of stitches, 15.6% of the trims, 3.1% of the thread.

**C addresses a different source.** It cuts satin's short stitches by 904 of
7,005 and adds 8 trims, and it leaves stacking alone. It is the second-priced
fix, and it is also gate 1 (a minimum column width is a physical constant).

**Also tried, no effect:** `satin_hairline_tier` ON and `small_letter_ties` ON
change nothing on these four designs (their paths do not run on them), and are
not priced.

## 7. What this does not say

- **No pro attribution.** The pro's sources are not known, so every pro
  comparison is a rate or a distribution, never a share. The tatami proxy is the
  one source-agnostic bridge and its pro recall is unmeasured.
- **Different designs, sizes and digitizers.** EMB-Bot digitizes at 80 mm; the
  pro's 28 files run 38-89 mm. Several are variants of one artwork, which is why
  the customer CI is quoted. The same-customer table in §2 is the cleaner read.
- **The JS engine is not measured.** Typed lettering is sewn by the browser's
  JS engine only (the prior review cites `machine.py:840-842`); this census
  covers the Python engine's plans, so `src/` lettering columns, `fillColumns`,
  `ties` and `fillStagger` are outside it. A JS port is the open half.
- **Counts are not defects.** A short or stacked stitch is only a break risk if
  it is sewn at speed on that fabric. Whether 0.73 mm beans, 0.8 mm locks or a
  0.15 mm row turn hold on cloth is gate 1 (a sew-out), and nothing here
  settles a constant.
- **Zero-length stitches are rare.** 45 on the EMB-Bot side (identical 0.1 mm
  hole twice running, after the export rounds), 0 on the pro side.

## 8. Reproduce

```
cd digitizer
python -m tools.short_stitch_sources pro --root "<scratch_kent>/Embroidery Files" --exclude "Test Files" --json pro.json
python -m tools.short_stitch_sources corpus --json corpus.json        # ~9 min
python -m tools.short_stitch_sources report corpus.json pro.json
```

The tool is `digitizer/tools/short_stitch_sources.py`, tested by
`digitizer/tests/test_short_stitch_sources.py` (21 tests: the labels are pinned
on hand-built plans, the folded locks and links are pinned, and the counts are
checked against the census it extends). Nothing in `digitizer_core/`,
`digitizer_service/` or the Studio imports it; a test asserts so.
