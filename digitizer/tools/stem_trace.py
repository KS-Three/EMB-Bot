#!/usr/bin/env python
"""Where does a thin lettering stem go? The lowercase 'i' trace (2026-10-13).

PR #887 found that at 80 mm the synthetic 'i' stem in
`testdata/synthetic/lowercase_aileron.png` is tagged as lettering and sews
no satin. This traces the glyphs `i l I L j J` through the same digitize
(`forced_class="flat"`, the Column lane ON, as #887 ran it) and prints, per
region the glyph owns: its area against the small-shape rescue's floor
(`cfg.min_detail_mm`^2), its long and short side, whether the text tagger
took it, and what thread it sewed (run / satin / underlay stitches).

Finding, measured by this tool (80 mm; `tests/test_small_stem.py` pins it):

- the 'i' stem is NOT dropped and NOT merged with its dot. It is its own
  lettering region of 2.124 mm^2 (0.57 x 3.73 mm), and stage 7's small-shape
  rescue (`routes_to_run`: area < `min_detail_mm`^2 = 2.25) sends it to the
  RUN tier, a two-line outline, BEFORE the Column lane is asked. The capital
  I at the same 0.57 mm width is 4.87 mm tall (2.771 mm^2), clears the floor,
  and sews satin. At 120 mm the i stem is 5.126 mm^2 and sews satin;
- the 'l' (3.129 mm^2 at 80 mm, 1.03 mm wide) sews satin at both sizes;
- the 'i' DOT is lost at 80 mm, by a different rule: stage 3's run-tier
  loop floor drops it (0.446 mm^2, 0.75 mm across, perimeter proxy
  2 x 0.75 = 1.5 mm against `machine.RUN_MIN_LOOP_MM` 2.2; with that floor
  at 1.0 the dot comes back as a 49th region). At 120 mm the dot is 1.12 mm
  across (proxy 2.24, just clearing 2.2) and sews as a non-lettering run of
  20 points. Not touched here: the floor is a cloth value (ROADMAP gate 1);
- the rule is the area floor, not the letter case: a capital I at 31.6 px/mm
  (0.51 x 4.34 mm, 2.196 mm^2) runs too (`--word HILTIL 18.42`), and a stem
  narrower than `machine.SATIN_MIN_CROSS_MM` (0.5) stays a run even with the
  flag (the same I at 36 px/mm is 0.44 mm across);
- `cfg.lettering_columns_small_stem` (default OFF) lets a lettering stem under
  the floor (long side >= `min_detail_mm`, short side >= 0.5, long / short
  >= 6) into the lane. The corpus sets the aspect bar: the phone screenshot
  has seven lettering shapes under the floor that are stems by length alone
  (`--census screenshot`); aspect 3.1-4.1 at 0.63-0.90 mm across stay run.

    python -m tools.stem_trace [WIDTH_MM ...] [--small-stem] [--word TEXT]
    python -m tools.stem_trace 80 --render DIR     # OFF / ON stitch-path zoom
    python -m tools.stem_trace --census screenshot # lettering shapes under the floor

`--word TEXT` draws TEXT in the same CC0 face at the fixture's pixels per
mm (no image is kept) so a glyph the fixture does not carry (the j) can be
read; the default word is the fixture itself.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from tools.lowercase_angle import FIXTURE, FONT_SIZE, mm_to_px  # noqa: E402

GLYPHS = "ilIL" + "jJ"


def word_image(text: str, out: Path) -> dict:
    """Draw `text` (one line, FONT_SIZE) to `out`; -> the glyph-box meta in
    the fixture's shape. Same face and size as the fixture."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=FONT_SIZE)
    margin = 60
    width = int(font.getlength(text)) + 2 * margin
    height = FONT_SIZE * 2 + 2 * margin
    img = Image.new("RGB", (width, height), "white")
    ImageDraw.Draw(img).text((margin, margin), text, font=font, fill="black")
    glyphs = []
    for i, ch in enumerate(text):
        x = margin + font.getlength(text[:i])
        bb = font.getbbox(ch)
        glyphs.append(dict(ch=ch, line=0, box=[x + bb[0], margin + bb[1], x + bb[2], margin + bb[3]]))
    img.save(out)
    return dict(image=[width, height], glyphs=glyphs)


def _sides(poly):
    import math
    pts = list(poly.minimum_rotated_rectangle.exterior.coords)
    a = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    b = math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
    return max(a, b), min(a, b)


def _glyph_at(meta, px, py):
    best, bd = None, 1e9
    for g in meta["glyphs"]:
        x0, y0, x1, y1 = g["box"]
        if x0 - 4 <= px <= x1 + 4 and y0 - 4 <= py <= y1 + 4:
            d = abs(px - (x0 + x1) / 2.0)
            if d < bd:
                best, bd = g, d
    return best


def trace(width_mm: float, small_stem: bool = False, word: str | None = None,
          tmp: Path | None = None):
    """-> (rows, result, plan, meta). One row per region in a traced glyph."""
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.columns import is_lettering, is_thin_stem
    if word:
        path = (tmp or Path(".")) / "stem_trace_word.png"
        meta = word_image(word, path)
    else:
        path = FIXTURE.with_suffix(".png")
        meta = json.loads(FIXTURE.with_suffix(".json").read_text(encoding="utf-8"))
    cfg = PipelineConfig(target_width_mm=width_mm, forced_class="flat",
                         **({"lettering_columns_small_stem": True} if small_stem else {}))
    result, plan = digitize(path, cfg)
    to_px, s = mm_to_px(result, meta["image"])
    sewn = {}
    for _b, run in plan.iter_runs():
        d = sewn.setdefault(run.shape_id, {})
        d[run.kind] = d.get(run.kind, 0) + len(run.points)
    floor = cfg.min_detail_mm ** 2
    rows = []
    for r in result.regions:
        c = r.polygon.centroid
        g = _glyph_at(meta, *to_px(c.x, c.y))
        if g is None or g["ch"] not in GLYPHS:
            continue
        long_s, short_s = _sides(r.polygon)
        rows.append(dict(ch=g["ch"], shape=r.shape_id, lettering=bool(is_lettering(r, cfg)),
                         area=round(r.polygon.area, 3), floor=floor, long=round(long_s, 2),
                         short=round(short_s, 2), aspect=round(long_s / max(short_s, 1e-9), 1),
                         under_floor=r.polygon.area < floor,
                         thin_stem=bool(is_thin_stem(r.polygon, cfg.min_detail_mm)),
                         sewn=sewn.get(r.shape_id, {})))
    return rows, result, plan, meta, to_px, s


def tier_of(row) -> str:
    kinds = set(row["sewn"])
    return "satin" if "satin" in kinds else ("run" if "run" in kinds else
                                              "fill" if "fill" in kinds else "none")


def render_zoom(width_mm: float, out_dir: Path, chars: str = "iIl", ppm: float = 120.0):
    """OFF above ON, the STITCH PATH of each glyph at `ppm` px per mm
    (satin dark, underlay blue, travel green, run red). -> files written."""
    import cv2
    out_dir.mkdir(parents=True, exist_ok=True)
    ink = {"satin": (60, 60, 60), "underlay": (215, 160, 120), "travel": (120, 190, 120),
           "run": (40, 40, 200)}
    shots = {}
    for on in (False, True):
        _rows, result, plan, meta, to_px, s = trace(width_mm, small_stem=on)
        cx, cy = to_px(0.0, 0.0)
        for ch in chars:
            line = 1 if ch.islower() else 0
            g = next(g for g in meta["glyphs"] if g["ch"] == ch and g["line"] == line)
            bx0, by0 = (g["box"][0] - cx) / s - 0.6, (g["box"][1] - cy) / s - 0.6
            bx1, by1 = (g["box"][2] - cx) / s + 0.6, (g["box"][3] - cy) / s + 0.6
            pane = np.full((int((by1 - by0) * ppm), int((bx1 - bx0) * ppm), 3), 255, np.uint8)

            def P(p):
                return (int(round((p[0] - bx0) * ppm)), int(round((p[1] - by0) * ppm)))
            for kind in ("travel", "underlay", "run", "satin"):
                for _b, run in plan.iter_runs():
                    if run.kind != kind:
                        continue
                    for a, b in zip(run.points[:-1], run.points[1:]):
                        cv2.line(pane, P(a), P(b), ink[kind], 1, cv2.LINE_AA)
            shots[(on, ch)] = pane
    written = []

    def label(im, text):
        bar = np.full((40, im.shape[1], 3), 255, np.uint8)
        cv2.putText(bar, text, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        return np.vstack([bar, im])
    for ch in chars:
        a, b = shots[(False, ch)], shots[(True, ch)]
        w = max(a.shape[1], b.shape[1], 700)
        pad = lambda im: np.pad(im, ((0, 0), (0, w - im.shape[1]), (0, 0)), constant_values=255)
        pair = np.vstack([label(pad(a), f"OFF (shipped) {width_mm:g} mm '{ch}'"),
                          np.full((6, w, 3), 200, np.uint8),
                          label(pad(b), "ON  lettering_columns_small_stem")])
        p = out_dir / f"stem-{width_mm:g}mm-{'cap-' if ch.isupper() else ''}{ch.lower()}.png"
        cv2.imwrite(str(p), pair)
        written.append(p)
    return written


def census(name: str, small_stem: bool = False) -> list[dict]:
    """Every lettering shape of corpus fixture `name` under the area floor,
    with its sides and what it sewed (the fixtures of `lowercase_angle.CORPUS`)."""
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.columns import is_lettering, is_thin_stem
    from tools.lowercase_angle import CORPUS
    rel, width, garment, *_ = CORPUS[name]
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                         **({"lettering_columns_small_stem": True} if small_stem else {}))
    result, plan = digitize(ROOT / "testdata" / rel, cfg)
    sewn = {}
    for _b, run in plan.iter_runs():
        d = sewn.setdefault(run.shape_id, {})
        d[run.kind] = d.get(run.kind, 0) + len(run.points)
    out = []
    for r in result.regions:
        if is_lettering(r, cfg) and r.polygon.area < cfg.min_detail_mm ** 2:
            long_s, short_s = _sides(r.polygon)
            out.append(dict(shape=r.shape_id, area=round(r.polygon.area, 3),
                            long=round(long_s, 2), short=round(short_s, 2),
                            aspect=round(long_s / max(short_s, 1e-9), 1),
                            thin_stem=bool(is_thin_stem(r.polygon, cfg.min_detail_mm)),
                            sewn=sewn.get(r.shape_id, {})))
    return out


def main(argv: list[str]) -> None:
    if {"-h", "--help"} & set(argv):
        print(__doc__.strip())
        return
    if "--census" in argv:
        name = argv[argv.index("--census") + 1]
        for row in census(name, "--small-stem" in argv):
            print(f"  {row['shape']} area {row['area']:.3f} {row['long']:.2f} x {row['short']:.2f} mm "
                  f"aspect {row['aspect']:4.1f} thin_stem={row['thin_stem']} sewn {row['sewn']}")
        return
    widths = [float(a) for a in argv if a.replace(".", "", 1).isdigit()] or [80.0]
    if "--render" in argv:
        out = Path(argv[argv.index("--render") + 1])
        for w in widths:
            for p in render_zoom(w, out):
                print(f"wrote {p}")
        return
    word = argv[argv.index("--word") + 1] if "--word" in argv else None
    for w in widths:
        rows, _res, plan, _meta, _px, s = trace(w, "--small-stem" in argv, word)
        print(f"{w:g} mm  {s:.3f} px/mm  small_stem={'--small-stem' in argv}  "
              f"stitches {plan.stats.stitch_count}  trims {plan.stats.trims}")
        for r in sorted(rows, key=lambda r: (r["ch"], r["shape"])):
            print(f"  {r['ch']} {r['shape']} lettering={str(r['lettering']):5s} "
                  f"area {r['area']:6.3f} vs floor {r['floor']:.2f} "
                  f"({'UNDER' if r['under_floor'] else 'over '}) "
                  f"{r['long']:.2f} x {r['short']:.2f} mm aspect {r['aspect']:4.1f} "
                  f"thin_stem={str(r['thin_stem']):5s} -> {tier_of(r)} {r['sewn']}")


if __name__ == "__main__":
    main(sys.argv[1:])
