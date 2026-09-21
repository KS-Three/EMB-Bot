#!/usr/bin/env python
"""Which enclosed regions would sew, on which garment — the census behind
quality review 2026-09-08 item 9 (plan: docs/superpowers/plans/2026-09-10-
enclosed-by-garment.md).

An enclosed region (the inside of a B, the field a frame surrounds) is
unstitched by a global default whatever the garment. The proposed rule sews
it when the artwork's background colour — the colour stage 1 flooded from
the border, which the hole really is — differs from the GARMENT by more than
`preflight.DELTA_E_VISIBLE`; a hole found through the alpha channel has no
colour of its own (`Prep.bg_from_alpha`, `enclosed_colour_unknown`) and is
left alone, as the 2026-08-15 verdict requires. This prints, per fixture:

  enclosed ..... count, area (mm2) and share of the design's region area
  source ....... alpha (no colour) or flood (the background colour, RGB)
  threads ...... the cones the enclosed regions carry (stage 2's, from the
                 background colour -- what the rule would sew them in)
  per swatch ... dE00 from the background colour to each of the Studio's
                 eight garment swatches, and whether the rule would SEW

    .venv/bin/python tools/enclosed_census.py                 # the 26 corpus fixtures at 80 mm
    .venv/bin/python tools/enclosed_census.py becker_marine_logo.png --width 95.7
    .venv/bin/python tools/enclosed_census.py --json out.json

Nothing here changes stitches; it runs stages 0-4 only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from skimage.color import deltaE_ciede2000  # noqa: E402

from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import run_stages  # noqa: E402
from digitizer_core.preflight import DELTA_E_CLEARLY_DIFFERENT, DELTA_E_VISIBLE  # noqa: E402
from digitizer_core.stage1_prep import _dominant_border_color, prep  # noqa: E402
from digitizer_core.threads import chart_for, rgb_to_lab  # noqa: E402

TESTDATA = ROOT / "testdata"

# GarmentStep.svelte's FABRIC_SWATCHES, verbatim (2026-09-10).
SWATCHES = [
    ("White", (255, 255, 255)),
    ("Natural", (235, 232, 223)),
    ("Sand", (214, 199, 175)),
    ("Red", (179, 35, 45)),
    ("Royal", (32, 64, 150)),
    ("Navy", (25, 34, 60)),
    ("Forest", (30, 79, 52)),
    ("Black", (20, 20, 22)),
]


def _lab(rgb) -> np.ndarray:
    return rgb_to_lab(np.asarray([rgb], dtype=np.uint8))[0]


def census(fixture: str, width_mm: float) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest")
    result = run_stages(TESTDATA / fixture, cfg)
    regions = result.regions
    p = prep(TESTDATA / fixture, cfg)          # stage 1 alone, for bg_from_alpha and the pixels
    chart = chart_for(cfg)
    enclosed = [r for r in regions if r.meta.get("enclosed_background")]
    total = sum(r.area_mm2 for r in regions) or 1e-9
    area = sum(r.area_mm2 for r in enclosed)
    row = {
        "fixture": fixture, "width_mm": width_mm,
        "regions": len(regions), "enclosed": len(enclosed),
        "enclosed_mm2": round(area, 1), "share": round(area / total, 4),
        "source": "alpha" if p.bg_from_alpha else "flood",
        "colour_unknown": sum(1 for r in enclosed if r.meta.get("enclosed_colour_unknown")),
        "threads": sorted({f"{r.thread_number} {chart[r.thread_index].name}" for r in enclosed}),
        "bg_rgb": None, "per_swatch": {},
    }
    if enclosed and not p.bg_from_alpha:
        bg = [int(v) for v in _dominant_border_color(p.rgb)]
        row["bg_rgb"] = bg
        lab_bg = _lab(bg)
        for name, rgb in SWATCHES:
            de = float(deltaE_ciede2000(lab_bg, _lab(rgb)))
            row["per_swatch"][name] = {"de00": round(de, 1), "sews": de > DELTA_E_VISIBLE,
                                       "sews_clearly": de > DELTA_E_CLEARLY_DIFFERENT}
    return row


def print_row(r: dict) -> None:
    stem = Path(r["fixture"]).stem
    head = (f"{stem:28} {r['width_mm']:5.1f} mm  regions {r['regions']:3}  enclosed {r['enclosed']:3}"
            f"  {r['enclosed_mm2']:8.1f} mm2 ({r['share']:6.1%})  {r['source']:5}")
    if not r["enclosed"]:
        print(head + "  -")
        return
    if r["source"] == "alpha":
        print(head + f"  colour unknown on {r['colour_unknown']}: the rule leaves them as they are")
        return
    sew = [n for n, v in r["per_swatch"].items() if v["sews"]]
    clearly = [n for n, v in r["per_swatch"].items() if v["sews_clearly"]]
    keep = [n for n, v in r["per_swatch"].items() if not v["sews"]]
    print(head + f"  bg {tuple(r['bg_rgb'])}  threads {r['threads']}")
    print(f"{'':28}    at {DELTA_E_VISIBLE:g}: sews on {sew or '-'}, a hole on {keep or '-'}  |  "
          f"at {DELTA_E_CLEARLY_DIFFERENT:g}: sews on {clearly or '-'}")
    print(f"{'':28}    dE00 {', '.join(f'{n} {v['de00']}' for n, v in r['per_swatch'].items())}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/; default: the 26 corpus fixtures")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    fixtures = a.fixtures
    if not fixtures:
        from tools.corpus_scorecard import FIXTURES
        fixtures = list(FIXTURES)
    print(f"# enclosed census — DELTA_E_VISIBLE {DELTA_E_VISIBLE}; a hole SEWS on a garment when its "
          f"background colour is further than that from the swatch\n")
    rows = []
    for fx in fixtures:
        try:
            r = census(fx, a.width)
        except Exception as exc:  # noqa: BLE001 — one bad fixture must not sink the census
            print(f"{Path(fx).stem:28} ERROR {type(exc).__name__}: {exc}")
            continue
        rows.append(r)
        print_row(r)
    with_holes = [r for r in rows if r["enclosed"]]
    flood = [r for r in with_holes if r["source"] == "flood"]
    print(f"\n{len(with_holes)} of {len(rows)} fixtures carry enclosed regions; {len(flood)} have a colour "
          f"(flood), {len(with_holes) - len(flood)} are alpha (colour unknown).")
    for name, _rgb in SWATCHES:
        n = sum(1 for r in flood if r["per_swatch"][name]["sews"])
        mm2 = sum(r["enclosed_mm2"] for r in flood if r["per_swatch"][name]["sews"])
        n2 = sum(1 for r in flood if r["per_swatch"][name]["sews_clearly"])
        print(f"  on {name:8}: at {DELTA_E_VISIBLE:g} the rule sews the holes of {n} fixtures ({mm2:8.1f} mm2); "
              f"at {DELTA_E_CLEARLY_DIFFERENT:g}, {n2}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1))
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
