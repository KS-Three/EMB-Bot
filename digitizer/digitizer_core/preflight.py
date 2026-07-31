"""Preflight — what will go wrong on the machine, said BEFORE the hoop moves.

A scoring pass over a FINISHED plan. It consumes what `digitize` produced —
the `PipelineResult`, the `StitchPlan`, the config that shaped them, and
optionally the artwork itself — and returns structured findings. It never
changes the plan: every check here reads geometry the planner already
committed to, because the operator's question is "should I sew this file",
not "how should it have been sewn".

Each finding is {code, severity, message, extra}. Severity means:
  * "info"  — worth knowing, sew anyway.
  * "warn"  — will cost machine time or quality; look before sewing.
  * "block" — will visibly go wrong; resolve it or get sign-off first.
The message is written for the person at the machine: sentence case, says
what to DO, never engine vocabulary.

Every threshold is a measurement, cited next to its constant. The
instruments were validated on known-clean fixtures first (probe run
2026-07-31): the fixture logo and the curved ribbon produce ZERO findings,
because a metric that flags clean work trains the operator to ignore the
report — the exact failure a past fan metric had when it scored a clean
ribbon 30%.

Codes are defined HERE, not in warnings_codes.py — that file is owned by
another lane this round. They follow its contract exactly (append-only
machine-readable strings, UI switches on codes never prose) and may migrate
there at merge.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000

from . import machine, stitches
from .config import PipelineConfig
from .pipeline import PipelineResult, fabric_for
from .stage1_prep import prep
from .stitches import StitchPlan
from .threads import chart_for, rgb_to_lab

# --- Codes (may migrate to warnings_codes.py at merge) ---------------------

THREAD_MATCH_POOR = "THREAD_MATCH_POOR"        # extra: {thread_number, thread_name, brand_id, delta_e, artwork_rgb, thread_rgb}
LETTERING_TOO_SMALL = "LETTERING_TOO_SMALL"    # extra: {count, shapes: [{shape_id, column_mm, extent_mm}]}
STITCHES_TOO_LONG = "STITCHES_TOO_LONG"        # extra: {count, max_mm}
STITCHES_TOO_SHORT = "STITCHES_TOO_SHORT"      # extra: {fraction, count, total}
TRIM_HEAVY = "TRIM_HEAVY"                      # extra: {per_1000, trims, stitches}
DENSITY_EXTREME = "DENSITY_EXTREME"            # extra: {kind, measured_mm, target_mm, ratio}

# --- Thresholds, each with its measurement ---------------------------------

# CIEDE2000 color difference. The JND sits near 1.0; the practical scale in
# Mokrzycki & Tatol 2011 ("Colour difference deltaE — a survey") reads 2-3.5
# as noticeable to an average observer, 3.5-5 as a clear difference, and
# above 5 as two different colors. Measured against our own charts: Isacord's
# worst match on the fixture logo is 4.4 (an honest "no spool is that exact
# red", not a defect), while Madeira Rayon's nearest to the same art's purple
# is 10.7 by this instrument (12.2 by the step-8 probe against the cluster
# center) — the motivating case, visibly a different color and previously
# silent. 5.0 separates those two worlds cleanly.
DELTA_E_VISIBLE = 5.0
# Twice the "two different colors" line: nobody argues the substitution is
# fine at this distance, so it escalates from warn to block.
DELTA_E_CLEARLY_DIFFERENT = 10.0

# Sewable lettering size. House sew-out fact (2026-07-22 flatten validation):
# stacked text below ~4 mm cap height dies at hat scale. Wilcom's Hatch fonts
# ship recommended ranges bottoming at 5 mm for run fonts and ~7 mm for satin
# fonts, so 4 mm is already the generous end. Measured on the benchmark logo:
# at 90 mm no shape trips this, at 55 mm one marginal letter does, at 40 mm
# nine of thirteen do — which matches how those sizes actually sew.
MIN_LETTER_EXTENT_MM = 4.0
# A satin column narrower than the needle minimum: every cross re-enters the
# previous hole's neighborhood and the stroke reads as a scar, not a line.
MIN_COLUMN_MM = machine.MIN_STITCH_MM

# Fraction of satin stitches under MIN_STITCH_MM. The benchmark logo measured
# 54.6% before the zigzag-order fix and 10.4% after (re-measured 9.9% by this
# instrument); clean fixtures sit at 1-3%. A plan back above 25% — halfway to
# the broken world — is a regression, not a style.
SATIN_SHORT_FRACTION_MAX = 0.25

# Trims per 1,000 stitches across the 39-file professional corpus: median
# 0.8, range 0.1-4.1 (docs/pro-digitizing-playbook.md, law 1). Above the top
# of the observed professional range, the machine spends real time cutting.
TRIMS_PER_1000_MAX = 4.1

# Emitted density vs the planner's own target. 1.5x either way is past any
# fabric preset's adjustment and means the geometry diverged from intent —
# gapping (too sparse) or fabric bunching (too dense) on the machine.
DENSITY_RATIO_MAX = 1.5

# Below this many samples a median is an anecdote; the metric stays silent
# rather than judging a design on a handful of stitches.
_MIN_SAMPLES = 30

# Sampled artwork pixels needed before a thread's color is judged. A region
# smaller than this is mostly anti-alias boundary and the median is noise.
_MIN_COLOR_PIXELS = 50

# Score deductions. A block is most of a letter grade on its own; two warns
# cost one. Grades: A >= 90, B >= 75, C >= 60, D >= 40, F below.
_DEDUCT = {"info": 0, "warn": 12, "block": 30}


def finding(code: str, severity: str, message: str, **extra) -> dict:
    """Same shape as warnings_codes.warn, plus severity — one report row."""
    out = {"code": code, "severity": severity, "message": message}
    if extra:
        out["extra"] = extra
    return out


# --- Thread color fidelity --------------------------------------------------

def _artwork_colors_by_thread(image, result: PipelineResult,
                              cfg: PipelineConfig) -> dict[int, np.ndarray]:
    """-> {thread_index: median artwork RGB under that thread's regions}.

    The pipeline does not carry the pre-snap cluster colors into its result,
    so the artwork is re-read through stage 1 (same config, deterministic,
    same alignment) and each region polygon is rasterized back over it.
    Region coordinates are mm with origin at the artwork bbox CENTER, y-down
    — the exact inverse of the transform stage 4 applied — so px = mm *
    px_per_mm + center. The mask is eroded one pixel and the color taken as
    the per-channel MEDIAN: both choices exist to keep anti-alias halo pixels
    from dragging a flat color toward the background.
    """
    p = prep(image, cfg)
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h, w = p.rgb.shape[:2]

    chunks: dict[int, list[np.ndarray]] = {}
    for r in result.regions:
        mask = np.zeros((h, w), np.uint8)

        def to_px(coords) -> np.ndarray:
            a = np.asarray(coords, np.float64)
            return np.column_stack(
                [a[:, 0] * p.px_per_mm + cx, a[:, 1] * p.px_per_mm + cy]
            ).astype(np.int32)

        cv2.fillPoly(mask, [to_px(r.polygon.exterior.coords)], 1)
        for ring in r.polygon.interiors:
            cv2.fillPoly(mask, [to_px(ring.coords)], 0)
        eroded = cv2.erode(mask, np.ones((3, 3), np.uint8))
        sel = (eroded > 0) & (~p.bg_mask)
        if not sel.any():
            sel = (mask > 0) & (~p.bg_mask)   # hairline shape: erosion ate it
        if sel.any():
            chunks.setdefault(r.thread_index, []).append(p.rgb[sel].reshape(-1, 3))

    out: dict[int, np.ndarray] = {}
    for t, parts in chunks.items():
        px = np.concatenate(parts)
        if len(px) >= _MIN_COLOR_PIXELS:
            out[t] = np.median(px, axis=0)
    return out


def _thread_match_findings(image, result: PipelineResult,
                           cfg: PipelineConfig) -> tuple[list[dict], float | None]:
    """One finding per thread whose spool is visibly off its artwork color.

    Distance is CIEDE2000 on CIELAB from skimage's rgb2lab on [0, 1] floats
    — the pinned house convention (threads.py), never cv2's 8-bit Lab.
    """
    chart = chart_for(cfg)
    findings: list[dict] = []
    worst: float | None = None
    for t, art_rgb in sorted(_artwork_colors_by_thread(image, result, cfg).items()):
        lab_art = rgb_to_lab(art_rgb.reshape(1, 3))
        lab_thr = rgb_to_lab(np.asarray(chart[t].rgb, np.float64).reshape(1, 3))
        de = float(deltaE_ciede2000(lab_art, lab_thr)[0])
        worst = de if worst is None else max(worst, de)
        if de <= DELTA_E_VISIBLE:
            continue
        thread = chart[t]
        clearly = de > DELTA_E_CLEARLY_DIFFERENT
        what = "is clearly a different color than" if clearly else "is visibly off"
        findings.append(finding(
            THREAD_MATCH_POOR,
            "block" if clearly else "warn",
            f"{chart.label} {thread.number} ({thread.name}) {what} "
            f"the artwork it sews. Pick a closer thread or a different "
            f"brand before sewing.",
            brand_id=chart.id,
            thread_number=thread.number,
            thread_name=thread.name,
            delta_e=round(de, 1),
            artwork_rgb=[int(v) for v in art_rgb],
            thread_rgb=list(thread.rgb),
        ))
    return findings, worst


# --- Lettering size ---------------------------------------------------------

def _lettering_findings(plan: StitchPlan) -> tuple[list[dict], int]:
    """Satin shapes below sewable lettering size, aggregated to one finding.

    Column width is the median consecutive-step distance inside the shape's
    SATIN runs — every consecutive pair of an emitted zigzag crosses the
    column (the return leg leans one 0.4 mm spacing forward, which inflates a
    0.9 mm column to 0.99; negligible). Never sliced at fixed parity — the
    playbook's parity trap. "Too small overall" is the LARGER bbox dimension
    under 4 mm: a shape that fits entirely inside a 4 mm box is below
    lettering scale in any orientation, while a long thin dash (4 x 1 mm,
    perfectly sewable) stays out of the net.
    """
    widths: dict[str, list[float]] = {}
    pts_by_shape: dict[str, list[tuple[float, float]]] = {}
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN:
            continue
        for a, b in zip(run.points, run.points[1:]):
            widths.setdefault(run.shape_id, []).append(math.dist(a, b))
        pts_by_shape.setdefault(run.shape_id, []).extend(run.points)

    small: list[dict] = []
    for sid, ws in sorted(widths.items()):
        ws.sort()
        med = ws[len(ws) // 2]
        xs = [p[0] for p in pts_by_shape[sid]]
        ys = [p[1] for p in pts_by_shape[sid]]
        extent = max(max(xs) - min(xs), max(ys) - min(ys))
        if med < MIN_COLUMN_MM or extent < MIN_LETTER_EXTENT_MM:
            small.append({"shape_id": sid, "column_mm": round(med, 2),
                          "extent_mm": round(extent, 1)})
    if not small:
        return [], len(widths)
    n = len(small)
    noun = "shape" if n == 1 else "shapes"
    return [finding(
        LETTERING_TOO_SMALL,
        "warn",
        f"{n} satin {noun} sew below readable size at this scale — columns "
        f"under {MIN_COLUMN_MM:g} mm or details under "
        f"{MIN_LETTER_EXTENT_MM:g} mm. Enlarge the design or remove the "
        "smallest lettering.",
        count=n,
        shapes=small,
    )], len(widths)


# --- Stitch length ----------------------------------------------------------

def _stitch_length_findings(plan: StitchPlan) -> tuple[list[dict], dict]:
    """The format ceiling as a backstop, and the satin-short fraction.

    A plan should never contain a needle-down step past MAX_STITCH_MM — the
    planner splits them at the source — so any count here is a regression
    report, not a normal state. The short fraction is a quality score even
    when it stays under threshold; it rides out in the metrics.
    """
    too_long = 0
    longest = 0.0
    satin_total = satin_short = 0
    for _b, run in plan.iter_runs():
        for a, b in zip(run.points, run.points[1:]):
            d = math.dist(a, b)
            if d > machine.MAX_STITCH_MM + 1e-6:
                too_long += 1
                longest = max(longest, d)
            if run.kind == stitches.SATIN:
                satin_total += 1
                if d < machine.MIN_STITCH_MM:
                    satin_short += 1

    findings: list[dict] = []
    if too_long:
        noun = "stitch" if too_long == 1 else "stitches"
        findings.append(finding(
            STITCHES_TOO_LONG,
            "warn",
            f"{too_long} {noun} exceed the {machine.MAX_STITCH_MM:g} mm "
            "machine ceiling. Export splits them so the file will run, but "
            "the plan should not contain them — re-run digitizing and "
            "report this design.",
            count=too_long,
            max_mm=round(longest, 2),
        ))
    frac = satin_short / satin_total if satin_total else 0.0
    if satin_total >= _MIN_SAMPLES and frac > SATIN_SHORT_FRACTION_MAX:
        findings.append(finding(
            STITCHES_TOO_SHORT,
            "warn",
            f"{frac:.0%} of satin stitches are under the "
            f"{machine.MIN_STITCH_MM:g} mm needle minimum (a healthy plan "
            "runs about 10%). Thread breaks are likely — enlarge the design "
            "or thicken its thinnest strokes.",
            fraction=round(frac, 3),
            count=satin_short,
            total=satin_total,
        ))
    return findings, {"satin_short_fraction": round(frac, 3),
                      "satin_steps": satin_total}


# --- Trims ------------------------------------------------------------------

def _trim_findings(plan: StitchPlan) -> tuple[list[dict], float]:
    """Trims per 1,000 stitches against the professional corpus.

    The plan marks the first run of every color block as trimmed, but the
    first block of the design has no thread to cut yet, so the FILE contains
    one trim fewer than plan.stats reports (the same correction the service's
    stats payload makes). The rate uses what the machine will actually do.
    """
    s = plan.stats
    first = plan.blocks[0].runs[0] if plan.blocks and plan.blocks[0].runs else None
    trims = s.trims - (1 if first is not None and first.trim else 0)
    per_1000 = 1000.0 * trims / s.stitch_count if s.stitch_count else 0.0
    if per_1000 <= TRIMS_PER_1000_MAX or s.stitch_count < _MIN_SAMPLES:
        return [], per_1000
    return [finding(
        TRIM_HEAVY,
        "warn",
        f"{per_1000:.1f} trims per 1,000 stitches — professional files run "
        "0.1 to 4.1. Each cut is 2-3 seconds of machine time; consider "
        "merging or removing the smallest shapes.",
        per_1000=round(per_1000, 1),
        trims=trims,
        stitches=s.stitch_count,
    )], per_1000


# --- Density ----------------------------------------------------------------

def _fill_row_advance_mm(plan: StitchPlan) -> float | None:
    """Median row-to-row advance of the emitted fill, or None without fill.

    A fill run is rows along one dominant axis with short turns between
    them. Each run's axis is recovered from its own steps (length-weighted
    axial mean — the angle-doubling trick, so a boustrophedon's opposite
    row directions reinforce instead of cancelling); a step within 45 deg of
    that axis is sewing along a row, anything else is a transition, and the
    transition's component PERPENDICULAR to the axis is the row advance. Two
    subtleties, both measured: the raw transition step is NOT the spacing
    (row ends ride the shape's edge — on a slanted edge it runs diagonally,
    median 1.07 mm on the fixture, nearly 3x the true 0.40), and comparing
    against the PREVIOUS step instead of the axis double-counts the first
    step of every row as a turn, which on a synthetic grid put the median on
    the wrong population entirely. Against the axis, the clean fixture reads
    0.400 mm on the 0.40 target. Median only — the tail holds column
    transitions and row skips, which are routing, not density.
    """
    adv: list[float] = []
    for _b, run in plan.iter_runs():
        if run.kind != stitches.FILL:
            continue
        pts = run.points
        if len(pts) < 3:
            continue
        # Length-weighted axial mean of the step directions.
        sx = sy = 0.0
        steps: list[tuple[float, float, float]] = []
        for a, b in zip(pts, pts[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy)
            if d < 1e-9:
                continue
            ang = math.atan2(dy, dx)
            sx += d * math.cos(2 * ang)
            sy += d * math.sin(2 * ang)
            steps.append((dx, dy, d))
        if not steps:
            continue
        axis = math.atan2(sy, sx) / 2.0
        ax, ay = math.cos(axis), math.sin(axis)
        for dx, dy, d in steps:
            if abs(dx * ax + dy * ay) / d >= math.cos(math.radians(45)):
                continue  # along a row
            perp = abs(dx * (-ay) + dy * ax)
            if perp > 1e-6:
                adv.append(perp)
    if len(adv) < _MIN_SAMPLES:
        return None
    adv.sort()
    return adv[len(adv) // 2]


def _satin_rail_advance_mm(plan: StitchPlan) -> float | None:
    """Median same-rail advance of the emitted satin, or None without satin.

    Rails alternate A, B, A, B ... so two apart is the same rail — measured
    two-apart, never sliced at fixed parity (the playbook's parity trap).
    """
    adv: list[float] = []
    for _b, run in plan.iter_runs():
        if run.kind != stitches.SATIN:
            continue
        pts = run.points
        for i in range(len(pts) - 2):
            adv.append(math.dist(pts[i], pts[i + 2]))
    if len(adv) < _MIN_SAMPLES:
        return None
    adv.sort()
    return adv[len(adv) // 2]


def _density_findings(plan: StitchPlan,
                      cfg: PipelineConfig) -> tuple[list[dict], dict]:
    """Emitted density against the planner's own targets.

    The fill target mirrors stage 7's exact formula — (cfg.fill_row_mm or
    machine default) scaled by the fabric preset — so a deliberate density
    override or a towel preset never trips this. What trips it is the
    emitted geometry diverging from what the pipeline itself intended:
    beyond 1.5x sparse the fabric grins through the rows, beyond 1.5x dense
    it puckers.
    """
    fabric = fabric_for(cfg)
    fill_target = (cfg.fill_row_mm or machine.FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    satin_target = machine.SATIN_SPACING_MM

    findings: list[dict] = []
    metrics: dict = {}
    for kind, measured, target in (
        ("fill", _fill_row_advance_mm(plan), fill_target),
        ("satin", _satin_rail_advance_mm(plan), satin_target),
    ):
        metrics[f"{kind}_advance_mm"] = None if measured is None else round(measured, 3)
        if measured is None:
            continue
        ratio = measured / target
        if 1.0 / DENSITY_RATIO_MAX <= ratio <= DENSITY_RATIO_MAX:
            continue
        way = ("looser: expect gaps in the coverage" if ratio > 1
               else "denser: expect the fabric to pucker")
        findings.append(finding(
            DENSITY_EXTREME,
            "warn",
            f"The {kind} stitching came out {ratio:.1f}x its "
            f"{target:.2f} mm density target, {way}. Check the density "
            "settings and re-digitize before sewing.",
            kind=kind,
            measured_mm=round(measured, 3),
            target_mm=round(target, 3),
            ratio=round(ratio, 2),
        ))
    return findings, metrics


# --- The report -------------------------------------------------------------

def run_preflight(result: PipelineResult, plan: StitchPlan,
                  cfg: PipelineConfig | None = None,
                  image=None) -> dict:
    """The full preflight report for one finished digitize() output.

    `image` is the same artwork `digitize` was given (path, bytes, or
    ndarray). It is optional because only the thread-match check needs it —
    everything else reads the plan — and a caller re-scoring a stored plan
    may no longer have the artwork. Without it the thread check is skipped
    and the report says so (`thread_match_checked`). `result` is likewise
    only read by the thread-match check, so a caller scoring a bare plan may
    pass None for both.

    Returns {"score", "grade", "findings", "metrics"} — every value a plain
    Python scalar/list/dict, safe to hand straight to a JSON boundary.
    """
    cfg = cfg or PipelineConfig()

    findings: list[dict] = []
    metrics: dict = {}

    worst_de: float | None = None
    if image is not None:
        thread_findings, worst_de = _thread_match_findings(image, result, cfg)
        findings.extend(thread_findings)
    metrics["thread_match_checked"] = image is not None
    metrics["thread_worst_delta_e"] = None if worst_de is None else round(worst_de, 1)

    lettering, satin_shape_count = _lettering_findings(plan)
    findings.extend(lettering)
    metrics["satin_shapes"] = satin_shape_count

    length_findings, length_metrics = _stitch_length_findings(plan)
    findings.extend(length_findings)
    metrics.update(length_metrics)

    trim_findings, per_1000 = _trim_findings(plan)
    findings.extend(trim_findings)
    metrics["trims_per_1000"] = round(per_1000, 1)

    density_findings, density_metrics = _density_findings(plan, cfg)
    findings.extend(density_findings)
    metrics.update(density_metrics)

    metrics["stitch_count"] = plan.stats.stitch_count

    score = 100
    for f in findings:
        score -= _DEDUCT.get(f["severity"], 0)
    score = max(0, score)
    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 40 else "F")

    return {"score": score, "grade": grade,
            "findings": findings, "metrics": metrics}
