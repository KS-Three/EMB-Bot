# Direction kappa: is it a satin-vs-fill axis bug? (2026-11-07)

**No, it is not a convention bug.** The scorer compares a satin and a tatami
on the same axis. The three below-chance rows are real disagreements, and
none of the three histograms peaks within 15 degrees of 90.

Nothing in the engine changed. `score_design` output is byte-identical: all
three `score.json` files and the `--explain` printout match before and after
the refactor (`cmp`). The tripwire ledger does not move, so there is nothing
to re-seed.

## The question

#1321 (`docs/flip-1301-attribution-2026-11-07.md`) found that the unclamped
direction kappa sits well below chance on three tripwire rows:

- toat_beanie: -0.292
- hotel_fremont_hat: -0.38
- mfab_lc: -0.31

It asked whether satin columns and the pro's fills were compared on the same
axis. The worry was that a satin's angle might come from its rails, while a
fill's comes from its rows (or the needle-penetration line). If so, every
satin-vs-fill cell would read 90 degrees off.

## How the scorer reads an angle

`cell_stats` builds both sides the same way. It takes every sewn segment
(needle to needle) and assigns it to the 2 mm cell holding its midpoint. Each
cell's angle is the length-weighted doubled-angle mean of those segments.

- In a satin, a segment is a **cross**, from one rail to the other.
- In a tatami, a segment is a piece of a **row**.

Both are the direction the thread lies on the fabric, so the convention is the
same on both sides. The diff is folded mod pi to [0, 90]
(`folded_angle_diff`, factored out unchanged).

## Synthetic pair (`digitizer/tests/test_scorecard_direction_axis.py`)

- **Pro side:** a 10 x 16 mm rectangle sewn as tatami. Rows run at angle t,
  0.4 mm apart, with stitches of 3.4 mm or less and a brick stagger.
- **Ours side:** the same rectangle sewn as one satin column. Its rails sit
  10 mm apart, so every cross runs at t.
- **Check:** the classifier must read the pro side as fill and ours as satin.
  This guards against the test quietly comparing two fills.

| pro rows | our crosses | shared cells | raw | kappa | histogram (15-deg bins, 0 to 90) |
|---|---|---|---|---|---|
| 0 | 0 | 8 | 1.000 | 1.000 | 8 0 0 0 0 0 |
| 45 | 45 | 11 | 0.997 | 0.994 | 11 0 0 0 0 0 |
| 90 | 90 | 8 | 1.000 | 1.000 | 8 0 0 0 0 0 |
| 0 | 90 (control) | 5 | 0.000 | 0.000 (unclamped -1.000) | 0 0 0 0 0 5 |
| 45 | 135 (control) | 8 | 0.126 | 0.000 (unclamped -0.747) | 1 0 0 0 0 7 |
| 30 | 80 | 8 | 0.443 | 0.000 (unclamped -0.113) | 0 0 0 8 0 0 |

**The agreeing pairs read +1 at every rotation.** A real axis bug would look
like the control rows: kappa 0, with the whole histogram in the 75-90 bin.

There are only a few shared cells for a reason. A satin's angle lands only in
the cells that hold its crosses' midpoints, which form the column's centre
line, so a 10 mm column puts its direction in one strip of cells. That is a
resolution property of the cell statistic, not an axis error.

## The three jobs

**Inputs:** the score directories #1321 measured today on Kent's laptop, at
main d40b2cd3 with shipped defaults ("on" arm). That is the pro DST and ours,
both run through `prep_all.decode`. They were copied to scratch and not
re-digitized: the question is about the scorer, and its inputs are fixed.

**Tool:** `python tools/pro_parity/scorecard.py --direction-hist <dir>` (new).
It uses the same registration, solid mask and cell grid as `score_design`, and
the test checks that its cell count and raw value match `score_design`'s.

| job | cells | 0-15 | 15-30 | 30-45 | 45-60 | **60-75** | 75-90 | median | unclamped kappa | peak within 15 of 90? |
|---|---|---|---|---|---|---|---|---|---|---|
| toat_beanie | 899 | 57 | 56 | 67 | 137 | **440** | 142 | 63.5 | -0.293 | **no** (peak 60-75) |
| hotel_fremont_hat | 754 | 25 | 47 | 66 | 95 | **341** | 180 | 68.7 | -0.378 | **no** (peak 60-75) |
| mfab_lc | 785 | 63 | 75 | 41 | 77 | **359** | 170 | 67.9 | -0.313 | **no** (peak 60-75) |

At 5-degree bins the modes are 60-65 (toat), 70-75 (Fremont) and 65-70 (MFab).
None of them reaches 75.

### Where the disagreement lives

The type pair is (pro, ours), using the scorer's own classifier. The table
counts cells.

| job | fill / fill | of which 60-75 | pro satin / our fill (peak bin) | satin / satin (raw) |
|---|---|---|---|---|
| toat_beanie | 484 | 333 (69%) | 167 (60-75: 54, 75-90: 49) | 167 (0.529, flat) |
| hotel_fremont_hat | 278 | 215 (77%) | 90 (75-90: 48) | 276 (0.422) |
| mfab_lc | 303 | 262 (86%) | 136 (75-90: 60) | 316 (0.469) |

**Fill-vs-fill cells set the number on every job.** In those cells each side
holds one fill angle across the design. Our fill angle sits on an axis, and
the pro's sits about 20 degrees off the other axis. The angles below are
doubled-angle circular means over the fill/fill cells, in the decoded frame
both sides share.

| job | pro fill | ours fill | pro minus ours (mod 180) |
|---|---|---|---|
| toat_beanie | 156.5 | 87.8 | 67.1 |
| hotel_fremont_hat | 71.8 | 0.8 | 70.9 |
| mfab_lc | 20.7 | 89.6 | 111.3 (= -68.7) |

### Ruling out a convention or frame error

**The sign of the gap flips between jobs.** It is +67 and +71 on two jobs and
-69 on the third. A swapped convention would show a constant gap of 90. A
rotation or mirror between the two decoders would show a gap with a fixed
sign, or one that scales with the angle.

**Mirroring ours does not help.** Mirroring our angles in y gives raw 0.369,
0.244 and 0.329, no better than the scored 0.354, 0.311 and 0.344. Both sides
also go through one decoder, `prep_all.decode`.

**What is left is a real difference in fill direction.** Our design angle is
whichever row direction cuts the fills into the fewest columns
(`designangle.py`, rule 3). On a slab that is usually 0 or 90. The pro sews a
slanted tatami about 18-24 degrees off the axis perpendicular to ours.

`designangle.py`'s docstring already records the same gap on Becker Marine.
There our objective picks 90 and the pro sews 18-21, also about 70 degrees
apart. These three rows are that known gap, measured.

The pro-satin / our-fill cells do peak in 75-90. In those cells the pro
crosses a stroke and we sew rows along it. The synthetic pair proves the
scorer reads those as genuinely crossed threads, not a frame error. They are
a minority on every job: 167/899, 90/754 and 136/785.

## Not done

- **No fix and no keyword.** The task asked for a keyword only if this was a
  convention bug, and it is not, so `score_design`'s signature is unchanged.
- **No engine change.** A fill-angle rule nearer the pro's slant would be an
  engine decision with its own ROADMAP gate, not a scorer fix.
- **Satin/satin cells read at chance** (raw 0.42-0.53). That is a separate
  question, not looked into here. One candidate is the midpoint-only
  attribution, where a column's angle sits only on its centre line.
