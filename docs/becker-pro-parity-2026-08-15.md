# Becker Marine: EMB-Bot vs. the professional file — 2026-08-15

The first direct measurement of EMB-Bot's auto-digitizing against a
professionally digitized version of the same logo. MASTER_SCOPE has carried
this as a live defect since 2026-08-13 ("auto-digitized `becker logo.png` rates
well below its professionally digitized version"), blocked the whole time on
Kent supplying the files. He delivered them on 2026-08-15 via the asset inbox.

**Everything below is measured from actual stitch coordinates** — the pro files
parsed with `pyembroidery`, ours from `plan.iter_runs()`. Nothing here is
estimated.

## The professional baseline

Five variants shipped, all digitized in Wilcom from the same brand:

| variant | stitches | colours | trims | size (mm) | st/mm² | trims/1k |
|---|---|---|---|---|---|---|
| `becker_chest_small_..._lc_2_a` | 8,694 | 3 | 12 | 76.5 × 46.8 | 2.4 | 1.38 |
| `becker_hat_small_..._hat_2_a` | 8,694 | 4 | 11 | 76.5 × 46.8 | 2.4 | 1.27 |
| `becker_hat_polo_large_..._logolc` | 11,274 | 3 | 12 | 95.7 × 58.3 | 2.0 | 1.06 |
| `becker_hat_polo_large_..._logo_hat` | 12,356 | 4 | 10 | 101.9 × 62.1 | 2.0 | 0.81 |
| `becker_hat_small_..._hat_smaller` | 12,562 | 4 | 11 | 101.9 × 62.1 | 2.0 | 0.88 |

**Every one falls inside 0.81–1.38 trims per 1,000 stitches.** That
independently corroborates the 0.1–4.1 "professional corpus band" that
`test_chaining_cuts_the_benchmark_fixtures_trim_rate` has asserted against
since 2026-08-06 — the band was not invented, and real professional work sits
comfortably in its lower third.

Files live in `digitizer/testdata/reference/`.

## EMB-Bot on the same artwork

`becker_marine_logo.png`, `garment_id="left_chest"`, matched widths:

| | EMB-Bot @76.5mm | Pro @76.5mm | EMB-Bot @101.9mm | Pro @101.9mm |
|---|---|---|---|---|
| stitches | 3,417 | 8,694 | 4,792 | 12,356 |
| separate runs | **129** | **15** | — | — |
| trims | 29 | 11 | 23 | 10 |
| **trims/1k** | **8.49** | 1.27 | **4.80** | 0.81 |
| colours | 1 | 4 | 1 | 4 |

Warnings on both runs: `BACKGROUND_UNCERTAIN`, `BACKGROUND_ENCLOSED` ×7,
`ABSORBED_SMALL_SHAPES` ×1, `EMPTY_THREAD_LAYER`.

## What the gap actually is

### 1. Run fragmentation — the real defect

**129 runs against the professional's 15.** Rendered side by side, our
letterforms are assembled from many short disconnected passes; theirs from a
few long continuous ones. This is the finding worth acting on, because it is
unambiguously worse rather than a matter of taste, and it drives everything
else: 129 fragments is why the trim rate is 8.49/1k when the professional
achieves 1.27/1k on the identical logo at the identical size.

**8.49 is more than double the top of the corpus band** (4.1) that this repo
already treats as the outer limit of acceptable.

### 2. The stitch-count gap is mostly a design decision, not a defect

The professional **filled the banner field and let the letters read as bare
fabric** — negative space. EMB-Bot **filled the letters** and left the banner
empty. Both are defensible readings of the artwork, and it accounts for most of
the 3,417-vs-8,694 difference. Do not treat "39% of the professional's stitch
count" as a quality verdict on its own; it is largely two different designs.

### 3. The colour difference is NOT defect #1

The obvious reading of "1 colour vs 4" is MASTER_SCOPE live defect #1 (every
shade sewing in one colour). **It is not.** The source PNG is genuinely
monochrome — 100% of opaque pixels are `#231F20`, verified pixel-by-pixel — so
one thread is the correct output for this input. The professional used 3–4
because they worked from **richer artwork than the file we were given**.

That is itself worth recording: *we are not being handed the same input the
professional had.* Any future comparison on this logo should establish which
artwork the professional actually worked from before drawing conclusions.

### 4. Source resolution

`becker_marine_logo.png` is **146 × 91 px** — about 46 dpi at 76.5 mm. Every
other logo Kent delivered the same day is 3–17× denser (127 to 794 dpi). If the
professional worked from vector art, part of this gap is input quality rather
than algorithm, and the comparison flatters neither side fairly.

## Reproducing

```bash
cd digitizer
.venv/bin/python - <<'PY'
from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize
r,p = digitize("testdata/becker_marine_logo.png",
               PipelineConfig(target_width_mm=76.5, garment_id="left_chest"))
runs = [list(x.points) for _, x in p.iter_runs() if len(x.points) > 1]
print(p.stats.stitch_count, "stitches |", len(runs), "runs |", p.stats.trims, "trims")
PY
```

`pyembroidery` is needed to read the reference DSTs and is **not** in
`requirements.txt` — install it ad hoc rather than pinning it, since nothing in
the shipped pipeline depends on it.

## What this does not settle

- **No sew-out.** Every number here is geometry, same standing caveat as the
  rest of the project.
- **Which design intent is correct** — banner-fill or letter-fill — is Kent's
  call, not a measurement.
- **Why fragmentation happens.** This documents that 129 runs is wrong; it does
  not diagnose the cause. That is the next piece of work.
