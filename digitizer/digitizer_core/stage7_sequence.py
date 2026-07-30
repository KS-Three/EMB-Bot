"""Stage 7 — sew order within a color, lock stitches, and the jump/trim call.

Stage 5 fixed which thread goes first. What is left is the order shapes are
sewn inside one thread, and the housekeeping that decides whether a finished
design runs clean on a machine or produces a garment covered in loose ends:

- **Order within a color** is nearest-neighbour on the sewing geometry, not on
  centroids: the distance that matters is the one the needle travels, and a
  long thin shape's centroid can sit nowhere near the part of it the needle
  can actually reach. Order is settled BEFORE the stitches exist, because
  where a shape starts now depends on where the needle already is — stage 6
  takes `start_near` and enters the shape there. Generating first and ordering
  on the result meant every shape began at its own top-left corner and the
  needle was sent back across the design to get there.
- **Ties.** A lock stitch goes in wherever the thread starts and wherever it is
  about to be cut. Without them the first stitches pull out the moment the
  garment is worn, which is the kind of defect that surfaces after delivery.
- **Jump or trim.** A short hop stays a jump; anything past the fabric preset's
  trim distance is cut, because a float long enough to catch a finger is a
  float someone has to remove with scissors.
"""
from __future__ import annotations

import math

from shapely.geometry import Point
from shapely.ops import unary_union

from . import stitches
from .config import PipelineConfig
from .fabrics import Fabric
from .machine import FILL_ROW_MM, FILL_STITCH_MM, SATIN_MAX_WIDTH_MM, TINY_STITCH_MM
from .stage5_overlap import PlannedRegion
from .stage6_fill import stitch_shape
from .stage6_satin import is_satin_candidate, satin_shape
from .stitches import StitchBlock, StitchRun, tie_run
from .threads import chart_for
from .warnings_codes import LONG_JUMPS_TRIMMED, SHAPE_NOT_STITCHED, SHAPE_TOO_THIN_TO_FILL, warn


def _apply_ties(runs: list[StitchRun]) -> None:
    """Lock the thread wherever it starts and wherever it gets cut.

    Ties are folded into the run they protect rather than added as runs of
    their own, so nothing downstream has to special-case a two-millimetre run
    that is not really stitching.
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


def sequence(
    planned: list[PlannedRegion], fabric: Fabric, cfg: PipelineConfig
) -> tuple[list[StitchBlock], list[dict]]:
    """-> (blocks in sew order, warnings)."""
    row_mm = (cfg.fill_row_mm or FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    stitch_mm = cfg.fill_stitch_mm or FILL_STITCH_MM
    underlay_style = (cfg.underlay_style or fabric.fill_underlay) if cfg.underlay else "none"
    satin_underlay = fabric.satin_underlay if cfg.underlay else "none"
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    trim_at = fabric.trim_at_mm

    thin = empty = jumps = 0
    blocks: list[StitchBlock] = []
    cursor: tuple[float, float] | None = None

    for sew_index in sorted({p.sew_index for p in planned}):
        group = [p for p in planned if p.sew_index == sew_index]

        def stitch_one(p: PlannedRegion, entry: tuple[float, float] | None):
            # Satin or fill is decided per shape, not per design: one logo
            # routinely holds both a big filled emblem and thin satin lettering.
            # Classified on the ARTWORK polygon, not the stage-5 grown one —
            # otherwise heavy fabric (0.6 mm pull comp widens a ribbon 1.2 mm)
            # flips the same artwork from satin to fill, and a logo would sew
            # differently structured on a towel than on a polo.
            if cfg.satin and is_satin_candidate(p.region.polygon, satin_max):
                runs, report = satin_shape(
                    p.polygon,
                    p.shape_id,
                    underlay_style=satin_underlay,
                    trim_at_mm=trim_at,
                    start_near=entry,
                )
                # A ribbon the skeleton could not resolve still has to sew:
                # fall through to fill rather than silently dropping artwork.
                if not report["empty"]:
                    return runs, report, False
            runs, report = stitch_shape(
                p.polygon,
                p.shape_id,
                angle_deg=cfg.fill_angle_deg,
                row_mm=row_mm,
                stitch_mm=stitch_mm,
                underlay_style=underlay_style,
                trim_at_mm=trim_at,
                start_near=entry,
            )
            return runs, report, True

        # Order first, stitches second. A shape's path now depends on where the
        # needle is when it starts, so the order has to be settled before the
        # geometry exists — and the honest proxy for "how far must the needle
        # fly" is the distance to the shape itself, not to one arbitrary point
        # on it. Picking on a start point the shape had not chosen yet is what
        # sent the needle to every shape's top-left corner: on eight filled
        # letters that was 112 mm of thread flown and nine trims.
        rank = {i: r for r, i in enumerate(sorted(
            range(len(group)),
            key=lambda i: (group[i].polygon.bounds[1], group[i].polygon.bounds[0],
                           group[i].shape_id)))}
        # Where a color starts when nothing is sewn yet. Nearest-neighbour from
        # a shape in the MIDDLE of a group strands the far end and pays for it
        # with one long haul at the finish — on eight letters of a word, a
        # 42 mm flight back across the whole design. Starting at an extreme of
        # the group means the sweep never has to come back.
        centre = unary_union([p.polygon for p in group]).centroid
        far = {i: round(group[i].polygon.centroid.distance(centre), 6)
               for i in range(len(group))}

        remaining = list(range(len(group)))
        ordered: list[StitchRun] = []
        while remaining:
            if cursor is None:
                pick = min(remaining, key=lambda i: (-far[i], rank[i]))
            else:
                here = Point(cursor)
                pick = min(remaining, key=lambda i: (
                    round(group[i].polygon.distance(here), 6), rank[i]))
            p = group[pick]
            remaining.remove(pick)
            runs, report, filled = stitch_one(p, cursor)
            thin += int(filled and report["too_thin"])
            jumps += report["jumps"]
            if report["empty"] or not runs:
                empty += 1
                continue
            if cursor is not None:
                d = math.dist(cursor, runs[0].points[0])
                if d >= TINY_STITCH_MM:
                    runs[0].jump = True
                    runs[0].trim = d > trim_at
            ordered.extend(runs)
            cursor = runs[-1].points[-1]
        if not ordered:
            continue

        # The needle always lifts into a new color, and the thread is always cut
        # coming out of the previous one.
        ordered[0].jump = True
        ordered[0].trim = True
        _apply_ties(ordered)

        thread = chart_for(cfg)[group[0].region.thread_index]
        blocks.append(
            StitchBlock(
                thread_index=group[0].region.thread_index,
                thread_number=thread.number,
                rgb=tuple(thread.rgb),
                runs=ordered,
            )
        )
        cursor = ordered[-1].points[-1]

    warnings: list[dict] = []
    if thin:
        warnings.append(
            warn(
                SHAPE_TOO_THIN_TO_FILL,
                f"{thin} shape{'s are' if thin != 1 else ' is'} too narrow to "
                "fill cleanly but not stroke-like enough for satin — worth a "
                "look on the review screen.",
                count=thin,
            )
        )
    if empty:
        warnings.append(
            warn(
                SHAPE_NOT_STITCHED,
                f"{empty} shape{'s' if empty != 1 else ''} produced no stitches "
                "and were left out.",
                count=empty,
            )
        )
    if jumps:
        warnings.append(
            warn(
                LONG_JUMPS_TRIMMED,
                f"The thread had to be lifted {jumps} time"
                f"{'s' if jumps != 1 else ''} inside a shape.",
                count=jumps,
            )
        )
    return blocks, warnings
