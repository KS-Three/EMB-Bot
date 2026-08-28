"""Per-stroke coverage — the letterform instrument that sees a DROPPED feature.

## Why this exists

The two measures this project already had are both blind to letterform damage,
and they are blind for the same reason: **they average.**

- **Bare-fabric coverage** scores THERMAL's visibly deformed `H` at "1.9% bare",
  i.e. fine. It totals bare area over the whole letter, so a wholly missing arm
  is a rounding error next to a correctly-sewn stem.
- **Thread-vs-artwork IoU** (`s11_iou.py`) is a real improvement and still
  averages. DRONE's `E` sews as a visible "L" and scores 0.534 against a 0.580
  thread-width ceiling — 92% of the best achievable, for a letter missing two
  arms out of three.

Deformation is LOCAL. A metric that reports a mean cannot see it, whatever the
mean is of. So this reports the WORST stroke rather than the average one.

## What it measures

The artwork letter's medial axis is decomposed into strokes — the same
`_skeleton_edges` + `_merge_through_junctions` decomposition `extract_strokes`
uses to build satin rails, so these are the strokes the engine itself works in
terms of. Each stroke is walked at `step_mm` and scored on the fraction of its
samples that have thread on them.

Measured on `drone_render.png` (2026-08-28):

| letter | IoU | mean coverage | worst stroke |
| --- | --- | --- | --- |
| DRONE `E`, sews as an "L" | 0.384 | 72.7% | **58.3%** |
| THERMAL `E` | 0.594 | 96.6% | 92.9% |
| PRECISION `P` | 0.685 | 96.3% | 86.1% |
| PRECISION `O` | 0.644 | 100% | 100% |
| THERMAL `L` | 0.633 | 100% | 100% |

The mean separates DRONE's `E` from the rest by 24 points; the worst stroke
separates it by 28 and, more usefully, points AT the stroke that failed.

## A "stroke" here is a medial-axis CHAIN, not a limb

`_merge_through_junctions` welds arms that run straight through a branch node,
which is what makes a T's bar one stroke rather than two trimmed halves. Useful
for satin rails; it means the granularity of this measure is not "per limb".
A synthetic block `E` decomposes into 2 chains (31.8 mm and 7.7 mm), not 4
limbs, while `DRONE`'s real `E` gives 4.

So a break is scored against however much chain it sits on. A missing arm on a
letter whose arms weld into the stem reads as a dent in a long chain rather
than a dead short one — still visible, less dramatic than the DRONE numbers
above suggest. Read the worst stroke as "the worst PART of this letter", and
go look at which chain it was before quoting a figure.

## What it is blind to, and this is not a small caveat

**Tilt.** THERMAL's `H` is visibly deformed and scores 100% here, because its
defect is a column sewn at the wrong ANGLE, not a column that is missing.
Thread is on every stroke. This instrument answers "is there thread where the
letter is", not "is the thread going the right way".

So it does NOT close `README.md`'s standing ask — *"do not put a quality claim
on it until it can separate a tilted column from a covered one."* It closes the
other half: a feature that got dropped. Quote it for that and nothing else.

**A measured dead end, recorded so it is not walked twice.** The obvious
companion metric — per-stroke deviation of thread direction from the medial
axis's local perpendicular — was built and rejected on 2026-08-28. It ranks a
GOOD letter worse than the deformed one:

| letter | median cross-angle error | p90 |
| --- | --- | --- |
| THERMAL `H`, deformed | 16.6° | 62.3° |
| THERMAL `L`, control | 14.7° | 47.3° |
| PRECISION `O`, control | **31.7°** | **75.5°** |

The reference is what is wrong, not the idea: on a curved letter the spine
turns constantly, so "perpendicular to the local spine" confounds curvature
with deformation, and the roundest letter scores worst. A tilt metric needs a
reference that is stable under curvature — the satin rails the engine actually
built, rather than the medial axis it built them from, is the untried candidate.
"""
from __future__ import annotations

import math

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

from digitizer_core.shapefield import build_shape_field
from digitizer_core.textcluster import _skeleton_chains_mm

# A stroke shorter than this is not scored. Below roughly one stroke width the
# medial axis is a junction artifact rather than a limb of the letter, and a
# two-sample "stroke" reports 0% or 100% with nothing in between — which, in a
# WORST-of measure, is exactly the noise that would swamp the signal.
MIN_STROKE_MM = 0.5

# Walk step. Fine enough that a missing arm cannot hide between samples on the
# smallest letter in the corpus (DRONE's caps are 2.91 mm), coarse enough that
# a whole design stays cheap.
STEP_MM = 0.25


def stroke_coverage(poly: Polygon, thread: BaseGeometry,
                    step_mm: float = STEP_MM,
                    min_stroke_mm: float = MIN_STROKE_MM
                    ) -> list[tuple[float, float]]:
    """`(arc length mm, fraction covered)` for each medial-axis stroke of `poly`.

    `thread` is the sewn thread as a single geometry — typically every stitch
    segment buffered to half the thread width and unioned, which is what
    `s11_iou.py` already builds.

    Returns `[]` rather than raising when the shape will not field or has no
    skeleton, matching the fail-open discipline of the modules it borrows from.
    """
    field = build_shape_field(poly)
    if field is None or not field.skel.any():
        return []

    out: list[tuple[float, float]] = []
    for chain in _skeleton_chains_mm(field):
        if len(chain) < 2:
            continue
        cum = [0.0]
        for a, b in zip(chain, chain[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        total = cum[-1]
        if total < min_stroke_mm:
            continue
        samples = max(3, int(total / step_mm))
        hit = 0
        j = 0
        for i in range(samples + 1):
            target = total * i / samples
            # cum is monotonic, so advance rather than re-scan per sample.
            while j + 1 < len(cum) and cum[j + 1] <= target:
                j += 1
            if thread.covers(Point(chain[j])):
                hit += 1
        out.append((total, hit / (samples + 1)))
    return out


def worst_stroke(coverage: list[tuple[float, float]]) -> float | None:
    """The least-covered stroke, or None when nothing was measurable.

    THE headline number. A letter is as good as its worst limb, which is the
    whole point: `mean` is what lets a missing arm hide behind a good stem.
    """
    return min((c for _, c in coverage), default=None)


def mean_coverage(coverage: list[tuple[float, float]]) -> float | None:
    """Length-weighted mean coverage, or None when nothing was measurable.

    Reported alongside `worst_stroke` deliberately, not instead of it: the GAP
    between the two is the signal that a letter is locally rather than
    uniformly bad. DRONE's `E` reads 72.7% mean against 58.3% worst; a letter
    that is merely under-covered everywhere reads the two close together.
    """
    total = sum(length for length, _ in coverage)
    if total <= 0.0:
        return None
    return sum(length * c for length, c in coverage) / total
