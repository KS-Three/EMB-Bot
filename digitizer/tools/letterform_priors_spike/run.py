"""Rebuild the spike's inputs: run the engine (current main) on the seven
real-art logos the outline-cut spike used and pickle what the fit and the
downstream checks need. Same `CASES` table as that spike's `run.py`.

Outputs go to `scratch_letterform_priors/` at the repo root (gitignored by
the `scratch_*` pattern -- the pickles hold client artwork and this repo is
public), or wherever `LETTERFORM_SCRATCH` points.

    <logo>.pkl         regions + runs as plain dicts (the sibling's layout)
    <logo>.result.pkl  the whole PipelineResult + the config kwargs, so
                       `plan_stitches` can re-run stages 5-7 on refit
                       polygons without paying for stages 0-4 again

Usage:  python run.py [logo ...]     (default: all seven, becker first)
"""
import os
import pickle
import sys
import time
import traceback
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]        # digitizer/
sys.path.insert(0, str(ROOT))
SCRATCH = Path(os.environ.get("LETTERFORM_SCRATCH", ROOT.parent / "scratch_letterform_priors"))

from digitizer_core import PipelineConfig, digitize            # noqa: E402
from digitizer_core.adapter import plan_to_design              # noqa: E402

CASES = {
    "becker": ("becker_marine_logo.png", 95.7, "left_chest"),
    "fremont": ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
    "enthusiast": ("photo/enthusiast_logo.png", 100.0, "left_chest"),
    "tires": ("logo_script_tires.png", 100.0, "left_chest"),
    "bridge": ("photo/logo_bridge_bar.jpg", 80.0, "left_chest"),
    "gaulke": ("art/logo_golke_roofing.png", 95.2, "left_chest"),
    "drone": ("photo/drone_render.png", 80.0, "left_chest"),
}


def main(names: list[str]) -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for n in names:
        rel, w, g = CASES[n]
        t = time.time()
        try:
            kw = dict(target_width_mm=w, garment_id=g, max_colors=6)
            cfg = PipelineConfig(**kw)
            src = ROOT / "testdata" / rel
            with Image.open(src) as im:
                img_w, img_h = im.size
            result, plan = digitize(src, cfg)
            design = plan_to_design(plan)
            regs = [dict(shape_id=r.shape_id, polygon=r.polygon, meta=dict(r.meta),
                         thread_index=getattr(r, "thread_index", None)) for r in result.regions]
            runs = [dict(block=i, kind=r.kind, jump=r.jump, trim=r.trim, shape_id=r.shape_id,
                         role=r.role, points=list(r.points))
                    for i, b in enumerate(plan.blocks) for r in b.runs]
            st = plan.stats
            common = dict(name=n, rel=rel, width=w, garment=g, cfg_kwargs=kw,
                          image_size=(img_w, img_h), art_box_frac=result.art_box_frac,
                          px_per_mm=result.px_per_mm, design_size_mm=result.design_size_mm,
                          design_class=result.design_class)
            pickle.dump(dict(common, regions=regs, runs=runs, design=design, stats=repr(st),
                             warnings=[str(x) for x in getattr(result, "warnings", [])]),
                        open(SCRATCH / f"{n}.pkl", "wb"))
            try:
                pickle.dump(dict(common, result=result), open(SCRATCH / f"{n}.result.pkl", "wb"))
                kept = "result pickled"
            except Exception as e:                      # noqa: BLE001 - diagnostics only
                kept = f"result NOT pickled ({type(e).__name__}: {e})"
            text = sum(1 for r in regs if r["meta"].get("text_candidate"))
            print(f"OK {n} {rel} w={w} class={result.design_class} regions={len(regs)} "
                  f"text={text} runs={len(runs)} img={img_w}x{img_h} art_box={result.art_box_frac} "
                  f"grid={result.px_per_mm:.2f}px/mm {st} {time.time() - t:.0f}s [{kept}]", flush=True)
        except Exception:                               # noqa: BLE001 - keep the batch going
            print(f"FAIL {n} after {time.time() - t:.0f}s", flush=True)
            traceback.print_exc()
            sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1:] or list(CASES))
