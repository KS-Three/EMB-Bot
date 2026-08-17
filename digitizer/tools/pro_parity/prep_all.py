"""Corpus prep: for every professional design, produce the comparable artifacts.

Per design under OUT/<slug>/:
  pro_blocks.json, pro_stitches.csv, pro_render.png
  art.png                (source art reconstructed from pro stitch coverage)
  art_meta.json          (scale, palette, per-block measurements — the sidecar
                          that says which parts of the art are a STITCH
                          treatment rather than something artwork can express)
  ours_blocks.json, ours_stitches.csv, ours_regions.json, ours_render.png,
  ours.dst               (our own machine file — decoded back through the
                          SAME `decode()` the pro side uses, so `runs` /
                          `trims` / `jumps` mean one thing on both sides; see
                          `decode_plan`)
  side_by_side.png
  meta.json              (size, counts, warnings, timing)

Reconstruction rules (2026-08-14 rebuild — every one of these replaced a rule
that was measurably destroying the art the engine then got graded on):

  * COVERAGE IS PER RUN, NOT PER BLOCK. A colour block is cut into runs at
    every JUMP / TRIM / STOP / COLOR_CHANGE the machine file actually records,
    and at any implied hop >= TRAVEL_MM. The old code only cut on distance, so
    every sub-7.5 mm letter-to-letter hop got inked as artwork (proseal_beanie's
    tagline reconstructed as 2 blobs made almost entirely of walks).

  * TRAVEL WALKS INSIDE A RUN ARE FOUND AND DROPPED. A short chain of stitches
    that runs through empty space (local thread density far below what a satin
    or a fill puts down) and lands back on covered ground is a connector, not
    art. A LONG thin chain, or one with no covered ground on either side, is
    run-stitch linework and is kept — that is the distinction the old blanket
    MORPH_OPEN could not make.

  * THE CLOSE RADIUS IS MEASURED, NOT GUESSED FROM STITCH LENGTH. For each
    block we shoot rays perpendicular to every stitch and record the distance
    to the next row of the same structure; the close is sized to bridge that
    measured spacing and nothing wider. The old `len_p50 >= 2.8 -> 3.8 mm
    close` rule selected exactly wrong (long satin stitches got the huge
    close) and fused whole words into single blobs.

  * NO MORPH_OPEN. It erased single-pass run-stitch linework outright. Specks
    are removed by area instead, which cannot delete a line.

  * THE ART IS RGBA. Background is transparent, not white — stage 1 reads the
    alpha channel as ground truth, so a white/near-white thread (PES encodes
    white as 240,240,240) is finally distinguishable from "no artwork here".
    Under the transparency the RGB carries a nearest-colour flood so denoise
    and edge statistics see no manufactured contrast.
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
import pystitch
import shapely.wkt
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.stage0_classify import CLASSES
from digitizer_core.export import write_dst

# The corpus lives outside the repo (it is customer work — see BACKUPS.md), so
# the path is per-machine. It used to be hard-coded to the cloud sandbox that
# first ran this, which meant every local invocation resolved nothing and the
# `PRO_PARITY_ROOT` the docs tell you to set was read by prep_both.py only.
ROOT = Path(os.environ.get(
    "PRO_PARITY_ROOT",
    "/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/embfiles/Embroidery Files"))
OUT = Path(os.environ.get(
    "PRO_PARITY_OUT",
    "/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/corpus",
))

# The customer designs: (slug, primary stitch file). PES preferred (colors);
# DST where that's all there is.
DESIGNS = [
    ("becker_chest_small", "Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES"),
    ("becker_hat_small",   "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES"),
    ("becker_hat_large",   "Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES"),
    ("becker_lc_large",    "Becker Marine/Becker Hat & Polo Large/beckers logolc.PES"),
    ("becker_beanie",      "To a T:Becker Beanies/beckers logo hat 2 A a.PES"),
    ("tires_hat_3d",       "TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.PES"),
    ("mfab_hat",           "MFAB/Mfab Hat & Polo/mf4b logo hat.PES"),
    ("mfab_lc",            "MFAB/Mfab Hat & Polo/mf4b logo lc.PES"),
    ("machine_beanie",     "To a T Machine/Machine beanie E-1 (1).PES"),
    ("machine_hat",        "To a T Machine/Machine HAT.DST"),
    ("machine_lc",         "To a T Machine/Machine LC.DST"),
    ("toat_beanie",        "To a T:Becker Beanies/Machine beanie.PES"),
    ("golf_hat",           " Golden Tee/GOLF HAT.PES"),
    ("hotel_fremont_hat",  "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES"),
    ("hotel_fremont_patch","Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES"),
    ("precision_drone",    "Precision Drone/PRECISION DRON HAT 2.PES"),
    ("gaulke_roofing_hat", "Gaulke Roofing/c golke logo hat.DST"),
    ("gaulke_roofing_lc",  "Gaulke Roofing/c golke logo LC.DST"),
    ("gaulke_plowing_hat", " C Gaulke Plowing/C GOLKE hat.DST"),
    ("gaulke_plowing_lc",  " C Gaulke Plowing/C GOLKE LC.DST"),
    ("gaulke_jb",          " C Gaulke Plowing/GOLKE LOGO JB 1.DST"),
    ("proseal_hat",        "Proseal/PROSEALHAT.DST"),
    ("proseal_beanie",     "Proseal/PROSEALHAT BEANI.DST"),
]

TRAVEL_MM = 7.5          # implied hop at/above this is never thread on cloth
SCALE = 10               # art raster resolution, px per mm
THREAD_W_MM = 0.4        # painted stroke width
GREYS = [(20, 20, 20), (135, 135, 135), (200, 60, 60), (60, 60, 200), (60, 160, 60), (200, 160, 40)]

# --- travel detection ------------------------------------------------------
# Radius of the disc local thread density is measured over. 1.05 mm: wide
# enough that a satin's neighbouring rows fall inside it, tight enough that a
# lone connector stitch stays lonely.
DENS_R_MM = 1.05
# mm of thread per mm^2 below which a stitch is "unsupported" — running
# through space nothing else covers. A satin/tatami at 0.4 mm rows measures
# ~2.5; one isolated pass measures ~0.5. 1.20 sits in the empty middle.
DENS_SUPPORT = 1.20
# A chain of unsupported stitches this long or longer is linework, not a
# connector, however it is anchored.
TRAVEL_CHAIN_MAX_MM = 12.0
TRAVEL_CHAIN_MAX_N = 8

# --- row-spacing measurement ----------------------------------------------
RAY_MAX_MM = 3.0         # how far perpendicular to a stitch we look for its neighbour row
ROW_HIT_MIN = 0.35       # below this share of stitches finding a neighbour there is no row structure
CLOSE_FACTOR = 1.30      # close kernel vs. measured spacing
CLOSE_MIN_MM = 0.30
CLOSE_CAP_MM = 2.60
SPECK_MM2 = 0.60         # painted islands smaller than this are noise, not art


def find_file(rel):
    p = ROOT / rel
    if p.exists():
        return p
    # forgiving lookup: match by basename anywhere under ROOT
    base = Path(rel).name.lower()
    for q in ROOT.rglob("*"):
        if q.name.lower() == base and not q.name.startswith("._"):
            return q
    return None


def decode(path):
    """-> (blocks, breaks, threads, bounds, jumps, trims)

    `blocks[i]` is a LIST OF RUNS; a run is a list of (x_mm, y_mm) the needle
    walked through with the thread down and continuous. Runs break wherever
    the machine file records a JUMP / TRIM / STOP / COLOR_CHANGE, and wherever
    two consecutive stitches imply a hop of TRAVEL_MM or more. Both kinds of
    break are places where NO thread was laid as coverage, so nothing between
    them may ever be painted as artwork.

    `breaks[i][j]` says what opened run j: "start" | "trim" | "color" | "jump"
    | "hop". That is the machine's own account of where thread stops, and it
    is written into the stitch CSVs so a scorer never has to guess it.
    """
    pat = pystitch.read(str(path))
    blocks, cur_runs, run = [], [], []
    cur_breaks, breaks = [], []
    jumps = trims = 0
    last = None
    pend_trim = pend_color = pend_jump = False
    started = False

    def end_run():
        nonlocal run
        if len(run) >= 1:
            cur_runs.append(run)
        run = []

    def end_block():
        nonlocal cur_runs, cur_breaks
        end_run()
        if cur_runs:
            blocks.append(cur_runs)
            breaks.append(cur_breaks)
        cur_runs, cur_breaks = [], []

    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            p = (x / 10.0, y / 10.0)
            broken = pend_trim or pend_color or pend_jump
            if broken or last is None or math.dist(last, p) >= TRAVEL_MM:
                end_run()
                # Priority mirrors what actually happened to the thread: a cut
                # beats a float beats a bare hop. A leading JUMP is the machine
                # moving to where sewing starts, so it never marks the first
                # stitch — but a leading TRIM still does, because that is what
                # the file says and the scorer's own re-decode agrees.
                kind = ("color" if pend_color else
                        "trim" if pend_trim else
                        "start" if not started else
                        "jump" if pend_jump else "hop")
                cur_breaks.append(kind)
            run.append(p)
            last = p
            started = True
            pend_trim = pend_color = pend_jump = False
            continue
        if c == pystitch.JUMP:
            jumps += 1
            pend_jump = True
            last = (x / 10.0, y / 10.0)
        elif c == pystitch.TRIM:
            trims += 1
            pend_trim = True
            last = None
        elif c in (pystitch.COLOR_CHANGE, pystitch.STOP):
            end_block()
            pend_color = True
            pend_trim = pend_jump = False
            last = None
        elif c == pystitch.END:
            break
        else:
            pend_jump = True           # SEQUIN/NEEDLE_SET/... — not cover stitching
    end_block()

    threads = [(t.get_red(), t.get_green(), t.get_blue()) for t in pat.threadlist]
    if not threads or all(t == (0, 0, 0) for t in threads):
        threads = [GREYS[i % len(GREYS)] for i in range(len(blocks))]
    x0, y0, x1, y1 = pat.bounds()
    return blocks, breaks, threads, (x0 / 10, y0 / 10, x1 / 10, y1 / 10), jumps, trims


def decode_plan(plan, dst_path):
    """`decode()` applied to OUR OWN output, so ours and pro are counted in
    the same unit. -> the same 6-tuple `decode` returns.

    A `StitchPlan` run is a PLAN OBJECT — one per fill, satin, underlay or
    travel segment. A decoded run is a THREAD PATH. Travel is thread-down, so
    the machine sews straight through it and one path swallows however many
    plan objects it was assembled from. The two counts are not the same
    measurement and were never comparable:

        becker_hat_small   pro 13 runs   ours 290 plan objects   ours 35 paths
        becker_beanie      pro 14 runs   ours 241 plan objects   ours 37 paths

    Writing the file and reading it back, rather than counting the plan, is
    deliberate: it shares `decode`'s run-splitting rule by construction
    instead of keeping a second copy of it in step, and `ours.dst` is a
    useful artifact in its own right — until now the harness rendered our
    stitches but never emitted a machine file anyone could open.
    """
    return decode(write_dst(plan, dst_path))


def flat(runs):
    return [p for r in runs for p in r]


def segments(runs):
    """-> (A, B, D) float arrays of every stitch segment inside the runs."""
    a, b = [], []
    for r in runs:
        for k in range(len(r) - 1):
            a.append(r[k]); b.append(r[k + 1])
    if not a:
        z = np.zeros((0, 2), np.float64)
        return z, z, np.zeros((0,), np.float64)
    A = np.asarray(a, np.float64); B = np.asarray(b, np.float64)
    return A, B, np.hypot(*(B - A).T)


class Canvas:
    """Shared mm -> px mapping for one design."""

    def __init__(self, bounds, scale=SCALE, pad_mm=6.0):
        self.scale = scale
        self.pad = int(round(pad_mm * scale))
        self.x0, self.y0, self.x1, self.y1 = bounds
        self.W = int(round((self.x1 - self.x0) * scale)) + 2 * self.pad
        self.H = int(round((self.y1 - self.y0) * scale)) + 2 * self.pad

    def px(self, pts):
        p = np.asarray(pts, np.float64)
        i = ((p[:, 0] - self.x0) * self.scale + self.pad).astype(np.int32)
        j = ((p[:, 1] - self.y0) * self.scale + self.pad).astype(np.int32)
        return np.clip(i, 0, self.W - 1), np.clip(j, 0, self.H - 1)


def thread_density(A, B, D, cvs):
    """mm of thread per mm^2, measured over a DENS_R_MM disc, as a raster.

    Every segment is sampled at ~1 px and each sample deposits the mm of
    thread it stands for; a box filter then integrates the neighbourhood.
    """
    acc = np.zeros((cvs.H, cvs.W), np.float32)
    if len(D):
        n = np.maximum(1, np.ceil(D * cvs.scale).astype(np.int64))
        total = int(n.sum())
        seg = np.repeat(np.arange(len(D)), n)
        start = np.repeat(np.cumsum(n) - n, n)
        t = ((np.arange(total) - start) + 0.5) / n[seg]
        P = A[seg] + (B[seg] - A[seg]) * t[:, None]
        i, j = cvs.px(P)
        acc = np.bincount((j.astype(np.int64) * cvs.W + i),
                          weights=D[seg] / n[seg],
                          minlength=cvs.H * cvs.W).reshape(cvs.H, cvs.W).astype(np.float32)
    k = int(round(DENS_R_MM * 2 * cvs.scale)) | 1
    box = cv2.boxFilter(acc, -1, (k, k), normalize=False)
    return box / ((k / cvs.scale) ** 2)


def row_spacing(A, B, D, mask, cvs):
    """Measured centre-to-centre spacing to the NEIGHBOURING ROW, in mm.

    From each stitch's midpoint we walk both ways along the stitch's normal
    and record where painted thread reappears. That distance IS the fill/satin
    row spacing where a row structure exists, and nothing at all where the
    stitch is a lone line — which is exactly the difference the close radius
    has to respect. -> (spacing_mm | None, hit_fraction)
    """
    if len(D) == 0:
        return None, 0.0
    keep = D > 1e-6
    A, B, D = A[keep], B[keep], D[keep]
    if len(D) == 0:
        return None, 0.0
    mid = (A + B) / 2.0
    nx = -(B[:, 1] - A[:, 1]) / D
    ny = (B[:, 0] - A[:, 0]) / D
    skip = int(round(THREAD_W_MM * cvs.scale * 0.5)) + 2      # step off our own stroke
    steps = np.arange(skip, int(RAY_MAX_MM * cvs.scale) + 1)
    best = np.full(len(D), np.inf)
    for sgn in (1.0, -1.0):
        hit = np.zeros(len(D), bool)
        dist = np.full(len(D), np.inf)
        for s in steps:
            todo = ~hit
            if not todo.any():
                break
            px = mid[todo, 0] + sgn * nx[todo] * (s / cvs.scale)
            py = mid[todo, 1] + sgn * ny[todo] * (s / cvs.scale)
            i, j = cvs.px(np.column_stack([px, py]))
            on = mask[j, i]
            idx = np.nonzero(todo)[0][on]
            dist[idx] = s / cvs.scale
            hit[idx] = True
        best = np.minimum(best, dist)
    got = np.isfinite(best)
    frac = float(got.mean())
    if frac < ROW_HIT_MIN:
        return None, frac
    return float(np.percentile(best[got], 75)), frac


def travel_flags(runs, dens, cvs):
    """Per-segment: True where the stitch is a connector walk, not coverage.

    Unsupported stitches (local density under DENS_SUPPORT) are grouped into
    maximal consecutive chains. A chain is a TRAVEL walk when it is short —
    at most TRAVEL_CHAIN_MAX_N stitches and TRAVEL_CHAIN_MAX_MM of thread —
    and touches supported stitching on at least one side (it left, or arrived
    at, real coverage). Anything longer, or free-floating, is linework.
    """
    out = []
    for r in runs:
        n = len(r) - 1
        if n <= 0:
            out.append(np.zeros(max(n, 0), bool))
            continue
        A = np.asarray(r[:-1], np.float64); B = np.asarray(r[1:], np.float64)
        D = np.hypot(*(B - A).T)
        i, j = cvs.px((A + B) / 2.0)
        sup = dens[j, i] >= DENS_SUPPORT
        flag = np.zeros(n, bool)
        k = 0
        while k < n:
            if sup[k]:
                k += 1
                continue
            e = k
            while e < n and not sup[e]:
                e += 1
            span = D[k:e]
            anchored = (k > 0) or (e < n)          # supported stitching adjoins
            if anchored and (e - k) <= TRAVEL_CHAIN_MAX_N and span.sum() <= TRAVEL_CHAIN_MAX_MM:
                flag[k:e] = True
            k = e
        out.append(flag)
    return out


def paint(runs, flags, cvs, width_px=None):
    m = np.zeros((cvs.H, cvs.W), np.uint8)
    w = width_px or max(1, int(round(THREAD_W_MM * cvs.scale)))
    for r, f in zip(runs, flags):
        for k in range(len(r) - 1):
            if f[k]:
                continue
            a, b = r[k], r[k + 1]
            ia, ja = cvs.px([a]); ib, jb = cvs.px([b])
            cv2.line(m, (int(ia[0]), int(ja[0])), (int(ib[0]), int(jb[0])), 255, w)
    return m


def despeckle(mask, cvs, min_mm2=SPECK_MM2):
    """Drop islands under min_mm2. Unlike MORPH_OPEN this cannot thin or
    sever a one-stitch-wide line, which is what run-stitch linework is."""
    px = min_mm2 * cvs.scale * cvs.scale
    n, lab, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    small = np.array([False] + [st[i, cv2.CC_STAT_AREA] < px for i in range(1, n)])
    out = mask.copy()
    out[small[lab]] = 0
    return out


def dominant_angle(A, B, D):
    if not len(D):
        return None
    keep = D > 1e-6
    if not keep.any():
        return None
    ang = np.arctan2(B[keep, 1] - A[keep, 1], B[keep, 0] - A[keep, 0])
    vx = float((np.cos(2 * ang) * D[keep]).sum()); vy = float((np.sin(2 * ang) * D[keep]).sum())
    return round(math.degrees(math.atan2(vy, vx) / 2) % 180.0, 1)


def analyse_block(runs, cvs):
    """Everything measured about one colour block, plus its coverage mask."""
    A, B, D = segments(runs)
    dens = thread_density(A, B, D, cvs)
    flags = travel_flags(runs, dens, cvs)
    trav_n = int(sum(int(f.sum()) for f in flags))
    trav_mm = 0.0
    kept = []
    for r, f in zip(runs, flags):
        for k in range(len(r) - 1):
            d = math.dist(r[k], r[k + 1])
            if f[k]:
                trav_mm += d
            else:
                kept.append((r[k], r[k + 1], d))
    raw = paint(runs, flags, cvs)
    kA = np.asarray([k[0] for k in kept], np.float64) if kept else np.zeros((0, 2))
    kB = np.asarray([k[1] for k in kept], np.float64) if kept else np.zeros((0, 2))
    kD = np.asarray([k[2] for k in kept], np.float64) if kept else np.zeros((0,))
    spacing, hitfrac = row_spacing(kA, kB, kD, raw > 0, cvs)
    if spacing is None:
        close_mm = CLOSE_MIN_MM
    else:
        close_mm = min(CLOSE_CAP_MM, max(CLOSE_MIN_MM, CLOSE_FACTOR * spacing))
    kk = int(round(close_mm * cvs.scale)) | 1
    mask = raw
    if kk > 1:
        se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, se)
    mask = despeckle(mask, cvs)
    meas = {
        "runs": len(runs),
        "stitches": sum(len(r) for r in runs),
        "thread_mm": round(float(kD.sum()), 1),
        "travel_segments": trav_n,
        "travel_mm": round(trav_mm, 1),
        "row_spacing_mm": None if spacing is None else round(spacing, 2),
        "row_hit_frac": round(hitfrac, 2),
        "close_mm": round(close_mm, 2),
        # A structure whose measured rows sit further apart than a cover
        # stitch does is an OPEN treatment (lattice / low-density fill). The
        # artwork under it is solid, so it still closes — but anything scoring
        # stitch DIRECTION over this area is scoring a choice the artwork
        # never carried, and this flag is how a scorer can know that.
        "open_fill": bool(spacing is not None and spacing > 0.60 and hitfrac >= 0.5),
        "angle_deg": dominant_angle(kA, kB, kD),
        "raw_area_mm2": round(float((raw > 0).sum()) / (cvs.scale ** 2), 1),
        "area_mm2": round(float((mask > 0).sum()) / (cvs.scale ** 2), 1),
    }
    return mask, meas, flags


def block_summary(blocks, threads, meas):
    out = []
    for i, runs in enumerate(blocks):
        pts = flat(runs)
        # Per run, so a cross-run hop never enters the length distribution —
        # the old version measured hops as if they were stitches, which is
        # what pushed len_p50 over the 2.8 mm cliff the close radius used to
        # branch on.
        lens = sorted(math.dist(r[k], r[k + 1]) for r in runs for k in range(len(r) - 1))
        n = len(lens)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        row = {
            "block": i,
            "rgb": list(threads[i % len(threads)]),
            "stitches": len(pts),
            "bbox_mm": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)] if pts else [0, 0, 0, 0],
            "len_p10": round(lens[n // 10], 2) if n else 0,
            "len_p50": round(lens[n // 2], 2) if n else 0,
            "len_p90": round(lens[9 * n // 10], 2) if n else 0,
        }
        row.update(meas[i])
        out.append(row)
    return out


def render(blocks, threads, flags_per_block, path, bounds, scale=10):
    """Stitch-view render of a decoded design (runs already exclude travel)."""
    x0, y0, x1, y1 = bounds
    W = int((x1 - x0) * scale) + 40
    H = int((y1 - y0) * scale) + 40
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    for i, runs in enumerate(blocks):
        rgb = tuple(threads[i % len(threads)])
        fl = flags_per_block[i] if flags_per_block else [None] * len(runs)
        for r, f in zip(runs, fl):
            for k in range(len(r) - 1):
                if f is not None and f[k]:
                    continue
                a = ((r[k][0] - x0) * scale + 20, (r[k][1] - y0) * scale + 20)
                b = ((r[k + 1][0] - x0) * scale + 20, (r[k + 1][1] - y0) * scale + 20)
                d.line([a, b], fill=rgb, width=2)
    im.save(path)
    return im


def nearest_colour_flood(bgr, opaque):
    """Fill the transparent RGB with the nearest painted colour.

    The alpha channel is what stage 1 reads, but the RGB under it is not
    inert: denoise runs over it and stage 2 samples the artwork's outer edge
    colour from it. A flat canvas colour there manufactures contrast at every
    boundary (and, on a white canvas, made white thread invisible). The
    nearest-colour flood makes every boundary a no-op instead.
    """
    if opaque.all() or not opaque.any():
        return bgr
    _, lab = cv2.distanceTransformWithLabels(
        (~opaque).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL
    )
    ys, xs = np.nonzero(opaque)
    order = lab[opaque]                       # label ids are 1..N over the zero pixels
    lut = np.zeros((int(lab.max()) + 1, 3), np.uint8)
    lut[order] = bgr[ys, xs]
    out = bgr.copy()
    out[~opaque] = lut[lab[~opaque]]
    return out


def reconstruct(blocks, threads, cvs, path, meta_path):
    """Paint each block's MEASURED coverage in its thread colour, in sew order.

    Later blocks cover earlier ones because that is what the finished garment
    looks like — but only over the area they actually cover, which is the
    whole point of measuring the close radius instead of guessing it.
    """
    bgr = np.zeros((cvs.H, cvs.W, 3), np.uint8)
    alpha = np.zeros((cvs.H, cvs.W), np.uint8)
    masks, meas, flags = [], [], []
    for runs in blocks:
        m, mm, fl = analyse_block(runs, cvs)
        masks.append(m); meas.append(mm); flags.append(fl)
    for i, m in enumerate(masks):
        rgb = threads[i % len(threads)]
        sel = m > 0
        bgr[sel] = (rgb[2], rgb[1], rgb[0])
        alpha[sel] = 255
    opaque = alpha > 0
    for i, m in enumerate(masks):
        vis = (m > 0).copy()
        for j in range(i + 1, len(masks)):
            vis &= ~(masks[j] > 0)
        meas[i]["visible_mm2"] = round(float(vis.sum()) / (cvs.scale ** 2), 1)
    bgr = nearest_colour_flood(bgr, opaque)
    cv2.imwrite(str(path), np.dstack([bgr, alpha]))
    meta = {
        "scale_px_per_mm": cvs.scale,
        "pad_px": cvs.pad,
        "origin_mm": [round(cvs.x0, 2), round(cvs.y0, 2)],
        "size_px": [cvs.W, cvs.H],
        "palette": [{"block": i, "rgb": list(threads[i % len(threads)])} for i in range(len(blocks))],
        "blocks": [dict(block=i, **meas[i]) for i in range(len(blocks))],
        "art_area_mm2": round(float(opaque.sum()) / (cvs.scale ** 2), 1),
        "open_fill_mm2": round(sum(meas[i]["visible_mm2"] for i in range(len(blocks))
                                   if meas[i]["open_fill"]), 1),
    }
    Path(meta_path).write_text(json.dumps(meta, indent=1))
    return meas, flags


def run_ours(art_path, width_mm, outdir, garment_id=None):
    """`garment_id=None` (the default, and what every run before 2026-08-15
    used) leaves `fabrics.py` on `DEFAULT_FABRIC_ID = "pique_knit"` — a polo
    left chest — for every design including cap fronts and beanies. Passing the
    real garment picks up that garment's pull compensation and underlay style.
    Kept optional so existing callers reproduce their recorded numbers exactly;
    see docs/pro-parity-real-art-2026-08-15.md §5b.
    """
    cfg = PipelineConfig()
    cfg.garment_id = garment_id
    # Stage 0's flat/gradient gate misroutes 10 of the 15 real-artwork designs
    # into the photo lane, where their regions never reach the satin/fill
    # ladder at all (docs/classifier-misroutes-real-logos-2026-08-15.md). That
    # blocks any measurement OF that ladder, and its own fix is blocked on
    # artwork, so this lets a probe pin the class instead of waiting.
    # Unset — the default — is exactly the behaviour every run before
    # 2026-08-16 had.
    forced = os.environ.get("PRO_PARITY_FORCED_CLASS")
    if forced:
        # Checked against the canonical list rather than passed through. An
        # unrecognized value matches no downstream branch and takes the flat
        # path silently, so a typo like `photo` for `photo_subject` would
        # produce a complete, plausible-looking corpus run measured through the
        # WRONG lane — and these numbers get quoted as project status.
        # `classify` raises too; this exists so the operator reads the valid
        # list instead of a traceback, before any design is processed.
        if forced not in CLASSES:
            sys.exit(f"PRO_PARITY_FORCED_CLASS={forced!r} is not a class. "
                     f"Valid: {', '.join(CLASSES)}")
        cfg.forced_class = forced
    # Task A2 (2026-08-14): fill_density_boost is SEW-OUT GATED off by
    # default (see PipelineConfig's own comment) — this harness exists
    # specifically to measure a candidate engine change against the corpus
    # before it ships, so it opts in explicitly rather than measuring the
    # shipped single-pass default.
    #
    # PipelineConfig is a plain dataclass, so a bare `cfg.fill_density_boost =
    # True` on a tree where that field does not exist sets a stray attribute
    # nothing reads and raises nothing — the harness would go on silently
    # measuring a different configuration than its own comment claims. That is
    # exactly what happened when `a6435f2` reverted PR #146 and removed the
    # field (2026-08-15). Check instead of assuming, and say so out loud.
    if "fill_density_boost" in PipelineConfig.__dataclass_fields__:
        cfg.fill_density_boost = True
    else:
        print("  WARNING: PipelineConfig has no `fill_density_boost` field on "
              "this tree — measuring the shipped default, NOT the boosted fill "
              "every pro-parity number before 2026-08-15 was measured with.",
              flush=True)
    cfg.target_width_mm = round(width_mm, 1)
    res = run_stages(str(art_path), cfg)
    plan = plan_stitches(res, cfg)
    # trim/jump are the engine's OWN run flags (stitches.iter_machine_commands
    # is the authority on what the exported file will contain), so the scorer
    # never has to infer where our thread was cut. `trim` matches the pro-side
    # column exactly: 1 = the move arriving at this stitch laid no thread
    # because the machine had cut (or stopped for a colour change).
    with open(outdir / "ours_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        started = False
        for i, b in enumerate(plan.blocks):
            for ri, r in enumerate(b.runs):
                if not r.points:
                    continue
                trim = 1 if (getattr(r, "trim", False) or (ri == 0 and i > 0)) else 0
                jump = 1 if (getattr(r, "jump", False) and started and not trim) else 0
                for k, (x, y) in enumerate(r.points):
                    t = trim if k == 0 else 0
                    j = jump if k == 0 else 0
                    f.write(f"{i},{ri},{t},{j},{x:.2f},{y:.2f}\n")
                started = True
    # Ours in the pro's unit. `plan_runs` is the old `runs` field, renamed
    # because it never meant what the pro side's `runs` meant — see
    # `decode_plan`. Anything comparing the two files must read `runs`.
    mblocks, mbreaks, _mthreads, _mbounds, mjumps, mtrims = decode_plan(
        plan, outdir / "ours.dst")
    ours_meta = {
        "runs": sum(len(r) for r in mblocks),
        "plan_runs": sum(len(b.runs) for b in plan.blocks),
        "jumps": mjumps, "trims": mtrims,
        "run_breaks": {k: sum(kk.count(k) for kk in mbreaks)
                       for k in ("start", "color", "trim", "jump", "hop")},
    }
    # Written rather than returned so `run_ours`'s signature does not move
    # under the other callers. `machine_meta(outdir)` is the reader.
    (outdir / "ours_meta.json").write_text(json.dumps(ours_meta, indent=1))
    summary = []
    ours_blocks = []
    for i, b in enumerate(plan.blocks):
        runs = [list(r.points) for r in b.runs]
        pts = [p for r in runs for p in r]
        ours_blocks.append(runs)
        lens = sorted(math.dist(r[k], r[k + 1]) for r in runs for k in range(len(r) - 1))
        n = len(lens)
        summary.append({
            "block": i, "rgb": list(b.rgb), "stitches": len(pts),
            "runs": len(mblocks[i]) if i < len(mblocks) else 0,
            "plan_runs": len(b.runs),
            "plan_runs_by_kind": {k: sum(1 for r in b.runs if r.kind == k)
                                  for k in sorted({r.kind for r in b.runs})},
            "len_p10": round(lens[n // 10], 2) if n else 0,
            "len_p50": round(lens[n // 2], 2) if n else 0,
            "len_p90": round(lens[9 * n // 10], 2) if n else 0,
        })
    (outdir / "ours_blocks.json").write_text(json.dumps(summary, indent=1))
    # `wkt` is the ARTWORK polygon stage 7 classifies satin-vs-fill on — the
    # same object `is_satin_candidate` is handed — so a probe can re-ask the
    # classifier's question about a prepped design without re-running stages
    # 0-4 and risking a different config than the one that produced these
    # stitches. Rounded to 3 dp: sub-micron precision on a polygon measured in
    # millimetres is noise, and the full float repr triples the file size.
    regions = [{"shape_id": r.shape_id, "area_mm2": round(r.area_mm2, 1),
                "thread": r.thread_number, "tier": r.meta.get("tier"),
                "bounds": [round(v, 1) for v in r.polygon.bounds],
                "wkt": shapely.wkt.dumps(r.polygon, rounding_precision=3)}
               for r in res.regions]
    (outdir / "ours_regions.json").write_text(json.dumps(regions, indent=1))
    return res, plan, ours_blocks, [tuple(b.rgb) for b in plan.blocks]


def machine_meta(outdir):
    """Our `runs` / `trims` / `jumps` / `run_breaks` for a prepped design, in
    the same unit `entry["pro"]` reports them in. `{}` on an output directory
    prepped before this existed, so an old corpus still loads."""
    p = Path(outdir) / "ours_meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


def main():
    manifest = []
    targets = DESIGNS
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:                                   # optional: prep just the named slugs
        want = set(args)
        targets = [d for d in DESIGNS if d[0] in want]

    for slug, rel in targets:
        t0 = time.time()
        outdir = OUT / slug
        outdir.mkdir(parents=True, exist_ok=True)
        entry = {"slug": slug, "source": rel}
        try:
            path = find_file(rel)
            if path is None:
                raise FileNotFoundError(rel)
            entry["file"] = str(path)
            blocks, breaks, threads, bounds, jumps, trims = decode(path)
            assert all(len(b) == len(k) for b, k in zip(blocks, breaks))
            cvs = Canvas(bounds)
            meas, flags = reconstruct(blocks, threads, cvs, outdir / "art.png",
                                      outdir / "art_meta.json")
            entry["pro"] = {
                "stitches": sum(len(p) for runs in blocks for p in runs),
                "blocks": len(blocks),
                "runs": sum(len(runs) for runs in blocks),
                "jumps": jumps, "trims": trims,
                "run_breaks": {k: sum(kk.count(k) for kk in breaks)
                               for k in ("start", "color", "trim", "jump", "hop")},
                "travel_segments": sum(m["travel_segments"] for m in meas),
                "travel_mm": round(sum(m["travel_mm"] for m in meas), 1),
                "width_mm": round(bounds[2] - bounds[0], 1),
                "height_mm": round(bounds[3] - bounds[1], 1),
            }
            (outdir / "pro_blocks.json").write_text(
                json.dumps(block_summary(blocks, threads, meas), indent=1))
            # Row k is still the k'th STITCH of the pattern, in order — the
            # property every consumer relies on. `trim` is now written from
            # the machine file itself instead of being re-derived downstream:
            # 1 exactly when a TRIM / COLOR_CHANGE / STOP stands between this
            # stitch and the one before it. `jump` marks a needle-up float
            # (thread spans the gap but lays no coverage), which is why
            # neither kind is ever painted into art.png.
            with open(outdir / "pro_stitches.csv", "w") as f:
                f.write("block,run,trim,jump,x_mm,y_mm\n")
                for i, runs in enumerate(blocks):
                    for ri, (r, kind) in enumerate(zip(runs, breaks[i])):
                        t = 1 if kind in ("trim", "color") else 0
                        j = 1 if kind == "jump" else 0
                        for k, (x, y) in enumerate(r):
                            f.write(f"{i},{ri},{t if k == 0 else 0},"
                                    f"{j if k == 0 else 0},{x:.2f},{y:.2f}\n")
            render(blocks, threads, flags, outdir / "pro_render.png", bounds=bounds)
            res, plan, ours_blocks, ours_threads = run_ours(
                outdir / "art.png", bounds[2] - bounds[0], outdir)
            entry["ours"] = {
                "stitches": sum(len(p) for runs in ours_blocks for p in runs),
                "blocks": len(ours_blocks),
                "regions": len(res.regions),
                **machine_meta(outdir),
                "warnings": [w["code"] for w in res.warnings],
            }
            allpts = [p for runs in ours_blocks for r in runs for p in r]
            if allpts:
                ox0 = min(p[0] for p in allpts); oy0 = min(p[1] for p in allpts)
                ox1 = max(p[0] for p in allpts); oy1 = max(p[1] for p in allpts)
                render(ours_blocks, ours_threads, None, outdir / "ours_render.png",
                       bounds=(ox0, oy0, ox1, oy1))
                pro_im = Image.open(outdir / "pro_render.png")
                ours_im = Image.open(outdir / "ours_render.png")
                h = max(pro_im.height, ours_im.height) + 40
                side = Image.new("RGB", (pro_im.width + ours_im.width + 60, h), "white")
                d = ImageDraw.Draw(side)
                d.text((20, 8), f"PRO - {entry['pro']['stitches']} st, {entry['pro']['blocks']} blocks, {entry['pro']['trims']} trims", fill="black")
                d.text((pro_im.width + 40, 8), f"EMB-BOT - {entry['ours']['stitches']} st, {entry['ours']['blocks']} blocks, {entry['ours']['trims']} trims", fill="black")
                side.paste(pro_im, (20, 30)); side.paste(ours_im, (pro_im.width + 40, 30))
                side.save(outdir / "side_by_side.png")
            entry["ok"] = True
        except Exception as e:
            entry["ok"] = False
            entry["error"] = f"{type(e).__name__}: {e}"
            entry["trace"] = traceback.format_exc()[-600:]
        entry["seconds"] = round(time.time() - t0, 1)
        manifest.append(entry)
        print(f"[{slug}] ok={entry['ok']} {entry.get('pro', {}).get('stitches', '-')} pro st "
              f"/ {entry.get('ours', {}).get('stitches', '-')} ours st ({entry['seconds']}s)"
              + ("" if entry["ok"] else f"  ERR {entry['error']}"), flush=True)

    if len(targets) == len(DESIGNS):
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    else:
        p = OUT / "manifest.json"
        old = json.loads(p.read_text()) if p.exists() else []
        by = {e["slug"]: e for e in old}
        by.update({e["slug"]: e for e in manifest})
        p.write_text(json.dumps([by[s] for s, _ in DESIGNS if s in by], indent=1))
    print(f"\n{sum(1 for e in manifest if e['ok'])}/{len(manifest)} designs prepped")


if __name__ == "__main__":
    main()
