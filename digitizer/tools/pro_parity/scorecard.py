"""Pro-similarity scorecard: how close is EMB-Bot's output to the professional
digitization of the same design? One number per design, 0-100.

Components (weights sum to 100):
  coverage   20  registered agreement of the SOLID sewn area — 0.125 mm raster,
                 ~0.5 mm thread, opacity-gated (widely-spaced rows do not read
                 as solid), symmetric (overspill is penalised), plus a visible
                 colour-surface comparison so a word replaced by the slab it
                 sits on cannot hide inside a good IoU
  direction  20  mean angular agreement of dominant stitch direction over the
                 shared solid area (2mm cells; 90deg off = 0, 0deg off = 1),
                 CHANCE-CORRECTED so random angles score 0 rather than 0.5
  sttype     20  agreement of stitch TYPE (satin vs fill vs run) over the shared
                 solid area, classified from geometry the same way on both sides,
                 CHANCE-CORRECTED against the two sides' own type mixes (this is
                 Cohen's kappa: an all-fill guess on an all-fill design earns 0)
  density    15  thread mm per solid mm2, ours vs pro, scored min(r, 1/r)
  underlay   10  sequence-aware: a stitch is underlay iff the ground it lies on
                 is re-covered later by top stitching of the same element.
                 Scored on economy (how much underlay, ours vs pro) and
                 composition (is it in the same places)
  travel     15  exposed drag (3/4): mm of UNTRIMMED thread lying on ground
                 that is bare and stays bare — a trimmed jump lays no thread, so
                 it is invisible here. Step length is irrelevant: a chain of
                 2.5 mm sewn steps across bare fabric costs exactly what one
                 30 mm drag costs. Plus trim economy (1/4): invisible is not the
                 same as free, and reaching zero drag by cutting the thread nine
                 times as often as the pro is not parity either.

Every overlap metric runs AFTER registration: pro files keep their native hoop
origin, ours is bbox-centred, so the two are compared only once a best-shift
search has aligned them.

SCALE CHANGE, 2026-08-14: `direction` and `sttype` are bounded agreement
measures whose raw floor is ~0.5, not 0 — random angles score 0.505 and a
shuffled type map scores 0.553 across this corpus, so about 21 of their combined
40 points used to be paid out for a wrong answer. Both are now chance-corrected
before weighting, (observed - chance) / (1 - chance), clamped at 0. Scores from
before this commit are on the old scale and are NOT comparable; `score_raw` and
`parts_raw` carry the old numbers forward so the two can be lined up.

The floors are analytic, not sampled, so the score stays deterministic:
  direction — a random angle mod pi puts the folded difference uniform on
              [0, pi/2], so the expected raw score is exactly 0.5 for any design
  sttype    — expected agreement under independence, sum_c p_pro(c)*p_ours(c),
              which is design-specific: matching a 95%-fill design by calling
              everything fill is worth ~0.9 raw and ~0 corrected

Usage: scorecard.py [--explain] [--json] <design_dir> [...]   (dirs from prep_all.py)
Emits score.json per dir and a summary table on stdout.
"""
import csv
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------- constants
# mm/px for the coverage raster. 0.125 rather than 0.25 because cv2.line
# quantises stroke width to an ODD pixel count: at 0.25 mm/px the thinnest line
# wider than one pixel is 3 px = 0.75 mm, half again as fat as real thread, and
# that alone let a 1.2 mm-spaced fill read as 81% as solid as a dense one. At
# 0.125 the same call paints 5 px across / ~3.7 px diagonally, i.e. 0.46-0.63 mm
# — actual embroidery thread, 0.4-0.6 mm.
RES = 0.125
THREAD_W = 0.5      # mm, drawn thread width (embroidery thread is 0.4-0.6)
CELL = 2.0          # mm, direction/type analysis cell
LONG_MM = 12.1      # machine max stitch; longer than this is never one stitch

# Opacity gate: ground counts as SOLID only where thread actually fills it.
OPACITY_WIN = 1.5   # mm, window the eye integrates over
OPACITY_MIN = 0.55  # covered fraction inside that window to read as solid

# "Hidden" test for exposed drag. A pixel is hidden if a SECOND thread pass
# covers it (leave-one-out: the drag's own thread contributes exactly one), or
# if it belongs to a sewn ELEMENT: a close that bridges rows up to CLOSE mm
# apart, then an open wider than a thread, which erases lone travel lines but
# keeps fills and satins whole (including their outermost, un-neighboured row).
DRAG_CLOSE_MM = 1.0
DRAG_OPEN_MM = 1.0
ACC_CHUNK = 16     # consecutive stitches that count as ONE pass of the needle

# Registration search
REG_RES = 0.5       # mm, raster used inside the shift search (speed)
REG_MAX = 40.0      # mm, largest shift the search may apply

# Trim inference when the artifacts carry no command column (see load_side).
TRIM_MIN_MM = 3.0   # machine.TRIM_AT_MM — engine trims jumps longer than this
TRIM_NEIGHBOUR = 2.5  # an isolated long move is a jump; a chain of them is a walk
# Trim economy floor: a handful of trims either way is not a parity difference,
# so the ratio only starts to bite once one side is well past this many.
TRIM_FLOOR = 8

# Underlay: a covering pass this many stitches later is a different pass, not
# the neighbouring stitch of the same column.
UNDERLAY_GAP = 15
UNDERLAY_MIN_MM = 0.5   # shorter than this is a degenerate defect, not underlay
UNDERLAY_COVERED = 0.6  # share of a stitch's ground that must be re-covered

WEIGHTS = {"coverage": 20, "direction": 20, "sttype": 20,
           "density": 15, "underlay": 10, "travel": 15}

# Chance floor for `direction`. Folding a random angle mod pi leaves the
# difference uniform on [0, pi/2], so E[1 - diff/(pi/2)] = 0.5 for every design
# — no sampling needed, and no seed to make the score wobble.
DIRECTION_CHANCE = 0.5
# Above this the two type mixes agree so completely (e.g. both sides all fill)
# that there is nothing left to discriminate and the correction is 0/0.
CHANCE_DEGENERATE = 0.999

_MANIFEST = {}


# ------------------------------------------------------------------ loading
def _manifest(dirpath):
    """manifest.json sits beside the design dirs; it carries the pro source path."""
    root = Path(dirpath).parent
    if root not in _MANIFEST:
        f = root / "manifest.json"
        try:
            _MANIFEST[root] = {e["slug"]: e for e in json.loads(f.read_text())}
        except Exception:
            _MANIFEST[root] = {}
    return _MANIFEST[root]


def read_csv(path):
    """Rows of (block, x, y, trim_before). trim_before comes from a `trim`/`cmd`
    column when prep wrote one, else it is left None for infer_trims()."""
    rows = []
    with open(path) as f:
        rdr = csv.DictReader(f)
        cols = set(rdr.fieldnames or ())
        has_trim = "trim" in cols or "cmd" in cols
        for r in rdr:
            t = None
            if "trim" in cols:
                t = str(r["trim"]).strip().lower() in ("1", "true", "t", "yes")
            elif "cmd" in cols:
                t = str(r["cmd"]).strip().upper() in ("TRIM", "COLOR_CHANGE", "STOP")
            rows.append((int(r["block"]), float(r["x_mm"]), float(r["y_mm"]), t))
    return rows, has_trim


def pro_trims_from_source(slug, dirpath, n):
    """Authoritative trim flags, re-decoded from the pro file in prep's manifest.

    prep_all.decode() appends STITCH coordinates in order and drops JUMP/TRIM,
    so index k of the CSV is the k'th STITCH of the pattern. Returns None if the
    file is unreadable or the counts disagree (then we fall back to inference).
    """
    ent = _manifest(dirpath).get(slug)
    if not ent or not ent.get("file"):
        return None
    try:
        import pystitch
        pat = pystitch.read(ent["file"])
    except Exception:
        return None
    flags, pending = [], False
    for _x, _y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            flags.append(pending)
            pending = False
        elif c in (pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.STOP):
            pending = True
        elif c == pystitch.END:
            break
    return flags if len(flags) == n else None


def infer_trims(segs):
    """Fallback when no command data exists: a long move that stands ALONE
    between two ordinary stitches is a jump the machine trimmed; a long move
    with long neighbours is a walk, which is sewn thread and stays visible.

    Measured against the engine's real run flags on gaulke_roofing_hat /
    gaulke_roofing_lc / hotel_fremont_hat this recovers 99.7% of stitches
    correctly and lands within ~6 mm of the exposed-drag figure the exact flags
    give (vs. a 5-40x overshoot if trims are ignored altogether).
    """
    out = []
    for i, s in enumerate(segs):
        d = s[4]
        prev = segs[i - 1][4] if i > 0 else 0.0
        nxt = segs[i + 1][4] if i + 1 < len(segs) else 0.0
        trimmed = d >= TRIM_MIN_MM and prev < TRIM_NEIGHBOUR and nxt < TRIM_NEIGHBOUR
        out.append(s[:6] + (trimmed,))
    return out


def to_segs(rows):
    """(x0,y0,x1,y1,len,block,trimmed) for consecutive same-block stitch pairs."""
    segs = []
    for k in range(len(rows) - 1):
        b0, x0, y0, _ = rows[k]
        b1, x1, y1, t1 = rows[k + 1]
        if b0 != b1:
            continue
        segs.append((x0, y0, x1, y1, math.hypot(x1 - x0, y1 - y0), b0, bool(t1)))
    return segs


def load_side(dirpath, which, slug):
    rows, has_trim = read_csv(Path(dirpath) / f"{which}_stitches.csv")
    src = "csv-column" if has_trim else None
    if not has_trim and which == "pro":
        flags = pro_trims_from_source(slug, dirpath, len(rows))
        if flags is not None:
            rows = [(b, x, y, flags[i]) for i, (b, x, y, _) in enumerate(rows)]
            has_trim, src = True, "pro-source"
    segs = to_segs(rows)
    if not has_trim:
        segs = infer_trims(segs)
        src = "inferred"
        # Inference marks SEGMENTS, not rows, and to_segs drops the pair that
        # straddles a block boundary — so count what we actually know about.
        n_trims = sum(1 for s in segs if s[6])
    else:
        n_trims = sum(1 for r in rows if r[3])
    return rows, segs, src, n_trims


def load_blocks(dirpath, which):
    try:
        return json.loads((Path(dirpath) / f"{which}_blocks.json").read_text())
    except Exception:
        return []


# --------------------------------------------------------------- rasterising
def bounds(*seglists, pad=8.0):
    xs, ys = [], []
    for segs in seglists:
        for (x0, y0, x1, y1, d, b, t) in segs:
            xs += [x0, x1]
            ys += [y0, y1]
    if not xs:
        return (0.0, 0.0, 1.0, 1.0)
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _grid(bb, res):
    x0, y0, x1, y1 = bb
    return int((x1 - x0) / res) + 4, int((y1 - y0) / res) + 4


def raster(segs, bb, res=RES, tw=THREAD_W, shift=(0.0, 0.0), only_blocks=None):
    """Binary thread coverage. Trimmed moves lay no thread, so they are skipped;
    so are impossible moves (> one machine stitch) that survived inference."""
    x0, y0 = bb[0], bb[1]
    W, H = _grid(bb, res)
    m = np.zeros((H, W), np.uint8)
    th = max(1, int(round(tw / res)))
    dx, dy = shift
    for (ax, ay, bx, by, d, blk, tr) in segs:
        if tr or d > LONG_MM or d <= 0:
            continue
        if only_blocks is not None and blk not in only_blocks:
            continue
        cv2.line(m,
                 (int((ax + dx - x0) / res) + 2, int((ay + dy - y0) / res) + 2),
                 (int((bx + dx - x0) / res) + 2, int((by + dy - y0) / res) + 2),
                 1, th)
    return m > 0


def acc_raster(segs, bb, res=RES, tw=THREAD_W, chunk=ACC_CHUNK):
    """Per-pixel count of SEPARATE thread passes.

    Counted per chunk of `chunk` consecutive stitches, not per stitch: stitches
    that are neighbours in sew order are one pass of the needle, and their
    unavoidable overlap at the shared endpoint must not make a walk look like
    two passes covering each other. A pass that comes back over the same ground
    later in the file is a different chunk and does count.
    """
    x0, y0 = bb[0], bb[1]
    W, H = _grid(bb, res)
    acc = np.zeros((H, W), np.int32)
    tmp = np.zeros((H, W), np.uint8)
    th = max(1, int(round(tw / res)))
    pad = th + 2
    n = 0
    lo_i = lo_j = 1 << 30
    hi_i = hi_j = -1

    def flush():
        nonlocal lo_i, lo_j, hi_i, hi_j
        if hi_i < 0:
            return
        i0, i1 = max(0, lo_i - pad), min(H, hi_i + pad)
        j0, j1 = max(0, lo_j - pad), min(W, hi_j + pad)
        acc[i0:i1, j0:j1] += tmp[i0:i1, j0:j1]
        tmp[i0:i1, j0:j1] = 0
        lo_i = lo_j = 1 << 30
        hi_i = hi_j = -1

    for (ax, ay, bx, by, d, blk, tr) in segs:
        if tr or d > LONG_MM or d <= 0:
            continue
        if n and n % chunk == 0:
            flush()
        pa = (int((ax - x0) / res) + 2, int((ay - y0) / res) + 2)
        pb = (int((bx - x0) / res) + 2, int((by - y0) / res) + 2)
        cv2.line(tmp, pa, pb, 1, th)
        lo_i = min(lo_i, pa[1], pb[1]); hi_i = max(hi_i, pa[1], pb[1])
        lo_j = min(lo_j, pa[0], pb[0]); hi_j = max(hi_j, pa[0], pb[0])
        n += 1
    flush()
    return acc


def opacity(cov, res=RES, win=OPACITY_WIN):
    k = max(1, int(round(win / res)) | 1)
    return cv2.blur(cov.astype(np.float32), (k, k))


def solid(cov, res=RES):
    """Ground a customer reads as sewn: thread that actually fills its window.
    A 41%-density fill is thread on the fabric but it is NOT solid coverage."""
    return opacity(cov, res) >= OPACITY_MIN


# -------------------------------------------------------------- registration
def _iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def register(pro_segs, our_segs, bb):
    """Best translation of OURS onto PRO. Pro keeps its native hoop origin and
    ours is bbox-centred, so raw overlap can be meaningless (machine_beanie is
    26.7 mm apart in y). Seeds at both no-shift and bbox-centre delta, then
    hill-climbs on solid IoU, 1.0 mm down to 0.25 mm."""
    pc = solid(raster(pro_segs, bb, res=REG_RES), res=REG_RES)

    def centre(segs):
        xs = [s[0] for s in segs] + [s[2] for s in segs]
        ys = [s[1] for s in segs] + [s[3] for s in segs]
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)

    def at(dx, dy):
        return _iou(pc, solid(raster(our_segs, bb, res=REG_RES, shift=(dx, dy)),
                              res=REG_RES))

    pcx, pcy = centre(pro_segs)
    ocx, ocy = centre(our_segs)
    seeds = [(0.0, 0.0), (round(pcx - ocx, 2), round(pcy - ocy, 2))]
    best = (0.0, 0.0, at(0.0, 0.0))
    for sx, sy in seeds:
        if math.hypot(sx, sy) > REG_MAX:
            continue
        cx, cy, cur = sx, sy, at(sx, sy)
        if cur > best[2]:
            best = (cx, cy, cur)
        step = 1.0
        while step >= 0.25:
            moved = True
            while moved:
                moved = False
                for ddx, ddy in ((step, 0), (-step, 0), (0, step), (0, -step),
                                 (step, step), (-step, -step),
                                 (step, -step), (-step, step)):
                    if math.hypot(cx + ddx, cy + ddy) > REG_MAX:
                        continue
                    v = at(cx + ddx, cy + ddy)
                    if v > cur + 1e-6:
                        cur, cx, cy, moved = v, cx + ddx, cy + ddy, True
                        if v > best[2]:
                            best = (cx, cy, v)
            step /= 2
    return best[0], best[1], best[2]


def shifted(segs, dx, dy):
    if dx == 0.0 and dy == 0.0:
        return segs
    return [(a + dx, b + dy, c + dx, d + dy, e, f, g) for (a, b, c, d, e, f, g) in segs]


# ------------------------------------------------------------- cell analysis
def cell_stats(segs, bb):
    """Per CELL-mm cell: dominant direction (length-weighted mean of doubled
    angles) and a stitch-type guess from median seg length + reversal rate."""
    x0, y0, x1, y1 = bb
    W = int((x1 - x0) / CELL) + 2
    H = int((y1 - y0) / CELL) + 2
    vx = np.zeros((H, W)); vy = np.zeros((H, W)); tot = np.zeros((H, W))
    lens = [[[] for _ in range(W)] for _ in range(H)]
    revs = [[[0, 0] for _ in range(W)] for _ in range(H)]
    prev_ang = {}
    for (ax, ay, bx, by, d, blk, tr) in segs:
        if tr or d > LONG_MM or d < 0.05:
            prev_ang.pop(blk, None)
            continue
        ci = int(((ay + by) / 2 - y0) / CELL)
        cj = int(((ax + bx) / 2 - x0) / CELL)
        if not (0 <= ci < H and 0 <= cj < W):
            continue
        ang = math.atan2(by - ay, bx - ax)
        vx[ci, cj] += math.cos(2 * ang) * d
        vy[ci, cj] += math.sin(2 * ang) * d
        tot[ci, cj] += d
        lens[ci][cj].append(d)
        pa = prev_ang.get(blk)
        if pa is not None:
            flip = abs(((ang - pa + math.pi) % (2 * math.pi)) - math.pi) > math.radians(150)
            revs[ci][cj][0] += 1
            revs[ci][cj][1] += 1 if flip else 0
        prev_ang[blk] = ang
    ang_map = np.full((H, W), np.nan)
    typ_map = np.full((H, W), -1)   # 0=run 1=satin 2=fill
    for i in range(H):
        for j in range(W):
            if tot[i, j] < 2.0:
                continue
            ang_map[i, j] = math.atan2(vy[i, j], vx[i, j]) / 2
            ls = sorted(lens[i][j]); p50 = ls[len(ls) // 2]
            n, f = revs[i][j]
            rev = (f / n) if n else 0
            if rev > 0.55 and p50 >= 0.8:
                typ_map[i, j] = 1
            elif p50 >= 2.6 and rev < 0.55:
                typ_map[i, j] = 2
            elif p50 < 0.8:
                typ_map[i, j] = 0
            else:
                typ_map[i, j] = 2 if rev < 0.3 else 1
    return ang_map, typ_map, tot


def solid_cells(solid_mask, bb):
    """Downsample the 0.25mm solid mask onto the CELL grid used above."""
    x0, y0, x1, y1 = bb
    W = int((x1 - x0) / CELL) + 2
    H = int((y1 - y0) / CELL) + 2
    step = int(round(CELL / RES))
    out = np.zeros((H, W), bool)
    sh, sw = solid_mask.shape
    for i in range(H):
        r0 = i * step + 2
        if r0 >= sh:
            break
        blk = solid_mask[r0:r0 + step, 2:2 + W * step]
        if blk.size == 0:
            continue
        cols = blk.shape[1] // step
        if cols == 0:
            continue
        red = blk[:, :cols * step].reshape(blk.shape[0], cols, step).mean(axis=(0, 2))
        out[i, :cols] = red >= 0.5
    return out


# ------------------------------------------------------------------ coverage
def colour_groups(blocks):
    """block index -> rgb, grouped by colour so one word sewn in one colour is
    one group even when prep split it across blocks."""
    groups = {}
    for b in blocks:
        rgb = tuple(b.get("rgb", (0, 0, 0)))
        groups.setdefault(rgb, []).append(b["block"])
    return groups


def surface(segs, bb, groups, order):
    """Per-pixel visible colour id, painted in sew order — last thread down wins,
    which is what the customer actually sees. -1 = bare fabric."""
    W, H = _grid(bb, RES)
    lab = np.full((H, W), -1, np.int16)
    for cid in order:
        m = solid(raster(segs, bb, only_blocks=set(groups[cid])))
        lab[m] = cid
    return lab


def coverage_component(pro_segs, our_segs, bb, pro_blocks, our_blocks):
    pc = raster(pro_segs, bb)
    oc = raster(our_segs, bb)
    sp, so = solid(pc), solid(oc)
    px = float(RES * RES)
    inter = float((sp & so).sum())
    iou = inter / max(float((sp | so).sum()), 1.0)
    recall = inter / max(float(sp.sum()), 1.0)
    precision = inter / max(float(so.sum()), 1.0)
    overspill_mm2 = float((so & ~sp).sum()) * px
    missing_mm2 = float((sp & ~so).sum()) * px

    # Gap/opacity diagnostics. The scoring work is done by the solid() gate —
    # rows spaced past the thread width never enter sp/so at all, which is what
    # stopped a 41%-density fill from reading as 98% covered. These numbers say
    # how much fabric still shows through where the pro reads solid; they are
    # reported, not re-scored, because the gate already removed that ground.
    pop, oop = opacity(pc), opacity(oc)
    op_in_pro = float(oop[sp].mean()) if sp.any() else 0.0
    p_op = float(pop[sp].mean()) if sp.any() else 0.0
    o_op = float(oop[so].mean()) if so.any() else 0.0

    # ---- colour surface -------------------------------------------------
    # Group both sides by thread colour, then map each of OUR colours to the
    # nearest PRO colour. Painting each side in sew order gives the visible
    # surface; comparing the two catches "right ground, wrong shape" — a word
    # replaced by the slab it sits on covers the same mm2 and still reads wrong.
    pgroups = colour_groups(pro_blocks)
    ogroups_rgb = colour_groups(our_blocks)
    pkeys = list(pgroups.keys())
    if pkeys:
        ogroups = {}
        for rgb, idxs in ogroups_rgb.items():
            near = min(range(len(pkeys)),
                       key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, pkeys[i])))
            ogroups.setdefault(near, []).extend(idxs)
        pg = {i: pgroups[k] for i, k in enumerate(pkeys)}
        plab = surface(pro_segs, bb, pg, sorted(pg, key=lambda i: min(pg[i])))
        olab = surface(our_segs, bb, ogroups, sorted(ogroups, key=lambda i: min(ogroups[i])))
        vis = sp | so
        agree = float((plab[vis] == olab[vis]).mean()) if vis.any() else 0.0
    else:
        plab = olab = None
        agree = recall

    # per-colour recall — an entire missing word cannot hide behind a good IoU
    per_colour = []
    for i, rgb in enumerate(pkeys):
        m = solid(raster(pro_segs, bb, only_blocks=set(pgroups[rgb])))
        a = float(m.sum())
        if a * px < 15.0:            # ignore slivers under 15 mm2
            continue
        entry = {
            "rgb": list(rgb),
            "area_mm2": round(a * px, 1),
            "recall": round(float((m & so).sum()) / a, 3),
        }
        if plab is not None:
            shown = plab == i                       # pixels this colour is ON TOP of
            entry["visible_mm2"] = round(float(shown.sum()) * px, 1)
            entry["colour_recall"] = round(
                float((olab[shown] == i).mean()) if shown.any() else 1.0, 3)
        per_colour.append(entry)
    per_colour.sort(key=lambda c: -c["area_mm2"])
    tot_a = sum(c["area_mm2"] for c in per_colour) or 1.0
    big = [c for c in per_colour if c["area_mm2"] / tot_a >= 0.03]
    worst = min((c.get("colour_recall", c["recall"]) for c in big), default=recall)

    score = 0.5 * iou + 0.3 * agree + 0.2 * worst
    detail = {
        "solid_iou": round(iou, 3),
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "colour_surface_agreement": round(agree, 3),
        "worst_colour_recall": round(worst, 3),
        "opacity_self_pro": round(p_op, 3),
        "opacity_self_ours": round(o_op, 3),
        "opacity_over_pro_solid": round(op_in_pro, 3),
        "overspill_mm2": round(overspill_mm2, 1),
        "missing_mm2": round(missing_mm2, 1),
        "pro_solid_mm2": round(float(sp.sum()) * px, 1),
        "ours_solid_mm2": round(float(so.sum()) * px, 1),
        "pro_thread_mm2": round(float(pc.sum()) * px, 1),
        "ours_thread_mm2": round(float(oc.sum()) * px, 1),
        "per_colour": per_colour,
    }
    return score, sp, so, detail


# -------------------------------------------------------------------- travel
def hidden_mask(segs, bb):
    """Ground where thread does not read as a stray line on the fabric.

    Two ways to qualify, and both are needed:

    `acc >= 2` — leave-one-out. A drag lays exactly one pass over the ground it
    crosses, so a second pass means something ELSE is there covering it. This is
    what stops a lone travel line from hiding behind its own thread, which a
    plain opacity test cannot do at any window small enough to see the 2-3 mm
    gaps between letters.

    ELEMENT — a closing that bridges gaps up to DRAG_CLOSE_MM followed by an
    opening wider than a thread. A fill's rows close into a blob and survive the
    opening; a single travel line is erased by it however long it runs. Without
    this every element's outermost row (which has no neighbour on one side, so
    `acc == 1`) would read as drag, charging each shape for its own perimeter.
    """
    acc = acc_raster(segs, bb)
    cov = (acc >= 1).astype(np.uint8)
    kc = max(3, int(round(DRAG_CLOSE_MM / RES)) | 1)
    ko = max(3, int(round(DRAG_OPEN_MM / RES)) | 1)
    elem = cv2.morphologyEx(cov, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kc, kc)))
    elem = cv2.morphologyEx(elem, cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ko, ko)))
    return (acc >= 2) | (elem > 0)


def exposed_drag(segs, bb, hid):
    """mm of untrimmed thread whose path lies on ground that stays bare.

    Length-agnostic on purpose: sampled every RES mm, so 12 sewn 2.5 mm steps
    across bare fabric score exactly the same as one 30 mm drag. Trimmed moves
    lay no thread and are skipped entirely.
    """
    x0, y0 = bb[0], bb[1]
    H, W = hid.shape
    total = 0.0
    walks = 0
    worst = 0.0
    for (ax, ay, bx, by, d, blk, tr) in segs:
        if tr or d <= 1e-9:
            continue
        n = max(2, int(d / RES) + 1)
        ts = np.linspace(0.0, 1.0, n)
        px = ((ax + (bx - ax) * ts - x0) / RES).astype(np.int32) + 2
        py = ((ay + (by - ay) * ts - y0) / RES).astype(np.int32) + 2
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        bare = np.ones(n, bool)
        bare[ok] = ~hid[py[ok], px[ok]]
        f = float(bare.mean())
        e = f * d
        total += e
        if f > 0.5 and d >= 2.0:
            walks += 1
        worst = max(worst, e)
    return total, walks, worst


# ------------------------------------------------------------------ underlay
def underlay_stats(segs, bb, res=0.4):
    """Sequence-aware underlay: a stitch is underlay iff the ground it lies on
    is re-covered LATER by stitching of the same element.

    "Later" means at least UNDERLAY_GAP stitches later — the next stitch of the
    same satin column does not count as covering its neighbour. Degenerate
    sub-0.5 mm stitches are defects, not underlay, and are excluded from both
    the numerator and the denominator (machine_beanie's 935 of them used to read
    as a perfect 1.0 underlay share).

    The cover must be the SAME COLOUR BLOCK: underlay is sewn with the needle
    that will cover it. A gold background later covered by black lettering is
    layered artwork, not underlay, and counting it as such invents underlay
    the pro never sewed.

    Returns (underlay_mm, sewn_mm, mask of underlay ground at RES).
    """
    x0, y0 = bb[0], bb[1]
    W, H = _grid(bb, res)
    last = np.full((H, W), -1, np.int32)
    lastb = np.full((H, W), -2, np.int32)
    keep = [s for s in segs if not s[6] and 0 < s[4] <= LONG_MM]
    paths = []
    for idx, (ax, ay, bx, by, d, blk, tr) in enumerate(keep):
        n = max(2, int(d / res) + 1)
        ts = np.linspace(0.0, 1.0, n)
        px = ((ax + (bx - ax) * ts - x0) / res).astype(np.int32) + 2
        py = ((ay + (by - ay) * ts - y0) / res).astype(np.int32) + 2
        ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        px, py = px[ok], py[ok]
        paths.append((px, py, d, blk))
        last[py, px] = idx
        lastb[py, px] = blk
    under_mm = 0.0
    sewn_mm = 0.0
    under_paths = []
    for idx, (px, py, d, blk) in enumerate(paths):
        if d < UNDERLAY_MIN_MM:
            continue
        sewn_mm += d
        if px.size == 0:
            continue
        covered = float(((last[py, px] > idx + UNDERLAY_GAP)
                         & (lastb[py, px] == blk)).mean())
        if covered >= UNDERLAY_COVERED:
            under_mm += d
            under_paths.append((px, py))
    umask = np.zeros((H, W), bool)
    for px, py in under_paths:
        umask[py, px] = True
    return under_mm, sewn_mm, umask


def _to_cells(mask, res):
    """Any-underlay-in-this-CELL, so composition asks 'is there underlay in this
    part of the design' rather than 'are the two underlay paths pixel-identical'
    (a zigzag and an edge-walk underlay serve the same purpose)."""
    step = max(1, int(round(CELL / res)))
    H, W = mask.shape
    h, w = H // step, W // step
    if h == 0 or w == 0:
        return mask
    return mask[:h * step, :w * step].reshape(h, step, w, step).any(axis=(1, 3))


def underlay_component(pro_segs, our_segs, bb, res=0.4):
    pu, ps_, pmask = underlay_stats(pro_segs, bb, res=res)
    ou, os_, omask = underlay_stats(our_segs, bb, res=res)
    pf = pu / ps_ if ps_ else 0.0
    of = ou / os_ if os_ else 0.0
    eps = 0.02                                   # 2% of thread ~= "no underlay"
    r = (of + eps) / (pf + eps)
    economy = min(r, 1.0 / r)                    # over-spend is as wrong as under
    pcell, ocell = _to_cells(pmask, res), _to_cells(omask, res)
    if pcell.any() or ocell.any():
        composition = _iou(pcell, ocell)
    else:
        composition = 1.0                        # neither side lays underlay
    if pf < 0.01 and of < 0.01:
        composition = 1.0
    score = 0.5 * economy + 0.5 * composition
    return score, {
        "underlay_share_pro": round(pf, 3),
        "underlay_share_ours": round(of, 3),
        "underlay_mm_pro": round(pu, 1),
        "underlay_mm_ours": round(ou, 1),
        "underlay_economy": round(economy, 3),
        "underlay_composition": round(composition, 3),
    }


# -------------------------------------------------------------------- scoring
def thread_len(segs):
    return sum(d for (_, _, _, _, d, _, tr) in segs if not tr and d <= LONG_MM)


def chance_correct(observed, chance):
    """Rescale a bounded agreement measure so `chance` reads 0 and 1 stays 1.

    Clamped at 0: doing WORSE than chance is not more informative than chance,
    and a negative component would let one bad area claw points off another.
    When chance is degenerate (nothing to discriminate) the raw value is passed
    through — the alternative is 0/0, and a design whose types genuinely all
    match should not be marked down for the task having been easy.
    """
    if chance >= CHANCE_DEGENERATE:
        return observed
    return max(0.0, (observed - chance) / (1.0 - chance))


def type_chance(pro_types, our_types):
    """Expected type agreement if the two maps were independent: the kappa
    baseline, sum over classes of p_pro(c) * p_ours(c).

    Design-specific on purpose. A design the pro sewed 95% as fill is matched
    95% of the time by an engine that can only fill, and that number says
    nothing about whether the engine knows what a satin is.
    """
    if pro_types.size == 0 or our_types.size == 0:
        return 0.0
    return float(sum(float((pro_types == c).mean()) * float((our_types == c).mean())
                     for c in (0, 1, 2)))


def score_design(dirpath, explain=False):
    d = Path(dirpath)
    slug = d.name
    _pro_rows, pro, pro_src, p_trims = load_side(d, "pro", slug)
    _our_rows, our, our_src, o_trims = load_side(d, "ours", slug)
    pro_blocks = load_blocks(d, "pro")
    our_blocks = load_blocks(d, "ours")
    parts, detail = {}, {}

    # 1. registration -------------------------------------------------------
    # Search in a frame holding both sides where they sit; score in a frame
    # holding both sides where they END UP. machine_beanie moves 26.7 mm, and a
    # raster clipped at the old frame would silently drop the thread that moved
    # out of it — and count the clipped-away path as exposed drag.
    dx, dy, reg_iou = register(pro, our, bounds(pro, our))
    our_r = shifted(our, dx, dy)
    bb = bounds(pro, our_r)
    detail["registration_mm"] = [round(dx, 2), round(dy, 2)]
    detail["trim_source"] = {"pro": pro_src, "ours": our_src}

    # 2. coverage -----------------------------------------------------------
    cov, sp, so, cov_detail = coverage_component(pro, our_r, bb, pro_blocks, our_blocks)
    parts["coverage"] = cov
    detail.update({k: v for k, v in cov_detail.items() if k != "per_colour"})

    # 3/4. direction + stitch type over the SHARED SOLID area ---------------
    pa, pt, _ = cell_stats(pro, bb)
    oa, ot, _ = cell_stats(our_r, bb)
    shared = solid_cells(sp & so, bb)
    h = min(pa.shape[0], shared.shape[0]); w = min(pa.shape[1], shared.shape[1])
    both = np.zeros(pa.shape, bool)
    both[:h, :w] = shared[:h, :w]
    both &= ~np.isnan(pa) & ~np.isnan(oa)
    # Both are chance-corrected before they are weighted — see the module
    # docstring. `raw` keeps the uncorrected agreement so old scores can still
    # be lined up against new ones.
    chance, raw = {}, {}
    if both.any():
        diff = np.abs(pa[both] - oa[both])
        diff = np.minimum(diff, math.pi - diff)          # angles are mod pi
        raw["direction"] = float(np.mean(1 - diff / (math.pi / 2)))
        chance["direction"] = DIRECTION_CHANCE
        parts["direction"] = chance_correct(raw["direction"], DIRECTION_CHANCE)

        tboth = both & (pt >= 0) & (ot >= 0)
        if tboth.any():
            raw["sttype"] = float(np.mean(pt[tboth] == ot[tboth]))
            chance["sttype"] = type_chance(pt[tboth], ot[tboth])
            parts["sttype"] = chance_correct(raw["sttype"], chance["sttype"])
        else:
            raw["sttype"] = 0.0
            chance["sttype"] = 0.0
            parts["sttype"] = 0.0
        detail["shared_cells"] = int(both.sum())
        detail["type_cells"] = int(tboth.sum())
    else:
        for k in ("direction", "sttype"):
            raw[k] = chance[k] = parts[k] = 0.0
        detail["shared_cells"] = 0
        detail["type_cells"] = 0
    detail["chance_floor"] = {k: round(v, 3) for k, v in chance.items()}
    detail["raw_agreement"] = {k: round(v, 3) for k, v in raw.items()}

    # 5. density over SOLID area -------------------------------------------
    px = RES * RES
    dens_p = thread_len(pro) / max(float(sp.sum()) * px, 1.0)
    dens_o = thread_len(our_r) / max(float(so.sum()) * px, 1.0)
    r = dens_o / dens_p if dens_p else 0.0
    parts["density"] = min(r, 1 / r) if r > 0 else 0.0
    detail["dens_pro_mm_per_mm2"] = round(dens_p, 2)
    detail["dens_ours_mm_per_mm2"] = round(dens_o, 2)

    # 6. underlay -----------------------------------------------------------
    parts["underlay"], und_detail = underlay_component(pro, our_r, bb)
    detail.update(und_detail)

    # 7. travel = exposed drag + trim economy -------------------------------
    p_drag, p_walks, p_worst = exposed_drag(pro, bb, hidden_mask(pro, bb))
    o_drag, o_walks, o_worst = exposed_drag(our_r, bb, hidden_mask(our_r, bb))
    width_mm = max(bb[2] - bb[0] - 16.0, 10.0)
    tol = 0.2 * width_mm            # half credit at ~1/5 of a design width of drag
    excess = max(0.0, o_drag - p_drag)
    drag_score = 1.0 / (1.0 + excess / tol)
    # Trim COUNTS are only scored when they are real. Inference was tuned for
    # drag (where being wrong about a 5 mm move costs 5 mm) and validated there;
    # as a census it over-counts an order of magnitude, flagging every isolated
    # long satin stitch. Scoring on that would be inventing a number.
    trims_real = "inferred" not in (pro_src, our_src)
    trim_economy = (min(1.0, (p_trims + TRIM_FLOOR) / (o_trims + TRIM_FLOOR))
                    if trims_real else 1.0)
    parts["travel"] = 0.75 * drag_score + 0.25 * trim_economy
    detail.update({
        "exposed_drag_mm_pro": round(p_drag, 1),
        "exposed_drag_mm_ours": round(o_drag, 1),
        "exposed_walks_pro": p_walks,
        "exposed_walks_ours": o_walks,
        "longest_exposed_mm_ours": round(o_worst, 1),
        "drag_tolerance_mm": round(tol, 1),
        "drag_score": round(drag_score, 3),
        "trim_economy": round(trim_economy, 3),
        "trim_economy_scored": trims_real,
        "trims_pro": p_trims,
        "trims_ours": o_trims,
    })

    total = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    parts_raw = dict(parts, **raw)          # raw only differs for the two above
    total_raw = sum(WEIGHTS[k] * parts_raw[k] for k in WEIGHTS)
    out = {"score": round(total, 1),
           "score_raw": round(total_raw, 1),
           "parts": {k: round(v, 3) for k, v in parts.items()},
           "parts_raw": {k: round(v, 3) for k, v in parts_raw.items()},
           "detail": detail}
    if explain:
        out["explain"] = {
            "weights": WEIGHTS,
            "points": {k: round(WEIGHTS[k] * parts[k], 2) for k in WEIGHTS},
            "lost": {k: round(WEIGHTS[k] * (1 - parts[k]), 2) for k in WEIGHTS},
            "registration": {"shift_mm": [round(dx, 2), round(dy, 2)],
                             "solid_iou_at_shift": round(reg_iou, 3)},
            # Now SCORED, not a warning label: `chance_floor` is the baseline
            # each component was rescaled against, and `chance_points_removed`
            # is what the old scale used to hand over for a wrong answer.
            "chance_floor": {k: round(v, 3) for k, v in chance.items()},
            "raw_agreement": {k: round(v, 3) for k, v in raw.items()},
            "chance_points_removed": {
                k: round(WEIGHTS[k] * (parts_raw[k] - parts[k]), 2)
                for k in chance},
            "score_raw_old_scale": round(total_raw, 1),
            "per_colour_recall": cov_detail["per_colour"],
            "params": {"raster_mm": RES, "thread_mm": THREAD_W,
                       "opacity_win_mm": OPACITY_WIN, "opacity_min": OPACITY_MIN,
                       "drag_close_mm": DRAG_CLOSE_MM, "drag_open_mm": DRAG_OPEN_MM,
                       "acc_chunk_stitches": ACC_CHUNK, "trim_floor": TRIM_FLOOR,
                       "underlay_gap_stitches": UNDERLAY_GAP},
        }
    (d / "score.json").write_text(json.dumps(out, indent=1))
    return out


def print_explain(name, s):
    p, det = s["parts"], s["detail"]
    e = s.get("explain", {})
    print(f"\n=== {name}  score {s['score']}/100 "
          f"(old uncorrected scale: {s.get('score_raw', '-')}) ===")
    print(f"  registration shift {det['registration_mm']} mm   "
          f"trim data from {det['trim_source']['pro']} (pro) / "
          f"{det['trim_source']['ours']} (ours)")
    ch = det.get("chance_floor", {})
    rawa = det.get("raw_agreement", {})
    for k in WEIGHTS:
        line = (f"  {k:9s} {p[k]:.3f} x{WEIGHTS[k]:3d} = {e.get('points', {}).get(k, 0):5.2f}"
                f"   (lost {e.get('lost', {}).get(k, 0):5.2f})")
        if k in ch:
            line += (f"   [raw {rawa.get(k, 0):.3f} - chance {ch[k]:.3f} "
                     f"= {WEIGHTS[k] * (rawa.get(k, 0) - p[k]):5.2f} pts removed]")
        print(line)
    print(f"  coverage : solid IoU {det['solid_iou']} recall {det['recall']} "
          f"precision {det['precision']} colour-surface {det['colour_surface_agreement']} "
          f"worst-colour {det['worst_colour_recall']}")
    print(f"             opacity: pro fills {det['opacity_self_pro']} of its own solid, "
          f"ours {det['opacity_self_ours']} of its own, {det['opacity_over_pro_solid']} of pro's")
    print(f"             missing {det['missing_mm2']}mm2  overspill {det['overspill_mm2']}mm2")
    print(f"             solid area pro {det['pro_solid_mm2']} vs ours {det['ours_solid_mm2']} mm2")
    for c in e.get("per_colour_recall", []):
        print(f"               rgb{tuple(c['rgb'])} area {c['area_mm2']:8.1f}mm2  "
              f"recall {c['recall']}  visible {c.get('visible_mm2', '-')}mm2 "
              f"colour-recall {c.get('colour_recall', '-')}")
    print(f"  density  : pro {det['dens_pro_mm_per_mm2']} vs ours "
          f"{det['dens_ours_mm_per_mm2']} mm thread / mm2 solid")
    print(f"  underlay : share pro {det['underlay_share_pro']} ours {det['underlay_share_ours']}"
          f"  economy {det['underlay_economy']} composition {det['underlay_composition']}")
    print(f"  travel   : exposed drag pro {det['exposed_drag_mm_pro']}mm "
          f"ours {det['exposed_drag_mm_ours']}mm "
          f"(walks {det['exposed_walks_pro']}/{det['exposed_walks_ours']}, "
          f"longest ours {det['longest_exposed_mm_ours']}mm, tol {det['drag_tolerance_mm']}mm)"
          f" -> drag {det['drag_score']}")
    print(f"             trims pro {det['trims_pro']} vs ours {det['trims_ours']} "
          f"-> economy {det['trim_economy']}"
          + ("" if det["trim_economy_scored"] else "  (INFERRED counts, not scored)"))


if __name__ == "__main__":
    args = sys.argv[1:]
    explain = "--explain" in args
    as_json = "--json" in args
    dirs = [a for a in args if not a.startswith("--")]
    rows = []
    for dd in dirs:
        name = Path(dd).name
        if not (Path(dd) / "pro_stitches.csv").exists():
            continue
        try:
            s = score_design(dd, explain=explain)
            rows.append((name, s))
            p = s["parts"]
            print(f"{name:22s} {s['score']:5.1f}  cov={p['coverage']:.2f} dir={p['direction']:.2f} "
                  f"typ={p['sttype']:.2f} den={p['density']:.2f} und={p['underlay']:.2f} "
                  f"trv={p['travel']:.2f}  (old scale {s['score_raw']:5.1f})", flush=True)
            if explain:
                print_explain(name, s)
        except Exception as e:
            import traceback
            print(f"{name:22s} ERROR {type(e).__name__}: {e}")
            if explain:
                traceback.print_exc()
    if rows:
        avg = sum(r[1]["score"] for r in rows) / len(rows)
        avg_raw = sum(r[1]["score_raw"] for r in rows) / len(rows)
        print(f"\ncorpus mean: {avg:.1f} / 100 (target 95)"
              f"   [old uncorrected scale: {avg_raw:.1f}]")
        if as_json:
            print(json.dumps({n: s for n, s in rows}, indent=1))
