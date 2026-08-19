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
RUN = "run"            # the run tier: a rescued small shape's outline, bean technique
TRAVEL = "travel"
TIE = "tie"

# The machine command stream a plan compiles to — see `iter_machine_commands`.
CMD_STITCH = "stitch"
CMD_JUMP = "jump"
CMD_TRIM = "trim"
CMD_COLOR_CHANGE = "color_change"

# Two positions closer than this are the same needle position, and emitting a
# stitch between them would be a zero-length record the machine skips anyway.
# Only meaningful while the needle is sewing a continuous path — see the
# dedupe rule in `iter_machine_commands` for the three events that reset it.
SAME_POINT_MM = 0.01


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
    # The chart index this run's shade snapped to, for a blend-tier run that
    # carries its own per-shade thread (stage6_blend.blend_fill) — None is
    # legacy behaviour, "this run sews in the region's one thread" (every
    # non-blend run, and blend_fill's own tatami fallback). Stage 7's block
    # assembly partitions on this field: `shade_thread_index or
    # region.thread_index`, so an unset run collapses to today's single
    # region-thread block by construction.
    shade_thread_index: int | None = None

    @property
    def length_mm(self) -> float:
        return sum(
            math.dist(self.points[i - 1], self.points[i])
            for i in range(1, len(self.points))
        )


@dataclass
class StitchBlock:
    """Everything sewn between two machine functions, in sew order.

    A block was "everything sewn with one thread" until the specialty tiers
    arrived. It is still exactly that for ordinary artwork — but a block
    boundary is a color change in the file, and on a single head a color change
    IS a stop, so the boundary is really "the machine halts and a human does
    something". Appliqué and puff both sew consecutive blocks on ONE thread and
    depend on the stop between them. See `step`.
    """

    thread_index: int          # index into threads.CHART
    thread_number: str
    rgb: tuple[int, int, int]
    runs: list[StitchRun] = field(default_factory=list)
    # Operator step metadata, or None for an ordinary artwork block. A plain
    # JSON-shaped dict so it rides the service response with no schema work;
    # `stage6_applique.plan_steps` is the reader and documents the keys. The
    # load-bearing one is `action` — the human instruction at the stop that
    # ENDS this block. One color stop = one human action.
    step: dict | None = None

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
    # The cones this plan sews, ONE PER BLOCK, in sew order — `palette[i]`
    # describes `blocks[i]`, and `stats.thread_mm_by_color[i]` measures it.
    # Deliberately NOT `PipelineResult.palette`, which is the per-LAYER list
    # the review screen edits against: a layer can produce no block at all
    # (every region in it unstitched — see SHAPES_LEFT_UNSEWN) and a layer can
    # produce several (a specialty step's stop, or shapes that re-snapped onto
    # two threads), so the two lists have different lengths and different
    # meanings. Reading the layer list positionally against blocks is what
    # shipped `golf_hat`'s black block labelled "0020 Tangerine" until
    # 2026-08-14.
    palette: list[dict]
    warnings: list[dict] = field(default_factory=list)
    design_size_mm: tuple[float, float] = (0.0, 0.0)

    def iter_runs(self):
        for b in self.blocks:
            for r in b.runs:
                yield b, r

    @property
    def stats(self) -> PlanStats:
        # The accounting is counted off `iter_machine_commands` — the same
        # stream `export.plan_to_pattern` encodes — so the sheet and the file
        # tell the operator the same numbers by construction, not by two
        # hand-kept copies of one rule agreeing. `jumps` counts trim-less
        # moves only: a trim implies its jump, and the two are reported
        # disjointly (a cut is a "trim", a float is a "jump").
        count = trims = jumps = changes = 0
        prev_cmd: str | None = None
        for cmd, _pt in iter_machine_commands(self):
            if cmd == CMD_STITCH:
                count += 1
            elif cmd == CMD_TRIM:
                trims += 1
            elif cmd == CMD_COLOR_CHANGE:
                changes += 1
            elif cmd == CMD_JUMP and prev_cmd != CMD_TRIM:
                jumps += 1
            prev_cmd = cmd

        # Geometry is measured over the plan's own points, not the emitted
        # stream: a deduped penetration coincides with the one that was kept,
        # so it cannot move the bbox, and thread length is needle-path length.
        x0 = y0 = math.inf
        x1 = y1 = -math.inf
        by_color: list[float] = []
        for b in self.blocks:
            for r in b.runs:
                for x, y in r.points:
                    x0, y0 = min(x0, x), min(y0, y)
                    x1, y1 = max(x1, x), max(y1, y)
            by_color.append(b.length_mm * machine.THREAD_LENGTH_FACTOR)
        if not math.isfinite(x0):
            x0 = y0 = x1 = y1 = 0.0
        return PlanStats(
            stitch_count=count,
            color_changes=changes,
            trims=trims,
            jumps=jumps,
            bbox_mm=(x0, y0, x1, y1),
            size_mm=(x1 - x0, y1 - y0),
            thread_mm_by_color=by_color,
        )


def iter_machine_commands(plan: StitchPlan):
    """The command stream a plan compiles to — THE one trim/jump/stitch
    accounting, yielded as `(CMD_*, point-or-None)` in machine order.

    `export.plan_to_pattern` encodes exactly this stream into a pattern, and
    `StitchPlan.stats` counts it, so the worksheet and the file cannot drift:
    both are this generator consumed twice. They used to be two hand-kept
    copies of the same rule, which made the suite's "file holds what the plan
    promised" check a tautology — a dropped stitch dropped identically from
    both counts, and the comparison could not fail.

    The dedupe: two penetrations closer than SAME_POINT_MM are the same needle
    position and the second would be a zero-length record the machine skips
    anyway — but only while the needle is sewing a continuous path. The
    tracker is forgotten at every event that breaks the path, because the
    penetration after it is real however close it lands:

      * a JUMP moves the needle WITHOUT penetrating, so the stitch after one
        is the first penetration of the new path (bd9afad: carrying `last`
        across a jump deleted the anchor of `tie_run`'s five-point lock —
        run 0 point 0 of a block, distance 0.000000 on the appliqué
        benchmark — landing 4 of 5);
      * a TRIM cuts the thread, and the next penetration anchors a NEW one;
      * a block boundary is a machine stop — a color change, or an appliqué /
        puff step boundary on one thread (see `StitchBlock.step`) — and
        sewing restarts fresh after it, whatever flags the next run carries.

    A jump is only emitted once something has been sewn: the machine stands
    at the first run's start, so a leading JUMP would be a move to nowhere.
    """
    last: tuple[float, float] | None = None
    started = False
    for bi, block in enumerate(plan.blocks):
        if bi > 0:
            yield CMD_COLOR_CHANGE, None
            last = None
        for run in block.runs:
            if not run.points:
                continue
            if run.trim:
                yield CMD_TRIM, None
                last = None
            if run.jump and started:
                yield CMD_JUMP, run.points[0]
                last = None
            for pt in run.points:
                if last is not None and math.dist(last, pt) < SAME_POINT_MM:
                    continue
                yield CMD_STITCH, pt
                last = pt
                started = True
            last = run.points[-1]


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


def apply_ties(runs: list[StitchRun]) -> None:
    """Lock the thread wherever it starts and wherever it gets cut.

    Ties are folded into the run they protect rather than added as runs of
    their own, so nothing downstream has to special-case a two-millimetre run
    that is not really stitching.

    Moved here verbatim from stage 7 (where it ties every ordinary color
    block) so stage 6's appliqué fall-through can tie its plain-stitching
    block by the SAME rule rather than a second textual copy of it — the
    fallen piece is ordinary flat stitching, so §2.14's per-LAYER appliqué
    ties (`stage6_applique._tie_layers`) deliberately do not apply to it.
    """
    if not runs:
        return

    def tie_in(run: StitchRun) -> None:
        if len(run.points) < 2:
            return
        pts = tie_run(run.points[0], run.points[1]).points
        run.points = pts[:-1] + run.points

    def tie_off(run: StitchRun) -> None:
        if len(run.points) < 2:
            return
        pts = tie_run(run.points[-1], run.points[-2]).points
        run.points = run.points + pts[1:]

    # The first run needs a tie because the thread starts there, and a trimmed
    # run needs one because the thread starts there too. Ask both questions in
    # one pass: the first run of a color is always both, and tying it twice
    # doubles the lock into eight stitches of thread piled in one spot.
    for i, run in enumerate(runs):
        if i == 0 or run.trim:
            tie_in(run)
        if run.trim and i > 0:
            tie_off(runs[i - 1])
    tie_off(runs[-1])


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


def strip_ties(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """The points of a plan-level run with its folded-in lock stitches removed.

    Stage 7 splices `tie_run` bounces INTO the runs they protect (see
    `_apply_ties`), which is right for the machine and wrong for any instrument
    that reads a satin run's points as rail penetrations: the four appended
    points pair the last real penetration with a tie midpoint, and the "rail
    gap" measured across that seam is `final_cross - TIE_STITCH_MM` — a number
    about the column's width, not its density. Measured on the benchmark logo,
    the audit's headline gap was a 1.61 mm tie phantom over a 0.86 mm truth,
    an instrument error found by adversarial review of the emitter change.

    Detection is exact, not heuristic: a tie is a bounce between exactly two
    coordinates (`[at, inner, at, inner]` leading, `[inner, at, inner, at]`
    trailing), so points two apart are EQUAL. Real satin penetrations are
    never equal two apart — rails advance a spacing per station and the
    emitter drops coincident crosses.
    """
    pts = list(points)
    while len(pts) >= 5 and pts[0] == pts[2] and pts[1] == pts[3]:
        pts = pts[4:]
    while len(pts) >= 5 and pts[-1] == pts[-3] and pts[-2] == pts[-4]:
        pts = pts[:-4]
    return pts
