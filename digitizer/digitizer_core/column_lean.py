"""Crosses square to the LINE OF TEXT in the Column lane
(`cfg.lettering_columns_text_lean`, 2026-10-23).

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
from shapely.geometry import LineString, Polygon

from .columns import Column

# A lean under this is the station scan's own rounding, not a lean: the
# column keeps its original stations (caps, fans and mitres included).
MIN_LEAN_DEG = 0.5
# A cross shorter than this is a corner clipping, not a station (the same
# floor `outline_cut._scan_cross` applies to its scanline segments).
_MIN_SEG_MM = 0.05
_FAR = 200.0


def cross_direction(axis, house_deg: float) -> tuple[float, float, float]:
    """The cross direction the convention gives a straight piece of unit
    `axis` under the house cross `house_deg` (degrees, plan frame): a unit
    vector along the clamped house (`stage6_satin._clamp_to_span`) and the
    lean, in degrees, off the piece's own normal."""
    from .stage6_satin import _clamp_to_span
    tangent = math.atan2(axis[1], axis[0])
    cross = _clamp_to_span(math.radians(house_deg), tangent)
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


def lean_column(col: Column, house_deg: float, pitch_mm: float) -> Column:
    """`col` re-stationed under the house cross, or `col` itself where the
    convention leaves it: not straight, no axis, a lean under
    `MIN_LEAN_DEG`, or a scan that cannot station it."""
    if col.kind != "straight" or col.axis is None or not col.stations:
        return col
    cx, cy, lean = cross_direction(col.axis, house_deg)
    if lean < MIN_LEAN_DEG:
        return col
    sc = lean_stations(col.piece, col.axis, (cx, cy), pitch_mm)
    if sc is None:
        return col
    st, dropped = sc
    return Column(stations=st, piece=col.piece, kind=col.kind, axis=col.axis,
                  width_mm=col.width_mm, rail_a=list(col.rail_a), rail_b=list(col.rail_b),
                  dropped_mm=dropped)


def lean_columns(columns: list[Column], house_deg: float | None, pitch_mm: float) -> list[Column]:
    """Every column of a letter through `lean_column`; `house_deg` None is
    the lane as it was (the same list object). Inside `italic_lean`, a bar
    of an italic word is crossed along the word's stems instead."""
    if house_deg is None:
        return columns
    words = _ITALIC.get()
    word = _word_of(columns, words) if words else None
    if word is None:
        return [lean_column(c, float(house_deg), pitch_mm) for c in columns]
    return [italic_bar(c, word, pitch_mm) or lean_column(c, float(house_deg), pitch_mm)
            for c in columns]


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
