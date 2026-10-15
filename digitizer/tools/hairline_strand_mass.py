"""The strand test's hair-mass exemption, measured (2026-10-15).

    python -m tools.hairline_strand_mass synth               # mane + #882 synthetics
    python -m tools.hairline_strand_mass census              # owl_kent extraction census
    python -m tools.hairline_strand_mass owl --arm mass      # one owl plan per call
    python -m tools.hairline_strand_mass drawn               # hair_strands / hair_fine
    python -m tools.hairline_strand_mass logos [--only a,b]  # the nine corpus logos
    python -m tools.hairline_strand_mass render              # before/after strips
    python -m tools.hairline_strand_mass table               # table.json

#897's strand test (`cfg.hairline_lines_strand_test`) refuses any stack of
parallel lines, so it refuses #882's own synthetic (8 strands ~3 mm apart)
and would refuse a mane or a beard. This measures
`cfg.hairline_lines_strand_mass` (`stage6_hairline_lines.is_hair_mass`),
which keeps a stack whose members are strands themselves. Three arms:
`lines` (the line route, strand test OFF), `test` (strand test ON), `mass`
(strand test ON + the exemption).

- `synth`: a drawn mane (strands about 1 mm apart, centre to centre, of
  varied length; `mane_image`) and #882's 8-strand synthetic, each through
  the photo lane (`photo_scene`, `photo_prep=False`), one plan per arm. A
  drawn strand is KEPT when sewn dark line-route thread lies within
  `KEEP_NEAR_MM` of at least `KEEP_SHARE` of its length.
- `census`: owl_kent on #897's route (`classical`: photo lane,
  `photo_prep=False`, 40 wt, 127 mm), the extraction only, strands counted
  by #882's zones (each strand's centroid), plus a map of what each arm
  keeps.
- `owl --arm`: the plan for one arm: stitches, trims, thread, bare fabric
  new against the `test` arm (`tools.hairline_renders.bare_cells`).
- `drawn` / `logos`: the drawn hair fixtures and the nine logos, with and
  without the exemption, on the strand-test path and on the full gradient
  supplement (#942 + #971's logo refusal).

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitchviz  # noqa: E402
from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import hair_reach as hr  # noqa: E402
from tools import hairline_lines_gradient as G  # noqa: E402
from tools.hairline_lines_trial import PHOTO, ROUTE, ZONES, measure, write_jpeg  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402
from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

DEBUG = ROOT / "debug_out" / "hairline_strand_mass"
OUT = ROOT.parent / "docs" / "renders" / "strand-mass-exemption"
FLAG = "hairline_lines_strand_mass"
LINES = dict(hairline=True, hairline_from_lines=True)
ARMS = {"lines": dict(LINES),
        "test": dict(LINES, hairline_lines_strand_test=True),
        "mass": dict(LINES, hairline_lines_strand_test=True, **{FLAG: True})}
LABELS = {"lines": "strand test OFF", "test": "strand test ON",
          "mass": "strand test ON + mass exemption"}
OWL_WIDTH = 127.0
# A drawn strand is kept when sewn thread lies within KEEP_NEAR_MM of at
# least KEEP_SHARE of its length (#882's done-test reads 0.4 mm and 70%).
KEEP_NEAR_MM = 0.4
KEEP_SHARE = 0.7
SYN_PX_PER_MM = 8.0
# The head-outline fringe, as a fraction of the source photo (the left
# wisps on #897's census map), and its render scale.
FRINGE_BOX = (0.06, 0.10, 0.20, 0.32)
FRINGE_PX_PER_MM = 16.0


# ------------------------------------------------------------- synthetics

def mane_image(n: int = 28, spacing_mm: float = 1.0, jitter_mm: float = 0.15,
               size: int = 320, seed: int = 3):
    """-> (RGB image, drawn strands as px polylines). A drawn mane: `n`
    thin dark strands (2 px = 0.25 mm at 8 px/mm, anti-aliased) on #882's
    mid-tone ground with its noise, one flow, `spacing_mm` +- `jitter_mm`
    apart centre to centre (a gap of about two 40 wt thread widths), each
    starting and ending at its own height (varied length)."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size, 3), (150, 120, 95), np.float64)
    img += rng.normal(0.0, 4.0, (size, size, 1))
    img = np.clip(img, 0, 255).astype(np.uint8)
    drawn = []
    x = 40.0
    for _ in range(n):
        x += (spacing_mm + rng.uniform(-jitter_mm, jitter_mm)) * SYN_PX_PER_MM
        y0 = 30 + rng.uniform(0, 80)
        ln = rng.uniform(80, 260 - y0)
        t = np.linspace(0.0, 1.0, 60)
        pts = np.column_stack([x + 14 * np.sin(1.8 * t + 0.4) + 10 * t, y0 + ln * t])
        cv2.polylines(img, [np.round(pts).astype(np.int32)], False, (40, 30, 25), 2,
                      cv2.LINE_AA)
        drawn.append(pts)
    return img, drawn


def s882_image():
    """#882's synthetic (`tests/test_hairline_lines._fixture`): 8 strands
    25 px (3.1 mm) apart at 8 px/mm -> (RGB image, drawn px polylines)."""
    from tests.test_hairline_lines import SIZE_PX, _drawn_lines
    rng = np.random.default_rng(7)
    img = np.full((SIZE_PX, SIZE_PX, 3), (150, 120, 95), np.float64)
    img += rng.normal(0.0, 4.0, (SIZE_PX, SIZE_PX, 1))
    img = np.clip(img, 0, 255).astype(np.uint8)
    drawn = _drawn_lines()
    for pts in drawn:
        cv2.polylines(img, [np.round(pts).astype(np.int32)], False, (40, 30, 25), 2,
                      cv2.LINE_AA)
    return img, drawn


# name -> (image, design width mm). The mane at 30 mm reads at 7.97 px/mm,
# so its strands sit 1.0 mm apart in the design (a gap of two 40 wt
# widths); `mane_40mm` is the same picture a third larger (1.34 mm), past
# the dense arm's 3 widths. #882's synthetic at #882's own 30 mm (6.2
# px/mm: 4 mm apart).
SYNTHETICS = {"mane": (mane_image, 30.0), "mane_40mm": (mane_image, 40.0),
              "s882": (s882_image, 30.0)}


def syn_cfg(arm: str, width_mm: float) -> PipelineConfig:
    return PipelineConfig(target_width_mm=width_mm, forced_class="photo_scene",
                          photo_prep=False, **ARMS[arm])


def dark_runs(plan) -> list:
    """The line route's sewn DARK strands: the dark block is sewn first
    (`strand_blocks`), so the first `sewn_by_polarity["dark"]` runs."""
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    if not w:
        return []
    n = w[0]["sewn_by_polarity"].get("dark", 0)
    runs = [r for _, r in plan.iter_runs() if r.shape_id == L.SHAPE_ID and r.kind == "run"]
    return runs[:n]


def drawn_kept(drawn_mm, runs) -> int:
    """How many drawn strands (mm polylines) the sewn `runs` keep: thread
    within `KEEP_NEAR_MM` of at least `KEEP_SHARE` of the strand's length."""
    if not runs:
        return 0
    sewn = MultiLineString([r.points for r in runs if len(r.points) >= 2])
    kept = 0
    for pts in drawn_mm:
        line = LineString(pts)
        n = max(2, int(line.length / 0.25))
        near = sum(sewn.distance(line.interpolate(i / (n - 1), normalized=True)) <= KEEP_NEAR_MM
                   for i in range(n))
        kept += near >= KEEP_SHARE * n
    return kept


def cmd_synth() -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    for name, (make, width) in SYNTHETICS.items():
        img, drawn = make()
        src = DEBUG / f"{name}.png"
        cv2.imwrite(str(src), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        result = run_stages(src, syn_cfg("lines", width))
        sp = result.source_pixels
        drawn_mm = [[sp.to_mm(x, y) for x, y in pts] for pts in drawn]
        row = {"case": name, "drawn": len(drawn), "design_class": result.design_class,
               "width_mm": width, "px_per_mm": round(sp.px_per_mm, 3)}
        for arm in ARMS:
            plan = plan_stitches(result, syn_cfg(arm, width))
            m = measure(plan)
            w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"][0]
            m["census"] = {k: w.get(k) for k in ("found", "refused_no_ridge", "refused_bar",
                                                 "exempt_mass", "sewn_by_polarity")
                           if k in w}
            m["drawn_kept"] = drawn_kept(drawn_mm, dark_runs(plan))
            row[arm] = m
            (DEBUG / f"{name}_{arm}_design.json").write_text(
                json.dumps(plan_to_design(plan, name=f"{name} {arm}")), encoding="utf-8")
        _write(row, f"synth_{name}")
    return 0


# ------------------------------------------------------------- owl_kent

def owl_cfg(arm: str) -> PipelineConfig:
    return PipelineConfig(target_width_mm=OWL_WIDTH, thread_wt=40, **ROUTE, **ARMS[arm])


def zone_counts(sp, strands) -> dict:
    """#882's census reading: sewable strands per zone, by centroid."""
    h, w = sp.rgb.shape[:2]
    out = collections.Counter({z: 0 for z in list(ZONES) + ["elsewhere"]})
    for s in strands:
        if s["length_mm"] < machine.RUN_MIN_LOOP_MM:
            continue
        fx, fy = np.array([sp.to_px(x, y) for x, y in s["pts"]]).mean(axis=0) / [w, h]
        out[next((z for z, (x0, y0, x1, y1) in ZONES.items()
                  if x0 <= fx < x1 and y0 <= fy < y1), "elsewhere")] += 1
    return dict(out)


def _key(s) -> tuple:
    return (s["polarity"], tuple(map(tuple, s["pts"])))


def cmd_census() -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    sp = run_stages(PHOTO, owl_cfg("lines")).source_pixels
    row, kept = {"image": "owl_kent", "route": "classical", "width_mm": OWL_WIDTH}, {}
    for arm in ARMS:
        strands, census = L.extract_strands(sp, owl_cfg(arm))
        kept[arm] = {_key(s) for s in strands if s["length_mm"] >= machine.RUN_MIN_LOOP_MM}
        row[arm] = {"zones": zone_counts(sp, strands), "sewable": len(kept[arm]),
                    **{k: census[k] for k in ("refused_bar", "exempt_mass") if k in census}}
    _write(row, "owl_census")
    census_map(sp, kept)
    return 0


def census_map(sp, kept, k: int = 3) -> None:
    """Every sewable ridge line on the photo: kept by all three arms red
    (dark) / blue (light), refused by the strand test and kept by the
    exemption orange, refused by both magenta."""
    big = cv2.resize(cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR), None, fx=k, fy=k,
                     interpolation=cv2.INTER_NEAREST)
    big = (0.55 * big + 0.45 * 255).astype(np.uint8)
    for key in sorted(kept["lines"]):
        pol, pts = key
        if key in kept["test"]:
            colour = (0, 0, 230) if pol == "dark" else (230, 160, 0)
        elif key in kept["mass"]:
            colour = (0, 140, 255)
        else:
            colour = (200, 0, 200)
        q = np.array([sp.to_px(x, y) for x, y in pts]) * k
        cv2.polylines(big, [np.round(q).astype(np.int32)], False, colour, 2, cv2.LINE_AA)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jpeg(OUT / "owl_census_map.jpg", big)


def cmd_owl(arm: str) -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    from digitizer_core import preflight
    t0 = time.time()
    cfg = owl_cfg(arm)
    result = run_stages(PHOTO, cfg)
    plan = plan_stitches(result, cfg)
    row = {"image": "owl_kent", "arm": arm, **measure(plan)}
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    if w:
        row["hairline"].update({k: w[0][k] for k in ("refused_bar", "exempt_mass") if k in w[0]})
    bare = bare_cells(plan, result, preflight.prep(PHOTO, cfg,
                                                   design_class=result.design_class))
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    npz = DEBUG / "owl_test_bare.npz"
    if arm == "test":
        np.savez_compressed(npz, grid=bare[0], origin=np.array(bare[1]), cell=bare[2])
    if npz.exists():
        z = np.load(npz)
        row["bare_new_vs_test_mm2"] = round(bare_new_mm2(
            bare, (z["grid"], tuple(z["origin"]), float(z["cell"]))), 2)
    (DEBUG / f"owl_{arm}_design.json").write_text(
        json.dumps(plan_to_design(plan, name=f"owl {arm}")), encoding="utf-8")
    sp = result.source_pixels
    h, w_ = sp.rgb.shape[:2]
    fx0, fy0, fx1, fy1 = FRINGE_BOX
    (DEBUG / "owl_fringe_box_mm.json").write_text(json.dumps(
        [*sp.to_mm(fx0 * w_, fy0 * h), *sp.to_mm(fx1 * w_, fy1 * h)]), encoding="utf-8")
    crop = sp.rgb[int(fy0 * h):int(fy1 * h), int(fx0 * w_):int(fx1 * w_)]
    kk = FRINGE_PX_PER_MM / sp.px_per_mm
    cv2.imwrite(str(DEBUG / "owl_fringe_source.png"),
                cv2.cvtColor(cv2.resize(crop, None, fx=kk, fy=kk,
                                        interpolation=cv2.INTER_NEAREST), cv2.COLOR_RGB2BGR))
    row["seconds"] = round(time.time() - t0)
    _write(row, f"owl_{arm}")
    return 0


# ------------------------------------------------------ drawn hair, logos

# Paths the exemption can reach: the strand test's own path (the line route
# runs on the photo lanes only) and the full gradient supplement, #942 +
# #971's logo refusal. Each without and with the flag.
PATHS = {"test": dict(G.BASE), "test_mass": dict(G.BASE, **{FLAG: True}),
         "supp": dict(G.BASE, hairline_lines_gradient=True,
                      hairline_lines_logo_refusal=True),
         "supp_mass": dict(G.BASE, hairline_lines_gradient=True,
                           hairline_lines_logo_refusal=True, **{FLAG: True})}


def _studio_cfg(path: str, width: float, **kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=width, work_px_per_mm=8.0, thread_wt=40,
                          **hr.STUDIO, **PATHS[path], **kw)


def _paths_row(image, width, kw) -> dict:
    result = run_stages(image, _studio_cfg("supp", width, **kw))
    row = {"design_class": result.design_class}
    for p in PATHS:
        plan = plan_stitches(result, _studio_cfg(p, width, **kw))
        row[p] = {"md5": G.plan_md5(plan), "stitches": plan.stats.stitch_count,
                  "trims": plan.stats.trims}
    row["identical"] = (row["test"]["md5"] == row["test_mass"]["md5"]
                        and row["supp"]["md5"] == row["supp_mass"]["md5"])
    return row


def cmd_drawn() -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    for image in hr.DRAWN:
        _write({"image": image, "width_mm": hr.DRAWN_WIDTH,
                **_paths_row(hr.IMAGES[image], hr.DRAWN_WIDTH, {})}, f"drawn_{image}")
    return 0


def cmd_logos(only) -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    for name, path, width, garment in corpus_cases():
        if only and name not in only:
            continue
        t0 = time.time()
        row = {"logo": name, "width_mm": width,
               **_paths_row(path, width, dict(garment_id=garment, max_colors=STUDIO_MAX_COLORS))}
        row["seconds"] = round(time.time() - t0)
        _write(row, f"logo_{name}")
    return 0


# ------------------------------------------------------- renders, table

def _render(design_file: Path, px_per_mm: float, box_mm=None):
    design = json.loads(design_file.read_text(encoding="utf-8"))
    img = stitchviz.render_design(design, px_per_mm=px_per_mm,
                                  thread_mm=machine.thread_profile(40).width_mm)
    if box_mm is None:
        return img
    from digitizer_core.adapter import UNITS_PER_MM
    _size, to_px = stitchviz._frame(design.get("stitches") or [], px_per_mm, 2.0)
    x0, y0, x1, y1 = box_mm
    a = to_px({"x": x0 * UNITS_PER_MM, "y": -y0 * UNITS_PER_MM})
    b = to_px({"x": x1 * UNITS_PER_MM, "y": -y1 * UNITS_PER_MM})
    px0, px1 = sorted((max(a[0], 0), max(b[0], 0)))
    py0, py1 = sorted((max(a[1], 0), max(b[1], 0)))
    return img[py0:py1, px0:px1]


def _strip(tiles, dest: Path) -> None:
    out = []
    h = min(t.shape[0] for _l, t in tiles)
    w = min(t.shape[1] for _l, t in tiles)
    for label, t in tiles:
        band = np.full((34, w, 3), 255, np.uint8)
        cv2.putText(band, label[:48], (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2,
                    cv2.LINE_AA)
        out += [np.vstack([band, t[:h, :w]]), np.full((h + 34, 8, 3), 255, np.uint8)]
    write_jpeg(dest, np.hstack(out[:-1]))


def cmd_render() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("mane", "s882"):
        src = cv2.imread(str(DEBUG / f"{name}.png"))
        if src is None:
            print("run `synth` first")
            return 1
        ppm = 16.0
        tiles = [(f"drawn {name} ({ppm:g} px/mm)",
                  cv2.resize(src, None, fx=ppm / SYN_PX_PER_MM, fy=ppm / SYN_PX_PER_MM,
                             interpolation=cv2.INTER_NEAREST))]
        tiles += [(LABELS[a], _render(DEBUG / f"{name}_{a}_design.json", ppm))
                  for a in ("test", "mass")]
        _strip(tiles, OUT / f"{name}_before_after_16pxmm.jpg")
    box = json.loads((DEBUG / "owl_fringe_box_mm.json").read_text(encoding="utf-8"))
    tiles = [(f"photo ({FRINGE_PX_PER_MM:g} px/mm)", cv2.imread(str(DEBUG / "owl_fringe_source.png")))]
    tiles += [(LABELS[a], _render(DEBUG / f"owl_{a}_design.json", FRINGE_PX_PER_MM, box))
              for a in ("test", "mass")]
    _strip(tiles, OUT / "owl_fringe_before_after_16pxmm.jpg")
    return 0


def cmd_table() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {f.stem: json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(DEBUG.glob("*.json")) if not f.stem.endswith("_design")
            and f.stem != "owl_fringe_box_mm"}
    (OUT / "table.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=1))
    return 0


def _write(row: dict, name: str) -> dict:
    (DEBUG / f"{name}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(row), flush=True)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("synth")
    sub.add_parser("census")
    o = sub.add_parser("owl")
    o.add_argument("--arm", choices=list(ARMS), required=True)
    sub.add_parser("drawn")
    g = sub.add_parser("logos")
    g.add_argument("--only", default="")
    sub.add_parser("render")
    sub.add_parser("table")
    args = ap.parse_args(argv)
    if args.cmd == "synth":
        return cmd_synth()
    if args.cmd == "census":
        return cmd_census()
    if args.cmd == "owl":
        return cmd_owl(args.arm)
    if args.cmd == "drawn":
        return cmd_drawn()
    if args.cmd == "logos":
        return cmd_logos({s for s in args.only.split(",") if s})
    if args.cmd == "render":
        return cmd_render()
    return cmd_table()


if __name__ == "__main__":
    raise SystemExit(main())
