"""The Column object and its construction engine for traced lettering.

A Column is what an `.embf` glyph already is (`src/satinplay.js`: two rails
plus rungs, "no skeletonization, no guessing"): a list of STATIONS, each a
rail-to-rail cross `(pa, pb)` in mm, plus the piece of the letter it covers.
`outline_cut.letter_columns` produces them from a traced letter; this module
turns them into stitches with the rules a typed glyph gets and a traced one
never did (`docs/lettering-route-review-2026-09-19.md` §3, the construction
gap; `docs/lettering-architecture-rd-2026-10-07.md` §5 L5, Kent's pick
2026-10-07: port the glyph rules to Python rather than play Columns back in
the Studio).

What this carries (each rule is the font engine's, `src/satinfont.js`
`routeGlyph`, ported):

- pull compensation on the RAILS, per side, by the fabric's own
  `pull_comp_mm`, held back across a counter (`stage6_satin._push_rails`,
  the same function the shipped satin tier uses, on the same artwork
  polygon);
- the cross floor (`machine.SATIN_MIN_CROSS_MM`): a cross the needle cannot
  resolve is dropped and counted, never sewn as a smear;
- split satin above `split_above_mm` with the column-wide comb
  (`_comb_thresholds`, `_split_points`: Kent's 2026-09-30 "smooth and flow"
  rule), so a wide stem is a split column, never a fill;
- **the Euler walk** (Kent's pick 2026-10-07, second step of the lane): a
  letter's columns are the edges of a span graph -- column ends merged
  into nodes, a column end that lands mid-stroke on another column cutting
  that column into spans -- made Eulerian per component by duplicating a
  minimal set of spans along shortest paths between odd nodes
  (Chinese-postman, greedy), walked by Hierholzer's trail; a span sews
  SATIN on its last visit and a running UNDERPATH on every earlier one, so
  every travel lies under a column sewn later and the needle never leaves
  the letter inside one component. Before this the order was nearest-next
  and every hop that left the letter was a jump (enthusiast 13 -> 22
  trims, Fremont 17 -> 38 on the first wiring);
- a centre-walk underlay laid immediately before each satin span, out and
  back so the needle is where the satin starts, where the letter is large
  enough for underlay at all (the caller passes "none" under
  `machine.SATIN_UNDERLAY_MIN_EXTENT_MM`, as it does for the satin tier);
- the shipped sew-or-jump rule between runs (a short hop inside the letter
  is a stitch, a long one or one over bare fabric a jump, a jump past
  `trim_at_mm` a trim).

NOT yet: junction overlap between a butting column and the one it butts,
short stitches on the inside of a bend, tie stitches, an edge-walk underlay
for tall caps. Every one of those is a Column consumer and goes here.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon
from shapely.ops import substring

from . import machine, stitches
from .stitches import StitchRun

# A column end within this many stroke widths (plus a constant for the pull)
# of another column's centreline sits ON that column: the two meet there.
# routeGlyph's `mergeR = max(2, 1.3 * medW)`; at 0.75 Becker's M left its
# stem as a component of its own (the mitred diagonal starts a width away).
_MERGE_WIDTHS = 1.3
_MERGE_PAD_MM = 0.3
# A hop between two legs that stays INSIDE the letter is sewn as a connector
# up to this many stroke widths long, whatever `trim_at_mm` says: the font
# engine's walk is continuous along the glyph and the pro's Becker file cuts
# 12 times for the whole design. Past it the sew-or-jump rule decides.
_CONNECTOR_WIDTHS = 2.0
# A junction closer than this fraction of a column's length to one of its
# ends IS that end, not a mid-stroke cut (routeGlyph: 0.06 / 0.94).
_END_FRAC = 0.06
# The running underpath under a later column: the font engine's 2 mm step.
_UNDERPATH_STEP_MM = 2.0
# Centre-walk underlay: step and end inset (satinfont.js UNDERLAY_*).
_UNDERLAY_STEP_MM = 3.0
_UNDERLAY_INSET_MM = 0.4


@dataclass
class Column:
    """One satin column of a letter: rail-to-rail crosses in sew order."""

    stations: list[tuple[tuple[float, float], tuple[float, float]]]
    piece: Polygon                      # the stroke piece these crosses cover
    kind: str                           # "straight" | "curved" | "ring"
    axis: tuple[float, float] | None    # unit axis of a straight piece
    width_mm: float                     # the letter's mean stroke width
    rail_a: list[tuple[float, float]] = field(default_factory=list)
    rail_b: list[tuple[float, float]] = field(default_factory=list)

    @property
    def start(self) -> tuple[float, float]:
        a, b = self.stations[0]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    @property
    def end(self) -> tuple[float, float]:
        a, b = self.stations[-1]
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

    def reversed(self) -> "Column":
        return Column(stations=self.stations[::-1], piece=self.piece, kind=self.kind,
                      axis=self.axis, width_mm=self.width_mm,
                      rail_a=self.rail_a[::-1], rail_b=self.rail_b[::-1])


def is_lettering(region) -> bool:
    """Does the lane take this shape? Either tagger says lettering: the text
    cluster (`textcluster.tag`, `text_candidate`) or the house-angle group
    (`set_lettering_house_angle`, `lettering_group`). The two disagree on
    real logos and merging them is the architecture's L1; until then the
    lane reads both."""
    m = region.meta or {}
    return bool(m.get("text_candidate") or m.get("lettering_group"))


# ----------------------------------------------------------------- geometry

def _mids(stations):
    return [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in stations]


def _walk_points(path, step_mm: float) -> list[tuple[float, float]]:
    """`path` resampled every `step_mm` of arc length, both ends kept."""
    ln = LineString(path)
    if ln.length < 1e-9:
        return [tuple(path[0]), tuple(path[-1])]
    n = max(1, int(math.ceil(ln.length / step_mm)))
    return [ln.interpolate(ln.length * k / n).coords[0] for k in range(n + 1)]


def _satin_points(stations, split_above_mm: float, comb_thresholds, split_points):
    """Stations in traversal order -> the zigzag's penetrations, split comb on.
    ONE penetration per station, rails alternating (a_0, b_1, a_2, ...): a
    cross is the thread from one station's penetration to the next's, and
    consecutive crosses sit one station apart -- the engine's satin
    (`_resample_by_pitch`) and the spike's `zigzag`. The first wiring put
    both ends of every station down and sewed boxes at double density."""
    legs = [math.dist(a, b) for a, b in stations]
    thr = comb_thresholds(legs, split_above_mm)
    pts: list[tuple[float, float]] = []
    for i, (a, b) in enumerate(stations):
        pt = a if i % 2 == 0 else b
        if pts:
            if math.dist(pts[-1], pt) < stitches.SAME_POINT_MM:
                continue
            pts.extend(split_points(pts[-1], pt, i, thr[i] if i < len(thr) else split_above_mm))
        pts.append(pt)
    return pts


def _centre_underlay(mids) -> list[tuple[float, float]] | None:
    """Centre walk down the span, inset at both ends, out and back."""
    ln = LineString(mids)
    if ln.length <= 2 * _UNDERLAY_INSET_MM + machine.MIN_STITCH_MM:
        return None
    core = substring(ln, _UNDERLAY_INSET_MM, ln.length - _UNDERLAY_INSET_MM)
    path = _walk_points(list(core.coords), _UNDERLAY_STEP_MM)
    return path + path[-2::-1]


# ---------------------------------------------------------------- the walk

def _span_graph(columns: list[Column], merge_r: float):
    """Columns -> (nodes, spans). A span is a stretch of one column between
    two station indices, with its two node ids; a column is cut where
    another column's END lands on its centreline away from its own ends."""
    mids = [_mids(c.stations) for c in columns]
    ends = [m[0] for m in mids] + [m[-1] for m in mids]
    cuts_per: list[list[int]] = []
    for m in mids:
        n = len(m)
        idx = {0, n - 1}
        lo, hi = _END_FRAC * (n - 1), (1 - _END_FRAC) * (n - 1)
        for p in ends:
            best = min(range(n), key=lambda k: math.dist(m[k], p))
            if math.dist(m[best], p) <= merge_r and lo < best < hi:
                idx.add(best)
        cuts = sorted(idx)
        uniq = [cuts[0]]
        for k in cuts[1:]:
            if k - uniq[-1] >= 2:
                uniq.append(k)
        if uniq[-1] != n - 1:
            uniq[-1] = n - 1
        cuts_per.append(uniq)
    nodes: list[tuple[float, float]] = []

    def node_of(p):
        for i, q in enumerate(nodes):
            if math.dist(q, p) <= merge_r:
                return i
        nodes.append(p)
        return len(nodes) - 1

    spans = []      # dict(ci, i0, i1, na, nb)
    for ci, cuts in enumerate(cuts_per):
        own = []
        for i0, i1 in zip(cuts, cuts[1:]):
            own.append(dict(ci=ci, i0=i0, i1=i1,
                            na=node_of(mids[ci][i0]), nb=node_of(mids[ci][i1])))
        # A stub at a column's END whose two ends fall in ONE node is not a
        # span of its own (a bold letter's merge radius swallows the tail
        # past a junction): it rides with its neighbour, so the walk never
        # finishes a leg a stub's length away from the node it reports.
        while len(own) > 1 and own[0]["na"] == own[0]["nb"]:
            own[1]["i0"], own[1]["na"] = own[0]["i0"], own[0]["na"]
            own.pop(0)
        while len(own) > 1 and own[-1]["na"] == own[-1]["nb"]:
            own[-2]["i1"], own[-2]["nb"] = own[-1]["i1"], own[-1]["nb"]
            own.pop()
        spans.extend(own)
    return nodes, spans


def _euler_trail(nodes, spans, start_near):
    """Chinese-postman duplication plus Hierholzer, per component.
    -> list of components, each a list of (span index, from node, to node)
    in walk order; components ordered nearest-first from `start_near`."""
    adj: list[list[tuple[int, int]]] = [[] for _ in nodes]     # (instance id, to)
    inst: list[tuple[int, int, int]] = []                        # (span, a, b)

    def add_inst(si, a, b):
        iid = len(inst)
        inst.append((si, a, b))
        adj[a].append((iid, b))
        adj[b].append((iid, a))

    for si, s in enumerate(spans):
        add_inst(si, s["na"], s["nb"])
    comp = [-1] * len(nodes)
    comps: list[list[int]] = []
    for s0 in range(len(nodes)):
        if comp[s0] != -1 or not adj[s0]:
            continue
        comp[s0] = len(comps)
        members = [s0]
        q = [s0]
        while q:
            u = q.pop()
            for _, v in adj[u]:
                if comp[v] == -1:
                    comp[v] = comp[s0]
                    members.append(v)
                    q.append(v)
        comps.append(members)

    def trail(cnodes, cursor):
        deg = {i: len(adj[i]) for i in cnodes}
        odd = [i for i in cnodes if deg[i] % 2 == 1]
        guard = 0
        while len(odd) > 2 and guard < 200:
            guard += 1
            u = odd[0]
            prev_n, prev_i, seen = {}, {}, {u}
            q = deque([u])
            tgt = -1
            while q:
                x = q.popleft()
                if x != u and deg[x] % 2 == 1:
                    tgt = x
                    break
                for iid, v in adj[x]:
                    if v not in seen:
                        seen.add(v)
                        prev_n[v], prev_i[v] = x, iid
                        q.append(v)
            if tgt < 0:
                break
            x = tgt
            while x != u:
                p = prev_n[x]
                si, a, b = inst[prev_i[x]]
                add_inst(si, a, b)
                deg[x] += 1
                deg[p] += 1
                x = p
            odd = [i for i in cnodes if deg[i] % 2 == 1]
        pool = odd if odd else cnodes
        start = min(pool) if cursor is None else min(pool, key=lambda i: math.dist(nodes[i], cursor))
        used: set[int] = set()
        ptr = {i: 0 for i in cnodes}
        stack, edge_stack, circuit = [start], [], []
        while stack:
            v = stack[-1]
            while ptr[v] < len(adj[v]) and adj[v][ptr[v]][0] in used:
                ptr[v] += 1
            if ptr[v] < len(adj[v]):
                iid, to = adj[v][ptr[v]]
                ptr[v] += 1
                used.add(iid)
                edge_stack.append((inst[iid][0], v, to))
                stack.append(to)
            else:
                stack.pop()
                if edge_stack:
                    circuit.append(edge_stack.pop())
        circuit.reverse()
        return circuit

    # Components in the order the needle meets them: each next component is
    # the one with a node nearest where the last walk ended, entered there.
    out = []
    cursor = start_near
    left = list(comps)
    while left:
        if cursor is None:
            pick = left[0]
        else:
            pick = min(left, key=lambda c: min(math.dist(nodes[i], cursor) for i in c))
        left.remove(pick)
        circuit = trail(pick, cursor)
        if circuit:
            out.append(circuit)
            cursor = nodes[circuit[-1][2]]
    return out


# --------------------------------------------------------------- the engine

def column_runs(columns: list[Column], poly: Polygon, shape_id: str, *,
                trim_at_mm: float,
                spacing_mm: float = machine.SATIN_SPACING_MM,
                split_above_mm: float | None = None,
                pull_mm: float = 0.0,
                pull_floor_mm: float = 0.0,
                underlay_style: str = "none",
                start_near: tuple[float, float] | None = None,
                min_cross_mm: float = machine.SATIN_MIN_CROSS_MM,
                ) -> tuple[list[StitchRun], dict]:
    """Columns of ONE letter -> runs in sew order, plus a report in the
    satin tier's contract (`empty`, `too_thin`, `jumps`), extended with the
    column census stage 7 copies into the plan's counters."""
    from .stage6_satin import (_comb_thresholds, _push_rails, _short_stitch_guard,   # same package,
                               _split_points)                                        # same rules

    report = {"too_thin": False, "jumps": 0, "empty": False,
              "columns": 0, "columns_unsewn": 0, "thin_crosses": 0, "stations": 0,
              "spans": 0, "underpath_mm": 0.0}
    above = split_above_mm if split_above_mm is not None else machine.SPLIT_SATIN_ABOVE_MM

    # 1. Each column's stations as the fabric will get them: pushed on the
    #    rails, crosses under the floor dropped.
    ready: list[Column] = []
    for col in columns:
        a_pts = [a for a, _ in col.stations]
        b_pts = [b for _, b in col.stations]
        if pull_mm > 0:
            a_pts, b_pts = _push_rails(a_pts, b_pts, poly, pull_mm, pull_floor_mm)
        # Short stitches on the inside of a bend (`satinplay.js` pullShort;
        # the engine's own guard): where a rail's penetrations bunch up
        # under SATIN_SHORT_STITCH_AT_MM -- the inner rail of an S's curl is
        # a single point every outer cross converges on -- every other cross
        # is pulled back toward the outer rail, so the inside stops re-entering
        # one needle hole. The pro's S: the outer rail dense, the inner rail
        # short-stitched (lettering-thickness-fremont-2026-10-06).
        guarded = _short_stitch_guard(a_pts, b_pts)
        kept = [(a, b) for a, b in guarded if math.dist(a, b) >= min_cross_mm]
        report["thin_crosses"] += len(col.stations) - len(kept)
        if len(kept) < 3:
            report["columns_unsewn"] += 1
            continue
        ready.append(Column(stations=kept, piece=col.piece, kind=col.kind, axis=col.axis,
                            width_mm=col.width_mm, rail_a=col.rail_a, rail_b=col.rail_b))
    if not ready:
        report["empty"] = True
        return [], report
    report["columns"] = len(ready)
    report["stations"] = sum(len(c.stations) for c in ready)

    # 2. The span graph and the walk.
    W = sorted(c.width_mm for c in ready)[len(ready) // 2]
    merge_r = _MERGE_WIDTHS * W + _MERGE_PAD_MM + pull_mm
    nodes, spans = _span_graph(ready, merge_r)
    components = _euler_trail(nodes, spans, start_near)

    # 3. Emit: the last visit of a span sews satin, earlier visits run under it.
    #    (`poly_link` is the sew-or-jump rule's polygon, see step 4; the
    #    connector below asks it the same question one leg early.)
    poly_link = poly.buffer(0.1 + pull_mm)
    runs: list[StitchRun] = []
    for circuit in components:
        seen: set[int] = set()
        is_satin = [False] * len(circuit)
        for k in range(len(circuit) - 1, -1, -1):
            si = circuit[k][0]
            if si not in seen:
                seen.add(si)
                is_satin[k] = True
        # collapse contiguous visits of one column, same type, same direction
        legs: list[dict] = []       # ci, sat, i0, i1 in traversal order (i0 may be > i1)
        for k, (si, frm, _to) in enumerate(circuit):
            s = spans[si]
            fwd = frm == s["na"] or s["na"] == s["nb"]      # a ring's self-loop walks forward
            i0, i1 = (s["i0"], s["i1"]) if fwd else (s["i1"], s["i0"])
            prev = legs[-1] if legs else None
            if prev and prev["ci"] == s["ci"] and prev["sat"] == is_satin[k] and prev["i1"] == i0:
                prev["i1"] = i1
            else:
                legs.append(dict(ci=s["ci"], sat=is_satin[k], i0=i0, i1=i1))
        for leg in legs:
            col = ready[leg["ci"]]
            lo, hi = min(leg["i0"], leg["i1"]), max(leg["i0"], leg["i1"])
            sts = col.stations[lo:hi + 1]
            if leg["i1"] < leg["i0"]:
                sts = sts[::-1]
            mids = _mids(sts)
            # The walk is continuous along CENTRELINES; a zigzag ends on a
            # rail. From that rail point to the next leg's first penetration
            # the straight hop can cut the outer corner of a mitre and read
            # as a jump, so the hop goes through the junction: a connector
            # run to this leg's first centre point, inside the letter.
            if runs and runs[-1].shape_id == shape_id:
                tail = runs[-1].points[-1]
                hop = math.dist(tail, mids[0])
                if (machine.TINY_STITCH_MM <= hop <= max(trim_at_mm, _CONNECTOR_WIDTHS * W)
                        and poly_link.covers(LineString([tail, mids[0]]))):
                    runs.append(StitchRun(points=_walk_points([tail, mids[0]], _UNDERPATH_STEP_MM),
                                          kind=stitches.TRAVEL, shape_id=shape_id))
                # else a real gap: the link rule in step 4 decides
            if leg["sat"]:
                report["spans"] += 1
                if underlay_style != "none":
                    ul = _centre_underlay(mids)
                    if ul is not None:
                        runs.append(StitchRun(points=ul, kind=stitches.UNDERLAY, shape_id=shape_id))
                pts = _satin_points(sts, above, _comb_thresholds, _split_points)
                if len(pts) >= 4:
                    runs.append(StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id))
                    continue
            # an underpath (an earlier visit), or a satin span too short to
            # sew: the needle still has to reach the far end, under later thread
            path = _walk_points(mids, _UNDERPATH_STEP_MM)
            if len(path) >= 2:
                runs.append(StitchRun(points=path, kind=stitches.TRAVEL, shape_id=shape_id))
                report["underpath_mm"] += LineString(path).length
    if not any(r.kind == stitches.SATIN for r in runs):
        report["empty"] = True
        return [], report
    # 4. Link consecutive runs: the satin tier's own sew-or-jump rule, verbatim
    #    (`satin_shape`'s tail). Under rail comp the rails sit a pull outside
    #    the artwork and a hop that ends on one is still inside the column.
    allow = max(trim_at_mm, _CONNECTOR_WIDTHS * W)
    for prev_run, cur in zip(runs, runs[1:]):
        a, b = prev_run.points[-1], cur.points[0]
        d = math.dist(a, b)
        if d < machine.TINY_STITCH_MM:
            continue
        if d <= allow and poly_link.covers(LineString([a, b])):
            continue        # needle-down inside the letter, under thread sewn later
        cur.jump = True
        cur.trim = d > trim_at_mm
        report["jumps"] += 1
    return runs, report


def lettering_columns_shape(poly: Polygon, shape_id: str, *, trim_at_mm: float,
                            spacing_mm: float = machine.SATIN_SPACING_MM,
                            split_above_mm: float | None = None,
                            pull_mm: float = 0.0, pull_floor_mm: float = 0.0,
                            underlay_style: str = "none",
                            start_near: tuple[float, float] | None = None,
                            ) -> tuple[list[StitchRun], dict]:
    """One lettering shape (its ARTWORK polygon) -> runs, report. The
    stage 7 entry point behind `cfg.lettering_columns`: cut, then construct."""
    from .outline_cut import letter_columns

    # One station per `spacing_mm` along the rail, rails alternating: the
    # engine's own meaning of satin spacing (`_resample_by_pitch`). The spike
    # stationed at half that and sewed every letter twice as dense.
    cut = letter_columns(poly, pitch_mm=spacing_mm)
    runs, report = column_runs(cut.columns, cut.poly, shape_id, trim_at_mm=trim_at_mm,
                               spacing_mm=spacing_mm, split_above_mm=split_above_mm,
                               pull_mm=pull_mm, pull_floor_mm=pull_floor_mm,
                               underlay_style=underlay_style, start_near=start_near)
    report["cuts"] = len(cut.cuts)
    report["columns_unsewn"] += len(cut.unsewn)
    return runs, report
