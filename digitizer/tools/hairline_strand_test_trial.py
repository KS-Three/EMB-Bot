"""The line route's strand test on the real photo (2026-10-13).

    python -m tools.hairline_strand_test_trial --arm off40     # one plan per call
    python -m tools.hairline_strand_test_trial --arm lines40
    python -m tools.hairline_strand_test_trial --arm strand40
    python -m tools.hairline_strand_test_trial --drawn         # hair_strands, hair_fine
    python -m tools.hairline_strand_test_trial --compose       # strips, census, table

Follows #882 (`cfg.hairline_from_lines`): on `testdata/photo/owl_kent.jpg` only
5 of the line route's 75 strands reached the facial bristles and 31 were the
breast barring. This measures `cfg.hairline_lines_strand_test`
(`stage6_hairline_lines.stack_share`) on #882's route: `classical` (photo lane,
`photo_prep=False`), 40 wt, 127 mm. Arms: `off40` (hairline off), `lines40`
(#882's line route), `strand40` (the line route with the strand test).

Per arm: stitches, trims, colour changes, thread laid, stitches under 1 mm,
the `HAIRLINE_TIER_SEWN` census, where the sewn strands land (#882's zones, by
each run's centroid on the photo), and bare fabric new against `off40`
(`tools.hairline_renders.bare_cells`, the instrument `tools.hairline_coverage`
reads). `--drawn` checks the drawn hair fixtures are unchanged by the flag.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitchviz  # noqa: E402
from digitizer_core.adapter import UNITS_PER_MM, plan_to_design  # noqa: E402
from digitizer_core.pipeline import digitize, plan_stitches, run_stages  # noqa: E402
from tools.hairline_lines_trial import (PHOTO, ROUTE, SYN, WIDTH_MM, ZONES,  # noqa: E402
                                        measure, write_jpeg)
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402

# arm -> (cfg.hairline, cfg.hairline_from_lines, cfg.hairline_lines_strand_test)
ARMS = {"off40": (False, False, False), "lines40": (True, True, False),
        "strand40": (True, True, True)}
LABELS = {"lines40": "strand test OFF (#882)", "strand40": "strand test ON"}
# Boxes as fractions of the SOURCE photo, and the render scale: the beak and
# its bristle field (#882's `beak`), a 9 mm patch of the bristles (#882's
# `zoom`), and the barred left breast.
BOXES = {"beak": ((0.36, 0.18, 0.68, 0.48), 16.0),
         "bristles": ((0.45, 0.24, 0.52, 0.31), 40.0),
         "breast": ((0.04, 0.62, 0.40, 0.98), 16.0)}
PARTS = ROOT / "debug_out" / "hairline_strand_test_trial"
OUT = ROOT.parent / "docs" / "renders" / "claude-hairline-lines-strand-test"


def arm_cfg(arm: str) -> PipelineConfig:
    on, lines, test = ARMS[arm]
    return PipelineConfig(target_width_mm=WIDTH_MM, hairline=on, hairline_from_lines=lines,
                          hairline_lines_strand_test=test, thread_wt=40, **ROUTE)


def zone_of(sp, pts) -> str:
    h, w = sp.rgb.shape[:2]
    fx, fy = np.array([sp.to_px(x, y) for x, y in pts]).mean(axis=0) / [w, h]
    return next((z for z, (x0, y0, x1, y1) in ZONES.items()
                 if x0 <= fx < x1 and y0 <= fy < y1), "elsewhere")


def strand_zones(plan, sp) -> dict:
    """Sewn line-route runs per zone: count and thread mm."""
    out = {z: {"strands": 0, "mm": 0.0} for z in list(ZONES) + ["elsewhere"]}
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id != "hairline_lines" or len(r.points) < 2:
                continue
            z = zone_of(sp, r.points)
            out[z]["strands"] += 1
            out[z]["mm"] = round(out[z]["mm"] + sum(
                math.dist(a, c) for a, c in zip(r.points, r.points[1:])), 1)
    return out


def render_parts(design: dict, sp, arm: str) -> None:
    for name, (box, ppm) in BOXES.items():
        img = stitchviz.render_design(design, px_per_mm=ppm,
                                      thread_mm=machine.thread_profile(40).width_mm)
        _size, to_px = stitchviz._frame(design.get("stitches") or [], ppm, 2.0)
        h, w = sp.rgb.shape[:2]
        fx0, fy0, fx1, fy1 = box
        x0, y0 = sp.to_mm(fx0 * w, fy0 * h)
        x1, y1 = sp.to_mm(fx1 * w, fy1 * h)
        a = to_px({"x": x0 * UNITS_PER_MM, "y": -y0 * UNITS_PER_MM})
        b = to_px({"x": x1 * UNITS_PER_MM, "y": -y1 * UNITS_PER_MM})
        px0, px1 = sorted((max(a[0], 0), max(b[0], 0)))
        py0, py1 = sorted((max(a[1], 0), max(b[1], 0)))
        cv2.imwrite(str(PARTS / f"{arm}_{name}.png"), img[py0:py1, px0:px1])


def source_parts(sp) -> None:
    h, w = sp.rgb.shape[:2]
    for name, (box, ppm) in BOXES.items():
        fx0, fy0, fx1, fy1 = box
        crop = sp.rgb[int(fy0 * h):int(fy1 * h), int(fx0 * w):int(fx1 * w)]
        k = ppm / sp.px_per_mm
        big = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(PARTS / f"source_{name}.png"), cv2.cvtColor(big, cv2.COLOR_RGB2BGR))


def census_map(sp, k: int = 3) -> None:
    """Every ridge the line route keeps, on the photo: sewn dark strands
    red, sewn light strands blue, refused by the strand test as a bar
    magenta, under the loop floor green. Lines the ridge test refuses are
    left out (#882's census shows them)."""
    from digitizer_core.stage6_hairline_lines import extract_strands
    cfg_off, cfg_on = arm_cfg("lines40"), arm_cfg("strand40")
    off, _ = extract_strands(sp, cfg_off)
    on, _ = extract_strands(sp, cfg_on)
    kept = {id_key(s) for s in on}
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)
    for s in off:
        if s["length_mm"] < machine.RUN_MIN_LOOP_MM:
            colour = (0, 170, 0)
        elif id_key(s) not in kept:
            colour = (200, 0, 200)
        else:
            colour = (0, 0, 230) if s["polarity"] == "dark" else (230, 160, 0)
        q = np.array([sp.to_px(x, y) for x, y in s["pts"]]) * k
        cv2.polylines(big, [np.round(q).astype(np.int32)], False, colour, 2, cv2.LINE_AA)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jpeg(OUT / "owl_strand_census.jpg", big)


def id_key(s) -> tuple:
    return (s["polarity"], tuple(map(tuple, s["pts"])))


def run_arm(arm: str) -> dict:
    cfg = arm_cfg(arm)
    result = run_stages(PHOTO, cfg)
    plan = plan_stitches(result, cfg)
    row = measure(plan)
    p = preflight.prep(PHOTO, cfg, design_class=result.design_class)
    bare = bare_cells(plan, result, p)
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    npz = PARTS / "off40_bare.npz"
    if arm == "off40":
        np.savez_compressed(npz, grid=bare[0], origin=np.array(bare[1]), cell=bare[2])
        row["bare_new_mm2"] = 0.0
    elif npz.exists():
        z = np.load(npz)
        row["bare_new_mm2"] = round(bare_new_mm2(
            bare, (z["grid"], tuple(z["origin"]), float(z["cell"]))), 2)
    if result.source_pixels is not None:
        row["zones"] = strand_zones(plan, result.source_pixels)
        design = plan_to_design(plan, name=f"owl {arm}")
        render_parts(design, result.source_pixels, arm)
        source_parts(result.source_pixels)
    (PARTS / f"{arm}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    return row


def run_drawn() -> dict:
    """The drawn hair fixtures (gradient lane): the flag must change
    nothing, with the line route on and with the hairline tier alone."""
    out = {}
    for fixture in ("hair_strands.png", "hair_fine.png"):
        row = {}
        for arm, kw in (("on40", dict(hairline=True)),
                        ("on40_test", dict(hairline=True, hairline_lines_strand_test=True)),
                        ("lines40", dict(hairline=True, hairline_from_lines=True)),
                        ("strand40", dict(hairline=True, hairline_from_lines=True,
                                          hairline_lines_strand_test=True))):
            result, plan = digitize(SYN / fixture, PipelineConfig(target_width_mm=80.0, **kw))
            m = measure(plan)
            m["design_class"] = result.design_class
            row[arm] = m
        row["identical"] = len({row[a]["md5"] for a in row}) == 1
        out[fixture] = row
        print(fixture, json.dumps({a: (r["md5"], r["stitches"]) for a, r in row.items()
                                   if isinstance(r, dict)}), row["identical"], flush=True)
    (PARTS / "drawn.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def strip(panels: list[tuple[Path, str]], dest: Path) -> None:
    tiles = []
    for f, label in panels:
        img = cv2.imread(str(f))
        if img is None:
            print("missing", f)
            return
        band = np.full((34, img.shape[1], 3), 255, np.uint8)
        cv2.putText(band, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2,
                    cv2.LINE_AA)
        tiles.append(np.vstack([band, img]))
    h = min(t.shape[0] for t in tiles)
    w = min(t.shape[1] for t in tiles)
    sep = np.full((h, 8, 3), 255, np.uint8)
    row = []
    for t in tiles:
        row += [t[:h, :w], sep]
    write_jpeg(dest, np.hstack(row[:-1]))


def compose() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    arms = [a for a in ARMS if (PARTS / f"{a}.json").exists()]
    for name, (_box, ppm) in BOXES.items():
        strip([(PARTS / f"source_{name}.png", f"photo ({ppm:g} px/mm)")]
              + [(PARTS / f"{a}_{name}.png", LABELS[a]) for a in LABELS if a in arms],
              OUT / f"owl_{name}_{int(ppm)}pxmm.jpg")
    rows = {a: json.loads((PARTS / f"{a}.json").read_text(encoding="utf-8")) for a in arms}
    drawn = (json.loads((PARTS / "drawn.json").read_text(encoding="utf-8"))
             if (PARTS / "drawn.json").exists() else {})
    (OUT / "table.json").write_text(json.dumps({"owl_classical_40wt": rows, "drawn": drawn},
                                               indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=list(ARMS))
    ap.add_argument("--drawn", action="store_true")
    ap.add_argument("--census", action="store_true",
                    help="the census map (stages only, no plan)")
    ap.add_argument("--compose", action="store_true")
    ap.add_argument("--parts", type=Path, help="scratch folder for the per-arm parts "
                    "(default debug_out/hairline_strand_test_trial)")
    args = ap.parse_args(argv)
    global PARTS
    if args.parts:
        PARTS = args.parts
    PARTS.mkdir(parents=True, exist_ok=True)
    if args.arm:
        print(args.arm, json.dumps(run_arm(args.arm)), flush=True)
    if args.census:
        census_map(run_stages(PHOTO, arm_cfg("lines40")).source_pixels)
    if args.drawn:
        run_drawn()
    if args.compose:
        compose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
