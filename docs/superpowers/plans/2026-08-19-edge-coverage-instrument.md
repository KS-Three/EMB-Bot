# Edge Coverage Instrument Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `edgeband.py`, a probe that measures how much of the band just inside a shape's boundary carries no thread — on our output and on a professional digitiser's, through one code path — so that "the shape isn't filled to its edge" becomes a number instead of an impression.

**Architecture:** A standalone probe in `digitizer/tools/pro_parity/`, built on the existing `artfidelity` / `enginefidelity` raster frame (10 px/mm, 0.40 mm thread ribbon, translation-only alignment). It reads the artifacts a `prep_both.py` run already writes and emits a CSV. It imports the shipped mask readers rather than rasterising thread itself, adds no key to the scorecard's `WEIGHTS`, and changes no engine behaviour.

**Tech Stack:** Python 3.14, numpy, OpenCV (`cv2`), `scipy.ndimage.distance_transform_edt`, shapely, pytest. Already present in the digitizer's environment.

**Spec:** [`docs/superpowers/specs/2026-08-19-edge-coverage-instrument-design.md`](../specs/2026-08-19-edge-coverage-instrument-design.md) — read it first; this plan argues from it.

## Global Constraints

- **Phase A (Tasks 1-5) is cloud-safe. Phase B (Task 6) is local-only.** The real lane's source artwork lives on `G:/My Drive/EMB-Bot/Embroidery Files` and is absent from the tracked zip — verified file by file, all seven logos, 2026-08-19. Every Phase A test runs on synthetic fixtures with no corpus and no Drive.
- **Never modify `artfidelity.py` or `enginefidelity.py`.** Their constants are pinned to published numbers (`artfidelity.py:32-57` records a reverted attempt in detail). Import from them; do not touch them.
- **One rasteriser, not two.** Both sides' thread masks come from `artfidelity.pro_mask`. This is the exact defect fixed in `5328257`, where `prep_both` hand-rolled a second copy of a block and silently dropped three keys.
- **No scorecard change.** No new `WEIGHTS` key, no `score.json` field. Adding a scored component rebalances every historical score (`scorecard.py:34-40`).
- **No engine change, no flag flipped, no constant moved.** Not `border`, not `directional_comp`, not `FILL_ROW_MM`, not `BORDER_SEAM_OFFSET_MM`.
- **Band widths are `(0.2, 0.4, 0.8)` mm, all reported, never one chosen.** Choosing one invents a physical constant; ROADMAP gate 1 says cloth settles those.
- **Resolution is `artfidelity.RES = 10.0` px/mm**, so one pixel is 0.1 mm. Band widths are 2, 4 and 8 px.
- **Run tests from the `digitizer/` directory of whatever checkout you are in**, with a Python carrying the digitizer's dependencies:
  ```bash
  cd digitizer && python -m pytest -q tests/test_edgeband.py
  ```
  In a cloud session that is the environment's own interpreter. On Kent's machine a worktree has **no `.venv`** — venvs are not tracked — so use the primary checkout's `digitizer/.venv/Scripts/python.exe` while `cd`'d into the worktree's `digitizer/`. That is safe: cwd precedence puts the worktree's `digitizer_core` ahead of the editable install, verified 2026-08-19. It is also exactly why the rule is always `python -m pytest` and never `python foo.py`.
  **Never pipe pytest to `tail`** — you get tail's exit code, so a red run reads green.
- **Baseline to preserve:** 3 failed / 1187 passed, the known Windows golden divergence (`test_flat_lane_byte_identical[enthusiast_logo]`, `test_pushcomp[logo_whitebg-towel]`, `test_stage2_photo_segment[enthusiast_logo]`). No other test may change result.

---

## File Structure

| File | Responsibility |
|---|---|
| `digitizer/tools/pro_parity/edgeband.py` | **Create.** The whole probe: band geometry, bare arcs, one mask reader, per-design rows, CLI. |
| `digitizer/tests/test_edgeband.py` | **Create.** Calibration against synthetic ground truth, plus wiring tests on a fake design dir. |
| `docs/edge-coverage-2026-08-19.md` | **Create in Task 6 only.** The measured corpus table. |

One module, because the pieces are one instrument and are read together. It stays well under the size of its neighbours (`scorecard.py` is 968 lines).

---

## Task 1: Band geometry and bare fraction

**Files:**
- Create: `digitizer/tools/pro_parity/edgeband.py`
- Create: `digitizer/tests/test_edgeband.py`

**Interfaces:**
- Consumes: `artfidelity.RES` (10.0 px/mm).
- Produces: `BAND_WIDTHS_MM: tuple[float, ...]`; `band_mask(shape: np.ndarray, w_px: float) -> np.ndarray` (bool); `bare_frac(band: np.ndarray, thread: np.ndarray) -> float | None`.

- [ ] **Step 1: Write the failing test**

```python
"""Calibration and wiring for the edge-coverage probe (tools/pro_parity/edgeband.py).

Every number this instrument reports is a millimetre nobody can check by eye, so
each primitive is measured against a synthetic shape whose answer is known by
construction before it is ever pointed at real work. The repo already carries one
edge-coverage figure with no instrument behind it — "starvation 0.00 mm with zero
variance on 13 real letterforms", config.py:685, which appears exactly once in the
repository and nowhere else. That is what this file exists to prevent.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / "edgeband.py"
spec = importlib.util.spec_from_file_location("pro_parity_edgeband", TOOL)
eb = importlib.util.module_from_spec(spec)
sys.modules["pro_parity_edgeband"] = eb
spec.loader.exec_module(eb)


def square(h, w, y0, x0, sh, sw):
    """A solid rectangle `sh` x `sw` at (y0, x0) on an h x w bool canvas."""
    m = np.zeros((h, w), bool)
    m[y0:y0 + sh, x0:x0 + sw] = True
    return m


def test_band_is_the_ring_within_w_px_of_the_boundary():
    """A 100x100 px square banded at 4 px keeps a 92x92 core.

    Counted, not eyeballed: the band is every pixel whose exact Euclidean
    distance to outside the shape is <= 4 px, which for a rectangle is the
    4-pixel frame — 100*100 - 92*92 = 1536 pixels.
    """
    sh = square(140, 140, 20, 20, 100, 100)
    band = eb.band_mask(sh, 4.0)
    assert band.dtype == bool
    assert np.count_nonzero(band) == 100 * 100 - 92 * 92
    assert not (band & ~sh).any(), "band must never leave the shape"


def test_band_of_an_empty_shape_is_empty_not_an_error():
    assert not eb.band_mask(np.zeros((10, 10), bool), 4.0).any()


def test_bare_frac_counts_only_band_pixels_with_no_thread():
    """Thread covering the left half of a square leaves exactly half its band bare."""
    sh = square(140, 140, 20, 20, 100, 100)
    thread = np.zeros((140, 140), bool)
    thread[:, :70] = True          # covers x in [20, 70) of the shape
    band = eb.band_mask(sh, 4.0)
    got = eb.bare_frac(band, thread)
    expect = np.count_nonzero(band & ~thread) / np.count_nonzero(band)
    assert got == pytest.approx(expect)
    assert 0.4 < got < 0.6, f"half-covered square should be near half bare, got {got}"


def test_bare_frac_of_an_empty_band_is_none_not_zero():
    """None means 'not measured'. Zero would read as 'perfectly covered'."""
    assert eb.bare_frac(np.zeros((10, 10), bool), np.zeros((10, 10), bool)) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd .claude/worktrees/edge-coverage/digitizer && python -m pytest -q tests/test_edgeband.py
```
Expected: collection error — `edgeband.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `digitizer/tools/pro_parity/edgeband.py`:

```python
"""Edge coverage — how much of the band just inside a boundary carries no thread.

THE QUESTION. Along a shape's boundary, how much of the band just inside it has
no thread on it, and how does that compare to what a professional digitiser
leaves on the same artwork? Two numbers: the bare FRACTION of the band, and the
longest contiguous bare ARC along the boundary.

WHY THE ARC IS THE HEADLINE. Five percent of a band left bare as scattered
pinpricks is invisible; five percent as one 8 mm strip down the side of a letter
is the defect. `barecircle.py` makes exactly this argument for shape interiors
(:14-16) and then declines to make it for edges — its `clearance` is
`min(dist_out, dist_thread - w/2)` (:133-137), which caps any point's score at
its own distance from the boundary, so a continuous uncovered perimeter band is
indistinguishable from flawless work. This module answers the case that one
discounts. Nothing here supersedes it; they measure different failures.

WHY BOTH SIDES GO THROUGH ONE READER. `side_mask` delegates to
`artfidelity.pro_mask` for pro and ours alike. `prep_both.py` once hand-rolled a
second copy of a shared block and silently dropped three keys from it for weeks
(fixed 2026-08-18, 5328257); one rasteriser is how that does not happen here.

WHAT THIS DOES NOT DO. It sets no threshold. "How much bare edge is too much" is
a cloth question and ROADMAP gate 1 says cloth settles it, so the probe reports
millimetres at three band widths and lets the professional's own files be the
tolerance. It adds no key to the scorecard's WEIGHTS and changes no engine
behaviour.
"""
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artfidelity import RES  # noqa: E402

# Reported at all three, never one. Picking one would invent a physical
# constant; gate 1 says cloth settles those. Three widths also separate a thin
# uniform shortfall (visible at 0.2, washed out at 0.8) from a genuinely wide
# gap. At RES = 10 px/mm these are 2, 4 and 8 pixels.
BAND_WIDTHS_MM = (0.2, 0.4, 0.8)


def band_mask(shape: np.ndarray, w_px: float) -> np.ndarray:
    """Every pixel of `shape` within `w_px` of being outside it.

    Exact Euclidean, not a morphological erosion: a square structuring element
    measures Chebyshev distance, so a 4 px band would reach 5.7 px into a
    corner. `barecircle.py` uses the same EDT convention for the same reason.
    """
    if not shape.any():
        return np.zeros(shape.shape, bool)
    return shape & (distance_transform_edt(shape) <= w_px)


def bare_frac(band: np.ndarray, thread: np.ndarray) -> float | None:
    """Share of `band` with no thread on it, or None for an empty band.

    None rather than 0.0 deliberately: an empty band is a shape too small to
    measure, and 0.0 would read as "perfectly covered" in every table it
    reaches.
    """
    n = int(np.count_nonzero(band))
    if not n:
        return None
    return float(np.count_nonzero(band & ~thread) / n)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd .claude/worktrees/edge-coverage/digitizer && python -m pytest -q tests/test_edgeband.py
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/edgeband.py digitizer/tests/test_edgeband.py
git commit -m "feat(measure): band geometry for edge coverage, calibrated on a counted square"
```

---

## Task 2: Bare arcs along the boundary

**Files:**
- Modify: `digitizer/tools/pro_parity/edgeband.py`
- Modify: `digitizer/tests/test_edgeband.py`

**Interfaces:**
- Consumes: `band_mask` from Task 1.
- Produces: `bare_arcs(shape: np.ndarray, thread: np.ndarray, w_px: float, res: float = RES) -> list[float]` — lengths in mm, unsorted.

- [ ] **Step 1: Write the failing test**

Append to `digitizer/tests/test_edgeband.py`:

```python
def test_bare_arc_measures_a_strip_of_known_length():
    """THE calibration test. A 100 px square covered everywhere except a 30 px
    run of its bottom edge must report an arc of 30 px = 3.0 mm, within one
    pixel. An instrument never shown a known answer is how this repo acquired a
    0.00 mm figure with nothing behind it."""
    sh = square(140, 140, 20, 20, 100, 100)
    thread = sh.copy()
    thread[110:120, 40:70] = False      # 30 px of the bottom edge, 10 px deep
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert arcs, "a 30 px bare strip must produce an arc"
    assert max(arcs) == pytest.approx(3.0, abs=0.1), f"got {sorted(arcs)}"


def test_fully_covered_shape_reports_no_arcs():
    sh = square(140, 140, 20, 20, 100, 100)
    assert eb.bare_arcs(sh, sh, 4.0) == []


def test_shape_with_no_thread_at_all_reports_its_whole_perimeter():
    """Perimeter of a 100 px square is 400 px = 40 mm. The contour walks pixel
    centres, so it traces a 99 px square: 396 px = 39.6 mm."""
    sh = square(140, 140, 20, 20, 100, 100)
    arcs = eb.bare_arcs(sh, np.zeros((140, 140), bool), 4.0)
    assert max(arcs) == pytest.approx(39.6, abs=0.2), f"got {sorted(arcs)}"


def test_an_arc_wraps_the_start_of_a_ring():
    """A bare run straddling the contour's own index 0 is ONE arc, not two.
    Rings close; an implementation that forgets it halves its worst finding."""
    sh = square(140, 140, 20, 20, 100, 100)
    thread = sh.copy()
    thread[20:30, 20:60] = False        # top edge, spanning the top-left corner
    thread[20:60, 20:30] = False        # left edge, same corner
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert max(arcs) > 6.0, f"corner-spanning run must not be split: {sorted(arcs)}"


def test_holes_are_walked_as_well_as_the_outline():
    """A ring's inner boundary is an edge like any other."""
    sh = square(140, 140, 20, 20, 100, 100)
    sh[55:85, 55:85] = False           # a 30 px square hole
    thread = sh.copy()
    thread[50:90, 50:90] = False       # strip thread from all around the hole
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert arcs, "the hole's own boundary must be measured"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd .claude/worktrees/edge-coverage/digitizer && python -m pytest -q tests/test_edgeband.py
```
Expected: 5 failures, `AttributeError: module has no attribute 'bare_arcs'`.

- [ ] **Step 3: Write minimal implementation**

Append to `edgeband.py`:

```python
def _rings(shape: np.ndarray) -> list[np.ndarray]:
    """Every boundary ring of `shape` as an (N, 2) array of (row, col).

    `CHAIN_APPROX_NONE` because an arc length is a walk along real pixels — the
    simplified chain would drop the very pixels being measured. `RETR_CCOMP`
    returns holes as their own rings, and a hole's boundary is an edge like any
    other.
    """
    cs, _h = cv2.findContours(shape.astype(np.uint8), cv2.RETR_CCOMP,
                              cv2.CHAIN_APPROX_NONE)
    return [c.reshape(-1, 2)[:, ::-1] for c in cs if len(c) >= 2]


def _runs(flags: np.ndarray) -> list[list[int]]:
    """Maximal runs of True in a CLOSED sequence, as index lists.

    Rings close, so a run straddling index 0 is one run. Rotating the sequence
    to start at a False is what makes that fall out for free; an all-True ring
    has no False to rotate to and is returned whole.
    """
    n = len(flags)
    if not flags.any():
        return []
    if flags.all():
        return [list(range(n))]
    start = int(np.argmax(~flags))
    out, cur = [], []
    for k in range(n):
        i = (start + k) % n
        if flags[i]:
            cur.append(i)
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def bare_arcs(shape: np.ndarray, thread: np.ndarray, w_px: float,
              res: float = RES) -> list[float]:
    """Lengths in mm of every maximal boundary run further than `w_px` from thread.

    A boundary pixel is bare when the nearest thread pixel is more than `w_px`
    away. Distance rather than an inward-normal probe: a normal is ambiguous at
    a corner and wherever a ring doubles back, and two implementations would
    disagree there. An exact EDT has no such freedom.

    A run's length is the distance walked BETWEEN its pixels, so a lone bare
    pixel measures 0.0 and a 30 px strip measures 29 steps of 0.1 mm. That is
    the span a strip of that length actually occupies; counting the step off its
    final pixel would add a pixel of length that is not there.
    """
    if not shape.any():
        return []
    dist = (distance_transform_edt(~thread) if thread.any()
            else np.full(shape.shape, np.inf))
    out: list[float] = []
    for ring in _rings(shape):
        bare = dist[ring[:, 0], ring[:, 1]] > w_px
        if not bare.any():
            continue
        step = np.hypot(*(np.roll(ring, -1, axis=0) - ring).T) / res
        for run in _runs(bare):
            out.append(float(step[run[:-1]].sum()) if len(run) > 1 else 0.0)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd .claude/worktrees/edge-coverage/digitizer && python -m pytest -q tests/test_edgeband.py
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/edgeband.py digitizer/tests/test_edgeband.py
git commit -m "feat(measure): the longest contiguous bare arc, wrapped and calibrated"
```

---

## Task 3: One mask reader for both sides

**Files:**
- Modify: `digitizer/tools/pro_parity/edgeband.py`
- Modify: `digitizer/tests/test_edgeband.py`

**Interfaces:**
- Consumes: `artfidelity.pro_mask`.
- Produces: `side_mask(csv_path) -> np.ndarray` (bool).

- [ ] **Step 1: Write the failing test**

Append to `digitizer/tests/test_edgeband.py`:

```python
def write_stitches(path, pts, breaks=None):
    """A minimal `*_stitches.csv` in the harness's own column vocabulary."""
    breaks = breaks or [False] * len(pts)
    with open(path, "w", newline="") as f:
        f.write("x_mm,y_mm,trim,jump\n")
        for (x, y), b in zip(pts, breaks):
            f.write(f"{x},{y},{1 if b else 0},0\n")


def test_both_sides_read_through_one_rasteriser():
    """Mutation guard. `prep_both.py` hand-rolled a second copy of a shared
    block and silently dropped three keys from it for weeks (fixed 5328257).
    Re-hand-rolling a reader here — any different thread width, any different
    padding — fails this."""
    import artfidelity
    tmp = Path(__import__("tempfile").mkdtemp())
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    write_stitches(tmp / "s.csv", pts)
    assert np.array_equal(eb.side_mask(tmp / "s.csv"),
                          artfidelity.pro_mask(tmp / "s.csv"))


def test_side_mask_returns_bool():
    """`boundary_distance_mm` documents what a uint8 mask costs: 6553.6 mm
    returned as a plausible number, past every guard, with no exception
    (enginefidelity.py:96-105). Same trap, same guard."""
    tmp = Path(__import__("tempfile").mkdtemp())
    write_stitches(tmp / "s.csv", [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0)])
    assert eb.side_mask(tmp / "s.csv").dtype == bool
```

- [ ] **Step 2: Run tests to verify they fail**

Run the same pytest command. Expected: 2 failures, `AttributeError: ... 'side_mask'`.

- [ ] **Step 3: Write minimal implementation**

Append to `edgeband.py` (and extend the existing import line to `from artfidelity import RES, pro_mask`):

```python
def side_mask(csv_path) -> np.ndarray:
    """The thread raster for EITHER side. One reader, deliberately.

    `enginefidelity.engine_mask` is already `artfidelity.pro_mask` — the
    trim/jump semantics are identical on both sides — so naming it once here
    keeps a second copy from appearing. Sibling probes (bare.py, holecrop.py,
    forkprobe.py) all paint at THREAD_W_MM = 0.40; changing that constant
    anywhere means changing it in step or the directory stops agreeing about
    what "covered" means (artfidelity.py:55-57).
    """
    return pro_mask(csv_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/edgeband.py digitizer/tests/test_edgeband.py
git commit -m "feat(measure): one thread rasteriser for both sides, mutation-guarded"
```

---

## Task 4: The artwork band, both sides, one design

**Files:**
- Modify: `digitizer/tools/pro_parity/edgeband.py`
- Modify: `digitizer/tests/test_edgeband.py`

**Interfaces:**
- Consumes: `side_mask`, `band_mask`, `bare_frac`, `bare_arcs`.
- Produces: `art_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]`, each dict having keys `slug, band, side, width_mm, bare_frac, bare_arc_max_mm, bare_arc_p90_mm, band_mm2`.

- [ ] **Step 1: Write the failing test**

Append to `digitizer/tests/test_edgeband.py`:

```python
def fake_design(tmp, cover_ours=True):
    """A design dir: a 20x12 mm ink rectangle, a pro that covers it in rows, and
    an ours that either matches or stops 1.0 mm short of the bottom edge."""
    from PIL import Image
    d = Path(tmp); d.mkdir(parents=True, exist_ok=True)
    ink = np.full((120, 200, 3), 255, np.uint8)
    ink[10:110, 10:190] = 0            # 18 x 10 mm of ink at 10 px/mm
    Image.fromarray(ink).save(d / "art.png")

    def rows(y_end):
        pts, y, k = [], 1.0, 0
        while y <= y_end:
            pts += [(1.0, y), (18.0, y)] if k % 2 == 0 else [(18.0, y), (1.0, y)]
            y += 0.4; k += 1
        return pts

    write_stitches(d / "pro_stitches.csv", rows(10.6))
    write_stitches(d / "ours_stitches.csv", rows(10.6 if cover_ours else 9.6))
    return d


def test_art_band_rows_cover_both_sides_and_all_widths():
    tmp = Path(__import__("tempfile").mkdtemp()) / "becker_fake"
    rows = eb.art_band_rows(fake_design(tmp))
    assert {r["side"] for r in rows} == {"pro", "ours"}
    assert {r["width_mm"] for r in rows} == set(eb.BAND_WIDTHS_MM)
    assert all(r["band"] == "art" for r in rows)
    assert all(r["slug"] == "becker_fake" for r in rows)
    assert len(rows) == 2 * len(eb.BAND_WIDTHS_MM)


def test_a_short_last_row_shows_up_as_a_longer_bare_arc_than_the_pro():
    """The whole point of the instrument, on a case built to have one answer:
    ours stops 1.0 mm short along an 18 mm edge, the pro does not."""
    tmp = Path(__import__("tempfile").mkdtemp()) / "short"
    rows = eb.art_band_rows(fake_design(tmp, cover_ours=False))
    at = {(r["side"], r["width_mm"]): r for r in rows}
    ours = at[("ours", 0.4)]["bare_arc_max_mm"]
    pro = at[("pro", 0.4)]["bare_arc_max_mm"]
    assert ours > pro + 5.0, f"ours {ours:.2f} mm vs pro {pro:.2f} mm"


def test_a_design_dir_missing_a_side_yields_no_rows_for_it():
    tmp = Path(__import__("tempfile").mkdtemp()) / "onesided"
    d = fake_design(tmp)
    (d / "ours_stitches.csv").unlink()
    assert {r["side"] for r in eb.art_band_rows(d)} == {"pro"}
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: 3 failures, `AttributeError: ... 'art_band_rows'`.

- [ ] **Step 3: Write minimal implementation**

Extend the imports at the top of `edgeband.py`:

```python
from artfidelity import RES, SHIFT_MM, art_mask, best_iou, pro_mask  # noqa: E402
from enginefidelity import MASK_PAD_PX, _place  # noqa: E402
```

Append:

```python
def _summarise(shape, thread, w_mm, res=RES) -> dict:
    """The four numbers, for one band at one width."""
    w_px = w_mm * res
    band = band_mask(shape, w_px)
    arcs = bare_arcs(shape, thread, w_px, res)
    return {
        "width_mm": w_mm,
        "bare_frac": bare_frac(band, thread),
        "bare_arc_max_mm": round(max(arcs), 3) if arcs else 0.0,
        "bare_arc_p90_mm": round(float(np.percentile(arcs, 90)), 3) if arcs else 0.0,
        "band_mm2": round(int(np.count_nonzero(band)) / (res * res), 2),
    }


def art_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]:
    """Edge coverage against the ARTWORK's own boundary, for both sides.

    The artwork is the only boundary neither side authored, which is the whole
    reason it is the headline: measuring against our own polygons would let our
    segmentation decide where "the edge" is — the same circularity that bars the
    recon lane, whose art.png is reconstructed from the pro's own stitches.

    Each side is aligned to the artwork by the shipped `best_iou` shift and
    measured on its own canvas. The art geometry is identical between the two;
    only its placement differs, and placement cannot change an arc length.

    `width_mm` subtracts MASK_PAD_PX because `pro_mask`'s canvas is the stitch
    span PLUS a fixed 8 px margin. Scaling the artwork to the canvas instead
    stretched it 0.8 mm wider than the engine on every design and gave a
    flawless reproduction art_missed 0.042 (enginefidelity.py:50-58).
    """
    d = Path(dirpath)
    art = d / "art.png"
    if not art.exists():
        return []
    rows = []
    for side, name in (("pro", "pro_stitches.csv"), ("ours", "ours_stitches.csv")):
        csv_path = d / name
        if not csv_path.exists():
            continue
        M = side_mask(csv_path)
        A = art_mask(art, (M.shape[1] - MASK_PAD_PX) / RES)
        _iou, _extra, _missed, dx_mm, dy_mm = best_iou(M, A)
        H = max(M.shape[0], A.shape[0]) + int(2 * SHIFT_MM * RES) + 4
        W = max(M.shape[1], A.shape[1]) + int(2 * SHIFT_MM * RES) + 4
        Mp = _place(M, H, W)
        Ap = _place(A, H, W, int(round(dx_mm * RES)), int(round(dy_mm * RES)))
        for w_mm in widths_mm:
            rows.append({"slug": d.name, "band": "art", "side": side,
                         **_summarise(Ap, Mp, w_mm)})
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/edgeband.py digitizer/tests/test_edgeband.py
git commit -m "feat(measure): edge coverage against the artwork boundary, both sides"
```

---

## Task 5: Per-shape attribution, and the CLI

**Files:**
- Modify: `digitizer/tools/pro_parity/edgeband.py`
- Modify: `digitizer/tests/test_edgeband.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `shape_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]` (adds keys `shape_id, tier, area_mm2`, with `band == "shape"`); `main()` writing `edgeband_<slug>.csv`.

- [ ] **Step 1: Write the failing test**

Append to `digitizer/tests/test_edgeband.py`:

```python
def test_shape_rows_carry_the_shape_id_and_tier():
    """Attribution: which shape is short, and in which tier. The polygon is OURS
    on both sides, so this asks whether the pro laid thread where our shape
    claims its edge is — stated in every table that reports it."""
    import json
    tmp = Path(__import__("tempfile").mkdtemp()) / "shaped"
    d = fake_design(tmp, cover_ours=False)
    (d / "ours_regions.json").write_text(json.dumps([{
        "shape_id": "s1", "area_mm2": 180.0, "thread": 0, "tier": "fill",
        "bounds": [1.0, 1.0, 18.0, 10.6],
        "wkt": "POLYGON ((1 1, 18 1, 18 10.6, 1 10.6, 1 1))",
    }]))
    rows = eb.shape_band_rows(d)
    assert rows, "a region with a wkt must produce rows"
    assert {r["shape_id"] for r in rows} == {"s1"}
    assert {r["tier"] for r in rows} == {"fill"}
    assert all(r["band"] == "shape" for r in rows)


def test_no_regions_file_is_not_an_error():
    tmp = Path(__import__("tempfile").mkdtemp()) / "noregions"
    assert eb.shape_band_rows(fake_design(tmp)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: 2 failures, `AttributeError: ... 'shape_band_rows'`.

- [ ] **Step 3: Write minimal implementation**

Append to `edgeband.py`:

```python
def _poly_mask(poly, H, W, oy, ox, res=RES) -> np.ndarray:
    """Rasterise a shapely polygon into a canvas at a known pixel offset.

    `oy`/`ox` are where the side's own raster was placed, so the polygon lands
    in the same frame its own stitches did.
    """
    m = np.zeros((H, W), np.uint8)

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack([a[:, 0] * res + ox, a[:, 1] * res + oy]).astype(np.int32)

    parts = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    for p in parts:
        if p.geom_type != "Polygon":
            continue
        cv2.fillPoly(m, [px(p.exterior.coords)], 255)
        for ring in p.interiors:
            cv2.fillPoly(m, [px(ring.coords)], 0)
    return m.astype(bool)


def shape_band_rows(dirpath, widths_mm=BAND_WIDTHS_MM) -> list[dict]:
    """Edge coverage per OUR shape — the attribution number.

    Which shapes are short, and in which tier. The polygon is ours on BOTH
    sides, so this asks whether the pro laid thread where our shape claims its
    edge is. Where this and `art_band_rows` disagree IS the segmentation-shrink
    signal: our polygon landing inside the artwork's ink is invisible to any
    measure that uses our polygon as ground truth.

    Only our own side is measured here. Placing our polygons on the PRO's canvas
    needs a second registration path, and mixing `best_iou`'s whole-pixel shift
    with `scorecard.register`'s hill-climb is how two probes start disagreeing
    about where a shape is. The pro's side of the comparison is `art_band_rows`.
    """
    import shapely.wkt

    d = Path(dirpath)
    regions_path = d / "ours_regions.json"
    csv_path = d / "ours_stitches.csv"
    if not (regions_path.exists() and csv_path.exists()):
        return []
    regions = json.loads(regions_path.read_text())
    if not regions or "wkt" not in regions[0]:
        return []

    M = side_mask(csv_path)
    x0, y0 = _origin_mm(csv_path)
    H = M.shape[0] + 8
    W = M.shape[1] + 8
    Mp = _place(M, H, W)
    # `_place` centres; `pro_mask` itself pads 4 px inside its own raster.
    oy = (H - M.shape[0]) // 2 + 4 - y0 * RES
    ox = (W - M.shape[1]) // 2 + 4 - x0 * RES

    rows = []
    for r in regions:
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        P = _poly_mask(poly, H, W, oy, ox)
        if not P.any():
            continue
        for w_mm in widths_mm:
            rows.append({"slug": d.name, "band": "shape", "side": "ours",
                         "shape_id": r.get("shape_id"), "tier": r.get("tier"),
                         "area_mm2": r.get("area_mm2"),
                         **_summarise(P, Mp, w_mm)})
    return rows


def _origin_mm(csv_path) -> tuple[float, float]:
    """The mm corner `pro_mask` measures its raster from.

    Two mins, duplicated from `pro_mask` because it returns only the mask —
    its docstring says "plus its mm origin" and the code does not. Guarded by
    `test_origin_agrees_with_the_rasteriser`, which pins a known stitch to a
    known pixel, so a change to the rasteriser's framing cannot drift this
    silently.
    """
    xs, ys = [], []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            xs.append(float(r["x_mm"])); ys.append(float(r["y_mm"]))
    return min(xs), min(ys)


def main():
    out_rows = []
    for arg in sys.argv[1:]:
        d = Path(arg)
        rows = art_band_rows(d) + shape_band_rows(d)
        if not rows:
            print(f"{d.name:22s} (no artifacts)", flush=True)
            continue
        out_rows += rows
        art = {(r["side"], r["width_mm"]): r for r in rows if r["band"] == "art"}
        for w in BAND_WIDTHS_MM:
            p = art.get(("pro", w)); o = art.get(("ours", w))
            if p and o:
                print(f"{d.name:22s} W={w:.1f}  pro arc {p['bare_arc_max_mm']:6.2f} mm"
                      f" · ours arc {o['bare_arc_max_mm']:6.2f} mm"
                      f" · pro frac {p['bare_frac']:.3f} · ours frac {o['bare_frac']:.3f}",
                      flush=True)
        with open(d / f"edgeband_{d.name}.csv", "w", newline="") as f:
            keys = sorted({k for r in rows for k in r})
            w_ = csv.DictWriter(f, fieldnames=keys); w_.writeheader(); w_.writerows(rows)
    if out_rows:
        print(f"\n{len(out_rows)} rows over "
              f"{len({r['slug'] for r in out_rows})} designs")


if __name__ == "__main__":
    main()
```

Add `import csv` and `import json` to the module's imports.

- [ ] **Step 2b: Add the origin guard test**

Append to `digitizer/tests/test_edgeband.py`:

```python
def test_origin_agrees_with_the_rasteriser():
    """`_origin_mm` duplicates two mins from `pro_mask`. This pins them
    together: a stitch at the mm origin must land at pro_mask's own 4 px pad."""
    tmp = Path(__import__("tempfile").mkdtemp())
    write_stitches(tmp / "s.csv", [(3.0, 7.0), (13.0, 7.0), (13.0, 12.0)])
    x0, y0 = eb._origin_mm(tmp / "s.csv")
    assert (x0, y0) == (3.0, 7.0)
    m = eb.side_mask(tmp / "s.csv")
    assert m[4, 4:6].any(), "the origin stitch must sit at the 4 px pad"
```

- [ ] **Step 3: Run tests to verify they pass**

Expected: 17 passed.

- [ ] **Step 4: Run the full digitizer suite for the regression check**

Run:
```bash
cd .claude/worktrees/edge-coverage/digitizer && python -m pytest -q -n auto
```
Expected: **3 failed, 1187+17 passed.** The three are the known Windows golden divergence. Read the summary line directly — do not pipe to `tail`.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/edgeband.py digitizer/tests/test_edgeband.py
git commit -m "feat(measure): per-shape edge attribution and the edgeband CLI"
```

**Phase A ends here. Everything above runs with no corpus and no Drive.**

---

## Task 6: The corpus measurement — LOCAL ONLY

**Files:**
- Create: `docs/edge-coverage-2026-08-19.md`

**Cannot run in a cloud session.** The real lane's source artwork is on `G:` and absent from the tracked zip.

- [ ] **Step 1: Prepare the real lane in a pinned worktree**

```bash
cd .claude/worktrees/edge-coverage/digitizer && PRO_PARITY_ROOT="G:/My Drive/EMB-Bot/Embroidery Files" PRO_PARITY_OUT="$TMPDIR/edgeband-run" python tools/pro_parity/prep_both.py
```

Expect 15 designs under `$PRO_PARITY_OUT/real/`. A `FileNotFoundError` here means the Drive path is wrong — check it before anything else.

- [ ] **Step 2: Run the probe over the real lane**

```bash
cd .claude/worktrees/edge-coverage/digitizer && python tools/pro_parity/edgeband.py "$PRO_PARITY_OUT"/real/*
```

- [ ] **Step 3: Write the findings doc**

`docs/edge-coverage-2026-08-19.md`, following `docs/fragmentation-attribution-2026-08-18.md`'s shape: the per-design table (pro arc vs ours, all three widths), what the numbers attribute the cause to, and a "caveats that must travel with these numbers" section carrying spec §7 verbatim — `art_mask`'s dark-on-light threshold, translation-only registration, the ~0.15 mm instrument floor, our-polygon-on-both-sides for the shape band, and the 0.2 mm width sitting at two pixels.

State plainly whether the row-phase asymmetry in `stage6_fill._row_spans` accounts for the gap, or whether segmentation shrink dominates — and if the evidence does not separate them, say that instead of picking one.

- [ ] **Step 4: Commit**

```bash
git add docs/edge-coverage-2026-08-19.md
git commit -m "measure: what the pro leaves at an edge, and what we leave"
```

---

## Self-Review

**Spec coverage.** §1 question → Tasks 1-2. §5.1 two band sources → Tasks 4 (art) and 5 (shape). §5.2 three widths → `BAND_WIDTHS_MM`, asserted in Task 4. §5.3 four metrics → `_summarise`. §5.4 CSV, no score change → Task 5 `main()`. §6 no engine change → no task touches `digitizer_core/`. §7 blind spots → Task 6 step 3. §8 acceptance: 1 and 5 are Task 6; 2 is Task 3's mutation guard; 3 is `test_bare_arc_measures_a_strip_of_known_length`; 4 is `test_fully_covered_shape_reports_no_arcs` plus the short-row test; 6 is Task 5 step 4.

**One spec deviation, deliberate.** §5.1 implies the per-shape band is measured on both sides. Task 5 measures our side only, and says why in the docstring: placing our polygons on the pro's canvas needs `scorecard.register`'s hill-climb alongside `best_iou`'s whole-pixel shift, and two registration paths in one probe is how two instruments start disagreeing about where a shape is. The pro's half of the comparison is the artwork band, which is the honest one anyway. **Flag this to Kent when Phase A lands** — if he wants pro-side per-shape numbers it is a follow-up task with its own registration decision, not a silent omission.

**Placeholders:** none. Every code step is complete code.

**Type consistency:** `band_mask(shape, w_px)` takes pixels throughout; only `_summarise` converts mm to px, and it is the single caller of the three primitives. Row dicts share `slug/band/side/width_mm/bare_frac/bare_arc_max_mm/bare_arc_p90_mm/band_mm2`; shape rows add `shape_id/tier/area_mm2`, and `csv.DictWriter` is given the union of keys so the art rows write empty cells rather than raising.
