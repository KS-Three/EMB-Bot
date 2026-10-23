"""OFF/ON crops for `cfg.pro_measured_values` (2026-10-23): fill stitch length,
satin spacing and bean pitch on the hat preset, each a 12 x 7 mm window drawn
as a 0.1 mm thread over red penetrations, OFF left, ON right.
Run: python -m tools.pro_values_render <out_dir>"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric, stitches
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

PX, W, H = 60, 12.0, 7.0          # px per mm, window mm


def runs_for(poly, **kw):
    reg = Region(shape_id="S1", polygon=poly, thread_index=5, thread_number=CHART[5].number,
                 area_mm2=poly.area, meta={"layer": 0})
    fab, c = get_fabric("structured_cap"), PipelineConfig(underlay=False, **kw)
    planned, _ = resolve_overlaps([reg], fab, c)
    blocks, _ = sequence(planned, fab, c)
    return [r for b in blocks for r in b.runs]


def panel(runs, centre, label):
    im = Image.new("RGB", (int(W * PX), int(H * PX) + 22), "white")
    d = ImageDraw.Draw(im)
    for r in runs:
        pts = [((x - centre[0] + W / 2) * PX, (y - centre[1] + H / 2) * PX + 22) for x, y in r.points]
        if len(pts) > 1:
            d.line(pts, fill=(120, 150, 215), width=int(0.1 * PX))
    for r in runs:
        for x, y in r.points:
            px, py = (x - centre[0] + W / 2) * PX, (y - centre[1] + H / 2) * PX + 22
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(200, 30, 30))
    d.rectangle([0, 0, im.width, 20], fill="white")
    d.text((4, 4), label, fill="black", font=ImageFont.load_default())
    return im


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    field = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])
    stripe = Polygon([(-15, -1.2), (15, -1.2), (15, 1.2), (-15, 1.2)])
    cases = {
        "fill_stitch_length": (field, (9.0, 6.5), {"edge_cap": "none"}, lambda r: r.kind == stitches.FILL,
                               "fill stitch 3.0 -> 3.49 mm"),
        "satin_spacing": (stripe, (0.0, 0.0), {"edge_cap": "none"}, lambda r: r.kind == stitches.SATIN,
                          "satin spacing 0.40 -> 0.37 mm"),
        "bean_pitch": (field, (12.0, 8.0), {"edge_cap": "bean"}, lambda r: r.role == stitches.ROLE_EDGE_CAP,
                       "bean cap pitch 0.73 -> 0.95 mm"),
    }
    for name, (poly, centre, kw, keep, label) in cases.items():
        pair = [panel([r for r in runs_for(poly, pro_measured_values=on, **kw) if keep(r)], centre,
                      f"{label}  [{'ON' if on else 'OFF'}]") for on in (False, True)]
        sheet = Image.new("RGB", (pair[0].width * 2 + 8, pair[0].height), "white")
        sheet.paste(pair[0], (0, 0))
        sheet.paste(pair[1], (pair[0].width + 8, 0))
        sheet.save(out / f"{name}.png")
        print(name, sheet.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
