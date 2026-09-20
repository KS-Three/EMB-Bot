"""How much of stage 0's resolution-dependence is the RGB under an alpha
cutout's transparency, and how much is the pixel-absolute signal windows —
measured on the six scale-invariance fixtures across a width ladder, under
the three forms of `alpha_edge_extend` (Kent's pick 2026-09-20; committed
so the numbers keep their definition — DOCTRINE 2026-09-11).

`tests/test_classifier_scale_invariance.py` pins stage 0's known defect: the
same artwork classifies differently by export resolution, because
`_gradient_smoothness` and `_unique_color_mass` run with pixel-absolute
windows (`GRAD_VAR_WIN`, `CANNY_DILATE_PX`, `UCM_NEIGHBORHOOD`). When Kent
flipped `alpha_edge_extend` ON (gated on the resolution-floor upscale) the
drone left that test's broken sets: its 250-px `photo_subject` had been the
render's backdrop under its alpha, which stage 0 read through the whole-
raster kernels (`unique_color_mass` 0.335 -> 0.091). So the defect the test
pins has two parts, and this tool separates them: the three arms below read
each fixture at each width with the extension OFF (the pre-flip engine),
gated (the shipped engine — extension only where the upscale will run) and
whole-image (extension everywhere), and the opaque fixtures, which the
extension cannot touch, are the control.

    .venv/bin/python -m tools.stage0_scale_arms run --out scale_arms.json
    .venv/bin/python -m tools.stage0_scale_arms tables scale_arms.json

Downscale only, LANCZOS through PIL, exactly as the test does (upscaling
would invent detail and let the interpolator take the blame). Per row: the
class and the raw signals under each arm, whether the gate opened at that
width (`alpha_edge.upscale_expected` at the default target width), and
whether the extension changes any pixel at all (it cannot on an opaque file,
and it changes nothing where the exporter already left the ink colour under
the alpha). Measurement only: no threshold moves here (ROADMAP gate 2).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent            # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import stage0_classify  # noqa: E402
from digitizer_core.alpha_edge import extend_opaque_colour, upscale_expected  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402

TESTDATA = ROOT / "testdata"

# The scale test's fixtures and their native classes (its FIXTURES map).
FIXTURES = {
    "logo_alpha.png": "flat",
    "logo_whitebg.png": "flat",
    "ribbon_curve.png": "flat",
    "photo/enthusiast_logo.png": "flat",
    "photo/drone_render.png": "gradient",
    "photo/summit_badge.png": "gradient",
}
# The test's sweep is 250 / 400 / 640; the ladder around it shows where a
# class flips relative to the resolution floor. Widths at or above a
# fixture's native width are skipped (downscale only).
WIDTHS = (200, 250, 320, 400, 500, 640, 800, 1000, 1200)
SWEEP = (250, 400, 640)

ARMS: dict[str, dict] = {
    "off": {"alpha_edge_extend": False},
    "gated": {"alpha_edge_extend": True, "alpha_edge_extend_upscaled_only": True},
    "whole": {"alpha_edge_extend": True, "alpha_edge_extend_upscaled_only": False},
}
SIGNALS = ("unique_color_mass", "gradient_smoothness", "alpha_softness")


def _resized(path: Path, width: int | None, tmp: Path) -> Path:
    """The test's `_classify_at` resample: RGBA/RGB through PIL LANCZOS."""
    if width is None:
        return path
    im = Image.open(path)
    conv = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    assert width < conv.width, f"{path.name} is only {conv.width}px — would upscale"
    height = max(1, round(conv.height / conv.width * width))
    out = tmp / f"{path.stem}_{width}.png"
    conv.resize((width, height), Image.LANCZOS).save(out)
    return out


def _alpha_facts(path: Path, cfg: PipelineConfig) -> dict:
    """Whether the file has a real alpha, whether the gate opens at the
    default target width, and whether the extension would change a pixel."""
    arr = np.array(Image.open(path).convert("RGBA"))
    alpha = arr[..., 3]
    has_alpha = bool((alpha < 255).any())
    gate = bool(upscale_expected(alpha, cfg.target_width_mm, cfg.min_px_per_mm)) if has_alpha else False
    changes = False
    if has_alpha:
        rgb = arr[..., :3]
        ext = extend_opaque_colour(rgb, alpha)
        changes = ext is not rgb and bool(np.any(ext != rgb))
    return {"has_alpha": has_alpha, "gate_open": gate, "extension_changes_pixels": changes,
            "width_px": int(arr.shape[1]), "height_px": int(arr.shape[0])}


def measure_fixture(path: Path, widths=WIDTHS, arms=ARMS, tmp: Path | None = None,
                    target_mm: float | None = None, label: str | None = None) -> list[dict]:
    """One row per width (native last): the arms' classes and signals.
    `target_mm` is the target width the gate is decided at (the config's
    default when None — what the scale test uses; a corpus case's own width
    for the customer's reading)."""
    tmp = tmp or Path(tempfile.mkdtemp(prefix="stage0-scale-"))
    native_w = Image.open(path).width
    base = {} if target_mm is None else {"target_width_mm": float(target_mm)}
    rows = []
    for width in [w for w in widths if w < native_w] + [None]:
        src = _resized(path, width, tmp)
        facts = _alpha_facts(src, PipelineConfig(**base))
        row = {"fixture": label or (str(path.relative_to(TESTDATA)) if path.is_relative_to(TESTDATA) else path.name),
               "target_mm": PipelineConfig(**base).target_width_mm,
               "width": width if width is not None else "native", **facts}
        for arm, flags in arms.items():
            r = stage0_classify.classify(str(src), PipelineConfig(**base, **flags))
            row[arm] = {"class": r.class_, "confidence": round(float(r.confidence), 3),
                        **{k: (round(float(r.signals[k]), 5) if k in r.signals else None) for k in SIGNALS}}
        rows.append(row)
    return rows


def run(out: Path, fixtures=FIXTURES, widths=WIDTHS, corpus: bool = False) -> list[dict]:
    """The scale test's fixtures at the default target, and with `corpus` the
    nine REAL_ART logos at their own census widths (`tools.thin_strokes.corpus_cases`)."""
    rows: list[dict] = []
    jobs = [(TESTDATA / rel, None, None) for rel in fixtures]
    if corpus:
        from tools.thin_strokes import corpus_cases
        jobs += [(Path(p), float(w), f"corpus/{n}") for n, p, w, _g in corpus_cases()]
    for path, target_mm, label in jobs:
        rows.extend(measure_fixture(path, widths, target_mm=target_mm, label=label))
        out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        name = label or path.name
        print(f"{name}: {sum(1 for r in rows if r['fixture'] == (label or r['fixture']))} widths", file=sys.stderr)
    return rows


def _fmt(cell: dict) -> str:
    return f"{cell['class']} ({cell['unique_color_mass']:.3f} / {cell['gradient_smoothness']:.4f})"


def tables(rows: list[dict], arms=ARMS) -> str:
    """Per fixture, a width x arm table; then the invariance summary the scale
    test asks about, per arm: identical across the 250/400/640 sweep, identical
    across the whole ladder, and equal to the native class at every width."""
    out = []
    by_fix: dict[str, list[dict]] = {}
    for r in rows:
        by_fix.setdefault(r["fixture"], []).append(r)
    for fix, frows in by_fix.items():
        native = next(r for r in frows if r["width"] == "native")
        out.append(f"\n### {fix} — native {native['width_px']}x{native['height_px']}, "
                   f"{'alpha' if native['has_alpha'] else 'opaque'}, gate decided at {native.get('target_mm', 80.0):g} mm, native class "
                   f"{native['off']['class']} (OFF) / {native['gated']['class']} (gated) / {native['whole']['class']} (whole)\n")
        out.append("| width | gate | ext. changes px | " + " | ".join(f"{a}: class (ucm / grad)" for a in arms) + " |")
        out.append("|---|---|---|" + "---|" * len(arms))
        for r in frows:
            out.append(f"| {r['width']} | {'open' if r['gate_open'] else 'shut'} | {'yes' if r['extension_changes_pixels'] else 'no'} | "
                       + " | ".join(_fmt(r[a]) for a in arms) + " |")
    out.append("\n### Invariance per arm\n")
    out.append("| fixture | arm | same class across 250/400/640 | same across the ladder | equals native at every width |")
    out.append("|---|---|---|---|---|")
    for fix, frows in by_fix.items():
        native = next(r for r in frows if r["width"] == "native")
        for a in arms:
            classes = {r["width"]: r[a]["class"] for r in frows}
            sweep = {classes[w] for w in SWEEP if w in classes}
            ladder = {c for w, c in classes.items() if w != "native"}
            nat = native[a]["class"]
            out.append(f"| {fix} | {a} | {'yes' if len(sweep) <= 1 else 'NO: ' + ', '.join(f'{w}={classes[w]}' for w in SWEEP if w in classes)} "
                       f"| {'yes' if len(ladder) <= 1 else 'NO (' + str(len(ladder)) + ' classes)'} "
                       f"| {'yes' if all(c == nat for c in classes.values()) else 'NO: ' + ', '.join(f'{w}={c}' for w, c in classes.items() if c != nat)} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--fixtures", nargs="*", default=list(FIXTURES), choices=list(FIXTURES))
    r.add_argument("--widths", nargs="*", type=int, default=list(WIDTHS))
    r.add_argument("--corpus", action="store_true", help="also the nine REAL_ART logos at their census widths")
    t = sub.add_parser("tables")
    t.add_argument("json", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        rows = run(a.out, {k: FIXTURES[k] for k in a.fixtures}, tuple(a.widths), corpus=a.corpus)
        print(tables(rows))
    else:
        print(tables(json.loads(a.json.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
