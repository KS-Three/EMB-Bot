"""Edge-fault reader: WHERE does a sewn edge wobble, in the pins' own frame.

    python -m tools.edge_fault_reader run --pro-run DIR --out DIR [--tree DIGITIZER] [--only SLUG]
    python -m tools.fault_reader_harness score --marks MARKS.json --flags DIR

The first reader scored by `tools.fault_reader_harness` against Kent's
2026-11-10 pins, for the largest theme in his notes: edges that should be
smooth (17+ pins on 7 logos, filed under seven different kinds).

It invents no measurement. `digitizer_core.edge_wobble.analyse_plan` (the
instrument behind preflight's `edge_wobble_*` metrics, defect 46) already
gives every visible edge penetration a high-passed signed deviation from its
own shape's outline, and already lists the ones over `OVER_MM` as `flagged`
with their plan-mm location. Preflight then throws the locations away and
keeps three numbers per tier. This reader keeps the locations:

  1. re-run the job exactly as `defect_marks capture-pro` did (the worker's
     own call sequence, the stored `config_sent`, the job's own artwork), and
     REFUSE the item unless the re-run's stitches equal the stored design's
     stitch for stitch, so the flags belong to the render Kent marked;
  2. `analyse_plan(...)["flagged"]`: every edge penetration over `OVER_MM`;
  3. move them into the render's frame (`plan_to_render_mm`), the frame
     `defect_marks.mark_mm` puts his pins in;
  4. merge them into spots (`cluster`): strongest first, a point within
     `MERGE_MM` of a kept spot joins it. Strength = the spot's largest
     |deviation| in mm.

`OVER_MM` and `MERGE_MM` are the instrument's own pre-existing numbers (its
"visible" line and its `worst` de-duplication distance), fixed in the
pre-registration and not tuned on the pins.

`edge_smoothness.py` (render vs the artwork's ink mask) was not used: it needs
the artwork registered to the render, sees outline and stitch error summed,
and its own docstring shows a raster edge reads as a staircase. The plan-side
instrument has none of those problems and is what preflight already ships.

The worker runs with cwd = `--tree` (default: this checkout's `digitizer/`),
so point `--tree` at the checkout the kit was built on. Its output (`<item>.
flags.json`, `<item>.mask.npz`) holds no picture of the pro's file; the mask
is our own render's thread pixels, used only to draw chance points, and stays
out of the repo with the rest of `eye_pairs_out/`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]            # digitizer/
UNITS_PER_MM = 10.0                                   # adapter / stitchviz design units
OVER_MM = 0.15                                        # == edge_wobble.OVER_MM (asserted by the worker)
MERGE_MM = 2.0                                        # edge_wobble's own `worst` de-dup distance
PXMM = 12.0
PAD_MM = 2.0


# ------------------------------------------------------------ pure helpers ----

def design_origin(stitches: list[dict]) -> tuple[float, float]:
    """(x0, y1) of `stitchviz._bounds`: min x and MAX y over stitches and
    jumps, design units. The render's top-left (pad undone) sits there."""
    xs = [s["x"] for s in stitches if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in stitches if s.get("type") in ("stitch", "jump")]
    if not xs:
        raise ValueError("design has no stitch or jump")
    return float(min(xs)), float(max(ys))


def plan_to_render_mm(x_mm: float, y_mm: float, origin: tuple[float, float]) -> tuple[float, float]:
    """A plan-frame point (mm) -> the pins' frame. The adapter writes
    (x*10, -y*10); `stitchviz._frame` draws ((x - x0)/10, (y1 - y)/10) mm from
    the pad's inner corner, which is what `defect_marks.mark_mm` returns."""
    x0, y1 = origin
    return (x_mm - x0 / UNITS_PER_MM, y_mm + y1 / UNITS_PER_MM)


def cluster(points: list[dict], merge_mm: float = MERGE_MM) -> list[dict]:
    """Flagged points (`x_mm`, `y_mm`, `dev_mm`, `tier`, `zone`) -> spots.
    Strongest first; a point within `merge_mm` of a kept spot's centre joins
    it (count, tiers). Deterministic for a given input order."""
    order = sorted(range(len(points)), key=lambda i: (-abs(points[i]["dev_mm"]), i))
    spots: list[dict] = []
    for i in order:
        p = points[i]
        for s in spots:
            if (s["x_mm"] - p["x_mm"]) ** 2 + (s["y_mm"] - p["y_mm"]) ** 2 <= merge_mm ** 2:
                s["n"] += 1
                s["tiers"][p["tier"]] = s["tiers"].get(p["tier"], 0) + 1
                break
        else:
            spots.append({"x_mm": round(p["x_mm"], 2), "y_mm": round(p["y_mm"], 2),
                          "strength": round(abs(p["dev_mm"]), 3), "dev_mm": p["dev_mm"],
                          "tier": p["tier"], "zone": p.get("zone"), "n": 1, "tiers": {p["tier"]: 1}})
    return spots


def to_flags(flagged: list[dict], stitches: list[dict], merge_mm: float = MERGE_MM) -> list[dict]:
    """`analyse_plan(...)["flagged"]` + the stored design -> spots in the pins' frame."""
    origin = design_origin(stitches)
    pts = []
    for f in flagged:
        x, y = plan_to_render_mm(f["at_mm"][0], f["at_mm"][1], origin)
        pts.append({"x_mm": x, "y_mm": y, "dev_mm": f["dev_mm"], "tier": f["tier"], "zone": f.get("zone")})
    return cluster(pts, merge_mm)


# ------------------------------------------------------------------ worker ----

WORKER = r'''
import hashlib, json, sys
spec = json.loads(sys.argv[1])
sys.path.insert(0, spec["tree"])
import numpy as np
from digitizer_core import PipelineConfig
from digitizer_core import edge_wobble
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.adapter import plan_to_design
from digitizer_core.stitchviz import render_design
from digitizer_service.app import _decode, _parse_config
from tools import pro_baseline as pb
assert edge_wobble.OVER_MM == spec["over_mm"], ("OVER_MM moved", edge_wobble.OVER_MM)
stored = json.load(open(spec["job"], encoding="utf-8"))
art = pb.resolve(pb.JOBS[spec["slug"]][2])
data = open(art, "rb").read()
cfg = PipelineConfig(**_parse_config(json.dumps(stored["_meta"]["config_sent"])))
pixels = _decode(data)
gen = build_generation(pixels, cfg, exif_source=data)
result = finish_generation(gen.fork(), cfg)
plan = plan_stitches(result, cfg)
design = plan_to_design(plan, name="Digitized design")
def h(st): return hashlib.sha256(json.dumps([[s["x"], s["y"], s["type"]] for s in st]).encode()).hexdigest()
same = h(design["stitches"]) == h(stored["design"]["stitches"])
row = edge_wobble.analyse_plan({r.shape_id: r.polygon for r in result.regions if r.polygon is not None},
                               plan, unsewn=False)
cfgs = stored["_meta"]["config_sent"]
fabric = tuple(reversed(cfgs.get("garment_rgb") or [235, 232, 223]))
img = render_design(stored["design"], px_per_mm=spec["pxmm"], fabric_bgr=fabric, pad_mm=spec["pad"])
mask = (np.abs(img.astype(int) - np.array(fabric)[None, None, :]).sum(-1) > 0)
np.savez_compressed(spec["mask"], mask=mask)
json.dump({"same_stitches": same, "stored_sha": h(stored["design"]["stitches"]),
           "rerun_sha": h(design["stitches"]), "flagged": row["flagged"],
           "by_tier": row["by_tier"], "img_w": int(img.shape[1]), "img_h": int(img.shape[0])},
          open(spec["out"], "w", encoding="utf-8"))
'''


def _tree_sha(tree: Path) -> str | None:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(tree), capture_output=True, text=True)
    return r.stdout.strip() or None


def run(pro_run: Path, out: Path, tree: Path, slugs: list[str], timeout: float = 900.0) -> int:
    from tools.defect_marks import PRO_SLUGS
    out.mkdir(parents=True, exist_ok=True)
    sha = _tree_sha(tree)
    env = {**os.environ, "OPENCV_IPP": "avx2", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1", "OPENCV_FOR_THREADS_NUM": "1", "PYTHONIOENCODING": "utf-8"}
    bad = 0
    for slug in slugs or PRO_SLUGS:
        iid = f"L_{slug}"
        job = pro_run / f"{slug}.json"
        stored = json.loads(job.read_text(encoding="utf-8"))
        raw = out / f"{iid}.raw.json"
        spec = {"tree": str(tree), "slug": slug, "job": str(job), "out": str(raw),
                "mask": str(out / f"{iid}.mask.npz"), "pxmm": PXMM, "pad": PAD_MM, "over_mm": OVER_MM}
        proc = subprocess.run([sys.executable, "-c", WORKER, json.dumps(spec)], cwd=str(tree), env=env,
                              capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            print(slug, "ERROR", proc.stderr.strip().splitlines()[-3:], flush=True)
            bad += 1
            continue
        r = json.loads(raw.read_text(encoding="utf-8"))
        if not r["same_stitches"]:
            print(slug, "REFUSED: re-run stitches differ from the stored design", flush=True)
            bad += 1
            continue
        flags = to_flags(r["flagged"], stored["design"]["stitches"])
        rec = {"item": iid, "reader": "edge_fault_reader", "tree_sha": sha,
               "stored_tree_sha": (stored.get("_meta") or {}).get("tree_sha"),
               "stitches_sha256": r["stored_sha"], "over_mm": OVER_MM, "merge_mm": MERGE_MM,
               "px_per_mm": PXMM, "pad_mm": PAD_MM, "img_w": r["img_w"], "img_h": r["img_h"],
               "points_over": len(r["flagged"]), "by_tier": r["by_tier"], "flags": flags}
        (out / f"{iid}.flags.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
        raw.unlink()
        print(slug, "points over", len(r["flagged"]), "spots", len(flags), flush=True)
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--pro-run", type=Path, required=True, help="defect_marks capture-pro output")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--tree", type=Path, default=ROOT, help="digitizer/ of the checkout the kit was built on")
    r.add_argument("--only", action="append", default=[])
    a = ap.parse_args(argv)
    return run(a.pro_run, a.out, a.tree.resolve(), a.only)


if __name__ == "__main__":
    sys.exit(main())
