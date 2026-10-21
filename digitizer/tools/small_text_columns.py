"""small_text_columns: sewn column width, letter gaps and letter pieces of
small lettering, ours beside the professional's, each read in its own frame.

WHAT IT IS FOR. The pro's rule for raised small text (R4 and R6 of
`docs/pro-digitizer-rules-2026-10-21.md`): thin strokes sewn at a floor
(0.9 mm on Fremont, 1.26 on Drone and Proseal), wide strokes at the art's
width, letter gaps closed to 0.15-0.35 mm. This reads those three numbers
off a machine file the same way for both sides, so an arm of ours can be
held against the pro's file line by line.

HOW (the pro-rules doc's method, applied to BOTH files as DST):
- letters: per colour block, needle-down stitches of 6 mm or less drawn
  0.4 mm wide at 20 px/mm, opened by 0.55 mm so the runs travelling between
  letters fall away; each remaining connected piece is a letter or a joined
  pair. Pieces are read in the file's OWN frame (mm from its stitch extents'
  top-left), never inside a box mapped from the art or from the other file.
- a line: the pieces whose vertical centre lies in a band (mm, own frame),
  picked per side from `--pieces` output. Bars wider than 3x their height
  are dropped.
- cap: median height of pieces at least 0.7 of the line's tallest, less the
  0.4 mm thread.
- column: the satin crosses whose midpoint lies on one of the line's pieces;
  a cross is a needle-to-needle segment flanked by reversals, the crosses two
  back and two ahead parallel (|cos| >= 0.9) and of similar length (0.7-1.4x).
- gap: between x-adjacent pieces of a line, the nearest distance between
  their drawn masks (the 0.4 mm thread already in them): the VISIBLE gap.
  `gap_med` leaves out word spaces (wider than max(0.6, 0.35 cap)).
- band_<line>_<side>.png in --out: the band's stitches, the line's own
  colour blocks dark, the rest pale -- look before quoting a number.

Ours is digitized exactly as `tools.pro_pair.digitize` does (the Studio's
request through the service's parser), with `--set key=value` overrides
added to that request, written through `digitizer_service.formats.write`
as DST and read back with pystitch -- the file the customer gets.

  python -m tools.small_text_columns --job fremont --pieces --out DIR    # both piece lists; DIR/ours.dst
  python -m tools.small_text_columns --job fremont --ours DIR/ours.dst \
      --band pro:TAG:34:39.5:28:67 --band ours:TAG:33.3:39.3:28:66 --out DIR2
  python -m tools.small_text_columns --job fremont --set small_text_cap_mm=4.0 ... --out DIR
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

REPO = DIGITIZER.parent
# gitignored (third-party files): a lane under .claude/worktrees/ reads the
# primary checkout's copy
PRO_DIR = next((p / "scratch_kent" / "Embroidery Files" for p in (REPO, *REPO.parents)
                if (p / "scratch_kent" / "Embroidery Files").is_dir()),
               REPO / "scratch_kent" / "Embroidery Files")
PPM = 20.0
THREAD_MM = 0.4
OPEN_MM = 0.55
MAX_STITCH_MM = 6.0

#: job -> art, pro file, width, garment, and the letters of its small lines.
#: A line's band is given per side with --band, picked from `--pieces`: the
#: lines move when ours is grown, so no band is fixed here.
JOBS = {
    "fremont": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_hotel_fremont.webp",
        "pro": PRO_DIR / "Hotel Fremont" / "Hotel Hat" / "HOTEL FREMONT HAT.DST",
        "width_mm": 92.5, "garment": "hat_front",
        "letters": {"EST": 3, "1895": 4, "THE": 3, "TAG": 11},
    },
    "fremont_patch": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_hotel_fremont.webp",
        "pro": PRO_DIR / "Hotel Fremont" / "Hotel Patch" / "HOTEL FREMONT .DST",
        "width_mm": 92.5, "garment": "hat_front",
        "letters": {"EST": 3, "1895": 4, "THE": 3, "TAG": 11},
    },
    "drone": {
        "art": DIGITIZER / "testdata" / "photo" / "logo_drone_thermal_badge.png",
        "pro": PRO_DIR / "Precision Drone" / "PRECISION DRON HAT 2.DST",
        "width_mm": 62.6, "garment": "hat_front",
        "letters": {"AND DRONE": 8},
    },
    # the art is Kent's and lives ONLY in the gitignored scratch_kent/; never commit it
    "proseal": {
        "art": PRO_DIR.parent / "proseal.jpg",
        "pro": PRO_DIR / "Proseal" / "PROSEALHAT.DST",
        "width_mm": 85.9, "garment": "hat_front",
        "letters": {"SPRAY FOAM + COATINGS": 18},
    },
}


# ------------------------------------------------------------------ reading
def read_blocks(path) -> list[list]:
    """A machine file -> colour blocks of (x, y) mm points, y down, in the
    file's own frame (origin at its stitch extents' top-left); None marks a
    jump or trim."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    blocks, cur = [], []
    for x, y, c in pat.stitches:
        cmd = c & m
        if cmd == pystitch.COLOR_CHANGE:
            blocks.append(cur)
            cur = []
        elif cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
        elif cmd in (pystitch.JUMP, pystitch.TRIM):
            cur.append(None)
    blocks.append(cur)
    pts = np.array([q for b in blocks for q in b if q is not None])
    x0, y0 = pts.min(0)
    return [[None if q is None else (q[0] - x0, q[1] - y0) for q in b] for b in blocks]


def _runs(block):
    """Needle-down runs of a block: consecutive stitches no longer than
    `MAX_STITCH_MM`, split at every jump or trim."""
    runs, cur = [], []
    for q in block:
        if q is None or (cur and math.dist(q, cur[-1]) > MAX_STITCH_MM):
            if len(cur) > 1:
                runs.append(cur)
            cur = [] if q is None else [q]
        else:
            cur.append(q)
    if len(cur) > 1:
        runs.append(cur)
    return runs


def pieces(blocks) -> list[dict]:
    """Letter pieces of every colour block (module docstring)."""
    import cv2
    allp = np.array([q for b in blocks for q in b if q is not None])
    W, H = allp.max(0) + 2.0
    w, h = int(W * PPM) + 1, int(H * PPM) + 1
    tw = max(1, int(round(THREAD_MM * PPM)))
    k = int(round(OPEN_MM * PPM)) | 1
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    out = []
    for bi, b in enumerate(blocks):
        runs = _runs(b)
        if not runs:
            continue
        mask = np.zeros((h, w), np.uint8)
        for r in runs:
            p = np.round(np.array(r) * PPM).astype(np.int32)
            cv2.polylines(mask, [p], False, 255, tw)
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kern)
        n, lab, st, _c = cv2.connectedComponentsWithStats(opened, 8)
        for i in range(1, n):
            x, y, ww, hh, area = st[i]
            if area < (0.5 * PPM) ** 2:
                continue
            out.append({"block": bi, "x0": x / PPM, "y0": y / PPM, "x1": (x + ww) / PPM,
                        "y1": (y + hh) / PPM, "mask": lab[y:y + hh, x:x + ww] == i,
                        "ox": x, "oy": y})
    return out


def crosses(blocks) -> list[tuple[tuple, tuple]]:
    """Satin crosses of every block (module docstring)."""
    found = []
    for b in blocks:
        for r in _runs(b):
            p = np.array(r)
            if len(p) < 6:
                continue
            seg = np.diff(p, axis=0)
            ln = np.hypot(seg[:, 0], seg[:, 1])
            for i in range(2, len(seg) - 2):
                if ln[i] < 1e-6 or ln[i] > 4.0:
                    continue
                if np.dot(seg[i - 1], seg[i]) >= 0 or np.dot(seg[i], seg[i + 1]) >= 0:
                    continue
                ok = True
                for j in (i - 2, i + 2):
                    if ln[j] < 1e-6:
                        ok = False
                        break
                    cos = abs(np.dot(seg[i], seg[j])) / (ln[i] * ln[j])
                    if cos < 0.9 or not 0.7 <= ln[j] / ln[i] <= 1.4:
                        ok = False
                        break
                if ok:
                    found.append((tuple(p[i]), tuple(p[i + 1])))
    return found


def _on_piece(pt, pc) -> bool:
    x, y = int(round(pt[0] * PPM)) - pc["ox"], int(round(pt[1] * PPM)) - pc["oy"]
    m = pc["mask"]
    return 0 <= y < m.shape[0] and 0 <= x < m.shape[1] and bool(m[y, x])


def _gap(a, b) -> float:
    """Nearest distance (mm) between two pieces' drawn masks."""
    import cv2
    x0, y0 = min(a["ox"], b["ox"]), min(a["oy"], b["oy"])
    x1 = max(a["ox"] + a["mask"].shape[1], b["ox"] + b["mask"].shape[1])
    y1 = max(a["oy"] + a["mask"].shape[0], b["oy"] + b["mask"].shape[0])
    ma = np.zeros((y1 - y0, x1 - x0), np.uint8)
    ma[a["oy"] - y0:a["oy"] - y0 + a["mask"].shape[0], a["ox"] - x0:a["ox"] - x0 + a["mask"].shape[1]] = a["mask"]
    mb = np.zeros_like(ma, dtype=bool)
    mb[b["oy"] - y0:b["oy"] - y0 + b["mask"].shape[0], b["ox"] - x0:b["ox"] - x0 + b["mask"].shape[1]] = b["mask"]
    if (ma.astype(bool) & mb).any():
        return 0.0
    dist = cv2.distanceTransform((ma == 0).astype(np.uint8), cv2.DIST_L2, 5)
    return float(dist[mb].min()) / PPM


def line(pcs, xs, band) -> dict:
    """One line's numbers: pieces with vertical centre in `band`."""
    y0, y1 = band[:2]
    xlo, xhi = (band[2], band[3]) if len(band) == 4 else (-1e9, 1e9)
    sel = [p for p in pcs
           if y0 <= (p["y0"] + p["y1"]) / 2 <= y1 and xlo <= (p["x0"] + p["x1"]) / 2 <= xhi
           and (p["x1"] - p["x0"]) <= 3 * (p["y1"] - p["y0"])]
    if not sel:
        return {"pieces": 0}
    sel.sort(key=lambda p: p["x0"])
    hs = [p["y1"] - p["y0"] for p in sel]
    cap = float(np.median([hh for hh in hs if hh >= 0.7 * max(hs)])) - THREAD_MM
    widths = sorted(math.dist(a, b) for a, b in xs
                    if any(_on_piece(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), p) for p in sel))
    gaps = [_gap(a, b) for a, b in zip(sel, sel[1:])]
    vis = [g for g in gaps if g > 0]
    word_gap = max(0.6, 0.35 * cap)         # a space between words, not a letter gap
    letter_gaps = [g for g in gaps if g < word_gap]
    return {"pieces": len(sel), "blocks": sorted({p["block"] for p in sel}), "cap_mm": round(cap, 2),
            "column_med": round(float(np.median(widths)), 2) if widths else None,
            "column_p10": round(float(np.percentile(widths, 10)), 2) if widths else None,
            "column_p90": round(float(np.percentile(widths, 90)), 2) if widths else None,
            "crosses": len(widths),
            "gap_med": round(float(np.median(letter_gaps)), 2) if letter_gaps else None,
            "gaps": [round(g, 2) for g in gaps], "touching": len(gaps) - len(vis),
            "x": [round(sel[0]["x0"], 1), round(sel[-1]["x1"], 1)]}


def render_band(blocks, band, keep=None, ppm: float = 40.0, pad_mm: float = 1.0):
    """The band's needle-down stitches drawn 0.4 mm wide on white (BGR
    uint8): the blocks in `keep` (the line's own) dark, every other block
    pale. Jumps and trims left out."""
    import cv2
    y0, y1 = band[0] - pad_mm, band[1] + pad_mm
    x0, x1 = (band[2] - pad_mm, band[3] + pad_mm) if len(band) == 4 else (0.0, max(
        q[0] for b in blocks for q in b if q is not None) + pad_mm)
    w, h = int((x1 - x0) * ppm) + 1, int((y1 - y0) * ppm) + 1
    img = np.full((h, w, 3), 255, np.uint8)
    tw = max(1, int(round(THREAD_MM * ppm)))
    order = [bi for bi in range(len(blocks)) if keep is None or bi not in keep] + sorted(keep or [])
    for bi in order:
        shade = (30, 30, 30) if keep is None or bi in keep else (215, 215, 215)
        for r in _runs(blocks[bi]):
            p = np.round((np.array(r) - (x0, y0)) * ppm).astype(np.int32)
            cv2.polylines(img, [p], False, shade, tw, cv2.LINE_AA)
    return img


# ------------------------------------------------------------------ ours
def digitize_dst(job: dict, overrides: dict, out: Path):
    """Ours through `tools.pro_pair.digitize` with `overrides` on the
    Studio's request -> (path of ours.dst, Digitized)."""
    from digitizer_core.export import plan_to_pattern
    from digitizer_service import formats
    from tools import pro_pair

    from digitizer_core import small_text

    base = pro_pair.request
    grow = small_text.enlarge_small_text
    rows: list = []

    def request(width_mm, garment_id="hat_front"):
        return {**base(width_mm, garment_id), **overrides}

    def enlarge(*a, **k):           # the growth's own report, kept
        out = grow(*a, **k)
        rows.extend(out)
        return out
    pro_pair.request = request
    small_text.enlarge_small_text = enlarge
    try:
        d = pro_pair.digitize(job["art"], job["width_mm"], job["garment"])
    finally:
        pro_pair.request = base
        small_text.enlarge_small_text = grow
    d.growth = rows
    out.mkdir(parents=True, exist_ok=True)
    path = out / "ours.dst"
    path.write_bytes(formats.write(plan_to_pattern(d.plan), "dst"))
    return path, d


def _value(s: str):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return s


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--job", choices=sorted(JOBS), required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override on the Studio request (JSON value)")
    ap.add_argument("--band", action="append", default=[], metavar="SIDE:NAME:Y0:Y1[:X0:X1]",
                    help="a line's band on one side (pro|ours), mm in that file's own frame")
    ap.add_argument("--pieces", action="store_true", help="print every piece of both files")
    ap.add_argument("--ours", type=Path, help="read this DST as ours instead of digitizing")
    ap.add_argument("--out", type=Path, default=Path("small_text_columns_out"))
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    job = JOBS[args.job]
    overrides = dict((k, _value(v)) for k, v in (s.split("=", 1) for s in args.set))
    meta = {}
    if args.ours:
        ours_path = args.ours
    else:
        ours_path, d = digitize_dst(job, overrides, args.out)
        c = d.plan.counters if hasattr(d.plan, "counters") else {}
        meta = {k: v for k, v in (c or {}).items() if "column" in k or "floor" in k or "small" in k}
        meta["growth"] = d.growth
    sides = {"pro": read_blocks(job["pro"]), "ours": read_blocks(ours_path)}
    report = {"job": args.job, "overrides": overrides, "ours": str(ours_path), "counters": meta, "lines": {}}
    bands = {}
    for b in args.band:
        side, name, *nums = b.split(":")
        bands.setdefault(name, {})[side] = [float(v) for v in nums]
    for side, blocks in sides.items():
        pcs = pieces(blocks)
        if args.pieces:
            print(f"--- {side}")
            for p in sorted(pcs, key=lambda p: (round(p["y0"]), p["x0"])):
                print(f"  block {p['block']:2d}  x {p['x0']:5.1f}-{p['x1']:5.1f}  y {p['y0']:5.1f}-{p['y1']:5.1f}"
                      f"  ({p['x1'] - p['x0']:4.1f} x {p['y1'] - p['y0']:4.1f})")
        xs = crosses(blocks)
        for name, per in bands.items():
            if side in per:
                got = report["lines"].setdefault(name, {})[side] = line(pcs, xs, per[side])
                import cv2
                args.out.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(args.out / f"band_{name}_{side}.png"),
                            render_band(blocks, per[side], set(got.get("blocks", []))))
    print(json.dumps(report, indent=1))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
