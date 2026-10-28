#!/usr/bin/env python
"""Stage 0's photo gate, read out: the three 2026-10-28 signals, the class
under both arms of `cfg.stage0_texture_gate`, and the margins the gate sits
in — over the repo's fixtures and, when the gitignored images are present,
the 39-row Commons corpus (`testdata/photo/corpus/corpus.json`).

Spec: `docs/superpowers/specs/2026-10-28-stage0-photo-texture-gate-design.md`.
**Every number is an instrument reading, not a quality claim** (ROADMAP gate
4), and the tool moves nothing: it prints the engine's own class beside the
signals (DOCTRINE 2026-09-11 — an instrument restates the shipped answer next
to its own), so a threshold argument can be checked against this table
instead of a pasted one.

    cd digitizer && .venv/Scripts/python -m tools.stage0_photo_gate            # fixtures + corpus
    .venv/Scripts/python -m tools.stage0_photo_gate --fixtures-only
    .venv/Scripts/python -m tools.stage0_photo_gate --ladder               # export-width ladder per row
    .venv/Scripts/python -m tools.stage0_photo_gate --json                 # the rows as JSON

On Linux the interpreter is `.venv/bin/python` (CLAUDE.md).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import stage0_classify as s0  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402

TESTDATA = ROOT / "testdata"
CORPUS_JSON = TESTDATA / "photo" / "corpus" / "corpus.json"

#: The repo's real artwork (kind as the margin counts it) and its synthetic
#: fixtures (printed, never in a margin — ROADMAP gate 2).
FIXTURES = {
    "photo/owl_kent.jpg": "photo",
    "logo_whitebg.png": "logo", "logo_alpha.png": "logo", "ribbon_curve.png": "logo",
    "logo_script_tires.png": "logo", "becker_marine_logo.png": "logo", "bg_uncertain.png": "logo",
    "photo/enthusiast_logo.png": "logo", "photo/drone_render.png": "logo",
    "photo/summit_badge.png": "logo", "photo/logo_bridge_bar.jpg": "logo",
    "photo/logo_gaulke_roofing.png": "logo", "photo/logo_golden_tee.jpg": "logo",
    "photo/logo_hotel_fremont.webp": "logo", "photo/screenshot_phone_ui_golke.jpg": "logo",
    "photo/repro_gradient_white_icon.png": "synthetic",
    "photo/gradient_ramp_linear.png": "synthetic", "photo/gradient_ramp_radial.png": "synthetic",
    "photo/photo_subject_stub.png": "synthetic", "photo/photo_scene_stub.png": "synthetic",
    "photo/photo_owl_pale.png": "synthetic", "photo/photo_dof_meadow.png": "synthetic",
    "photo/photo_grass_macro.png": "synthetic", "photo/photo_sunset_backlit.png": "synthetic",
    "photo/photo_chrome_specular.png": "synthetic", "photo/tight_crop_pale_subject.png": "synthetic",
    "photo/fur_ramp.png": "synthetic",
}

LADDER_WIDTHS = (250, 400, 640, 900, 1200, 1600)

#: Corpus rows whose `kind` is `logo` but whose MEDIUM is a photograph or a
#: scan (a printed portrait, a café chalkboard, a framed poster, ink on paper,
#: a photographed comic poster, an engraving scan — spec §3). Stage 0 reads
#: the medium, so these are printed as `photo-of-logo` and sit in neither
#: margin: a hand label, kept here so the table says which rows it applies to.
PHOTOGRAPHED_GRAPHICS = frozenset({
    "halftone_dots", "chalkboard_lettering", "duotone_poster", "kanji_brush",
    "comic_halftone", "vintage_engraved_badge",
})


def _slug(path: Path) -> str:
    path = Path(path)
    if path.parent == TESTDATA:
        return path.name
    if path.parent == TESTDATA / "photo":
        return f"photo/{path.name}"
    return path.stem


def rows(paths: list[Path], cfg: PipelineConfig, kinds: dict[str, str] | None = None) -> list[dict]:
    """One row per path: the signals and the engine's class under both arms.
    `kinds` maps slug -> photo | logo | synthetic; unlisted paths are `fixture`."""
    kinds = kinds or {}
    out = []
    for p in paths:
        p = Path(p)
        on = s0.classify(str(p), cfg)
        off = s0.classify(str(p), dataclasses.replace(cfg, stage0_texture_gate=False))
        sig = on.signals
        slug = _slug(p)
        out.append({
            "slug": slug, "kind": kinds.get(slug, "fixture"), "cutout": bool(sig["cutout_alpha"]),
            "texture_frac": sig["texture_frac"], "two_tone_mass": sig["two_tone_mass"],
            "ucm": sig["unique_color_mass"], "grad": sig["gradient_smoothness"],
            "class_on": on.class_, "conf_on": on.confidence, "class_off": off.class_,
            "route": sig["photo_route"],
        })
    return out


def margins(rows_: list[dict]) -> dict:
    """Where the texture gate and the veto sit against the opaque rows: a
    `photo` row's lowest texture, a graphic (`logo`) row's highest, and the
    photos' highest two-tone mass. Cut-out rows and synthetic rows are left
    out (the former take the grain gate alone; the latter are barred from
    calibration by ROADMAP gate 2)."""
    photos = [r for r in rows_ if r["kind"] == "photo" and not r["cutout"]]
    graphics = [r for r in rows_ if r["kind"] == "logo" and not r["cutout"]]
    photographed = [r for r in rows_ if r["kind"] == "photo-of-logo"]

    def pick(items, key, fn):
        if not items:
            return (None, None)
        r = fn(items, key=lambda x: x[key])
        return (r[key], r["slug"])

    pmin = pick(photos, "texture_frac", min)
    gmax = pick(graphics, "texture_frac", max)
    return {
        "photo_texture_min": pmin, "graphic_texture_max": gmax,
        "photo_two_tone_max": pick(photos, "two_tone_mass", max),
        "graphic_two_tone_min": pick(graphics, "two_tone_mass", min),
        "texture_gap": (pmin[0] - gmax[0]) if pmin[0] is not None and gmax[0] is not None else None,
        "n_photo": len(photos), "n_graphic": len(graphics), "n_photo_of_logo": len(photographed),
    }


def corpus_kinds(corpus_rows: list[dict]) -> dict[str, str]:
    """slug -> kind, with the photographed graphics relabelled `photo-of-logo`."""
    return {r["slug"]: ("photo-of-logo" if r["slug"] in PHOTOGRAPHED_GRAPHICS else r["kind"])
            for r in corpus_rows}


def ladder(path: Path, widths=LADDER_WIDTHS) -> dict:
    """The two signals at each export width below the file's own (PIL LANCZOS
    downscale, as `tests/test_classifier_scale_invariance.py` resamples);
    None at a width the file does not reach — an upscale invents nothing."""
    from PIL import Image
    path = Path(path)
    im = Image.open(path)
    conv = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    out = {"slug": _slug(path), "native_w": conv.width, "widths": {}}
    for w in widths:
        if w >= conv.width:
            out["widths"][w] = None
            continue
        h = max(1, round(conv.height / conv.width * w))
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / f"{path.stem}_{w}.png"
            conv.resize((w, h), Image.LANCZOS).save(tmp)
            rgb, alpha = s0._load(str(tmp))
        fg = s0._fg_mask(rgb, alpha)
        out["widths"][w] = {"texture_frac": s0._texture_frac(rgb, fg),
                            "two_tone_mass": s0._two_tone_mass(rgb, fg)}
    return out


def corpus_items(corpus_json: Path = CORPUS_JSON) -> tuple[list[Path], dict[str, str]]:
    """The corpus rows whose gitignored image is present beside corpus.json."""
    if not corpus_json.exists():
        return [], {}
    corpus_rows = json.loads(corpus_json.read_text(encoding="utf-8"))
    kinds = corpus_kinds(corpus_rows)
    paths = []
    for r in corpus_rows:
        for ext in (".png", ".jpg"):
            p = corpus_json.parent / f"{r['slug']}{ext}"
            if p.exists():
                paths.append(p)
                break
    present = {p.stem for p in paths}
    return paths, {k: v for k, v in kinds.items() if k in present}


def print_table(rows_: list[dict], m: dict) -> None:
    print("# stage-0 photo gate — readings, not claims. Thresholds from stage0_classify.py:")
    print(f"#   UCM_PHOTO_MIN {s0.UCM_PHOTO_MIN}   TEXTURE_PHOTO_MIN {s0.TEXTURE_PHOTO_MIN} "
          f"(margin {s0.TEXTURE_MARGIN}, raster {s0.TEXTURE_NORM_PX} px)   "
          f"TWO_TONE_MAX {s0.TWO_TONE_MAX} (margin {s0.TWO_TONE_MARGIN})")
    print("# cut = alpha cut-out (grain gate alone, route legacy); class_off = stage0_texture_gate=False\n")
    hdr = (f"{'slug':<36} {'kind':<9} {'cut':>3} {'ucm':>7} {'grad':>8} {'tex':>6} {'2tone':>6} "
           f"{'route':<14} {'class_on':<14} {'conf':>5} {'class_off':<14}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows_:
        print(f"{r['slug'][:36]:<36} {r['kind']:<9} {'cut' if r['cutout'] else '  .':>3} "
              f"{r['ucm']:7.4f} {r['grad']:8.4f} {r['texture_frac']:6.3f} {r['two_tone_mass']:6.3f} "
              f"{r['route']:<14} {r['class_on']:<14} {r['conf_on']:5.2f} {r['class_off']:<14}")
    print(f"\n# margins over opaque rows ({m['n_photo']} photo, {m['n_graphic']} graphic; "
          f"{m['n_photo_of_logo']} photo-of-logo rows and every cut-out left out):")
    print(f"#   photo texture min   {m['photo_texture_min']}")
    print(f"#   graphic texture max {m['graphic_texture_max']}   gap {m['texture_gap']}")
    print(f"#   photo two-tone max  {m['photo_two_tone_max']}   graphic two-tone min {m['graphic_two_tone_min']}")


def print_ladder(lad: dict) -> None:
    cells = " ".join(f"{w}:{'-' if v is None else format(v['texture_frac'], '.3f')}"
                     for w, v in lad["widths"].items())
    print(f"{lad['slug'][:36]:<36} native {lad['native_w']:>5}  tex @ {cells}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.stage0_photo_gate",
                                 description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=Path, default=CORPUS_JSON, help="corpus.json (images beside it)")
    ap.add_argument("--fixtures-only", action="store_true")
    ap.add_argument("--ladder", action="store_true", help="the export-width ladder per row")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    paths = [TESTDATA / rel for rel in FIXTURES if (TESTDATA / rel).exists()]
    kinds = {rel: k for rel, k in FIXTURES.items()}
    if not a.fixtures_only:
        cpaths, ckinds = corpus_items(a.corpus)
        paths += cpaths
        kinds.update(ckinds)
    cfg = PipelineConfig(target_width_mm=80.0)
    rows_ = rows(paths, cfg, kinds)
    m = margins(rows_)
    if a.json:
        print(json.dumps({"rows": rows_, "margins": m}, indent=1))
    else:
        print_table(rows_, m)
    if a.ladder:
        print("\n# export-width ladder (PIL LANCZOS downscale; '-' = width above the file's own)")
        for p in paths:
            print_ladder(ladder(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
