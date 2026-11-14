"""Like shapes decided once per group (built OFF 2026-11-13): the run tier's
area floor under `cfg.group_consistent_tier`, the art-outline body test under
`cfg.group_consistent_outline_body`.

Kent pins one fault in many clothes: like things sewn unlike ("This stitch is
different than the AH RA", "the only letter that is thinly stitched"). A
person digitizing decides once for a word; the engine decides per shape,
against a threshold, so two like letters that straddle it come out different.

Census on main 7ad9c124 (`docs/group-consistency-2026-11-13.md`): of eleven
such notes, two are exactly that straddle, each on a different threshold.

* AHORA (`lt_ahora`, 80 mm): the sewn pink field reads as an art outline
  round its letters, and `art_outline`'s body test (`stroke >=
  OUTLINE_BODY_RATIO x band`, 1.0) takes AH (1.059) and RA (1.023) as
  bodies -- fill under a pink loop -- and leaves O (0.612) and ! (0.456) to
  the classifier, which sews them satin. The outline census saw no pro body
  between 0.87 and 1.34 (`machine.OUTLINE_BODY_RATIO`'s comment).
* K-Line's subline (`lt_k_line`, 80 mm): the run tier's area floor
  (`cfg.min_detail_mm`^2, 2.25 mm^2) sews 17 of its 2.5 mm letters (1.13-2.25
  mm^2) as bean outlines and 6 (2.54-3.07 mm^2) satin, in one line of one
  thread.

The rule, the same for both:

GROUP    like shapes on one line (`like_lines`): one thread, heights within
         `lettering_thread.STRAY_HEIGHT_RATIO`, sharing
         `STRAY_MIN_OVERLAP` of the shorter height, within `STRAY_MAX_GAP_H`
         heights of a member -- the stray-letter rule's own line test -- and at
         least `textcluster.MIN_CLUSTER_MEMBERS` of them. No new constant.
DECIDED  a member whose measure sits more than `MARGIN` times off the
         threshold, either way, is evidence; one inside the band is not.
VERDICT  the decided members' side when they all agree; the median measure's
         side when no member is decided; no verdict when the decided disagree
         (a genuinely mixed group keeps its shapes' own calls).
FOLLOW   an undecided member takes the verdict, unless the caller's guard says
         its shape cannot take that construction (a satin the classifier
         refuses, a fill body under the fill floor).

Pure: reads geometry and thread indices, decides nothing about cloth. Off,
nothing calls it.
"""
from __future__ import annotations

import statistics
from typing import Callable, Iterable

from .lettering_thread import STRAY_HEIGHT_RATIO, STRAY_MAX_GAP_H, STRAY_MIN_OVERLAP
from .textcluster import MIN_CLUSTER_MEMBERS

#: A member within this factor of the threshold, either side, is not evidence
#: for its group (`DECIDED` above). The outline census's own empty band is
#: 0.87-1.34 round 1.0, inside it; K-Line's six satin letters sit 1.13-1.36 x
#: the floor and its two smallest bean letters 0.50 x. A grouping margin, not
#: a cloth value (ROADMAP gate 1: no machine settles it); fitted on the census
#: above and nothing else -- a CANDIDATE.
MARGIN = 1.5


def _line_mates(a, b) -> bool:
    """`lettering_thread._on_its_line`, both ways round: like heights, one
    band, near each other."""
    x0, y0, x1, y1 = a.polygon.bounds
    u0, v0, u1, v1 = b.polygon.bounds
    h, k = y1 - y0, v1 - v0
    if h <= 0 or k <= 0 or min(h, k) / max(h, k) < STRAY_HEIGHT_RATIO:
        return False
    if min(y1, v1) - max(y0, v0) < STRAY_MIN_OVERLAP * min(h, k):
        return False
    return a.polygon.distance(b.polygon) <= STRAY_MAX_GAP_H * max(h, k)


def like_lines(regions: Iterable, *, min_members: int = MIN_CLUSTER_MEMBERS) -> list[list]:
    """Groups of like shapes on one line: the connected components of
    `_line_mates` within each thread, in input order, those of at least
    `min_members`. A shape with no polygon is never a member."""
    regs = [r for r in regions
            if r.polygon is not None and not r.polygon.is_empty]
    parent = list(range(len(regs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            if regs[i].thread_index == regs[j].thread_index and _line_mates(regs[i], regs[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    by: dict[int, list] = {}
    for i, r in enumerate(regs):
        by.setdefault(find(i), []).append(r)
    return [g for _k, g in sorted(by.items()) if len(g) >= min_members]


def decided(measure: float, threshold: float, margin: float = MARGIN) -> bool:
    """Is this reading evidence -- more than `margin` x off the threshold?"""
    if threshold <= 0:
        return True
    if measure <= 0:
        return True
    r = measure / threshold
    return r > margin or r < 1.0 / margin


def group_verdict(measures: list[float], threshold: float,
                  margin: float = MARGIN) -> bool | None:
    """The group's side of `threshold` (True: at or over it), or None.

    The decided members' side when they agree; with none decided, the median
    measure's; when the decided disagree, None."""
    if not measures:
        return None
    sides = {m >= threshold for m in measures if decided(m, threshold, margin)}
    if len(sides) == 1:
        return sides.pop()
    if sides:
        return None
    return statistics.median(measures) >= threshold


def follow(group: list, measure: Callable, threshold: float, *,
           can_take: Callable[[object, bool], bool] | None = None,
           margin: float = MARGIN) -> dict[str, bool]:
    """-> {shape_id: side} for every UNDECIDED member whose own side differs
    from the group's verdict and whose shape can take the verdict's side
    (`can_take(region, side)`, default yes). Empty when there is no verdict."""
    ms = [float(measure(r)) for r in group]
    verdict = group_verdict(ms, threshold, margin)
    if verdict is None:
        return {}
    out: dict[str, bool] = {}
    for r, m in zip(group, ms):
        if decided(m, threshold, margin) or (m >= threshold) == verdict:
            continue
        if can_take is not None and not can_take(r, verdict):
            continue
        out[r.shape_id] = verdict
    return out


def run_floor_overrides(regions: Iterable, floor_mm2: float, *,
                        can_leave_run: Callable[[object], bool]) -> dict[str, bool]:
    """The run tier's area floor, decided per line (K-Line's subline).

    -> {shape_id: under the floor?} for the members whose answer the group
    changes. A member moved ONTO the run tier always can (an outline run sews
    any shape); one moved OFF it only when `can_leave_run(region)` -- the
    ladder below will give it satin -- else it stays a run."""
    out: dict[str, bool] = {}
    for group in like_lines(regions):
        moved = follow(group, lambda r: r.polygon.area, floor_mm2,
                       can_take=lambda r, over: (not over) or can_leave_run(r))
        out.update({sid: not over for sid, over in moved.items()})
    return out


def outline_body_decider(min_body_mm: float):
    """A `find_art_outlines(group_decide=...)` hook: the art-outline body test
    decided per line of like candidates within one outline (AHORA).

    Each candidate is (body, hole, band, stroke); the measure is stroke / band
    against `machine.OUTLINE_BODY_RATIO`. A candidate the group makes a body
    must be at least `min_body_mm` across on average (2 x area / perimeter):
    it will be filled. -> the kept (body, hole) pairs, candidate order."""
    from . import machine

    def ratio(band: float, stroke: float) -> float:
        return stroke / band if band > 0 else float("inf")

    def decide(_holder, cands: list) -> list:
        own = {c[0].shape_id: ratio(c[2], c[3]) >= machine.OUTLINE_BODY_RATIO for c in cands}
        meas = {c[0].shape_id: ratio(c[2], c[3]) for c in cands}
        stroke = {c[0].shape_id: c[3] for c in cands}
        side = dict(own)
        for group in like_lines([c[0] for c in cands]):
            side.update(follow(group, lambda r: meas[r.shape_id], machine.OUTLINE_BODY_RATIO,
                               can_take=lambda r, body: (not body) or stroke[r.shape_id] >= min_body_mm))
        return [(c[0], c[1]) for c in cands if side[c[0].shape_id]]

    return decide
