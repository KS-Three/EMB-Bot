"""`cfg.lettering_columns_slot_guard` (2026-10-27, built OFF): a Column-lane
letter walked twice, kept the cheaper way.

`columns._span_graph` joins two column ends into one walk node when they lie
within `merge_r` (1.3 W + 0.3 + the pull, 5 mm on Becker's 3.3 mm strokes).
That is wider than an E's slot or an M's notch, so the top arm's root and the
middle arm's root became one node across the slot. The walk then treated them
as one place, the needle could not, and the hop between them left the letter:
step 4's strict route was a 9-47 mm detour, mostly not under later satin, so
it trimmed. Six of the eight trims inside a letter on seven paired jobs
(main 8341d1f7, `docs/satin-split-cuts-2026-10-27.md`) are that; the pro
links all six needle-down under satin he sews later.

The guard is the corner fold's own (`within`): two ends are one node only
when the letter, grown `SLOT_GUARD_GROW_MM`, covers the line between them.
On every letter it removed all eight, but step 4 already sews a hop with up
to `allow` = max(trim_at, 2 W) of it on finished satin. On four letters the
new walk's leg changes crossed satin just sewn (travel_cover 48.1 -> 58.3 mm
over the changed letters), and Fremont's job trims rose two.

So each letter is walked both ways (`pick`) and keeps the guarded walk only
where it is no worse on both counts below and better on one (`walk_cost`).
Geometry, not cloth: no constant here is a physical one (gate 1).
"""
from __future__ import annotations

import copy

from shapely.geometry import LineString
from shapely.ops import unary_union

from . import stitches
from .stitches import StitchRun

#: the letter grown this much is what the guard asks to cover the line between
#: two ends: float slack on the artwork's edge, never the pull (the corner
#: fold's `0.1 + pull` closes Gaulke's 1 mm slot at a 0.4 mm pull)
SLOT_GUARD_GROW_MM = 0.1
#: a satin run's needle-to-needle stitches widened this much each side read as
#: covered ground: the zigzag's 0.4 mm spacing closes, so a column reads whole
COVER_HALF_MM = 0.25
#: two walks this close in on-top travel are a tie, not a gain
TIE_MM = 0.05


def walk_cost(runs: list[StitchRun]) -> tuple[int, float]:
    """-> (cuts, on top mm) of one letter's walk. `cuts`: runs after the
    first that carry a trim (the first run's lift is the hop INTO the letter,
    stage 7's). `on top`: travel length no satin this letter sews after it
    covers -- thread left on finished work or bare fabric."""
    cuts = sum(1 for r in runs[1:] if r.trim)
    top = 0.0
    for k, r in enumerate(runs):
        if r.kind != stitches.TRAVEL or len(r.points) < 2:
            continue
        later = [LineString(s.points).buffer(COVER_HALF_MM) for s in runs[k + 1:]
                 if s.kind == stitches.SATIN and len(s.points) >= 2]
        line = LineString(r.points)
        top += line.difference(unary_union(later)).length if later else line.length
    return cuts, top


def pick(column_runs, columns, poly, shape_id: str, **kw):
    """`column_runs` both ways -> the (runs, report) to sew: today's walk,
    unless the guarded one (`slot_guard=True`) cuts no more, leaves no more
    travel on top (within `TIE_MM`) and is better on one of the two."""
    spare = copy.deepcopy(columns)
    today = column_runs(columns, poly, shape_id, **kw)
    guarded = column_runs(spare, poly, shape_id, slot_guard=True, **kw)
    if not today[0] or not guarded[0]:
        return today
    (ca, ta), (cb, tb) = walk_cost(today[0]), walk_cost(guarded[0])
    if cb <= ca and tb <= ta + TIE_MM and (cb < ca or tb < ta - TIE_MM):
        guarded[1]["slot_guard"] = 1
        return guarded
    return today
