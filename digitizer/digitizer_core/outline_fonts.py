"""Outline (TrueType / OpenType) fonts, digitized on demand.

The pre-digitized library (`src/fonts/*.embf`) carries hand-authored satin
columns per glyph and sews in the browser. This module is the OTHER kind of
font: a plain outline font whose glyphs have no stitch data at all. Its text
is laid out here from the font's own outlines, each glyph handed to the
pipeline as a lettering-tagged region, and stitched by the same Column lane
(`columns.py`, `outline_cut.letter_columns`) that sews a word traced out of a
customer's artwork — the construction Kent's 2026-07-24 "no outline fonts"
ruling predates (that ruling rejected the browser engine's auto-trace of
glyph bitmaps; the Column lane did not exist). Reopened by Kent 2026-11-06:
"not pre-digitized, but embot will have the ability to digitize them (slower,
but easier than importing an image of the font)".

Against the image route (render the word to a PNG, run stages 0-7) this is
exact: the outlines are the font's own curves, not a trace of their raster;
every glyph is a letter by construction, so no OCR/text-cluster tagging can
miss (the PNG route tagged 0 of Lobster's 5 shapes as letters in the spike);
and stages 0-4 are skipped. Measured 2026-11-06 on Kent's laptop: Fremont in
Montserrat Bold at cap 12 mm, 15.5 s against 24.2 s via PNG; ENTHUSIAST at
cap 6 mm, 2.0 s against 14.7 s.

What ships: `outline_fonts/fonts.json` + the TTFs, fetched UNMODIFIED from
google/fonts at a pinned commit by `tools/fetch_outline_fonts.py` (OFL-1.1
only, licence text beside each family). A variable font is instanced in
memory to the registry's named weights; the file on disk is the original.

Layout here is deliberately simple: cmap lookup per character (no ligatures,
no shaping), advance widths, pair kerning from the `kern` table and from
GPOS `kern` PairPos lookups (format 1 and 2, the Latin case). Enough for a
wordmark; not a text engine.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from functools import lru_cache
from pathlib import Path

from shapely.affinity import scale as _scale, translate
from shapely.geometry import Polygon
from shapely.validation import make_valid

from .pipeline import BackgroundInfo, PipelineResult
from .regions import Region, assign_shape_ids
from .threads import chart_for, rgb_to_lab

FONTS_DIR = Path(__file__).resolve().parent / "outline_fonts"
REGISTRY = FONTS_DIR / "fonts.json"

# Curve flattening: segments per Bezier. 8 puts a 12 mm cap's roundest bowl
# within ~0.01 mm of the curve; stage 4's own simplify tolerance is coarser.
CURVE_SEGMENTS = 8
MAX_TEXT_CHARS = 200
MAX_LINES = 6
# Line pitch when the font's own ascender/descender are missing.
LINE_PITCH_EM = 1.2


class OutlineFontError(ValueError):
    """A bad request: unknown font, empty text, no sewable glyph."""


@dataclass(frozen=True)
class OutlineFont:
    key: str
    name: str
    family: str
    group: str
    style: str
    weight: int
    file: str
    variable: bool
    license_id: str
    license_file: str
    source: str
    sha256: str

    def public(self) -> dict:
        return {
            "key": self.key, "name": self.name, "family": self.family,
            "group": self.group, "style": self.style, "weight": self.weight,
            "variable": self.variable, "licenseId": self.license_id,
            "source": self.source, "kind": "outline",
        }


@lru_cache(maxsize=1)
def registry() -> dict[str, OutlineFont]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    out: dict[str, OutlineFont] = {}
    for f in data["fonts"]:
        out[f["key"]] = OutlineFont(
            key=f["key"], name=f["name"], family=f["family"], group=f["group"],
            style=f["style"], weight=int(f["weight"]), file=f["file"],
            variable=bool(f["variable"]), license_id=f["licenseId"],
            license_file=f["licenseFile"], source=f["source"], sha256=f["sha256"])
    return out


def list_fonts() -> list[dict]:
    return [f.public() for f in registry().values()]


def font_path(key: str) -> Path:
    f = registry().get(key)
    if f is None:
        raise OutlineFontError(f"unknown outline font {key!r}")
    return FONTS_DIR / f.file


def license_text(key: str) -> str:
    f = registry().get(key)
    if f is None:
        raise OutlineFontError(f"unknown outline font {key!r}")
    return (FONTS_DIR / f.license_file).read_text(encoding="utf-8", errors="replace")


# --- font loading -----------------------------------------------------------

@lru_cache(maxsize=8)
def _load(key: str):
    """A fontTools TTFont for the registry key, instanced to its weight when
    the file is variable. Cached: instancing EB Garamond takes ~0.5 s."""
    from fontTools.ttLib import TTFont
    f = registry().get(key)
    if f is None:
        raise OutlineFontError(f"unknown outline font {key!r}")
    font = TTFont(str(FONTS_DIR / f.file))
    if f.variable and "fvar" in font:
        from fontTools.varLib import instancer
        axes = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in font["fvar"].axes}
        loc = {}
        if "wght" in axes:
            lo, _d, hi = axes["wght"]
            loc["wght"] = min(max(float(f.weight), lo), hi)
        for tag, (_lo, default, _hi) in axes.items():
            if tag != "wght":
                loc[tag] = default            # wdth / opsz at the font's default
        font = instancer.instantiateVariableFont(font, loc, inplace=True)
    return font


class _FlatPen:
    """Minimal fontTools pen: closed polylines in font units."""
    def __init__(self, glyphset, segs: int = CURVE_SEGMENTS):
        from fontTools.pens.basePen import BasePen

        rings: list[list[tuple[float, float]]] = []

        class P(BasePen):
            def __init__(self):
                super().__init__(glyphset)
                self.cur: list[tuple[float, float]] = []

            def _moveTo(self, p):
                self.cur = [p]

            def _lineTo(self, p):
                self.cur.append(p)

            def _curveToOne(self, p1, p2, p3):
                p0 = self.cur[-1]
                for i in range(1, segs + 1):
                    t = i / segs; m = 1 - t
                    self.cur.append((m*m*m*p0[0] + 3*m*m*t*p1[0] + 3*m*t*t*p2[0] + t*t*t*p3[0],
                                     m*m*m*p0[1] + 3*m*m*t*p1[1] + 3*m*t*t*p2[1] + t*t*t*p3[1]))

            def _qCurveToOne(self, p1, p2):
                p0 = self.cur[-1]
                for i in range(1, segs + 1):
                    t = i / segs; m = 1 - t
                    self.cur.append((m*m*p0[0] + 2*m*t*p1[0] + t*t*p2[0],
                                     m*m*p0[1] + 2*m*t*p1[1] + t*t*p2[1]))

            def _closePath(self):
                if len(self.cur) >= 3:
                    rings.append(self.cur)
                self.cur = []

            def _endPath(self):
                self._closePath()

        self.pen = P()
        self.rings = rings


def _polygon_parts(geom):
    """Every Polygon inside a Polygon / MultiPolygon / GeometryCollection."""
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            yield from _polygon_parts(g)


def _winding(ring: np.ndarray, x: float, y: float) -> int:
    """Winding number of (x, y) about a closed ring (Sunday's algorithm)."""
    x0 = ring[:, 0]; y0 = ring[:, 1]
    x1 = np.roll(x0, -1); y1 = np.roll(y0, -1)
    cross = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
    up = (y0 <= y) & (y1 > y) & (cross > 0)
    down = (y0 > y) & (y1 <= y) & (cross < 0)
    return int(up.sum()) - int(down.sum())


def _rings_to_polygons(rings) -> list[Polygon]:
    """A glyph's contours -> filled polygons under the NONZERO winding rule,
    which is what a font rasterizer applies.

    Not even-odd nesting, and not "outer minus inner": a variable font keeps
    OVERLAPPING contours (Roboto's B is two bowls drawn over a stem, so its
    outlines interpolate), and a TrueType contour may touch itself
    (Montserrat's B draws both counters as one figure-of-eight ring pinched
    at the waist). Nesting read the first as two bodies and the second as
    one counter, and "Fab" came back as six regions (2026-11-06). So: node
    every contour against every other, polygonize the linework into faces,
    keep each face whose winding number about all the contours is not zero,
    and dissolve the kept faces. The result carries its counters as holes.
    """
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union

    arrays = [np.asarray(r, dtype=np.float64) for r in rings if len(r) >= 3]
    arrays = [a for a in arrays if abs(_signed_area(a)) > 0]
    if not arrays:
        return []
    lines = [LineString(np.vstack([a, a[:1]])) for a in arrays]
    faces = list(polygonize(unary_union(lines)))
    keep = []
    for f in faces:
        pt = f.representative_point()
        if sum(_winding(a, pt.x, pt.y) for a in arrays) != 0:
            keep.append(f)
    if not keep:
        return []
    merged = unary_union(keep)
    out = []
    for p in _polygon_parts(merged):
        if not p.is_valid:
            p = make_valid(p)
        out.extend(q for q in _polygon_parts(p) if q.area > 0)
    return out


def _signed_area(a: np.ndarray) -> float:
    x = a[:, 0]; y = a[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# --- kerning ----------------------------------------------------------------

class _Kerner:
    """Pair kerning in font units: the legacy `kern` table plus GPOS PairPos
    under the `kern` feature — format 1 (explicit pairs) and format 2 (class
    pairs, kept as classes and answered per lookup, since expanding
    Montserrat's classes is ~1M pairs). First-glyph X advance only, which is
    what Latin kerning is; the first subtable that covers a pair wins, as
    in a shaper."""

    def __init__(self, font):
        self.pairs: dict[tuple[str, str], int] = {}
        self.class_tables: list[tuple[set, dict, dict, list]] = []
        if "kern" in font:
            for t in font["kern"].kernTables:
                for (a, b), v in getattr(t, "kernTable", {}).items():
                    self.pairs.setdefault((a, b), int(v))
        if "GPOS" not in font:
            return
        gpos = font["GPOS"].table
        if not gpos.FeatureList or not gpos.LookupList:
            return
        lookup_ids: list[int] = []
        for fr in gpos.FeatureList.FeatureRecord:
            if fr.FeatureTag == "kern":
                for i in fr.Feature.LookupListIndex:
                    if i not in lookup_ids:
                        lookup_ids.append(i)
        for li in lookup_ids:
            lookup = gpos.LookupList.Lookup[li]
            for st in lookup.SubTable:
                st = getattr(st, "ExtSubTable", st)
                if type(st).__name__ != "PairPos":
                    continue
                try:
                    cov = list(st.Coverage.glyphs)
                except AttributeError:
                    continue
                if st.Format == 1:
                    for g1, ps in zip(cov, st.PairSet):
                        for pvr in ps.PairValueRecord:
                            v = getattr(pvr.Value1, "XAdvance", 0) or 0
                            if v:
                                self.pairs.setdefault((g1, pvr.SecondGlyph), int(v))
                elif st.Format == 2:
                    c1 = dict(st.ClassDef1.classDefs) if st.ClassDef1 else {}
                    c2 = dict(st.ClassDef2.classDefs) if st.ClassDef2 else {}
                    self.class_tables.append((set(cov), c1, c2, st.Class1Record))

    def get(self, g1: str, g2: str) -> int:
        v = self.pairs.get((g1, g2))
        if v is not None:
            return v
        for cov, c1, c2, recs in self.class_tables:
            if g1 not in cov:
                continue
            k1 = c1.get(g1, 0)
            if k1 >= len(recs):
                continue
            c2recs = recs[k1].Class2Record
            k2 = c2.get(g2, 0)
            if k2 >= len(c2recs):
                continue
            v = getattr(c2recs[k2].Value1, "XAdvance", 0) or 0
            if v:
                return int(v)
        return 0


@lru_cache(maxsize=8)
def _kerner(key: str) -> _Kerner:
    return _Kerner(_load(key))


def _ranges(codepoints) -> list:
    """Sorted codepoints -> the Studio's coverage shape: a bare codepoint or
    an inclusive [lo, hi] run (`app/src/lib/fontCoverage.js`)."""
    out: list = []
    cps = sorted(codepoints)
    i = 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append(cps[i] if i == j else [cps[i], cps[j]])
        i = j + 1
    return out


@lru_cache(maxsize=64)
def coverage(key: str) -> list:
    """Codepoints the font draws, read from the file's cmap without
    instancing it (the full load is the slow part)."""
    from fontTools.ttLib import TTFont
    f = registry().get(key)
    if f is None:
        raise OutlineFontError(f"unknown outline font {key!r}")
    font = TTFont(str(FONTS_DIR / f.file), lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        return _ranges(cp for cp in cmap if cp > 0x20)
    finally:
        font.close()


# --- layout -----------------------------------------------------------------

@dataclass
class Letter:
    char: str
    line: int
    polygon: Polygon          # mm, y DOWN, before centring


@dataclass
class Layout:
    letters: list[Letter]
    width_mm: float
    height_mm: float
    cap_mm: float
    unsupported: list[str]    # characters the font has no glyph for


def _metrics(font) -> tuple[float, float, float, float]:
    """(unitsPerEm, cap height, ascender, descender) in font units."""
    upem = float(font["head"].unitsPerEm)
    os2 = font["OS/2"] if "OS/2" in font else None
    cap = float(getattr(os2, "sCapHeight", 0) or 0)
    if cap <= 0:
        cmap = font.getBestCmap()
        name = cmap.get(ord("H")) or cmap.get(ord("I")) or cmap.get(ord("E"))
        if name:
            fp = _FlatPen(font.getGlyphSet()); font.getGlyphSet()[name].draw(fp.pen)
            ys = [y for r in fp.rings for _, y in r]
            cap = max(ys) if ys else 0.0
    if cap <= 0:
        cap = 0.7 * upem
    asc = float(getattr(os2, "sTypoAscender", 0) or font["hhea"].ascent)
    desc = float(getattr(os2, "sTypoDescender", 0) or font["hhea"].descent)
    return upem, cap, asc, desc


ALIGNS = ("left", "center", "right")


def layout_text(key: str, text: str, *, width_mm: float | None = None,
                cap_mm: float | None = None, letter_spacing_mm: float = 0.0,
                line_spacing: float = 1.0, align: str = "center") -> Layout:
    """Lay `text` out in font `key` at either a target width (the whole block,
    the Studio's `sizeMm`) or a cap height. Lines are justified against the
    widest by `align` (the Studio's "Justify lines"). Returns mm polygons,
    y down, origin at the block's bbox centre."""
    if align not in ALIGNS:
        raise OutlineFontError(f"align must be one of {', '.join(ALIGNS)}")
    if not isinstance(text, str) or not text.strip():
        raise OutlineFontError("text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise OutlineFontError(f"text is {len(text)} characters; the limit is {MAX_TEXT_CHARS}")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(lines) > MAX_LINES:
        raise OutlineFontError(f"text has {len(lines)} lines; the limit is {MAX_LINES}")
    if (width_mm is None) == (cap_mm is None):
        raise OutlineFontError("give exactly one of width_mm / cap_mm")
    for v, name in ((width_mm, "width_mm"), (cap_mm, "cap_mm")):
        if v is not None and not (isinstance(v, (int, float)) and v > 0):
            raise OutlineFontError(f"{name} must be a positive number")

    font = _load(key)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    kern = _kerner(key)
    upem, cap_units, asc, desc = _metrics(font)
    pitch_units = (asc - desc) * line_spacing if asc > desc else upem * LINE_PITCH_EM * line_spacing

    unsupported: list[str] = []
    raw: list[tuple[str, int, Polygon]] = []     # (char, line, polygon in font units, y UP)
    line_widths: list[float] = []
    for li, line in enumerate(lines):
        x = 0.0
        prev = None
        y_base = -li * pitch_units
        for ch in line:
            name = cmap.get(ord(ch))
            if name is None:
                if not ch.isspace() and ch not in unsupported:
                    unsupported.append(ch)
                if ch.isspace():
                    x += hmtx[cmap[ord(" ")]][0] if ord(" ") in cmap else upem * 0.25
                prev = None
                continue
            if prev is not None:
                x += kern.get(prev, name)
            if not ch.isspace():
                fp = _FlatPen(gs); gs[name].draw(fp.pen)
                for poly in _rings_to_polygons(fp.rings):
                    raw.append((ch, li, translate(poly, xoff=x, yoff=y_base)))
            x += hmtx[name][0]
            prev = name
        line_widths.append(x)
    if not raw:
        raise OutlineFontError("no glyph in this font draws any of that text")
    if align != "left" and len(lines) > 1:
        widest = max(line_widths)
        shift = {li: (widest - w) * (0.5 if align == "center" else 1.0)
                 for li, w in enumerate(line_widths)}
        raw = [(ch, li, translate(p, xoff=shift[li])) for ch, li, p in raw]

    # units -> mm; y flips (font y up, pipeline y down)
    polys = [_scale(p, xfact=1.0, yfact=-1.0, origin=(0, 0)) for _, _, p in raw]
    xs0 = min(p.bounds[0] for p in polys); xs1 = max(p.bounds[2] for p in polys)
    ys0 = min(p.bounds[1] for p in polys); ys1 = max(p.bounds[3] for p in polys)
    ink_w_units = xs1 - xs0
    n_gaps = sum(max(len(l) - 1, 0) for l in lines)
    if cap_mm is not None:
        s = cap_mm / cap_units
    else:
        # width = ink width * s + letter spacing between glyphs
        s = max(width_mm - n_gaps * letter_spacing_mm, 1e-6) / ink_w_units
    letters: list[Letter] = []
    # letter spacing: shift each glyph by its index in its line
    idx_in_line: dict[int, int] = {}
    seen_glyph: dict[tuple[int, str, float], int] = {}
    extra: list[float] = []
    for ch, li, p in raw:
        gkey = (li, ch, round(p.bounds[0], 3))
        if gkey not in seen_glyph:
            seen_glyph[gkey] = idx_in_line.get(li, 0)
            idx_in_line[li] = seen_glyph[gkey] + 1
        extra.append(seen_glyph[gkey] * letter_spacing_mm)
    for (ch, li, _), p, dx in zip(raw, polys, extra):
        q = _scale(p, xfact=s, yfact=s, origin=(0, 0))
        q = translate(q, xoff=dx)
        letters.append(Letter(char=ch, line=li, polygon=q))
    # centre on the block's bbox
    b = [l.polygon.bounds for l in letters]
    x0, y0 = min(v[0] for v in b), min(v[1] for v in b)
    x1, y1 = max(v[2] for v in b), max(v[3] for v in b)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    for l in letters:
        l.polygon = translate(l.polygon, xoff=-cx, yoff=-cy)
    return Layout(letters=letters, width_mm=x1 - x0, height_mm=y1 - y0,
                  cap_mm=cap_units * s, unsupported=unsupported)


# --- pipeline input ---------------------------------------------------------

def _resolve_thread(chart, thread_index, thread_rgb) -> int:
    if thread_index is not None and thread_rgb is not None:
        raise OutlineFontError("give one of thread_index / thread_rgb, not both")
    if thread_index is not None:
        if not isinstance(thread_index, int) or isinstance(thread_index, bool) \
                or not 0 <= thread_index < len(chart):
            raise OutlineFontError(f"thread_index must be an integer in [0, {len(chart) - 1}]")
        return thread_index
    rgb = thread_rgb if thread_rgb is not None else [0, 0, 0]
    if not (isinstance(rgb, (list, tuple)) and len(rgb) == 3
            and all(isinstance(c, (int, float)) and 0 <= c <= 255 for c in rgb)):
        raise OutlineFontError("thread_rgb must be three numbers in [0, 255]")
    import numpy as np
    return int(chart.nearest_index(rgb_to_lab(np.asarray([int(c) for c in rgb], dtype=np.float64))))


def build_text_result(key: str, text: str, cfg, *, width_mm: float | None = None,
                      cap_mm: float | None = None, letter_spacing_mm: float = 0.0,
                      line_spacing: float = 1.0, align: str = "center",
                      thread_index: int | None = None,
                      thread_rgb=None) -> tuple[PipelineResult, Layout]:
    """Typed text in an outline font -> a `PipelineResult` `plan_stitches`
    consumes unchanged, every glyph a lettering-tagged auto-tier region so
    the Column lane takes it (`columns.is_lettering`: `text_candidate`;
    `pipeline._lane_has_letters`: tier "auto"). Raises `OutlineFontError`
    (a ValueError) on a bad request, never a failed job."""
    layout = layout_text(key, text, width_mm=width_mm, cap_mm=cap_mm,
                         letter_spacing_mm=letter_spacing_mm, line_spacing=line_spacing,
                         align=align)
    chart = chart_for(cfg)
    ti = _resolve_thread(chart, thread_index, thread_rgb)
    regions: list[Region] = []
    for l in layout.letters:
        regions.append(Region(
            shape_id="", polygon=l.polygon, thread_index=ti,
            thread_number=chart[ti].number, area_mm2=float(l.polygon.area),
            source="outline_font",
            meta={"layer": 0, "tier": "auto", "text_candidate": True,
                  "text_cluster_id": f"T{l.line}", "glyph": l.char,
                  "outline_font": key},
        ))
    assign_shape_ids(regions)
    # The real word tagger, when the lane reads words (`cfg.lettering_words`):
    # it needs regions only, no raster.
    if getattr(cfg, "lettering_words", False):
        from .words import tag_words
        tag_words(regions, chart=chart)
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    palette = [{"brand": chart.label, "brand_id": chart.id, "number": chart[ti].number,
                "name": chart[ti].name, "rgb": list(chart[ti].rgb)}]
    warnings = []
    if layout.unsupported:
        warnings.append("This font has no glyph for: " + " ".join(layout.unsupported))
    result = PipelineResult(
        regions=regions, palette=palette,
        background=BackgroundInfo(detected=False, outline_mm=None, stitched=False),
        px_per_mm=None, design_size_mm=(layout.width_mm, layout.height_mm),
        warnings=warnings, segmenter="outline_font", debug_dir=None,
        source_pixels=None, design_class="flat",
    )
    return result, layout
