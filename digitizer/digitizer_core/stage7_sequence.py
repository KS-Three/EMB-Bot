"""Stage 7 — sew order within a color, lock stitches, and the jump/trim call.

Stage 5 fixed which thread goes first. What is left is the order shapes are
sewn inside one thread, and the housekeeping that decides whether a finished
design runs clean on a machine or produces a garment covered in loose ends:

- **Order within a color** is nearest-neighbour on the actual stitch start
  points, not centroids: the distance that matters is the one the needle
  travels, and a long thin shape's centroid can sit nowhere near where its
  stitching begins.
- **Ties.** A lock stitch goes in wherever the thread starts and wherever it is
  about to be cut. Without them the first stitches pull out the moment the
  garment is worn, which is the kind of defect that surfaces after delivery.
- **Jump or trim.** A short hop stays a jump; anything past the fabric preset's
  trim distance is cut, because a float long enough to catch a finger is a
  float someone has to remove with scissors.
"""
from __future__ import annotations

import math

from . import stitches
from .config import PipelineConfig
from .fabrics import Fabric
from .machine import FILL_ROW_MM, FILL_STITCH_MM, SATIN_MAX_WIDTH_MM, TINY_STITCH_MM
from .stage5_overlap import PlannedRegion
from .stage6_fill import stitch_shape
from .stage6_satin import is_satin_candidate, satin_shape
from .stitches import StitchBlock, StitchRun, tie_run
from .threads import CHART
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

        # Stitches first, order second: a shape's runs do not depend on when it
        # is sewn, so generating them up front lets the ordering use real start
        # points instead of guessing from geometry.
        made: list[tuple[PlannedRegion, list[StitchRun]]] = []
        for p in group:
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
                )
                # A ribbon the skeleton could not resolve still has to sew:
                # fall through to fill rather than silently dropping artwork.
                if report["empty"]:
                    runs, report = stitch_shape(
                        p.polygon, p.shape_id, angle_deg=cfg.fill_angle_deg,
                        row_mm=row_mm, stitch_mm=stitch_mm,
                        underlay_style=underlay_style, trim_at_mm=trim_at,
                    )
                    thin += int(report["too_thin"])
            else:
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=cfg.fill_angle_deg,
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=underlay_style,
                    trim_at_mm=trim_at,
                )
                thin += int(report["too_thin"])
            jumps += report["jumps"]
            if report["empty"] or not runs:
                empty += 1
                continue
            made.append((p, runs))
        if not made:
            continue

        # Nearest-neighbour from wherever the previous color left the needle.
        remaining = list(range(len(made)))
        remaining.sort(key=lambda i: (made[i][1][0].points[0][1], made[i][1][0].points[0][0]))
        ordered: list[StitchRun] = []
        while remaining:
            if cursor is None:
                pick = remaining[0]
            else:
                pick = min(remaining, key=lambda i: (
                    round(math.dist(cursor, made[i][1][0].points[0]), 6), i))
            p, runs = made[pick]
            remaining.remove(pick)
            if cursor is not None:
                d = math.dist(cursor, runs[0].points[0])
                if d >= TINY_STITCH_MM:
                    runs[0].jump = True
                    runs[0].trim = d > trim_at
            ordered.extend(runs)
            cursor = runs[-1].points[-1]

        # The needle always lifts into a new color, and the thread is always cut
        # coming out of the previous one.
        ordered[0].jump = True
        ordered[0].trim = True
        _apply_ties(ordered)

        thread = CHART[group[0].region.thread_index]
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
