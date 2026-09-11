# digitizer/tools/pro_parity/overlay.py
"""Ours over the pro's, registered, on one canvas.

Pro in magenta, ours in cyan, overlap dark (multiply) — the convention every
print-registration viewer uses, so a misregistered edge reads as a coloured
fringe and an agreed one as black. Both sides go through
`stitchviz.render_design`, the Studio's lit-filament model, so what is
compared is what the product shows. Masks are taken FROM the renders
(thread pixel != fabric), so the diff masks and the picture agree by
construction. Spec §4.

    python tools/pro_parity/overlay.py --dir <out>/real/<slug>
    python tools/pro_parity/overlay.py --dir ... --crop 10 -5 40 15 --crop-name marine
    python tools/pro_parity/overlay.py --dir ... --by-thread
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true --against baseline
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import pairframe as pf                                        # noqa: E402
from digitizer_core.stitchviz import render_design             # noqa: E402
from skimage.color import deltaE_ciede2000                    # noqa: E402
from digitizer_core.threads import rgb_to_lab                 # noqa: E402
from thin_strokes import parse_flags                           # noqa: E402

WHITE = (255, 255, 255)
PRO_TINT = (255, 0, 255)      # RGB magenta
OURS_TINT = (0, 200, 255)     # RGB cyan
GHOST = 225                   # grey of the other side's silhouette on the *_only sheets
DEFAULT_PPM = 12.0
CROP_PPM = 36.0


def _fit_to_frame(design: dict, frame: pf.Frame) -> dict:
    """The design with nothing outside the frame, so `render_design`'s canvas
    is exactly the frame and pro and ours land on the same pixels.

    `render_design` sizes its canvas from every stitch AND jump record, and a
    machine file carries travel far outside what it sews: pystitch's DST
    writer splits the lead-in from the hoop origin into 12 mm jumps. A jump
    lays no thread (the renderer only breaks the path at it), so its position
    is clamped into the frame. Stitches fall outside the frame only for a
    crop window: each segment is clipped to the window (Liang-Barsky), a
    segment wholly outside becomes a break, and a segment that enters the
    window is redrawn from its entry point after a jump. A design already
    inside the frame comes back record for record, jumps clamped.
    """
    x0, x1, y0, y1 = frame.bounds_units

    def clamp(x, y):
        return min(max(x, x0), x1), min(max(y, y0), y1)

    def clip(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if p == 0:
                if q < 0:
                    return None
                continue
            t = q / p
            if p < 0:
                if t > t1:
                    return None
                t0 = max(t0, t)
            else:
                if t < t0:
                    return None
                t1 = min(t1, t)
        return ((round(a[0] + t0 * dx), round(a[1] + t0 * dy)),
                (round(a[0] + t1 * dx), round(a[1] + t1 * dy)))

    out = []
    prev = None      # last stitch position in the source, None after a break
    pen = None       # last point drawn in the output, None after a break
    for s in design["stitches"]:
        kind = s["type"]
        if kind != "stitch":
            if kind == "jump":
                cx, cy = clamp(s["x"], s["y"])
                out.append(dict(s, x=cx, y=cy))
            else:
                out.append(s)
            prev = pen = None
            continue
        p = (s["x"], s["y"])
        if prev is None:
            if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                out.append(s)
                pen = p
            prev = p
            continue
        seg = clip(prev, p)
        prev = p
        if seg is None:
            pen = None
            continue
        a, b = seg
        if pen != a:
            out.append({"x": a[0], "y": a[1], "type": "jump"})
            out.append({"x": a[0], "y": a[1], "type": "stitch"})
        out.append(s if b == p else {"x": b[0], "y": b[1], "type": "stitch"})
        pen = b
    return dict(design, stitches=out)


def render_side(design: dict, frame: pf.Frame) -> np.ndarray:
    d = pf.pin_frame(_fit_to_frame(design, frame), frame.bounds_units)
    return render_design(d, px_per_mm=frame.ppm, fabric_bgr=WHITE, pad_mm=frame.pad_mm, lit=True)


def thread_mask(img: np.ndarray) -> np.ndarray:
    return np.any(img < 250, axis=2)


def tint(img: np.ndarray, rgb: tuple) -> np.ndarray:
    """Thread pixels take the tint, keeping the filament shading as a
    brightness ramp (0.35..1.0 of the tint); fabric stays white."""
    m = thread_mask(img)
    L = img.astype(np.float32).mean(axis=2) / 255.0
    out = np.full_like(img, 255)
    bgr = (rgb[2], rgb[1], rgb[0])
    for c in range(3):
        ch = out[..., c]
        ch[m] = np.clip(bgr[c] * (0.35 + 0.65 * L[m]), 0, 255).astype(np.uint8)
    return out


def _only_sheet(only: np.ndarray, other: np.ndarray, rgb: tuple) -> np.ndarray:
    out = np.full(only.shape + (3,), 255, np.uint8)
    out[other] = GHOST
    out[only] = (rgb[2], rgb[1], rgb[0])
    return out


def _restrict(design: dict, blocks: set | None) -> dict:
    """The design's stitches limited to the given block indices (colour
    records kept so colours still advance)."""
    if blocks is None:
        return design
    keep, bi = [], 0
    for s in design["stitches"]:
        if s["type"] == "color":
            bi += 1
            keep.append(s)
        elif s["type"] in ("jump", "trim", "end") or bi in blocks:
            keep.append(s)
    return dict(design, stitches=keep)


def render_pair(pair: pf.Pair, reg: pf.Reg, ppm: float = DEFAULT_PPM, crop_mm=None,
                only_pro_block: int | None = None, only_ours_blocks: set | None = None,
                ours_path: Path | None = None, ours_rgb: list | None = None) -> dict:
    pro_d = pf.design_for(pair.pro_path, None, pair.pro_rgb, f"{pair.slug} pro")
    ours_d = pf.design_for(ours_path or pair.ours_path, reg, ours_rgb or pair.ours_rgb, f"{pair.slug} ours")
    # Compute frame from unrestricted designs to avoid sentinel bounds when restriction empties a side
    frame = pf.frame_for([pro_d, ours_d], ppm, crop_mm=crop_mm)
    # Apply restrictions only for rendering
    pro_d = _restrict(pro_d, {only_pro_block} if only_pro_block is not None else None)
    ours_d = _restrict(ours_d, only_ours_blocks)
    pro = render_side(pro_d, frame)
    ours = render_side(ours_d, frame)
    pm, om = thread_mask(pro), thread_mask(ours)
    pt, ot = tint(pro, PRO_TINT), tint(ours, OURS_TINT)
    over = (pt.astype(np.float32) * ot.astype(np.float32) / 255.0).astype(np.uint8)
    return {"frame": frame, "pro": pro, "ours": ours, "pro_mask": pm, "ours_mask": om,
            "overlay": over, "pro_only": pm & ~om, "ours_only": om & ~pm,
            "pro_only_img": _only_sheet(pm & ~om, om, PRO_TINT),
            "ours_only_img": _only_sheet(om & ~pm, pm, OURS_TINT)}


def _titled(img: np.ndarray, title: str) -> np.ndarray:
    bar = np.full((22, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, title, (6, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def write_overlay_set(out_dir: Path, r: dict, title: str, suffix: str = "") -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        f"overlay{suffix}.png": _titled(r["overlay"], title),
        f"pro_only{suffix}.png": _titled(r["pro_only_img"], title + "  PRO ONLY"),
        f"ours_only{suffix}.png": _titled(r["ours_only_img"], title + "  OURS ONLY"),
        f"flicker_pro{suffix}.png": r["pro"],
        f"flicker_ours{suffix}.png": r["ours"],
    }
    written = []
    for name, img in files.items():
        p = out_dir / name
        if not cv2.imwrite(str(p), img):
            raise RuntimeError(f"could not write {p}")
        written.append(p)
    return written


def title_for(pair: pf.Pair, reg: pf.Reg, extra: str = "") -> str:
    return (f"{pair.slug} {pair.width_mm:.1f} mm  iou {reg.iou:.2f}  scale {reg.scale:.3f}"
            f"{'  flipY' if reg.flip_y else ''}{('  ' + extra) if extra else ''}")


def crop_set(pair: pf.Pair, reg: pf.Reg, out_dir: Path, crop_mm: tuple, name: str,
             ppm: float = CROP_PPM, **kw) -> list:
    """Render a crop window at CROP_PPM (36.0) and write the same five files
    with suffix `_crop_<name>` (`name` passed through `_safe`, so a name with
    a path separator or other filesystem-illegal character still writes)."""
    r = render_pair(pair, reg, ppm=ppm, crop_mm=crop_mm, **kw)
    x0, y0, x1, y1 = crop_mm
    return write_overlay_set(out_dir, r, title_for(pair, reg, f"crop {x0:g},{y0:g}..{x1:g},{y1:g} mm"),
                             suffix=f"_crop_{_safe(name)}")


def match_blocks(pro_rgb: list, ours_rgb: list, max_de: float = 12.0) -> dict:
    """Pro block index -> our block indices within `max_de` CIEDE2000,
    nearest first. Chart-free: two RGBs straight to CIELAB, the module
    `threads.py` keeps as the one colour space."""
    if not pro_rgb or not ours_rgb:
        return {i: [] for i in range(len(pro_rgb))}
    pl = rgb_to_lab(np.array(pro_rgb, dtype=np.float64))
    ol = rgb_to_lab(np.array(ours_rgb, dtype=np.float64))
    out = {}
    for i in range(len(pro_rgb)):
        de = deltaE_ciede2000(np.repeat(pl[i:i + 1], len(ol), axis=0), ol)
        order = [int(j) for j in np.argsort(de) if de[j] <= max_de]
        out[i] = order
    return out


def by_thread(pair: pf.Pair, reg: pf.Reg, out_dir: Path, ppm: float = DEFAULT_PPM) -> list:
    """Write one overlay sheet per pro block, each named `<block_index>_<rrggbb>.png`,
    rendering pro block k against its matched our blocks. Title names unmatched blocks."""
    out_dir = Path(out_dir) / "by_thread"
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = match_blocks(pair.pro_rgb, pair.ours_rgb)
    written = []
    for k, rgb in enumerate(pair.pro_rgb):
        ours_blocks = set(matches.get(k, []))
        r = render_pair(pair, reg, ppm=ppm, only_pro_block=k,
                        only_ours_blocks=ours_blocks if ours_blocks else set())
        hexname = "%02x%02x%02x" % tuple(int(v) for v in rgb)
        extra = f"pro block {k} #{hexname} vs ours {sorted(ours_blocks) or 'NONE within 12 dE'}"
        p = out_dir / f"{k}_{hexname}.png"
        if not cv2.imwrite(str(p), _titled(r["overlay"], title_for(pair, reg, extra))):
            raise RuntimeError(f"could not write {p}")
        written.append(p)
    return written


# --------------------------------------------------------------------- CLI
def _safe(s) -> str:
    """A filename-safe token: any run of characters outside
    `[A-Za-z0-9._-]` becomes one `-`, leading/trailing `-` trimmed, and an
    all-illegal input falls back to `x` rather than an empty string."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(s)).strip("-") or "x"


def _suffix_for(flags: dict) -> str:
    """The `--flag` filename suffix, e.g. `{"curve_turn_deg": 0}` ->
    `_curve_turn_deg-0`. Empty for no flags. Both the key and the value go
    through `_safe`: `parse_flags` can hand back an arbitrary string for a
    str-typed `PipelineConfig` field (a forced_class, say), and that string
    lands straight in a filename otherwise."""
    if not flags:
        return ""
    return "_" + "_".join(f"{_safe(k)}-{_safe(v)}" for k, v in sorted(flags.items()))


def _resolve_dir(a) -> Path:
    if a.dir:
        return Path(a.dir)
    import os
    out = os.environ.get("PRO_PARITY_OUT")
    if not (a.slug and out):
        raise SystemExit("--dir <out>/real/<slug>, or --slug with PRO_PARITY_OUT set")
    return Path(out) / "real" / a.slug


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir")
    ap.add_argument("--slug")
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--against", default=None,
                    help="overlay two of OUR arms: 'baseline' or a flags hash, against the --flag arm")
    ap.add_argument("--crop", type=float, nargs=4, default=None, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--crop-name", default="crop")
    ap.add_argument("--by-thread", action="store_true")
    ap.add_argument("--ppm", type=float, default=DEFAULT_PPM)
    a = ap.parse_args(argv)

    pair = pf.load_pair(_resolve_dir(a))
    flags = parse_flags(a.flag)
    suffix = _suffix_for(flags)
    if flags:
        arm = pf.redigitize(pair, flags)
        pair = pf.load_pair(arm)
    reg = pf.register_pair(pair.pro_path, pair.ours_path)
    out = pair.dir / "overlay"
    extra = ""
    kw = {}
    if a.against:
        base_dir = pf._lane_root(pair.dir) / pair.slug
        arm_dir = base_dir if a.against == "baseline" else base_dir / "flags" / a.against
        if not (arm_dir / "ours.dst").exists():
            flags_root = base_dir / "flags"
            existing = sorted(p.name for p in flags_root.iterdir() if p.is_dir()) if flags_root.exists() else []
            raise SystemExit(f"--against {a.against!r}: no such arm under {flags_root}. "
                             f"Existing: {', '.join(existing) if existing else 'none'}")
        base = pf.load_pair(arm_dir)
        # the "pro" side becomes the other arm: register against it instead
        reg = pf.register_pair(base.ours_path, pair.ours_path)
        pair = dataclasses.replace(pair, pro_path=base.ours_path, pro_rgb=base.ours_rgb)
        extra = f"OURS {a.against} (magenta) vs OURS {suffix.strip('_') or 'baseline'} (cyan)"
        suffix += "_vs-" + _safe(a.against)
    title = title_for(pair, reg, extra)
    print(title)
    written = []
    if a.crop:
        written += crop_set(pair, reg, out, tuple(a.crop), a.crop_name, ppm=CROP_PPM, **kw)
    else:
        r = render_pair(pair, reg, ppm=a.ppm, **kw)
        written += write_overlay_set(out, r, title, suffix=suffix)
        if a.by_thread:
            written += by_thread(pair, reg, out, ppm=a.ppm)
    (out / f"registration{suffix}.json").write_text(json.dumps(reg.as_dict(), indent=1))
    for p in written:
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
