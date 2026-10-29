#!/usr/bin/env python
"""Classifier lens — measure where every fixture sits against stage 0's gates.

`stage0_classify.py` routes a whole design 4 ways (flat / gradient /
photo_subject / photo_scene) from three signals, and the photo lanes
(SLIC/RAG region-former, tonal tiers) hang off that verdict — so a misroute
decides which entire pipeline a customer's art gets. This tool prints, for
every committed fixture, one row: the three raw signals, every threshold the
classifier consults, the resulting class + confidence, and how far each
signal sits from changing the final verdict (distance-to-flip). `--sweep`
varies each threshold ±50% and reports which fixtures flip class where — the
sensitivity map a threshold change must be argued against.

It is an instrument, not engine code: nothing here is imported by the
pipeline, and it never changes a threshold — it measures them.

On measurement independence (the `shape_lens.py` rule, adapted): the SIGNALS
are computed by the engine itself (`classify()` is called and its
`signals` dict is read back). That is deliberate, not a circularity — the
question under measurement here is the DECISION SURFACE, i.e. where the
engine's own signals sit against the engine's own thresholds; recomputing
the signals with second implementations would measure a different
instrument. What IS re-derived independently is the decision: `decide()`
below rebuilds the threshold tree locally from the module's documented
constants, parameterized so it can be swept, and self-checks at nominal
thresholds that it reproduces the engine's class and confidence exactly for
every fixture (a mismatch is a hard error — the lens would be lying about
the surface it claims to map).

Before reading any number here as a case for moving a threshold, read the
"Real-fixture note" in `stage0_classify.py`'s docstring: `drone_render.png`
classifying as `gradient` (not photo) is a deliberate, documented routing —
`unique_color_mass` is the photo/non-photo gate precisely because that
fixture reads ROUGHER than the synthetic scene stub on `gradient_smoothness`.

Usage
-----
    PYTHONPATH=. python tools/classify_lens.py            # the table
    PYTHONPATH=. python tools/classify_lens.py --sweep    # + sensitivity map
    PYTHONPATH=. python tools/classify_lens.py --sweep --step 0.01
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import stage0_classify as s0  # noqa: E402  -- the SUBJECT
from digitizer_core.config import PipelineConfig  # noqa: E402

TESTDATA = ROOT / "testdata"
FIXTURE_DIRS = (TESTDATA, TESTDATA / "photo")


# --- The thresholds, as data ------------------------------------------------
#
# Read once from the module's documented constants, never hardcoded here, so
# the lens cannot silently drift from the subject. `replace()` on this frozen
# dataclass is how the sweep perturbs one threshold at a time.

@dataclass(frozen=True)
class Thresholds:
    ucm_photo_min: float
    ucm_margin: float
    grad_gradient_min: float
    grad_gradient_margin: float
    grad_subject_min: float
    grad_subject_margin: float
    confidence_floor: float
    # The 2026-10-28 texture route and two-ink veto (`decide_photo`).
    texture_photo_min: float
    texture_margin: float
    two_tone_max: float
    two_tone_margin: float

    @classmethod
    def nominal(cls) -> "Thresholds":
        return cls(
            ucm_photo_min=s0.UCM_PHOTO_MIN,
            ucm_margin=s0.UCM_MARGIN,
            grad_gradient_min=s0.GRAD_VAR_GRADIENT_MIN,
            grad_gradient_margin=s0.GRAD_VAR_GRADIENT_MARGIN,
            grad_subject_min=s0.GRAD_VAR_SUBJECT_MIN,
            grad_subject_margin=s0.GRAD_VAR_SUBJECT_MARGIN,
            confidence_floor=s0.CONFIDENCE_FLOOR,
            texture_photo_min=s0.TEXTURE_PHOTO_MIN,
            texture_margin=s0.TEXTURE_MARGIN,
            two_tone_max=s0.TWO_TONE_MAX,
            two_tone_margin=s0.TWO_TONE_MARGIN,
        )


SWEEP_FIELDS = [
    "ucm_photo_min", "ucm_margin",
    "grad_gradient_min", "grad_gradient_margin",
    "grad_subject_min", "grad_subject_margin",
    "confidence_floor",
    "texture_photo_min", "texture_margin",
    "two_tone_max", "two_tone_margin",
]


@dataclass(frozen=True)
class Decision:
    class_: str
    confidence: float
    demoted: bool           # would-be non-flat discarded below the floor
    raw_class: str          # the class before any floor demotion
    gates: tuple            # ((gate_name, signal_value, threshold, margin), ...)
    route: str = "legacy"   # what decided the photo gate (`decide_photo`'s route)


def _gate_conf(value: float, threshold: float, margin: float) -> float:
    """Local restatement of `stage0_classify._gate_confidence` — 0.5 at the
    threshold, 1.0 once clear by a full margin."""
    if margin <= 0:
        return 1.0
    return float(min(1.0, 0.5 + 0.5 * abs(value - threshold) / margin))


def _photo_gate(ucm: float, texture: float, two_tone: float, cutout: bool,
                th: Thresholds, gate_on: bool) -> tuple[bool, float, str]:
    """Local restatement of `stage0_classify.decide_photo`, parameterised by
    `th` so the sweep can move its thresholds."""
    by_grain = ucm >= th.ucm_photo_min
    grain_conf = _gate_conf(ucm, th.ucm_photo_min, th.ucm_margin)
    if cutout or not gate_on:
        return by_grain, grain_conf, "legacy"
    by_texture = texture >= th.texture_photo_min
    texture_conf = _gate_conf(texture, th.texture_photo_min, th.texture_margin)
    two_tone_fires = two_tone >= th.two_tone_max
    veto_conf = _gate_conf(two_tone, th.two_tone_max, th.two_tone_margin)
    if not (by_grain or by_texture):
        return False, min(grain_conf, texture_conf), "none"
    if two_tone_fires:
        return False, veto_conf, "veto"
    route = "+".join(n for n, fired in (("grain", by_grain), ("texture", by_texture)) if fired)
    strongest = max(c for c, fired in ((grain_conf, by_grain), (texture_conf, by_texture)) if fired)
    return True, min(strongest, veto_conf), route


def decide(ucm: float, grad: float, texture: float, two_tone: float, cutout: bool,
           th: Thresholds, gate_on: bool = True) -> Decision:
    """The stage-0 decision tree, re-derived from the documented constants.

    Must agree with `classify()` exactly at `Thresholds.nominal()` — the
    self-check in `measure()` (and `tests/test_classify_lens.py`) enforces
    it. `alpha_softness` does not appear because the engine's tree never
    consults it (carried in `signals` for the record only). `gate_on` is
    `cfg.stage0_texture_gate`; False, or a cut-out file, is the grain gate
    alone (the pre-2026-10-28 tree).
    """
    is_photo, photo_conf, route = _photo_gate(ucm, texture, two_tone, cutout, th, gate_on)
    photo_gates = (("ucm_photo", ucm, th.ucm_photo_min, th.ucm_margin),
                   ("texture_photo", texture, th.texture_photo_min, th.texture_margin),
                   ("two_tone", two_tone, th.two_tone_max, th.two_tone_margin))
    if is_photo:
        is_subject = grad >= th.grad_subject_min
        g2 = _gate_conf(grad, th.grad_subject_min, th.grad_subject_margin)
        raw = "photo_subject" if is_subject else "photo_scene"
        gates = (*photo_gates,
                 ("grad_subject", grad, th.grad_subject_min, th.grad_subject_margin))
    else:
        is_gradient = grad >= th.grad_gradient_min
        g2 = _gate_conf(grad, th.grad_gradient_min, th.grad_gradient_margin)
        raw = "gradient" if is_gradient else "flat"
        gates = (*photo_gates,
                 ("grad_gradient", grad, th.grad_gradient_min, th.grad_gradient_margin))
    conf = min(photo_conf, g2)
    demoted = raw != "flat" and conf < th.confidence_floor
    return Decision(class_="flat" if demoted else raw, confidence=conf,
                    demoted=demoted, raw_class=raw, gates=gates, route=route)


def decide_from_signals(signals: dict, th: Thresholds, gate_on: bool = True) -> Decision:
    """`decide` on an engine `signals` dict (the shape `classify` reports)."""
    return decide(signals["unique_color_mass"], signals["gradient_smoothness"],
                  signals["texture_frac"], signals["two_tone_mass"],
                  bool(signals["cutout_alpha"]), th, gate_on)


# --- Distance-to-flip -------------------------------------------------------
#
# For each decision signal (holding the other fixed), the nearest value at
# which the FINAL class changes — floor demotion included, which is why this
# is computed against `decide()` rather than against the bare thresholds:
# around each threshold there is a demotion band (|value - t| < 0.1 * margin
# puts the weakest gate's confidence under 0.55) where a would-be non-flat
# class collapses to `flat`, so the naive |signal - threshold| number can
# name the wrong flip class or miss a nearer one.

_EPS_FRAC = 1e-9


def _breakpoints_ucm(th: Thresholds) -> list[float]:
    t, m = th.ucm_photo_min, th.ucm_margin
    band = _demotion_halfwidth(th, m)
    return [t - band, t, t + band]


def _breakpoints_grad(th: Thresholds) -> list[float]:
    out = []
    for t, m in ((th.grad_gradient_min, th.grad_gradient_margin),
                 (th.grad_subject_min, th.grad_subject_margin)):
        band = _demotion_halfwidth(th, m)
        out += [t - band, t, t + band]
    return out


def _breakpoints_texture(th: Thresholds) -> list[float]:
    t, m = th.texture_photo_min, th.texture_margin
    band = _demotion_halfwidth(th, m)
    return [t - band, t, t + band]


def _breakpoints_two_tone(th: Thresholds) -> list[float]:
    t, m = th.two_tone_max, th.two_tone_margin
    band = _demotion_halfwidth(th, m)
    return [t - band, t, t + band]


def _demotion_halfwidth(th: Thresholds, margin: float) -> float:
    """|value - t| below which the gate's confidence sits under the floor:
    0.5 + 0.5*d/margin < floor  <=>  d < (floor - 0.5) * 2 * margin."""
    return max(0.0, (th.confidence_floor - 0.5) * 2.0 * margin)


@dataclass(frozen=True)
class Flip:
    signal: str        # unique_color_mass | gradient_smoothness | texture_frac | two_tone_mass
    at: float          # signal value just past which the final class changes
    delta: float       # at - current value (signed)
    to: str            # the class it becomes


def nearest_flip(signal: str, ucm: float, grad: float, texture: float, two_tone: float,
                 cutout: bool, th: Thresholds, lo: float = 0.0,
                 hi: float | None = None) -> Flip | None:
    """Nearest final-class change along one signal axis. None when no
    reachable value of that signal (within [lo, hi]) changes the verdict."""
    cur = decide(ucm, grad, texture, two_tone, cutout, th).class_
    if signal == "unique_color_mass":
        breaks, value = _breakpoints_ucm(th), ucm
        evalf = lambda v: decide(v, grad, texture, two_tone, cutout, th).class_      # noqa: E731
        hi = 1.0 if hi is None else hi
    elif signal == "texture_frac":
        breaks, value = _breakpoints_texture(th), texture
        evalf = lambda v: decide(ucm, grad, v, two_tone, cutout, th).class_         # noqa: E731
        hi = 1.0 if hi is None else hi
    elif signal == "two_tone_mass":
        breaks, value = _breakpoints_two_tone(th), two_tone
        evalf = lambda v: decide(ucm, grad, texture, v, cutout, th).class_          # noqa: E731
        hi = 1.0 if hi is None else hi
    else:
        breaks, value = _breakpoints_grad(th), grad
        evalf = lambda v: decide(ucm, v, texture, two_tone, cutout, th).class_      # noqa: E731
        hi = float("inf") if hi is None else hi
    eps = max(abs(value), max(abs(b) for b in breaks), 1.0) * _EPS_FRAC

    best: Flip | None = None
    for p in sorted(b for b in breaks if value < b <= hi):
        c = evalf(p + eps)
        if c != cur:
            best = Flip(signal, p, p - value, c)
            break
    for p in sorted((b for b in breaks if lo <= b < value), reverse=True):
        c = evalf(p - eps)
        if c != cur:
            if best is None or (value - p) < abs(best.delta):
                best = Flip(signal, p, p - value, c)
            break
    return best


# --- Measurement ------------------------------------------------------------

@dataclass
class Row:
    name: str
    ucm: float
    grad: float
    alpha: float
    class_: str
    confidence: float
    demoted: bool
    warnings: list[str]
    flips: list[Flip]
    texture: float = 0.0
    two_tone: float = 0.0
    cutout: bool = False
    route: str = "legacy"


IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def fixtures(extra_dirs: list[Path] = ()) -> list[Path]:
    out: list[Path] = []
    for d in (*FIXTURE_DIRS, *extra_dirs):
        out += sorted(p for p in Path(d).glob("*")
                      if p.suffix.lower() in IMG_EXTS)
    return out


def measure(path: Path, th: Thresholds) -> Row:
    cfg = PipelineConfig(target_width_mm=80.0)
    res = s0.classify(path, cfg)
    ucm = res.signals["unique_color_mass"]
    grad = res.signals["gradient_smoothness"]
    alpha = res.signals["alpha_softness"]
    texture = res.signals["texture_frac"]
    two_tone = res.signals["two_tone_mass"]
    cutout = bool(res.signals["cutout_alpha"])

    d = decide(ucm, grad, texture, two_tone, cutout, th)
    if th == Thresholds.nominal() and (
            d.class_ != res.class_ or abs(d.confidence - res.confidence) > 1e-12):
        raise AssertionError(
            f"lens decide() disagrees with the engine on {path.name}: "
            f"lens ({d.class_}, {d.confidence}) vs engine "
            f"({res.class_}, {res.confidence}) — the lens is broken, "
            f"nothing it prints can be trusted")

    name = (path.name if path.parent == TESTDATA
            else f"{path.parent.name}/{path.name}")
    return Row(
        name=name, ucm=ucm, grad=grad, alpha=alpha,
        class_=d.class_, confidence=d.confidence, demoted=d.demoted,
        warnings=[w["code"] for w in res.warnings],
        flips=[f for f in (nearest_flip(sig, ucm, grad, texture, two_tone, cutout, th)
                           for sig in ("unique_color_mass", "gradient_smoothness",
                                       "texture_frac", "two_tone_mass"))
               if f is not None],
        texture=texture, two_tone=two_tone, cutout=cutout, route=d.route,
    )


# --- Reporting --------------------------------------------------------------

def _fmt_flip(row: Row, signal: str) -> str:
    f = next((f for f in row.flips if f.signal == signal), None)
    if f is None:
        return "(no reachable flip)"
    return f"{f.to}@{f.at:.4g} (d={f.delta:+.3g})"


def print_table(rows: list[Row], th: Thresholds) -> None:
    print("# stage-0 classifier lens — thresholds read from stage0_classify.py:")
    print(f"#   UCM_PHOTO_MIN {th.ucm_photo_min}  (margin {th.ucm_margin})   "
          f"ucm >= min -> photo territory")
    print(f"#   GRAD_VAR_GRADIENT_MIN {th.grad_gradient_min}  "
          f"(margin {th.grad_gradient_margin})   non-photo: grad >= min -> gradient")
    print(f"#   GRAD_VAR_SUBJECT_MIN {th.grad_subject_min}  "
          f"(margin {th.grad_subject_margin})   photo: grad >= min -> photo_subject")
    print(f"#   CONFIDENCE_FLOOR {th.confidence_floor}   "
          f"non-flat below this -> flat + CLASSIFICATION_UNCERTAIN")
    print(f"#   TEXTURE_PHOTO_MIN {th.texture_photo_min}  (margin {th.texture_margin})   "
          f"opaque file: texture >= min -> photo territory too")
    print(f"#   TWO_TONE_MAX {th.two_tone_max}  (margin {th.two_tone_margin})   "
          f"two_tone >= max -> never photo territory (two inks)")
    print("# alpha_softness is carried for the record; the tree never consults it.")
    print("# cut = alpha cut-out; such a file takes the grain gate alone (route legacy).")
    print("# flip columns: nearest value of THAT signal (other held fixed) where")
    print("# the FINAL class changes, demotion band included; d = flip - current.\n")

    hdr = (f"{'fixture':<36} {'ucm':>8} {'grad_var':>10} {'alpha':>6} {'tex':>6} {'2tone':>6} {'cut':>3} "
           f"{'route':<14} {'class':<14} {'conf':>5} {'flr':>3}  "
           f"{'ucm flips to':<30} {'grad_var flips to':<34} {'tex flips to':<30} warnings")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r.name:<36} {r.ucm:8.4f} {r.grad:10.4f} {r.alpha:6.3f} {r.texture:6.3f} {r.two_tone:6.3f} "
              f"{'cut' if r.cutout else '  .':>3} {r.route:<14} "
              f"{r.class_:<14} {r.confidence:5.2f} {'DEM' if r.demoted else '  .':>3}  "
              f"{_fmt_flip(r, 'unique_color_mass'):<30} "
              f"{_fmt_flip(r, 'gradient_smoothness'):<34} "
              f"{_fmt_flip(r, 'texture_frac'):<30} "
              f"{','.join(r.warnings) or '-'}")


def sweep(rows: list[Row], th: Thresholds, lo: float, hi: float,
          step: float) -> None:
    """Vary each threshold constant by a multiplier in [lo, hi]; report every
    fixture whose FINAL class differs from nominal, as contiguous multiplier
    ranges. Signals are measured once — the sweep re-runs only the decision,
    which is the point: thresholds do not feed back into the signals."""
    n = int(round((hi - lo) / step)) + 1
    mults = [lo + i * step for i in range(n)]
    print(f"\n# --- sweep: each threshold x{lo:.2f}..x{hi:.2f} "
          f"step {step:g}, one at a time, others nominal ---")
    for field in SWEEP_FIELDS:
        base = getattr(th, field)
        flips: dict[str, list[tuple[float, str]]] = {}
        for m in mults:
            t2 = replace(th, **{field: base * m})
            for r in rows:
                c = decide(r.ucm, r.grad, r.texture, r.two_tone, r.cutout, t2).class_
                if c != r.class_:
                    flips.setdefault(r.name, []).append((m, c))
        print(f"\n{field} (nominal {base:g}):")
        if not flips:
            print("  no fixture changes class anywhere in the range")
            continue
        for name, hits in flips.items():
            row = next(r for r in rows if r.name == name)
            for lo_m, hi_m, cls in _ranges(hits, step):
                lo_v, hi_v = base * lo_m, base * hi_m
                print(f"  {name:<36} {row.class_} -> {cls:<14} "
                      f"for x{lo_m:.2f}..x{hi_m:.2f} "
                      f"({field} in {lo_v:g}..{hi_v:g})")


def _ranges(hits: list[tuple[float, str]],
            step: float) -> list[tuple[float, float, str]]:
    """[(mult, class)] -> contiguous [(lo_mult, hi_mult, class)]. Two hits are
    contiguous only when they are one sweep step apart AND flip to the same
    class — a gap or a class change starts a new range."""
    out: list[tuple[float, float, str]] = []
    for m, c in hits:
        if out and c == out[-1][2] and abs(m - out[-1][1]) <= step * 1.5:
            out[-1] = (out[-1][0], m, c)
        else:
            out.append((m, m, c))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep", action="store_true",
                    help="vary each threshold and report class flips")
    ap.add_argument("--lo", type=float, default=0.5, help="sweep low multiplier")
    ap.add_argument("--hi", type=float, default=1.5, help="sweep high multiplier")
    ap.add_argument("--step", type=float, default=0.05, help="sweep step")
    ap.add_argument("--dir", action="append", default=[], metavar="DIR",
                    help="extra image directory to measure (repeatable) — the "
                         "local-only real-art leg: point this at scratch_kent/ "
                         "or the Reference Art folder on a machine that has it")
    args = ap.parse_args()

    th = Thresholds.nominal()
    rows = [measure(p, th) for p in fixtures([Path(d) for d in args.dir])]
    print_table(rows, th)
    if args.sweep:
        sweep(rows, th, args.lo, args.hi, args.step)


if __name__ == "__main__":
    main()
