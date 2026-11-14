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
         least `textcluster.MIN_CLUSTER_MEMBERS` of them; a two-piece glyph
         joins a line its pieces span (`STACK_BAND_TOL`).
DECIDED  a member whose measure sits more than `MARGIN` times off the
         threshold, either way, is evidence; one inside the band is not.
VERDICT  the decided members' side when they all agree; the median measure's
         side when no member is decided; no verdict when the decided disagree
         (a genuinely mixed group keeps its shapes' own calls).
FOLLOW   an undecided member takes the verdict, unless the caller's guard says
         its shape cannot take that construction (a satin the classifier
         refuses, a fill body under the fill floor).

That is the run floor's rule. The outline body is decided by INK instead
(`outline_side`): the side with more area, or, within `MARGIN`, the side
with the wider strokes, and every member follows -- AHORA's odd ones, the
O and the !, were decided readings (0.61, 0.46) on the minority of ink.

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


#: A glyph in two stacked pieces (the ! and its dot, an i) joins a line its
#: pieces span together: the union's top and bottom each within this share of
#: the line's height of the line's own (median) top and bottom. AHORA's ! bar
#: is 10.25 mm against its line's 14.0 (0.73, under `STRAY_HEIGHT_RATIO`);
#: bar and dot together are -7.02..6.98 against the line's -7.03..6.98.
STACK_BAND_TOL = 0.1
#: ... the pieces apart by at most this share of the line's height, sharing
#: half the narrower's width.
STACK_GAP_MAX = 0.5


def _stacked(a, b) -> bool:
    """Two boxes one above the other: half the narrower's width shared, no
    vertical overlap (a counter or a gear's centre sits INSIDE, not on)."""
    if min(a[2], b[2]) - max(a[0], b[0]) < 0.5 * min(a[2] - a[0], b[2] - b[0]):
        return False
    return max(b[1] - a[3], a[1] - b[3]) >= 0


def _adopt_stacked(regs: list, groups: list[list[int]]) -> None:
    """Add to a line (index lists, edited in place) each pair of UNGROUPED
    same-thread pieces stacked on one another whose union spans the line's
    band (`STACK_BAND_TOL`), close enough to it (`STRAY_MAX_GAP_H`). Pieces a
    line already holds never move: MFab's small lower words sit under its big
    letters, but those letters are a line of their own."""
    import statistics as st
    grouped = {i for g in groups for i in g}
    free = [i for i in range(len(regs)) if i not in grouped]
    for x in free:
        for y in free:
            if y <= x or regs[x].thread_index != regs[y].thread_index:
                continue
            a, b = regs[x].polygon.bounds, regs[y].polygon.bounds
            if not _stacked(a, b):
                continue
            u = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
            for g in groups:
                if regs[g[0]].thread_index != regs[x].thread_index:
                    continue
                top = st.median(regs[i].polygon.bounds[1] for i in g)
                bot = st.median(regs[i].polygon.bounds[3] for i in g)
                H = bot - top
                if H <= 0 or abs(u[1] - top) > STACK_BAND_TOL * H or abs(u[3] - bot) > STACK_BAND_TOL * H:
                    continue
                gap = max(b[1] - a[3], a[1] - b[3])
                if gap > STACK_GAP_MAX * H:
                    continue
                near = min(regs[i].polygon.distance(regs[k].polygon) for i in g for k in (x, y))
                if near > STRAY_MAX_GAP_H * H:
                    continue
                g.extend([x, y])
                break


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
    for i in range(len(regs)):
        by.setdefault(find(i), []).append(i)
    groups = [g for _k, g in sorted(by.items()) if len(g) >= min_members]
    _adopt_stacked(regs, groups)
    return [[regs[i] for i in sorted(g)] for g in groups]


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


def outline_side(members: list, own: dict, stroke: dict, *,
                 close: float = MARGIN) -> bool | None:
    """The construction a line of like outline candidates takes: True (a body,
    filled under the outline's loop) or False (its own ladder), None when
    every member already agrees.

    Decided by INK, not by region count: AHORA's AH and RA are four letters in
    two fused shapes against O and ! (two letters, two regions), and Kent's
    pins sit on the O and the ! ("This stitch is different than the AH RA") --
    the odd ones are the minority of ink, 121 against 435 mm^2. The side with
    more area wins; when the two are within `close` of each other, the side
    whose strokes are wider (area-weighted mean of 2 x area / perimeter) wins,
    because a wide stroke forced into satin is the lumpy case (AHORA's AH as
    split satin: an A in pieces at three angles, a blocky bar)."""
    a_in = sum(r.polygon.area for r in members if own[r.shape_id])
    a_out = sum(r.polygon.area for r in members if not own[r.shape_id])
    if a_in <= 0 or a_out <= 0:
        return None
    if max(a_in, a_out) > close * min(a_in, a_out):
        return a_in > a_out

    def wide(side: bool) -> float:
        ms = [r for r in members if own[r.shape_id] == side]
        return sum(stroke[r.shape_id] * r.polygon.area for r in ms) / sum(r.polygon.area for r in ms)
    return wide(True) >= wide(False)


def outline_body_decider(min_body_mm: float):
    """A `find_art_outlines(group_decide=...)` hook: the art-outline body test
    decided per line of like candidates within one outline (AHORA), by
    `outline_side`, every member following -- a member's own reading is no
    exemption here, since the ink side is the evidence.

    Each candidate is (body, hole, band, stroke); a member's own side is
    stroke / band against `machine.OUTLINE_BODY_RATIO`. A candidate the group
    makes a body must be at least `min_body_mm` across on average (2 x area /
    perimeter): it will be filled. -> the kept (body, hole) pairs, candidate
    order."""
    from . import machine

    def ratio(band: float, stroke: float) -> float:
        return stroke / band if band > 0 else float("inf")

    def decide(_holder, cands: list) -> list:
        own = {c[0].shape_id: ratio(c[2], c[3]) >= machine.OUTLINE_BODY_RATIO for c in cands}
        stroke = {c[0].shape_id: c[3] for c in cands}
        side = dict(own)
        for group in like_lines([c[0] for c in cands]):
            verdict = outline_side(group, own, stroke)
            if verdict is None:
                continue
            for r in group:
                if own[r.shape_id] != verdict and ((not verdict) or stroke[r.shape_id] >= min_body_mm):
                    side[r.shape_id] = verdict
        return [(c[0], c[1]) for c in cands if side[c[0].shape_id]]

    return decide


# --- One angle per group of like shapes (`cfg.group_consistent_fill_angle`) ---
#
# Kent: "feet are differnt colors, they should be the same" (gradient_mascot,
# one spool, fills at 39 and 134 deg) and "right leg infill doesn't match left
# leg" (flat_emoji_icon, one spool, 11 and 180 deg): two row directions on one
# thread read as two shades. The flag's 50 congruent stars fill at 8 angles
# (36-160 deg) and To a T machine's 4 congruent rule lines satin at 64-85 deg
# (`regular-structure` census, 2026-11-13). Each shape picks its own angle
# (`stage6_fill.best_fill_angle_deg`, the satin tier's per-stroke tangent), so
# like shapes differ. ONE angle per group: the biggest member's own, and every
# member takes it -- not mirrored for a mirrored pair, by Kent's note.
#
# GROUP: the `regular_structure` tag `meta["congruent_group"]` when present
# (its `id`; the angle is then taken RELATIVE to each member's own
# `angle_deg`, so a rotated copy sews the same way round itself), else
# `like_shapes`: one thread, areas within `LIKE_AREA_RATIO`, elongations within
# `LIKE_ELONG_RATIO` (the inconsistency reader's own likeness, 2026-11-12).

#: areas within this factor are like (mascot feet 448 / 412 mm^2, emoji legs
#: 147 / 117 mm^2)
LIKE_AREA_RATIO = 1.5
#: elongations (long / short side of the minimum rectangle) within this factor
#: are like -- `tools/inconsistency_fault_reader.ELONG_RATIO`
LIKE_ELONG_RATIO = 1.25
#: a group whose members' own angles all sit within this of the biggest's
#: already agrees and is left alone (one of `best_fill_angle_deg`'s 16
#: candidate directions is 11.25 deg; under half of that is "the same").
AGREE_DEG = 5.0


def rect_axis(poly) -> tuple[float, float]:
    """(long-axis angle in degrees mod 180, elongation >= 1) of the shape's
    minimum rotated rectangle; (0, 1) for a degenerate one."""
    import math
    rect = poly.minimum_rotated_rectangle
    coords = list(getattr(getattr(rect, "exterior", None), "coords", []))
    if len(coords) < 4:
        return 0.0, 1.0
    (x0, y0), (x1, y1), (x2, y2) = coords[0], coords[1], coords[2]
    a = math.hypot(x1 - x0, y1 - y0)
    b = math.hypot(x2 - x1, y2 - y1)
    if a >= b:
        ang, long_, short = math.degrees(math.atan2(y1 - y0, x1 - x0)), a, b
    else:
        ang, long_, short = math.degrees(math.atan2(y2 - y1, x2 - x1)), b, a
    return ang % 180.0, (long_ / short) if short > 1e-9 else float("inf")


def like_shapes(regions: Iterable, *, min_members: int = 2) -> list[list]:
    """Groups of like shapes: connected components, within each thread, of
    "areas within `LIKE_AREA_RATIO` and elongations within
    `LIKE_ELONG_RATIO`", in input order, those of at least `min_members`."""
    regs = [r for r in regions if r.polygon is not None and not r.polygon.is_empty
            and r.polygon.area > 0]
    elong = [rect_axis(r.polygon)[1] for r in regs]
    parent = list(range(len(regs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def ratio(a, b):
        lo, hi = min(a, b), max(a, b)
        return hi / lo if lo > 0 else float("inf")

    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            if (regs[i].thread_index == regs[j].thread_index
                    and ratio(regs[i].polygon.area, regs[j].polygon.area) <= LIKE_AREA_RATIO
                    and ratio(elong[i], elong[j]) <= LIKE_ELONG_RATIO):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    by: dict[int, list] = {}
    for i, r in enumerate(regs):
        by.setdefault(find(i), []).append(r)
    return [g for _k, g in sorted(by.items()) if len(g) >= min_members]


def _congruent(r) -> dict | None:
    tag = (r.meta or {}).get("congruent_group")
    return tag if isinstance(tag, dict) and tag.get("id") is not None else None


def shared_angles(regions: Iterable, own_angle: Callable[[object], float | None], *,
                  fallback: bool = True, mirrored: bool = True) -> dict[str, float]:
    """-> {shape_id: angle deg mod 180} for every member of a group of like
    shapes: the biggest member's `own_angle`, relative to each member's
    `congruent_group["angle_deg"]` for a tagged group, absolute otherwise. A
    group whose biggest member has no angle of its own is left alone.
    `fallback` False: tagged groups only, no `like_shapes`. `mirrored` False:
    a tagged member marked `mirror` is left out."""
    regs = list(regions)
    tagged: dict = {}
    loose = []
    for r in regs:
        tag = _congruent(r)
        if tag is None:
            loose.append(r)
        elif mirrored or not tag.get("mirror"):
            tagged.setdefault(tag["id"], []).append(r)
    groups = [(g, True) for _k, g in sorted(tagged.items(), key=lambda kv: str(kv[0])) if len(g) >= 2]
    if fallback:
        groups += [(g, False) for g in like_shapes(loose)]
    out: dict[str, float] = {}
    for g, relative in groups:
        ref = max(g, key=lambda r: (r.polygon.area, r.shape_id))
        base = own_angle(ref)
        if base is None:
            continue
        a_ref = float(_congruent(ref).get("angle_deg") or 0.0) if relative else 0.0
        # A group whose members already agree is left as it sews: its own
        # angle may be read on another polygon than the one its rung fills
        # ((hed)p.e.'s parentheses, both 123.7 deg under their keyline loop,
        # read 90 on the art polygon), and moving both helps nothing.
        owns = []
        for r in g:
            a = base if r is ref else own_angle(r)
            if a is None:
                owns = []
                break
            d = float(_congruent(r).get("angle_deg") or 0.0) - a_ref if relative else 0.0
            owns.append((float(a) - d - float(base) + 90.0) % 180.0 - 90.0)
        if owns and max(abs(x) for x in owns) <= AGREE_DEG:
            continue
        for r in g:
            d = float(_congruent(r).get("angle_deg") or 0.0) - a_ref if relative else 0.0
            out[r.shape_id] = (float(base) + d) % 180.0
    return out
