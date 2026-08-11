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
         that strictly lowers total weighted cost, at fixed k.

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

    # --- SWAP (fixed k) ------------------------------------------------------
    # Refines placement, never count: k was decided by the excess rule above
    # and a swap keeps the excess bound's spirit by only ever lowering total
    # weighted cost.
    while True:
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
            if costs[cand] < best_cost - 1e-9:
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
