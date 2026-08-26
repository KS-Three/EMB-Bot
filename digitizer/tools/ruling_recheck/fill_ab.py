"""Regenerate the Lane A side-by-side: filled vs thread-paint, per fixture.

Two arms, exactly as the 2026-08-25 fill-coverage brief describes them:

  filled       PipelineConfig() with NO forced_class -- the photo classifies on
               its own, auto_photo_tier returns None, fill_technique stays
               "tatami". There is no other way to get the filled arm: an
               explicit fill_technique="tatami" reads as "no choice made" and
               loses to the auto route (config.py:919's sentinel trap).
  thread-paint PipelineConfig(forced_class="photo_subject") -- hits the auto
               route, which returns "streamline".

Output: one PNG per fixture, [source | filled | thread-paint], labelled with
the class each arm actually ran under, coverage, block and stitch counts.
"""
from __future__ import annotations

import io
import os
import sys
import time
import traceback
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from digitizer_core import stitchviz
from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "digitizer" / "testdata" / "photo"
OUT = Path(os.environ.get("RR_OUT", "/tmp/ruling_recheck"))
OUT.mkdir(parents=True, exist_ok=True)

PX_PER_MM = 16.0  # was 6.0 -- below the module default, where the sheen dies
NAMES = ["owl_kent.jpg", "photo_sunset_backlit.png", "photo_dof_meadow.png", "drone_render.png"]


def _font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def run_arm(path: Path, forced: str | None):
    """One arm. Returns (PIL image, stats dict)."""
    cfg = PipelineConfig(forced_class=forced) if forced else PipelineConfig()
    t0 = time.time()
    result, plan = digitize(str(path), cfg)
    design = plan_to_design(plan, name=path.stem)
    cov = stitchviz.coverage(design)
    png = stitchviz.render_png_bytes(design, px_per_mm=PX_PER_MM)
    img = Image.open(io.BytesIO(png)).convert("RGB")
    # Count off the PLAN, not the design dict: the design is a FLAT stitch
    # record list (jump/trim/color interleaved), so its length is not a
    # stitch count and it has no per-block nesting to sum over.
    blocks = len(plan.blocks)
    stitches = sum(len(run.points) for b in plan.blocks for run in b.runs)
    return img, {
        "class": result.design_class,
        "cov": cov,
        "blocks": blocks,
        "stitches": stitches,
        "secs": time.time() - t0,
    }


def panel(img: Image.Image, title: str, sub: str, w: int, h: int) -> Image.Image:
    """Letterbox `img` into a w x h tile with a title bar above it."""
    bar = 54
    tile = Image.new("RGB", (w, h + bar), (255, 255, 255))
    d = ImageDraw.Draw(tile)
    d.rectangle([0, 0, w, bar], fill=(28, 30, 36))
    d.text((12, 6), title, font=_font(20), fill=(255, 255, 255))
    d.text((12, 30), sub, font=_font(14), fill=(178, 184, 196))
    scale = min(w / img.width, h / img.height)
    rw, rh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    tile.paste(img.resize((rw, rh), Image.LANCZOS), ((w - rw) // 2, bar + (h - rh) // 2))
    return tile


def main(names: list[str]) -> None:
    for name in names:
        src_path = FIXTURES / name
        if not src_path.exists():
            print(f"MISSING {src_path}", flush=True)
            continue
        print(f"=== {name} ===", flush=True)
        try:
            filled, fs = run_arm(src_path, None)
            print(f"  filled       class={fs['class']:<14} cov={fs['cov']:.3f} "
                  f"blocks={fs['blocks']:<4} st={fs['stitches']:<7} {fs['secs']:.0f}s", flush=True)
            paint, ps = run_arm(src_path, "photo_subject")
            print(f"  thread-paint class={ps['class']:<14} cov={ps['cov']:.3f} "
                  f"blocks={ps['blocks']:<4} st={ps['stitches']:<7} {ps['secs']:.0f}s", flush=True)
        except Exception:
            traceback.print_exc()
            continue

        src = Image.open(src_path).convert("RGB")
        W, H = 620, 620
        tiles = [
            panel(src, "SOURCE", name, W, H),
            panel(filled, "FILLED  (tatami)",
                  f"class {fs['class']} · cov {fs['cov']:.3f} · {fs['blocks']} blocks · {fs['stitches']:,} st", W, H),
            panel(paint, "THREAD-PAINT  (streamline)",
                  f"class {ps['class']} · cov {ps['cov']:.3f} · {ps['blocks']} blocks · {ps['stitches']:,} st", W, H),
        ]
        gap = 10
        sheet = Image.new("RGB", (W * 3 + gap * 4, tiles[0].height + gap * 2), (242, 243, 246))
        for i, t in enumerate(tiles):
            sheet.paste(t, (gap + i * (W + gap), gap))
        out = OUT / f"{src_path.stem}_fill_ab.png"
        sheet.save(out)
        print(f"  -> {out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or NAMES)
