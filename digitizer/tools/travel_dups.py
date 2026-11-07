"""travel_dups: how often does one `stitch_shape` ask `travel_path` the same question twice?

Digitizes one design through the Studio's own request (`tools.pro_pair.request`)
with `stage6_fill.travel_path` replaced by a counter that ALWAYS runs the
unmemoized body (`_travel_path`) -- so the run is the pre-memo behaviour,
nothing is served from the memo -- and keys every call with the memo's own key
(`_TravelMemo.key`), grouped by `stitch_shape` scope, the memo's lifetime.

Reports, for stage 7 as a whole:

- `calls`: every `travel_path` call stage6_fill made inside a `stitch_shape`;
  `trivial` of them are the sub-`TINY_STITCH_MM` hops the memo never keys;
- `bypass`: calls the memo cannot key (an end that is not a tuple of two floats);
- `dups`: calls whose key was already seen in the same scope -- what the memo
  turns into hits -- and `dup_rate` = dups / calls;
- `secs` / `dup_secs`: wall time inside the body for all calls and for the
  duplicate ones, i.e. the most the memo can save (the key costs come back
  out of that; `key_secs` is their total);
- `loose`: the duplicates two LOOSER keys would find, which an exact memo
  may not merge -- `no_cache` ignores the stale rings in the caller's ring
  cache (the body tries them first, so they can change the route), `ends`
  keeps only the two ends and whether sewn ground was passed. The gap
  between them and `dups` is where the repeats are lost;
- `by_caller`: the same split per calling function.

    python -m tools.travel_dups testdata/photo/owl_kent.jpg --width 80 --garment left_chest
    python -m tools.travel_dups testdata/photo/logo_hotel_fremont.webp --width 81 --garment hat_front
        [--json OUT]

Read it as a duplicate RATE for the memo, not a timing benchmark: the counter's
own bookkeeping is inside the stage-7 wall it prints.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))


def measure(art, width_mm: float, garment: str) -> dict:
    from digitizer_core import machine
    from digitizer_core import stage6_fill as F
    from digitizer_service.app import _decode, _parse_config
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tools import pro_pair

    stats = Counter()
    secs = defaultdict(float)
    by_caller: dict[str, Counter] = defaultdict(Counter)
    state = {"scope": None, "seen": set(), "no_cache": set(), "ends": set()}
    raw = F._travel_path
    keyer = F._TravelMemo()          # its own id map; never stores a route

    def counted(poly, ring, a, b, slack=None, sewn=None, cache=None):
        scope = F._TRAVEL_MEMO
        if scope is None:            # outside stitch_shape: not the memo's business
            stats["unscoped"] += 1
            return raw(poly, ring, a, b, slack, sewn, cache)
        if scope is not state["scope"]:
            state.update(scope=scope, seen=set(), no_cache=set(), ends=set())
            keyer.ids.clear()
        caller = sys._getframe(1).f_code.co_name
        stats["calls"] += 1
        by_caller[caller]["calls"] += 1
        if math.dist(a, b) < machine.TINY_STITCH_MM:
            stats["trivial"] += 1
            return raw(poly, ring, a, b, slack, sewn, cache)
        t = time.perf_counter()
        key = keyer.key(poly, ring, a, b, slack, sewn, cache)
        secs["key"] += time.perf_counter() - t
        t = time.perf_counter()
        out = raw(poly, ring, a, b, slack, sewn, cache)
        dt = time.perf_counter() - t
        secs["all"] += dt
        if key is None:
            stats["bypass"] += 1
        elif key in state["seen"]:
            stats["dups"] += 1
            secs["dup"] += dt
            by_caller[caller]["dups"] += 1
            by_caller[caller]["dup_ms"] += dt * 1e3
        else:
            state["seen"].add(key)
        # Looser questions an EXACT memo may not merge, to show where the
        # repeats are lost: the same call but for the ring cache's stale
        # rings, and the same two ends with sewn ground or without.
        if key is not None:
            for name, k in (("no_cache", keyer.key(poly, ring, a, b, slack, sewn, None)),
                            ("ends", (a, b, sewn is None))):
                if k in state[name]:
                    stats[f"dups_{name}"] += 1
                    secs[f"dup_{name}"] += dt
                else:
                    state[name].add(k)
        by_caller[caller]["ms"] += dt * 1e3
        return out

    art = Path(art)
    data = art.read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(width_mm, garment))))
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    original = F.travel_path
    F.travel_path = counted
    try:
        t = time.perf_counter()
        plan_stitches(result, cfg)
        stage7 = time.perf_counter() - t
    finally:
        F.travel_path = original
    calls = stats["calls"]
    return {
        "art": str(art), "width_mm": width_mm, "garment": garment,
        "stage7_secs": round(stage7, 2),
        "calls": calls, "trivial": stats["trivial"], "bypass": stats["bypass"],
        "unscoped": stats["unscoped"], "dups": stats["dups"],
        "dup_rate": round(stats["dups"] / calls, 4) if calls else 0.0,
        "secs": round(secs["all"], 3), "dup_secs": round(secs["dup"], 3),
        "key_secs": round(secs["key"], 3),
        "loose": {name: {"dups": stats[f"dups_{name}"], "dup_secs": round(secs[f"dup_{name}"], 3)}
                  for name in ("no_cache", "ends")},
        "by_caller": {k: {f: round(v, 1) if isinstance(v, float) else v for f, v in c.items()}
                      for k, c in sorted(by_caller.items(), key=lambda kv: -kv[1]["ms"])},
    }


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
