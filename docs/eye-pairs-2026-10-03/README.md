# Eye pairs, 2026-10-03 — the built-OFF flags that had no verdict

Kent's pick on 2026-10-03: one labelled page for every finished flag still
waiting on his eye. Four were asked for — `satin_cap_recentre`,
`satin_patch_junctions="satin"`, `keep_counters`, `bean_letter_max_stroke_mm`
— and `split_off` rides with them, because the page it would replace
(`back-1001`, built 2026-10-01) holds five `split_off` pairs and no verdict.

**No verdicts yet.** The page is built and was checked in a browser from a
local server (19 pairs, five arm heads, five tables, no console error). The
republish to `https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp` was refused
by the session's permission classifier and is Kent's to allow; until then the
live page is still `back-1001`. The store was read twice before the attempt
(140 notes, 3 rulings, newest `pro_file__becker__pro-1001` at
2026-10-01T01:53Z) and nothing in it was written or moved.

## The base

`main` at `28c893e3` (bean letters #601 and `keep_counters` #602 merged)
**plus `satin_crown_cover` ON** — Kent's flip, commit `63c56ffa`, still local
to its own lane when these were drawn. It is in the base on purpose: the
envelope's ruling was given on pairs drawn without `satin_tip_caps` and had
to be re-read once that shipped. If the crown cover lands changed, or does
not land, these pairs are re-rendered. What it moves on its own: becker
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

*(measured 2026-10-03 — Windows, Kent's box; the page not yet published)*
