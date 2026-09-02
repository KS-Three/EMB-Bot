"""How far apart are the fill rows a machine actually sewed? Read from the path.

## Why this exists

The 2026-09-01 sew-out left exactly one claim unsettled, and it is the one
Kent actually complained about — fabric showing through. Two measurements of
the SAME file disagreed by a factor of two:

  * Reading A, the same night: 0.18-0.19 mm pitch, which retired the density
    story as a cause.
  * Reading B, later: a purpose-built estimator, calibrated against a known
    answer first, recovered 0.400 mm where 0.400 was the truth, then read
    0.400 mm median on `design.dst` with 0% of passes near 0.19.

Neither reading had a committed instrument. Reading B's was lost with its
session and existed on no ref after a `git fetch --all`. The project's own
rule out of that night is that "a pitch number quoted without a re-runnable
instrument is not evidence, whichever direction it points" — so this file is
that instrument, rebuilt to the method Reading B described.

## Why the answer matters beyond one sew-out

`machine.FILL_ROW_MM` is 0.40, and its own comment records that the corpus
splits into TWO POPULATIONS at ~0.20 mm: 29 freebie script files whose dense
reading is a satin crossing's half-step artifact and NOT a tatami row at all,
against 43 commissioned cap-logo files sewing a genuine ~0.19 mm area fill.
Which population our fills should match "is still unresolved". An instrument
that reads row pitch off a path is how a file gets assigned to a population
instead of argued about — including, very likely, Reading A, whose 0.18-0.19
is exactly where the satin artifact lives.

This measures. It does not set a constant, propose one, or grade anything:
ROADMAP gate 1 is untouched, and settling which population is right still
needs cloth.

## Method

Per needle-down PASS (a maximal run between lifts), not per design — a design
mixes fills, satins and runs, and averaging them answers nothing:

 1. Find the along-row direction from the path's own segment angles, taken mod
    180 deg and weighted by length. A tatami pass spends nearly all its length
    running along rows and only a step per turn crossing them, so the dominant
    angle IS the row direction.
 2. Project every penetration onto the perpendicular axis. Rows collapse to
    spikes spaced by the pitch.
 3. Autocorrelate that profile and take the first real peak. Autocorrelation
    rather than "average the turn-around steps" because it survives staggered
    starts, missed penetrations and rows of unequal length, and because it is
    the method the lost estimator used and calibrated.

## What it refuses to answer

A pass is scored only if it spans enough perpendicular width to hold several
rows and carries enough penetrations to see them. That is not defensive
padding: Reading B's own stated limit was that only 16 of roughly 1,700
needle-down passes on that file were wide enough to read, so it "speaks for
the substantial fills, not every small patch". Every report here carries its
readable/total ratio for the same reason — a median over three passes is not
the same claim as a median over three hundred.

## Calibration

`tests/test_fill_pitch.py` runs the engine at TWO different configured row
spacings and asserts this recovers each. Recovering one number proves little
(a stopped clock recovers 0.40); recovering two different ones proves the
instrument is reading the file rather than echoing a constant.

Usage (from digitizer/):
    .venv/bin/python tools/fill_pitch.py --image testdata/photo/enthusiast_logo.png
    .venv/bin/python tools/fill_pitch.py --dst path/to/design.dst
    ... [--width 80] [--row-mm 0.4] [--json out.json] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

# A pass must span at least this many multiples of the pitch it reports, or the
# "period" is a coincidence of two rows. Four gives three gaps to agree.
MIN_PERIODS = 4.0
# Below this many penetrations there is not enough profile to autocorrelate.
MIN_POINTS = 40
# The search window for a row pitch, in mm. The floor is under any plausible
# spacing (a needle cannot sew rows closer than the thread is wide); the
# ceiling is well past a coarse fill and short of any satin column width.
MIN_PITCH_MM = 0.08
MAX_PITCH_MM = 2.50
# Profile resolution. Fine enough for ~10 bins across the tightest pitch above.
BIN_MM = 0.01
# A peak must reach this share of the zero-lag energy to count as a period
# rather than profile noise.
PEAK_REL = 0.35


def _dominant_angle(points: np.ndarray) -> float | None:
    """The along-row direction, in radians, from length-weighted segment angles.

    Angles are doubled before averaging so that 179 deg and 1 deg -- the same
    line, opposite directions -- reinforce instead of cancelling. That is the
    standard axial-mean trick; without it a boustrophedon fill, which reverses
    direction every row, averages to nothing.
    """
    d = np.diff(points, axis=0)
    lengths = np.hypot(d[:, 0], d[:, 1])
    keep = lengths > 1e-9
    if not keep.any():
        return None
    d, lengths = d[keep], lengths[keep]
    ang2 = 2.0 * np.arctan2(d[:, 1], d[:, 0])
    x = float((lengths * np.cos(ang2)).sum())
    y = float((lengths * np.sin(ang2)).sum())
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None
    return 0.5 * math.atan2(y, x)


def _first_period(profile: np.ndarray, lo: int, hi: int) -> int | None:
    """First lag in [lo, hi] that is a real local maximum of the autocorrelation.

    Normalised by overlap count, so a long lag is not penalised for having
    fewer terms -- otherwise the first peak always wins by construction and
    the measure would be circular.
    """
    n = profile.size
    if hi >= n:
        hi = n - 1
    if lo > hi:
        return None
    p = profile - profile.mean()
    denom = float((p * p).sum())
    if denom <= 0:
        return None
    r = np.empty(hi + 1)
    for k in range(hi + 1):
        seg = float((p[: n - k] * p[k:]).sum())
        # Scale to what a full-length overlap would have given.
        r[k] = seg * (n / max(1, n - k))
    r /= denom
    best = None
    for k in range(max(lo, 1), hi):
        if r[k] >= r[k - 1] and r[k] >= r[k + 1] and r[k] >= PEAK_REL:
            best = k
            break
    return best


def pass_pitch_mm(points) -> dict | None:
    """Row pitch for ONE needle-down pass, or None if it cannot be read.

    Returning None is a real answer -- see "What it refuses to answer".
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < MIN_POINTS:
        return None
    theta = _dominant_angle(pts)
    if theta is None:
        return None
    # Perpendicular to the rows: this is the axis the pitch lives on.
    normal = np.array([-math.sin(theta), math.cos(theta)])
    s = pts @ normal
    span = float(s.max() - s.min())
    if span < MIN_PERIODS * MIN_PITCH_MM:
        return None
    nbins = int(round(span / BIN_MM)) + 1
    if nbins < 8:
        return None
    hist, _ = np.histogram(s, bins=nbins, range=(float(s.min()), float(s.max())))
    lag = _first_period(
        hist.astype(float),
        lo=int(round(MIN_PITCH_MM / BIN_MM)),
        hi=int(round(MAX_PITCH_MM / BIN_MM)),
    )
    if lag is None:
        return None
    pitch = lag * BIN_MM
    # The span test again, now against the pitch actually found: a 0.9 mm
    # "period" inside a 1.2 mm pass is two rows and a guess.
    if span < MIN_PERIODS * pitch:
        return None
    return {"pitch_mm": round(pitch, 4), "span_mm": round(span, 2),
            "points": int(pts.shape[0]), "angle_deg": round(math.degrees(theta) % 180.0, 1)}


def _summarise(passes: list, label: str) -> dict:
    read = [p for p in (pass_pitch_mm(pp) for pp in passes) if p]
    out = {
        "source": label,
        "passes_total": len(passes),
        "passes_read": len(read),
        "pitch_mm_median": None,
        "pitch_mm_p10": None,
        "pitch_mm_p90": None,
        "per_pass": read,
    }
    if read:
        vals = np.array([p["pitch_mm"] for p in read])
        out["pitch_mm_median"] = round(float(np.median(vals)), 4)
        out["pitch_mm_p10"] = round(float(np.percentile(vals, 10)), 4)
        out["pitch_mm_p90"] = round(float(np.percentile(vals, 90)), 4)
    return out


def passes_from_plan(plan) -> list:
    """Needle-down passes from one of our own plans.

    A run that is `jump` opens a new pass; everything after it up to the next
    lift belongs to that pass -- the same "maximal needle-down streak"
    definition tools/sequence_census.py uses, so the two tools count the same
    things.
    """
    passes, cur = [], []
    for _block, run in plan.iter_runs():
        if getattr(run, "jump", False) and cur:
            passes.append(cur)
            cur = []
        cur.extend(run.points)
    if cur:
        passes.append(cur)
    return passes


def passes_from_dst(path: Path) -> list:
    """Needle-down passes from a sewn DST, split on every lift.

    Read through pystitch, the same library `digitizer_core.export` uses --
    and note CLAUDE.md footgun 1: the BROWSER codec is transposed, so a file
    written by the Studio's own DST encoder reads rotated. Pitch is a distance
    and survives a rotation, but provenance still matters for anything else
    read off the same decode.
    """
    import pystitch

    with open(path, "rb") as fh:
        pattern = pystitch.read_dst(fh)
    passes, cur = [], []
    for st in pattern.stitches:
        x, y, cmd = st[0] / 10.0, st[1] / 10.0, st[2]
        if cmd == pystitch.STITCH:
            cur.append((x, y))
        else:
            if cur:
                passes.append(cur)
            cur = []
    if cur:
        passes.append(cur)
    return passes


def measure_image(image: Path, width_mm: float, row_mm: float | None) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import digitize

    kw = {"target_width_mm": width_mm}
    if row_mm is not None:
        kw["fill_row_mm"] = row_mm
    _result, plan = digitize(image, PipelineConfig(**kw))
    out = _summarise(passes_from_plan(plan), str(image))
    # The number the engine was TOLD to sew, so a reader can see recovery
    # without going and looking it up.
    if row_mm is not None:
        out["configured_row_mm"] = row_mm
    else:
        from digitizer_core import machine
        out["configured_row_mm"] = machine.FILL_ROW_MM
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", type=Path, help="digitize this artwork and measure the plan")
    src.add_argument("--dst", type=Path, help="measure a sewn/exported DST")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--row-mm", type=float, default=None,
                    help="override fill_row_mm (--image only); the calibration knob")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--verbose", action="store_true", help="list every readable pass")
    a = ap.parse_args(argv)

    rep = (measure_image(a.image, a.width, a.row_mm) if a.image
           else _summarise(passes_from_dst(a.dst), str(a.dst)))

    print(f"{rep['source']}")
    print(f"  passes read : {rep['passes_read']} of {rep['passes_total']}")
    if rep["pitch_mm_median"] is None:
        print("  row pitch   : unreadable — no pass was wide enough to hold a period")
    else:
        print(f"  row pitch   : {rep['pitch_mm_median']:.3f} mm median "
              f"(p10 {rep['pitch_mm_p10']:.3f}, p90 {rep['pitch_mm_p90']:.3f})")
    if "configured_row_mm" in rep:
        print(f"  engine told : {rep['configured_row_mm']:.3f} mm")
    if a.verbose:
        for p in rep["per_pass"]:
            print(f"    {p['pitch_mm']:.3f} mm over {p['span_mm']:>6.2f} mm span, "
                  f"{p['points']:>5} penetrations, rows at {p['angle_deg']:.0f} deg")
    if a.json:
        a.json.write_text(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
