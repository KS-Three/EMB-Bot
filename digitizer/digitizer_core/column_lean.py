"""Crosses square to the LINE OF TEXT in the Column lane
(`lettering_columns_text_lean`, 2026-10-23).

The pro sews every stroke of a 13-17 mm letter with its crosses square to
the line of text -- the stems' own cross -- diagonals included: Becker's
MARINE at 76.5 mm (the hat), 101.9 (the large hat), 95.7 (left chest) and
79.8 (the beanie), where the N's diagonal, the A's legs and the M's two
diagonals all carry the stems' horizontal cross, so every stroke of the
word has one sheen and his junctions are plain overlaps. The Column lane
stations a straight piece square to ITS OWN axis (`outline_cut.scan_stations`),
so our N's diagonal and A's legs read as another sheen beside the stems,
and the M's V, where two leaned pieces meet two upright ones, sews as a
tangle (`docs/lettering-10mm-up-2026-10-23.md`, the paths render). The
satin tier has sewn the house cross since 2026-09-03
(`stage6_satin._clamp_to_span`, Kent's adopted convention: stems square to
the line of text, a lean cap of 30 degrees, station spacing over cos of
the lean); the Column lane displaced that tier for lettering on 2026-10-12
without it. This module brings the convention to the lane.

`lean_columns` re-stations each STRAIGHT column of a letter whose axis the
house cross can span within the cap: the crosses lie along the clamped
house direction, one every `pitch / cos(lean)` along the axis so the
distance BETWEEN crosses stays the satin spacing, each cross the longest
segment its line cuts from the piece, ordered along the piece's normal so
rail A and rail B keep their sides. A column the house already crosses
square (an upright stem under upright text), a curved or ring column (the
R's bowl, which the pro fans round as we do), and a column whose lean
would be nil keep their stations, byte for byte -- so the flag moves the
diagonals and the slanted legs and nothing else.

## Italic bars (`cfg.lettering_columns_italic_lean`, 2026-10-25, built OFF; ON since 2026-10-27)

On an ITALIC word the pro crosses each BAR along the word's slant --
parallel to its stems, the way an upright digitizing looks once it is
sheared -- where the lane crosses it square to itself. Read per cross on
PROSEAL (`tools/italic_cross.py`, the pro's hat 85.9 mm and beanie 75.0 mm,
stems leaning 10.2-11.8 deg): his bar crosses sit at 71-78 deg off the line
of text on the slant's side, ours at 80-90 on either side (the P's, E's and
A's bars lean the WRONG way). His stems and the A's legs follow other
readings (see the tool); this moves bars only.

`italic_lean(regions)` reads each tagged word's slant once -- the median of
its letters' stem leans (`letterform_priors.letter_lean_deg`, DP chords
within `ITALIC_WINDOW_DEG` of the line's normal) -- and holds the words
whose slant is `ITALIC_MIN_DEG` to `ITALIC_MAX_DEG` in a context variable
for the length of one `sequence` call (`pipeline.plan_stitches` wraps it,
flag on only). `lean_columns` finds its letter's word by containment and
re-stations every straight column within `ITALIC_BAR_DEG` of the line of
text with its crosses along the stems. Off, the variable is never set and
`lean_columns` is the text-lean pass it was, object for object.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from .columns import Column

# A lean under this is the station scan's own rounding, not a lean: the
# column keeps its original stations (caps, fans and mitres included).
MIN_LEAN_DEG = 0.5
# A cross shorter than this is a corner clipping, not a station (the same
# floor `outline_cut._scan_cross` applies to its scanline segments).
_MIN_SEG_MM = 0.05
_FAR = 200.0


# `block_lean` (`cfg.extra["lettering_columns_block_lean"]`, 2026-11-18, built OFF): on a heavy block
# letter (stroke >= `outline_cut`'s `_butt_min_w()`, 3.5 mm or 3.0 under `block_butt_small`) a
# straight column is crossed level up to a 50 degree lean, not the satin convention's 30, so the
# M's V diagonals (45 deg to the line) sew with the stems' own cross. The pro's: every Becker
# MARINE file, the M's V in four level pieces whose crosses run 7.4-7.7 mm
# (`docs/marine-pro-construction-2026-11-18.md`, rule 3). Layout only (gate 1): the cross is
# longer along a leaning stroke, no floor, compensation or density number changes.
BLOCK_LEAN_SPAN_DEG = 40.0         # span floor 40 = lean cap 50
_BLOCK_LEAN: contextvars.ContextVar[bool] = contextvars.ContextVar("block_lean", default=False)


@contextlib.contextmanager
def block_lean_scope(on: bool):
    """`cfg.extra["lettering_columns_block_lean"]` for one plan. False sets nothing."""
    if not on:
        yield
        return
    token = _BLOCK_LEAN.set(True)
    try:
        yield
    finally:
        _BLOCK_LEAN.reset(token)


def cross_direction(axis, house_deg: float, wide: bool = False) -> tuple[float, float, float]:
    """The cross direction the convention gives a straight piece of unit
    `axis` under the house cross `house_deg` (degrees, plan frame): a unit
    vector along the clamped house (`stage6_satin._clamp_to_span`) and the
    lean, in degrees, off the piece's own normal."""
    from .stage6_satin import _clamp_to_span
    tangent = math.atan2(axis[1], axis[0])
    house = math.radians(house_deg)
    cross = _clamp_to_span(house, tangent)
    if wide and cross != house:
        # the wider cap only lets the house THROUGH on a steep stroke (the M's V, the N's diagonal); past it
        # the fade toward the house grows with the cap, which would tilt an arm's near-upright cross
        cross = _clamp_to_span(house, tangent, BLOCK_LEAN_SPAN_DEG)
        if cross != house:
            cross = _clamp_to_span(house, tangent)
    c = (math.cos(cross), math.sin(cross))
    n = (-axis[1], axis[0])
    cosl = max(-1.0, min(1.0, c[0] * n[0] + c[1] * n[1]))
    return c[0], c[1], math.degrees(math.acos(abs(cosl)))


def _cross_along(piece: Polygon, origin, c, n):
    """The longest segment the line through `origin` along `c` cuts from
    `piece`, its ends ordered along `n`. -> ((pa, pb), other segments' length)
    or None."""
    hit = LineString([(origin[0] - c[0] * _FAR, origin[1] - c[1] * _FAR),
                      (origin[0] + c[0] * _FAR, origin[1] + c[1] * _FAR)]).intersection(piece)
    segs = [g for g in getattr(hit, "geoms", [hit])
            if g.geom_type == "LineString" and g.length > _MIN_SEG_MM]
    if not segs:
        return None
    g = max(segs, key=lambda s: s.length)
    p, q = g.coords[0], g.coords[-1]
    if (p[0] * n[0] + p[1] * n[1]) > (q[0] * n[0] + q[1] * n[1]):
        p, q = q, p
    return (tuple(p), tuple(q)), sum(s.length for s in segs) - g.length


def lean_stations(piece: Polygon, axis, c, pitch_mm: float):
    """Stations along `axis`, crosses along `c`, spaced so consecutive
    crosses sit `pitch_mm` apart measured square to themselves
    (`pitch / cos(lean)` along the axis -- the convention's spacing rule).
    -> (stations, dropped_mm) or None under three stations."""
    u = axis
    n = (-u[1], u[0])
    cosl = abs(c[0] * n[0] + c[1] * n[1])
    if cosl < 1e-6:
        return None
    step = pitch_mm / cosl
    cs = np.array(piece.exterior.coords)
    t = cs @ np.array(u)
    # Each line runs through the axis line THROUGH THE PIECE (its centroid's
    # normal offset), not the one through the origin: a leaned line through
    # a point 20 mm off the piece meets it shifted along the axis by that
    # offset times tan(lean), and a third of the stations fell off one end
    # (Becker's A, 36 -> 22 stations, the first run of this).
    g = piece.centroid
    off = g.x * n[0] + g.y * n[1]
    base = (n[0] * off, n[1] * off)
    # the piece's slanted ends: a leaned line clips a corner up to half the
    # stroke times tan(lean) past the axis extent, so the scan reaches there
    tanl = math.sqrt(max(0.0, 1.0 - cosl * cosl)) / cosl
    ext = 0.5 * float(np.ptp(cs @ np.array(n))) * tanl
    out = []
    dropped = 0.0
    for tt in np.arange(t.min() - ext + step / 2, t.max() + ext, step):
        hit = _cross_along(piece, (base[0] + u[0] * tt, base[1] + u[1] * tt), c, n)
        if hit is None:
            continue
        cross, extra = hit
        dropped += extra
        out.append(cross)
    return (out, dropped) if len(out) >= 3 else None


# `lean_flat_ends` (`cfg.extra["lettering_columns_lean_flat_ends"]`,
# 2026-11-14, built OFF): a leaned column's end on a FLAT face of the letter
# (its top, its baseline, a slanted cut-off) turns its crosses to that face
# over its last stroke width and a half, the last cross the face itself
# (`_flat_ends`; until 2026-11-16 `outline_cut._mitre_ends`, which moved
# slanted arms' level tops and Drone's N foot away from the pro, see
# `FLAT_END_SPAN`) -- measured against the house cross, not the column's
# own normal. Re-stationed under
# the house cross, a stroke's last cross no longer lay on its face: Becker
# MARINE's N at 101.9 mm (Kent's #10 at its top, #11 at its foot, "The
# letters should be flat") ended in crosses 10-12 deg off its top line and
# baseline, so the edge was drawn by a tilted cross's body. The pro's needles
# there (read stitch by stitch, `docs/flat-ends-pro-2026-11-14.md`): his
# last cross lies ON the baseline at #11, and at #10 every cross end sits on
# the one top line.
_LEAN_FLAT_ENDS: contextvars.ContextVar[bool] = contextvars.ContextVar("lean_flat_ends", default=False)


@contextlib.contextmanager
def lean_flat_ends_scope(on: bool):
    """`cfg.extra["lettering_columns_lean_flat_ends"]` for one plan. False
    sets nothing."""
    if not on:
        yield
        return
    token = _LEAN_FLAT_ENDS.set(True)
    try:
        yield
    finally:
        _LEAN_FLAT_ENDS.reset(token)


# The face a leaned end turns to (2026-11-16, the fix behind the 11-15 STOP:
# as first built, `outline_cut._mitre_ends` on the leaned stations, the flag
# moved letters FURTHER from the pro -- `tools/apex_pro.py` on the lane
# inputs of 46 letters it moved, Gaulke, ProSeal, Drone, Becker, N SYNC):
# - it must span `FLAT_END_SPAN` of the column's median cross, measured
#   across the column. A slanted arm whose top is LEVEL has a 0.3-0.4 mm
#   chamfer at its inner corner, 35 deg off the house cross, and the mitre
#   took it for the face: Gaulke's V/W top 8.4 -> 18.5, ProSeal's Y 12.2 ->
#   17.2, where the pro sews level crosses to the top. The small-bold
#   mitre's own guard (`outline_cut.SMALL_BOLD_MITRE_SPAN`), the same 0.6.
FLAT_END_SPAN = 0.6
# - the crosses turn to it over `FLAT_END_TURN_W` stroke widths before it,
#   each a little more, the last one the face. The mitre turned them only
#   inside the face's own wedge, a few crosses through up to 30 deg: Gaulke's
#   N fanned (13.7 -> 17.9 against the pro's level crosses) and Drone's N
#   foot, 22 deg, stepped its needles back up the stem (the "upright
#   stub"). Turned gradually: Gaulke's N 12.1, Becker's N foot 10.6 -> 2.3
#   (the mitre 8.1), the pro's "crosses parallel to the baseline, the last
#   one lying ON it" (`docs/flat-ends-pro-2026-11-14.md`, #11).
FLAT_END_TURN_W = 1.5
# - a stroke that narrows to its end is a tapered tip, not a flat end: its
#   original crosses (rail to rail, before the lean) third to fifth from that
#   end under `FLAT_END_TAPER` of the column's median. Golden Tee's tails
#   read 0.38-0.61 there and the flag turned their last crosses along the
#   stroke; every flat foot and top the flag was built for reads 0.83 or more
#   (Gaulke's N's and arms, ProSeal's A, Drone's N's, Becker's N). The last two
#   crosses are the face's own to cut, so they do not vote.
FLAT_END_TAPER = 0.7


def _tapers(col: Column, last) -> bool:
    """Does `col` narrow to the end whose leaned last cross is `last`?"""
    L = [math.dist(a, b) for a, b in col.stations]
    if len(L) < 6:
        return False
    med = sorted(L)[len(L) // 2]
    m = ((last[0][0] + last[1][0]) / 2, (last[0][1] + last[1][1]) / 2)
    near = L[-5:-2] if math.dist(m, col.end) <= math.dist(m, col.start) else L[2:5]
    return min(near) < FLAT_END_TAPER * med


def _end_face(st, piece: Polygon, u, n, cut_lines, W: float, end: int, med: float):
    """The flat face at this end of leaned stations `st` (`end` 1: the last,
    -1: the first): the longest outline edge within 1.6 W of the end, beyond
    its last cross, `MITRE_MIN_DEG`..`MITRE_MAX_DEG` off the cross `n`,
    spanning `FLAT_END_SPAN` of `med` across the column, and not on a cut.
    -> (p, q, f) or None."""
    from .outline_cut import CAP_CUT_CLEAR_MM, MITRE_MAX_DEG, MITRE_MIN_DEG

    def proj(p):
        return p[0] * u[0] + p[1] * u[1]

    def projn(p):
        return p[0] * n[0] + p[1] * n[1]
    last = (st if end > 0 else st[::-1])[-1]
    t_last = end * proj(((last[0][0] + last[1][0]) / 2, (last[0][1] + last[1][1]) / 2))
    cs = list(piece.exterior.coords)
    face = None
    for p, q in zip(cs[:-1], cs[1:]):
        L = math.dist(p, q)
        if L < 0.25 * W:
            continue
        m = Point((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if any(c.distance(m) < CAP_CUT_CLEAR_MM for c in cut_lines):
            continue                                    # a cut or a counter, not an end
        if end * proj((m.x, m.y)) < t_last - 1.6 * W:
            continue                                    # not at this end
        f = ((q[0] - p[0]) / L, (q[1] - p[1]) / L)
        off = math.degrees(math.acos(min(1.0, abs(f[0] * n[0] + f[1] * n[1]))))
        if not (MITRE_MIN_DEG <= off <= MITRE_MAX_DEG):
            continue
        if min(end * proj(p), end * proj(q)) < t_last - 0.5 * W:
            continue                                    # not beyond the last cross
        if abs(projn(q) - projn(p)) < FLAT_END_SPAN * med:
            continue                                    # a corner chamfer, not the end
        if face is None or L > face[2]:
            face = (p, q, L, f)
    return None if face is None else (face[0], face[1], face[3])


def _flat_ends(st, col: Column, c, cut_lines, pitch_mm: float):
    """`lean_flat_ends`: at an end of leaned stations on a flat face
    (`_end_face`), every station within `FLAT_END_TURN_W` widths of the
    face keeps its centre and turns its cross from the house cross `c`
    toward the face, in proportion to how near it stands; the stations
    within half a pitch of the face give way to the face itself, a
    `CAP_INSET_MM` inside it. An end is left as it was when a turned cross
    falls off the piece, a rail would step back, or the new crosses leave
    the piece."""
    from .outline_cut import CAP_INSET_MM
    if len(st) < 4:
        return st
    piece, W = col.piece, col.width_mm
    u = (c[1], -c[0])
    if u[0] * col.axis[0] + u[1] * col.axis[1] < 0:
        u = (-u[0], -u[1])
    n = (-u[1], u[0])
    lengths = sorted(math.dist(a, b) for a, b in st)
    med = lengths[len(lengths) // 2]

    def proj(p):
        return p[0] * u[0] + p[1] * u[1]

    def projn(p):
        return p[0] * n[0] + p[1] * n[1]
    cover = piece.buffer(0.05)
    flip = projn(st[0][0]) > projn(st[0][1])           # the a end lies on +n
    for end in (1, -1):
        order = st if end > 0 else st[::-1]
        if set(order[-1]) & set(order[-2]):
            continue                                    # a fan already ends on its slant
        if _tapers(col, order[-1]):
            continue                                    # a tapered tip, not a flat end
        face = _end_face(st, piece, u, n, cut_lines, W, end, med)
        if face is None:
            continue
        p, q, f = face
        if f[0] * n[0] + f[1] * n[1] < 0:
            f = (-f[0], -f[1])
        ca, cb = (p, q) if projn(p) < projn(q) else (q, p)
        fn = (-f[1], f[0])
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if not piece.covers(Point(mid[0] + fn[0] * 0.02, mid[1] + fn[1] * 0.02)):
            fn = (-fn[0], -fn[1])
        ca_in = (float(ca[0] + fn[0] * CAP_INSET_MM), float(ca[1] + fn[1] * CAP_INSET_MM))
        cb_in = (float(cb[0] + fn[0] * CAP_INSET_MM), float(cb[1] + fn[1] * CAP_INSET_MM))
        t_face = end * proj(((ca_in[0] + cb_in[0]) / 2, (ca_in[1] + cb_in[1]) / 2))
        zone = FLAT_END_TURN_W * W
        new = []
        for a, b in order:
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            tm = end * proj(m)
            if tm >= t_face - 0.5 * pitch_mm:
                break                                   # the face takes its place
            s = (tm - (t_face - zone)) / zone
            if s <= 0:
                new.append((a, b))
                continue
            d = ((1 - s) * n[0] + s * f[0], (1 - s) * n[1] + s * f[1])
            dl = math.hypot(*d)
            hit = _cross_along(piece, m, (d[0] / dl, d[1] / dl), n)
            if hit is None:
                new = None
                break
            x, y = hit[0]                               # ordered along n
            new.append((y, x) if flip else (x, y))
        if new is None or len(new) < 2:
            continue
        new.append((cb_in, ca_in) if flip else (ca_in, cb_in))
        if any(end * proj(a1) < end * proj(a0) - 0.02 or end * proj(b1) < end * proj(b0) - 0.02
               for (a0, b0), (a1, b1) in zip(new[:-1], new[1:])):
            continue                                    # a rail would step back
        if not all(cover.covers(LineString([a, b])) for a, b in new[-6:]):
            continue
        new = [(tuple(map(float, a)), tuple(map(float, b))) for a, b in new]
        st = new if end > 0 else new[::-1]
    return st


def lean_column(col: Column, house_deg: float, pitch_mm: float, cut_lines=()) -> Column:
    """`col` re-stationed under the house cross, or `col` itself where the
    convention leaves it: not straight, no axis, a lean under
    `MIN_LEAN_DEG`, or a scan that cannot station it. `cut_lines`
    (`lean_flat_ends` only): the letter's other pieces' outlines, so a face
    on one is a cut, not an end."""
    if col.kind != "straight" or col.axis is None or not col.stations:
        return col
    wide = False
    if _BLOCK_LEAN.get():
        from .outline_cut import _butt_min_w
        wide = col.width_mm >= _butt_min_w()
    cx, cy, lean = cross_direction(col.axis, house_deg, wide)
    if lean < MIN_LEAN_DEG:
        return col
    sc = lean_stations(col.piece, col.axis, (cx, cy), pitch_mm)
    if sc is None:
        return col
    st, dropped = sc
    turned = ()
    if _LEAN_FLAT_ENDS.get():
        st0 = st
        st = _flat_ends(st, col, (cx, cy), cut_lines, pitch_mm)
        turned = tuple(e for e, (a, b) in ((0, (st0[0], st[0])), (1, (st0[-1], st[-1]))) if a != b)
    return Column(stations=st, piece=col.piece, kind=col.kind, axis=col.axis,
                  width_mm=col.width_mm, rail_a=list(col.rail_a), rail_b=list(col.rail_b),
                  dropped_mm=dropped, turned=turned)


def lean_columns(columns: list[Column], house_deg: float | None, pitch_mm: float,
                 letter: Polygon | None = None) -> list[Column]:
    """Every column of a letter through `lean_column`; `house_deg` None is
    the lane as it was (the same list object). Inside `italic_lean`, a bar
    of an italic word is crossed along the word's stems instead. `letter`
    (read by `lean_flat_ends` only): the polygon the columns were cut from,
    for its counters."""
    if house_deg is None:
        return columns
    words = _ITALIC.get()
    word = _word_of(columns, words) if words else None
    # `lean_flat_ends`: an edge of a counter is the inside of a bowl, never
    # an end -- the R's leg met its counter's floor and turned to it, 21 deg
    # the wrong way (Drone, 35.7 -> 38.5 against the pro there)
    counters = ([LineString(r.coords) for r in letter.interiors]
                if letter is not None and _LEAN_FLAT_ENDS.get() else [])

    def cuts(i):
        # `lean_flat_ends`: a face that lies on another piece of the letter
        # is a cut between two strokes, never an end to mitre
        if not _LEAN_FLAT_ENDS.get():
            return ()
        return [LineString(o.piece.exterior.coords) for j, o in enumerate(columns)
                if j != i and o.piece is not None and not o.piece.is_empty] + counters
    if word is None:
        return [lean_column(c, float(house_deg), pitch_mm, cuts(i)) for i, c in enumerate(columns)]
    return [italic_bar(c, word, pitch_mm) or lean_column(c, float(house_deg), pitch_mm, cuts(i))
            for i, c in enumerate(columns)]


# ------------------------------------------------------------- italic bars
# A word's slant this far off its line's normal, and no further, is italic.
# 5: MARINE reads 0.0, ProSeal's upright taglines 2.1, PROSEAL 9.7.
ITALIC_MIN_DEG = 5.0
ITALIC_MAX_DEG = 30.0
# The lean reading's window round the normal and its chord tolerance
# (`letterform_priors.letter_lean_deg`): wide enough for PROSEAL's ~11 deg
# stems, narrow enough that an A's 16 deg legs do not vote.
ITALIC_WINDOW_DEG = 15.0
ITALIC_TOL_MM = 0.1
# A straight column within this of the line of text is a bar.
ITALIC_BAR_DEG = 25.0
# A letter's word is found by containment, this far out of its outline.
_WORD_REACH_MM = 0.3


@dataclass(frozen=True)
class ItalicWord:
    line_deg: float           # the line of text, degrees on [0, 180)
    slant_deg: float          # the stems' lean off its normal, signed
    area: object              # shapely prepared geometry: the members, grown

    @property
    def stem_deg(self) -> float:
        return (self.line_deg + 90.0 + self.slant_deg) % 180.0


_ITALIC: contextvars.ContextVar[tuple[ItalicWord, ...] | None] = contextvars.ContextVar(
    "italic_words", default=None)


def italic_words(regions, words: bool = False) -> list[ItalicWord]:
    """The tagged words of `regions` whose stems lean `ITALIC_MIN_DEG` to
    `ITALIC_MAX_DEG` off their line's normal (the median of their letters'
    leans, two letters at least)."""
    from shapely.ops import unary_union
    from shapely.prepared import prep

    from .letterform_priors import lettering_words, letter_lean_deg
    from .textcluster import _line_of_text_deg
    out = []
    for members in lettering_words(regions, words):
        letters = members if words else [r for r in members if r.meta.get("text_candidate")]
        if len(letters) < 2:
            continue
        line = _line_of_text_deg(members)
        line = 0.0 if line is None else line
        leans = [letter_lean_deg(np.asarray(r.polygon.exterior.coords, float), (line + 90.0) % 180.0,
                                 ITALIC_TOL_MM, ITALIC_WINDOW_DEG)
                 for r in letters if r.polygon.geom_type == "Polygon"]
        known = [x for x in leans if x is not None]
        if len(known) < 2:
            continue
        slant = float(np.median(known))
        if not ITALIC_MIN_DEG <= abs(slant) <= ITALIC_MAX_DEG:
            continue
        area = prep(unary_union([r.polygon for r in letters]).buffer(_WORD_REACH_MM))
        out.append(ItalicWord(line_deg=float(line), slant_deg=slant, area=area))
    return out


@contextlib.contextmanager
def italic_lean(regions, words: bool = False):
    """`lean_columns` sees `regions`' italic words for the length of the
    block, and nothing after it (the variable is reset, not cleared, so a
    nested or concurrent plan keeps its own)."""
    token = _ITALIC.set(tuple(italic_words(regions, words)))
    try:
        yield
    finally:
        _ITALIC.reset(token)


def with_italic_lean(fn, regions, words: bool = False):
    """`fn` run inside `italic_lean(regions)` -- what `plan_stitches` calls
    `sequence` through when the flag is on."""
    def run(*args, **kwargs):
        with italic_lean(regions, words):
            return fn(*args, **kwargs)
    return run


def _word_of(columns: list[Column], words) -> ItalicWord | None:
    from shapely.geometry import Point
    for c in columns:
        if c.piece is None or c.piece.is_empty:
            continue
        p = c.piece.representative_point()
        pt = Point(p.x, p.y)
        for w in words:
            if w.area.contains(pt):
                return w
        return None
    return None


def italic_bar(col: Column, word: ItalicWord, pitch_mm: float) -> Column | None:
    """A bar of an italic word re-stationed with its crosses along the
    word's stems; `col` itself when its own cross is already that within
    `MIN_LEAN_DEG`; None (the text-lean pass decides) for anything that is
    not a straight bar, or that the scan cannot station."""
    if col.kind != "straight" or col.axis is None or not col.stations:
        return None
    ax = math.degrees(math.atan2(col.axis[1], col.axis[0]))
    if abs((ax - word.line_deg + 90.0) % 180.0 - 90.0) > ITALIC_BAR_DEG:
        return None
    s = math.radians(word.stem_deg)
    c = (math.cos(s), math.sin(s))
    n = (-col.axis[1], col.axis[0])
    lean = math.degrees(math.acos(min(1.0, abs(c[0] * n[0] + c[1] * n[1]))))
    if lean < MIN_LEAN_DEG:
        return col
    # past the convention's lean cap (a bar tilted against a steep slant)
    # the crosses would run long: the text lean decides that one
    from .stage6_satin import SATIN_HOUSE_MIN_SPAN_DEG
    if lean > 90.0 - SATIN_HOUSE_MIN_SPAN_DEG:
        return None
    sc = lean_stations(col.piece, col.axis, c, pitch_mm)
    if sc is None:
        return None
    st, dropped = sc
    return Column(stations=st, piece=col.piece, kind=col.kind, axis=col.axis,
                  width_mm=col.width_mm, rail_a=list(col.rail_a), rail_b=list(col.rail_b),
                  dropped_mm=dropped)
