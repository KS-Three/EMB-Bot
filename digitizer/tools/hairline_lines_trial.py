"""Hairline strands from LINES on the real photo (2026-10-13).

    python -m tools.hairline_lines_trial --arm off40      # one plan per call
    python -m tools.hairline_lines_trial --arm on40
    python -m tools.hairline_lines_trial --arm lines40
    python -m tools.hairline_lines_trial --drawn          # hair_strands, hair_fine
    python -m tools.hairline_lines_trial --compose        # strips + table

Follows #876 (docs/hairline-photo-trial-2026-10-12.md): on
`testdata/photo/owl_kent.jpg` the region tier sewed 3 strands and dropped 10,
because the segmenter merges the bristles into a few ragged regions. This
measures `cfg.hairline_from_lines` (`stage6_hairline_lines`), which takes the
strands from FDoG lines instead, against OFF and the region tier, on #876's
`classical` route (photo lane, `photo_prep=False`: what a machine without
the rembg venv runs, so it reproduces anywhere), 40 wt, 127 mm.

One arm per process, OFF first: a plan on this photo takes up to ~25 min on
a loaded laptop, and each arm's bare-fabric read compares against OFF's,
saved beside it. Per arm: stitches, trims, colour changes, thread laid,
stitches under the needle's 1.0 mm floor (not counting 0.8 mm lock legs),
strands sewn / dropped (`HAIRLINE_TIER_SEWN`), and bare fabric
(`tools.hairline_renders.bare_cells`, preflight's uncovered-artwork
instrument) new against OFF.

`--drawn` runs the drawn hair fixtures with the region tier and with the
line route on, and reports whether the plans are identical (they should be:
the line route only applies on a raster lane, and a drawn fixture is flat).

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import hashlib
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
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402

PHOTO = ROOT / "testdata" / "photo" / "owl_kent.jpg"
SYN = ROOT / "testdata" / "synthetic"
WIDTH_MM = 127.0
ROUTE = {"forced_class": "photo_subject", "photo_prep": False}
# arm -> (cfg.hairline, cfg.hairline_from_lines, cfg.thread_wt)
ARMS = {"off40": (False, False, 40), "on40": (True, False, 40),
        "lines40": (True, True, 40), "off60": (False, False, 60),
        "lines60": (True, True, 60)}
LABELS = {"off40": "OFF", "on40": "hairline ON (regions)",
          "lines40": "hairline ON + from_lines"}
# Boxes as fractions of the SOURCE photo (x0, y0, x1, y1): the beak and the
# bristle field round it (#876's `beak` box), and a 9 mm patch of the
# bristles above-left of the beak, where the line route sews its dark
# strands, for the 40 px/mm zoom.
BOXES = {"beak": ((0.36, 0.18, 0.68, 0.48), 16.0),
         "zoom": ((0.45, 0.24, 0.52, 0.31), 40.0)}
# Where the sewn strands land, by the strand's centroid as a fraction of the
# source (first match wins): the facial bristles round the beak (the target
# hair), the eyes, the barred breast; "elsewhere" is mostly the wispy
# feather tips at the head's outline and the fence.
ZONES = {"beak_bristles": (0.36, 0.18, 0.68, 0.48),
         "eyes": (0.25, 0.12, 0.75, 0.25),
         "breast": (0.0, 0.55, 1.0, 1.0)}
MAX_JPEG_BYTES = 400_000
PARTS = ROOT / "debug_out" / "hairline_lines_trial"
OUT = ROOT.parent / "docs" / "renders" / "claude-hairline-fdog-lines"


def arm_cfg(arm: str) -> PipelineConfig:
    on, lines, wt = ARMS[arm]
    return PipelineConfig(target_width_mm=WIDTH_MM, hairline=on,
                          hairline_from_lines=lines, thread_wt=wt, **ROUTE)


def plan_md5(plan) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def short_stitches(plan) -> int:
    """Stitches 0.01-1.0 mm that are not 0.8 mm lock legs."""
    n = 0
    for b in plan.blocks:
        for r in b.runs:
            for a, c in zip(r.points, r.points[1:]):
                d = math.dist(a, c)
                if 0.01 < d < machine.MIN_STITCH_MM and abs(d - machine.TIE_STITCH_MM) > 1e-6:
                    n += 1
    return n


def measure(plan) -> dict:
    st = plan.stats
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    hair = None
    if w:
        hair = {k: w[0].get(k) for k in ("shapes", "strands", "dropped", "source",
                                          "found", "refused_no_ridge", "sewn_by_polarity")
                if k in w[0]}
    line_runs = [r for b in plan.blocks for r in b.runs if r.shape_id == "hairline_lines"]
    return {
        "md5": plan_md5(plan),
        "stitches": st.stitch_count,
        "trims": st.trims,
        "color_changes": st.color_changes,
        "thread_m": round(sum(math.dist(a, c) for b in plan.blocks for r in b.runs
                              for a, c in zip(r.points, r.points[1:])) / 1000.0, 2),
        "under_1mm": short_stitches(plan),
        "hairline": hair,
        "line_strand_stitches": sum(len(r.points) for r in line_runs),
        "line_strand_thread_m": round(sum(math.dist(a, c) for r in line_runs
                                          for a, c in zip(r.points, r.points[1:])) / 1000.0, 3),
    }


def _src_box_mm(result, box) -> tuple[float, float, float, float]:
    """A `BOXES` fraction box on the source -> (x0, y0, x1, y1) mm in the
    plan's frame (the art bbox centre, `SourcePixels.to_mm`)."""
    sp = result.source_pixels
    h, w = sp.rgb.shape[:2]
    fx0, fy0, fx1, fy1 = box
    a = sp.to_mm(fx0 * w, fy0 * h)
    b = sp.to_mm(fx1 * w, fy1 * h)
    return a[0], a[1], b[0], b[1]


def render_parts(design: dict, result, arm: str, wt: int) -> None:
    for name, (box, ppm) in BOXES.items():
        img = stitchviz.render_design(design, px_per_mm=ppm,
                                      thread_mm=machine.thread_profile(wt).width_mm)
        _size, to_px = stitchviz._frame(design.get("stitches") or [], ppm, 2.0)
        x0, y0, x1, y1 = _src_box_mm(result, box)
        a = to_px({"x": x0 * UNITS_PER_MM, "y": -y0 * UNITS_PER_MM})
        b = to_px({"x": x1 * UNITS_PER_MM, "y": -y1 * UNITS_PER_MM})
        px0, px1 = sorted((max(a[0], 0), max(b[0], 0)))
        py0, py1 = sorted((max(a[1], 0), max(b[1], 0)))
        cv2.imwrite(str(PARTS / f"{arm}_{name}.png"), img[py0:py1, px0:px1])


def source_part(result, name: str) -> Path:
    """The photograph over the same box, nearest-neighbour at the box's
    render scale, so the strips read source | arms."""
    sp = result.source_pixels
    (box, ppm) = BOXES[name]
    h, w = sp.rgb.shape[:2]
    fx0, fy0, fx1, fy1 = box
    crop = sp.rgb[int(fy0 * h):int(fy1 * h), int(fx0 * w):int(fx1 * w)]
    k = ppm / sp.px_per_mm
    big = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_NEAREST)
    dest = PARTS / f"source_{name}.png"
    cv2.imwrite(str(dest), cv2.cvtColor(big, cv2.COLOR_RGB2BGR))
    return dest


def strand_map(result, k: int = 3) -> None:
    """Every line the detector found on the whole photo, on the photo:
    sewn dark strands red, sewn light strands cyan, refused (no ridge)
    yellow, under the loop floor green. Where the route's thread goes."""
    from digitizer_core.stage6_hairline_lines import (_light, _SRC_MIN_CONTRAST,
                                                      ridge_contrast)
    from digitizer_core.stage6_detail import (fdog_response, fdog_threshold,
                                              field_gray, lines_from_map)
    from digitizer_core import stage6_hairline_lines as L
    sp = result.source_pixels
    cfg = arm_cfg("lines40")
    prof = machine.thread_profile(cfg.thread_wt)
    sampler, gray = field_gray(sp)
    light = _light(sp)
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)        # wash the photo out
    side0 = 0.5 * prof.hairline_max_width_mm
    hh, ww = sp.rgb.shape[:2]
    zones: dict[str, list] = {k: [0, 0.0] for k in list(ZONES) + ["elsewhere"]}
    for pol, g, col in (("dark", gray, (0, 0, 230)), ("light", 1.0 - gray, (230, 160, 0))):
        H = fdog_response(g, sampler.field.tangent)
        lmap = L._fill_slits(fdog_threshold(H, sampler.field.tangent, sampler.field.coherence))
        for pts in lines_from_map(lmap, sp, sampler.scale, min_len_mm=0.0):
            c = ridge_contrast(pts, light, sp, polarity=pol, core_mm=0.5 * prof.hairline_run_width_mm,
                               side0_mm=side0, side1_mm=side0 + L._SIDE_REACH_PX / sp.px_per_mm,
                               step_mm=L._PROFILE_STEP_WIDTHS * prof.width_mm)
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            colour = ((0, 200, 230) if c < _SRC_MIN_CONTRAST
                      else (0, 170, 0) if length < machine.RUN_MIN_LOOP_MM else col)
            q = np.array([sp.to_px(x, y) for x, y in pts]) * k
            cv2.polylines(big, [np.round(q).astype(np.int32)], False, colour, 2, cv2.LINE_AA)
            if c >= _SRC_MIN_CONTRAST and length >= machine.RUN_MIN_LOOP_MM:
                fx, fy = (q.mean(axis=0) / k) / [ww, hh]
                zone = next((z for z, (x0, y0, x1, y1) in ZONES.items()
                             if x0 <= fx < x1 and y0 <= fy < y1), "elsewhere")
                zones[zone][0] += 1
                zones[zone][1] += round(length, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jpeg(OUT / "owl_line_census.jpg", big)
    (OUT / "zones.json").write_text(json.dumps(
        {z: {"strands": n, "mm": round(mm, 1)} for z, (n, mm) in zones.items()}, indent=1)
        + "\n", encoding="utf-8")
    print("zones", json.dumps(zones), flush=True)


def run_arm(arm: str) -> dict:
    cfg = arm_cfg(arm)
    result = run_stages(PHOTO, cfg)
    plan = plan_stitches(result, cfg)
    row = measure(plan)
    p = preflight.prep(PHOTO, cfg, design_class=result.design_class)
    bare = bare_cells(plan, result, p)
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    base_wt = f"off{ARMS[arm][2]}"
    npz = PARTS / f"{base_wt}_bare.npz"
    if arm == base_wt:
        np.savez_compressed(npz, grid=bare[0], origin=np.array(bare[1]), cell=bare[2])
        row["bare_new_mm2"] = 0.0
    elif npz.exists():
        z = np.load(npz)
        base = (z["grid"], tuple(z["origin"]), float(z["cell"]))
        row["bare_new_mm2"] = round(bare_new_mm2(bare, base), 2)
    design = plan_to_design(plan, name=f"owl {arm}")
    (PARTS / f"{arm}_design.json").write_text(json.dumps(design), encoding="utf-8")
    render_parts(design, result, arm, ARMS[arm][2])
    for name in BOXES:
        source_part(result, name)
    (PARTS / f"{arm}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    return row


def run_drawn() -> dict:
    """The drawn fixtures, region tier vs line route: identical plans
    expected (the line route applies on raster lanes only)."""
    out = {}
    for fixture in ("hair_strands.png", "hair_fine.png"):
        row = {}
        for arm, lines in (("on40", False), ("lines40", True)):
            cfg = PipelineConfig(target_width_mm=80.0, hairline=True,
                                 hairline_from_lines=lines)
            result, plan = digitize(SYN / fixture, cfg)
            m = measure(plan)
            m["design_class"] = result.design_class
            row[arm] = m
        row["identical"] = row["on40"]["md5"] == row["lines40"]["md5"]
        out[fixture] = row
        print(fixture, json.dumps(row), flush=True)
    (PARTS / "drawn.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return out


def write_jpeg(path: Path, img) -> None:
    q = 88
    while True:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= MAX_JPEG_BYTES or q <= 60:
            break
        q -= 7
    path.write_bytes(buf.tobytes())


def strip(panels: list[tuple[Path, str]], dest: Path) -> None:
    tiles = []
    for f, label in panels:
        img = cv2.imread(str(f))
        if img is None:
            print("missing", f)
            return
        band = np.full((34, img.shape[1], 3), 255, np.uint8)
        cv2.putText(band, label, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (30, 30, 30), 2, cv2.LINE_AA)
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
    arms = [a for a in LABELS if (PARTS / f"{a}.json").exists()]
    for name, (_box, ppm) in BOXES.items():
        strip([(PARTS / f"source_{name}.png", f"photo ({ppm:g} px/mm)")]
              + [(PARTS / f"{a}_{name}.png", LABELS[a]) for a in arms],
              OUT / f"owl_{name}_{int(ppm)}pxmm.jpg")
    rows = {a: json.loads((PARTS / f"{a}.json").read_text(encoding="utf-8")) for a in arms}
    drawn = (json.loads((PARTS / "drawn.json").read_text(encoding="utf-8"))
             if (PARTS / "drawn.json").exists() else {})
    (OUT / "table.json").write_text(json.dumps({"owl_classical_40wt": rows, "drawn": drawn},
                                               indent=1) + "\n", encoding="utf-8")
    lines = ["| owl_kent, `classical`, 40 wt, 127 mm | " + " | ".join(LABELS[a] for a in arms) + " |",
             "|---|" + "---|" * len(arms)]

    def hair(r, k):
        h = r.get("hairline")
        return "-" if not h else h.get(k)
    spec = [("strands sewn", lambda r: hair(r, "strands")),
            ("strands dropped (< 2.2 mm)", lambda r: hair(r, "dropped")),
            ("stitches", lambda r: f"{r['stitches']:,}"),
            ("trims", lambda r: r["trims"]),
            ("colour changes", lambda r: r["color_changes"]),
            ("thread laid (m)", lambda r: r["thread_m"]),
            ("of which line strands (m)", lambda r: r["line_strand_thread_m"]),
            ("stitches < 1.0 mm (excl. lock legs)", lambda r: r["under_1mm"]),
            ("bare fabric, new vs OFF (mm2)", lambda r: r.get("bare_new_mm2", "-"))]
    for label, fn in spec:
        lines.append(f"| {label} | " + " | ".join(str(fn(rows[a])) for a in arms) + " |")
    (OUT / "table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--arm", choices=list(ARMS))
    ap.add_argument("--drawn", action="store_true")
    ap.add_argument("--compose", action="store_true")
    ap.add_argument("--render", action="store_true",
                    help="re-render the parts from each arm's saved design (no re-plan)")
    args = ap.parse_args(argv)
    PARTS.mkdir(parents=True, exist_ok=True)
    if args.arm:
        print(args.arm, json.dumps(run_arm(args.arm)), flush=True)
    if args.render:
        result = run_stages(PHOTO, arm_cfg("off40"))
        strand_map(result)
        for name in BOXES:
            source_part(result, name)
        for arm in ARMS:
            f = PARTS / f"{arm}_design.json"
            if f.exists():
                render_parts(json.loads(f.read_text(encoding="utf-8")), result, arm,
                             ARMS[arm][2])
    if args.drawn:
        run_drawn()
    if args.compose:
        compose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
