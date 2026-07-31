"""The stitch-level contract: what the planner produces and what export consumes.

Coordinates keep stage 4's convention exactly — **millimetres, floats, origin at
the artwork bbox center, y-axis DOWN**. Nothing here converts units or flips an
axis; the DST writer converts to 0.1 mm units and the browser adapter (build
step 10) owns the y flip, so there is exactly one place each can go wrong.

The shape of the plan mirrors how a machine actually reads a file: a sequence of
blocks, one per thread change, each a sequence of runs. A run is a needle-down
path — the machine sews from point to point. Between runs the needle may lift
(`jump`) and the thread may be cut (`trim`), and those two facts are properties
of the run that FOLLOWS the move, because that is the run whose first stitch the
machine has to get to.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import machine

# Run kinds. Ordering within a shape is always underlay -> fill, with travel
# and tie runs interleaved as routing requires.
UNDERLAY = "underlay"
FILL = "fill"
SATIN = "satin"        # reserved for build step 4
BORDER = "border"      # a closed outline circuit, sewn as a satin column
BEAN = "bean"          # the light outline tier: a triple run on the same ring
TRAVEL = "travel"
TIE = "tie"


@dataclass
class StitchRun:
    """One needle-down path. `points` are consecutive stitch positions in mm."""

    points: list[tuple[float, float]]
    kind: str = FILL
    # True when the machine must lift the needle to reach points[0].
    jump: bool = False
    # True when the thread is cut before this run (implies jump).
    trim: bool = False
    shape_id: str = ""

    @property
    def length_mm(self) -> float:
        return sum(
            math.dist(self.points[i - 1], self.points[i])
            for i in range(1, len(self.points))
        )


@dataclass
class StitchBlock:
    """Everything sewn with one thread, in sew order."""

    thread_index: int          # index into threads.CHART
    thread_number: str
    rgb: tuple[int, int, int]
    runs: list[StitchRun] = field(default_factory=list)

    @property
    def stitch_count(self) -> int:
        return sum(len(r.points) for r in self.runs)

    @property
    def length_mm(self) -> float:
        return sum(r.length_mm for r in self.runs)


@dataclass
class PlanStats:
    stitch_count: int
    color_changes: int
    trims: int
    jumps: int
    bbox_mm: tuple[float, float, float, float]   # x0, y0, x1, y1
    size_mm: tuple[float, float]
    thread_mm_by_color: list[float]

    @property
    def thread_m_total(self) -> float:
        return sum(self.thread_mm_by_color) / 1000.0


@dataclass
class StitchPlan:
    blocks: list[StitchBlock]
    palette: list[dict]
    warnings: list[dict] = field(default_factory=list)
    design_size_mm: tuple[float, float] = (0.0, 0.0)

    def iter_runs(self):
        for b in self.blocks:
            for r in b.runs:
                yield b, r

    @property
    def stats(self) -> PlanStats:
        x0 = y0 = math.inf
        x1 = y1 = -math.inf
        count = trims = jumps = 0
        by_color: list[float] = []
        prev: tuple[float, float] | None = None
        for b in self.blocks:
            for r in b.runs:
                trims += int(r.trim)
                jumps += int(r.jump and not r.trim)
                for x, y in r.points:
                    # Count what the machine sews: the DST writer skips a point
                    # coincident with the previous one (two runs can share an
                    # endpoint exactly), and the operator-facing count must
                    # match the file's.
                    if prev is None or math.dist((x, y), prev) >= 0.01:
                        count += 1
                    prev = (x, y)
                    x0, y0 = min(x0, x), min(y0, y)
                    x1, y1 = max(x1, x), max(y1, y)
            by_color.append(b.length_mm * machine.THREAD_LENGTH_FACTOR)
        if not math.isfinite(x0):
            x0 = y0 = x1 = y1 = 0.0
        return PlanStats(
            stitch_count=count,
            color_changes=max(0, len(self.blocks) - 1),
            trims=trims,
            jumps=jumps,
            bbox_mm=(x0, y0, x1, y1),
            size_mm=(x1 - x0, y1 - y0),
            thread_mm_by_color=by_color,
        )


def split_long_moves(points: list[tuple[float, float]],
                     max_mm: float = machine.MAX_STITCH_MM) -> list[tuple[float, float]]:
    """Subdivide any step longer than the machine can encode.

    Applied to needle-DOWN paths only. A jump between runs is split by the
    exporter instead, since splitting it here would sew it.
    """
    if len(points) < 2:
        return list(points)
    out = [points[0]]
    for prev, cur in zip(points, points[1:]):
        d = math.dist(prev, cur)
        if d > max_mm:
            steps = math.ceil(d / max_mm)
            for s in range(1, steps):
                t = s / steps
                out.append((prev[0] + (cur[0] - prev[0]) * t,
                            prev[1] + (cur[1] - prev[1]) * t))
        out.append(cur)
    return out


# There is deliberately no "drop stitches shorter than X" pass. It sounds like
# obvious hygiene and it is not: the turn between two fill rows is exactly one
# row spacing (0.4 mm at standard density) and its endpoints are the
# penetrations that land on the shape's edge. Filtering them pulls the edge in
# and leaves it ragged — measured on the first smoke run. Stitch length is
# controlled where the geometry is generated, in `_row_points`, instead.


def tie_run(at: tuple[float, float], toward: tuple[float, float], kind: str = TIE,
            shape_id: str = "") -> StitchRun:
    """A lock stitch at `at`, laid along the path toward `toward`.

    The legs run back and forth between `at` and a point INTO the shape, and
    the run both starts and ends at `at`. Never past it: a tie that overshoots
    puts a whisker of thread outside the shape's edge, which on a finished
    garment reads as a stray stitch someone has to trim off. Measured on the
    first smoke run, where tie-offs put the design's bounding box 0.8 mm
    outside its own artwork.
    """
    dx, dy = toward[0] - at[0], toward[1] - at[1]
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return StitchRun(points=[at], kind=kind, shape_id=shape_id)
    # Never reach past the point being tied toward, on a path shorter than a leg.
    leg = min(machine.TIE_STITCH_MM, d)
    ux, uy = dx / d * leg, dy / d * leg
    inner = (at[0] + ux, at[1] + uy)
    pts = [at]
    for i in range(machine.TIE_STITCHES):
        pts.append(inner if i % 2 == 0 else at)
    if pts[-1] != at:
        pts.append(at)
    return StitchRun(points=pts, kind=kind, shape_id=shape_id)
