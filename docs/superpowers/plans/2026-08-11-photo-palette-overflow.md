# Photo Palette Floor-Aware Overflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `drone_render.png` scoring F/0 on `digitizer/tools/corpus_scorecard.py` by letting `select_palette`'s BUILD loop grow past `max_colors`, bounded, when a region being force-merged onto a bad spool actually has an excellent chart match sitting unused.

**Architecture:** One function, `digitizer_core/palette.py:select_palette`, gains a second cap (`hard_cap = max_k + PALETTE_OVERFLOW_K`) and a floor-aware gate on growing past the original `max_k` (now `soft_cap`): past `soft_cap`, only keep adding medoids while the worst-excess region's own `floor` is `<= excess_deltae * 0.5`. Every other function, every caller signature, and every design that already satisfies the excess bound within `max_colors` is untouched.

**Tech Stack:** Python 3.14, numpy, `skimage.color.deltaE_ciede2000`, pytest — matches the rest of `digitizer/`.

## Global Constraints

- `max_colors` (`PipelineConfig.max_colors`, default 12) stays a hard hint for the common case — the new overflow only fires to rescue a genuinely well-matchable region, never to pad the palette for a region no thread is close to. Design doc: `docs/superpowers/specs/2026-08-11-photo-palette-overflow-design.md`.
- New constant `PALETTE_OVERFLOW_K = 3`, defined in `palette.py` next to `PALETTE_EXCESS_DELTAE`.
- "Low floor" threshold is `excess_deltae * 0.5` (≈2.25 at the default 4.5) — derived from the existing named constant, not a new standalone magic number.
- Zero behavior change for any design that already satisfies `PALETTE_EXCESS_DELTAE` within `max_colors` medoids — those designs break out of BUILD's loop before ever reaching the new branch.
- Run tests as `.venv/Scripts/python -m pytest` from `digitizer/` (never the bare `pytest` script).
- Use the Edit tool for all source edits — PowerShell regex round-trips corrupt this repo's UTF-8 (`CLAUDE.md` fact #3).
- This repo's test culture measures real numbers before pinning them (`tests/test_palette.py`'s own header: "every numeric assertion here was MEASURED"). Every number below was actually run against the real `digitizer_core.threads.load_chart()` Isacord chart this planning session — see each test's docstring for what was measured and when.

---

### Task 1: Write the failing tests

**Files:**
- Modify: `digitizer/tests/test_palette.py` (append a new section, after `test_fur_ramp_fixture_segmentation_is_deterministic` at line 309)

**Interfaces:**
- Consumes: `select_palette`, `PALETTE_EXCESS_DELTAE`, `rgb_to_lab`, `load_chart` — all already imported in this file.
- Produces (for Task 2 to satisfy): `digitizer_core.palette.PALETTE_OVERFLOW_K` must exist and equal `3`; `select_palette(..., max_k=N)` must be able to return `len(medoids)` up to `N + PALETTE_OVERFLOW_K`.

This task is a pure red step: the tests import a constant that doesn't exist yet, so the whole file fails to collect until Task 2 lands. That is the expected, correct failure — it proves the tests exercise the new symbol, not a typo.

- [ ] **Step 1: Add `PALETTE_OVERFLOW_K` to the existing import block**

In `tests/test_palette.py`, change:

```python
from digitizer_core.palette import (
    CLASS_MULTIPLIERS,
    PALETTE_EXCESS_DELTAE,
    region_weight,
    select_palette,
)
```

to:

```python
from digitizer_core.palette import (
    CLASS_MULTIPLIERS,
    PALETTE_EXCESS_DELTAE,
    PALETTE_OVERFLOW_K,
    region_weight,
    select_palette,
)
```

- [ ] **Step 2: Append the new test section**

Add at the end of `tests/test_palette.py` (after `test_fur_ramp_fixture_segmentation_is_deterministic`):

```python
# --- 6. Fix #6.1: floor-aware overflow past max_colors -----------------------
# docs/photo-quality-root-cause-2026-08-11.md's drone_render.png finding:
# select_palette's max_colors cap can bind before every region satisfies
# PALETTE_EXCESS_DELTAE, even when the region being force-merged has an
# excellent chart match sitting unused (that fixture's real case: two
# regions with floor 1.98/1.51 force-merged onto "Armour" at ΔE 9.10-9.18).
# These three pin the fix: select_palette may grow past max_k, bounded by
# PALETTE_OVERFLOW_K, but only to rescue a region whose own floor is
# <= excess_deltae/2 -- never to pad the palette for a region no thread is
# actually close to. All floor/ΔE numbers below were measured against the
# real Isacord chart (load_chart()) on 2026-08-11.

_FILLERS_RGB = [(200, 30, 30), (30, 160, 40), (30, 60, 200)]  # 3 mutually
# distant families, each with a decent (not exact) chart match: measured
# floors 4.057 (-> #163 Poinsettia), 1.788 (-> #364 Emerald), 3.362
# (-> #275 Imperial Blue) -- all individually under PALETTE_EXCESS_DELTAE
# (4.5), so once each has its own medoid its own residual satisfies the
# excess bound on its own.


def _overflow_scenario(outlier_rgbs, outlier_area, max_k):
    """3 big, distant, decently-served filler regions (area 9000, so BUILD's
    weighted-cost greedy always picks them before any small-area outlier)
    plus N small (area=outlier_area) outlier regions. Returns (selection,
    labs) so callers can measure a specific outlier's residual."""
    rgbs = np.array(_FILLERS_RGB + list(outlier_rgbs), float)
    labs = rgb_to_lab(rgbs)
    weights = np.array(
        [9000.0] * len(_FILLERS_RGB) + [float(outlier_area)] * len(outlier_rgbs)
    )
    return select_palette(labs, weights, CHART, max_k=max_k), labs


def test_overflow_does_not_fire_for_a_genuinely_hard_to_match_region():
    """A cyan outlier with NO good chart match nearby (measured floor=7.611
    -> #317 Turquoise, well over the excess_deltae/2=2.25 rescue threshold)
    must NOT trigger overflow -- more medoids wouldn't help it, so the
    palette stays at max_k and the outlier keeps riding an existing filler
    medoid. Measured against this scenario: 3 medoids, max_excess_de00
    =29.960 -- the fix must not move either number here, since nothing
    about this region is actually rescuable."""
    sel, labs = _overflow_scenario([(0, 255, 255)], 300.0, max_k=3)
    assert len(sel.medoids) == 3, (
        f"got {len(sel.medoids)} medoids -- overflow fired for a high-floor "
        "region it shouldn't have rescued"
    )
    assert sel.max_excess_de00 == pytest.approx(29.960, abs=0.01)


def test_overflow_rescues_a_genuinely_low_floor_region():
    """A grey outlier that IS an exact chart match (measured floor=0.0 ->
    #308 Silver) -- the same shape as drone_render.png's real defect
    (root-cause doc: 'e.g. Isacord Silver (204,204,204)'). Without the fix
    this force-merges onto a filler medoid at ΔE 33.067 (measured). With
    the fix it must get its own medoid: every region's own floor (fillers
    4.057/1.788/3.362, outlier 0.0) is individually under
    PALETTE_EXCESS_DELTAE, so once the outlier has a medoid the excess
    condition is fully satisfiable and BUILD stops at 4, not the hard cap."""
    sel, labs = _overflow_scenario([(204, 204, 204)], 300.0, max_k=3)
    assert len(sel.medoids) == 4, f"got {len(sel.medoids)} medoids"
    assert sel.max_excess_de00 <= PALETTE_EXCESS_DELTAE, (
        f"max_excess_de00={sel.max_excess_de00:.3f} still over the bound "
        "after the rescue medoid was added"
    )
    from skimage.color import deltaE_ciede2000

    outlier_lab = labs[len(_FILLERS_RGB)]
    outlier_resid = float(
        deltaE_ciede2000(
            outlier_lab.reshape(1, 3),
            CHART.lab[sel.region_spools[len(_FILLERS_RGB)]].reshape(1, 3),
        )[0]
    )
    assert outlier_resid <= PALETTE_EXCESS_DELTAE, (
        f"outlier still {outlier_resid:.3f} ΔE00 from its assigned spool"
    )


def test_overflow_is_bounded_by_palette_overflow_k():
    """Four low-floor outliers (Silver/Black/White/Citrus-yellow -- measured
    floors all 0.0, mutually far apart in Lab, all far from the filler
    hues) but only PALETTE_OVERFLOW_K=3 overflow slots: one must stay
    unresolved. Pins the hard ceiling itself -- len(medoids) never exceeds
    max_k + PALETTE_OVERFLOW_K even when a 4th region would also benefit
    from further growth. Measured against today's code (no overflow at
    all): 3 medoids, max_excess_de00=40.243."""
    outliers = [(204, 204, 204), (0, 0, 0), (255, 255, 255), (255, 255, 0)]
    sel, labs = _overflow_scenario(outliers, 300.0, max_k=3)
    assert len(sel.medoids) <= 3 + PALETTE_OVERFLOW_K, (
        f"got {len(sel.medoids)} medoids -- hard cap did not bind"
    )
    assert len(sel.medoids) == 3 + PALETTE_OVERFLOW_K, (
        "expected the cap to actually bind (4 low-floor outliers competing "
        f"for 3 overflow slots) -- got {len(sel.medoids)}, cap wasn't reached"
    )
    assert sel.max_excess_de00 > PALETTE_EXCESS_DELTAE, (
        "expected at least one region to remain unresolved past the hard "
        f"cap, but max_excess_de00={sel.max_excess_de00:.3f} is within "
        "bound -- the cap didn't actually bind anything in this scenario"
    )
```

- [ ] **Step 3: Run the new tests to verify they fail correctly**

Run: `.venv/Scripts/python -m pytest tests/test_palette.py -q` from `digitizer/`.
Expected: collection error — `ImportError: cannot import name 'PALETTE_OVERFLOW_K' from 'digitizer_core.palette'`. This is the correct red state (proves the tests exercise the not-yet-added symbol, not a typo elsewhere).

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/test_palette.py
git commit -m "test: pin fix #6.1's floor-aware overflow behavior (red)"
```

---

### Task 2: Implement the floor-aware overflow in `select_palette`

**Files:**
- Modify: `digitizer/digitizer_core/palette.py:93` (add the new constant)
- Modify: `digitizer/digitizer_core/palette.py:174-188` (the BUILD loop)

**Interfaces:**
- Consumes: nothing new — same `region_labs`, `region_weights`, `chart`, `max_k`, `excess_deltae` signature.
- Produces: `PALETTE_OVERFLOW_K: int = 3` at module level, importable as `from digitizer_core.palette import PALETTE_OVERFLOW_K`. `select_palette` unchanged in signature and return type (`PaletteSelection`), only its BUILD loop's stopping behavior changes.

- [ ] **Step 1: Add the constant**

In `digitizer_core/palette.py`, change:

```python
PALETTE_EXCESS_DELTAE = 4.5
```

to:

```python
PALETTE_EXCESS_DELTAE = 4.5

# How many medoids BUILD may add past max_k when a region past the cap has
# an excellent chart match sitting unused (docs/photo-quality-root-cause-
# 2026-08-11.md's drone_render.png finding) -- bounded so a pathological
# gradient-heavy design can't balloon the color count with no ceiling. See
# tests/test_palette.py's "Fix #6.1" section for the measured before/after.
PALETTE_OVERFLOW_K = 3
```

- [ ] **Step 2: Rewrite the BUILD loop**

In `digitizer_core/palette.py`, change:

```python
    # --- BUILD ---------------------------------------------------------------
    selected: list[int] = []
    res = np.full(n, np.inf)
    cap = max(1, min(int(max_k), len(chart)))
    while len(selected) < cap:
        if selected and ((res - floor) <= excess_deltae).all():
            break
        costs = (w[:, None] * np.minimum(res[:, None], dist)).sum(axis=0)
        costs[selected] = np.inf
        cand = int(np.argmin(costs))  # ties -> lowest chart index
        current = float((w * res).sum()) if selected else np.inf
        if costs[cand] >= current - 1e-9:
            break  # nothing left improves — adding would only pad the palette
        selected.append(cand)
        res = np.minimum(res, dist[:, cand])
```

to:

```python
    # --- BUILD ---------------------------------------------------------------
    selected: list[int] = []
    res = np.full(n, np.inf)
    soft_cap = max(1, min(int(max_k), len(chart)))
    hard_cap = max(1, min(int(max_k) + PALETTE_OVERFLOW_K, len(chart)))
    while len(selected) < hard_cap:
        if selected and ((res - floor) <= excess_deltae).all():
            break
        if len(selected) >= soft_cap:
            # Past max_colors: only keep growing to rescue a region whose
            # own floor is low enough that a genuinely good chart match
            # exists (docs/photo-quality-root-cause-2026-08-11.md's
            # drone_render.png finding) -- never to pad the palette for a
            # region no thread is actually close to.
            worst = int(np.argmax(res - floor))
            if not (floor[worst] <= excess_deltae * 0.5):
                break
        costs = (w[:, None] * np.minimum(res[:, None], dist)).sum(axis=0)
        costs[selected] = np.inf
        cand = int(np.argmin(costs))  # ties -> lowest chart index
        current = float((w * res).sum()) if selected else np.inf
        if costs[cand] >= current - 1e-9:
            break  # nothing left improves — adding would only pad the palette
        selected.append(cand)
        res = np.minimum(res, dist[:, cand])
```

- [ ] **Step 3: Run the new tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_palette.py -q` from `digitizer/`.
Expected: all pass, including the 3 new ones and every pre-existing test in this file (the fur-ramp and eye/subject-weight tests never hit `soft_cap` before satisfying their own excess bound, so the new branch is dead code for them — confirm this by reading their pass, not just trusting the reasoning).

- [ ] **Step 4: Run the full digitizer suite to check for unrelated regressions**

Run: `.venv/Scripts/python -m pytest -q` from `digitizer/`.
Expected: same pass/fail counts as the pre-merge baseline established 2026-08-11 (1035 passed / 8 pre-existing-environment failed / 3 skipped — see `COOKBOOK.md`'s pre-existing-failure note, which this session found stale at 3 documented items vs. 8 actual; not this task's job to fix that staleness, just don't let the count silently grow past 8). Any NEW failure beyond that set means the BUILD loop change touched something unintended — stop and diagnose before continuing.

- [ ] **Step 5: Commit**

```bash
git add digitizer_core/palette.py
git commit -m "fix: floor-aware overflow past max_colors in select_palette (#6.1)"
```

---

### Task 3: Verify against the real `drone_render.png` fixture and update the scope dashboard

**Files:**
- Read-only verification: `digitizer/tools/corpus_scorecard.py`
- Modify: `MASTER_SCOPE.md` (status note only, via the `update-master-scope` skill)

**Interfaces:**
- Consumes: the merged fix from Task 2.
- Produces: nothing new — this task is verification and documentation, no code.

- [ ] **Step 1: Run the corpus scorecard diff**

Run, from `digitizer/`: `.venv/Scripts/python tools/corpus_scorecard.py diff`

This re-digitizes every committed fixture (including `photo/drone_render.png`) at both `MATRIX` configs (`left_chest`, `hat_front`) and prints score/grade deltas against the stored baseline — it does not require a `capture` first.

Expected: `photo/drone_render.png @ 80mm/left_chest` and `@ 80mm/hat_front` both show a score/grade improvement (root-cause doc's baseline: F/0 at both). Read the actual printed delta — do not assume a specific number, the real chart-wide effect of the overflow depends on which spools get selected on the real fixture, not the synthetic test scenarios from Task 1.

- [ ] **Step 2: Decide whether to capture a new baseline**

If the score moved in the expected direction and no *other* fixture regressed (the diff output covers all 14 fixtures × 2 configs — read all of it, not just `drone_render.png`'s lines): run `.venv/Scripts/python tools/corpus_scorecard.py capture` to make this the new baseline, per the tool's own docstring ("re-run this deliberately... whenever a change's new behaviour should become the new baseline rather than a regression to flag").

If anything else moved unexpectedly, stop and diagnose before capturing — capturing would silently adopt a regression as the new normal.

- [ ] **Step 3: Commit the new baseline (if captured)**

```bash
git add testdata/corpus_scorecard_baseline.json
git commit -m "chore: recapture corpus scorecard baseline after fix #6.1"
```

- [ ] **Step 4: Update MASTER_SCOPE.md**

Invoke the `update-master-scope` skill to record: fix #6.1 (drone_render.png `max_colors` floor-aware overflow) landed, with the real before/after corpus-scorecard numbers from Step 1. Cross-reference `docs/photo-quality-root-cause-2026-08-11.md` so a future reader knows fixes #6.2 (summit_badge.png) and #6.3 (repro_gradient_white_icon.png) from that same doc are still open.
