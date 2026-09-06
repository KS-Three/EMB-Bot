#!/usr/bin/env python
"""How many cones does `revalidate_threads` ADD, and how many escape the
selected palette? (MASTER_SCOPE 15)

Defect 15 records that an undeclared photograph "sews more spools than the cone
list names", because the re-snap's argmin runs over the WHOLE chart on every
non-photo class. That is deliberate and byte-identity-pinned — the function's
own docstring argues it — but it had never been counted across the corpus.

Measured 2026-09-06: **34 cones added, 25 of them outside the selected
palette**, and every escape is on the GRADIENT lane. All nine photo-class
fixtures add zero, which is the control: the 2026-08-23 palette binding works,
and the lane real customer logo art routes to never got it.

Two columns, and the difference matters:
  ADDED            cones in the final design that no region wore at pass entry
                   (a re-snap onto a palette spool nothing happened to wear is
                   legitimate — the flat lane's 1s are all this)
  outside palette  cones that are in NEITHER the entry set NOR the selection —
                   the actual escape

    python -m tools.resnap_escape        # from digitizer/, ~20 min

Probes `pipeline.revalidate_threads`, NOT `stage4_vectorize`'s: `pipeline`
binds the name at import, so patching the defining module silently does
nothing.
"""
import pathlib
from digitizer_core import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core import pipeline as pl
from digitizer_core.threads import chart_for
from tools.corpus_scorecard import FIXTURES

TD = pathlib.Path("testdata")
chart = chart_for(PipelineConfig())
_real = pl.revalidate_threads

def one(fx):
    seen = {}
    def probe(regions, p, cfg, **kw):
        seen["entry"] = {r.thread_index for r in regions
                         if not r.meta.get("enclosed_background")}
        seen["cls"] = kw.get("design_class")
        seen["palette"] = set(kw.get("palette_indices") or ())
        return _real(regions, p, cfg, **kw)
    pl.revalidate_threads = probe
    try:
        res = run_stages(TD / fx, PipelineConfig(target_width_mm=80.0))
    finally:
        pl.revalidate_threads = _real
    end = {r.thread_index for r in res.regions}
    return seen, end

print(f"{'fixture':<34}{'class':>14}{'entry':>7}{'final':>7}{'ADDED':>7}"
      f"{'outside palette':>17}")
tot_added = 0
for fx in FIXTURES:
    try:
        seen, end = one(fx)
    except Exception as e:
        print(f"{pathlib.Path(fx).name:<34}  SKIP {type(e).__name__}: {e}")
        continue
    added = end - seen["entry"]
    outside = end - seen["palette"] if seen["palette"] else set()
    tot_added += len(added)
    mark = "  <==" if added else ""
    print(f"{pathlib.Path(fx).name:<34}{str(seen['cls']):>14}"
          f"{len(seen['entry']):>7}{len(end):>7}{len(added):>7}"
          f"{len(outside):>17}{mark}")
print(f"\ncones added by the re-snap across the corpus: {tot_added}")
