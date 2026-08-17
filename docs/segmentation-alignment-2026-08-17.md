# What kind of satin/fill straddling caps the oracle at 76.6% — measured

*2026-08-17. Item 7 of `docs/superpowers/plans/2026-08-17-measurement-debt-knockout.md`, following
`docs/satin-gate-attribution-2026-08-16.md` §4's finding that our regions
straddle the pro's satin/fill boundary.*

**Verdict up front: SPECKLE dominates. Of the 4,253 graded cells sitting in a
straddled shape, 4,073 (95.8%) are cell-scale noise — neither a satin border
around a fill core (`ring`, 19 cells, 0.4%) nor a side-by-side partition
(`split`, 161 cells, 3.8%). Region-level surgery — border-satin generation or
region-splitting — can recover at most the `ring`+`split` share: 180 of 8,539
graded cells, 2.1% of the whole population. The draft spec below is written,
per the plan's own instruction for this outcome, as a recommendation NOT to
build it.**

## 1. Population and method

The same 15-design real-artwork corpus the corrected-kappa verdict was
measured on (`docs/satin-gate-attribution-2026-08-16.md` §9): kappa 0.167 →
0.193 after the ribbon promotion, oracle ceiling 76.6% vs 55.4% sewn, and
48.1% of graded cells in shapes under 75% one pro type. This probe answers
the question that number leaves open — *what shape* is that straddling in.

The join is `tools/pro_parity/gateprobe.py`'s own: `scorecard.load_side` both
sides, `register`, `cell_stats` for the pro's 2 mm type map, then
`gateprobe._cells_of` for the centre-in-polygon cells of each of our regions
(`ours_regions.json`). What's new is `tools/pro_parity/splitprobe.py`: it lays
those cells out as a local grid per shape (pro type codes, -1 where a cell is
outside the region or the pro never sewed there) and classifies the layout:

- `ring` — the shape's cell border is decisively (≥80% share) one type and
  its interior decisively the other type. The classic "pro satins the
  outline, fills the body."
- `split` — each type present forms at most 2 connected components: a clean
  side-by-side partition.
- `speckle` — neither: mixed at cell scale, more components than a clean
  partition would produce.
- `pure` — a shape over the attribution doc's own 75% one-type threshold; not
  a straddle at all.

Instrument, not engine code — `classify_straddle` is unit-tested first
(`digitizer/tests/test_splitprobe.py`, 5 cases: ring, split, speckle, pure,
and outside-cell handling) against synthetic grids before it ever touches the
corpus. Full per-shape output: `straddle.csv` (619 rows), disk-canonical in
the measurement worktree, not committed — regenerate with the command in §4.

**One deviation, evidence-based:** the `claude/measurement-debt` worktree was
cut from `d96f9ff`, which predates the ribbon-promotion refactor (`26ceaa3`)
that renamed `is_satin_candidate`'s implementation to `classify_ribbon` —
`gateprobe.py` doesn't exist in that worktree's history at all (the same gap
Task 1's report flagged as a plan bug for its own `kappa-before` pin).
`gateprobe.py` was copied in verbatim from the branch that has it (byte-
identical, `diff` confirmed) since splitprobe needs it as a real sibling
module, not a hand-copied one. Its top-level `from digitizer_core.stage6_satin
import classify_ribbon` still doesn't resolve in this worktree — splitprobe
never calls `classify_ribbon` (only `_cells_of`/`TYPE_NAMES`, unchanged since
before that refactor), so a documented no-op stub on `stage6_satin` satisfies
the import without touching engine code. See `task-5-report.md` for the full
trace.

## 2. The distribution

| pattern | shapes | cells | share of graded cells |
|---|---|---|---|
| `speckle` | 50 | 4,073 | 47.7% |
| `split` | 42 | 161 | 1.9% |
| `ring` | 2 | 19 | 0.2% |
| `pure` | 352 | 4,286 | 50.2% |
| **total graded** | **446** | **8,539** | **100%** |

619 shapes across 15 designs; 446 land on ground the pro also sewed (173 are
on ground the pro left un-sewn — no type to grade against). 49.8% of graded
cells sit in a straddled shape (4,253 of 8,539) — matching the attribution
doc's 48.1% "under 75% one type" figure closely enough to cross-check the
join (different cell-counting nuance: that figure came from `gateprobe.py`'s
own summary, this one from the region-level classification pass over the
same cells).

**Within the straddled population itself**, the split by pattern:

| pattern | cells | share of straddled cells |
|---|---|---|
| `speckle` | 4,073 | 95.8% |
| `split` | 161 | 3.8% |
| `ring` | 19 | 0.4% |

**Per-design**, speckle dominates in 12 of 15 designs (`hotel_fremont_patch`
627 speckle cells vs 12 split vs 8 ring; `mfab_hat` 507 vs 12 vs 0;
`becker_lc_large` 464 vs 6 vs 0). `ring` appears at all in only 2 designs
(`becker_hat_large` 11 cells, `hotel_fremont_patch` 8 cells) — the "pro
satins the outline, fills the body" hypothesis this plan's item 7 set out to
test essentially does not occur on this corpus. `split` is present more
widely (11 of 15 designs) but its shapes are small — 161 cells over 42 shapes
is under 4 cells/shape on average, consistent with boundary-adjacent slivers
rather than genuine two-region partitions. `tires_hat_3d` straddles nothing
at all (233/233 cells pure) — the one design in this corpus where our
segmentation already tracks the pro's.

## 3. The disconfirming check (this is the actionable result)

**Speckle dominates by a wide margin — 95.8% of straddled cells, 47.7% of the
whole graded population, against `ring`+`split` combined at 4.2% of straddled
cells (0.2% of the whole population).** Per this task's own gate: when
speckle dominates, region-level work cannot recover this headroom, and the
draft spec should not be built.

That is the honest reading here. A cell-scale mixed pattern with no dominant
border/interior split and more connected components than a clean partition is
what registration noise and 2 mm cell-grid granularity look like — not what a
systematic "pro drew the boundary somewhere our region doesn't" error looks
like. Two things this rules out as fixable at the region level:

- **Border-satin generation** (the `ring` mechanism) would touch at most 19
  of 8,539 graded cells (0.2%) on this corpus — two shapes, both small.
- **Region splitting at an artwork-visible boundary** (the `split` mechanism)
  would touch at most 161 cells (1.9%) — and those cells sit in shapes
  averaging under 4 graded cells each, too small to confidently localize an
  "artwork-visible boundary" from cell data alone.

Even a perfect implementation of both mechanisms recovers only ~2.1% of the
graded population — nowhere near the 20+ points of headroom the oracle ceiling
implies. The remaining ~48% (speckle) is not a segmentation-boundary problem
this plan's item 7 was framed to find; it reads as registration/cell-grid
noise, which is a different, likely harder, and unscoped problem.

## 4. Reproducing

```powershell
cd digitizer
& C:/Users/EE-LT-11030/Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe -m pytest -q tests/test_splitprobe.py
& C:/Users/EE-LT-11030/Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe tools/pro_parity/splitprobe.py --csv straddle.csv `
  (Get-ChildItem "<kappa-after-worktree>/parity_out/real" -Directory).FullName
```

(measured 2026-08-17 — `splitprobe.py` over the 15-design `kappa-after`
corpus; probe runtime 27.5s for all 15 designs, well under the per-design
"minutes" the task brief anticipated)
