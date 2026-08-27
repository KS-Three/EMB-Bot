"""Are the edges smooth, or sawtoothed? Kent's most frequent complaint.

Reviewing fourteen stitch-outs on 2026-08-27 he raised this on EIGHT of them:
*"Lines/circles are not smooth like the photo, Shapes are accurate but
smoothness is not"*, *"the edges around BECKER... they are jaged"*, *"it's
sawtoothed and jaged"*, *"ENTHUSIAST looks to wavey and not crisp/clean"*,
*"should be cleaner and more crisp"*.

That sentence — **shapes are accurate but smoothness is not** — is the whole
problem statement. Every instrument this repo had scores the shape:

  * `artfidelity_self.coverage` is an area IoU. A sawtoothed edge and a clean
    one enclose almost the same area, so it barely moves.
  * `preflight` graded `logo_whitebg` **A 100** on a design Kent says is not
    smooth, and `becker_marine_logo` **B 76** where he calls the edges jagged.
  * `dropped_elements` deliberately OPENS the boundary band away, because a
    half-millimetre halo around every shape would swamp the lost elements it
    exists to find. It says so, and points here.

The repo already learned this the hard way on lettering: *"a wrong-angle letter
scores a perfect IoU"*, and bare-fabric coverage graded a visibly deformed H at
"1.9% bare, fine" (`.claude/memory/letterform-fidelity-2026-08-26.md`).

## Displacement is not raggedness

`pro_parity/enginefidelity.py` already measures outline deviation, and its
`boundary_distance_mm` is reused here rather than reimplemented — including for
the dtype trap its docstring documents, where a uint8 mask silently returns
6553.6 instead of raising.

But mean boundary distance answers "how far off is the outline", which is NOT
the question. An outline offset a clean 0.3 mm and an outline sawtoothing
+/-0.3 mm about the true edge have the same mean. One is a pull-compensation
question; the other is what Kent is looking at. So:

    offset_mm       mean distance from the sewn outline to the artwork's —
                    displacement, which pull comp and registration own.
    ragged_mm       the STANDARD DEVIATION of that distance along the outline.
                    A smooth outline sits at a near-constant distance whatever
                    that distance is; a sawtooth wanders. This is the number
                    the complaint is about. Measured only inside `BAND_MM`, so
                    a dropped element cannot masquerade as a rough edge — see
                    that constant for the measurement that forced the clip.
    perimeter_ratio sewn outline length / artwork outline length. The blunt,
                    physical reading: a jagged edge is simply LONGER than the
                    smooth one enclosing the same shape. 1.0 is a perfect
                    trace; a sawtooth runs well above it.

## Curve fidelity is NOT measurable from a raster — measured, not assumed

Kent's notes hold TWO smoothness complaints and he confirmed both matter about
equally: "sawtoothed and jaged" (edge noise, which `ragged_mm` addresses) and
"Lines/circles are not smooth like the photo" — a curve sewn as a polygon,
the case `enginefidelity.py`'s docstring names as "a 20 mm circle RDP'd into a
20-gon".

A turning-concentration measure for the second was built and REJECTED here on
2026-08-27. The idea was sound — a circle spreads its 360 degrees evenly, a
20-gon concentrates them in 20 corners — but it cannot work on a rasterised
mask, and the experiment says so plainly. Turning concentration of a 20 mm
circle against regular n-gons, at four resample steps:

    step mm   circle   60-gon   40-gon   20-gon   12-gon   monotonic?
        0.5    0.320    0.222    0.231    0.414    0.554   no
        1.0    0.314    0.236    0.217    0.296    0.373   no
        2.0    0.211    0.126    0.121    0.154    0.230   no
        3.0    0.177    0.100    0.108    0.100    0.163   no

The rasterised CIRCLE scores more angular than a 40-gon at every step, because
a raster boundary is itself a staircase of 45 and 90 degree steps — the raster
IS a polygon, and no resampling of it recovers the curve underneath.

So curve fidelity has to be read from the STITCH PATH — `plan.iter_runs()`'s
own points, which are the vertices the machine actually sews — not from any
render of it. That is the next instrument, and it is a different input, not a
different threshold.

`ragged_mm` and `perimeter_ratio` are deliberately two views of one thing. They
fail differently — the ratio is fooled by a shape that gains detail, the
deviation by a boundary that wanders slowly — and a design where they disagree
is worth looking at rather than averaging.

Usage:
    python -m tools.edge_smoothness <image> [<image> ...]
    python -m tools.edge_smoothness --all
    python -m tools.edge_smoothness --all --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "pro_parity"))

from enginefidelity import _boundary, boundary_distance_mm  # noqa: E402

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from tools.artfidelity_self import (FIXTURES, RES, art_ink_field,  # noqa: E402
                                    ink_is_ambiguous, ink_saturation,
                                    INK_SATURATION_MAX, register,
                                    stitch_coverage_field)


BAND_MM = 1.0
# Only sewn-outline pixels within this distance of the artwork outline are
# measured. Beyond it the thread is not tracing that edge at all — it is a lost
# element, an invented one, or a limb the engine put somewhere else, and
# `dropped_elements` owns those.
#
# Without the clip the two instruments contaminate each other. Measured
# 2026-08-27 on `becker_marine_logo`: its lost C infill sits 3.32 mm from the
# artwork outline (Hausdorff, against 0.7-1.0 mm for every other flat design),
# and it alone drove that design to the TOP of the raggedness ranking while its
# perimeter ratio was the LOWEST of the five. One missing element was
# masquerading as a jagged edge.
#
# JUDGEMENT at 1.0 mm: wide enough to contain any real boundary wobble (a
# 0.40 mm thread laid a stitch or two off), narrow enough that a dropped
# element cannot reach into it. It is deliberately the mirror of
# `dropped_elements.HALO_OPEN_PX`, which throws away the same band from the
# other side.


def perimeter_mm(mask: np.ndarray) -> float:
    """Total contour length of `mask`, in mm.

    `cv2.arcLength` on real contours rather than counting boundary pixels: a
    45-degree edge has about 1.41 boundary pixels per unit of true length, so a
    pixel count would report a diagonal as half again as long as it is and make
    every rotated shape look rough. Contours measure the chain, so the diagonal
    is a diagonal.

    Holes count. A counter's edge is edge — if the inside of an O is ragged the
    design is ragged, and RETR_LIST keeps inner contours that RETR_EXTERNAL
    would silently drop.
    """
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_LIST,
                             cv2.CHAIN_APPROX_NONE)
    return float(sum(cv2.arcLength(c, True) for c in cs)) / RES


def boundary_spread(sewn: np.ndarray, art: np.ndarray) -> tuple[float, float]:
    """-> (mean, standard deviation) in mm of the distance from each SEWN
    outline pixel to the nearest artwork outline pixel.

    Directed on purpose, unlike `boundary_distance_mm`'s symmetric mean. The
    question is how the thread's own edge behaves, and the symmetric version
    mixes in "artwork outline the engine never went near", which is a lost
    element — a different instrument's job.

    The standard deviation is the raggedness: a boundary that is uniformly
    0.3 mm outside the artwork has spread ~0, however wrong its offset; a
    boundary that sawtooths across the true edge has a large spread even when
    its mean is near zero.
    """
    for name, m in (("sewn", sewn), ("art", art)):
        if m.dtype != bool:
            raise ValueError(f"{name} must be a bool mask, got {m.dtype}")
    bs, ba = _boundary(sewn), _boundary(art)
    if not bs.any() or not ba.any():
        raise ValueError("empty boundary")
    # Same distance-transform trick enginefidelity uses, and the same reason
    # its docstring gives for the bool check above: `~ba` on a uint8 array
    # flips 1 -> 254, every pixel reads nonzero, and OpenCV returns a
    # saturation sentinel that looks like a plausible measurement.
    dt = cv2.distanceTransform((~ba).astype(np.uint8), cv2.DIST_L2,
                               cv2.DIST_MASK_PRECISE)
    vals = dt[bs] / RES
    near = vals[vals <= BAND_MM]
    if near.size == 0:
        # Nothing is tracing the artwork at all. That is an element-level
        # failure, not a rough edge, and saying so beats returning a number.
        raise ValueError("no sewn outline within the measurement band")
    return float(near.mean()), float(near.std())


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None) -> dict:
    """Digitize `image_path` and measure how its sewn edges behave."""
    cfg = cfg or PipelineConfig()
    image_path = Path(image_path)

    result, plan = digitize(image_path, cfg)
    design = plan_to_design(plan)

    ours = stitch_coverage_field(design)
    art = art_ink_field(image_path, float(design["widthMM"]))
    _, O_f, A_f, dx, dy = register(ours, art)
    sewn, ink = O_f >= 0.5, A_f >= 0.5

    offset_mm, ragged_mm = boundary_spread(sewn, ink)
    haus_mm, sym_mean_mm = boundary_distance_mm(sewn, ink)
    p_sewn, p_art = perimeter_mm(sewn), perimeter_mm(ink)

    sat = ink_saturation(image_path)
    if sat > INK_SATURATION_MAX:
        refusal = f"ink mask saturates the frame, {sat:.0%}"
    elif ink_is_ambiguous(image_path):
        refusal = "ink ambiguous (knocked-out lettering)"
    else:
        refusal = None

    return {
        "fixture": image_path.name,
        "route": result.design_class,
        "ragged_mm": round(ragged_mm, 3),
        "offset_mm": round(offset_mm, 3),
        "perimeter_ratio": round(p_sewn / p_art, 3) if p_art else 0.0,
        "perimeter_sewn_mm": round(p_sewn, 1),
        "perimeter_art_mm": round(p_art, 1),
        "hausdorff_mm": round(haus_mm, 2),
        "sym_mean_mm": round(sym_mean_mm, 3),
        "shift_x_mm": round(dx, 1),
        "shift_y_mm": round(dy, 1),
        "refusal": refusal,
    }


def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Measure edge raggedness — the sawtoothing Kent raised on "
                    "eight of fourteen designs, which every area-based metric "
                    "in this repo is blind to.")
    ap.add_argument("images", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args(argv)

    names = list(FIXTURES) if args.all else args.images
    if not names:
        ap.error("give image paths or --all")

    rows = []
    paths = _resolve(names)
    for i, p in enumerate(paths, 1):
        if not p.exists():
            print(f"skip (missing): {p}", file=sys.stderr)
            continue
        print(f"[{i}/{len(paths)}] {p.name} ...", file=sys.stderr, flush=True)
        r = analyse(p)
        rows.append(r)
        print(f"[{i}/{len(paths)}] {p.name}: ragged {r['ragged_mm']} mm, "
              f"perimeter x{r['perimeter_ratio']}", file=sys.stderr, flush=True)

    if not rows:
        print("nothing analysed", file=sys.stderr)
        return 1

    head = (f"{'fixture':26s} {'route':12s} {'ragged':>8s} {'offset':>8s} "
            f"{'perim x':>8s} {'haus':>7s}")
    print(head)
    print("-" * len(head))
    for r in sorted(rows, key=lambda r: -r["ragged_mm"]):
        print(f"{r['fixture']:26s} {r['route']:12s} {r['ragged_mm']:>8.3f} "
              f"{r['offset_mm']:>8.3f} {r['perimeter_ratio']:>8.2f} "
              f"{r['hausdorff_mm']:>7.2f}"
              + ("   REFUSED" if r["refusal"] else ""))

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
