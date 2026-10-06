import sys, pickle, time, traceback, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]        # digitizer/
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
from digitizer_core import PipelineConfig, digitize
from digitizer_core.adapter import plan_to_design
CASES = {
 "becker": ("becker_marine_logo.png", 95.7, "left_chest"),
 "fremont": ("photo/logo_hotel_fremont.webp", 92.5, "patch"),
 "enthusiast": ("photo/enthusiast_logo.png", 100.0, "left_chest"),
 "tires": ("logo_script_tires.png", 100.0, "left_chest"),
 "bridge": ("photo/logo_bridge_bar.jpg", 80.0, "left_chest"),
 "gaulke": ("art/logo_golke_roofing.png", 95.2, "left_chest"),
 "drone": ("photo/drone_render.png", 80.0, "left_chest"),
}
names = sys.argv[1:] or list(CASES)
for n in names:
    rel, w, g = CASES[n]
    t = time.time()
    try:
        cfg = PipelineConfig(target_width_mm=w, garment_id=g, max_colors=6)
        result, plan = digitize(ROOT / "testdata" / rel, cfg)
        design = plan_to_design(plan)
        regs = [dict(shape_id=r.shape_id, polygon=r.polygon, meta=dict(r.meta),
                     thread_index=getattr(r, "thread_index", None)) for r in result.regions]
        runs = [dict(block=i, kind=r.kind, jump=r.jump, trim=r.trim, shape_id=r.shape_id, role=r.role,
                     points=list(r.points)) for i, b in enumerate(plan.blocks) for r in b.runs]
        st = plan.stats
        pickle.dump(dict(name=n, rel=rel, width=w, garment=g, design_class=result.design_class,
                         regions=regs, runs=runs, design=design, stats=repr(st),
                         warnings=[str(x) for x in getattr(result, "warnings", [])]),
                    open(OUT / f"{n}.pkl", "wb"))
        print(f"OK {n} {rel} w={w} class={result.design_class} regions={len(regs)} runs={len(runs)} {st} {time.time()-t:.0f}s", flush=True)
    except Exception:
        print(f"FAIL {n}", flush=True); traceback.print_exc(); sys.stdout.flush()
