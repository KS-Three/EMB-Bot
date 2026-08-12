#!/usr/bin/env python
"""Shape lens — measure how a shape would be classified, and by what.

The engine decides satin-vs-fill in `stage6_satin.is_satin_candidate`: mean
ribbon width `2*area/perimeter` under a cap, AND a 3:1 aspect estimate. The
patent record (Goldman/SoftSight US6804573, expired 2018) decides it from the
*distance transform sampled at skeletal pixels* — `max`, `mu`, `sigma` — with
the rule `2*sigma < mu < max/2` reading as "predominantly regular", i.e. of
uniform thickness, i.e. satinable.

This tool runs BOTH over the same shapes and prints one row each, so the
disagreements can be looked at rather than argued about. It is an instrument,
not engine code: nothing here is imported by the pipeline.

Two deliberate independences, because an instrument that shares code with its
subject proves nothing:

1. **Its own rasteriser.** `stage6_satin._rasterize` picks its resolution from
   `ribbon_width_mm(poly)` — the subject's own statistic. Measuring the DT on
   a grid whose resolution is a function of the number under test would be
   circular. `mask_of` here uses a fixed px/mm with a hard pixel cap and knows
   nothing about width.
2. **Its own skeleton statistics.** `medial_axis` is the shared library call
   (there is no second exact medial axis worth writing), but every statistic,
   the endpoint trim, and every rule arm are computed here from the raw
   arrays.

Usage
-----
    PYTHONPATH=. python tools/shape_lens.py dt          # the table
    PYTHONPATH=. python tools/shape_lens.py dt --ablate # + confusion matrices
    PYTHONPATH=. python tools/shape_lens.py dt --render # + PNGs of disagreements
    PYTHONPATH=. python tools/shape_lens.py timing      # cost against stages 1-4
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point as SPoint
from shapely.geometry import Polygon
from skimage.morphology import medial_axis

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import machine  # noqa: E402
from digitizer_core.stage6_satin import (  # noqa: E402  -- the SUBJECT
    is_satin_candidate,
    ribbon_width_mm,
)

# The lens's own raster resolution. Fixed, so it is not a function of the
# statistic under test, and high enough that the thinnest sewable stroke
# (MIN_FILL_WIDTH_MM = 1.2) is 24 px across — the DT of a 24 px wall is
# quantized at 1/24 of its width, well under the decision margin. The cap
# stops a 200 mm banner allocating a 4000 px grid; it only ever binds on
# shapes far too big for the satin question to be interesting.
LENS_PX_PER_MM = 20.0
LENS_MAX_PX = 1400


# --- The field -------------------------------------------------------------

def mask_of(poly: Polygon, px_per_mm: float = LENS_PX_PER_MM
            ) -> tuple[np.ndarray, float]:
    """-> (bool mask, scale px/mm). Holes are holes; 2 px of margin all round.

    Deliberately NOT `stage6_satin._rasterize`: that one derives its scale
    from `ribbon_width_mm`, which is half of what this tool is measuring.
    """
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0, 1e-6)
    scale = min(px_per_mm, LENS_MAX_PX / dim)
    w = int(math.ceil((x1 - x0) * scale)) + 4
    h = int(math.ceil((y1 - y0) * scale)) + 4
    img = np.zeros((h, w), np.uint8)

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack(
            [(a[:, 0] - x0) * scale + 2, (a[:, 1] - y0) * scale + 2]
        ).astype(np.int32)

    cv2.fillPoly(img, [px(poly.exterior.coords)], 255)
    for ring in poly.interiors:
        cv2.fillPoly(img, [px(ring.coords)], 0)
    return img.astype(bool), scale


def trim_endpoints(skel: np.ndarray, k: int) -> np.ndarray:
    """Peel `k` rounds of degree-1 pixels off a skeleton.

    The DT-first note specifies this at `k = round(max radius)`: the medial
    axis of a square-capped bar forks into the cap corners, those forks carry
    DT values falling to zero, and left in they inflate sigma on exactly the
    shapes that are most obviously satin.

    **Measured here, the trim makes every arm worse and the max-radius trim is
    actively dangerous.** The peel removes the LOW-DT skeletal pixels, and low
    DT is precisely the evidence that a shape is not of uniform thickness. On
    an 18 mm blob with a 2 mm tail, trimming by the global max radius (179 px)
    deletes the blob's entire skeleton and leaves the tail: sigma collapses
    45.6 -> 0.0 px and the verdict flips fill -> satin. A 4x4 mm square goes
    irregular -> regular at k=3, an 8x8 at k=8. Kept for the ablation, and
    for anybody who reads the note and wonders; the default is 0.

    Guarded: a shape whose skeleton is shorter than the trim would come back
    empty, and an empty skeleton has no statistics — the untrimmed skeleton is
    returned instead and the caller is told nothing was trimmed.
    """
    if k <= 0:
        return skel
    cur = skel.copy()
    for _ in range(k):
        nb = sum(np.roll(np.roll(cur, dy, 0), dx, 1)
                 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0))
        ends = cur & (nb <= 1)
        if not ends.any():
            break
        nxt = cur & ~ends
        if not nxt.any():
            return skel
        cur = nxt
    return cur if cur.any() else skel


@dataclass(frozen=True)
class DTStats:
    """Distance-transform statistics at skeletal pixels. Radii, in pixels."""
    scale: float          # px per mm
    n: int                # skeletal pixels sampled
    mx: float             # max radius
    mu: float             # mean radius
    sd: float             # standard deviation of radius
    med: float
    p10: float
    p90: float
    trimmed: int          # rounds of endpoint peel actually applied

    @property
    def max_width_mm(self) -> float:
        return 2.0 * self.mx / self.scale

    @property
    def mean_width_mm(self) -> float:
        return 2.0 * self.mu / self.scale

    @property
    def med_width_mm(self) -> float:
        return 2.0 * self.med / self.scale

    @property
    def regular(self) -> bool:
        """Goldman's variance term: uniform thickness along the spine."""
        return 2.0 * self.sd < self.mu

    @property
    def mu_over_half_max(self) -> bool:
        """Goldman's second term, the one the sibling patent drops."""
        return self.mu > 0.5 * self.mx

    @property
    def robust_regular(self) -> bool:
        """Order-statistic restatement of `regular`, immune to a single spike."""
        return self.med > 2.0 * (self.p90 - self.p10)


def dt_stats(mask: np.ndarray, scale: float, trim: int | str = 0) -> DTStats:
    """One `medial_axis` call; statistics of the DT at skeletal pixels only.

    `trim` is the endpoint peel: an int, or "R" for the max-radius peel the
    DT-first note specifies. **The default is 0, and that is a measured
    correction to the note** — see `trim_endpoints`.

    `rng=0` is not optional — unseeded tie-breaking makes the skeleton
    irreproducible, which a determinism test caught in the engine already.
    """
    skel, dist = medial_axis(mask, return_distance=True, rng=0)
    if not skel.any():
        return DTStats(scale, 0, 0, 0, 0, 0, 0, 0, 0)
    k = int(round(float(dist[skel].max()))) if trim == "R" else int(trim)
    kept = trim_endpoints(skel, k)
    r = dist[kept]
    if r.size == 0:
        kept, r = skel, dist[skel]
        k = 0
    return DTStats(
        scale=scale, n=int(r.size),
        mx=float(r.max()), mu=float(r.mean()), sd=float(r.std()),
        med=float(np.median(r)),
        p10=float(np.percentile(r, 10)), p90=float(np.percentile(r, 90)),
        trimmed=k if kept is not skel else 0,
    )


# --- The rule arms ---------------------------------------------------------
#
# Each takes DTStats and the satin width cap in mm, returns True for "sew this
# as a satin column". `ribbon` is the engine as it stands today and is here so
# every arm is scored on identical inputs.

def arm_ribbon(poly: Polygon, cap_mm: float) -> bool:
    return is_satin_candidate(poly, cap_mm)


def arm_R1(s: DTStats, cap_mm: float) -> bool:
    """Sibling-patent reading (US6397120B1): regularity + MEAN thinness.

    No `mu > max/2` term. Thinness is the mean width against the cap, which is
    the closest DT analogue of what the engine does today.
    """
    return s.n > 0 and s.regular and s.mean_width_mm <= cap_mm


def arm_R2(s: DTStats, cap_mm: float) -> bool:
    """Full bench reading of US6804573: 2*sigma < mu < max/2, then MAX thinness.

    `max_width_mm <= cap` is the physical test — "can a cross of this length
    lie flat" — not a tuned proxy. It is strictly stricter than R1.
    """
    return (s.n > 0 and s.regular and s.mu_over_half_max
            and s.max_width_mm <= cap_mm)


def arm_R2n(s: DTStats, cap_mm: float) -> bool:
    """R2 with the `mu > max/2` term ABLATED. The open question, isolated."""
    return s.n > 0 and s.regular and s.max_width_mm <= cap_mm


def arm_R3(s: DTStats, cap_mm: float) -> bool:
    """Robust variant: moments replaced by order statistics."""
    return s.n > 0 and s.robust_regular and s.max_width_mm <= cap_mm


def arm_MIN(poly: Polygon, s: DTStats, cap_mm: float) -> bool:
    """The smallest change that could capture the benefit: today's rule, AND
    the widest point of the shape fits under the cap.

    One extra term on shipped code. It is a pure TIGHTENING — it can only turn
    a satin call into a fill call, never the reverse — so it cannot create the
    error direction that costs more (fill-where-satin-was-right is a lumpy
    scribble in lettering; satin-where-fill-was-right is a floating cross).
    Everything the DT buys here is bought by `max`, with no variance term.
    """
    return is_satin_candidate(poly, cap_mm) and 0 < s.max_width_mm <= cap_mm


def arm_MIN2(poly: Polygon, s: DTStats, cap_mm: float) -> bool:
    """MIN plus Goldman's variance term. Two extra terms, still a tightening."""
    return arm_MIN(poly, s, cap_mm) and s.regular


def arm_VAR(poly: Polygon, s: DTStats, cap_mm: float) -> bool:
    """Today's rule AND Goldman's variance term, and nothing else.

    The candidate that survived adjudication. It keeps `2*area/perimeter` as
    the width — which is fine, because what `2*area/perimeter` gets WRONG is
    not the width of a ribbon but the recognition that a shape is not a ribbon
    at all, and that is exactly what `2*sigma < mu` reports. Also a pure
    tightening, so no shape that sews correctly today can start sewing worse.
    """
    return is_satin_candidate(poly, cap_mm) and s.n > 0 and s.regular


def arm_P90(poly: Polygon, s: DTStats, cap_mm: float) -> bool:
    """Today's rule AND the 90th-percentile width under the cap.

    The percentile exists because `max` is not a width on a letterform: at the
    crossbar of a 't' the inscribed circle is sqrt(2) times the stroke, and at
    a serif foot it is wider still, so `max` rejects the glyphs satin exists
    for. Melco US9702070 reaches the same conclusion from the other end and
    takes the 70th percentile of its stitch-width distribution.
    """
    return (is_satin_candidate(poly, cap_mm) and s.n > 0
            and 2.0 * s.p90 / s.scale <= cap_mm)


def arm_VP90(poly: Polygon, s: DTStats, cap_mm: float) -> bool:
    """VAR and P90 together — the recommendation.

    Two DT terms bolted onto the shipped rule, off one `medial_axis` call:
    `2*sigma < mu` says the shape is of uniform thickness, `2*p90 <= cap` says
    the part of it that is genuinely wide still fits under the needle. Neither
    replaces `2*area/perimeter` and neither touches the aspect gate, so the
    change is a pure tightening of a rule that is already tuned.
    """
    return arm_VAR(poly, s, cap_mm) and arm_P90(poly, s, cap_mm)


DT_ARMS = {"R1": arm_R1, "R2": arm_R2, "R2n": arm_R2n, "R3": arm_R3}
# Arms that need the polygon as well as the field, because they ADD a term to
# the shipped rule rather than replacing it. Every one is a pure tightening.
HYBRID_ARMS = {"MIN": arm_MIN, "MIN2": arm_MIN2, "VAR": arm_VAR,
               "P90": arm_P90, "VP90": arm_VP90}
ALL_ARMS = [*DT_ARMS, *HYBRID_ARMS]


# --- Populations -----------------------------------------------------------

@dataclass
class Case:
    name: str
    poly: Polygon
    truth: str | None      # "satin" | "fill" | None when nobody has adjudicated
    group: str


def _rect(w: float, h: float) -> Polygon:
    return Polygon([(0, 0), (w, 0), (w, h), (0, h)])


def _wedge(w0: float, w1: float, length: float, n: int = 120) -> Polygon:
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = t * length
        half = (w0 + (w1 - w0) * t) / 2.0
        top.append((x, -half))
        bot.append((x, half))
    return Polygon(top + bot[::-1])


def _serrated_disc(r: float, tooth: float, n: int = 120) -> Polygon:
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        rr = r + (tooth if i % 2 else -tooth)
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return Polygon(pts)


def _arc_ribbon(radius: float, width: float, sweep: float) -> Polygon:
    n = 90
    outer = [((radius + width / 2) * math.cos(t), (radius + width / 2) * math.sin(t))
             for t in np.linspace(0, sweep, n)]
    inner = [((radius - width / 2) * math.cos(t), (radius - width / 2) * math.sin(t))
             for t in np.linspace(sweep, 0, n)]
    return Polygon(outer + inner)


def unit_fixtures() -> list[Case]:
    """The five archetypes `test_satin.py` pins, plus the shapes this spike
    exists to expose. Truth is the sewing call a digitizer would make, and it
    is stated here so a disagreement has something to be wrong against."""
    BAR = _rect(24, 2)
    O_RING = Polygon(
        [(math.cos(t) * 10, math.sin(t) * 10) for t in np.linspace(0, 2 * math.pi, 80)],
        [[(math.cos(t) * 7.5, math.sin(t) * 7.5)
          for t in np.linspace(2 * math.pi, 0, 80)]],
    )
    C_STROKE = Polygon(
        [(math.cos(t) * 15, math.sin(t) * 15)
         for t in np.linspace(0.6, 2 * math.pi - 0.6, 50)]
        + [(math.cos(t) * 12, math.sin(t) * 12)
           for t in np.linspace(2 * math.pi - 0.6, 0.6, 50)]
    )
    T_SHAPE = Polygon([(0, 0), (20, 0), (20, 3), (11.5, 3),
                       (11.5, 20), (8.5, 20), (8.5, 3), (0, 3)])
    BLOB = SPoint(0, 0).buffer(8.0)
    return [
        # --- the five the engine's tests already pin ---
        Case("BAR 24x2", BAR, "satin", "unit"),
        Case("O_RING 2.5 wall", O_RING, "satin", "unit"),
        Case("C_STROKE 3 wall", C_STROKE, "satin", "unit"),
        Case("T_SHAPE 3 wall", T_SHAPE, "satin", "unit"),
        Case("BLOB r8 disc", BLOB, "fill", "unit"),
        # --- the shapes this spike exists for ---
        # A ribbon that fattens into a blob. Mean width is inside the cap and
        # the aspect ratio passes, so the engine satins a 9 mm end.
        Case("WEDGE 1->9 over 30", _wedge(1.0, 9.0, 30.0), "fill", "stress"),
        Case("WEDGE 1->5 over 30", _wedge(1.0, 5.0, 30.0), "satin", "stress"),
        Case("WEDGE 2->4 over 30", _wedge(2.0, 4.0, 30.0), "satin", "stress"),
        # Boundary noise doubles the perimeter and collapses 2*area/P.
        Case("SERRATED disc r10 t0.6", _serrated_disc(10.0, 0.6), "fill", "stress"),
        Case("SERRATED disc r10 t1.2", _serrated_disc(10.0, 1.2), "fill", "stress"),
        # Mixture: one shape, two techniques. Neither rule can express this;
        # what matters is which one at least reports that it is heterogeneous.
        Case("BLOB r9 + 2mm tail 25",
             SPoint(0, 0).buffer(9.0).union(
                 Polygon([(0, -1), (25, -1), (25, 1), (0, 1)])),
             "fill", "stress"),
        # Right at the cap. SATIN_MAX_WIDTH_MM is 5.0 here, 3.0 on main.
        Case("BAR 40x2.8", _rect(40, 2.8), "satin", "threshold"),
        Case("BAR 40x4.8", _rect(40, 4.8), "satin", "threshold"),
        Case("BAR 40x5.2", _rect(40, 5.2), "fill", "threshold"),
        Case("BAR 40x6.0", _rect(40, 6.0), "fill", "threshold"),
        Case("BAR 40x8.0", _rect(40, 8.0), "fill", "threshold"),
        # Compact shapes: the aspect gate's whole job.
        Case("SQUARE 4x4", _rect(4, 4), "fill", "compact"),
        Case("SQUARE 8x8", _rect(8, 8), "fill", "compact"),
        Case("DOT r1.5", SPoint(0, 0).buffer(1.5), "fill", "compact"),
        # Curved ribbons — the fixture art's own subject.
        Case("ARC r15 w2.5 180deg", _arc_ribbon(15, 2.5, math.pi), "satin", "curve"),
        Case("ARC r15 w6.0 180deg", _arc_ribbon(15, 6.0, math.pi), "fill", "curve"),
    ]


def art_cases(images: list[tuple[str, Path, float]]) -> list[Case]:
    """Every region of every real artwork, through stages 1-4 as the engine
    runs them. Truth is left None: these get adjudicated by eye."""
    from digitizer_core import PipelineConfig, run_stages
    out: list[Case] = []
    for label, path, width_mm in images:
        if not path.exists():
            print(f"  (skip {label}: {path} not present)")
            continue
        res = run_stages(path, PipelineConfig(target_width_mm=width_mm))
        for r in res.regions:
            out.append(Case(f"{label}/{r.shape_id}", r.polygon, None, label))
    return out


def default_art() -> list[tuple[str, Path, float]]:
    td = ROOT / "testdata"
    cases = ROOT / "debug_out" / "cases"
    return [
        ("logo_whitebg", td / "logo_whitebg.png", 80.0),
        ("logo_alpha", td / "logo_alpha.png", 80.0),
        ("bg_uncertain", td / "bg_uncertain.png", 80.0),
        ("ribbon_curve", td / "ribbon_curve.png", 80.0),
        ("serif_text", cases / "serif_text.png", 80.0),
        ("curved_ribbon", cases / "curved_ribbon.png", 80.0),
        ("nested_colors", cases / "nested_colors.png", 70.0),
    ]


# --- Reporting -------------------------------------------------------------

def measure(case: Case, cap_mm: float, trim: int | str = 0) -> dict:
    mask, scale = mask_of(case.poly)
    s = dt_stats(mask, scale, trim=trim)
    row = {
        "case": case, "stats": s, "mask": mask,
        "ribbon_w": ribbon_width_mm(case.poly),
        "ribbon": arm_ribbon(case.poly, cap_mm),
    }
    for name, fn in DT_ARMS.items():
        row[name] = fn(s, cap_mm)
    for name, fn in HYBRID_ARMS.items():
        row[name] = fn(case.poly, s, cap_mm)
    return row


HDR = (f"{'shape':<28} {'2A/P':>6} {'dtmax':>6} {'dtp90':>6} {'dtmu':>6} "
       f"{'sd/mu':>6} {'2s<m':>5} {'n':>5}  {'rib':>4} "
       + " ".join(f"{a:>4}" for a in ALL_ARMS) + "  truth")


def fmt(row: dict) -> str:
    s, c = row["stats"], row["case"]
    b = lambda v: " Y" if v else " ."  # noqa: E731
    arms = " ".join(f"{b(row[a]):>4}" for a in ALL_ARMS)
    return (f"{c.name:<28} {row['ribbon_w']:6.2f} {s.max_width_mm:6.2f} "
            f"{2*s.p90/s.scale:6.2f} {s.mean_width_mm:6.2f} "
            f"{(s.sd/s.mu if s.mu else 0):6.3f} {b(s.regular):>5} "
            f"{s.n:5d}  {b(row['ribbon']):>4} {arms}  {c.truth or '-'}")


def confusion(rows: list[dict], arm: str) -> dict:
    """Against stated truth. Only rows that have one."""
    m = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
    for r in rows:
        t = r["case"].truth
        if t is None:
            continue
        pred, want = r[arm], (t == "satin")
        m["TP" if (pred and want) else "FP" if pred else
          "FN" if want else "TN"] += 1
    return m


def render_disagreements(rows: list[dict], arm_a: str, arm_b: str, out: Path,
                         limit: int = 40) -> int:
    """Write one PNG per disagreeing shape: mask, skeleton, and the numbers.

    A confusion matrix with no adjudication is worth nothing, and a shape
    cannot be adjudicated from a row of floats.
    """
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for r in rows:
        if r[arm_a] == r[arm_b]:
            continue
        if n >= limit:
            break
        mask, s = r["mask"], r["stats"]
        skel, dist = medial_axis(mask, return_distance=True, rng=0)
        kept = trim_endpoints(skel, s.trimmed)
        img = np.zeros((*mask.shape, 3), np.uint8)
        img[mask] = (60, 60, 60)
        # DT as a heat ramp inside the shape, so a fat spot is visible.
        if dist.max() > 0:
            heat = cv2.applyColorMap(
                (255 * dist / dist.max()).astype(np.uint8), cv2.COLORMAP_INFERNO)
            img[mask] = heat[mask]
        img[skel] = (90, 90, 255)
        img[kept] = (255, 255, 255)
        pad = np.zeros((img.shape[0] + 54, max(img.shape[1], 560), 3), np.uint8)
        pad[54:54 + img.shape[0], :img.shape[1]] = img
        name = r["case"].name.replace("/", "_")
        cv2.putText(pad, name[:46], (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(pad, f"2A/P {r['ribbon_w']:.2f}  dtmax {s.max_width_mm:.2f}"
                         f"  dtmu {s.mean_width_mm:.2f}  sd {s.sd:.2f}",
                    (4, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1,
                    cv2.LINE_AA)
        cv2.putText(pad, f"{arm_a}={'satin' if r[arm_a] else 'fill'}   "
                         f"{arm_b}={'satin' if r[arm_b] else 'fill'}",
                    (4, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 255, 120), 1,
                    cv2.LINE_AA)
        cv2.imwrite(str(out / f"{arm_a}_vs_{arm_b}__{name}.png"), pad)
        n += 1
    return n


# --- Commands --------------------------------------------------------------

def cmd_dt(args) -> None:
    cap = args.cap or machine.SATIN_MAX_WIDTH_MM
    print(f"# satin cap {cap} mm, lens raster {LENS_PX_PER_MM} px/mm "
          f"(cap {LENS_MAX_PX} px), endpoint trim = {args.trim}")
    print(f"# widths in mm; mu/sd are DT RADII in px at skeletal pixels\n")

    rows: list[dict] = []
    print(HDR)
    print("-" * len(HDR))
    for c in unit_fixtures():
        r = measure(c, cap, args.trim)
        rows.append(r)
        print(fmt(r))

    if not args.no_art:
        print()
        art = art_cases(default_art())
        print(HDR)
        print("-" * len(HDR))
        for c in art:
            r = measure(c, cap, args.trim)
            rows.append(r)
            print(fmt(r))

    print("\n# --- agreement, ribbon vs each arm ---")
    print(f"  {'arm':<6} {'all shapes':>18} {'real artwork only':>22}")
    art_rows = [r for r in rows if r["case"].truth is None]
    for arm in ALL_ARMS:
        a = sum(1 for r in rows if r["ribbon"] == r[arm])
        b = sum(1 for r in art_rows if r["ribbon"] == r[arm])
        print(f"  {arm:<6} agree {a:3d}/{len(rows):<3d} dis {len(rows)-a:<3d}"
              f"   agree {b:3d}/{len(art_rows):<3d} dis {len(art_rows)-b}")

    truth_rows = [r for r in rows if r["case"].truth]
    print(f"\n# --- confusion vs stated truth ({len(truth_rows)} adjudicated "
          f"shapes), satin = positive ---")
    print("  FN (fill where satin was right) is the expensive direction: a "
          "lumpy scribble in lettering.")
    print(f"  {'arm':<8} {'TP':>3} {'FP':>3} {'TN':>3} {'FN':>3}")
    for arm in ["ribbon", *ALL_ARMS]:
        m = confusion(rows, arm)
        wrong = m["FP"] + m["FN"]
        print(f"  {arm:<8} {m['TP']:3d} {m['FP']:3d} {m['TN']:3d} {m['FN']:3d}"
              f"   wrong {wrong}/{len(truth_rows)}")

    if args.ablate:
        print("\n# --- per-shape misses, by arm ---")
        for arm in ["ribbon", *ALL_ARMS]:
            bad = [r["case"].name for r in truth_rows
                   if r[arm] != (r["case"].truth == "satin")]
            print(f"  {arm:<5} {len(bad):2d}  {', '.join(bad) if bad else '(none)'}")
        print("\n# --- does `mu > max/2` ever change a verdict? "
              "(R2 vs R2n, the note's open question) ---")
        diff = [r["case"].name for r in rows if r["R2"] != r["R2n"]]
        print(f"  {len(diff)} shapes of {len(rows)}: "
              f"{', '.join(diff) if diff else '(none — the term is redundant here)'}")

    if args.render:
        out = ROOT / "debug_out" / "shape_lens"
        total = 0
        for arm in ALL_ARMS:
            total += render_disagreements(rows, "ribbon", arm, out)
        print(f"\n# wrote {total} disagreement renders to {out}")


# --- The professional corpus, as referee ----------------------------------
#
# A human digitizer already made the satin-vs-fill call on every region of
# every file in `scratch_corpus/`. Their verdict is recoverable from the
# stitch DYNAMICS (a satin run reverses on nearly every stitch; a fill run
# runs long and turns rarely), while both classifiers under test read the
# GEOMETRY those stitches cover. Different evidence, same question — which is
# what makes it a referee and not a mirror.

_MM = 0.1  # pystitch units are 0.1 mm


def pro_runs(path: Path) -> list[list[tuple[float, float]]]:
    """Needle-down point strings between lifts. Own decode, own loop."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        return []
    out, cur = [], []
    for x, y, c in pat.stitches:
        if (c & pystitch.COMMAND_MASK) == pystitch.STITCH:
            cur.append((x * _MM, y * _MM))
            continue
        if len(cur) >= 3:
            out.append(cur)
        cur = []
    if len(cur) >= 3:
        out.append(cur)
    return out


def pro_verdict(pts: list[tuple[float, float]]) -> str | None:
    """-> "satin" | "fill" | None, from how the needle moved.

    A satin column reverses direction at nearly every penetration because it
    is crossing a band; a tatami fill runs a long row then turns once. The
    reversal fraction separates them without ever looking at the shape. Runs
    that are neither (locks, travels, bean runs) return None and are dropped
    rather than guessed at.
    """
    seg = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    seg = [s for s in seg if math.hypot(*s) > 1e-9]
    if len(seg) < 12:
        return None
    lens = sorted(math.hypot(*s) for s in seg)
    med = lens[len(lens) // 2]
    rev = sum(1 for a, b in zip(seg, seg[1:])
              if (a[0] * b[0] + a[1] * b[1])
              / (math.hypot(*a) * math.hypot(*b)) < -0.2)
    frac = rev / (len(seg) - 1)
    if frac >= 0.70 and med >= 0.7:
        return "satin"
    if 0.02 <= frac <= 0.45 and med >= 1.5:
        return "fill"
    return None


def pro_shapes(pts: list[tuple[float, float]], px_per_mm: float = 20.0,
               thread_mm: float = machine.SATIN_SPACING_MM,
               simplify_mm: float = 0.2, travel_mm: float = 4.0,
               min_area_mm2: float = 2.0) -> list[Polygon]:
    """The patches of fabric a run actually covered, one polygon per shape.

    **The reconstruction is the hard part and the first version of it was
    wrong.** Tracing each needle-down segment as a 1 px line and closing the
    gaps produced a band whose boundary was serrated at the stitch pitch; the
    medial axis of that band is a starburst of spurs, sigma/mu came out at
    0.6-1.0 on obvious satin, and every variance arm scored 100% false
    negatives. The instrument was measuring its own closing kernel. Looking at
    four rendered masks is what caught it — the confusion matrix alone read
    like a real result.

    What fixes it is physical rather than cosmetic: thread has WIDTH. Each
    segment is stroked at the thread's own width, which is what actually
    covers the fabric, and the recovered contour is then simplified at the
    same 0.2 mm stage 4 uses on artwork — so the polygon under test has the
    same boundary regularity as the polygons the engine really classifies.
    Both classifiers see the same reconstruction, so any residual error is
    shared.

    **One run is not one shape, and that was the second thing this got wrong.**
    A professional satins a whole word without lifting the needle, travelling
    letter to letter on long stitches, so the first version returned the
    largest contour of an entire word: `pro=satin` rows came back with
    `dtmax` of 14, 17, 21 mm, which is the height of the lettering, not the
    width of a stroke. Segments longer than `travel_mm` are therefore dropped
    before rasterising — inside a column or a fill row, a stitch that long is
    a travel wearing a stitch's clothes — and EVERY connected component that
    survives is returned as its own shape.

    Fidelity is still unproven against the digitizer's original artwork, which
    nobody has. Treat this population as a smoke test on real geometry, not as
    ground truth.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs) - 1.0, min(ys) - 1.0
    w = int((max(xs) - x0 + 1.0) * px_per_mm) + 2
    h = int((max(ys) - y0 + 1.0) * px_per_mm) + 2
    if w < 8 or h < 8 or w > 4000 or h > 4000:
        return []
    img = np.zeros((h, w), np.uint8)
    th = max(1, int(round(thread_mm * px_per_mm)))
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > travel_mm:
            continue
        cv2.line(img, (int((a[0] - x0) * px_per_mm), int((a[1] - y0) * px_per_mm)),
                 (int((b[0] - x0) * px_per_mm), int((b[1] - y0) * px_per_mm)),
                 255, th, cv2.LINE_8)
    cs, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out: list[Polygon] = []
    for c in cs:
        c = cv2.approxPolyDP(c, simplify_mm * px_per_mm, True)
        if len(c) < 4:
            continue
        ring = [(x0 + p[0][0] / px_per_mm, y0 + p[0][1] / px_per_mm) for p in c]
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if isinstance(poly, Polygon) and poly.area >= min_area_mm2:
            out.append(poly)
    return out


def cmd_corpus(args) -> None:
    cap = args.cap or machine.SATIN_MAX_WIDTH_MM
    files = sorted(Path(args.dir).glob("*.dst"))
    if not files:
        raise SystemExit(f"no .dst under {args.dir}")
    print(f"# {len(files)} professional files, cap {cap} mm\n")

    counts = {a: {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
              for a in ["ribbon", *ALL_ARMS]}
    n_runs = n_used = 0
    flips: list[tuple[str, str, dict]] = []
    for f in files:
        for pts in pro_runs(f):
            n_runs += 1
            want = pro_verdict(pts)
            if want is None:
                continue
            for poly in pro_shapes(pts):
                n_used += 1
                mask, scale = mask_of(poly)
                s = dt_stats(mask, scale, trim=0)
                preds = {"ribbon": arm_ribbon(poly, cap)}
                for nm, fn in DT_ARMS.items():
                    preds[nm] = fn(s, cap)
                for nm, fn in HYBRID_ARMS.items():
                    preds[nm] = fn(poly, s, cap)
                for nm, p in preds.items():
                    counts[nm]["TP" if (p and want == "satin") else
                               "FP" if p else
                               "FN" if want == "satin" else "TN"] += 1
                if preds["ribbon"] != preds[args.against]:
                    flips.append((f.name, want, {
                        "2A/P": ribbon_width_mm(poly), "dtmax": s.max_width_mm,
                        "dtp90": 2 * s.p90 / s.scale,
                        "sd/mu": s.sd / s.mu if s.mu else 0,
                        "ribbon": preds["ribbon"],
                        args.against: preds[args.against]}))

    print(f"# {n_runs} needle-down runs, {n_used} adjudicated by the pro's own "
          f"stitch structure\n")
    print("#" + "=" * 74)
    print("# THIS MATRIX IS NOT GROUND TRUTH. DO NOT QUOTE IT AS ONE.")
    print("# The unit of analysis is wrong and cannot be fixed from stitch")
    print("# data alone: in a script face the letters TOUCH, so the connected")
    print("# region a satin run covers is the whole word. Rendering three")
    print("# `pro=satin` shapes from bridesman.dst returns the word")
    print("# \"Bridesm\" at 38x40, 42x44 and 55x38 mm. Every arm here, ours")
    print("# included, is being asked to give ONE verdict for a whole word,")
    print("# which is not the operation the digitizer performed. Both")
    print("# classifiers score badly and neither score means anything.")
    print("# Kept because the population is real geometry and the failure is")
    print("# the finding: per-shape classification is the wrong question for")
    print("# connected lettering — the shape has to be decomposed first.")
    print("#" + "=" * 74 + "\n")
    print(f"  {'arm':<8} {'TP':>5} {'FP':>5} {'TN':>5} {'FN':>5}   "
          f"{'wrong':>6}  {'FN rate':>8}")
    for nm in ["ribbon", *ALL_ARMS]:
        m = counts[nm]
        tot = sum(m.values())
        pos = m["TP"] + m["FN"]
        print(f"  {nm:<8} {m['TP']:5d} {m['FP']:5d} {m['TN']:5d} {m['FN']:5d}   "
              f"{m['FP']+m['FN']:5d}   {100*m['FN']/max(pos,1):7.2f}%")

    print(f"\n# where ribbon and {args.against} disagree "
          f"({len(flips)} of {n_used}):")
    for name, want, d in flips[:args.show]:
        print(f"  {name:<26} pro={want:<5} 2A/P {d['2A/P']:5.2f} "
              f"dtmax {d['dtmax']:5.2f} dtp90 {d['dtp90']:5.2f} "
              f"sd/mu {d['sd/mu']:5.3f}  ribbon="
              f"{'satin' if d['ribbon'] else 'fill':<5} "
              f"{args.against}={'satin' if d[args.against] else 'fill'}")
    if len(flips) > args.show:
        print(f"  ... {len(flips)-args.show} more")


def cmd_taper(args) -> None:
    """Sweep a wedge's taper ratio and find where `2*sigma < mu` gives up.

    Closed form, for the wedge whose width runs linearly a -> b along a spine:
    the DT at skeletal pixels is uniform on [a/2, b/2], so mu = (a+b)/4 and
    sigma = (b-a)/(4*sqrt(3)). `2*sigma < mu` reduces to `b < (2+sqrt(3))^2 * a`,
    i.e. **b/a < 13.93**. Every taper gentler than about 14:1 is
    "predominantly regular" no matter how much the width varies.

    That is the opposite of what the variance rule is advertised to do, so it
    gets measured on rasters rather than asserted from the algebra.
    """
    cap = args.cap or machine.SATIN_MAX_WIDTH_MM
    print(f"# wedge, 30 mm long, narrow end 1.0 mm, cap {cap} mm")
    print(f"# closed form says `2*sigma < mu` holds until b/a = "
          f"{(2 + math.sqrt(3))**2:.2f}\n")
    print(f"{'b/a':>6} {'wide end':>9} {'2A/P':>6} {'dtmax':>6} {'dtp90':>6} "
          f"{'dtmu':>6} {'sd/mu':>6} {'2s<m':>5}  {'rib':>4} {'VAR':>4} "
          f"{'P90':>4} {'MIN':>4}")
    b = lambda v: " Y" if v else " ."  # noqa: E731
    for ratio in (1, 1.5, 2, 3, 4, 6, 8, 10, 12, 13, 14, 16, 20, 30, 50):
        wide = 1.0 * ratio
        poly = _wedge(1.0, wide, 30.0)
        m, sc = mask_of(poly)
        s = dt_stats(m, sc, trim=0)
        print(f"{ratio:6.1f} {wide:8.1f}mm {ribbon_width_mm(poly):6.2f} "
              f"{s.max_width_mm:6.2f} {2*s.p90/s.scale:6.2f} "
              f"{s.mean_width_mm:6.2f} {(s.sd/s.mu if s.mu else 0):6.3f} "
              f"{b(s.regular):>5}  {b(arm_ribbon(poly, cap)):>4} "
              f"{b(arm_VAR(poly, s, cap)):>4} {b(arm_P90(poly, s, cap)):>4} "
              f"{b(arm_MIN(poly, s, cap)):>4}")


def cmd_timing(args) -> None:
    """What the DT+skeleton pass costs against the pipeline it would join."""
    from digitizer_core import PipelineConfig, run_stages
    cap = args.cap or machine.SATIN_MAX_WIDTH_MM
    path = ROOT / "testdata" / "logo_whitebg.png"
    reps = args.reps

    t = []
    for _ in range(reps):
        t0 = time.perf_counter()
        res = run_stages(path, PipelineConfig(target_width_mm=80.0))
        t.append(time.perf_counter() - t0)
    stages14 = min(t)
    polys = [r.polygon for r in res.regions]
    print(f"stages 1-4, {path.name} @80mm, best of {reps}: {stages14*1000:8.1f} ms "
          f"({len(polys)} regions)")

    t = []
    for _ in range(reps):
        t0 = time.perf_counter()
        for p in polys:
            is_satin_candidate(p, cap)
        t.append(time.perf_counter() - t0)
    cur = min(t)
    print(f"  current classify (2A/P + aspect), all regions:  {cur*1000:8.3f} ms "
          f"= {100*cur/stages14:6.3f}% of stages 1-4")

    gated = [p for p in polys if is_satin_candidate(p, cap)]
    for res_px in (6.0, LENS_PX_PER_MM):
        for label, subset in (("ALL regions (DT-first)", polys),
                              ("only regions the current rule already "
                               "calls satin", gated)):
            t = []
            for _ in range(reps):
                t0 = time.perf_counter()
                for p in subset:
                    m, sc = mask_of(p, res_px)
                    dt_stats(m, sc, trim=0)
                t.append(time.perf_counter() - t0)
            dtc = min(t)
            print(f"  DT @{res_px:4.1f} px/mm, {label:<52} "
                  f"{dtc*1000:8.2f} ms = {100*dtc/stages14:7.3f}% of stages 1-4")

    # Stage 6 already runs `medial_axis` on every shape it satins. The arms
    # that ADD a term to the current rule only ever need the field on shapes
    # the current rule already accepted — so that work is not new, it is work
    # moved earlier. Say the split out loud; the ALL-regions number above is
    # the cost of a real DT-FIRST restructure and it is not the same number.
    print(f"  of {len(polys)} regions, {len(gated)} pass the current rule and "
          f"already pay for a medial axis in stage 6;")
    print(f"  {len(polys)-len(gated)} would be NEW work under a DT-first "
          f"restructure, and 0 under the add-a-term arms.")

    print("\n# resolution sensitivity — does the verdict depend on the grid?")
    print(f"  {'shape':<26} " + " ".join(f"{f'p90@{r:g}':>9}"
                                         for r in (6.0, 10.0, 20.0, 30.0)))
    for p, reg in zip(polys, res.regions):
        vals = []
        for r_px in (6.0, 10.0, 20.0, 30.0):
            m, sc = mask_of(p, r_px)
            s = dt_stats(m, sc, trim=0)
            vals.append(2 * s.p90 / s.scale)
        print(f"  {reg.shape_id:<26} " + " ".join(f"{v:9.3f}" for v in vals)
              + f"   spread {max(vals)-min(vals):.3f} mm")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dt", help="the classifier table")
    d.add_argument("--cap", type=float, default=None,
                   help=f"satin width cap mm (default {machine.SATIN_MAX_WIDTH_MM})")
    d.add_argument("--trim", default="0",
                   help="endpoint peel: an int, or R for max-radius. Default 0 "
                        "— the note says R and R measures worse; see "
                        "trim_endpoints")
    d.add_argument("--ablate", action="store_true", help="per-shape miss lists")
    d.add_argument("--render", action="store_true",
                   help="write PNGs of every ribbon-vs-DT disagreement")
    d.add_argument("--no-art", action="store_true", help="fixtures only")
    d.set_defaults(fn=cmd_dt)

    c = sub.add_parser("corpus", help="score every arm against professional files")
    c.add_argument("dir", help="directory of .dst files (scratch_corpus/)")
    c.add_argument("--cap", type=float, default=None)
    c.add_argument("--against", default="VP90", choices=list(ALL_ARMS),
                   help="which arm to list ribbon's disagreements with")
    c.add_argument("--show", type=int, default=25)
    c.set_defaults(fn=cmd_corpus)

    w = sub.add_parser("taper", help="where the variance rule gives up")
    w.add_argument("--cap", type=float, default=None)
    w.set_defaults(fn=cmd_taper)

    t = sub.add_parser("timing", help="cost against stages 1-4")
    t.add_argument("--cap", type=float, default=None)
    t.add_argument("--reps", type=int, default=5)
    t.set_defaults(fn=cmd_timing)

    args = ap.parse_args()
    if args.cmd == "dt" and args.trim != "R":
        args.trim = int(args.trim)
    args.fn(args)


if __name__ == "__main__":
    main()
