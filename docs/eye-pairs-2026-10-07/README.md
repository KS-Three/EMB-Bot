# Eye pairs, 2026-10-07 — Lettering as Columns (`lettering_columns`), Kent's pairs

The step the lettering lane's memory ends on ("the E/F cut … Then Kent's
pairs", `lettering-architecture-2026-10-07`) and the R&D report's §6 item 1
names ("default-OFF, pairs for Kent"): the outline-cut Column lane beside
shipped, BEFORE left and AFTER right, on every corpus logo, with the price
table under the arm's head. **The flag stays OFF.** Nothing here is a
verdict; the sitting is Kent's.

**Not published by the session that drew it.** The page is built locally
(recipe below, about ten CPU-minutes on four cores) and is gitignored like
every other sitting's gallery.

## The base, and a bug the pairs found first

Engine: PR #660's head (`1782fbea`, slanted terminals + the density
correction) **plus one fix this PR makes**: `outline_cut._spine_ends`
called `skimage`'s `medial_axis` without `rng`, so ties broke from OS
entropy and the Column lane sewed a different design on every run —
golden_tee ON read 8,312 / 8,318 / 8,319 / 8,315 stitches over four runs at
`PYTHONHASHSEED=0`, and two eye-pairs renders of one arm disagreed on
golden_tee and drone. Every other `medial_axis` call in the engine already
passes `rng=0`. With it: three runs, one hash (8,311 stitches, `6cc23d72`).
`tests/test_lettering_columns.py::test_every_engine_medial_axis_call_is_seeded`
pins it on the source (red without the fix, `outline_cut.py:294`). A pair
drawn on an unseeded arm is a sample, not the arm; these were all redrawn
after the fix, and every `base` design came out byte-identical to the
first draw (the fix touches only the lane).

Eight logos at the Studio's defaults (`REAL_ART` less `screenshot`, less
`thermal`, drone's artwork byte for byte), sitting tag `columns-1007`.
This container has no `rembg_isolated/venv`, so tires was prepped without
the cutout on BOTH sides — no confound, but not the shipped tires picture.

## The price (`price-tables.json`, the page's `--tables` file)

Counted from the designs that drew the pairs by `tools/eye_pairs_price.py`
(new: the first sitting whose price table is a committed tool and not a
scratch script, and it carries the fidelity rows the 10-03 table left out).
"Changed shapes" are the shapes whose runs differ between the two designs —
here mostly the letters the lane rebuilt, but a
non-letter shape whose entry point moved with the new order counts too; "their trims" are trims INTO them.

| fixture | stitches | trims | changed shapes | their stitches | their trims | uncovered ink | lost_frac |
|---|---|---|---|---|---|---|---|
| becker | 10,347 → 8,721 | 63 → 29 | 6 | 4,709 → 3,083 | 42 → 8 | 5.80 → 5.84% | 0.0241 → 0.0273 |
| bridge | 18,401 → 18,571 | 97 → 99 | 10 | 586 → 756 | 9 → 11 | 0.16% | 0.2214 → 0.2311 |
| drone | 19,353 → 18,806 | 138 → 141 | 30 | 4,173 → 3,626 | 34 → 37 | 0.33 → 0.40% | 0.0986 → 0.1035 |
| enthusiast | 2,614 → 2,280 | 14 → 15 | 27 | 2,576 → 2,242 | 14 → 15 | 1.84 → 0.53% | 0.2934 → 0.2896 |
| fremont | 20,177 → 20,242 | 57 → 62 | 62 | 4,608 → 4,673 | 18 → 23 | 0.00% | 0.0304 → 0.0325 |
| gaulke | 4,583 → 4,361 | 33 → 26 | 42 | 3,936 → 3,714 | 32 → 25 | 94.74 → 94.72% | 0.9810 → 0.9828 |
| golden_tee | 8,941 → 8,311 | 44 → 43 | 14 | 5,137 → 4,507 | 19 → 18 | 0.17 → 0.28% | 0.4689 → 0.4931 |
| tires | 2,870 | 6 | 0 | — | — | 0.02% | 0.1061 |

Colour changes and cones do not move, except **enthusiast's colour changes
2 → 1** (not investigated; *suspected*, the lane's reordered letters let two
runs of one thread meet). tires is **identical** — no text-tagged shape —
and stays off the page as the gallery's identical rule says.

What the table says, without grading it:

- **MARINE is the lane's case**: letter trims 42 → 8, letter stitches down a
  third (no zigzag underlay, no junction sewn twice).
- **lost_frac rises on six of seven** (largest golden_tee +0.024), and the
  coverage regression test bars enthusiast's at 0.29 — enthusiast moves the
  other way (0.2934 → 0.2896; uncovered ink 1.84 → 0.53%). A flip would have
  to re-read `tests/test_lettering_coverage_regression.py` against these.
- **gaulke's 94.7% uncovered ink is the instrument, not the lane** — the
  same on both sides, the photo file's ink mask; read only its movement.
- Fremont and drone gain letter trims (slab serifs and the diagonal cut into
  more pieces, as recorded on #660).

## Known open on this engine (visible on the page)

The E/F body is still three slabs (the `ext` rule takes the slot's longer
edge into the body) — MARINE's E is the biggest bare patch left. The lane's
memory had the E/F cut before these pairs; they were drawn first on the
caller's word, so expect Kent's becker verdict to name the E. Bowls (band
C/B) still fan.

## How it was built

```
cd digitizer
# four lanes by fixture pair, one process each (4 cores, ~7 min wall)
python -m tools.eye_pairs --render --out <lane> --fixtures becker,tires --arms lettering_columns
#   ... enthusiast,fremont / bridge,golden_tee / gaulke,drone
python -m tools.eye_pairs.merge <merged> <lane> <lane> <lane> <lane>
python -m tools.eye_pairs_price <merged> lettering_columns --out ../docs/eye-pairs-2026-10-07/price-tables.json
python -m tools.eye_pairs --pair --out <merged>
python -m tools.eye_pairs_gallery --labelled --src <merged> --out <gallery> \
    --tables ../docs/eye-pairs-2026-10-07/price-tables.json --sitting columns-1007
```

16 arm-runs, none failed; the labelled page: **7 pairs, 1 identical (tires),
0 failed**. *(measured 2026-10-07 — Linux cloud container, python 3.12)*
