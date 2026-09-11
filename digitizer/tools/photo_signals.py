#!/usr/bin/env python
"""What the two photograph signals say about every committed artwork.

Quality review 2026-09-08 item 13; the reader is
`digitizer_core/photo_signals.py` and this is the CLI over it. For each
fixture: the EXIF camera, the YuNet face count on the stage-1 prep raster,
stage 0's class, and the verdict `config.is_photographic` reaches with
`cfg.detect_photographic` ON against the one it reaches with it off.

The wiring landed 2026-09-11 (stage 1.25 in `pipeline.build_generation`),
DEFAULT OFF. This stays the way to re-measure the corpus after either signal
changes — the suite pins the false-positive count, this prints the table.

The number that matters here is the FALSE POSITIVE count — a logo that
trips either signal would gain the photographic machinery it must not have,
and that is the risk this build carries. The true-positive side rests on
the 2026-08-25 measurement (4/4 photos by EXIF, 4/4 portraits by face) plus
whatever real photographs are reachable: `owl_kent.jpg` is committed and is
the blind-spot case — re-saved so no EXIF, an owl so no face — which is why
the declaration stays.

    .venv/bin/python tools/photo_signals.py            # the committed corpus
    .venv/bin/python tools/photo_signals.py --art PATH
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import photo_signals as ps                 # noqa: E402
from digitizer_core.config import PHOTO_CLASSES, PipelineConfig  # noqa: E402
from digitizer_core.stage0_classify import classify            # noqa: E402
from digitizer_core.stage1_prep import prep                    # noqa: E402

TESTDATA = ROOT / "testdata"

# label -> what the artwork IS, by hand. `photo` means a real photograph;
# `synthetic-photo` means this repo's own generator wrote it
# (`tools/make_photo_fixtures.py`) and it is a photograph only in style.
CORPUS: dict[str, str] = {
    "becker_marine_logo.png": "logo",
    "logo_script_tires.png": "logo",
    "logo_whitebg.png": "logo",
    "logo_alpha.png": "logo",
    "ribbon_curve.png": "logo",
    "bg_uncertain.png": "logo",
    "photo/enthusiast_logo.png": "logo",
    "photo/logo_hotel_fremont.webp": "logo",
    "photo/logo_bridge_bar.jpg": "logo",
    "photo/logo_gaulke_roofing.png": "logo",
    "photo/logo_golden_tee.jpg": "logo",
    "photo/screenshot_phone_ui_golke.jpg": "logo",
    "photo/drone_render.png": "logo",
    "photo/summit_badge.png": "logo",
    "photo/owl_kent.jpg": "photo",
    "photo/photo_owl_pale.png": "synthetic-photo",
    "photo/photo_dof_meadow.png": "synthetic-photo",
    "photo/photo_grass_macro.png": "synthetic-photo",
    "photo/photo_sunset_backlit.png": "synthetic-photo",
    "photo/photo_chrome_specular.png": "synthetic-photo",
    "photo/photo_scene_stub.png": "synthetic-photo",
    "photo/photo_subject_stub.png": "synthetic-photo",
}

ACCEPTANCE = TESTDATA / "photo" / "acceptance"
ACCEPTANCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def rows(extra: list[Path] | None = None):
    out = [(rel, kind, TESTDATA / rel) for rel, kind in CORPUS.items()
           if (TESTDATA / rel).exists()]
    if ACCEPTANCE.is_dir():
        out += [(f"acceptance/{p.name}", "photo", p) for p in sorted(ACCEPTANCE.iterdir())
                if p.suffix.lower() in ACCEPTANCE_SUFFIXES]
    out += [(str(p), "?", p) for p in (extra or [])]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--art", type=Path, action="append", default=None)
    a = ap.parse_args(argv)

    cfg = PipelineConfig()
    head = (f"{'artwork':<40} {'is':<16} {'class':<13} {'EXIF camera':<22} "
            f"{'faces':>6}  {'detected':<9} {'today':<7} {'with detection':<14}")
    print(head)
    print("-" * len(head))
    wrong_positive, wrong_negative, unavailable = [], [], None
    for rel, kind, path in rows(a.art):
        try:
            klass = classify(path, cfg, forced_class=None).class_
            sig = ps.detect(path, prep(path, cfg).rgb, cfg)
        except Exception as exc:                      # noqa: BLE001
            print(f"{rel:<40} {kind:<16} ERROR {type(exc).__name__}: {exc}")
            continue
        if sig.faces is None:
            unavailable = sig.face_reason
        today = klass in PHOTO_CLASSES
        with_det = today or sig.is_photograph is True
        print(f"{rel:<40} {kind:<16} {klass:<13} {str(sig.exif_camera or '—'):<22} "
              f"{('n/a' if sig.faces is None else sig.faces):>6}  "
              f"{str(sig.is_photograph):<9} {str(today):<7} {str(with_det):<14}")
        if kind == "logo" and sig.is_photograph is True:
            wrong_positive.append(rel)
        if kind == "photo" and sig.is_photograph is not True:
            wrong_negative.append(rel)

    print(f"\nfalse positives (a LOGO a signal called a photograph): "
          f"{len(wrong_positive)}{' — ' + ', '.join(wrong_positive) if wrong_positive else ''}")
    print(f"real photographs NEITHER signal catches: "
          f"{len(wrong_negative)}{' — ' + ', '.join(wrong_negative) if wrong_negative else ''}"
          f"  (the declaration's reason for existing)")
    if unavailable:
        print(f"\n[note] the face detector could not run here: {unavailable} — "
              f"the EXIF half still measured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
