#!/usr/bin/env python
"""Defect 20: thread layers per 1 mm cell, tonal split OFF-cap vs ON-cap.

For each fixture prints the max and p50/p90/p95/p99 FILL LAYERS over sewn
cells (`digitizer_core.layer_density.layer_stats`), the area past the warn
(2.5) and ceiling (3.5) layers, the region count and how many tonal parents
the split cut, for three arms:

    split   the engine as shipped (`tonal_split_layer_cap` OFF)
    cap     `tonal_split_layer_cap` ON
    whole   the tonal split off (`split_tonal_regions=False`), for reference

    python -m tools.layer_density                       # the default set
    python -m tools.layer_density photo/owl_kent.jpg --force-split
    python -m tools.layer_density --jobs 4 --json out.json

A density reading, not a quality one: nothing here scores tonal gradation.
The default set is the committed photo-class fixtures (split by default)
plus the two real tonal images `tools/tonal_stack_hist.py` uses, which
classify `gradient` and so need `--force-split` (applied to them
automatically in the default set).
"""
import argparse
import json
import pathlib
import time
from concurrent.futures import ProcessPoolExecutor

TD = pathlib.Path(__file__).resolve().parent.parent / "testdata"
DEFAULT = ["photo/photo_scene_stub.png", "photo/photo_subject_stub.png",
           "photo/photo_dof_meadow.png", "photo/photo_grass_macro.png",
           "photo/photo_chrome_specular.png", "photo/photo_owl_pale.png",
           "photo/photo_sunset_backlit.png", "photo/tight_crop_pale_subject.png"]
FORCED = ["photo/owl_kent.jpg", "photo/drone_render.png"]
ARMS = ("split", "cap", "whole")


def measure(fx: str, arm: str, force: bool, width_mm: float) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.layer_density import layer_stats
    from digitizer_core.pipeline import digitize
    kw = dict(target_width_mm=width_mm, garment_id="left_chest")
    if force:
        kw.update(split_tonal_regions=True, is_photographic=True)
    if arm == "cap":
        kw["tonal_split_layer_cap"] = True
    if arm == "whole":
        kw["split_tonal_regions"] = False
    t = time.time()
    res, plan = digitize(TD / fx, PipelineConfig(**kw))
    split = sum(int(w.get("count", 0)) for w in res.warnings
                if w.get("code") == "TONAL_REGIONS_SPLIT")
    stitches = sum(len(r.points) for _b, r in plan.iter_runs())
    return {"fixture": fx, "arm": arm, "forced": force, "class": res.design_class,
            "regions": len(res.regions), "tonal_parents_split": split,
            "stitches": stitches, "seconds": round(time.time() - t, 1),
            **layer_stats(plan)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/")
    ap.add_argument("--force-split", action="store_true",
                    help="force the tonal split on (gradient-class tonal art)")
    ap.add_argument("--width-mm", type=float, default=80.0)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--json", type=pathlib.Path, help="also write the rows here")
    a = ap.parse_args(argv)
    if a.fixtures:
        todo = [(fx, a.force_split) for fx in a.fixtures]
    else:
        todo = [(fx, False) for fx in DEFAULT] + [(fx, True) for fx in FORCED]
    jobs = [(fx, arm, force, a.width_mm) for fx, force in todo for arm in ARMS]
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        rows = list(ex.map(measure, *zip(*jobs)))
    head = (f"{'fixture':<28} {'arm':<6} {'regs':>4} {'cut':>3} {'stitches':>8} "
            f"{'max':>5} {'p50':>5} {'p90':>5} {'p95':>5} {'p99':>5} "
            f"{'>2.5mm2':>7} {'>3.5mm2':>7}")
    print(head)
    for r in rows:
        name = pathlib.Path(r["fixture"]).name + ("*" if r["forced"] else "")
        print(f"{name:<28} {r['arm']:<6} {r['regions']:>4} {r['tonal_parents_split']:>3} "
              f"{r['stitches']:>8} {r['max']:>5.2f} {r['p50']:>5.2f} {r['p90']:>5.2f} "
              f"{r['p95']:>5.2f} {r['p99']:>5.2f} {r['over_warn_mm2']:>7.0f} "
              f"{r['over_ceiling_mm2']:>7.0f}")
    print("layers = fill layers per 1 mm cell; * = split forced; ceiling 3.5")
    if a.json:
        a.json.write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
