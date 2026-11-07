"""ring_route_share: how much of `_order_cost_walk` a numpy `_ring_route` could save.

PR #1309 left this as option 3: on owl_kent, `_order_cost_walk` makes 2,729
`travel_path` calls costing ~10 s, and a vectorised `_ring_route` (C3 in
`stage7-scene-speed-2026-10-29`) was estimated at 5-7% of stage 7. This tool
measures that before anyone lands it. It digitizes one design through the
Studio's request (`tools.pro_pair.request`) and reports, for stage 7
(`plan_stitches`):

- `stage7_secs`, `walk_secs`: wall time of stage 7 and of every
  `_order_cost_walk` generator (time inside its `next()` calls only);
- `dst_md5`: md5 of `export_dst` of the plan;
- with `--profile`: `_ring_route` calls and time, overall and inside the
  walk, and a REPLAY of every captured call. The replay times the engine's
  `_ring_route` against `ring_route_np` below (interleaved, median of 3) and
  splits the engine's time into what no Python rewrite can touch: the
  `_ring_arc` cache lookup (an `lru_cache` hashing the ring's WKB on every
  call), two `project` and two `interpolate` GEOS calls, and `ring.length`.
  `rewritable_secs` is what is left: the most a numpy body can save.

`--candidate` swaps `ring_route_np` in for the engine's `_ring_route` (in
stage6_fill and in knockdown, which imports it by name) for the whole run, so
two runs give the before/after walk time and DST md5.

    python -m tools.ring_route_share testdata/photo/owl_kent.jpg --width 80 --garment left_chest --profile
    python -m tools.ring_route_share testdata/photo/owl_kent.jpg --width 80 --garment left_chest [--candidate]

Measured 2026-11-07 on owl_kent (80 mm, left chest), on a loaded laptop (stage
7 at 104 s against ~56 s quiet): the walk's 6,630 `_ring_route` calls cost
2.83 s of its 18.8 s. Half of that is GEOS and the cache lookup, so the most
any rewrite of the body could save is 1.68 s here (~0.9 s quiet). The
candidate, replayed, saved 0.28 s in the walk and nothing over all 12,067 calls
(numpy's per-call overhead eats the gain on the median 152-vertex ring). It is
exact (7 DSTs identical), and it stays out of the engine.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

import numpy as np  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402

from digitizer_core import knockdown, machine  # noqa: E402
from digitizer_core import stage6_fill as F  # noqa: E402


@functools.lru_cache(maxsize=256)
def _arc_arrays(ring: LineString):
    """`F._ring_arc`'s table, plus numpy copies of it. `cum` is built by the
    engine's own loop (`math.dist`, summed left to right) and only then put in
    an array, so every offset below is computed from the same float the
    engine's loop reads; `np.cumsum` of `np.hypot` would not be."""
    coords, cum = F._ring_arc(ring)
    return coords, np.asarray(coords, dtype=float), np.asarray(cum[1:], dtype=float), ring.length


def ring_route_np(ring: LineString, a: tuple[float, float],
                  b: tuple[float, float], way: str | None = None,
                  ) -> list[tuple[float, float]]:
    """`stage6_fill._ring_route` with the per-vertex loop and sort in numpy.

    Exact by construction, which `tests/test_ring_route_exact.py` checks:

    - `np.remainder` on float64 is Python's float `%` (fmod, then add the
      divisor when the signs differ; a zero takes the divisor's sign), so each
      offset is the engine's offset bit for bit, `% total` wrap included;
    - `between.sort()` sorts (offset, (x, y)) tuples: offset first, a tie
      broken by x, then y. `np.lexsort` with keys (y, x, offset) is that order,
      and it is stable, so a full tie (a repeated vertex) keeps ring order as
      the engine's stable sort does (equal values either way);
    - the TINY_STITCH_MM floor keeps the engine's Python loop and
      `math.dist`, over the sorted points only: it depends on the last point
      kept, and `np.hypot` may differ from `math.dist` in the last bit;
    - every point returned is the engine's own tuple of Python floats.
    """
    coords, xy, cum, total = _arc_arrays(ring)
    ta, tb = ring.project(Point(a)), ring.project(Point(b))
    forward = (tb - ta) % total
    backward = total - forward
    ahead = forward <= backward if way is None else way == "ahead"
    span = forward if ahead else backward

    off = np.remainder(cum - ta, total) if ahead else np.remainder(ta - cum, total)
    idx = np.flatnonzero((off > 0.0) & (off < span))
    if len(idx) > 1:
        sel = xy[idx + 1]
        keys = [sel[:, d] for d in range(sel.shape[1] - 1, -1, -1)]
        keys.append(off[idx])
        idx = idx[np.lexsort(keys)]

    start, end = ring.interpolate(ta), ring.interpolate(tb)
    out = [(start.x, start.y)]
    last = out[0]
    tiny = machine.TINY_STITCH_MM
    for i in (idx + 1).tolist():
        p = coords[i]
        if math.dist(last, p) >= tiny:
            out.append(p)
            last = p
    out.append((end.x, end.y))
    return out


@contextlib.contextmanager
def swapped(fn):
    """`fn` in place of `_ring_route` everywhere the engine calls it."""
    old_f, old_k = F._ring_route, knockdown._ring_route
    F._ring_route = knockdown._ring_route = fn
    try:
        yield
    finally:
        F._ring_route, knockdown._ring_route = old_f, old_k


@contextlib.contextmanager
def timing(profile: bool):
    """Time every `_order_cost_walk` (and with `profile`, every `_ring_route`,
    keeping its arguments for the replay). Yields the dict it fills."""
    st = {"walk_secs": 0.0, "walk_calls": 0}
    depth = [0]
    calls: list = []
    raw_walk = F._order_cost_walk
    raw_rr, raw_rr_k = F._ring_route, knockdown._ring_route
    pc = time.perf_counter

    def walk(*a, **k):
        st["walk_calls"] += 1
        g = raw_walk(*a, **k)
        while True:
            depth[0] += 1
            t = pc()
            try:
                v = next(g)
            except StopIteration:
                return
            finally:
                depth[0] -= 1
                st["walk_secs"] += pc() - t
            yield v

    def rr(ring, a, b, way=None):
        t = pc()
        out = raw_rr(ring, a, b, way)
        calls.append((ring, a, b, way, pc() - t, depth[0] > 0))
        return out

    F._order_cost_walk = walk
    if profile:
        F._ring_route = knockdown._ring_route = rr
    try:
        yield st
    finally:
        F._order_cost_walk = raw_walk
        F._ring_route, knockdown._ring_route = raw_rr, raw_rr_k
        if profile:
            st["calls"] = calls


def replay(calls, reps: int = 3) -> dict:
    """Time the engine's `_ring_route` against `ring_route_np` on `calls`
    ((ring, a, b, way) ...), and the engine's fixed costs, median of `reps`."""
    pc = time.perf_counter
    eng = F._ring_route
    mismatch = sum(1 for r, a, b, w in calls if ring_route_np(r, a, b, w) != eng(r, a, b, w))
    t_eng, t_np, t_fixed = [], [], []
    for _ in range(reps):
        for fn, sink in ((eng, t_eng), (ring_route_np, t_np)):
            t = pc()
            for r, a, b, w in calls:
                fn(r, a, b, w)
            sink.append(pc() - t)
        t = pc()
        for r, a, b, w in calls:
            F._ring_arc(r)
            ta, tb = r.project(Point(a)), r.project(Point(b))
            r.interpolate(ta), r.interpolate(tb), r.length
        t_fixed.append(pc() - t)
    e, n, f = (statistics.median(x) for x in (t_eng, t_np, t_fixed))
    return {"calls": len(calls), "mismatch": mismatch, "engine_secs": round(e, 3),
            "numpy_secs": round(n, 3), "saved_secs": round(e - n, 3),
            "fixed_secs": round(f, 3), "rewritable_secs": round(e - f, 3)}


def measure(art, width_mm: float, garment: str, candidate: bool = False,
            profile: bool = False) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.export import export_dst
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_pair

    art = Path(art)
    data = art.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(width_mm, garment))))
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    swap = swapped(ring_route_np) if candidate else contextlib.nullcontext()
    with swap, timing(profile) as st:
        t = time.perf_counter()
        plan = plan_stitches(result, cfg)
        stage7 = time.perf_counter() - t
    out = {"art": str(art), "width_mm": width_mm, "garment": garment,
           "ring_route": "numpy" if candidate else "engine",
           "stage7_secs": round(stage7, 2), "walk_secs": round(st["walk_secs"], 2),
           "walk_calls": st["walk_calls"],
           "dst_md5": hashlib.md5(export_dst(plan)).hexdigest()}
    if profile:
        calls = st["calls"]
        walk = [c for c in calls if c[5]]
        out["ring_route_calls"] = len(calls)
        out["ring_route_secs"] = round(sum(c[4] for c in calls), 3)
        out["ring_route_walk_calls"] = len(walk)
        out["ring_route_walk_secs"] = round(sum(c[4] for c in walk), 3)
        out["replay_all"] = replay([c[:4] for c in calls])
        out["replay_walk"] = replay([c[:4] for c in walk])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("art")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--candidate", action="store_true",
                    help="run with ring_route_np in place of the engine's _ring_route")
    ap.add_argument("--profile", action="store_true",
                    help="time every _ring_route call and replay them")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    out = measure(a.art, a.width, a.garment, a.candidate, a.profile)
    text = json.dumps(out, indent=2)
    print(text)
    if a.json:
        Path(a.json).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
