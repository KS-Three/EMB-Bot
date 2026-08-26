"""Re-check the satin-border ruling through the honest renderer.

The ruling (MASTER_SCOPE, 2026-08-25): borders go on shapes significant AND
smooth, never blanket. Measured then as blanket `border="auto"` spending +60%
stitches to WORSEN the silhouette, against `border="significant"` taking 4
shapes of 35 for +4%. Every one of those judgements was made through the
pre-2026-08-25 renderer, which had no light in it -- so this re-runs the same
three arms and reports stitch counts alongside the pictures.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from digitizer_core import stitchviz
from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "digitizer" / "testdata" / "photo" / "owl_kent.jpg"
OUT = Path(os.environ.get("RR_OUT", "/tmp/ruling_recheck"))
OUT.mkdir(parents=True, exist_ok=True)
PX_PER_MM = 16.0
ARMS = [("off", "BORDER OFF"), ("significant", "SIGNIFICANT  (shipped)"), ("auto", "BLANKET  (auto)")]


def _font(sz, bold=True):
    p = f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"
    return ImageFont.truetype(p, sz) if Path(p).exists() else ImageFont.load_default()


def main() -> None:
    results = []
    for mode, label in ARMS:
        cfg = PipelineConfig(border=mode)
        _, plan = digitize(str(SRC), cfg)
        design = plan_to_design(plan, name=f"owl_{mode}")
        st = sum(len(r.points) for b in plan.blocks for r in b.runs)
        cov = stitchviz.coverage(design)
        img = Image.open(io.BytesIO(stitchviz.render_png_bytes(design, px_per_mm=PX_PER_MM))).convert("RGB")
        print(f"  {mode:<12} cov={cov:.3f}  blocks={len(plan.blocks):<4} st={st}", flush=True)
        results.append((label, img, st, cov))

    base = results[0][2]
    W, gap, bar = 620, 10, 62
    tiles = []
    for label, img, st, cov in results:
        delta = "" if st == base else f"  ({(st - base) / base:+.0%} stitches)"
        t = Image.new("RGB", (W, W + bar), (255, 255, 255))
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, W, bar], fill=(28, 30, 36))
        d.text((12, 8), label, font=_font(21), fill=(255, 255, 255))
        d.text((12, 36), f"cov {cov:.3f} · {st:,} st{delta}", font=_font(13, False), fill=(178, 184, 196))
        sc = min(W / img.width, W / img.height)
        rw, rh = int(img.width * sc), int(img.height * sc)
        t.paste(img.resize((rw, rh), Image.LANCZOS), ((W - rw) // 2, bar + (W - rh) // 2))
        tiles.append(t)

    sheet = Image.new("RGB", (W * 3 + gap * 4, tiles[0].height + gap * 2), (242, 243, 246))
    for i, t in enumerate(tiles):
        sheet.paste(t, (gap + i * (W + gap), gap))
    out = OUT / "owl_border_ab.png"
    sheet.save(out)
    print(f"-> {out}", flush=True)


if __name__ == "__main__":
    main()
