"""Chart-restricted weighted k-medoids palette selection (photo plan,
technique-menu row 13; build-order step 7).

Replaces per-region nearest-thread snapping for photo-class designs. The
defect it fixes, measured before writing this module: an 8-step brown fur
ramp snapped per-region lands on SEVEN distinct Isacord spools (Very Dark
Brown, Coffee Bean, Espresso, Pine Park, Khaki, Pecan, Taupe) — each region
independently grabbing its own idiosyncratic nearest neighbor, the
"scattered near-duplicates" the plan's row-13 accept criterion names. The
same ramp through this module resolves to FIVE browns (L 21 -> 73, one
family), because a medoid must serve several regions at once: its
weighted-cost-minimizing position sits centrally in the ramp's family
instead of at each region's private nearest thread.

Why k-MEDOIDS and not k-means: the palette is restricted to the in-repo
thread chart — every "center" must BE a purchasable spool (`threads.Chart`,
already policy-filtered under the 2026-07-29 facts-doctrine decision), so
the candidate set is the chart itself and the objective is evaluated only at
chart points. Distances are CIEDE2000 (`skimage.color.deltaE_ciede2000` —
the same ΔE machinery `threads.nearest_index`, `stage2_photo_segment` and
`stage6_blend` already use, not a new implementation; CIEDE2000 provides no
mean anyway, which is the other reason means are the wrong tool here).

The algorithm is classic PAM, deterministic by construction (no RNG
anywhere; every argmin tie resolves to the lowest chart index, and a chart
is a fixed ordered list):

  BUILD  greedily add the chart thread minimizing total weighted cost
         Σ w_i · min(res_i, ΔE00(region_i, candidate)), until every
         region's assignment is within `PALETTE_EXCESS_DELTAE` of its own
         personal-best chart distance (the "excess" — see below), or no
         candidate strictly improves. Bounded stopping: soft cap max_k gates
         where excess-only stopping applies; past max_k, allows growth to at
         most hard_cap = max_k + PALETTE_OVERFLOW_K, only when a region with
         low floor (<= excess_deltae/2) exists — never to pad palette for a
         region no thread actually matches well (docs/photo-quality-root-
         cause-2026-08-11.md's drone_render.png finding).
  SWAP   repeatedly take the single best (selected, unselected) exchange
         that strictly lowers total weighted cost, at fixed k. "Strictly"
         is RELATIVE to the cost scale (`PALETTE_COST_RTOL`) and the sweep
         count is capped (`PALETTE_MAX_SWAP_SWEEPS`): with an absolute
         epsilon this loop cycled forever between two bit-identical chart
         spools on a real portrait — see those constants for the measurement.

The stop rule is EXCESS over each region's own floor, not an absolute ΔE00:
a region whose nearest chart thread is already 8.1 ΔE00 away (measured on
the fur ramp's darkest step — charts are sparse in dark browns) can never
satisfy an absolute tolerance, and an absolute rule was measured to inflate
k to the cap by appending medoids that serve nobody (whites, black). Excess
asks the answerable question: "is this region's assigned spool at most T
worse than the best the chart could ever have given it?"
`PALETTE_EXCESS_DELTAE` is half of `stage6_blend.SHADE_STEP_DELTAE` (the
blend tier's measured perceptual step between adjacent shades of one ramp):
a medoid may stand in for a region up to half a shade step worse than its
personal best — coarser than that and the substitution reads as a different
shade, finer and near-duplicate spools survive. The two constants are
cross-pinned in `tests/test_palette.py` so they cannot drift apart silently.

THE CLASS-WEIGHT SEAM (this slice's honest scope, same pattern as
`stage6_streamline`'s documented multi-color seam and
`stage2_photo_segment._face_local_threshold`): the plan's row-13 weight is
region area × a class multiplier — eyes 8-10, skin 4-5, subject 2,
background 1 — so that under a binding color cap the palette spends its
spools where a portrait's fidelity actually lives. `CLASS_MULTIPLIERS`
carries those values and `region_weight` applies them. STATUS 2026-08-05:
the seam is FULLY WIRED for real. "eyes" and "skin" flow from the YuNet
face priors (`stage1_photo_prep.detect_faces_seam` ->
`stage2_photo_segment._region_classes`, behind the photo_prep gate),
wired 2026-08-04. "subject"/"background" flow from the rembg subject
cutout (`stage1_photo_prep.remove_background_seam` -> `pipeline.
run_stages`'s `subject_bg_mask` -> `stage2_photo_segment._region_classes`,
behind the photo_prep_background_removal gate on top of that), wired
2026-08-05: a non-face region majority-inside the real rembg mask classes
"background", otherwise "subject" — nothing runs this off stage 1's
border-flood `bg_mask` default, which was never meant to distinguish a
subject's interior from its background and would misrepresent what that
mask actually knows. Regions no prior covers (and every run with neither
face priors nor a real rembg mask) still pass `region_class=None` and
weigh plain area, exactly the area-honest degradation this paragraph
always promised. Measured proof the seam is live, not decorative (pinned
in tests): a 300 px near-black eye region against two 9000 px tan patches
under a k=2 cap loses its dark entirely at multiplier 1 (assigned to
Pecan, 44.5 ΔE00 off) and keeps a dedicated dark at the eyes multiplier
(Black, 6.3 ΔE00); the analogous subject/background test in
`tests/test_palette.py` measures the same shape of result for a small
subject patch against a large background field under a binding cap.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from skimage.color import deltaE_ciede2000

from .threads import Chart

# Half of stage6_blend.SHADE_STEP_DELTAE (9.0) — the relationship is the
# point (see module docstring), and tests/test_palette.py pins it against
# the blend tier's own constant. Not imported from stage6_blend at runtime:
# this module has no other reason to pull in shapely/stage machinery, and a
# broken cross-pin should fail a test, not an import.
PALETTE_EXCESS_DELTAE = 4.5

# How many medoids BUILD may add past max_k when a region past the cap has
# an excellent chart match sitting unused (docs/photo-quality-root-cause-
# 2026-08-11.md's drone_render.png finding) -- bounded so a pathological
# gradient-heavy design can't balloon the color count with no ceiling. See
# tests/test_palette.py's "Fix #6.1" section for the measured before/after.
PALETTE_OVERFLOW_K = 3

# Plan row 13's class multipliers, midpoints of its stated ranges. Applied
# by `region_weight`; keys are the vocabulary plan step 3's face priors will
# speak when they exist (see THE CLASS-WEIGHT SEAM above).
CLASS_MULTIPLIERS: dict[str, float] = {
    "eyes": 9.0,        # plan: 8-10
    "skin": 4.5,        # plan: 4-5
    "subject": 2.0,
    "background": 1.0,
}

# "Strictly lowers total cost" has to be measured RELATIVE to that cost, not
# against a fixed 1e-9, because weights are pixel areas: a portrait's total
# weighted cost runs ~1e7, where one double ULP is ~1.9e-9 -- already larger
# than the old absolute epsilon. The two sides of the comparison are computed
# by DIFFERENT numpy reductions (a length-N `(w * d1).sum()` versus a column
# of an (N, C) `.sum(axis=0)`), so they disagree in the last ulp on a swap
# that is mathematically a no-op, and the loop accepts it forever.
#
# Measured 2026-08-23 on a 2 MP selfie (N=58, C=398, cost 9.779e6): the chart
# holds two spools with BIT-IDENTICAL Lab (indices 8 and 9, dE00 0.0), SWAP
# alternated 8 -> 9 -> 8 claiming a 3.7e-9 gain each sweep, and the medoid set
# repeated on sweep 3 with a total cost drop of exactly 0. The job never
# returned -- 25+ min of wall clock inside this loop, with the service's
# single worker blocked behind it.
#
# Two conditions have to coincide, which is why this hid for so long. The
# cost must clear ~4.5e6 (= 2^52 * 1e-9) so that one ulp outgrows the old
# epsilon -- but that alone is not enough: the four other real portraits
# measured the same day all clear it (7.4e6 to 1.7e7) and converge fine.
# A pair of candidates whose TRUE cost difference is zero must also be in
# play, and the chart's duplicate-Lab spools are the way that happens. Every
# committed fixture missed the first condition; four real photos met the
# first and not the second; the selfie met both.
#
# 1e-12 relative sits ~5000x above the ulp noise floor at portrait scale
# (9.8e-6 against a 1.9e-9 ulp) and ~5000x above it at unit scale too, so the
# rule is scale-free where the old absolute epsilon was not. It is also far
# below anything perceptual: 1e-12 of a ~1e7 weighted cost is ~1e-5 ΔE00·px,
# against the 4.5 ΔE00 excess bound this module actually reasons in.
#
# The threshold is set from the noise floor, not from observed swap sizes,
# and the measurement says that is the right way round: across the twelve
# calls surveyed for PALETTE_MAX_SWAP_SWEEPS, the real accepted swaps are
# ordinary cost improvements nowhere near this margin, while the rejected
# one is a bit-for-bit no-op. Old rule vs new produced IDENTICAL medoids on
# all five real photos including the one that hung -- the fix decides
# termination, not palettes. `max(1.0, ...)` floors the scale so a near-zero
# cost cannot collapse the threshold to nothing.
PALETTE_COST_RTOL = 1e-12

# Belt and braces: PAM's swap phase terminates because each accepted swap
# strictly lowers a bounded cost, but that argument is only as good as the
# arithmetic underneath it -- and the bug above is precisely a case where it
# was not. A cap converts any future floating-point pathology from a hung
# request into a slightly-suboptimal palette, which is the right way to fail.
# Measured 2026-08-23 across twelve calls -- seven corpus fixtures
# (drone_render, owl_kent, fur_ramp, photo_sunset_backlit, photo_dof_meadow,
# enthusiast_logo) plus five real photos: the fixtures all converge on the
# first sweep (BUILD's greedy result is already swap-optimal there), and the
# photos, where SWAP does earn its keep, take at most THREE. 200 is ~65x that
# worst case and cannot bind on anything resembling current inputs; if it
# ever does, that is a bug report, not a tuning knob.
PALETTE_MAX_SWAP_SWEEPS = 200


def _strictly_better(candidate_cost: float, current_cost: float) -> bool:
    """Is `candidate_cost` a REAL improvement on `current_cost`?

    Extracted so the rule is testable without running the loop it guards:
    under the pre-2026-08-23 absolute epsilon this returned True for the
    measured pair (9779152.0087797288, 9779152.0087797325) -- a swap between
    two bit-identical chart spools whose true gain is zero -- and SWAP
    cycled on it forever. `tests/test_palette.py` pins that exact pair.

    `current_cost` is +inf on BUILD's first pass (nothing selected yet, so
    every region's residual is inf). A relative margin is meaningless there
    -- `inf - rtol * inf` is nan, and a nan comparison would silently reject
    the first medoid and return an EMPTY palette -- so an infinite incumbent
    is beaten by any finite candidate, which is what the absolute form did.
    """
    if not math.isfinite(current_cost):
        return candidate_cost < current_cost
    return candidate_cost < current_cost - PALETTE_COST_RTOL * max(1.0, abs(current_cost))

# Belt and braces: PAM's swap phase terminates because each accepted swap
# strictly lowers a bounded cost, but that argument is only as good as the
# arithmetic underneath it -- and the bug above is precisely a case where it
# was not. A cap converts any future floating-point pathology from a hung
# request into a slightly-suboptimal palette, which is the right way to fail.
# Measured 2026-08-23 across seven corpus calls (drone_render, owl_kent,
# fur_ramp, photo_sunset_backlit, photo_dof_meadow, enthusiast_logo, the 2 MP
# selfie): **every one converges in a single sweep** -- BUILD's greedy result
# is already swap-optimal on real art, so SWAP's one pass only confirms it.
# 200 is therefore ~200x observed need and cannot bind on anything resembling
# current inputs; if it ever does, that is a bug report, not a tuning knob.
PALETTE_MAX_SWAP_SWEEPS = 200


def region_weight(area_px: float, region_class: str | None = None) -> float:
    """Plan row 13's region weight: area × class multiplier.

    `region_class=None` (the only value any caller can honestly supply until
    plan step 3's face priors exist) means multiplier 1.0 — plain area. An
    unknown class name raises rather than silently weighting wrong: by the
    time real classes flow here, a typo'd class would otherwise quietly
    demote a portrait's eyes to background weight.
    """
    if region_class is None:
        return float(area_px)
    if region_class not in CLASS_MULTIPLIERS:
        raise KeyError(
            f"unknown region class {region_class!r} (known: {sorted(CLASS_MULTIPLIERS)})"
        )
    return float(area_px) * CLASS_MULTIPLIERS[region_class]


@dataclass(frozen=True)
class PaletteSelection:
    """The selection result: which chart spools, and who sews with what.

    `medoids[assignment[i]]` is region i's chart index — `region_spools`
    spells that out for callers that only want the flat mapping.
    """
    medoids: list[int]          # chart indices, in selection (BUILD) order
    assignment: np.ndarray      # (N,) int — index into `medoids` per region
    max_excess_de00: float      # worst residual-over-personal-floor, ΔE00

    @property
    def region_spools(self) -> list[int]:
        return [self.medoids[int(a)] for a in self.assignment]


def select_palette(
    region_labs: np.ndarray,
    region_weights: np.ndarray,
    chart: Chart,
    max_k: int,
    excess_deltae: float = PALETTE_EXCESS_DELTAE,
) -> PaletteSelection:
    """Weighted k-medoids over `chart`, ΔE00 objective. See module docstring.

    `region_labs` — (N, 3) CIELAB (threads.py's pinned convention: true
    CIELAB ranges from skimage rgb2lab, never cv2's 8-bit scaling).
    `region_weights` — (N,) positive weights (`region_weight`'s output).
    `max_k` — soft palette cap: BUILD's stopping point when all regions
    satisfy the excess bound. May be exceeded up to hard_cap = max_k +
    PALETTE_OVERFLOW_K if low-floor regions (floor <= excess_deltae/2)
    require rescue. Callers pass cfg.max_colors.

    Deterministic: no RNG; ties resolve to the lowest chart index.
    N = 0 returns an empty selection; N = 1 is exactly the old per-region
    nearest snap (one medoid = that region's nearest thread).
    """
    labs = np.asarray(region_labs, np.float64).reshape(-1, 3)
    w = np.asarray(region_weights, np.float64).reshape(-1)
    n = len(labs)
    if n != len(w):
        raise ValueError(f"{n} region labs but {len(w)} weights")
    if n == 0:
        return PaletteSelection([], np.empty(0, np.int64), 0.0)
    if (w <= 0).any():
        raise ValueError("region weights must be positive")

    # (N, C) ΔE00 of every region against every chart thread — the whole
    # objective, evaluated once. N is tens of regions, C ~400 threads;
    # trivial, same order as the blend tier's own shade selection.
    dist = deltaE_ciede2000(labs[:, None, :], chart.lab[None, :, :])
    floor = dist.min(axis=1)  # each region's personal best — the excess baseline

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
            if floor[worst] > excess_deltae * 0.5:
                break
        costs = (w[:, None] * np.minimum(res[:, None], dist)).sum(axis=0)
        costs[selected] = np.inf
        cand = int(np.argmin(costs))  # ties -> lowest chart index
        current = float((w * res).sum()) if selected else np.inf
        if not _strictly_better(float(costs[cand]), current):
            break  # nothing left improves — adding would only pad the palette
        selected.append(cand)
        res = np.minimum(res, dist[:, cand])

    # --- SWAP (fixed k) ------------------------------------------------------
    # Refines placement, never count: k was decided by the excess rule above
    # and a swap keeps the excess bound's spirit by only ever lowering total
    # weighted cost.
    for _sweep in range(PALETTE_MAX_SWAP_SWEEPS):
        sel = np.array(selected)
        d = dist[:, sel]                              # (N, k)
        order = np.argsort(d, axis=1, kind="stable")
        rows = np.arange(n)
        near = order[:, 0]
        d1 = d[rows, near]
        d2 = d[rows, order[:, 1]] if len(selected) > 1 else np.full(n, np.inf)
        best_cost = float((w * d1).sum())
        best_swap: tuple[int, int] | None = None
        for mi in range(len(selected)):
            # Residuals with medoid mi removed: second-nearest where mi was
            # nearest, unchanged elsewhere.
            base = np.where(near == mi, d2, d1)
            costs = (w[:, None] * np.minimum(base[:, None], dist)).sum(axis=0)
            costs[sel] = np.inf
            cand = int(np.argmin(costs))
            if _strictly_better(float(costs[cand]), best_cost):
                best_cost = float(costs[cand])
                best_swap = (mi, cand)
        if best_swap is None:
            break
        selected[best_swap[0]] = best_swap[1]

    sel = np.array(selected)
    assignment = np.argmin(dist[:, sel], axis=1)
    final_res = dist[np.arange(n), sel[assignment]]
    return PaletteSelection(
        medoids=[int(s) for s in selected],
        assignment=assignment.astype(np.int64),
        max_excess_de00=float((final_res - floor).max()),
    )
