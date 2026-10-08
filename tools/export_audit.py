"""Python half of tools/export-audit.mjs: the service writers, and the renders.

Two subcommands, both deliberately dumb — every comparison lives on the Node
side, the way `tools/crossval_decode.py` is split from its harness.

  write  DESIGNS.json OUTDIR FMT [FMT ...]
      For every design in DESIGNS.json ({name: design}), write OUTDIR/
      <name>.svc.<fmt> through EXACTLY the service's `/export` body —
      `adapter.design_to_pattern` then `formats.write` — minus HTTP.

  render SPEC.json OUT.png
      Draw a row of panels, one per stitch stream, each fitted to its own
      sewn extents so an orientation error shows as one (a shared frame would
      hide a mirror inside a translation). SPEC is
      {"title": str, "panels": [{"title": str, "segs": [[x0,y0,x1,y1,"#rgb"]],
        "travel": [[x0,y0,x1,y1]]}]}, in design frame (+y UP, 0.1 mm units).

Reading files back is NOT done here: that is `tools/crossval_decode.py`,
the same pystitch call the crossval harness and preview-vs-dst make.
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "digitizer"))


def write(designs_path: str, outdir: str, fmts: list[str]) -> None:
    from digitizer_core.adapter import design_to_pattern
    from digitizer_service import formats

    with open(designs_path) as fh:
        designs = json.load(fh)
    os.makedirs(outdir, exist_ok=True)
    for name, design in designs.items():
        for fmt in fmts:
            # A fresh pattern per format: a writer is free to mutate it.
            data = formats.write(design_to_pattern(design, label=name[:16]), fmt)
            with open(os.path.join(outdir, f"{name}.svc.{fmt}"), "wb") as fh:
                fh.write(data)


PANEL = 420
PAD = 18
HEAD = 46


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def render(spec_path: str, out: str) -> None:
    from PIL import Image, ImageDraw

    with open(spec_path) as fh:
        spec = json.load(fh)
    panels = spec["panels"]
    cols = min(5, len(panels))
    rows = (len(panels) + cols - 1) // cols
    img = Image.new("RGB", (cols * PANEL, rows * (PANEL + HEAD) + 30), (250, 248, 243))
    dr = ImageDraw.Draw(img)
    dr.text((8, 8), spec.get("title", ""), fill=(0, 0, 0))
    for k, p in enumerate(panels):
        ox = (k % cols) * PANEL
        oy = 30 + (k // cols) * (PANEL + HEAD)
        dr.rectangle([ox + 2, oy + 2, ox + PANEL - 3, oy + PANEL + HEAD - 3], outline=(200, 196, 188))
        for i, line in enumerate(p["title"].split("\n")[:3]):
            dr.text((ox + 8, oy + 6 + 13 * i), line, fill=(0, 0, 0))
        segs = p.get("segs") or []
        if not segs:
            dr.text((ox + PANEL // 2 - 30, oy + HEAD + PANEL // 2), "(nothing)", fill=(160, 0, 0))
            continue
        xs = [v for s in segs for v in (s[0], s[2])]
        ys = [v for s in segs for v in (s[1], s[3])]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        span = max(x1 - x0, y1 - y0, 1)
        sc = (PANEL - 2 * PAD) / span
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

        def m(x, y):  # design frame +y UP -> raster +y DOWN
            return (ox + PANEL / 2 + (x - cx) * sc, oy + HEAD + PANEL / 2 - (y - cy) * sc)

        for t in p.get("travel") or []:
            dr.line([m(t[0], t[1]), m(t[2], t[3])], fill=(205, 205, 215), width=1)
        for s in segs:
            dr.line([m(s[0], s[1]), m(s[2], s[3])], fill=_hex(s[4]), width=1)
    img.save(out)


if __name__ == "__main__":
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "write":
        write(args[0], args[1], args[2:])
    elif cmd == "render":
        render(args[0], args[1])
    else:
        raise SystemExit(f"unknown subcommand {cmd!r}")
