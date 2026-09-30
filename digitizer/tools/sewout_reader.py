"""Read the sew-out card back off a PHOTO — command line. The reader lives
in `digitizer_core.calibration.reader` (the service's `/calibration/read`
runs it); this is the terminal front and the `--simulate` harness that
fakes a phone photo with planted distortions and scores the reader.

Usage (from digitizer/):
    .venv/bin/python tools/sewout_reader.py --simulate [--px-per-mm 12] [--out DIR]
    .venv/bin/python tools/sewout_reader.py --photo card.jpg [--corners x,y x,y x,y x,y]
        [--design debug_out/sewout/EMBBOT_SEWOUT_CARD.design.json] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitizer_core.calibration.card import OUT                          # noqa: E402
from digitizer_core.calibration.reader import (                          # noqa: E402
    Distortion, compare, distort, overlay, read_card, read_reference,
    render_reference, simulate_photo, with_fiducials)

DEFAULT_DESIGN = OUT / "EMBBOT_SEWOUT_CARD.design.json"


def _load_design(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"{path} not found — build it: PYTHONPATH=. .venv/bin/python tools/sewout_card.py")
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _cli_simulate(design: dict, px_per_mm: float, out: Path | None, seed: int) -> None:
    truth = [Distortion("satin-4mm", dx_mm=0.4, dy_mm=-0.3),
             Distortion("satin-5mm", dx_mm=0.4, dy_mm=-0.5),
             Distortion("fill-B-0.20", dx_mm=-0.4, dy_mm=0.0),
             Distortion("seam-A-0", dx_mm=-2.0, dy_mm=0.0)]
    bent = distort(design, truth)
    photo, true_corners = simulate_photo(bent, px_per_mm, seed=seed)
    ref = read_reference(design)
    report = {"photo_px_per_mm": px_per_mm, "truth": [asdict(t) for t in truth], "modes": {}}
    for mode in ("corners", "auto", "fiducials"):
        try:
            if mode == "fiducials":
                fid = with_fiducials(bent)
                p2, _ = simulate_photo(fid, px_per_mm, seed=seed)
                rd = read_card(p2, with_fiducials(design), mode="fiducials")
            else:
                rd = read_card(photo, design, corners_px=true_corners, mode=mode)
        except ValueError as e:
            report["modes"][mode] = {"error": str(e)}
            continue
        cmp = compare(rd, ref)
        report["modes"][mode] = {"ecc": rd["ecc"], "compare": cmp}
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            shown = design if mode != "fiducials" else with_fiducials(design)
            ov = overlay(rd["_rectified"], shown, rd)
            cv2.imwrite(str(out / f"overlay_{mode}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / "sim_photo.jpg"), photo, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(out / "render_reference.png"), render_reference(design))
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for mode, r in report["modes"].items():
        print(f"== {mode} ==")
        if "error" in r:
            print("  ", r["error"])
            continue
        for row in r["compare"]["features"]:
            if row["role"] in ("bar", "square"):
                print(f"  {row['name']:<14} dW {row['d_width_mm']!s:>7} "
                      f"dH {row['d_height_mm']!s:>7} dC {row['d_coverage']!s:>8}")
        print("   seams:", r["compare"]["seam_gap_delta_mm"])
        print("   draft:", {k: v for k, v in r["compare"]["draft_profile_delta"].items() if k != "basis"})


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    ap.add_argument("--photo", type=Path, help="a photo of the sewn card")
    ap.add_argument("--corners", nargs=4, metavar="x,y",
                    help="pixel corners of the sewn bbox: TL TR BR BL")
    ap.add_argument("--mode", choices=("auto", "corners", "fiducials"), default=None)
    ap.add_argument("--ocr", action="store_true", help="read the words with tesseract when present")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--overlay", type=Path, help="write the rectified photo with readings drawn on")
    ap.add_argument("--simulate", action="store_true", help="fake a photo with known distortions and score the reader")
    ap.add_argument("--px-per-mm", type=float, default=12.0, help="simulated phone resolution")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, help="--simulate: directory for the photo, overlays and report")
    a = ap.parse_args(argv)

    design = _load_design(a.design)
    if a.simulate:
        _cli_simulate(design, a.px_per_mm, a.out, a.seed)
        return
    if a.photo is None:
        ap.error("--photo or --simulate")
    img = cv2.imread(str(a.photo), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"cannot read {a.photo}")
    corners = None
    mode = a.mode or ("corners" if a.corners else "auto")
    if a.corners:
        corners = np.array([[float(v) for v in c.split(",")] for c in a.corners], np.float32)
    rd = read_card(img, design, corners_px=corners, mode=mode, ocr=a.ocr)
    ref = read_reference(design, ocr=a.ocr)
    result = {"photo": _strip(rd), "reference": _strip(ref), "compare": compare(rd, ref)}
    if a.overlay:
        cv2.imwrite(str(a.overlay), overlay(rd["_rectified"], design, rd))
    if a.json:
        a.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["compare"], indent=2))


if __name__ == "__main__":
    main()
