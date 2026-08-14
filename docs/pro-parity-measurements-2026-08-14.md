# Pro-parity: measurements for the lane-B merge (2026-08-14)

Every number here was produced in this session, on the full 23-design corpus,
with a freshly re-measured baseline. It is the evidence behind the
recommendation in `pro-parity-program-2026-08-14.md`.

- **Baseline** = `3a1f673` (junction-entry walk + the twig drop).
- **New** = `070a113` (baseline + lane B's corner-fork removal, with the twig
  drop deleted because lane B supersedes it).
- Both trees were run over the SAME reconstructed artwork so only the engine
  differs. Module resolution was confirmed to hit each worktree's own
  `digitizer_core`, not the editable install.

## 1. Scorecard, all 23 designs

The baseline reproduced at 70.92, matching the previously recorded figure
exactly. The merge is **-0.20**.

```
design                     base    new   delta   components that moved (base -> new)
toat_beanie                71.7   69.8   -1.90   stt 0.73->0.69, den 0.69->0.73, und 0.68->0.65, tra 0.82->0.73
precision_drone            63.1   62.3   -0.80   dir 0.51->0.52, stt 0.57->0.55, und 0.74->0.70, tra 0.88->0.86
mfab_hat                   77.0   76.3   -0.70   dir 0.57->0.56, stt 0.77->0.76, und 0.94->0.91
becker_beanie              71.1   70.6   -0.50   dir 0.58->0.58, stt 0.61->0.60, den 0.87->0.85, und 0.61->0.59
becker_hat_small           68.6   68.1   -0.50   dir 0.64->0.63, stt 0.42->0.40, den 0.78->0.81, und 0.85->0.81
becker_chest_small         71.9   71.5   -0.40   stt 0.43->0.41, den 0.77->0.81, und 0.86->0.81
hotel_fremont_patch        57.6   57.2   -0.40   und 0.71->0.68
becker_hat_large           70.1   69.7   -0.40   dir 0.60->0.61, stt 0.56->0.55, den 0.75->0.73, und 0.77->0.76
gaulke_plowing_lc          72.1   71.7   -0.40   cov 0.83->0.82, stt 0.56->0.59, den 0.83->0.82, und 0.69->0.62
becker_lc_large            73.0   72.8   -0.20   stt 0.55->0.56, den 0.78->0.78, und 0.76->0.74, tra 0.84->0.83
machine_beanie             73.5   73.3   -0.20   stt 0.78->0.79, den 0.68->0.66, und 0.68->0.66, tra 0.90->0.90
machine_lc                 80.3   80.1   -0.20   den 0.94->0.93
proseal_beanie             71.6   71.4   -0.20   stt 0.54->0.53, den 0.92->0.93, und 0.57->0.55
gaulke_plowing_hat         70.7   70.6   -0.10   stt 0.63->0.64, den 0.73->0.72, und 0.74->0.70, tra 0.91->0.91
machine_hat                80.3   80.2   -0.10   
gaulke_jb                  65.0   65.0   +0.00   den 0.60->0.58, tra 0.76->0.77
gaulke_roofing_lc          79.8   79.8   +0.00   stt 0.78->0.81, den 0.89->0.88, und 0.75->0.77, tra 1.00->0.97
proseal_hat                77.6   77.6   +0.00   den 0.97->0.95
hotel_fremont_hat          68.1   68.2   +0.10   
tires_hat_3d               53.5   53.7   +0.20   dir 0.51->0.53, stt 0.20->0.19
gaulke_roofing_hat         73.0   73.5   +0.50   dir 0.54->0.54, stt 0.55->0.56, den 0.94->0.94, und 0.70->0.71
mfab_lc                    71.8   72.5   +0.70   dir 0.58->0.57, stt 0.65->0.66, und 0.73->0.82, tra 0.82->0.81
golf_hat                   69.8   70.6   +0.80   den 0.64->0.65, und 0.72->0.77, tra 0.89->0.89

MEAN                      70.92  70.72   -0.20   over 23 designs
```

The movement is concentrated in `und` (underlay economy). That is the cost
lane B predicted: columns that now run out to the artwork edge start their
first stitch with a cross rather than a short underlay run, which is what this
sub-score counts. It is a metric artifact more than a defect — but it is also
not evidence of improvement.

## 2. Bare fabric, all 23 designs — THE DECIDING NUMBER

The scorecard does not measure bare fabric. Coverage is a whole-design IoU, so
a 5 mm² hole inside a covered letter barely moves it. Bare fabric is measured
separately, with the same instrument (`bare.py`) that originally caught the
`hotel_fremont_patch` regression: region area not within 0.2 mm of an emitted
stitch, rasterised at 10 px/mm.

```
design                    bare base  bare new    delta | maxhole b maxhole n   delta
hotel_fremont_patch           26.8      18.8     -8.0 |      5.77      1.71   -4.06
gaulke_jb                     89.3      84.6     -4.7 |     13.39     13.39   +0.00
gaulke_roofing_lc             64.6      60.6     -4.0 |      8.56      8.50   -0.06
proseal_hat                   21.1      18.4     -2.7 |      3.12      2.79   -0.33
golf_hat                      24.6      22.4     -2.2 |      6.99      6.99   +0.00
becker_hat_small              79.7      77.6     -2.1 |     34.22     34.22   +0.00
becker_chest_small            86.9      84.9     -2.0 |     34.61     34.61   +0.00
gaulke_roofing_hat            56.5      55.8     -0.7 |      4.71      4.88   +0.17
hotel_fremont_hat              4.0       3.6     -0.4 |      0.77      0.77   +0.00
machine_lc                     3.2       3.2     +0.0 |      2.55      2.58   +0.03
machine_hat                    3.2       3.3     +0.1 |      2.60      2.63   +0.03
becker_lc_large               65.3      65.5     +0.2 |     19.39     21.30   +1.91
precision_drone               37.7      38.0     +0.3 |      4.42      4.42   +0.00
proseal_beanie                16.9      17.6     +0.7 |      3.90      3.76   -0.14
gaulke_plowing_hat            58.9      60.2     +1.3 |      4.33      4.33   +0.00
becker_beanie                 54.5      55.9     +1.4 |     34.02     34.28   +0.26
mfab_hat                      19.6      21.3     +1.7 |      3.44      3.41   -0.03
tires_hat_3d                  35.5      40.5     +5.0 |     26.31     26.31   +0.00
becker_hat_large              82.0      87.6     +5.6 |     17.44     25.61   +8.17
mfab_lc                       16.0      22.8     +6.8 |      1.72      5.40   +3.68
toat_beanie                   28.6      37.7     +9.1 |     11.71     14.04   +2.33
gaulke_plowing_lc             30.9      53.1    +22.2 |      4.15     13.67   +9.52
machine_beanie                46.8      77.4    +30.6 |     13.41     13.52   +0.11

TOTAL                        952.6    1010.8    +58.2   (+6.1%)  over 23 designs
bare DOWN >0.5mm2 on 8 designs;  bare UP >0.5mm2 on 10 designs
max-hole GREW >0.5mm2 on 5: becker_lc_large 19.4->21.3, becker_hat_large 17.4->25.6, mfab_lc 1.7->5.4, toat_beanie 11.7->14.0, gaulke_plowing_lc 4.2->13.7
max-hole SHRANK >0.5mm2 on 1: hotel_fremont_patch 5.8->1.7
```

**Bare fabric rises 6.1% across the corpus.** `mfab_lc` is not an outlier —
it is a pattern. `machine_beanie` +30.6 mm², `gaulke_plowing_lc` +22.2 mm²
with its largest hole growing 4.2 -> 13.7 mm². Ten designs get worse by more
than 0.5 mm²; eight improve.

This is why the merge is NOT recommended for landing, despite the judge's
scorecard-based recommendation. The judge measured the scorecard and its own
fan metric, both of which lane B improves. Neither instrument sees bare fabric.

## 3. The regression this work set out to fix — CONFIRMED FIXED

`3a1f673` dropped corner twigs on a length bound alone, with no check that
anything covered the corner it vacated. That left a 5.41 mm² hole at design mm
(29.95, 2.39) in the "N" of FREMONT.

An independent healed-blob diff reports **5.43 mm² healed at design mm
(29.95, 2.39)** — the same coordinate, found without being told where to look.

| | total bare | largest hole |
|---|---|---|
| `3a1f673` | 26.8 mm² | 5.77 mm² |
| `070a113` | **18.8 mm²** | **1.71 mm²** |

Verified by eye as well as by metric.

## 4. Ablation: the merge is better than either parent

Neither the lane nor the judge ran this combination, so this is new.

| tree | `hotel_fremont_patch` bare | `mfab_lc` bare |
|---|---|---|
| `3a1f673` (entry walk + twig drop) | 26.8 mm² | **16.0 mm²** |
| lane B alone (fork drop + tuck-under) | 19.9 mm² | 37.2 mm² |
| **`070a113` (both)** | **18.8 mm²** | 22.8 mm² |

Lane B on its own is badly worse on `mfab_lc`. Composing it with the entry
walk repairs most of that (37.2 -> 22.8). The two mechanisms are genuinely
complementary — but the composition still does not get back to baseline.

## 5. Ablation: what actually causes the new `mfab_lc` holes

Run with the fork classifier forced to return nothing (`FORKS_OFF=1` in
`forkprobe.py`), everything else in lane B intact:

| | total bare | largest holes |
|---|---|---|
| forks ON | 22.8 mm² | 5.40, 3.77, 1.72 |
| forks OFF | 18.8 mm² | 5.40, 1.72, 1.32 |

So the **3.77 mm² hole is the fork drop** and vanishes without it, but the
**5.40 mm² hole is not** — it survives with the classifier disabled and
therefore comes from lane B's cap/weld changes, not its headline mechanism.
Anyone retuning `_FORK_NODE_MULT` to chase the larger hole is tuning the
wrong constant.

## 6. Test status — INCOMPLETE

- Targeted: `tests/test_satin.py` + `tests/test_textcluster.py` **71 passed**,
  including all four pinned over-correction fixtures.
- Full suite: **not completed.** The run was stopped part-way. Baseline is 7
  pre-existing failures (5 tesseract-dependent, 2 `enthusiast_logo` platform
  goldens). Lane B reported exactly one new failure,
  `test_chaining_cuts_the_benchmark_fixtures_trim_rate` (4.55 trims/1k against
  a 4.1 ceiling), which the judge independently confirmed. **The merged form's
  full-suite status is unverified.**

## 7. Reproducing any of this

```bash
# per-lane output dir is mandatory — parallel runs clobber a shared one
export PRO_PARITY_OUT=/some/scratch/dir
python digitizer/tools/pro_parity/prep_all.py            # all 23, ~15s each
python digitizer/tools/pro_parity/scorecard.py $PRO_PARITY_OUT/*/

# bare fabric: <digitizer-tree> <corpus-out> <tag> <slug>...
python bare.py ../path/to/digitizer $PRO_PARITY_OUT BASE mfab_lc

# isolate the fork classifier's contribution
FORKS_OFF=1 python forkprobe.py ../path/to/digitizer $PRO_PARITY_OUT mfab_lc

# render a BEFORE/AFTER crop around a hole, at thread width
python holecrop.py <dz_before> <dz_after> $PRO_PARITY_OUT mfab_lc 901 104 tag
```

Caveat carried from the auditor's original setup: `bare.py` runs with
`fill_density_boost=True`, which is gated OFF in shipped config. Baseline and
new are measured identically, so the comparison holds, but the absolute mm²
figures are under that setting rather than shipped defaults.
