#!/usr/bin/env python
"""DT-first classifier probe — Goldman's rule vs the shipped classifier,
region by region, over the committed corpus fixtures.

The 2026-08-01 masters teardown named ONE structural lead the expired
Goldman/SoftSight chain has on this pipeline: satin-vs-fill is decided from
distance-transform statistics at skeletal pixels (rule of record:
`2*sigma < mu < max/2` => "predominantly regular" => satin), computed in the
same pass as the contour and skeleton — before anything decides how a shape
sews. EMB-Bot decides from `2*area/perimeter` + an aspect gate first and
builds the DT after (and, since `satin-classifier-organic-shapes` landed,
re-checks its own YES with two DT terms — the `VP90` tightening — inside
`is_satin_candidate` itself).

This probe answers the question that stayed open after the 2026-08-02 spike
(`digitizer/docs/dt-classifier-spike-2026-08-02.md`) and the hardening
closeout that scored its VP90 recommendation NOT_SOUND at the then-shipped
cap: **is a DT-FIRST verdict — the DT statistics deciding, not merely
tightening — better, worse, or mixed against what ships today**, measured on
every region the current pipeline actually produces on the committed
fixtures (the same 14 files `tools/corpus_scorecard.py` scores, which
include the benchmark `photo/enthusiast_logo.png` and the fixture logo).

Standalone, like `tools/shape_lens.py` (whose rasteriser and DTStats it
imports — same instrument independence: fixed 20 px/mm grid, never a
function of the statistic under test). NOTHING here is imported by the
pipeline; this is a measurement, not a feature.

Three DT-first arms, all three-way (run / satin / fill):

  goldman_printed   2s<mu AND mu<max/2, thin = 2*max<=cap  (the rule AS
                    PRINTED in US6804573 — kept because it is the rule of
                    record, even though the architecture note's own bench
                    pass says the middle term is transcribed inverted)
  goldman_bench     2s<mu AND mu>max/2 AND 2*max<=cap      (the corrected
                    reading the note ships as its spec = spike arm R2)
  dt_var_p90        2s<mu AND 2*p90<=cap                   (the two terms
                    the closeout said were the only ones worth keeping,
                    HERE STANDING ALONE — no ribbon width, no aspect gate.
                    The shipped classifier already ANDs these same terms
                    onto ribbon+aspect, so this arm isolates exactly what
                    the ribbon+aspect half still contributes.)

  run tier, all arms: 2*max <= 1.0 mm — Law 31's satin floor ("under 1 mm:
  convert to multi-ply run"), the DT analogue of the shipped
  `area < min_detail_mm^2` rescue.

The shipped verdict is reproduced with stage 7's own predicates in stage 7's
own order (`stitch_one`'s auto ladder): run rescue by area floor, then
`is_satin_candidate` (which now internally includes the VP90 DT tightening),
else fill. Classified on the ARTWORK polygon, exactly as stage 7 does.

Disagreements are adjudicated by the machine-physics laws
(`docs/machine-physics-playbook-2026-07-31.md`), mechanically where a law
decides and by rendered gallery where it does not:

  - Law 31 / SATIN_MAX_WIDTH_MM: a satin call on a shape whose p90 DT width
    exceeds the 5.0 mm cap is wrong (crosses float/snag); over 8 mm it is
    wrong twice.
  - Law 31 floor: satin under ~1 mm is a multi-ply run's job; a shape whose
    WIDEST point is under the floor cannot carry satin or fill at all.
  - MIN_FILL_WIDTH_MM: a fill call on a shape too narrow to hold a single
    row (poly.buffer(-0.6) empty) is wrong — rows have nowhere to run.
  - Blob test: satin on a compact shape (skeleton shorter than ~2 mean
    widths) is the starburst defect the spike photographed; fill is right.
  - Escape test: a satin choice whose rendered crosses leave the artwork
    outline is wrong regardless of any statistic.

One scope caveat, discovered against the real plans and corrected for in the
verdict doc (docs/dt-first-verdict-2026-08-11.md): the gallery here sews both
choices on the ARTWORK polygon — the classifier's own input, per stage 7's
comment — while the machine sews the stage-5 pull-compensated polygon. On
sub-millimetre strokes compensation can more than double the sewn width, so
a "satin skeleton unresolvable" verdict here can still sew as (very narrow)
satin end-to-end. The verdict doc re-measures every satin-vs-run flip off
the realized plan's own emitted crosses; the adjudications quoted there are
the realized-geometry ones.

Usage (from digitizer/, PYTHONPATH=.):
    .venv/Scripts/python tools/dt_first_probe.py            # table + matrices
    .venv/Scripts/python tools/dt_first_probe.py --render   # + gallery PNGs
    .venv/Scripts/python tools/dt_first_probe.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from digitizer_core import PipelineConfig, run_stages  # noqa: E402
from digitizer_core import machine, stitches  # noqa: E402
from digitizer_core.machine import (  # noqa: E402
    FILL_ROW_MM,
    FILL_STITCH_MM,
    SATIN_MAX_WIDTH_MM,
)
from digitizer_core.stage6_border import run_outline  # noqa: E402
from digitizer_core.stage6_fill import stitch_shape  # noqa: E402
from digitizer_core.stage6_satin import is_satin_candidate, satin_shape  # noqa: E402
from digitizer_core.stage6_satin import ribbon_width_mm, strip_splits  # noqa: E402
from shape_lens import DTStats, dt_stats, mask_of  # noqa: E402  (the instrument)

OUT_DIR = ROOT.parent / "debug_out" / "dt_first_probe"

# The same fixtures tools/corpus_scorecard.py scores — the committed corpus.
FIXTURES = [
    "bg_uncertain.png",
    "logo_alpha.png",
    "logo_whitebg.png",
    "ribbon_curve.png",
    "photo/drone_render.png",
    "photo/enthusiast_logo.png",
    "photo/fur_ramp.png",
    "photo/gradient_ramp_linear.png",
    "photo/gradient_ramp_radial.png",
    "photo/photo_scene_stub.png",
    "photo/photo_subject_stub.png",
    "photo/region_blobs.png",
    "photo/repro_gradient_white_icon.png",
    "photo/summit_badge.png",
]
WIDTH_MM = 80.0

# Law 31's satin floor: "under 1 mm: convert to multi-ply run". A shape whose
# WIDEST point is under this cannot hold satin (crosses degenerate) or fill
# (rows have nowhere to run) — the DT analogue of the shipped area rescue.
RUN_FLOOR_MM = 1.0
# Law 31's snag ceiling: "over 8 mm: split or fill". Any satin verdict on a
# shape this wide at p90 is wrong twice (cap first, snag second).
SATIN_SNAG_MM = 8.0
# A satin cross midpoint may legitimately sit ON the boundary; farther out
# than this is the escaping-starburst defect, not raster rounding.
ESCAPE_TOL_MM = 0.15
ESCAPE_FRAC = 0.05


# --- Verdicts ---------------------------------------------------------------

def shipped_verdict(poly: Polygon, area_mm2: float, design_class: str,
                    cfg: PipelineConfig) -> str:
    """Stage 7's auto ladder, predicates verbatim, in stage 7's order."""
    detail_mm2 = cfg.min_detail_mm ** 2
    if cfg.small_shape_rescue and area_mm2 < detail_mm2:
        return "run"
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    if cfg.satin and is_satin_candidate(poly, satin_max,
                                        design_class=design_class):
        return "satin"
    return "fill"


def dt_verdict(s: DTStats, cap_mm: float, arm: str) -> str:
    """Three-way DT-first verdict for one arm. See module docstring."""
    if s.n == 0:
        return "run"                       # nothing skeletonizable at 20 px/mm
    if s.max_width_mm <= RUN_FLOOR_MM:
        return "run"
    regular = 2.0 * s.sd < s.mu
    if arm == "goldman_printed":
        # The rule of record, as printed: 2*sigma < mu < max/2.
        satin = regular and (s.mu < 0.5 * s.mx) and s.max_width_mm <= cap_mm
    elif arm == "goldman_bench":
        # The architecture note's corrected spec (spike arm R2).
        satin = regular and (s.mu > 0.5 * s.mx) and s.max_width_mm <= cap_mm
    elif arm == "dt_var_p90":
        # The closeout's "only terms worth shipping", standing alone.
        satin = regular and (2.0 * s.p90 / s.scale) <= cap_mm
    else:  # pragma: no cover - guarded by argparse choices
        raise ValueError(arm)
    return "satin" if satin else "fill"


ARMS = ["goldman_printed", "goldman_bench", "dt_var_p90"]


# --- The physics judge ------------------------------------------------------

@dataclass
class Judgement:
    winner: str        # "shipped" | "dt" | "tossup"
    reason: str


def _satin_cross_lengths_mm(runs) -> list[float]:
    """Cross lengths of a rendered satin choice — consecutive point distances
    inside SATIN runs (points strictly alternate rails, so each step is one
    cross plus its spine advance). Independent of the lens DT: this is the
    engine's own emitted geometry, which is what makes it a legitimate judge
    of a verdict the lens DT produced."""
    out: list[float] = []
    for r in runs:
        if r.kind != stitches.SATIN or len(r.points) < 2:
            continue
        pts = strip_splits(r.points)
        out.extend(math.dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))
    return out


def _satin_cross_escape_frac(runs, poly: Polygon) -> float:
    """Fraction of satin cross midpoints outside the artwork outline."""
    pts_out = total = 0
    slack = poly.buffer(ESCAPE_TOL_MM)
    from shapely.geometry import Point as SPoint
    for r in runs:
        if r.kind != stitches.SATIN or len(r.points) < 2:
            continue
        for i in range(1, len(r.points)):
            mx = (r.points[i - 1][0] + r.points[i][0]) / 2.0
            my = (r.points[i - 1][1] + r.points[i][1]) / 2.0
            total += 1
            if not slack.contains(SPoint(mx, my)):
                pts_out += 1
    return pts_out / total if total else 0.0


def render_choice(poly: Polygon, tier: str, shape_id: str):
    """Actually sew one choice, exactly as stage 7 would (no underlay — the
    question is the cover pass). -> (runs, report)."""
    if tier == "satin":
        return satin_shape(poly, shape_id, underlay_style="none",
                           trim_at_mm=math.inf)
    if tier == "run":
        return run_outline(poly, shape_id, entry=None, trim_at_mm=math.inf)
    return stitch_shape(poly, shape_id, angle_deg=None, row_mm=FILL_ROW_MM,
                        stitch_mm=FILL_STITCH_MM, underlay_style="none",
                        trim_at_mm=math.inf)


def judge(poly: Polygon, s: DTStats, shipped: str, dt: str,
          rendered: dict) -> Judgement:
    """Which of two disagreeing verdicts do the physics laws favour?

    `rendered` maps tier -> (runs, report) for the tiers already sewn by the
    caller. Rules fire in severity order; the first that decides, decides.
    """
    p90_mm = 2.0 * s.p90 / s.scale
    mean_mm = s.mean_width_mm
    skel_len_mm = s.n / s.scale if s.scale else 0.0
    compact = mean_mm > 0 and skel_len_mm < 2.0 * mean_mm

    def against_satin(other: str, who_satin: str) -> Judgement | None:
        """Laws that kill a satin call. `other` wins if one fires."""
        runs, rep = rendered[("shipped" if who_satin == "shipped" else "dt")]
        if rep.get("empty"):
            return Judgement(other, "satin skeleton unresolvable — falls "
                                    "through to fill anyway")
        if p90_mm > SATIN_SNAG_MM:
            return Judgement(other, f"p90 width {p90_mm:.2f} mm > {SATIN_SNAG_MM} "
                                    "mm snag ceiling (Law 31: split or fill)")
        if p90_mm > SATIN_MAX_WIDTH_MM:
            return Judgement(other, f"p90 width {p90_mm:.2f} mm > "
                                    f"{SATIN_MAX_WIDTH_MM} mm SATIN_MAX_WIDTH")
        esc = _satin_cross_escape_frac(runs, poly)
        if esc > ESCAPE_FRAC:
            return Judgement(other, f"{esc:.0%} of rendered crosses escape "
                                    "the outline (starburst defect)")
        if compact:
            return Judgement(other, f"compact blob: skeleton {skel_len_mm:.1f} "
                                    f"mm < 2x mean width {mean_mm:.2f} mm — "
                                    "satin reads as a starburst, not a column")
        return None

    def against_fill(other: str) -> Judgement | None:
        """Laws that kill a fill call."""
        if poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
            return Judgement(other, "too narrow to hold one fill row "
                                    f"(MIN_FILL_WIDTH {machine.MIN_FILL_WIDTH_MM} "
                                    "mm) — fill rows have nowhere to run")
        return None

    def against_run(other: str) -> Judgement | None:
        """A run call on a shape with sewable body drops coverage."""
        if s.max_width_mm > 2.0 and poly.area > 4.0:
            return Judgement(other, f"run tier on a {s.max_width_mm:.1f} mm wide, "
                                    f"{poly.area:.1f} mm^2 shape leaves bare "
                                    "fabric — outline is not coverage")
        return None

    pair = {shipped: "shipped", dt: "dt"}
    if "satin" in pair:
        other = "dt" if pair["satin"] == "shipped" else "shipped"
        j = against_satin(other, pair["satin"])
        if j:
            return j
    if "satin" in pair and "run" in pair:
        # Law 31's floor, tested NON-CIRCULARLY: not on the lens DT (which is
        # what produced the run verdict) but on the crosses the satin choice
        # actually emits. Under 1 mm they are a multi-ply run's job; at or
        # above it, the stroke genuinely carries satin and an outline run
        # would abandon its coverage.
        crosses = _satin_cross_lengths_mm(rendered[pair["satin"]][0])
        if crosses:
            med = float(np.median(crosses))
            if med < RUN_FLOOR_MM:
                return Judgement(pair["run"],
                                 f"rendered satin crosses median {med:.2f} mm "
                                 f"< {RUN_FLOOR_MM} mm (Law 31: under 1 mm "
                                 "converts to multi-ply run)")
            return Judgement(pair["satin"],
                             f"rendered satin crosses median {med:.2f} mm — a "
                             "real column; an outline run abandons its cover")
    if "fill" in pair:
        other = "dt" if pair["fill"] == "shipped" else "shipped"
        j = against_fill(other)
        if j:
            return j
    if "run" in pair:
        other = "dt" if pair["run"] == "shipped" else "shipped"
        j = against_run(other)
        if j:
            return j
    # No law fires against either choice. If satin survived every satin-killing
    # law on a genuinely ribbon-like shape, satin is the pro call (fill on a
    # clean sub-cap ribbon is the "lumpy scribble" error direction).
    if "satin" in pair and "fill" in pair and not compact \
            and p90_mm <= SATIN_MAX_WIDTH_MM:
        return Judgement(pair["satin"], f"clean ribbon under the cap "
                                        f"(p90 {p90_mm:.2f} mm, skeleton "
                                        f"{skel_len_mm:.1f} mm): satin is the "
                                        "pro call, fill is the lumpy-scribble "
                                        "direction")
    return Judgement("tossup", "no law decides; adjudicate from the render")


# --- Gallery ----------------------------------------------------------------

_KIND_COLOR = {
    stitches.SATIN: (80, 220, 80),
    stitches.FILL: (60, 160, 255),
    stitches.RUN: (255, 200, 60),
    stitches.BEAN: (255, 200, 60),
    stitches.BORDER: (255, 120, 200),
    stitches.UNDERLAY: (110, 110, 110),
    stitches.TRAVEL: (70, 70, 70),
}


def _draw_runs(canvas: np.ndarray, runs, poly: Polygon, scale: float,
               ox: float, oy: float) -> None:
    def px(pt):
        return (int((pt[0] - ox) * scale), int((pt[1] - oy) * scale))

    ext = np.array([px(p) for p in poly.exterior.coords], np.int32)
    cv2.polylines(canvas, [ext], True, (200, 200, 200), 1, cv2.LINE_AA)
    for ring in poly.interiors:
        arr = np.array([px(p) for p in ring.coords], np.int32)
        cv2.polylines(canvas, [arr], True, (140, 140, 140), 1, cv2.LINE_AA)
    for r in runs:
        col = _KIND_COLOR.get(r.kind, (255, 255, 255))
        arr = np.array([px(p) for p in r.points], np.int32)
        if len(arr) >= 2:
            cv2.polylines(canvas, [arr], False, col, 1, cv2.LINE_AA)


def render_gallery_png(row: dict, arm: str, out: Path) -> Path:
    """Three panels: DT heat + skeleton | shipped choice sewn | DT choice sewn."""
    poly, s = row["poly"], row["stats"]
    mask, scale = mask_of(poly)
    from skimage.morphology import medial_axis
    skel, dist = medial_axis(mask, return_distance=True, rng=0)

    h, w = mask.shape
    heat = np.zeros((h, w, 3), np.uint8)
    if dist.max() > 0:
        ramp = cv2.applyColorMap((255 * dist / dist.max()).astype(np.uint8),
                                 cv2.COLORMAP_INFERNO)
        heat[mask] = ramp[mask]
    heat[skel] = (255, 255, 255)

    x0, y0, x1, y1 = poly.bounds
    ox, oy = x0 - 2 / scale, y0 - 2 / scale
    panel_a = np.zeros((h, w, 3), np.uint8)
    panel_b = np.zeros((h, w, 3), np.uint8)
    _draw_runs(panel_a, row["rendered"]["shipped"][0], poly, scale, ox, oy)
    _draw_runs(panel_b, row["rendered"]["dt"][0], poly, scale, ox, oy)

    gap = np.full((h, 6, 3), 30, np.uint8)
    strip = np.concatenate([heat, gap, panel_a, gap, panel_b], axis=1)
    pad = np.zeros((strip.shape[0] + 74, max(strip.shape[1], 900), 3), np.uint8)
    pad[74:74 + strip.shape[0], :strip.shape[1]] = strip

    j: Judgement = row["judgements"][arm]
    name = row["name"]
    lines = [
        f"{name}   [{arm}]",
        (f"2A/P {row['ribbon_w']:.2f}  dt p90 {2*s.p90/s.scale:.2f}  "
         f"max {s.max_width_mm:.2f}  mu {s.mean_width_mm:.2f}  "
         f"sd/mu {(s.sd/s.mu if s.mu else 0):.3f}  skel {s.n/s.scale:.1f} mm"),
        (f"shipped={row['shipped']}   dt={row['arms'][arm]}   "
         f"judge: {j.winner.upper()} — {j.reason}"),
        "panels: DT heat + skeleton | shipped choice | dt choice",
    ]
    for i, txt in enumerate(lines):
        cv2.putText(pad, txt[:150], (4, 15 + 15 * i), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (230, 230, 230) if i else (255, 255, 120), 1,
                    cv2.LINE_AA)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{arm}__{name.replace('/', '_')}.png"
    cv2.imwrite(str(path), pad)
    return path


# --- The run ----------------------------------------------------------------

def collect_rows(cap_mm: float) -> list[dict]:
    cfg = PipelineConfig(target_width_mm=WIDTH_MM)
    rows: list[dict] = []
    td = ROOT / "testdata"
    for fixture in FIXTURES:
        path = td / fixture
        if not path.exists():
            print(f"  (skip {fixture}: not present)", file=sys.stderr)
            continue
        res = run_stages(path, cfg)
        for r in res.regions:
            if not r.meta.get("stitched", True):
                continue  # excluded from the machine's work; no verdict exists
            forced = str(r.meta.get("tier", "auto")).lower()
            poly = r.polygon
            mask, scale = mask_of(poly)
            s = dt_stats(mask, scale, trim=0)
            row = {
                "fixture": fixture,
                "name": f"{Path(fixture).stem}/{r.shape_id}",
                "poly": poly,
                "area": poly.area,
                "ribbon_w": ribbon_width_mm(poly),
                "stats": s,
                "design_class": res.design_class,
                "forced": forced if forced != "auto" else None,
                "shipped": (forced if forced in ("run", "satin", "fill")
                            else shipped_verdict(poly, poly.area,
                                                 res.design_class, cfg)),
                "arms": {arm: dt_verdict(s, cap_mm, arm) for arm in ARMS},
            }
            rows.append(row)
    return rows


def confusion(rows: list[dict], arm: str) -> dict:
    tiers = ("run", "satin", "fill")
    m = {(a, b): 0 for a in tiers for b in tiers}
    for r in rows:
        m[(r["shipped"], r["arms"][arm])] += 1
    return m


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cap", type=float, default=None,
                    help="satin width cap mm (default machine.SATIN_MAX_WIDTH_MM)")
    ap.add_argument("--render", action="store_true",
                    help="write disagreement gallery PNGs")
    ap.add_argument("--json", type=Path, default=None,
                    help="dump rows + matrices as JSON")
    args = ap.parse_args()
    cap = args.cap or SATIN_MAX_WIDTH_MM

    print(f"# DT-first probe. cap={cap} mm, lens 20 px/mm, trim=0, "
          f"fixtures at {WIDTH_MM:g} mm.")
    rows = collect_rows(cap)
    print(f"# {len(rows)} stitched regions across "
          f"{len({r['fixture'] for r in rows})} fixtures.\n")

    hdr = (f"{'region':<42} {'2A/P':>6} {'p90w':>6} {'maxw':>6} {'sd/mu':>6} "
           f"{'ship':>6} " + " ".join(f"{a[:9]:>9}" for a in ARMS))
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        s = r["stats"]
        print(f"{r['name']:<42} {r['ribbon_w']:6.2f} {2*s.p90/s.scale:6.2f} "
              f"{s.max_width_mm:6.2f} {(s.sd/s.mu if s.mu else 0):6.3f} "
              f"{r['shipped']:>6} "
              + " ".join(f"{r['arms'][a]:>9}" for a in ARMS))

    # Confusion matrices, shipped as rows / arm as columns.
    for arm in ARMS:
        m = confusion(rows, arm)
        agree = sum(m[(t, t)] for t in ("run", "satin", "fill"))
        print(f"\n# --- {arm}: shipped (rows) vs {arm} (cols) — "
              f"agree {agree}/{len(rows)} ---")
        print(f"  {'':>8} {'run':>5} {'satin':>6} {'fill':>5}")
        for a in ("run", "satin", "fill"):
            print(f"  {a:>8} " + " ".join(
                f"{m[(a, b)]:>{5 if b != 'satin' else 6}}"
                for b in ("run", "satin", "fill")))

    # Disagreements: render both choices, judge by physics.
    print("\n# --- disagreements, adjudicated by the physics laws ---")
    tally = {arm: {"shipped": 0, "dt": 0, "tossup": 0} for arm in ARMS}
    gallery: list[str] = []
    for r in rows:
        needed = {t for t in (r["shipped"],
                              *(r["arms"][a] for a in ARMS
                                if r["arms"][a] != r["shipped"]))}
        if needed == {r["shipped"]}:
            continue
        rendered: dict[str, tuple] = {}
        by_tier = {t: render_choice(r["poly"], t, r["name"].split("/")[-1])
                   for t in needed}
        r["judgements"] = {}
        for arm in ARMS:
            if r["arms"][arm] == r["shipped"]:
                continue
            rendered = {"shipped": by_tier[r["shipped"]],
                        "dt": by_tier[r["arms"][arm]]}
            r["rendered"] = rendered
            j = judge(r["poly"], r["stats"], r["shipped"], r["arms"][arm],
                      rendered)
            r["judgements"][arm] = j
            tally[arm][j.winner] += 1
            print(f"  {r['name']:<42} shipped={r['shipped']:<5} "
                  f"{arm}={r['arms'][arm]:<5} -> {j.winner.upper():<7} {j.reason}")
            if args.render:
                gallery.append(str(render_gallery_png(r, arm, OUT_DIR)))

    print("\n# --- who was right, per arm (physics-law adjudication) ---")
    print(f"  {'arm':<16} {'dt right':>9} {'shipped right':>14} {'tossup':>7}")
    for arm in ARMS:
        t = tally[arm]
        print(f"  {arm:<16} {t['dt']:>9} {t['shipped']:>14} {t['tossup']:>7}")

    if args.render:
        print(f"\n# wrote {len(gallery)} gallery renders to {OUT_DIR}")

    if args.json:
        payload = {
            "cap_mm": cap,
            "n_regions": len(rows),
            "rows": [{
                "name": r["name"], "fixture": r["fixture"],
                "design_class": r["design_class"],
                "area_mm2": round(r["area"], 3),
                "ribbon_w_mm": round(r["ribbon_w"], 4),
                "dt_p90_w_mm": round(2 * r["stats"].p90 / r["stats"].scale, 4),
                "dt_max_w_mm": round(r["stats"].max_width_mm, 4),
                "dt_mean_w_mm": round(r["stats"].mean_width_mm, 4),
                "sd_over_mu": round(r["stats"].sd / r["stats"].mu, 4)
                              if r["stats"].mu else None,
                "skel_mm": round(r["stats"].n / r["stats"].scale, 2),
                "shipped": r["shipped"],
                **{a: r["arms"][a] for a in ARMS},
                "judgements": {a: {"winner": j.winner, "reason": j.reason}
                               for a, j in r.get("judgements", {}).items()},
            } for r in rows],
            "confusion": {arm: {f"{a}->{b}": n for (a, b), n in
                                confusion(rows, arm).items() if n}
                          for arm in ARMS},
            "adjudication": tally,
            "gallery": gallery,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"# wrote {args.json}")


if __name__ == "__main__":
    main()
