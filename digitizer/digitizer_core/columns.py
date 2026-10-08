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

- **the junction tuck** (Kent's pick 2026-10-07, fourth step): a column
  that butts another mid-stroke -- the M's diagonal on its stem, the T's
  stem on its bar -- and sews BEFORE it is extended under it by the satin
  tier's own `_JUNCTION_TUCK_MM` plus the pull, capped at half a stroke,
  so the stroke sewn later covers the seam instead of meeting it at a line
  of needle holes. A butting column that sews AFTER the one it butts stays
  square: an overlap on top is a lump, not a tuck.

NOT yet: short stitches on the inside of a bend, tie stitches, an edge-walk
underlay for tall caps. Every one of those is a Column consumer and goes here.
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
# The tuck never reaches past the middle of the stroke it goes under: the
# other side of that stroke is bare fabric or the next junction.
_TUCK_MAX_WIDTHS = 0.5
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
    dropped_mm: float = 0.0             # scanline length a straight scan left unstationed

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
                      rail_a=self.rail_a[::-1], rail_b=self.rail_b[::-1], dropped_mm=self.dropped_mm)


def is_lettering(region, cfg=None) -> bool:
    """Does the lane take this shape? Under `cfg.lettering_words` the one
    tagger's word (`words.tag_words`, `word_id`, L1). Off, either old
    tagger: the text cluster (`textcluster.tag`, `text_candidate`) or the
    house-angle group (`set_lettering_house_angle`, `lettering_group`),
    which disagree on real logos (`tools/word_tagger_eval.py`)."""
    m = region.meta or {}
    if getattr(cfg, "lettering_words", False):
        return bool(m.get("word_id"))
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
    BOTH ends of every station, the engine's flat zigzag (`satin_stroke`:
    A1, B1, A2, B2, ...): the needle crosses from a_i to b_i and crosses
    back from b_i to a_(i+1), so each rail gets a penetration every station,
    one `SATIN_SPACING_MM` apart -- what the satin tier lays on the same
    stem (MARINE's I: 0.40 mm per rail). The 10-07 wiring put ONE end down
    per station, rails alternating, and sewed every rail at 0.80 mm, half
    the engine's density; it had read the spike's 0.2 mm stations with both
    ends down (double density, boxes) as the ends being the error rather
    than the pitch."""
    legs = [math.dist(a, b) for a, b in stations]
    thr = comb_thresholds(legs, split_above_mm)
    pts: list[tuple[float, float]] = []
    for i, (a, b) in enumerate(stations):
        for pt in (a, b):
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


def _tuck_stations(col: Column, end: int, through: Polygon, tuck_mm: float,
                   max_reach_mm: float, pitch_mm: float, poly_link):
    """Stations continuing `col` past the given end (0 or -1) into the piece
    it butts: one per `pitch_mm`, in order away from the column, until the
    cut line plus `tuck_mm` is reached (0 for a plain butt), never more
    than `max_reach_mm` past the cut, and stopping at the first cross the
    letter does not cover. The last station of a cut piece sits up to a
    pitch short of the cut, so even a plain butt usually gains a station."""
    sts = col.stations if end == 0 else col.stations[::-1]
    (a0, b0), (a1, b1) = sts[0], sts[1]
    m0 = ((a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2)
    m1 = ((a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2)
    L = math.dist(m0, m1)
    if L < 1e-9:
        return []
    d = ((m0[0] - m1[0]) / L, (m0[1] - m1[1]) / L)
    reach = 4.0 * col.width_mm
    ray = LineString([m0, (m0[0] + d[0] * reach, m0[1] + d[1] * reach)])
    if through.covers(ray.interpolate(0.0)):
        gap = 0.0
    else:
        gap = min((math.dist(m0, g) for g in _coords(ray.intersection(through.boundary))), default=reach)
    if gap >= reach:
        return []
    out = []
    k = 1
    while True:
        sh = k * pitch_mm
        if sh - pitch_mm - gap >= tuck_mm - 1e-9:      # the previous station already reached
            break
        if sh - gap > max_reach_mm + 1e-9:            # never past the middle of the stroke
            break
        a = (a0[0] + d[0] * sh, a0[1] + d[1] * sh)
        b = (b0[0] + d[0] * sh, b0[1] + d[1] * sh)
        if not poly_link.covers(LineString([a, b])):
            break
        out.append((a, b))
        k += 1
    return out


def _coords(geom):
    if geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        return [c for g in geom.geoms for c in _coords(g)]
    return list(geom.coords)


# ---------------------------------------------------------------- the walk

def _span_graph(columns: list[Column], merge_r: float):
    """Columns -> (nodes, spans, junctions). A span is a stretch of one
    column between two station indices, with its two node ids; a column is
    cut where another column's END lands on its centreline away from its
    own ends, and each such landing is a junction (the butting column and
    end, the through column and the station it lands on)."""
    mids = [_mids(c.stations) for c in columns]
    ends = [(cj, 0, m[0]) for cj, m in enumerate(mids)] + [(cj, -1, m[-1]) for cj, m in enumerate(mids)]
    cuts_per: list[list[int]] = []
    junctions: list[dict] = []      # butting column `ci`/`end` meets `through` at station `k`
    for ci, m in enumerate(mids):
        n = len(m)
        idx = {0, n - 1}
        lo, hi = _END_FRAC * (n - 1), (1 - _END_FRAC) * (n - 1)
        for cj, end, p in ends:
            if cj == ci:
                continue
            best = min(range(n), key=lambda k: math.dist(m[k], p))
            if math.dist(m[best], p) <= merge_r and lo < best < hi:
                idx.add(best)
                junctions.append(dict(ci=cj, end=end, through=ci, k=best))
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
    return nodes, spans, junctions


def _euler_trail(nodes, spans, start_near, prefer=frozenset(), prefer_within_mm=math.inf):
    """Chinese-postman duplication plus Hierholzer, per component.
    -> list of components, each a list of (span index, from node, to node)
    in walk order; components ordered nearest-first from `start_near`.
    `prefer` names nodes to START a trail from when they are odd -- the free
    ends of butting columns, so the stem of a T is sewn before the bar it
    goes under: the trail's endpoints are the odd nodes left unpaired, and
    the pairing below consumes every other odd node first. A preferred
    start farther than `prefer_within_mm` from the needle is not taken:
    on 4 mm caps it turned the entry hop into a trim on 7 of 39 letters
    (gaulke 23 -> 30) for a tuck the letter is too small to show."""
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
        rank = sorted(cnodes, key=lambda i: i in prefer)       # preferred nodes last
        odd = [i for i in rank if deg[i] % 2 == 1]
        guard = 0
        while len(odd) > 2 and guard < 200:
            guard += 1
            u = odd[0]
            prev_n, prev_i, seen = {}, {}, {u}
            q = deque([u])
            tgt, fallback = -1, -1
            while q:
                x = q.popleft()
                if x != u and deg[x] % 2 == 1:
                    # a preferred node is paired only when nothing else is
                    # odd: paired, it goes even and can no longer start the
                    # trail (a T's junction paired with the stem's foot
                    # doubled the stem and split the bar in two)
                    if x not in prefer:
                        tgt = x
                        break
                    if fallback < 0:
                        fallback = x
                for iid, v in adj[x]:
                    if v not in seen:
                        seen.add(v)
                        prev_n[v], prev_i[v] = x, iid
                        q.append(v)
            if tgt < 0:
                tgt = fallback
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
            odd = [i for i in rank if deg[i] % 2 == 1]
        pool = odd if odd else cnodes
        if cursor is None:
            start = min(pool, key=lambda i: (i not in prefer, i))
        else:
            near = [i for i in pool if i in prefer and math.dist(nodes[i], cursor) <= prefer_within_mm]
            start = min(near or pool, key=lambda i: math.dist(nodes[i], cursor))
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
    from .stage6_satin import (_JUNCTION_TUCK_MM, _comb_thresholds, _push_rails,   # same package,
                               _short_stitch_guard, _split_points)                  # same rules

    report = {"too_thin": False, "jumps": 0, "empty": False,
              "columns": 0, "columns_unsewn": 0, "thin_crosses": 0, "stations": 0,
              "spans": 0, "underpath_mm": 0.0, "junctions": 0, "tucks": 0}
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
    nodes, spans, junctions = _span_graph(ready, merge_r)
    report["junctions"] = len(junctions)
    # The free end of a butting column (its other end, when nothing else
    # meets it there) is where its component's walk should start -- when
    # the stroke has room for the whole tuck. Where the half-stroke cap
    # already truncates it (gaulke's 0.96 mm strokes at 0.3 pull) the
    # reorder bought a sliver and cost six entry trims over 39 letters.
    tuck_mm = min(_JUNCTION_TUCK_MM + pull_mm, _TUCK_MAX_WIDTHS * W)
    roomy = _TUCK_MAX_WIDTHS * W >= _JUNCTION_TUCK_MM + pull_mm
    touch: dict[int, int] = {}
    for sp in spans:
        touch[sp["na"]] = touch.get(sp["na"], 0) + 1
        touch[sp["nb"]] = touch.get(sp["nb"], 0) + 1
    prefer: set[int] = set()
    for j in junctions if roomy else ():
        n = len(ready[j["ci"]].stations)
        free_idx = n - 1 if j["end"] == 0 else 0
        for sp in spans:
            if sp["ci"] != j["ci"]:
                continue
            for key, idx in (("na", sp["i0"]), ("nb", sp["i1"])):
                if idx == free_idx and touch.get(sp[key], 0) == 1:
                    prefer.add(sp[key])
    components = _euler_trail(nodes, spans, start_near, frozenset(prefer), trim_at_mm)

    # 3. Emit: the last visit of a span sews satin, earlier visits run under it.
    #    (`poly_link` is the sew-or-jump rule's polygon, see step 4; the
    #    connector below asks it the same question one leg early.)
    poly_link = poly.buffer(0.1 + pull_mm)
    all_legs: list[dict] = []       # ci, sat, i0, i1 in traversal order (i0 may be > i1)
    for circuit in components:
        seen: set[int] = set()
        is_satin = [False] * len(circuit)
        for k in range(len(circuit) - 1, -1, -1):
            si = circuit[k][0]
            if si not in seen:
                seen.add(si)
                is_satin[k] = True
        # collapse contiguous visits of one column, same type, same direction
        legs: list[dict] = []
        for k, (si, frm, _to) in enumerate(circuit):
            s = spans[si]
            fwd = frm == s["na"] or s["na"] == s["nb"]      # a ring's self-loop walks forward
            i0, i1 = (s["i0"], s["i1"]) if fwd else (s["i1"], s["i0"])
            prev = legs[-1] if legs else None
            if prev and prev["ci"] == s["ci"] and prev["sat"] == is_satin[k] and prev["i1"] == i0:
                prev["i1"] = i1
            else:
                legs.append(dict(ci=s["ci"], sat=is_satin[k], i0=i0, i1=i1, head=[], tail=[]))
        all_legs.extend(legs)
    # The junction tuck: a butting column that sews BEFORE the column it
    # butts runs on under it, so the later stroke covers the seam. Decided on
    # the satin order the walk produced -- sewn after, it stays square.
    for j in junctions:
        n = len(ready[j["ci"]].stations)
        end_idx = 0 if j["end"] == 0 else n - 1
        mine = [k for k, lg in enumerate(all_legs) if lg["sat"] and lg["ci"] == j["ci"]
                and min(lg["i0"], lg["i1"]) <= end_idx <= max(lg["i0"], lg["i1"])]
        theirs = [k for k, lg in enumerate(all_legs) if lg["sat"] and lg["ci"] == j["through"]
                  and min(lg["i0"], lg["i1"]) <= j["k"] <= max(lg["i0"], lg["i1"])]
        if not mine or not theirs:
            continue
        # Sewn before the stroke it meets (before the later of that stroke's
        # halves when the junction splits it): go under it by the tuck.
        # Sewn after: a plain butt, up to the cut line and no further.
        before = mine[0] < max(theirs)
        ext = _tuck_stations(ready[j["ci"]], j["end"], ready[j["through"]].piece,
                             tuck_mm if before else 0.0, _TUCK_MAX_WIDTHS * W,
                             spacing_mm, poly_link)
        if not ext:
            continue
        if before:
            report["tucks"] += 1
        leg = all_legs[mine[0]]
        at_start = (leg["i0"] <= leg["i1"]) == (j["end"] == 0)      # the end in traversal terms
        if at_start:
            leg["head"] = ext[::-1]
        else:
            leg["tail"] = ext
    runs: list[StitchRun] = []
    for leg in all_legs:
        col = ready[leg["ci"]]
        lo, hi = min(leg["i0"], leg["i1"]), max(leg["i0"], leg["i1"])
        sts = col.stations[lo:hi + 1]
        if leg["i1"] < leg["i0"]:
            sts = sts[::-1]
        if leg["sat"]:
            sts = leg["head"] + sts + leg["tail"]
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

    # One station per `spacing_mm` along the rail, both ends of each sewn:
    # the engine's own meaning of satin spacing (a needle every `spacing_mm`
    # on EACH rail). The spike stationed at half that with both ends down
    # and sewed every letter twice as dense.
    cut = letter_columns(poly, pitch_mm=spacing_mm)
    runs, report = column_runs(cut.columns, cut.poly, shape_id, trim_at_mm=trim_at_mm,
                               spacing_mm=spacing_mm, split_above_mm=split_above_mm,
                               pull_mm=pull_mm, pull_floor_mm=pull_floor_mm,
                               underlay_style=underlay_style, start_near=start_near)
    report["cuts"] = len(cut.cuts)
    report["columns_unsewn"] += len(cut.unsewn)
    return runs, report
