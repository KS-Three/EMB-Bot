# Eye pairs, 2026-10-03 — the built-OFF flags that had no verdict

Kent's pick on 2026-10-03: one labelled page for every finished flag still
waiting on his eye. Four were asked for — `satin_cap_recentre`,
`satin_patch_junctions="satin"`, `keep_counters`, `bean_letter_max_stroke_mm`
— and `split_off` rides with them, because the page it would replace
(`back-1001`, built 2026-10-01) holds five `split_off` pairs and no verdict.

**Published and judged 2026-10-03** — all 19 pairs, no ruling set; see
"Outcome" at the end. Republished to
`https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp` (version 10) after being
driven in a browser from a local server (19 pairs, five arm heads, five
tables, no console error). The first attempt was refused by the session's
permission classifier as a data-sharing upload and went ahead on Kent's word;
a second refusal was a Read rule on image files outside the session folder,
cleared by publishing from the lane's `digitizer/eye_pairs_out/gallery/`
rather than a temp directory. The store was read before each attempt (140
notes, 3 rulings, newest `pro_file__becker__pro-1001` at 2026-10-01T01:53Z)
and nothing in it was written or moved. The `back-1001` pairs are no longer
on the page; `split_off` is on it under this sitting's tag.

## The base

`main` at `28c893e3` (bean letters #601 and `keep_counters` #602 merged)
**plus `satin_crown_cover` ON** — Kent's flip, commit `63c56ffa`, still local
to its own lane when these were drawn. It is in the base on purpose: the
envelope's ruling was given on pairs drawn without `satin_tip_caps` and had
to be re-read once that shipped. If the crown cover lands changed, or does
not land, these pairs are re-rendered. **It landed the same day as #608, the
same one-file change to `config.py`, so the base these pairs were drawn on is
`main` as shipped.** What it moves on its own: becker
9,662 → 9,715 stitches, enthusiast 2,474 → 2,486.

Eight logos at the Studio's defaults (`REAL_ART` less `screenshot`, less
`thermal` which is drone's artwork byte for byte), tag `off-flags-1003`, the
photo-prep venv linked into the lane so `tires` takes the shipped cutout path.

## What each flag did

| arm | pairs | identical | stitches, all eight | trims | colour changes |
|---|---|---|---|---|---|
| `cap_recentre` | 8 | 0 | 84,475 → 84,460 | 455 → 454 | 32 |
| `bean_letters` (1.0 mm) | 6 | 2 | 84,475 → 84,413 | 455 → 507 | 32 → 33 |
| `split_off` | 5 | 3 | 84,475 → 81,770 | 455 | 32 |
| `keep_counters` | 0 | 8 | 84,475 | 455 | 32 |
| `patch_junctions` | 0 | 8 | 84,475 | 455 | 32 |

Per fixture: `price-tables.json`, the gallery's `--tables` file, shown under
each arm's head. Stitches and trims are counted from the stitch records of
the designs that drew the pairs; colour changes and cones are the rows'
`stops` and `cones`. It is a price list, not a grade — nothing in it says
which side is better.

- **`cap_recentre` is nearly free and nearly invisible.** Every logo's
  design changes, by 0 to 13 stitches. The change locator finds something on
  two: becker (three boxes, all in the MARINE line; zoomed, the first is a
  stem's foot that tapers to a point with a bare notch before and ends
  square after) and tires (one). On the other six it reports *no change
  found after blur*.
- **`bean_letters` is the one a glance can see, and it costs trims.** Six
  logos move, the locator boxes all six, and trims rise 52 across the eight:
  gaulke 33 → 57, drone 138 → 156 with one more colour change, golden_tee
  44 → 52, bridge 97 → 103; fremont falls 57 → 53. becker and tires hold no
  lettering under the line and are identical.
- **`split_off`** moves the five logos it moved on 2026-10-01 and no trim.
  The locator finds nothing after blur on any of them; the needle-holes
  toggle is where it shows, as its own head says.
- **`keep_counters` changes none of the eight** at six colours, which is
  what its own record says (`docs/renders/keep-counters-2026-10-02/`: 25 of
  26 identical at twelve colours, bridge's counters closed in the JPEG). Its
  only picture is that record's synthetic panel. On these logos the flip is
  free and buys nothing.
- **`patch_junctions` was never waiting on anyone.** See below.

## `satin_patch_junctions="satin"` is already the engine

`stage6_satin` hands the junction cover `"satin"` whenever
`satin_junction_stack` is on and nothing else was asked for — part C of the
stack, ON since Kent's flip of 2026-09-19 — so the flag off and the flag on
are one design. `tests/test_junction_patch_flag.py` holds the stack OFF in
its own config for exactly this reason. MASTER_SCOPE "Waiting on Kent" 19
still listed it as a flip call on 2026-09-30.

Measured three ways: identical to the stitch on all eight logos here; with
the crown cover off on BOTH sides, still identical on becker (9,662 both) and
enthusiast (2,474 both); and `tests/test_junction_stack.py` now pins it —
asked for or not, the cover gets the same calls, the same floors, the same
plan. The arm moved from the pending table to the retired one, so this
sitting's rows are still named on the page. An explicit `True` (the tatami
patch) is untouched and still wins over part C.

## How it was built

```
# four lanes by fixture, then one more pass per lane for split_off
python -m tools.eye_pairs --render --out <lane> --fixtures <two logos> \
    --arms cap_recentre,patch_junctions,keep_counters,bean_letters
python -m tools.eye_pairs --render --out <lane> --fixtures <two logos> --arms split_off
python -m tools.eye_pairs.merge <merged> <lane> <lane> <lane> <lane>
python -m tools.eye_pairs_gallery --labelled --src <merged> --out <gallery> \
    --tables ../docs/eye-pairs-2026-10-03/price-tables.json --sitting off-flags-1003
```

48 arm-runs, none failed, 21 identical to shipped and not shown. On Kent's
box beside another session's full digitizer suite a run took 2 to 12.5
minutes (mean 5.7), and the four lanes 84 minutes of wall clock.

*(measured and published 2026-10-03 — Windows, Kent's box)*

## Outcome — Kent's sitting, 2026-10-03 (all 19 judged, no ruling)

Judged in seven minutes, 16:29Z to 16:36Z. Every verdict and note, verbatim:
`kent-notes.json`. He set no per-arm ruling on the page.

| arm | after better | before better | no difference | both bad |
|---|---|---|---|---|
| `bean_letters` | 0 | 5 | 0 | 1 |
| `cap_recentre` | 2 | 0 | 4 | 2 |
| `split_off` | 0 | 0 | 4 | 1 |

- **`bean_letters` at 1.0 reads worse than today's satin, and his word for
  why is weight.** drone, enthusiast, fremont, gaulke and golden_tee
  *before*; bridge *both bad*. His notes: *"very thin and they don't look
  like the actual letters"* (bridge), *"little worms"* (enthusiast), *"to
  skinny and not clean"* (gaulke), *"cleaner in the after, but they aren't
  thick enough"* (fremont), *"inconsistant and not uniform stitch
  patterning"* (drone), *"hard to tell what one is better here"*
  (golden_tee, still *before*). Fremont's note is the useful one: the path
  along the source ink read cleaner, the line on it read too light. The flag
  stays OFF. The session that drew the page had called gaulke's after-side
  "clean line letters" before he looked; his eye said the opposite, which is
  the reason the page takes his verdict and not a description.
- **`cap_recentre`: after on the two logos where it does anything he can
  see, no difference or both bad everywhere else, never before.** becker
  (*"Th "E" and "N" is slightly cleaner on the after"*) and tires (*"The "T"
  is slightly cleaner on the after"*) are exactly the two pairs the change
  locator boxed. It costs 15 stitches fewer and one trim fewer across the
  eight. **He flipped it ON the same day, in chat**, asked with that tally in
  front of him (`kent-notes.json`, rulings).
- **`split_off`: no difference on four, both bad on becker.** As with
  `split_7mm` on the texture sitting, the thread render gives him nothing to
  see; it is a gate-1 question and cloth answers it, not this page.
- **Three logos drew a *both bad*:** bridge (twice), gaulke, becker. No
  flag here is what is wrong with them.

One thing the bean verdict cannot separate *(suspected, not measured)*: the
renderer draws each stitch at one thread's width, so three passes laid along
one path draw as a single line. On cloth a three-pass bean builds up; on the
page it cannot. "Too thin" may be the construction, the picture of it, or
both, and gate 1 already holds a three-pass bean on knit as `pending
sew-out`. Before the letters are rebuilt heavier, find out which.

## After the ruling — the price this page left out, and what it turned out to be

The table under each arm's head priced a flag in stitches, trims and colour
changes. It should have carried the fidelity rows too, and for `cap_recentre`
they were not flat:

| enthusiast, 80 mm | flag off | flag on |
|---|---|---|
| `lost_frac`, as the instrument reads it | 0.2573 | 0.2819 |
| lost elements | 36 | 46 |
| uncovered ink | 1.52% | 1.91% |
| design width | 80.5 mm | 80.3 mm |
| alignment the instrument chose | (0.0, +0.4) | (+0.4, +0.4) |

That took `tests/test_lettering_coverage_regression.py` over its 0.26 bar on
the flip's first CI run (1 failed, 3,153 passed). Kent asked for a spill
guard on the flag. None was built, because nothing spills: the instrument
centres the stitches before it searches alignment on a 0.4 mm grid, the flag
shortens this design by 0.2 mm at its right end, and the search snaps a whole
step. The same two designs, alignment forced instead of searched:

| alignment (physically matched) | flag off | flag on |
|---|---|---|
| where the flag-off design was scored | 0.2573 | 0.2481 |
| best one-pixel alignment | 0.1636 | 0.1555 |
| one pixel from it | 0.1737 | 0.1623 |

The other seven logos keep their width and their alignment and do not move
(becker +0.0001, tires +0.0015 on the grid). Kent's ruling on that: the bar
re-pinned 0.26 → 0.29 with the attribution beside it, the grid recorded as the
instrument's third measurement bias (`tools/dropped_elements.py`), and a
second guard at a one-pixel alignment (reads 0.1555, bar 0.17) with a test
that it still sees this fixture's known spill-maker
(`satin_rails_follow_edge=True`, 0.2173).

*(measured 2026-10-03 — the sitting's kept designs, `analyse_design` with
`register` forced; Windows, and the 0.2819 reproduced on CI's Linux run)*
