"""Width ledger: where a design's ink gets wider than its art, stage by stage.

The Director's fat-ink brief, 2026-11-13. Kent's biggest stitch-side pin
cluster is merged letters, closed counters, lost spacing and lost detail; one
renderer read our dark-ink area 18-30% over the art where the pro's file is
within 1% (`eye_pairs_out/agent-eye-1113/width_check*.json`). This names the
stage the width enters at, on ONE frame (plan mm, y down) for every footprint,
each a map of the VISIBLE colour (painted in sew order; a thread the
garment's colour paints page, so a white keyline sewn over a black band reads
as the gap it is):

  art     the source raster, each pixel snapped to the nearest of the page
          colours and the design's thread colours (a 50% edge between any two);
          an enclosed background region (a counter) is page whatever colour
          the raster gives it (a PNG's transparent counter decodes black)
  stage4  the traced regions, before the small-text re-set
  reset   the regions after the re-set
  stage5  stage 5's planned sewing shapes (pull, underlap, holds)
  needle  the area each run's needle points enclose (the run's stitches 1 px
          wide, closed by `NEEDLE_CLOSE_MM` on their own)
  thread  every stitch drawn `THREAD_MM` wide (40 wt laid thread)
  pro     the professional's file registered onto ours
          (`pro_parity.pairframe.register_pair`), drawn like `thread`, each
          colour block given the colour our stage-5 shapes have under it

Per footprint: ink area (all non-page), enclosed page holes, six named stroke
widths (one colour each) and four named gaps / counters (narrow PAGE the art
keeps open), each read at the ART's own medial points: 2 x the largest
distance to an edge within `PROBE_REACH` of the art width of the point, so a
fatter or slightly moved stroke is found and a closed gap reads 0.

  python -m tools.width_ledger <run dir> [...]
  (a run dir holds capture.pkl, design.json and ours.dst from one digitize
  that kept every stage: `eye_pairs_out/fat-ink-1113/scripts/ledger_run.py`)
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi
from shapely import wkb

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

#: raster resolution of every footprint (px per mm)
R = 20.0
#: laid width of one 40 wt thread on the cloth (mm)
THREAD_MM = 0.4
#: closing radius that fills between a shape's own rows / zigzags (mm): a
#: fill's 0.4 mm rows and a satin's penetrations, which open past 0.4 mm on a
#: curve's outer rail (0.2 left specks inside Jakarta's bowls). Per SHAPE
#: (`_paint_shapes`): two shapes are never welded by it, and a fill sewn row
#: by row as separate runs still closes between its rows
NEEDLE_CLOSE_MM = 0.3
#: a thread colour this close to the garment (RGB distance) reads as the page
PAGE_RGB = 45.0
#: a page feature is a gap / counter at risk when the art leaves it this
#: narrow (mm, 2 x its medial distance)
GAP_MAX_MM = 2.0
GAP_MIN_MM = 0.3
#: a stroke is probed when the art draws it at least this wide (mm): a
#: hairline under it is not sewn as drawn by anyone (Bridge's 0.2-0.4 mm
#: lines read 0 in ours and the pro's alike), so it says nothing of width
STROKE_MIN_MM = 0.6
#: a probe reads a footprint's widest point within this share of the art
#: width at its own medial point
PROBE_REACH = 0.35
#: probes stay this far from anything the small-text re-set moved (mm)
AVOID_MM = 1.0
#: a pro segment longer than this is a jump, not a stitch (mm)
PRO_JUMP_MM = 12.0
FOOTPRINTS = ("art", "stage4", "reset", "stage5", "needle", "thread", "pro")


# ---------------------------------------------------------------- frame ----
class Frame:
    """mm (plan frame, y down) <-> ledger raster px."""

    def __init__(self, x0, y0, x1, y1, pad=2.0):
        self.x0, self.y0 = x0 - pad, y0 - pad
        self.w = int(np.ceil((x1 - x0 + 2 * pad) * R))
        self.h = int(np.ceil((y1 - y0 + 2 * pad) * R))

    def px(self, pts):
        a = np.asarray(pts, np.float64)
        return np.stack([(a[:, 0] - self.x0) * R, (a[:, 1] - self.y0) * R], 1)

    def mm(self, col, row):
        return col / R + self.x0, row / R + self.y0

    def blank(self):
        return np.zeros((self.h, self.w), np.uint8)


def _fill_polys(frame: Frame, geoms) -> np.ndarray:
    m = frame.blank()
    for g in geoms:
        for poly in getattr(g, "geoms", [g]):
            if poly.geom_type != "Polygon" or poly.is_empty:
                continue
            cv2.fillPoly(m, [np.round(frame.px(poly.exterior.coords)).astype(np.int32)], 1)
            for hole in poly.interiors:
                cv2.fillPoly(m, [np.round(frame.px(hole.coords)).astype(np.int32)], 0)
    return m.astype(bool)


def _paint_polys(frame: Frame, items) -> np.ndarray:
    """`items`: (class, geometry) in paint order, a later one covering an
    earlier one; class 0 is the page. -> label map."""
    lab = frame.blank()
    for cls, g in items:
        lab[_fill_polys(frame, [g])] = cls
    return lab


def _paint_runs(frame: Frame, items, width_mm: float, close_mm: float = 0.0) -> np.ndarray:
    """`items`: (class, [(x, y) mm ...]) stitch runs in sew order, each drawn
    `width_mm` wide (>= 1 px); `close_mm` closes each run on its own, so two
    runs are never welded by the closing. -> label map."""
    lab = frame.blank()
    t = max(1, int(round(width_mm * R)))
    k = int(round(close_mm * R))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)) if k > 0 else None
    for cls, pts in items:
        if len(pts) < 2:
            continue
        p = np.round(frame.px(pts)).astype(np.int32)
        m = 3 * k + t + 1
        x0, y0 = max(0, p[:, 0].min() - m), max(0, p[:, 1].min() - m)
        x1, y1 = min(frame.w, p[:, 0].max() + m), min(frame.h, p[:, 1].max() + m)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.polylines(sub, [p - [x0, y0]], False, 1, t, lineType=cv2.LINE_8)
        if ker is not None:
            sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, ker)
        lab[y0:y1, x0:x1][sub > 0] = cls
    return lab


# ------------------------------------------------------------ footprints ---
def classes(cap) -> dict[int, int]:
    """thread index -> colour class: 0 for a thread the garment's colour
    (sewn, it reads as the page), else its own class 1..n."""
    g = np.array(cap["garment_rgb"], float)
    inks = sorted(ti for ti, rgb in cap["chart"].items() if np.linalg.norm(np.array(rgb, float) - g) >= PAGE_RGB)
    out = {ti: 0 for ti in cap["chart"]}
    out.update({ti: i + 1 for i, ti in enumerate(inks)})
    return out


def pages(cap) -> list[tuple]:
    """The art's page colours: the garment's, and the art's own background
    when that is no thread's colour (a PNG's transparent page decodes black)."""
    pr = cap["prep"]
    out = [tuple(int(v) for v in cap["garment_rgb"])]
    bgp = pr["rgb"][pr["bg_mask"]]
    if len(bgp):
        med = np.median(bgp, 0)
        if all(np.linalg.norm(med - np.array(c, float)) >= PAGE_RGB for c in cap["chart"].values()):
            out.append(tuple(int(v) for v in med))
    return out


def art_labels(cap, frame: Frame, cls: dict[int, int]) -> np.ndarray:
    pr = cap["prep"]
    rgb = pr["rgb"].astype(np.float32)
    pg = pages(cap)
    pal = [np.array(c, np.float32) for c in pg] + [np.array(c, np.float32) for c in cap["chart"].values()]
    ids = [0] * len(pg) + [cls[ti] for ti in cap["chart"]]
    d = ((rgb[:, :, None, :] - np.stack(pal)[None, None]) ** 2).sum(-1)
    lab = np.asarray(ids, np.uint8)[d.argmin(-1)]
    lab[pr["bg_mask"]] = 0
    x0, y0, x1, y1 = pr["art_bbox"]
    cx, cy, ppm = (x0 + x1) / 2.0, (y0 + y1) / 2.0, pr["ppm"]
    xm, ym = frame.mm(np.arange(frame.w), np.arange(frame.h))
    mx, my = np.meshgrid((xm * ppm + cx).astype(np.float32), (ym * ppm + cy).astype(np.float32))
    return cv2.remap(lab, mx, my, cv2.INTER_NEAREST, borderValue=0)


def pro_runs(cap, our_dst: Path, frame: Frame, ours_s5: np.ndarray):
    """The pro's stitch runs in OUR plan frame, each colour block given the
    class our stage-5 shapes most often have under its stitches. ->
    (items, Reg) or (None, None)."""
    path = cap.get("pro_pes") or cap.get("pro_dst")
    if not path:
        return {}, None
    import pystitch
    from tools.pro_parity.pairframe import register_pair
    reg = register_pair(Path(path), our_dst)
    pat = pystitch.read(str(path))
    runs, cur, block = [], [], 0
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            px, py = x / 10.0, y / 10.0
            # pro frame -> ours: invert p = s * o' + d, o' = ours, y flipped when flip_y
            ox, oy = (px - reg.dx) / reg.scale, (py - reg.dy) / reg.scale
            if reg.flip_y:
                oy = -oy
            if cur and np.hypot(ox - cur[-1][0], oy - cur[-1][1]) > PRO_JUMP_MM:
                runs.append((block, cur))
                cur = []
            cur.append((ox, oy))
        else:
            if cur:
                runs.append((block, cur))
            cur = []
            if c == pystitch.COLOR_CHANGE:
                block += 1
            if c == pystitch.END:
                break
    if cur:
        runs.append((block, cur))
    # Two ways to give a block its colour, and the one that agrees better
    # with OUR thread map is kept (`footprints`): a PES's own thread colour,
    # nearest of the garment and our threads (Becker's PES lists colours that
    # are not the ones it sews), or the class our stage-5 shapes most often
    # have under the block's stitches (MFab's white keyline block lands on our
    # black band). A DST names no colours and may be one block (Gaulke's): one
    # vote per run between jumps and trims.
    cands = {}
    if cap.get("pro_pes") and len(pat.threadlist) > block:
        g = np.array(cap["garment_rgb"], float)
        ours = [(0, g)] + [(cls_, np.array(cap["chart"][ti], float)) for ti, cls_ in cap["classes"].items()]
        by_colour = {}
        for i, th in enumerate(pat.threadlist[:block + 1]):
            rgb = np.array([(th.color >> 16) & 255, (th.color >> 8) & 255, th.color & 255], float)
            by_colour[i] = min(ours, key=lambda t: np.linalg.norm(t[1] - rgb))[0]
        cands["pes colour"] = [(by_colour.get(b, 0), pts) for b, pts in runs]
    per_block = block > 0
    votes: dict[int, list] = {}
    for i, (b, pts) in enumerate(runs):
        p = np.round(frame.px(pts)).astype(int)
        ok = (p[:, 0] >= 0) & (p[:, 0] < frame.w) & (p[:, 1] >= 0) & (p[:, 1] < frame.h)
        votes.setdefault(b if per_block else i, []).extend(ours_s5[p[ok, 1], p[ok, 0]].tolist())
    vote = {k: int(np.bincount(v).argmax()) if v else 0 for k, v in votes.items()}
    cands["vote per block" if per_block else "vote per run"] = [
        (vote[b if per_block else i], pts) for i, (b, pts) in enumerate(runs)]
    return cands, reg


def our_runs(cap, design: dict, cls: dict[int, int]) -> list[tuple]:
    """Our stitches as (kind, class, run, shape) in sew order (plan mm, y
    down: the design dict is 0.1 mm y-up)."""
    thread_of = {sid: ti for sid, ti, _b, _m in cap["final"]}
    st = design["stitches"]
    seq = []
    for run in design["runs"]:
        c = cls.get(thread_of.get(run.get("shape")), 0)
        cur = []
        for i in range(run["i0"], run["i1"] + 1):
            s = st[i]
            if s.get("type", "stitch") in ("jump", "trim", "color", "stop", "end"):
                if len(cur) > 1:
                    seq.append((run["kind"], c, cur, run.get("shape")))
                cur = []
                continue
            cur.append((s["x"] / 10.0, -s["y"] / 10.0))
        if len(cur) > 1:
            seq.append((run["kind"], c, cur, run.get("shape")))
    return seq


def _paint_shapes(frame: Frame, items, close_mm: float) -> np.ndarray:
    """The needle footprint: `items` (class, shape, run) in sew order, each
    SHAPE's runs drawn 1 px and closed together by `close_mm` (a fill sewn
    row by row as separate runs still closes between its rows), painted in
    the order each shape first sews."""
    order, by = [], {}
    for cls, shape, pts in items:
        if shape not in by:
            order.append(shape)
            by[shape] = (cls, [])
        by[shape][1].append(pts)
    lab = frame.blank()
    k = int(round(close_mm * R))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    for shape in order:
        cls, runs = by[shape]
        ps = [np.round(frame.px(p)).astype(np.int32) for p in runs if len(p) > 1]
        if not ps:
            continue
        allp = np.vstack(ps)
        m = 3 * k + 2
        x0, y0 = max(0, allp[:, 0].min() - m), max(0, allp[:, 1].min() - m)
        x1, y1 = min(frame.w, allp[:, 0].max() + m), min(frame.h, allp[:, 1].max() + m)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.polylines(sub, [p - [x0, y0] for p in ps], False, 1, 1, lineType=cv2.LINE_8)
        sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, ker)
        lab[y0:y1, x0:x1][sub > 0] = cls
    return lab


def footprints(cap, design: dict, run_dir: Path) -> tuple[Frame, dict]:
    """-> (frame, {footprint: label map})."""
    cls = classes(cap)
    cap["classes"] = cls
    # whether a shape sews is decided after stage 4: read it off the end
    sews = {sid: m.get("stitched", True) is not False for sid, _ti, _b, m in cap["final"]}

    # A traced region is drawn whole: a later colour's region still covers
    # the earlier colours it will be clipped to (Becker's blue band holds its
    # white letters until stage 5 cuts them out). Stage 5 clips every later
    # colour by what is already down, so the visible map of the traced shapes
    # is painted EARLIER on top (the final layers: stage 4's are not set yet).
    layer = {sid: m.get("layer", 0) for sid, _ti, _b, m in cap["final"]}
    thread = {sid: ti for sid, ti, _b, _m in cap["final"]}

    def painted(rows):
        rows = sorted((r for r in rows if sews.get(r[0], True)),
                      key=lambda r: -layer.get(r[0], r[3].get("layer", 0)))
        # the colour each shape SEWS in: a recolour after stage 4 (Becker's
        # letters are traced dark and sewn white) is the shape's colour
        return [(cls.get(thread.get(r[0], r[1]), 0), wkb.loads(r[2])) for r in rows]

    s4, rs = painted(cap["stage4"]), painted(cap["reset"])
    s5 = [(cls.get(ti, 0), wkb.loads(b)) for _sid, ti, b in cap["stage5"]]
    xs = [g.bounds for _c, g in s4 + rs + s5]
    frame = Frame(min(b[0] for b in xs), min(b[1] for b in xs), max(b[2] for b in xs), max(b[3] for b in xs))
    seq = our_runs(cap, design, cls)
    art = art_labels(cap, frame, cls)
    art[_fill_polys(frame, [wkb.loads(b) for _s, _t, b, m in cap["stage4"] if m.get("enclosed_background")])] = 0
    s5map = _paint_polys(frame, s5)
    fp = {
        "art": art,
        "stage4": _paint_polys(frame, s4),
        "reset": _paint_polys(frame, rs),
        "stage5": s5map,
        "needle": _paint_shapes(frame, [(c, sh, p) for k, c, p, sh in seq if k not in ("underlay", "travel")],
                                NEEDLE_CLOSE_MM),
        "thread": _paint_runs(frame, [(c, p) for _k, c, p, _sh in seq], THREAD_MM),
    }
    cands, reg = pro_runs(cap, run_dir / "ours.dst", frame, s5map)
    if cands:
        ours = fp["thread"]
        best = None
        for how, items in cands.items():
            m = _paint_runs(frame, items, THREAD_MM)
            either = (m > 0) | (ours > 0)
            agree = float(((m == ours) & either).sum()) / max(1, int(either.sum()))
            if best is None or agree > best[0]:
                best = (agree, how, m)
        fp["pro"] = best[2]
        cap["pro_reg"] = {"scale": round(reg.scale, 4), "flip_y": reg.flip_y, "dx": round(reg.dx, 3),
                          "dy": round(reg.dy, 3), "iou": round(reg.iou, 3), "colours": best[1],
                          "agree": round(best[0], 3)}
    return frame, fp


# ---------------------------------------------------------------- probes ---
def _skeleton(m: np.ndarray) -> np.ndarray:
    from skimage.morphology import skeletonize
    return skeletonize(m)


def _holes(ink: np.ndarray, min_mm2: float = 0.2) -> int:
    bg, n = ndi.label(~ink)
    if n == 0:
        return 0
    border = set(np.unique(np.concatenate([bg[0], bg[-1], bg[:, 0], bg[:, -1]])))
    areas = ndi.sum(np.ones_like(bg), bg, index=np.arange(1, n + 1))
    return int(sum(1 for i, a in enumerate(areas, 1) if i not in border and a / R ** 2 >= min_mm2))


def _grouped(mask_pts_label, k):
    pts, labs = mask_pts_label
    order = np.argsort(labs, kind="stable")
    pts, labs = pts[order], labs[order]
    cuts = np.searchsorted(labs, np.arange(1, k + 2))
    return [pts[cuts[i - 1]:cuts[i]] for i in range(1, k + 1)]


def pick_strokes(art: np.ndarray, frame: Frame, owner, n: int = 6, avoid=None):
    """Six art strokes spread over the design's stroke widths, any colour:
    per component of one colour, its medial points away from ends and joins
    (art half-width at least 0.7 of the component's median)."""
    comps = []
    for c in sorted(set(np.unique(art)) - {0}):
        m = art == c
        lab, k = ndi.label(m)
        dt = ndi.distance_transform_edt(m) / R
        sk = _skeleton(m)
        allp = np.argwhere(sk)
        for pts in _grouped((allp, lab[allp[:, 0], allp[:, 1]]), k):
            if len(pts) < 0.8 * R:              # under 0.8 mm of centreline
                continue
            if avoid is not None and avoid[tuple(pts[len(pts) // 2])]:
                continue
            w = dt[pts[:, 0], pts[:, 1]]
            keep = pts[w >= 0.7 * np.median(w)]
            if len(keep) < 5:
                continue
            w = float(2 * np.median(dt[keep[:, 0], keep[:, 1]]))
            if w >= STROKE_MIN_MM:
                comps.append((w, int(c), keep))
    if not comps:
        return []
    comps.sort(key=lambda t: t[0])
    idx = sorted({int(round(q * (len(comps) - 1))) for q in np.linspace(0, 1, n)})
    out = []
    for j, i in enumerate(idx):
        w, c, keep = comps[i]
        r, col = keep[len(keep) // 2]
        x, y = frame.mm(col, r)
        out.append({"name": f"S{j + 1}", "cls": c, "art_mm": round(w, 3), "at_mm": (round(x, 2), round(y, 2)),
                    "shape": owner(x, y), "pts": keep})
    return out


def pick_gaps(art: np.ndarray, frame: Frame, owner, n: int = 4, avoid=None):
    """The art's narrowest page features under `GAP_MAX_MM` (counters,
    spaces, keylines): medial points of the page, grouped; two enclosed and
    two open when there are."""
    bg = art == 0
    w2 = 2 * ndi.distance_transform_edt(bg) / R
    narrow = _skeleton(bg) & (w2 >= GAP_MIN_MM) & (w2 <= GAP_MAX_MM)
    lab, k = ndi.label(ndi.binary_dilation(narrow, iterations=1))
    bgl, _nb = ndi.label(bg)
    border = set(np.unique(np.concatenate([bgl[0], bgl[-1], bgl[:, 0], bgl[:, -1]])))
    allp = np.argwhere(narrow)
    feats = []
    for pts in _grouped((allp, lab[allp[:, 0], allp[:, 1]]), k):
        if len(pts) < 0.5 * R:
            continue
        if avoid is not None and avoid[tuple(pts[len(pts) // 2])]:
            continue
        feats.append((float(np.median(w2[pts[:, 0], pts[:, 1]])), bgl[tuple(pts[0])] not in border, pts))
    feats.sort(key=lambda f: f[0])
    pick = [f for f in feats if f[1]][:2] + [f for f in feats if not f[1]][:2]
    pick += [f for f in feats if all(f is not q for q in pick)][: max(0, n - len(pick))]
    out = []
    for j, (_med, enclosed, pts) in enumerate(sorted(pick, key=lambda f: f[0])[:n]):
        r, c = pts[len(pts) // 2]
        x, y = frame.mm(c, r)
        out.append({"name": f"{'C' if enclosed else 'G'}{j + 1}", "kind": "counter" if enclosed else "gap",
                    "art_mm": round(_med, 3),
                    "at_mm": (round(x, 2), round(y, 2)), "shape_near": owner(x, y), "pts": pts})
    return out


def width_at(mask: np.ndarray, pts: np.ndarray, radius_mm: float, extent_mm: float = 6.0) -> float:
    """2 x the largest distance-to-edge of `mask` within `radius_mm` of each
    point, median over the points (mm); 0 where the mask is gone. The window
    reaches `extent_mm` past the points: the distance to the window's own
    edge must never be the answer."""
    if len(pts) == 0:
        return 0.0
    r = max(1, int(round(radius_mm * R)))
    e = 2 * r + int(np.ceil(extent_mm * R))
    y0, x0 = np.maximum(pts.min(0) - e, 0)
    y1, x1 = np.minimum(pts.max(0) + e + 1, mask.shape)
    sub = mask[y0:y1, x0:x1]
    dt = ndi.distance_transform_edt(np.pad(sub, 1, constant_values=False))[1:-1, 1:-1] / R
    mx = ndi.maximum_filter(dt, size=2 * r + 1)
    return float(2 * np.median(mx[pts[:, 0] - y0, pts[:, 1] - x0]))


# ---------------------------------------------------------------- ledger ---
#: transitions and the bucket each stage's change goes to
STEPS = (("art", "stage4", "trace (stages 2-4)"), ("stage4", "reset", "small-text re-set"),
         ("reset", "stage5", "stage-5 growth (pull, underlap, round joins)"),
         ("stage5", "needle", "stitch emitter (satin rail pull, minimum widths, borders/edge caps)"),
         ("needle", "thread", "thread width"))


def ledger(run_dir: Path, write: bool = True) -> dict:
    cap = pickle.load(open(run_dir / "capture.pkl", "rb"))
    design = json.load(open(run_dir / "design.json"))
    frame, fp = footprints(cap, design, run_dir)
    from shapely.geometry import Point
    s4 = [(sid, wkb.loads(b)) for sid, _ti, b, _m in cap["stage4"]]

    def owner(x, y):
        p = Point(x, y)
        hit = [sid for sid, g in s4 if g.distance(p) < 0.3]
        return hit[0] if hit else None

    moved = {sid for (sid, _t, a, _m), (_s, _t2, b, _m2) in zip(cap["stage4"], cap["reset"]) if a != b}
    avoid = (_fill_polys(frame, [wkb.loads(b).buffer(AVOID_MM) for sid, _ti, b, _m in cap["stage4"] if sid in moved])
             if moved else None)
    strokes = pick_strokes(fp["art"], frame, owner, avoid=avoid)
    gaps = pick_gaps(fp["art"], frame, owner, avoid=avoid)
    kinds: dict = {}
    for run in design["runs"]:
        kinds.setdefault(run.get("shape"), set()).add(run["kind"])
    rows = {"slug": cap["slug"], "arm": cap["arm"], "garment": cap["garment"], "width": cap["width"],
            "flags": {**cap.get("extra", {}), **cap.get("over", {})},
            "pull_mm": cap.get("pull_mm"), "overlap_mm": cap.get("overlap_mm"),
            "classes": {str(k): v for k, v in cap["classes"].items()}, "pro_reg": cap.get("pro_reg"),
            "footprints": {}, "strokes": [], "gaps": []}
    for name, m in fp.items():
        ink = m > 0
        rows["footprints"][name] = {"ink_mm2": round(float(ink.sum()) / R ** 2, 1), "holes": _holes(ink),
                                    "by_class_mm2": {str(int(c)): round(float((m == c).sum()) / R ** 2, 1)
                                                     for c in np.unique(m) if c}}
    for s in strokes:
        art_w = width_at(fp["art"] == s["cls"], s["pts"], 0.0, extent_mm=s["art_mm"] + 1.0)
        rad = max(0.15, PROBE_REACH * art_w)
        row = {k: v for k, v in s.items() if k != "pts"}
        row["kinds"] = sorted(kinds.get(s["shape"], ()))
        row["mm"] = {name: round(width_at(m == s["cls"], s["pts"], rad, art_w + 2.0), 3) for name, m in fp.items()}
        rows["strokes"].append(row)
    for g in gaps:
        art_w = width_at(fp["art"] == 0, g["pts"], 0.0, extent_mm=g["art_mm"] + 1.0)
        rad = max(0.1, PROBE_REACH * art_w)
        row = {k: v for k, v in g.items() if k != "pts"}
        row["mm"] = {name: round(width_at(m == 0, g["pts"], rad, art_w + 2.0), 3) for name, m in fp.items()}
        rows["gaps"].append(row)
    rows["shares"] = shares(rows)
    if write:
        json.dump(rows, open(run_dir / "ledger.json", "w"), indent=1, default=str)
        strip(run_dir, frame, fp, strokes, gaps, rows)
    return rows


def shares(rows) -> dict:
    """MEAN over the probes of each step's added width (a gap's: width lost),
    so the steps sum to the art -> thread total, and each step's share."""
    out = {}
    for what, sign in (("strokes", 1.0), ("gaps", -1.0)):
        items = rows[what]
        if not items:
            continue
        d = {lab: float(np.mean([sign * (it["mm"][b] - it["mm"][a]) for it in items])) for a, b, lab in STEPS}
        total = float(np.mean([sign * (it["mm"]["thread"] - it["mm"]["art"]) for it in items]))
        out[what] = {"total_mm": round(total, 3), "steps_mm": {k: round(v, 3) for k, v in d.items()},
                     "share": {k: round(v / total, 2) if abs(total) > 1e-6 else None for k, v in d.items()}}
        if "pro" in items[0]["mm"]:
            out[what]["pro_minus_art_mm"] = round(float(np.mean([sign * (it["mm"]["pro"] - it["mm"]["art"])
                                                                 for it in items])), 3)
    return out


def _colour(lab: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(3)
    lut = np.vstack([[255, 255, 255], rng.integers(20, 200, (255, 3))]).astype(np.uint8)
    lut[1:] = np.minimum(lut[1:], 160)
    return lut[lab]


def strip(run_dir: Path, frame: Frame, fp: dict, strokes, gaps, rows, half_mm: float = 3.0):
    """One zoom row per probe (strokes then gaps), one column per footprint;
    each colour its own tint, page white, the art's edges red."""
    h = int(2 * half_mm * R)
    art = fp["art"]
    edge = (art != np.roll(art, 1, 0)) | (art != np.roll(art, 1, 1))
    named = {it["name"]: it for it in rows["strokes"] + rows["gaps"]}
    lines = []
    for probe in list(strokes) + list(gaps):
        x, y = probe["at_mm"]
        c, r = int((x - frame.x0) * R), int((y - frame.y0) * R)
        tiles = []
        for name in FOOTPRINTS:
            if name not in fp:
                continue
            img = np.full((h, h, 3), 255, np.uint8)
            y0, x0 = r - h // 2, c - h // 2
            ys0, xs0 = max(0, y0), max(0, x0)
            ys1, xs1 = min(frame.h, y0 + h), min(frame.w, x0 + h)
            sub = img[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
            sub[:] = _colour(fp[name][ys0:ys1, xs0:xs1])
            sub[edge[ys0:ys1, xs0:xs1]] = (0, 0, 230)
            cv2.putText(img, name, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 0, 0), 1, cv2.LINE_AA)
            tiles += [img, np.full((h, 3, 3), 180, np.uint8)]
        row = np.hstack(tiles[:-1])
        lab = np.full((16, row.shape[1], 3), 255, np.uint8)
        it = named[probe["name"]]
        txt = f"{probe['name']} ({probe.get('kind', 'stroke')}) mm: " + " ".join(f"{k} {v}" for k, v in it["mm"].items())
        cv2.putText(lab, txt[:170], (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1, cv2.LINE_AA)
        lines += [lab, row, np.full((4, row.shape[1], 3), 255, np.uint8)]
    if lines:
        w = max(line.shape[1] for line in lines)
        lines = [np.pad(line, ((0, 0), (0, w - line.shape[1]), (0, 0)), constant_values=255) for line in lines]
        cv2.imwrite(str(run_dir / "zoom_strip.png"), np.vstack(lines))
    full = [np.pad(_colour(fp[n]), ((24, 0), (0, 0), (0, 0)), constant_values=255) for n in FOOTPRINTS if n in fp]
    for img, n in zip(full, [n for n in FOOTPRINTS if n in fp]):
        img[24:][edge] = (0, 0, 230)
        cv2.putText(img, n, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 0, 0), 1, cv2.LINE_AA)
    s = 900 / full[0].shape[1]
    cv2.imwrite(str(run_dir / "footprints.png"),
                np.vstack([cv2.resize(f, (900, int(f.shape[0] * s)), interpolation=cv2.INTER_AREA) for f in full]))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    for d in argv:
        rows = ledger(Path(d))
        fpr = rows["footprints"]
        print(rows["slug"], rows["arm"], " ".join(f"{k}={v['ink_mm2']}/{v['holes']}" for k, v in fpr.items()))
        print("  shares", json.dumps(rows["shares"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
