"""Defect 2: what `cfg.satin_floor_content_gate` changes, OFF vs ON.

    python -m tools.floor_content_gate [--photo] [--logos] [--out FILE.json]

Each arm digitizes once (`run_stages`) and plans twice (flag OFF, ON) on that
one result, so a difference is the flag and nothing else.

Per fixture it records:
  * detected    -- did `detect_photographic` fire (EXIF / face)?
  * verdicts    -- regions `classify_ribbon` sends to `photo_width_floor`
  * reroutes    -- shapes whose emitted stitches differ OFF vs ON

Arms: `default` (no declaration, flag has nothing to act on: ON must equal OFF),
`declared` (`is_photographic=True`, the Studio's "It's a photo"), `detect`
(`detect_photographic=True`), and `forced_photo` (the Aug-22 reference route:
`forced_class="photo_subject"`, verdict count only).

Takes a CPU slot (`$TEMP/embwt/cpu.lock` or `cpu.lock2`) for the whole run:
the laptop is shared. Nothing here is committed output; the numbers go in the
PR body.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PHOTO = ["drone_render.png", "summit_badge.png",
         "logo_drone_thermal_badge.png", "owl_kent.jpg"]
LOGOS = ["logo_bridge_bar.jpg", "logo_golden_tee.jpg", "logo_hotel_fremont.webp",
         "logo_gaulke_roofing.png", "enthusiast_logo.png"]


def _take_slot():
    tmp = os.environ.get("TEMP") or os.environ.get("TMP")
    base = Path(tmp) / "embwt"
    while True:
        for name in ("cpu.lock", "cpu.lock2"):
            d = base / name
            try:
                d.mkdir()
            except FileExistsError:
                continue
            (d / "holder.txt").write_text(
                "floor_content_gate (defect 2 measurement)\n"
                f"taken {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
            return d
        time.sleep(2)


def _release(d: Path):
    try:
        (d / "holder.txt").unlink()
    except OSError:
        pass
    d.rmdir()


def _sig(plan) -> dict[str, tuple[str, frozenset]]:
    by: dict[str, list] = {}
    for _b, r in plan.iter_runs():
        by.setdefault(r.shape_id, []).append(
            (r.kind, [(round(x, 3), round(y, 3)) for x, y in r.points]))
    return {k: (hashlib.md5(repr(v).encode()).hexdigest(),
                frozenset(kind for kind, _ in v)) for k, v in by.items()}


def _verdicts(result, cfg, floor_applies: bool) -> tuple[int, int]:
    """-> (photo_width_floor verdicts, regions judged satin without the floor)."""
    from digitizer_core.machine import satin_ceiling_mm
    from digitizer_core.stage6_satin import classify_ribbon
    mx = satin_ceiling_mm(cfg)
    n = 0
    for r in result.regions:
        v = classify_ribbon(r.polygon, mx, design_class=result.design_class,
                            floor_applies=floor_applies)
        n += v.reason == "photo_width_floor"
    return n, len(result.regions)


def arm(img: Path, name: str, cfg0, plan_it=True) -> dict:
    from digitizer_core.config import satin_floor_applies
    from digitizer_core.pipeline import plan_stitches, run_stages
    t = time.time()
    off = replace(cfg0, satin_floor_content_gate=False)
    on = replace(cfg0, satin_floor_content_gate=True)
    result = run_stages(str(img), off)
    from digitizer_core.photo_signals import apply_detection
    folded = apply_detection(on, result.detected_photographic)
    applies = satin_floor_applies(folded, result.design_class)
    row = {"arm": name, "class": result.design_class,
           "detected": bool(result.detected_photographic),
           "floor_applies": applies,
           "regions": len(result.regions)}
    # verdicts: class floor only (applies False) vs content gate widened
    row["verdicts_off"] = _verdicts(result, off, False)[0]
    row["verdicts_on"] = _verdicts(result, folded, applies)[0]
    if plan_it:
        a, b = _sig(plan_stitches(result, off)), _sig(plan_stitches(result, on))
        # reroutes: a shape that sewed satin OFF and sews no satin ON -- the
        # Aug-22 "emitted-stitch reroute". `changed` also counts knock-on
        # shapes whose travel or trims moved.
        row["reroutes"] = sum(1 for k in a if "satin" in a[k][1]
                              and "satin" not in b.get(k, ("", frozenset()))[1])
        row["changed"] = sum(1 for k in set(a) | set(b) if a.get(k) != b.get(k))
        row["plan_identical"] = a == b
    row["secs"] = round(time.time() - t, 1)
    return row


def main():
    from digitizer_core.config import PipelineConfig
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", action="store_true")
    ap.add_argument("--logos", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--have-slot", default="",
                    help="a CPU slot dir this run already owns")
    a = ap.parse_args()
    photo_dir = ROOT / "testdata" / "photo"
    slot = Path(a.have_slot) if a.have_slot else _take_slot()
    rows = []
    try:
        def emit(fx, r):
            r["fixture"] = fx
            rows.append(r)
            print(json.dumps(r), flush=True)
            if a.out:
                Path(a.out).write_text(json.dumps(rows, indent=1))
        if a.photo:
            for fx in PHOTO:
                img = photo_dir / fx
                emit(fx, arm(img, "default", PipelineConfig()))
                emit(fx, arm(img, "declared", PipelineConfig(is_photographic=True)))
                emit(fx, arm(img, "detect", PipelineConfig(detect_photographic=True)))
                emit(fx, arm(img, "forced_photo",
                             PipelineConfig(forced_class="photo_subject"),
                             plan_it=False))
        if a.logos:
            for fx in LOGOS:
                img = photo_dir / fx
                emit(fx, arm(img, "default", PipelineConfig()))
                emit(fx, arm(img, "detect", PipelineConfig(detect_photographic=True)))
    finally:
        _release(slot)


if __name__ == "__main__":
    main()
