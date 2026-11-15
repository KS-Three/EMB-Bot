"""apex_pro: how the professional sews the point where two letter strokes meet,
read stitch by stitch, and how far our construction is from it (2026-11-14).

Kent, on `lettering_columns_apex_cut` + its guard: "Off was closer to the pros
here, but still not perfect" and "I want it exactly like the pros." This tool
reads the pro's DST at every acute letter tip (the M's V, an A's apex, an N's
or W's points), registered onto our plan frame, and puts a number on "closer".

FRAMES. The corpus capture (`tools.jag_strips capture`) holds our regions and
runs in plan mm, y down. The pro's DST is mm y down (`letter_pieces.runs_of`).
One global registration (uniform scale + translation, `scorecard.register`)
maps the pro onto the plan, then each LETTER is re-registered by translation
alone on its own thread (the pro's MARINE sits ~2.5 mm higher in his extents
than the art puts it), so a window compares the same stroke.

READING. The pro's crosses come from `letter_pieces` (fuse, chains, split at
35 deg turns): one reader on both files. A piece's sewing order is its index
in the file.

THE INSTRUMENT (`measure`). In a window round the joint (the disk through the
crotch and the tip, `WIN_W` stroke widths beyond), each side's stitches are
painted in sewing order at `RES` px/mm, 0.4 mm thread, the last stitch over
a pixel owning it (what the eye sees; underlay is buried). Then:

  angle_err_deg  mean |our cross angle - his| (mod 180, 0..90) over the
                 pixels both sew, area-weighted: degrees per mm2 of shared
                 thread. 0 = his exact stitch directions.
  seam_mm        the split line: pixels where the visible direction jumps by
                 more than SEAM_DEG to a neighbour within 0.2 mm. Symmetric
                 mean distance, ours to his nearest and his to ours, mm.
                 A side with no seam in the window reads as the window's
                 radius (no split line where he has one is as far as it gets).
  shared_mm2     the area both sew (the denominator), and iou of coverage.

    python -m tools.apex_pro tips DESIGN [--arm off]             # list tips
    python -m tools.apex_pro read DESIGN [--tip N ...] [--out DIR] # pro pieces at each tip
    python -m tools.apex_pro measure DESIGN ARMDIR [ARMDIR ...] [--out JSON]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
for _p in (DIGITIZER, DIGITIZER / "tools" / "pro_parity"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

def _eye_root() -> Path:
    """`EMB_EYE_PAIRS`, else the first `digitizer/eye_pairs_out` above this
    checkout that holds the apex corpus (a lane finds the primary's)."""
    env = os.environ.get("EMB_EYE_PAIRS")
    if env:
        return Path(env)
    for p in (DIGITIZER.parent, *DIGITIZER.parents):
        q = p / "digitizer" / "eye_pairs_out"
        if (q / "jag-source-1113").is_dir():
            return q
    return DIGITIZER / "eye_pairs_out"


EYE = _eye_root()
CORPUS = Path(os.environ.get("EMB_APEX_CORPUS")
              or EYE / "jag-source-1113" / "apex-corpus")

TIP_TURN = 100.0      # a convex corner turning this much: legs under 80 deg apart
CROTCH_TURN = 25.0    # a reflex corner this sharp is a crotch
CROTCH_CONE = 20.0    # ... and it lies within this of the tip's bisector
RES = 20.0            # px per mm, instrument rasters
THREAD = 0.4          # mm
SEAM_DEG = 25.0
WIN_W = 0.9           # window radius beyond the crotch-tip half span, in stroke widths
WIN_MIN = 1.5         # mm

SLUG = {  # corpus capture name -> pro fixture slug (`flip_sheet_renders.fixture_files`)
    "becker_hat_large": "becker_hat_large", "becker_lc_large": "becker_lc_large",
    "becker_hat_small": "becker_hat_small", "becker_chest_small": "becker_chest_small",
    "becker_beanie": "becker_beanie", "proseal_hat": "proseal_hat",
    "proseal_beanie": "proseal_beanie", "mfab_hat": "mfab_hat", "mfab_lc": "mfab_lc",
}


# ------------------------------------------------------------------ loading
def load_cap(path: Path) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def our_runs(cap: dict) -> list[dict]:
    """Needle-down runs in sewing order: [{block, pts, kind, sid}] (plan mm)."""
    out = []
    for bi, blk in enumerate(cap["runs"]):
        for _rgb, runs in blk:
            for pts, kind, jump, _trim, sid in runs:
                if jump or len(pts) < 2:
                    continue
                out.append({"block": bi, "pts": np.asarray(pts, float), "kind": kind, "sid": sid})
    return out


def _segs(runs, only=None):
    segs = []
    for r in runs:
        p = r["pts"]
        for a, b in zip(p[:-1], p[1:]):
            if only is not None and not only(a, b):
                continue
            segs.append((float(a[0]), float(a[1]), float(b[0]), float(b[1]),
                         float(np.hypot(*(b - a))), r["block"], False))
    return segs


def _ext(segs):
    xs = [q[0] for q in segs] + [q[2] for q in segs]
    ys = [q[1] for q in segs] + [q[3] for q in segs]
    return min(xs), min(ys), max(xs), max(ys)


def register_global(pro_runs, ours) -> tuple[float, float, float, float]:
    """(scale, dx, dy, iou): ours * scale + (dx, dy) lies on the pro."""
    import scorecard as sc
    pro, our = _segs(pro_runs), _segs(ours)
    pe, oe = _ext(pro), _ext(our)
    s = (pe[2] - pe[0]) / max(oe[2] - oe[0], 1e-9)
    our_s = [(a * s, b * s, c * s, d * s, e * s, f, g) for a, b, c, d, e, f, g in our]
    se = _ext(our_s)
    dx, dy = (pe[0] + pe[2] - se[0] - se[2]) / 2, (pe[1] + pe[3] - se[1] - se[3]) / 2
    our_c = sc.shifted(our_s, dx, dy)
    rdx, rdy, iou = sc.register(pro, our_c, sc.bounds(pro, our_c))
    return s, dx + rdx, dy + rdy, float(iou)


def register_local(pro_runs, ours, box, pad: float = 3.0) -> tuple[float, float, float]:
    """Translation (dx, dy, iou) moving OUR thread in `box` (plan mm) onto the
    pro's (already in plan mm), searched within the box grown by `pad`."""
    import scorecard as sc
    x0, y0, x1, y1 = box
    inside = lambda q0, q1: (x0 <= q0[0] <= x1 and y0 <= q0[1] <= y1)          # noqa: E731
    near = lambda q0, q1: (x0 - pad <= q0[0] <= x1 + pad and y0 - pad <= q0[1] <= y1 + pad)  # noqa: E731
    our = _segs(ours, inside)
    pro = _segs(pro_runs, near)
    if not our or not pro:
        return 0.0, 0.0, 0.0
    bb = sc.bounds(pro, our)
    dx, dy, iou = sc.register(pro, our, bb)
    if math.hypot(dx, dy) > pad:
        return 0.0, 0.0, float(iou)
    return float(dx), float(dy), float(iou)


class Case:
    """One design: our capture(s) and the pro's runs in plan mm."""

    def __init__(self, design: str, cap_path: Path | None = None):
        from tools.flip_sheet_renders import fixture_files
        from tools.letter_pieces import runs_of
        self.design = design
        self.cap = load_cap(cap_path or CORPUS / "off" / f"{design}.pkl")
        self.ours = our_runs(self.cap)
        self.pro_path = fixture_files(SLUG.get(design, design))["pro_dst"]
        raw = runs_of(self.pro_path)
        self.reg = register_global(raw, self.ours)
        s, dx, dy, _ = self.reg
        self.pro = [{**r, "pts": (r["pts"] - [dx, dy]) / s} for r in raw]
        self.regions = self.cap["regions"]
        self._local: dict = {}

    def pro_at(self, sid: str) -> list[dict]:
        """The pro's runs shifted onto letter `sid` (local registration)."""
        if sid not in self._local:
            poly = next(r[0] for r in self.regions if r[2] == sid)
            dx, dy, iou = register_local(self.pro, [r for r in self.ours if r["sid"] == sid],
                                         poly.bounds)
            self._local[sid] = (dx, dy, iou)
        dx, dy, _ = self._local[sid]
        return [{**r, "pts": r["pts"] - [dx, dy]} for r in self.pro]


# --------------------------------------------------------------------- tips
def is_text(meta: dict) -> bool:
    return bool(meta.get("text_candidate") or meta.get("lettering_group") or meta.get("word_id"))


def tips(regions) -> list[dict]:
    """Acute convex corners of lettering shapes, each with the crotch that
    closes on it (the nearest reflex corner its bisector points at), if any."""
    from shapely.geometry import LineString
    from digitizer_core.outline_cut import corners, stroke_width
    out = []
    for poly, ti, sid, meta in regions:
        if not is_text(meta) or poly.area < 2.0:
            continue
        W = stroke_width(poly)
        reflex, convex = corners(poly, W)
        for c in convex:
            if c["turn"] < TIP_TURN:
                continue
            p = np.array(c["p"])
            bis = np.array(c["bis"])
            best = None
            for r in reflex:
                if r["turn"] < CROTCH_TURN:
                    continue
                q = np.array(r["p"])
                v = q - p
                d = float(np.hypot(*v))
                if d < 0.3 * W or d > 4.0 * W:
                    continue
                if float(v @ bis) / d < math.cos(math.radians(CROTCH_CONE)):
                    continue
                if not poly.buffer(1e-6).contains(LineString([p + 0.02 * v, q - 0.02 * v])):
                    continue
                if best is None or d < best[0]:
                    best = (d, q)
            out.append({"sid": sid, "thread": ti, "W": round(W, 3), "tip": [round(float(v), 3) for v in p],
                        "turn": round(c["turn"], 1), "bis": [round(float(v), 4) for v in bis],
                        "crotch": None if best is None else [round(float(v), 3) for v in best[1]],
                        "reach_W": None if best is None else round(best[0] / W, 2)})
    return out


def window(t: dict) -> tuple[np.ndarray, float]:
    """(centre, radius) of the joint window: through the crotch and the tip."""
    p = np.array(t["tip"])
    if t["crotch"] is not None:
        q = np.array(t["crotch"])
        c = (p + q) / 2
        r = float(np.hypot(*(q - p))) / 2 + WIN_W * t["W"]
    else:
        c = p + np.array(t["bis"]) * t["W"]
        r = 1.6 * t["W"]
    return c, max(r, WIN_MIN)


# ------------------------------------------------------------------ reading
def pieces_near(runs, c, r: float) -> list[dict]:
    """`letter_pieces` pieces with a cross midpoint within r of c, in sewing order."""
    from tools.letter_pieces import chains, fuse, piece_stats, split_turns
    out, order = [], 0
    for ri, run in enumerate(runs):
        fp = fuse(run["pts"])
        for ch in chains(fp):
            for part in split_turns(ch):
                order += 1
                mids = np.array([s[2] for s in part])
                if float(np.min(np.hypot(*(mids - c).T))) > r:
                    continue
                st = piece_stats(part) if len(part) >= 2 else {}
                out.append({"order": order, "run": ri, "crosses": part, "stats": st})
    return out


# --------------------------------------------------------------- instrument
def paint(runs, c, r: float, res: float = RES):
    """Last-sewn-wins direction field in the disk: (angle deg [0,180) or nan,
    owner stitch index or -1)."""
    import cv2
    n = int(math.ceil(2 * r * res)) + 1
    x0, y0 = c[0] - r, c[1] - r
    ang = np.full((n, n), np.nan, np.float32)
    th = max(1, int(round(THREAD * res)))
    k = 0
    for run in runs:
        p = run["pts"]
        if len(p) < 2:
            continue
        near = np.hypot(*(p - c).T) < r + 10.0
        if not near.any():
            continue
        for a, b in zip(p[:-1], p[1:]):
            k += 1
            if min(np.hypot(*(a - c)), np.hypot(*(b - c))) > r + 8.0:
                continue
            d = b - a
            L = float(np.hypot(*d))
            if L < 0.25:      # a lock or a tie: no direction worth a pixel
                continue
            m = np.zeros((n, n), np.uint8)
            cv2.line(m, (int(round((a[0] - x0) * res)), int(round((a[1] - y0) * res))),
                     (int(round((b[0] - x0) * res)), int(round((b[1] - y0) * res))), 1, th)
            ang[m > 0] = math.degrees(math.atan2(d[1], d[0])) % 180.0
    yy, xx = np.mgrid[0:n, 0:n]
    disk = np.hypot((xx + 0.5) / res - r, (yy + 0.5) / res - r) <= r
    ang[~disk] = np.nan
    return ang, disk


def _adiff(a, b):
    d = np.abs(a - b) % 180.0
    return np.minimum(d, 180.0 - d)


def seam_mask(ang, res: float = RES, deg: float = SEAM_DEG):
    reach = max(1, int(round(0.2 * res)))
    seam = np.zeros(ang.shape, bool)
    ok = ~np.isnan(ang)
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            if dx == 0 and dy == 0:
                continue
            sh = np.roll(np.roll(ang, dy, 0), dx, 1)
            okb = ok & ~np.isnan(sh)
            seam |= okb & (_adiff(ang, np.where(okb, sh, ang)) > deg)
    return seam


def measure_window(ours, pro, c, r: float, res: float = RES) -> dict:
    import cv2
    a, disk = paint(ours, c, r, res)
    b, _ = paint(pro, c, r, res)
    oa, ob = ~np.isnan(a), ~np.isnan(b)
    both = oa & ob
    shared = float(both.sum()) / res ** 2
    err = float(_adiff(a[both], b[both]).mean()) if both.any() else float("nan")
    union = float((oa | ob).sum())
    sa, sb = seam_mask(a, res), seam_mask(b, res)

    def mean_to(src, dst):
        if not src.any():
            return None
        if not dst.any():
            return r
        dt = cv2.distanceTransform((~dst).astype(np.uint8), cv2.DIST_L2, 5) / res
        return float(dt[src].mean())
    d_ab, d_ba = mean_to(sa, sb), mean_to(sb, sa)
    if d_ab is None and d_ba is None:
        seam = 0.0
    else:
        seam = float(np.mean([v if v is not None else r for v in (d_ab, d_ba)]))
    return {"angle_err_deg": round(err, 2), "seam_mm": round(seam, 3),
            "shared_mm2": round(shared, 2), "iou": round(float(both.sum()) / max(union, 1), 3)}


# ------------------------------------------------------------------ drawing
PAL = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189),
       (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207)]


def draw_pieces(img, pieces, x0, y0, ppm, label=True):
    import cv2
    P = lambda q: (int(round((q[0] - x0) * ppm)), int(round((q[1] - y0) * ppm)))  # noqa: E731
    for k, pc in enumerate(pieces):
        col = PAL[k % len(PAL)][::-1]
        for s in pc["crosses"]:
            cv2.line(img, P(s[0]), P(s[1]), col, 1, cv2.LINE_AA)
        if label:
            m0 = pc["crosses"][0][2]
            cv2.putText(img, str(k + 1), P(m0), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(img, str(k + 1), P(m0), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
    return img


def draw_runs(img, runs, c, r, x0, y0, ppm, col=None):
    """Every stitch near the window, thin, coloured by sewing order (red ->
    violet) unless `col`."""
    import cv2
    P = lambda q: (int(round((q[0] - x0) * ppm)), int(round((q[1] - y0) * ppm)))  # noqa: E731
    segs = []
    for run in runs:
        p = run["pts"]
        for a, b in zip(p[:-1], p[1:]):
            if min(np.hypot(*(a - c)), np.hypot(*(b - c))) <= r * 1.6:
                segs.append((a, b))
    n = max(1, len(segs))
    for k, (a, b) in enumerate(segs):
        cc = col or cv2.cvtColor(np.uint8([[[int(150 * k / n), 230, 210]]]), cv2.COLOR_HSV2BGR)[0, 0].tolist()
        cv2.line(img, P(a), P(b), cc, 1, cv2.LINE_AA)
        cv2.circle(img, P(b), 2, cc, -1)
    return img


def panel(runs, c, r, poly=None, title="", ppm=None, side=520, mode="order"):
    import cv2
    half = r * 1.35
    ppm = ppm or side / (2 * half)
    img = np.full((side, side, 3), 248, np.uint8)
    x0, y0 = c[0] - half, c[1] - half
    if poly is not None:
        for ring in [poly.exterior, *poly.interiors]:
            pts = np.array([[(q[0] - x0) * ppm, (q[1] - y0) * ppm] for q in ring.coords], np.int32)
            cv2.polylines(img, [pts], True, (170, 170, 170), 1, cv2.LINE_AA)
    cv2.circle(img, (int(round(half * ppm)), int(round(half * ppm))), int(round(r * ppm)), (220, 220, 220), 1)
    if mode == "order":
        draw_runs(img, runs, c, r, x0, y0, ppm)
    else:
        draw_pieces(img, pieces_near(runs, c, r * 1.2), x0, y0, ppm)
    cv2.putText(img, title, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 190), 1, cv2.LINE_AA)
    return img


# ------------------------------------------------------------ the windows
#: The joints read for `docs/apex-pro-construction-2026-11-14.md`: (label,
#: centre x, y, radius) in mm of the reference design's plan, scaled to the
#: others by plan width (one art, so one frame up to scale).
BECKER_REF_W = 101.9
BECKER = [("M_V", -40.0, 22.0, 6.0), ("N_top", 20.5, 19.5, 5.5), ("N_foot", 29.0, 26.5, 5.5),
          ("A_top", -21.5, 17.5, 5.0)]
PROSEAL_REF_W = 85.9
PROSEAL = [("A_top", 24.0, 17.5, 4.0), ("small_M", -2.4, 30.4, 2.4)]
MFAB_REF_W = 104.9
MFAB = [("W_small", -14.3, 8.7, 4.0), ("N_small", 15.8, 9.5, 3.5), ("G_small", 22.7, 10.5, 4.0),
        ("LLC_small", 33.8, 8.7, 4.0)]
REF = {**{d: (BECKER, BECKER_REF_W) for d in SLUG if d.startswith("becker")},
       **{d: (PROSEAL, PROSEAL_REF_W) for d in SLUG if d.startswith("proseal")},
       **{d: (MFAB, MFAB_REF_W) for d in SLUG if d.startswith("mfab")}}


def windows(design: str, width: float) -> list[tuple[str, np.ndarray, float]]:
    rows, ref = REF[design]
    k = width / ref
    return [(lab, np.array([x * k, y * k]), r * k) for lab, x, y, r in rows]


def letter_at(regions, c):
    from shapely.geometry import Point
    regs = [rr for rr in regions if is_text(rr[3]) and rr[0].area > 1.0]
    return min(regs, key=lambda rr: rr[0].distance(Point(*c)))


# --------------------------------------------------------------- the sheet
def thread_panel(runs, c, r, side: int, title: str, rgb=(70, 70, 78)):
    """Every stitch as 0.4 mm of thread, outlined, in sewing order."""
    import cv2
    half = r * 1.15
    ppm = side / (2 * half)
    img = np.full((side, side, 3), (232, 236, 238), np.uint8)
    x0, y0 = c[0] - half, c[1] - half
    th = max(2, int(round(THREAD * ppm)))
    P = lambda q: (int(round((q[0] - x0) * ppm * 4)), int(round((q[1] - y0) * ppm * 4)))  # noqa: E731
    for run in runs:
        p = run["pts"]
        for a, b in zip(p[:-1], p[1:]):
            if min(np.hypot(*(a - c)), np.hypot(*(b - c))) > half * 1.6:
                continue
            cv2.line(img, P(a), P(b), (150, 150, 150), th + 2, cv2.LINE_AA, shift=2)
            cv2.line(img, P(a), P(b), rgb, th, cv2.LINE_AA, shift=2)
    cv2.putText(img, title, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 190), 1, cv2.LINE_AA)
    return img


def art_panel(cap_path: Path, c, r, side: int):
    import cv2
    from tools.jag_strips import _Ctx
    half = r * 1.15
    img = _Ctx(str(cap_path)).source_panel(c[0] - half, c[1] - half, 2 * half, 2 * half)
    img = cv2.resize(img, (side, side), interpolation=cv2.INTER_AREA)
    cv2.putText(img, "art", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 190), 1, cv2.LINE_AA)
    return img


# --------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tips")
    t.add_argument("design")
    ms = sub.add_parser("measure")
    ms.add_argument("design")
    ms.add_argument("arms", nargs="+", help="NAME=CAPTURE.pkl, the first is the frame")
    ms.add_argument("--json")
    ms.add_argument("--sheet", help="sheet folder: art | arms... | pro per window")
    ms.add_argument("--sheet-arms", help="comma list of the arms the sheet shows (default all)")
    rd = sub.add_parser("read")
    rd.add_argument("design")
    rd.add_argument("--tip", type=int, nargs="*")
    rd.add_argument("--out", default=str(EYE / "apex-like-pro-1114" / "read"))
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        import cv2
        arms = [s.split("=", 1) for s in a.arms]
        case = Case(a.design, Path(arms[0][1]))
        caps = {name: (case.cap if i == 0 else load_cap(Path(p))) for i, (name, p) in enumerate(arms)}
        runs = {name: our_runs(cp) for name, cp in caps.items()}
        import hashlib
        out = {"design": a.design, "reg": [round(float(v), 3) for v in case.reg], "windows": [],
               "md5": {n: hashlib.md5(b"".join(np.round(r["pts"], 4).tobytes() for r in rr)).hexdigest()[:10]
                       for n, rr in runs.items()},
               "stitches": {n: int(sum(len(r["pts"]) for r in rr)) for n, rr in runs.items()}}
        print(json.dumps({"md5": out["md5"], "stitches": out["stitches"]}))
        for lab, c, r in windows(a.design, case.cap["width"]):
            poly, _ti, sid, _m = letter_at(case.regions, c)
            pro = case.pro_at(sid)
            row = {"window": lab, "centre": [round(float(v), 2) for v in c], "r": round(r, 2), "sid": sid,
                   "local": [round(v, 3) for v in case._local[sid]]}
            for name in runs:
                row[name] = measure_window(runs[name], pro, c, r)
            out["windows"].append(row)
            print(json.dumps(row))
            if a.sheet:
                side = 420
                panels = [art_panel(Path(arms[0][1]), c, r, side)]
                panels += [thread_panel(runs[n], c, r, side,
                                        f"{n}  err {row[n]['angle_err_deg']} seam {row[n]['seam_mm']}")
                           for n in (a.sheet_arms.split(",") if a.sheet_arms else runs)]
                panels.append(thread_panel(pro, c, r, side, "pro", rgb=(95, 95, 95)))
                Path(a.sheet).mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(Path(a.sheet) / f"{a.design}_{lab}.png"), np.hstack(panels))
        if a.json:
            Path(a.json).write_text(json.dumps(out, indent=1))
        return 0
    if a.cmd == "tips":
        cap = load_cap(CORPUS / "off" / f"{a.design}.pkl")
        for i, tp in enumerate(tips(cap["regions"])):
            print(i, json.dumps(tp))
        return 0
    if a.cmd == "read":
        import cv2
        case = Case(a.design)
        print("global reg", case.reg)
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        tl = tips(case.regions)
        for i, tp in enumerate(tl):
            if a.tip and i not in a.tip:
                continue
            c, r = window(tp)
            pro = case.pro_at(tp["sid"])
            poly = next(rr[0] for rr in case.regions if rr[2] == tp["sid"])
            row = [panel(case.ours, c, r, poly, f"OFF #{i} W{tp['W']:.2f}"),
                   panel(pro, c, r, poly, f"pro order (local {case._local[tp['sid']][2]:.2f})"),
                   panel(pro, c, r, poly, "pro pieces", mode="pieces")]
            cv2.imwrite(str(out / f"{a.design}_tip{i}.png"), np.hstack(row))
            pcs = pieces_near(pro, c, r * 1.2)
            print(i, json.dumps(tp))
            for k, pc in enumerate(pcs):
                st = pc["stats"]
                print(f"   {k + 1}: order {pc['order']} n {st.get('n')} role {st.get('role')} "
                      f"W {st.get('width_mm')} axis {st.get('axis_deg')} cross {st.get('first_dir')}->{st.get('last_dir')} "
                      f"drift {st.get('drift_deg')} start {st.get('start')} end {st.get('end')}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
