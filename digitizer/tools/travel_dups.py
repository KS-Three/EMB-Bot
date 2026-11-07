"""travel_dups: how often does one `stitch_shape` ask `travel_path` the same question twice?

The question this answers is whether memoizing `stage6_fill.travel_path` per
`stitch_shape` (PR #1294's named follow-up) can pay. It digitizes one design
through the Studio's own request (`tools.pro_pair.request`) with
`stage6_fill.travel_path` wrapped by a counter. The counter always runs the
real function and changes nothing. It keys every call with an EXACT key (`Key`
below: everything the function reads, which `tests/test_travel_dups.py` holds
against its call graph) and groups the calls by the `stitch_shape` call they
are made under, which is the lifetime such a memo would have.

Reports, over the whole stage-7 run (`plan_stitches`):

- `calls`: every `travel_path` call stage6_fill made under a `stitch_shape`.
  `trivial` of them are hops shorter than `TINY_STITCH_MM`, which return at
  once and are not keyed;
- `bypass`: calls with an end that is not a tuple of two Python floats, which
  an exact key will not merge (`_densify` hands `b` itself back as the route's
  last point);
- `dups`: calls whose exact key was already seen under the same
  `stitch_shape` (what a memo would serve) and `dup_rate` = dups / calls;
- `secs` / `dup_secs`: time inside `travel_path` for all keyed calls and for
  the repeated ones. `dup_secs` is the MOST an exact memo can save; `key_secs`
  is what keying cost and comes back out of it;
- `loose`: repeats under two LOOSER keys an exact memo may not use. `no_cache`
  ignores the stale rings in the caller's ring cache (the function tries them
  first, so they can change the route). `ends` keeps only the two ends and
  whether sewn ground was passed. These are ceilings on any memo of
  `travel_path`, exact or not;
- `by_caller`: calls, time and repeats per calling function.

    python -m tools.travel_dups testdata/photo/owl_kent.jpg --width 80 --garment left_chest
    python -m tools.travel_dups testdata/photo/logo_hotel_fremont.webp --width 81 --garment hat_front
        [--json OUT]

Measured 2026-11-07 on owl_kent (80 mm, left chest): 4,915 calls, 428 exact
repeats (8.7%), 0.75 s of 17.5 s in `travel_path`. The loosest key finds
1.3 s. Stage 7 is ~56 s, so a travel memo cannot reach 2.5% of it. Read the
output as a repeat RATE, not a stage-7 benchmark: the counter's bookkeeping
runs inside the wall time it prints.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from digitizer_core import machine  # noqa: E402
from digitizer_core import stage6_fill as F  # noqa: E402
from shapely.geometry import LineString  # noqa: E402


class Key:
    """An exact key for one `travel_path(poly, ring, a, b, slack, sewn, cache)`
    call. Two calls with equal keys get the same route and leave the same ring
    cache behind.

    - `poly`, `slack` and each guide ring are keyed by their WKB bytes. Each
      object is hashed once: shapely geometry is immutable, and `ids` keeps
      every object it has hashed alive, so an id cannot be reused.
    - `a` and `b` are keyed by their float bits, and only when both are tuples
      of two Python floats. Any other end returns None.
    - `sewn` is keyed as None, as a `_Sewn` by its footprints IN ORDER
      (`clipped` unions them, which is order-sensitive in the last bits), or
      as any other geometry by its WKB.
    - `cache` is keyed as absent, or by the stale unsewn rings it holds, ring
      by ring, which the function tries before building fresh ones.

    Everything else the function reads (constants, `machine`, three pure
    caches) is fixed for a process; `tests/test_travel_dups.py` pins that list.
    """

    def __init__(self) -> None:
        self.ids: dict[int, tuple[object, bytes]] = {}

    def geom(self, g) -> bytes:
        got = self.ids.get(id(g))
        if got is not None and got[0] is g:
            return got[1]
        d = hashlib.blake2b(g.wkb, digest_size=16).digest()
        self.ids[id(g)] = (g, d)
        return d

    def __call__(self, poly, ring, a, b, slack, sewn, cache) -> bytes | None:
        if not (type(a) is tuple and type(b) is tuple and len(a) == 2 and len(b) == 2
                and type(a[0]) is float and type(a[1]) is float
                and type(b[0]) is float and type(b[1]) is float):
            return None
        h = hashlib.blake2b(digest_size=32)
        h.update(struct.pack("<4d", a[0], a[1], b[0], b[1]))
        h.update(self.geom(poly))
        h.update(b"s-" if slack is None else b"s+" + self.geom(slack))
        if ring is None:
            h.update(b"r-")
        elif isinstance(ring, LineString):
            h.update(b"r1" + self.geom(ring))
        else:
            h.update(b"r*" + struct.pack("<I", len(ring)))
            for r in ring:
                h.update(self.geom(r))
        if sewn is None:
            h.update(b"w-")
        elif isinstance(sewn, F._Sewn):
            h.update(b"w+" + struct.pack("<I", sewn._n))
            for i in range(sewn._n):
                h.update(self.geom(sewn._parts[i]))
        else:
            h.update(b"wg" + self.geom(sewn))
        if cache is None:
            h.update(b"c-")
        else:
            stale = cache.get("unsewn_rings")
            if not stale:
                h.update(b"c0")
            else:
                h.update(b"c+" + struct.pack("<I", len(stale)))
                for r in stale:
                    h.update(self.geom(r))
        return h.digest()


def _stitch_shape_code():
    fn = F.stitch_shape
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn.__code__


@contextlib.contextmanager
def counting():
    """Count `stage6_fill.travel_path` calls inside the block (the dict it
    yields, filled in as they happen); every call still runs the real thing."""
    stats = Counter()
    secs: dict[str, float] = defaultdict(float)
    by_caller: dict[str, Counter] = defaultdict(Counter)
    state: dict = {"scope": None}
    raw = F.travel_path
    key = Key()
    shape_code = _stitch_shape_code()

    def scope_frame():
        f = sys._getframe(2)
        while f is not None and f.f_code is not shape_code:
            f = f.f_back
        return f

    def counted(poly, ring, a, b, slack=None, sewn=None, cache=None):
        scope = scope_frame()
        if scope is None:           # outside stitch_shape: no memo would be open
            stats["unscoped"] += 1
            return raw(poly, ring, a, b, slack, sewn, cache)
        if scope is not state["scope"]:
            # held, so the frame cannot be freed and its id reused
            state.update(scope=scope, exact=set(), no_cache=set(), ends=set())
            key.ids.clear()
        caller = sys._getframe(1).f_code.co_name
        stats["calls"] += 1
        by_caller[caller]["calls"] += 1
        if math.dist(a, b) < machine.TINY_STITCH_MM:
            stats["trivial"] += 1
            return raw(poly, ring, a, b, slack, sewn, cache)
        t = time.perf_counter()
        k = key(poly, ring, a, b, slack, sewn, cache)
        loose = None if k is None else key(poly, ring, a, b, slack, sewn, None)
        secs["key"] += time.perf_counter() - t
        t = time.perf_counter()
        out = raw(poly, ring, a, b, slack, sewn, cache)
        dt = time.perf_counter() - t
        secs["all"] += dt
        by_caller[caller]["ms"] += dt * 1e3
        if k is None:
            stats["bypass"] += 1
            return out
        for name, kk in (("exact", k), ("no_cache", loose), ("ends", (a, b, sewn is None))):
            if kk in state[name]:
                stats[f"dups_{name}"] += 1
                secs[f"dup_{name}"] += dt
                if name == "exact":
                    by_caller[caller]["dups"] += 1
                    by_caller[caller]["dup_ms"] += dt * 1e3
            else:
                state[name].add(kk)
        return out

    report: dict = {}
    F.travel_path = counted
    try:
        yield report
    finally:
        F.travel_path = raw
        state.clear()
        calls = stats["calls"]
        report.update({
            "calls": calls, "trivial": stats["trivial"], "bypass": stats["bypass"],
            "unscoped": stats["unscoped"], "dups": stats["dups_exact"],
            "dup_rate": round(stats["dups_exact"] / calls, 4) if calls else 0.0,
            "secs": round(secs["all"], 3), "dup_secs": round(secs["dup_exact"], 3),
            "key_secs": round(secs["key"], 3),
            "loose": {name: {"dups": stats[f"dups_{name}"],
                             "dup_secs": round(secs[f"dup_{name}"], 3)}
                      for name in ("no_cache", "ends")},
            "by_caller": {c: {f: round(v, 1) if isinstance(v, float) else v
                              for f, v in n.items()}
                          for c, n in sorted(by_caller.items(), key=lambda kv: -kv[1]["ms"])},
        })


def measure(art, width_mm: float, garment: str) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_pair

    art = Path(art)
    data = art.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(width_mm, garment))))
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    with counting() as report:
        t = time.perf_counter()
        plan_stitches(result, cfg)
        stage7 = time.perf_counter() - t
    return {"art": str(art), "width_mm": width_mm, "garment": garment,
            "stage7_secs": round(stage7, 2), **report}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("art")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    out = measure(a.art, a.width, a.garment)
    text = json.dumps(out, indent=2)
    print(text)
    if a.json:
        Path(a.json).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
