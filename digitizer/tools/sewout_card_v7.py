"""Sew-out card v7: the two flags still waiting on fabric (2026-10-25)

    # 1. cut both jobs, four arms each (one stage 0-4 run per job, minutes)
    python -m tools.sewout_card_v7 --cut fremont
    python -m tools.sewout_card_v7 --cut becker
    # 2. build the card (reads the cuts)
    python -m tools.sewout_card_v7 [--out ../docs/sewout/card-v7-2026-10-25]

Kent's ruling 2026-10-22: stitch LAYOUT flips from renders; only what fabric
does to thread (pull, satin density, fill stitch length as density) needs a
sew-out. Two flags on main are that kind and wait on cloth:

- `pull_comp_by_stroke` (#1045): a Column-lane satin column's pull falls with
  its own drawn stroke, the pro's hat rule (+0.58 mm at 0.85, +0.42 at 2.6,
  nothing at 4).
- `pro_measured_values` (#1039): on hat / LC / beanie, fill stitch 3.49 mm
  (3.0), satin spacing 0.37 (0.40; 0.35 beanie), bean stitch 0.95 (0.73).

Arms, in tooth order, each pinning BOTH flags explicitly (the card tools pin
nothing by default, so an unpinned OFF would silently follow a later default
flip -- memory `bean-holds-on-2026-10-15`):

- (a) 1 tooth  both OFF (what ships, once BASE lands)
- (b) 2 teeth  `pull_comp_by_stroke` ON
- (c) 3 teeth  `pro_measured_values` ON
- (d) 4 teeth  both ON

Every arm sits on `BASE`: the flips Kent has ruled (10-23 flip sheet, 10-24
wave 2) whose flags are on main but whose flip PR (#1057, #1070) had not
merged when this card was cut. Without them arm (a) would not be what ships
by the time it is sewn -- card v4 replaced three cards for exactly that.
`tie_in_off` and `border_from_outline` are ruled too but are not flags on
main, so the card cannot carry them.

Three blocks, all on the Hat preset (the two jobs at the width the pro's file has):

- F  Hotel Fremont at 92.5 mm (Kent's patch; hold each row against it):
     the HOTEL FREMONT band (THE, HOTEL FREMONT, the two bars) and the crest
     above it (Wisconsin's fill, EST, 1895).
- M  Becker MARINE at 76.5 mm: wide satin strokes (drawn ~4.2 mm), where
     `pull_comp_by_stroke` acts. Fremont's strokes are ~0.85 mm, where the fit
     returns the preset's own 0.4, so on F's pieces arm (b) is arm (a) byte
     for byte and (d) is (c) (across the whole design the flag moves two
     tagline letters by 0.02 mm): F sews only (a) and (c), the cut proves it.
- P  a fill plate (`plate_png`, 34 mm): rows over 10 mm for the fill stitch
     and a small disc for the bean edge cap, the two values Fremont's crop
     cannot show. No column, so it too sews (a) and (c).
- M  carries the pro's own I and N beside it in the readout (`pro_satin`).

Both flags are read in stage 7 only (`stage7_sequence`, `columns`), so each
job's stages 0-4 (`build_generation`) run once and every arm forks it --
the same plan a fresh digitize per arm gives. Everything else is the
Studio's request (`tools.pro_pair.request`). One dark cone, 40 wt. Through
`digitizer_service.formats.write` (pystitch, the service's /export path),
read back with pystitch. EVERY NUMBER HERE IS A CANDIDATE UNTIL KENT SEWS IT
(gate 1). No default changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core.export import plan_to_pattern  # noqa: E402
from digitizer_core.stitches import StitchPlan, StitchRun  # noqa: E402
from digitizer_service import formats  # noqa: E402
from tools import hairline_card as hc  # noqa: E402
from tools import sewout_candidates_card as v2  # noqa: E402
from tools import sewout_card_v3 as v3  # noqa: E402
from tools import sewout_card_v4 as c4  # noqa: E402

REPO = hc.REPO
WT = v3.WT
NAME = "card_v7_40wt"
DEFAULT_OUT = REPO / "docs" / "sewout" / "card-v7-2026-10-25"
DEFAULT_CUTS = DEFAULT_OUT / "cuts"
WHITE_MIN = v3.WHITE_MIN             # a block this light on every channel is the white ground

FABRIC_FLAGS = ("pull_comp_by_stroke", "pro_measured_values")

#: Kent's ruled flips whose flags are on main, not yet main's defaults when
#: the card was cut: the flip sheet of 2026-10-23 (#1049 -> #1057: "flip the
#: eight ON", the ninth, then three more) and wave 2 of 2026-10-24 (#1070).
BASE = {
    "fill_turn_slant": True,
    "trim_bury_under_later": True,
    "small_solids_satin": True,
    "compact_solids_satin": True,
    "satin_underlay_short_columns": True,
    "fill_underlay_cross": True,
    "small_text_cap_mm": 4.0,
    "small_text_cap_max_width_scale": 1.05,
    "small_text_cap_min_stroke_mm": 0.85,
    "small_text_cap_letter_gap_mm": 0.25,
    "small_text_cap_bold_scale": 1.45,
    "lettering_columns_small_bold": True,
    "border_by_size": True,
    "enclosed_alpha_hole_parts": True,
    "lettering_columns_corner_fold": True,
    "small_text_cap_reach_edges": True,
}

#: arm -> (label, the two fabric flags, both always pinned), in tooth order
ARMS = {
    "a": ("both off", {"pull_comp_by_stroke": False, "pro_measured_values": False}),
    "b": ("pull by stroke", {"pull_comp_by_stroke": True, "pro_measured_values": False}),
    "c": ("pro values", {"pull_comp_by_stroke": False, "pro_measured_values": True}),
    "d": ("both on", {"pull_comp_by_stroke": True, "pro_measured_values": True}),
}
TEETH = {arm: k for k, arm in enumerate(ARMS, start=1)}

JOBS = {
    "fremont": {"art": ROOT / "testdata" / "photo" / "logo_hotel_fremont.webp", "width_mm": 92.5,
                "garment_id": "hat_front"},
    "plate": {"art": None, "width_mm": 34.0, "garment_id": "hat_front"},    # `plate_png`
    "becker": {"art": ROOT / "testdata" / "becker_marine_logo.png", "width_mm": 76.5,
               "garment_id": "hat_front"},
}

#: The fill plate (mm, on a 34 x 9.5 mm canvas), one dark ink on a
#: transparent ground: a field with one rounded corner (rows over the 10 mm
#: the pro's 3.49 fill stitch was read on), a 7.5 mm disc, and a 5.5 mm disc.
#: Under BASE's `border_by_size` the field and the big disc get a satin ring
#: (border density is not one of the flag's numbers: the rings match across
#: arms, memory `pro-measured-values-2026-10-23`); the small disc is over
#: the 5.0 mm satin ceiling and under the ring's 6 mm, so it keeps the bean
#: edge cap whose stitch the flag lengthens -- nothing else on the card has one.
PLATE_MM = (34.0, 9.5)
PLATE_FIELD = (0.5, 0.5, 18.5, 9.0)
PLATE_RADIUS_MM = 2.5
PLATE_DISCS = ((23.0, 4.75, 3.75), (30.5, 4.75, 2.75))     # centre x, y, radius


def plate_png(ppm: int = 20) -> bytes:
    import math

    import cv2
    import numpy as np
    img = np.zeros((int(PLATE_MM[1] * ppm), int(PLATE_MM[0] * ppm), 4), np.uint8)
    x0, y0, x1, y1 = PLATE_FIELD
    r = PLATE_RADIUS_MM
    pts = [(x0, y0), (x1 - r, y0)]
    pts += [(x1 - r + r * math.cos(math.radians(a)), y0 + r + r * math.sin(math.radians(a)))
            for a in np.linspace(-90, 0, 40)]
    pts += [(x1, y1), (x0, y1)]
    ink = (30, 30, 30, 255)
    cv2.fillPoly(img, [np.array([[px * ppm, py * ppm] for px, py in pts], np.int32)], ink, cv2.LINE_AA)
    for cx, cy, rad in PLATE_DISCS:
        cv2.circle(img, (int(cx * ppm), int(cy * ppm)), int(rad * ppm), ink, -1, cv2.LINE_AA)
    return cv2.imencode(".png", img)[1].tobytes()


def overrides(arm: str) -> dict:
    """The arm's whole override set on the Studio request: BASE, then its two flags."""
    return {**BASE, **ARMS[arm][1]}


def _runs_json(plan) -> list[dict]:
    return [{"kind": r.kind, "shape_id": r.shape_id, "rgb": [int(v) for v in b.rgb],
             "points": [[round(q[0], 4), round(q[1], 4)] for q in r.points]}
            for b in plan.blocks for r in b.runs if len(r.points) > 1]


def runs_md5(runs: list[dict]) -> str:
    return hashlib.md5(json.dumps([[r["kind"], r["points"]] for r in runs]).encode()).hexdigest()


def cut(job: str, cuts: Path, cache: Path | None = None) -> Path:
    """Digitize the job once to stage 4, then plan every arm from a fork of
    it; save each arm's selected runs (`select`) as JSON, and with `cache`
    every run of the whole design too."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode as svc_decode, _parse_config
    from tools import pro_pair
    j = JOBS[job]
    data = plate_png() if j["art"] is None else Path(j["art"]).read_bytes()

    def cfg(arm):
        req = pro_pair.request(j["width_mm"], j["garment_id"], overrides(arm))
        c = PipelineConfig(**_parse_config(json.dumps(req)))
        missed = {k: v for k, v in overrides(arm).items() if getattr(c, k) != v}
        if missed:
            raise SystemExit(f"{job}/{arm}: the service parser did not carry {missed}")
        return c
    t = time.time()
    gen = build_generation(svc_decode(data), cfg("a"), exif_source=data)
    print(f"{job}: stages 0-4 {time.time() - t:.0f} s", flush=True)
    art = "plate_png()" if j["art"] is None else Path(j["art"]).relative_to(ROOT).as_posix()
    out = {"job": job, "art": art, "width_mm": j["width_mm"],
           "garment_id": j["garment_id"], "base": BASE, "arms": {}}
    for arm in ARMS:
        t = time.time()
        c = cfg(arm)
        plan = plan_stitches(finish_generation(gen.fork(), c), c)
        runs = _runs_json(plan)
        if cache is not None:
            cache.mkdir(parents=True, exist_ok=True)
            (cache / f"{job}_{arm}.json").write_text(json.dumps(runs), encoding="utf-8")
        keep = select(job, runs)
        out["arms"][arm] = {"overrides": overrides(arm), "stitches_whole": plan.stats.stitch_count,
                            "trims_whole": plan.stats.trims,
                            "size_mm_whole": [round(v, 2) for v in plan.stats.size_mm],
                            "md5_whole": runs_md5(runs), "md5": runs_md5(keep), "runs": keep}
        print(f"{job}/{arm}: {plan.stats.stitch_count:,} st, {plan.stats.trims} trims, "
              f"{len(keep)} runs kept, {time.time() - t:.0f} s", flush=True)
    cuts.mkdir(parents=True, exist_ok=True)
    path = cuts / f"{job}.json"
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


#: job -> windows (x0, y0, x1, y1, thread): fractions of the job's own
#: stitched extent (white ground left out, y down), and "dark" / "light" /
#: None for which thread's shapes it takes (Fremont's rope is the light tan
#: of EST and 1895, and runs past both). A shape is cut when every run of it
#: lies in one window (grown by `WINDOW_PAD_MM`), so no shape is halved.
WINDOWS = {
    "fremont": ((0.0, 0.31, 1.0, 0.675, "dark"),     # THE, HOTEL FREMONT, the bars
                (0.44, 0.10, 0.56, 0.30, "dark"),    # Wisconsin: the job's one fill
                (0.30, 0.22, 0.72, 0.33, "light")),  # EST, 1895
    "plate": ((0.0, 0.0, 1.0, 1.0, None),),          # all of it
    "becker": ((0.56, 0.62, 0.83, 1.0, None),),      # MARINE's I and N (I: one stem to measure)
}
WINDOW_PAD_MM = 0.6


def _bbox(pts) -> tuple[float, float, float, float]:
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def _thread(rgb) -> str:
    return "dark" if max(rgb) < 100 else "light"


def select(job: str, runs: list[dict]) -> list[dict]:
    """The runs of the shapes inside the job's `WINDOWS`, in sewing order."""
    ink = [r for r in runs if min(r["rgb"]) < WHITE_MIN]
    x0, y0, x1, y1 = _bbox([p for r in ink for p in r["points"]])
    wins = [((x0 + a * (x1 - x0) - WINDOW_PAD_MM, y0 + b * (y1 - y0) - WINDOW_PAD_MM,
              x0 + c * (x1 - x0) + WINDOW_PAD_MM, y0 + d * (y1 - y0) + WINDOW_PAD_MM), thread)
            for a, b, c, d, thread in WINDOWS[job]]

    def inside(box, w):
        return box[0] >= w[0] and box[1] >= w[1] and box[2] <= w[2] and box[3] <= w[3]
    # A shared id (`__edge_cap__`: every cap of the design) is judged run by run.
    key = [r["shape_id"] if not r["shape_id"].startswith("__") else f"{r['shape_id']}#{i}"
           for i, r in enumerate(ink)]
    by_shape: dict[str, list] = {}
    colour: dict[str, str] = {}
    for k, r in zip(key, ink):
        colour[k] = _thread(r["rgb"])
        if r["kind"] != "travel":
            by_shape.setdefault(k, []).extend(r["points"])
    keep = {sid: w for sid, pts in by_shape.items() for w, thread in wins
            if inside(_bbox(pts), w) and thread in (None, colour[sid])}
    return [r for k, r in zip(key, ink) if k in keep and inside(_bbox(r["points"]), keep[k])]


def reselect(job: str, cuts: Path, cache: Path) -> Path:
    """Re-cut a job's windows from `--cache` without digitizing again."""
    path = cuts / f"{job}.json"
    out = json.loads(path.read_text(encoding="utf-8"))
    for arm, a in out["arms"].items():
        keep = select(job, json.loads((cache / f"{job}_{arm}.json").read_text(encoding="utf-8")))
        a["runs"], a["md5"] = keep, runs_md5(keep)
    path.write_text(json.dumps(out), encoding="utf-8")
    return path


def load(cuts: Path, job: str) -> dict:
    return json.loads((cuts / f"{job}.json").read_text(encoding="utf-8"))


def piece_runs(cut_: dict, arm: str) -> list[StitchRun]:
    return [StitchRun(points=[tuple(p) for p in r["points"]], kind=r["kind"], jump=True, trim=False,
                      shape_id=r["shape_id"]) for r in cut_["arms"][arm]["runs"]]


def satin_stats(runs) -> dict:
    """The planned satin (not sewn) of the runs: `width_mm`, the median cross
    rail to rail -- a cross is the stitches between two reversals, so a SPLIT
    satin's two half stitches count as one cross (`small_text_columns.crosses`
    reads only single stitches and caps at 4 mm, which truncates MARINE);
    `stitch_mm`, the median needle-to-needle stitch; `split_pct`, the share of
    crosses sewn in more than one stitch; `rail_step_mm`, the median distance
    between consecutive needle holes on one rail -- the satin spacing as the
    engine lays it (0.40 by default, 0.37 under `pro_measured_values`). Never
    read it off a DST: the format's 0.1 mm grid turns 0.37 into 0.4 (the
    settings audit, row 1)."""
    import math
    widths, steps, rail, split = [], [], [], 0
    for r in runs:
        if r.kind != "satin":
            continue
        p = [q for i, q in enumerate(r.points) if i == 0 or math.dist(q, r.points[i - 1]) > 1e-9]
        seg = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:])]
        turns = [p[i] for i in range(1, len(seg)) if seg[i - 1][0] * seg[i][0] + seg[i - 1][1] * seg[i][1] < 0]
        rail += [math.dist(a, b) for a, b in zip(turns, turns[2:]) if math.dist(a, b) < 2.0]
        start, n = 0, len(seg)
        for i in range(1, n + 1):
            if i == n or seg[i - 1][0] * seg[i][0] + seg[i - 1][1] * seg[i][1] < 0:
                if 0 < start and i < n:       # whole crosses only: both ends are reversals
                    leg = seg[start:i]
                    w = math.hypot(sum(s[0] for s in leg), sum(s[1] for s in leg))
                    if 0.3 <= w <= 12.0:
                        widths.append(w)
                        steps += [math.hypot(*s) for s in leg]
                        split += len(leg) > 1
                start = i
    med = lambda v: round(sorted(v)[len(v) // 2], 2) if v else None  # noqa: E731
    return {"width_mm": med(widths), "stitch_mm": med(steps), "rail_step_mm": med(rail),
            "split_pct": round(100.0 * split / len(widths), 1) if widths else None}


def fill_stats(runs) -> dict:
    """The planned fill (not sewn): the fill stitch, read as the 75th
    percentile of fill stitches over 0.5 mm -- a row's interior stitch; its
    ends, turns and short rows sit below it -- and the bean edge cap's median
    stitch (its `run` passes on the cap's shared `__edge_cap__` id)."""
    import math

    def pct(kind, floor, q, sid=None):
        v = sorted(math.dist(a, b) for r in runs if r.kind == kind and (sid is None or r.shape_id.startswith(sid))
                   for a, b in zip(r.points, r.points[1:]) if math.dist(a, b) > floor)
        return round(v[int(q * (len(v) - 1))], 2) if v else None
    return {"fill_stitch_mm": pct("fill", 0.5, 0.75), "cap_stitch_mm": pct("run", 0.05, 0.5, "__edge_cap__")}


#: The pro's own file for the M job (committed reference), read with the same
#: reader through the same window: what (a)-(d) are held against.
PRO_DST = {"becker": ROOT / "testdata" / "reference" / "becker_hat_small_beckers_logo_hat_2_a.dst"}


def pro_satin(job: str) -> dict:
    """`satin_stats` of the pro's stitches in the job's window: each stitch
    sequence between needle-up moves is one run, kept when it lies inside."""
    import pystitch
    pat = pystitch.read_dst(str(PRO_DST[job]))
    mask = pystitch.COMMAND_MASK
    seqs, cur = [], []
    for x, y, cmd in pat.stitches:
        if (cmd & mask) == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
        else:
            seqs.append(cur)
            cur = []
    seqs = [s for s in seqs + [cur] if len(s) > 3]
    x0, y0, x1, y1 = _bbox([q for s in seqs for q in s])
    (a, b, c, d, _thread), = WINDOWS[job]
    w = (x0 + a * (x1 - x0) - WINDOW_PAD_MM, y0 + b * (y1 - y0) - WINDOW_PAD_MM,
         x0 + c * (x1 - x0) + WINDOW_PAD_MM, y0 + d * (y1 - y0) + WINDOW_PAD_MM)
    keep = [StitchRun(points=s, kind="satin") for s in seqs
            if (lambda bx: bx[0] >= w[0] and bx[1] >= w[1] and bx[2] <= w[2] and bx[3] <= w[3])(_bbox(s))]
    return {**satin_stats(keep), "file": PRO_DST[job].name, "stitches": sum(len(r.points) for r in keep)}


#: Each job's sewn arms, in order. On F the pull flag has nothing to act on
#: (strokes ~0.85 mm: the fit returns the preset's 0.4), so (b) and (d) are
#: (a) and (c) byte for byte -- `same_as` reads that off the cut, the test
#: holds it, and F sews only (a) and (c). The plate has no column at all.
SEWN = {"fremont": ("a", "c"), "plate": ("a", "c"), "becker": ("a", "b", "c", "d")}
BLOCK = {"fremont": "F", "plate": "P", "becker": "M"}


def same_as(cut_: dict) -> dict[str, str]:
    """arm -> the earlier arm whose cut runs are byte-identical to it."""
    out = {}
    arms = list(cut_["arms"])
    for i, arm in enumerate(arms):
        for prev in arms[:i]:
            if cut_["arms"][arm]["md5"] == cut_["arms"][prev]["md5"] and prev not in out:
                out[arm] = prev
                break
    return out


class CardV7(v3.CardV3):
    DIGITIZED = tuple(f"{b}:" for b in ("F", "P", "M"))    # every piece keeps the digitizer's cuts


TOP = 2.6               # room above a piece for its teeth
ROW_GAP = 2.4
COL_GAP = 4.0


def build(cuts: Path) -> tuple[StitchPlan, CardV7, dict]:
    """F: one row per sewn arm. P and M: their arms side by side, one row each.
    Teeth above each piece count its arm (a = 1 ... d = 4)."""
    c = CardV7(WT)
    report: list[dict] = []
    y = 0.0
    for job in JOBS:
        cut_ = load(cuts, job)
        blk = BLOCK[job]
        sewn = SEWN[job]
        per_row = 1 if job == "fremont" else len(sewn)
        pieces = {arm: piece_runs(cut_, arm) for arm in sewn}
        pitch = max(_bbox([p for r in rs for p in r.points])[2] - _bbox([p for r in rs for p in r.points])[0]
                    for rs in pieces.values()) + COL_GAP
        y_block = y
        for i, arm in enumerate(sewn):
            col = i % per_row
            runs = pieces[arm]
            top = y + TOP
            c.add(0, hc.teeth(col * pitch, top - 0.8, TEETH[arm]), f"{blk}:label:{arm}")
            box = v3.place_runs(c, runs, col * pitch, top, blk, arm)
            a = cut_["arms"][arm]
            report.append({"block": blk, "job": job, "arm": arm, "teeth": TEETH[arm], "label": ARMS[arm][0],
                           "flags": ARMS[arm][1], "runs": len(runs), "satin": satin_stats(runs),
                           "fill": fill_stats(runs),
                           "stitches_whole": a["stitches_whole"], "trims_whole": a["trims_whole"],
                           "width_mm": round(box[2] - box[0], 2), "height_mm": round(box[3] - box[1], 2)})
            if col == per_row - 1 or i == len(sewn) - 1:
                y = max(b[3] for k, b in c.arms.items() if k.startswith(f"{blk}:")) + ROW_GAP
        c.boxes[blk] = (0.0, y_block, max(b[2] for k, b in c.arms.items() if k.startswith(f"{blk}:")),
                        y - ROW_GAP)
        y += 0.6
    plan = c.plan()
    xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
    ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for b in plan.blocks:
        for r in b.runs:
            r.points = [(px - cx, py - cy) for px, py in r.points]
    for table in (c.boxes, c.arms):
        for kk, (a0, b0, c0, d0) in list(table.items()):
            table[kk] = (a0 - cx, b0 - cy, c0 - cx, d0 - cy)
    plan.design_size_mm = (max(xs) - min(xs), max(ys) - min(ys))
    return plan, c, {"pieces": report}


# --- renders -----------------------------------------------------------------------------------

def _rendered(plan: StitchPlan, ppm: float):
    """The card at `ppm` px/mm (thread at its laid width) and a plan-mm box -> pixel crop."""
    from digitizer_core import machine, stitchviz
    from digitizer_core.adapter import plan_to_design
    design = plan_to_design(plan, name=f"card v7 {WT} wt")
    img = stitchviz.render_design(design, px_per_mm=ppm, pad_mm=2.0, thread_mm=machine.thread_profile(WT).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], ppm, 2.0)
    u = stitchviz.UNITS_PER_MM

    def px(box, pad=0.0):
        a = to_px({"x": (box[0] - pad) * u, "y": -(box[1] - pad) * u})
        b = to_px({"x": (box[2] + pad) * u, "y": -(box[3] + pad) * u})
        (xa, xb), (ya, yb) = sorted((a[0], b[0])), sorted((a[1], b[1]))
        return max(0, xa), max(0, ya), xb, yb
    return img, px


def arm_previews(plan: StitchPlan, card: CardV7, cuts: Path, out: Path, ppm: float = 20.0) -> list[Path]:
    """One picture per arm: its F row (or the arm it equals there, said so)
    beside its M piece, cropped from the card render."""
    import cv2
    img, px = _rendered(plan, ppm)
    same = {job: same_as(load(cuts, job)) for job in JOBS}
    paths = []
    for arm, (label, _flags) in ARMS.items():
        tiles = []
        for job in JOBS:
            blk = BLOCK[job]
            src = arm if arm in SEWN[job] else same[job][arm]
            x0, y0, x1, y1 = px(card.arms[f"{blk}:{src}"], pad=0.4)
            note = f"{blk} ({arm})" if src == arm else f"{blk}: sewn as ({src}), byte-identical"
            tiles.append(v2._label(img[y0:y1, x0:x1].copy(), note))
        pic = v2._label(v2._hstack(tiles, gap=24), f"arm ({arm}) {TEETH[arm]} teeth: {label}  "
                        f"{' '.join(f'{k}={v}' for k, v in ARMS[arm][1].items())}")
        path = out / f"arm_{arm}.jpg"
        cv2.imwrite(str(path), pic, [cv2.IMWRITE_JPEG_QUALITY, 88])
        paths.append(path)
    return paths


# --- the worksheet -----------------------------------------------------------------------------

LOOK = {
    "F": ("Hold it beside the pro's Fremont patch. HOTEL FREMONT and the two bars: fabric showing "
          "between satin stitches? bars puckered or flat? Wisconsin: fabric through the fill? "
          "Letters as heavy as the pro's?"),
    "P": ("Fill coverage: fabric showing through the field or the big disc (fill stitch 3.0 vs "
          "3.49)? Puckering or tunnels round them? The SMALL disc's bean edge line (0.73 vs 0.95): "
          "smooth, or lumpy / gappy? Lies flat off the hoop?"),
    "M": ("Calipers across the I's stem: the art draws ~4.2 mm, the pro sews 4.0. Split satin (a line "
          "of needle holes down the column) or plain, like the pro's? The gap between I and N and the "
          "N's two notches: open or closed up? Puckering beside the columns? Fabric showing?"),
}


def planned(p: dict) -> list[str]:
    s, f = p["satin"], p["fill"]
    out = ([f"satin {s['width_mm']} / {s['stitch_mm']}", f"rail step {s['rail_step_mm']}",
            f"split {s['split_pct']:.0f}%"] if s["width_mm"] else [])
    out += [f"fill stitch {f['fill_stitch_mm']} (p75)"] if f["fill_stitch_mm"] else []
    out += [f"bean cap {f['cap_stitch_mm']}"] if f["cap_stitch_mm"] else []
    return out or ["-"]


def worksheet(plan: StitchPlan, card: CardV7, rb: dict, out: Path) -> list[Path]:
    """One letter-size page Kent reads at the machine: the card with each
    piece's arm marked, then per arm its flags, stitches, planned satin
    width and what to look at, with boxes to tick. PNG and PDF."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    W, H, M = 1700, 2200, 70
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    font = lambda n: ImageFont.load_default(size=n)  # noqa: E731
    y = M
    d.text((M, y), "Sew-out card v7: pull by stroke and the pro's values", fill="black", font=font(46))
    y += 62
    est = rb["stitches_file"] / 650
    sew = (f"{NAME}.dst  |  one dark cone, 40 wt, 75/11  |  4 x 4 in hoop ({rb['extent_mm'][0]} x "
           f"{rb['extent_mm'][1]} mm: too tall for a cap frame)  |  twill + your Fremont backing  |  "
           f"{rb['stitches_file']:,} stitches, {rb['trims']} trims, ~{est:.0f} min at 650 spm  |  trims on")
    for line in _wrap(d, sew, font(24), W - 2 * M):
        d.text((M, y), line, fill="black", font=font(24))
        y += 32
    y += 10
    ppm = 14.0
    img, px = _rendered(plan, ppm)
    pic = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    s = min((W - 2 * M) / pic.width, 640 / pic.height)
    pic = pic.resize((int(pic.width * s), int(pic.height * s)), Image.LANCZOS)
    left = (W - pic.width) // 2
    page.paste(pic, (left, y))
    for key, box in card.arms.items():          # each piece's name, right of its teeth
        blk, arm = key.split(":")
        x0, y0, _x1, _y1 = px(box)
        lx = left + (x0 + (2.4 * TEETH[arm] + 1.0) * ppm) * s
        name = f"{blk} ({arm})" + (f" {ARMS[arm][0]}" if blk == "F" else "")   # M's sit too close
        d.text((lx, y + (y0 - TOP * ppm) * s), name, fill=(200, 30, 30), font=font(15))
    y += pic.height + 24
    by_piece = rb["stitches_by_piece"]
    cols = (M, M + 110, M + 210, M + 540, M + 650, M + 840)
    for x, head in zip(cols, ("piece", "teeth", "flags", "stitches", "plan (mm)", "look for")):
        d.text((x, y), head, fill=(90, 90, 90), font=font(22))
    y += 34
    for p in rb["pieces"]:
        d.line((M, y - 6, W - M, y - 6), fill=(200, 200, 200), width=1)
        flags = [f"{'ON ' if v else 'off'} {k}" for k, v in p["flags"].items()]
        row = [f"{p['block']} ({p['arm']})", "|" * p["teeth"], flags,
               f"{by_piece.get(p['block'] + ':' + p['arm'], 0):,}", planned(p),
               _wrap(d, LOOK[p["block"]], font(19), W - M - cols[5])]
        h = 0
        for x, cell in zip(cols, row):
            lines = cell if isinstance(cell, list) else [cell]
            f = font(19 if x in (cols[2], cols[4], cols[5]) else 24)
            for i, line in enumerate(lines):
                d.text((x, y + i * 24), line, fill="black", font=f)
            h = max(h, 24 * len(lines))
        marks = ("" if p["arm"] == "a" else "better than (a)?  Y / N      ") + (
            "fabric showing?  Y / N      puckered?  Y / N      breaks: ____")
        d.text((M, y + max(h, 50) + 2), marks, fill=(60, 60, 60), font=font(19))
        y += max(h, 50) + 40
    y += 10
    pro = rb["pro_satin"]["M"]
    tail = (f"The pro's own I and N (his DST, same reader, same window): cross {pro['width_mm']}, stitch "
            f"{pro['stitch_mm']}, split {pro['split_pct']:.0f}%. "
            "On these F pieces (b) is (a) and (d) is (c) byte for byte (across the whole design the pull flag "
            "moves two tagline letters by 0.02 mm): Fremont's strokes are ~0.85 mm, where the pull fit "
            "returns the hat's own 0.4. F sews (a) and (c) only. Planned satin = the file's medians, "
            "not the cloth's: cross = rail to rail, stitch = needle to needle, split = crosses sewn in two "
            "stitches. Every number is a candidate until this is sewn (ROADMAP gate 1).")
    for line in _wrap(d, tail, font(20), W - 2 * M):
        d.text((M, y), line, fill=(60, 60, 60), font=font(20))
        y += 26
    y += 12
    for q in ("Flip pull_comp_by_stroke?   Y / N", "Flip pro_measured_values?   Y / N"):
        d.text((M, y), q, fill="black", font=font(28))
        y += 40
    if y > H - M // 2:
        raise SystemExit(f"worksheet overflows the page: {y} > {H}")
    png, pdf = out / f"{NAME}_worksheet.png", out / f"{NAME}_worksheet.pdf"
    page.save(png)
    page.save(pdf, resolution=200.0)
    return [png, pdf]


def _wrap(d, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


# --- docs ----------------------------------------------------------------------------------------

README = """# Sew-out card v7 (2026-10-25): the two flags still waiting on fabric

**Sew this one beside the pro's Fremont patch.** Kent ruled 2026-10-22 that
stitch layout is judged in the preview; only what fabric does to thread needs
a sew-out. Two flags on main are that kind. Every number is a candidate until
you sew it (ROADMAP gate 1). Print `card_v7_40wt_worksheet.png` (or `.pdf`) and
take it to the machine.

**What to sew:** `card_v7_40wt.dst`, **one dark cone**, **40 wt**, 75/11, a
**flat 4 x 4 in hoop** (the design is SIZE_MM mm: too tall for a cap frame's
~57 mm), the structured twill you sewed card v4 on, with your Fremont backing. STITCHES stitches, TRIMS trims, about MINUTES minutes
(stitch count at 650 spm, not a measurement). Trims on.

## The arms

Teeth above each piece count its arm. Each arm pins BOTH flags (an unpinned
OFF would follow a later default flip):

| Teeth | Arm | `pull_comp_by_stroke` | `pro_measured_values` |
|---|---|---|---|
| 1 | (a) both off | off | off |
| 2 | (b) pull by stroke | **ON** | off |
| 3 | (c) pro values | off | **ON**: fill stitch 3.49 (3.0), satin 0.37 (0.40), bean 0.95 (0.73) |
| 4 | (d) both on | **ON** | **ON** |

Every arm also carries `BASE`, the flips Kent has ruled whose flags are on
main but whose flip PRs (#1057, #1070) had not merged when this was cut, so
row (a) is what ships: BASE_LIST. `tie_in_off` and `border_from_outline` are
ruled too but are not flags on main yet; the card cannot carry them.

## The three blocks

- **F**: Hotel Fremont at **92.5 mm, the pro's size**, Hat: the HOTEL FREMONT
  band (THE, HOTEL FREMONT, the two bars) and the crest (Wisconsin's fill, EST,
  1895). **F sews (a) and (c) only**: Fremont's strokes are ~0.85 mm, where
  the pull fit returns the hat's own 0.4, so on these pieces (b) is (a) and (d)
  is (c) byte for byte (the cut's md5s: SAME_F). Across the whole Fremont
  design the flag moves two letters of the tagline (not on the card) by at
  most 0.02 mm, and stitch and trim counts are unchanged: WHOLE_F. Hold each F
  row against the pro's patch.
- **P**: a fill plate through the real pipeline, Hat: a field with 18 mm rows
  (the pro's 3.49 was read on rows over 10 mm), a 7.5 mm disc, and a 5.5 mm
  disc. Under BASE's `border_by_size` the field and the big disc get a satin
  ring; the small disc keeps the bean edge cap, the only one on the card.
  Fremont's crop has neither a long-row fill nor a cap. Sews (a) and (c):
  no column, so (b) and (d) are the same (SAME_P).
- **M**: Becker MARINE at **76.5 mm, the pro's size**, Hat: wide satin strokes,
  where the pull flag acts: the I and the N, all four arms side by side.
  **Here the pull flag changes construction, not just width:** OFF plans the
  columns as SPLIT satin (two ~2.3 mm stitches per cross, a line of needle
  holes down the middle), ON as plain satin, as the pro sews them (his DST,
  same reader, last row of the table).

PIECES_TABLE

Look for: satin coverage (fabric between stitches), the bars and the wide
columns lying flat or puckering, the plate's fill covering and the small
disc's bean edge, the I's stem width against the art (~4.2 mm drawn, the pro
sews 4.0) and whether it sews split or plain, and the gaps staying open.

![](card_v7_40wt.png)

## Why only these two

Grepped on main (memory, `config.py`, MASTER_SCOPE) for flags held "until a
sew-out" / "unsewn" / "Kent flips after sew-out", then each checked against a
later ruling:

DROPPED

## The file (pystitch reading the DST back)

READBACK
"""

DROPPED = """| Candidate | Not on this card because |
|---|---|
| `fill_turn_slant` | Kent held it for "the next card's OFF/ON swatch" (10-22), then flipped it ON from the flip sheet (10-23, #1049 -> #1057). In BASE. |
| `satin_underlay_short_columns` | flipped ON 10-23 (layout: underlay presence). In BASE. Its zigzag pitch has no knob, and the pro's pitch is not measured (0.6-1.3 mm, it swings with the reader's satin gate: `short-column-underlay-2026-10-22`), so there is no candidate value to sew. |
| `fill_underlay_cross` | flipped ON 10-23 (layout). In BASE. Its constants match the pro already: row 1.0 / stitch 4.0 against his 0.98 / 3.99 (`docs/settings-vs-pro-2026-10-21.md` row 15). |
| `trim_bury_under_later`, `small_solids_satin`, `compact_solids_satin` | flipped ON 10-23 (layout). In BASE. |
| `cut_every_jump` | held by Kent until #1048's walk-on-the-work lands: a construction hold, not fabric. |
| `tie_in_off`, `border_from_outline` | ruled ON, not flags on main yet (#1042, #1065). |
| older gate-1 candidates (`bean_letter_*`, hairline / small-print flags, `chain_links`, ...) | not re-armed: cards v2-v6 carry them, and this card is the two flags Kent's 10-22 ruling leaves on fabric (queue item I5). The small-text set in BASE sews Fremont's small words as satin, so the bean-letter candidates no longer reach them. |
| `edge_cap_bean_pitch_mm` | its question (a longer bean stitch than 0.73) is asked here: `pro_measured_values` sews the bean edge cap at the pro's 0.95. |
"""


def whole_counts(cuts: Path, job: str) -> str:
    """Each arm's whole-design stitches / trims, as the cut recorded them."""
    return ", ".join(f"({arm}) {a['stitches_whole']:,} / {a['trims_whole']}"
                     for arm, a in load(cuts, job)["arms"].items())


def pieces_table(rb: dict, cuts: Path) -> str:
    n = rb["stitches_by_piece"]
    lines = ["| Piece | Teeth | Arm | Stitches | Planned satin: cross / stitch / rail step (mm), split | Planned fill "
             "stitch (p75) / bean cap stitch (mm) | Whole design, stitches / trims |", "|---|---|---|---|---|---|---|"]
    for p in rb["pieces"]:
        s, f = p["satin"], p["fill"]
        sat = (f"{s['width_mm']} / {s['stitch_mm']} / {s['rail_step_mm']}, {s['split_pct']}%"
               if s["width_mm"] else "-")
        whole = f"{p['stitches_whole']:,} / {p['trims_whole']}" if p["job"] != "plate" else "(the plate is whole)"
        lines.append(f"| {p['block']} | {p['teeth']} | ({p['arm']}) {p['label']} | "
                     f"{n.get(p['block'] + ':' + p['arm'], 0):,} | {sat} | {f['fill_stitch_mm'] or '-'} / "
                     f"{f['cap_stitch_mm'] or '-'} | {whole} |")
    for blk, s in rb["pro_satin"].items():
        lines.append(f"| {blk} | - | the pro's file (`{s['file']}`) | {s['stitches']:,} | {s['width_mm']} / "
                     f"{s['stitch_mm']} / (DST grid), {s['split_pct']}% | - | - |")
    return "\n".join(lines)


def generate(out: Path, cuts: Path | None = None, *, quiet: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cuts = cuts or out / "cuts"
    plan, card, extra = build(cuts)
    pattern = plan_to_pattern(plan)
    pattern.metadata("name", "CARD V7 40WT")
    path = out / f"{NAME}.dst"
    path.write_bytes(formats.write(pattern, "dst"))
    v3.render(plan, out / f"{NAME}.png")
    rb = v2.readback(path, plan, WT, card)
    rb["pieces"] = extra["pieces"]
    rb["arm_md5"] = c4.arm_digests(plan)
    rb["same_as"] = {job: same_as(load(cuts, job)) for job in JOBS}
    rb["minutes_at_650spm"] = round(rb["stitches_file"] / 650, 1)
    rb["pro_satin"] = {BLOCK[job]: pro_satin(job) for job in PRO_DST}
    if not quiet:
        print(json.dumps({k: v for k, v in rb.items() if k not in
                          ("pieces", "pieces_mm", "stitches_by_piece", "arm_md5")}))
    (out / "readback.json").write_text(json.dumps(rb, indent=1) + "\n", encoding="utf-8")
    arm_previews(plan, card, cuts, out)
    worksheet(plan, card, rb, out)
    same_f = ", ".join(f"({k}) = ({v})" for k, v in rb["same_as"]["fremont"].items()) or "none"
    text = (README.replace("READBACK", v3.readback_markdown(rb))
            .replace("PIECES_TABLE", pieces_table(rb, cuts))
            .replace("DROPPED", DROPPED.strip())
            .replace("SAME_F", same_f)
            .replace("SAME_P", ", ".join(f"({k}) = ({v})" for k, v in rb["same_as"]["plate"].items()))
            .replace("WHOLE_F", whole_counts(cuts, "fremont"))
            .replace("BASE_LIST", ", ".join(f"`{k}` {v}" for k, v in BASE.items()))
            .replace("SIZE_MM", f"{rb['extent_mm'][0]} x {rb['extent_mm'][1]}")
            .replace("STITCHES", f"{rb['stitches_file']:,}")
            .replace("TRIMS", f"{rb.get('trims', '?')}")
            .replace("MINUTES", f"{rb['stitches_file'] / 650:.0f}"))
    (out / "README.md").write_text(text, encoding="utf-8")
    return rb


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cut", choices=list(JOBS))
    ap.add_argument("--reselect", choices=list(JOBS), help="re-cut the windows from --cache")
    ap.add_argument("--cuts", default=str(DEFAULT_CUTS))
    ap.add_argument("--cache", default=None, help="also dump every run of each arm here")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    if args.cut:
        cut(args.cut, Path(args.cuts), Path(args.cache) if args.cache else None)
        return 0
    if args.reselect:
        reselect(args.reselect, Path(args.cuts), Path(args.cache))
        return 0
    generate(Path(args.out), Path(args.cuts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
