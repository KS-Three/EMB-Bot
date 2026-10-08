# Eye pairs, 2026-10-08: L1, one lettering tagger (`lettering_words`)

Kent picked the pairs on 2026-10-08, when the L1 build closed
(`docs/word-tagger-2026-10-08/README.md`). The page shows the tagger beside
shipped on every corpus logo: BEFORE on the left, AFTER on the right, with
the price table under the arm's head.

- **The flag stays OFF.** Nothing here is a verdict; the sitting is Kent's.
- **Not published by the session that drew it.** The page is built locally
  (recipe below, about ten CPU-minutes on four cores) and is gitignored,
  like every other sitting's gallery.

The engine is PR #675's head with `main` merged in at `e86b7d7` (#666,
`satin_join_square` ON again). It covers eight logos at the Studio's
defaults: `REAL_ART` less `screenshot` and `thermal`. The sitting tag is
`words-1008`. This container has no `rembg_isolated/venv`, so tires was
prepped without the cutout on both sides. That is no confound, but it is
not the shipped tires picture.

## The price (`price-tables.json`, the page's `--tables` file)

Counted by `tools/eye_pairs_price.py` from the designs that drew the pairs.

| fixture | on the page | stitches | trims | changed shapes | their stitches | their trims | uncovered ink | lost_frac |
|---|---|---|---|---|---|---|---|---|
| becker | identical | 10,975 | 60 | 0 | — | — | 6.00% | 0.0250 |
| bridge | pair | 18,487 → 18,475 | 101 | 9 | 565 → 553 | 9 | 0.17% | 0.2207 → 0.2199 |
| drone | pair | 19,345 | 138 → 140 | 9 | 1,069 | 6 → 8 | 0.33 → 0.34% | 0.0986 → 0.0976 |
| enthusiast | pair | 2,612 → 2,602 | 14 | 9 | 1,021 → 1,011 | 6 | 1.85 → 1.94% | 0.2934 → 0.2906 |
| fremont | pair | 20,175 | 57 | 4 | 438 | 1 | 0.00% | 0.0303 |
| gaulke | identical | 4,569 | 33 | 0 | — | — | 94.74% | 0.9811 |
| golden_tee | pair | 8,933 → 8,968 | 44 | 7 | 2,854 → 2,889 | 9 | 0.18 → 0.17% | 0.4466 → 0.4699 |
| tires | identical | 2,864 | 6 | 0 | — | — | 0.01% | 0.1074 |

Colour changes and cones do not move anywhere.

## What the table says, without grading it

- **On today's shipped flags the tagger barely moves the stitches.** The
  pictures are expected to be hard to tell apart.
  - Its measured gain is grouping: gaulke's and the screenshot's two lines
    become two words.
  - It changes no stitch on gaulke, whose letters are enclosed holes and
    unsewn there.
  - Its use is the lanes that read the word next: the Column lane, L2 and L3.
- **drone pays two trims on its changed shapes (6 → 8).**
- **golden_tee is the one fidelity move.** lost_frac rose 0.4466 → 0.4699.
  - What the eye sees: the tee's yellow shaft (left) turns its crosses at
    the top.
  - The shaft is not lettering. Both old taggers already tagged it, as
    text cluster member and house group member. Under the word model it
    lands in a different group, so it takes a different house angle.
  - golden_tee is the one logo the tagger was not scored on, because its
    bevelled letters have no honest labels.
- **enthusiast's uncovered ink rises 1.85 → 1.94% while its lost_frac
  falls.** These are small and opposite; read the picture.
- **What the page cannot show:** the tagger's effect under the Column lane
  (`lettering_columns`), where `is_lettering` reads the word instead of
  either old tagger. That is the combination a flip would actually change.
  It is not an arm here, because the gallery pairs every arm against
  shipped.

## How it was built

```
cd digitizer
# four lanes by fixture pair, one process each (4 cores, ~9 min wall)
python -m tools.eye_pairs --render --out <lane> --fixtures becker,tires --arms lettering_words
#   ... enthusiast,fremont / bridge,golden_tee / gaulke,drone
python -m tools.eye_pairs.merge <merged> <lane> <lane> <lane> <lane>
python -m tools.eye_pairs_price <merged> lettering_words --out ../docs/eye-pairs-2026-10-08/price-tables.json
python -m tools.eye_pairs --pair --out <merged>
python -m tools.eye_pairs_gallery --labelled --src <merged> --out <gallery> \
    --tables ../docs/eye-pairs-2026-10-08/price-tables.json --sitting words-1008
```

**Result:** 16 arm-runs, none failed. The labelled page has 5 pairs; 3 logos
were identical and are not shown. *(measured 2026-10-08, Linux cloud
container, python 3.12)*

## Second sitting: the same flag under the Column lane (`words-columns-1008`)

Kent picked this one after the first sitting, on 2026-10-08. **BEFORE is
not shipped here.** Both sides run `lettering_columns=True`, the Column
lane, built OFF. AFTER adds `lettering_words=True`, so the lane's
`is_lettering` reads the word instead of either old tagger. This is the
combination a flip of L1 would actually change.

Drawn with the new `--base` render option. It lays flags under every arm,
base included, and records them per row as `base_flags`.

**Result:** 3 pairs. Five logos are identical: becker, bridge, fremont,
gaulke and tires.

| fixture | stitches | trims | colour changes | changed shapes | their stitches | their trims | uncovered ink | lost_frac |
|---|---|---|---|---|---|---|---|---|
| drone | 18,806 → 18,866 | 141 → 144 | 9 | 17 | 1,854 → 1,914 | 19 → 22 | 0.40% | 0.1035 → 0.1043 |
| enthusiast | 2,278 → 2,431 | 15 → 14 | 1 → 2 | 4 | 640 → 793 | 4 → 3 | 0.53 → 0.52% | 0.2896 → 0.3090 |
| golden_tee | 8,311 → 8,380 | 43 | 9 | 4 | 1,237 → 1,306 | 7 | 0.28 → 0.20% | 0.4931 → 0.4690 |

What the pictures show, without grading them:

- **enthusiast: the shield's star.**
  - Before, the house group called the star a letter, so the Column lane
    cut it into crossed slabs.
  - After, the word model does not call it lettering (it is another ink),
    so it sews as a filled star.
  - lost_frac rises 0.2896 → 0.3090 and the colour changes go 1 → 2.
    `tests/test_lettering_coverage_regression.py` bars enthusiast near
    0.29, so a flip would have to re-read that test against this picture.
- **drone: the word model's extra letters go into the lane.**
  - THERMAL's M, A and L, which both old taggers missed, now go to the
    Column lane.
  - The sight's two arcs, a text-cluster false positive, leave it.
  - Cost: 3 more trims on the changed shapes.
- **golden_tee:** small changes in the G and in GOLF's shading. lost_frac
  falls 0.4931 → 0.4690.
- **Fremont is identical.** The rope twists the house group tagged never
  reached the lane's construction.

Recipe: as above, with `--base lettering_columns=true` on every
`--render`, a fresh `--out`, `columns/price-tables.json` as the tables, and
`--sitting words-columns-1008`. The price table's caption on the page says
the BEFORE is not shipped.
