#!/usr/bin/env python
"""Legibility of lettering, read by OCR on the RENDER against the artwork.

PR 1 of `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`,
and the phase-1 exit instrument for "lost": `docs/kent-review-2026-09-03.md`
records `dropped_elements` reading 0.2% on Hotel Fremont while Kent calls its
tagline "completely lost" — the instrument sees sewn-but-illegible as
covered, and nothing in this repo reads what the thread SAYS.

This does (the measurement lives in `digitizer_core/legibility.py` since
2026-09-10, when preflight's `LETTERING_ILLEGIBLE` check took it up — quality
review item 11; this file is the CLI over it). For every text cluster stage 4 tagged (`meta["text_cluster_id"]`,
`textcluster.detect_text_clusters`), it crops the same millimetres out of the
prepped artwork and out of `stitchviz.render_design`'s thread render, runs
tesseract on both, and reports the normalised edit similarity between the
two readings — 1.0 when the thread says what the art says, 0.0 when the art
reads and the thread does not. The design-level figure is weighted by the
length of the artwork reading, so a cluster tesseract cannot read on the ART
side contributes nothing rather than a false zero. When a design has no text
cluster, the whole artwork and the whole render are read once, as one row.

Gate 4: a per-cluster edit similarity is a distance, not an agreement rate,
and no chance floor is claimed for it. It is also not a quality score — a
design can read perfectly and sew badly — it answers one question the eye
has been asking and no number could: is the lettering still there.

Needs the `tesseract` binary. CI installs it; a box without it gets the
same skip the OCR tests take (`tests/conftest.py`, `requires_tesseract`).

    .venv/bin/python tools/legibility.py photo/logo_hotel_fremont.webp --width 92.5 --garment patch
    .venv/bin/python tools/legibility.py --corpus [--dump DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                              # noqa: E402
from digitizer_core.legibility import (  # noqa: E402,F401 — re-exported for tests/test_legibility.py and callers
    ART_CONF_MIN, ART_MIN_LETTERS, CROP_PAD_MM, OCR_BORDER_PX, OCR_MIN_HEIGHT_PX, OCR_MODES, RENDER_CONF_MIN,
    RENDER_MASK_GROW_MM, RENDER_PAD_MM, RENDER_PX_PER_MM, VARIANTS_MM, art_crop, cluster_boxes,
    cluster_members, measure, normalise, ocr, prepare_for_ocr, read_pair, read_side, render_crop,
    render_to_px, similarity, tesseract_available)
from digitizer_core.pipeline import (build_generation, finish_generation,  # noqa: E402
                                     plan_stitches)
from thin_strokes import corpus_cases, parse_flags              # noqa: E402


def run(art: Path, width_mm: float, garment: str, forced_class: str | None = None,
        dump: Path | None = None, flag=None) -> dict:
    extra = parse_flags(flag)
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment, forced_class=forced_class, **extra)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    out = measure(gen.p, result, plan, dump=dump, name=art.stem)
    out.update({"fixture": str(art), "width_mm": width_mm, "garment": garment,
                "design_class": result.design_class})
    return out


def _print(name: str, r: dict) -> None:
    leg = "  n/a" if r["legibility"] is None else f"{r['legibility']:5.2f}"
    drop = "  n/a" if r["confidence_drop"] is None else f"{r['confidence_drop']:+5.1f}"
    print(f"  {name:12} {r['design_class']:12} clusters {r['clusters']:3d} art readable {r['readable_on_art']:3d} "
          f"render readable {r['render_readable']:3d}  legibility {leg}  confidence drop {drop}")
    for row in r["rows"]:
        sim = "  n/a" if row["similarity"] is None else f"{row['similarity']:5.2f}"
        tag = " enclosed" if row.get("enclosed") else ""
        print(f"      {row['cluster'][:16]:16} {row['height_mm']:5.1f} mm  art {normalise(row['art_text'])[:20]:20} "
              f"({row['art_conf']:4.0f})  render {normalise(row['render_text'])[:20]:20} ({row['render_conf']:4.0f})  "
              f"{sim}  psm {row['psm']}{tag}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixture", nargs="?")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--forced-class", default=None, dest="forced_class")
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--dump", type=Path, default=None, help="write the OCR crops here")
    ap.add_argument("--flag", action="append", default=None,
                    help="PipelineConfig field to turn on, NAME or NAME=VALUE (repeatable)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.flag:
        try:
            parse_flags(a.flag)
        except ValueError as e:
            ap.error(str(e))
    if not tesseract_available():
        print("tesseract binary not on PATH — nothing measured (CI installs tesseract-ocr)")
        return 2
    if not a.corpus and not a.fixture:
        ap.error("a fixture or --corpus")
    if a.dump is not None:
        a.dump.mkdir(parents=True, exist_ok=True)
    if a.corpus:
        cases = corpus_cases()
    else:
        art = Path(a.fixture)
        if not art.exists():
            art = ROOT / "testdata" / a.fixture
        cases = [(art.stem, art, a.width, a.garment)]
    results = []
    for name, art, w, g in cases:
        r = run(art, w, g, a.forced_class, a.dump, a.flag)
        results.append(r)
        _print(name, r)
    if a.json:
        print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
