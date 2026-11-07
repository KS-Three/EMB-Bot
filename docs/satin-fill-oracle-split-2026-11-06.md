# Satin/fill: the oracle ground-splitter (C3), 2026-11-06

**Question** (`docs/lagging-areas-2026-11-06/2-satin-fill.md`, section C3): if we cut each
of OUR regions along the pro's minority-type blobs and gave every part the pro's type,
how far would the cell kappa rise? An upper bound on what any layering inference could
buy. **Measurement only**: no engine file, flag or default touched.

**Verdict: no verdict.** Mean oracle-split kappa is **0.482** over 21 jobs, between the
rule's 0.45 and 0.55 *(measured 2026-11-06 — `python -m tools.satin_fill_census oracle-split --runs OFF`)*.
**The answer turns on the blob floor**: 5 cells reads 0.561 (clears 0.55), 20 cells reads
0.427 (clears 0.45 the other way). The task fixed the floor at 10; the decision is Kent's
(question below).

**This oracle reads the pro's blobs, so it is optimistic by construction.** The number is
a maximum, not what inference from flat art could reach.

## Method

Same instrument as the 10-29 re-measure (`satin_fill_census.py`): the cell grid, the
registration, the graded population (`tboth`) and the owner map (a cell belongs to the
SMALLEST sewn region over it) are `cell_census`'s, now shared through `_cell_grids`.
Scored with the same `_kappa_of` (scorecard's chance-corrected sttype). The per-region
oracle is recomputed in the same call and matches `cell_census`'s oracle on all 22 jobs,
tie for tie (checked per job against `census.json`).

For each region: `dom` is the pro's majority type over its graded cells. For each other
pro type, the region's graded cells of that type form 4-connected blobs; a blob of
**>= 10 cells** (2 mm cells, so >= 40 mm²) becomes a part labelled with its type; the rest
of the region keeps `dom`. A region with no such blob is labelled as the per-region
oracle labels it. Cells outside any region keep our own type. Blobs are per type, not
mixed-type components.

Inputs: the OFF arm re-digitized on main `5caccdc8` (the 10-29 runs no longer exist).
Routing is therefore 0.381 here against 0.387 on `44ecf1cb` (main moved);
the per-region oracle reproduces 0.365 exactly.

## Per job

Chance floor beside the routing kappa. All figures chance-corrected (ROADMAP gate 4).
`grounds cut / blobs` and `cut mm²` count the blobs the oracle cut out.
*(measured 2026-11-06 — `python -m tools.satin_fill_census oracle-split --runs OFF`)*

| job | sttype kappa (chance) | per-region oracle | oracle-split (10+) | grounds cut / blobs | cut mm² | pro vs pro 0.5 mm |
|---|---|---|---|---|---|---|
| bridge_hat | 0.14 (0.49) | 0.45 | 0.45 | 0 / 0 | 0 | 0.61 |
| bridge_lc | 0.10 (0.49) | 0.46 | 0.50 | 1 / 1 | 44 | 0.67 |
| becker_hat_large | 0.29 (0.53) | 0.44 | 0.54 | 1 / 4 | 216 | 0.74 |
| becker_lc_large | 0.33 (0.51) | 0.48 | 0.56 | 1 / 3 | 140 | 0.69 |
| becker_hat_small | 0.53 (0.50) | 0.60 | 0.60 | 0 / 0 | 0 | 0.70 |
| becker_chest_small | 0.58 (0.50) | 0.62 | 0.62 | 0 / 0 | 0 | 0.70 |
| becker_beanie | 0.24 (0.56) | 0.12 | 0.26 | 2 / 2 | 132 | 0.62 |
| gaulke_roofing_hat | 0.14 (0.84) | 0.01 | 0.01 | 0 / 0 | 0 | 0.50 |
| gaulke_roofing_lc | 0.29 (0.87) | 0.00 | 0.00 | 0 / 0 | 0 | 0.48 |
| gaulke_roofing_beanie | 0.31 (0.51) | 0.40 | 0.40 | 0 / 0 | 0 | 0.58 |
| hotel_fremont_hat | 0.53 (0.43) | 0.46 | 0.61 | 1 / 2 | 260 | 0.78 |
| hotel_fremont_patch | 0.52 (0.43) | 0.06 | 0.85 | 1 / 5 | 880 | 0.76 |
| mfab_hat | 0.56 (0.48) | 0.56 | 0.72 | 1 / 5 | 288 | 0.69 |
| mfab_lc | 0.57 (0.49) | 0.60 | 0.72 | 1 / 3 | 160 | 0.70 |
| precision_drone | 0.38 (0.50) | 0.34 | 0.43 | 1 / 1 | 56 | 0.69 |
| proseal_hat | 0.17 (0.78) | 0.05 | 0.05 | 0 / 0 | 0 | 0.56 |
| proseal_beanie | 0.39 (0.46) | 0.44 | 0.44 | 0 / 0 | 0 | 0.60 |
| tires_hat_3d | 0.00 (0.51), undefined | - | - | 0 / 0 | 0 | - |
| goldentee_hat | 0.83 (0.62) | 0.82 | 0.82 | 0 / 0 | 0 | 0.76 |
| toat_machine_hat | 0.32 (0.57) | 0.22 | 0.48 | 1 / 5 | 388 | 0.56 |
| toat_machine_beanie | 0.38 (0.58) | 0.27 | 0.55 | 1 / 2 | 360 | 0.63 |
| toat_beanie | 0.40 (0.55) | 0.26 | 0.51 | 2 / 5 | 344 | 0.60 |
| **mean of 21** | **0.381** | **0.365** | **0.482** | 14 / 38 | 3,268 | **0.649** |

`tires_hat_3d` is left out of the means (the pro sews one type; its kappa is undefined).

## The three comparison columns

*(measured 2026-11-06 — `python -m tools.satin_fill_census oracle-split --runs OFF`)*

| | mean kappa, 21 jobs |
|---|---|
| today's routing | 0.381 |
| per-region oracle | 0.365 |
| **oracle-split (10+ cells)** | **0.482** |
| ceiling (pro vs pro, 0.5 mm off) | 0.649 |

- Oracle-split beats routing on 17 of 21 jobs and the plain per-region oracle on 12.
- **Share of the remaining gap removed (kappa-based):** 0.163 of the gap from routing to
  kappa 1; **0.377 of the gap from routing to the ceiling**. The ceiling is the honest
  denominator, since 2 mm cells cap even a perfect engine at 0.649.
- **Cut:** 14 grounds, 38 blobs, 3,268 mm² of blob, inside 18,692 mm² of ground regions
  touched. Nine of 21 jobs have no 10+ blob at all, and in them oracle-split equals the
  per-region oracle.
- Four jobs sit below routing: `gaulke_roofing_hat` and `_lc`, `proseal_hat`, `goldentee_hat`.
  None is cut (the split equals the per-region oracle there), and the per-region oracle is
  already below routing: the Gaulke pair and ProSeal hat have chance floors of 0.84, 0.87
  and 0.78, where one label per region collapses the mix. That is the 10-29 finding again,
  not the split. Goldentee's 0.83 -> 0.82 is within noise.

**The jobs the split lifts are the grounds.** Fremont patch 0.52 -> 0.85 (one ground,
880 mm² of blobs), MFab hat and LC 0.56/0.57 -> 0.72, To a T's three 0.32-0.40 ->
0.48-0.55, Becker large 0.29/0.33 -> 0.54/0.56. The same families of grounds the 10-29 note
named (Fremont's field, To a T's field, MFab's silhouette, Becker's slab).

## Floor sensitivity

*(measured 2026-11-06 — `python -m tools.satin_fill_census oracle-split --runs OFF`; the same run prints all three floors)*

| blob floor | grounds cut | blobs | mean oracle-split kappa | share of gap to ceiling | rule |
|---|---|---|---|---|---|
| 5 cells (>= 20 mm²) | 38 | 104 | 0.561 | 0.672 | worth designing |
| **10 cells (>= 40 mm²), as briefed** | 14 | 38 | **0.482** | 0.377 | no verdict |
| 20 cells (>= 80 mm²) | 5 | 8 | 0.427 | 0.172 | closes the direction |

A lower floor can only raise the number: a smaller blob is easier for the oracle to
read off the pro, and at 5 cells it begins to follow 2 mm grid noise (the pro against
himself 0.5 mm off loses a third of its kappa). So the 5-cell row is the least
trustworthy of the three as a statement about layering, and the 20-cell row the most
conservative. Neither is the briefed floor.

## Decision rule

- `>= 0.55`: a layering-inference stage is worth designing (an extension of
  `silhouette_underfill`, not a splitter).
- `<= 0.45`: the rest of the gap is edge caps and border tiers; close the layering direction.
- **0.482 is between: no verdict.**

What the number does say: even handing the splitter the pro's own blobs, 10+ cells,
buys 0.101 kappa over today's routing, and still leaves 0.167 to the 0.649 ceiling. A real
inference stage would reach less than this maximum. What it does not say is which side of
0.55/0.45 that falls on: the answer lives in the floor, which is a judgement about how small
a piece of another type counts as a layer.

## Question for Kent

The 10-cell floor was fixed in the brief and gives no verdict. Which floor defines "a layer"?

1. **Keep 10 cells (>= 40 mm²)** and treat 0.482 as no verdict (recommended: it is the
   floor the 10-29 note called "not grid noise").
2. **5 cells** reads 0.561 and opens the design, but it is the floor closest to grid noise.
3. **20 cells** reads 0.427 and closes the direction; only 5 grounds are cut.

This PR picks none; the instrument prints all three.

## Rebuild

From `digitizer/`, with `EMB_SCRATCH_KENT` / `EMB_BRIDGE_PRO` set as in `tools/pro_baseline.py`:

```
python -m tools.satin_fill_census digitize --runs OFF
python -m tools.satin_fill_census measure --runs OFF
python -m tools.satin_fill_census oracle-split --runs OFF
```

`oracle-split` itself needs only `measure`'s `census.json` and the per-job
`score/` folders, and runs in seconds. It writes `OFF/oracle_split.json`. No pro render
is written. The unit tests are in `digitizer/tests/test_satin_fill_census.py`.
