"""What each default-ON flag costs in WALL CLOCK, per design.

The edge cap's flip measured its stitch bill (+5.9-26.3%) and not its clock,
and the clock turned out to be 86 minutes a design (PR #464, DOCTRINE "Never
`unary_union` a stitch path before buffering it"). This is the sweep that
would have caught it, generalised: run each design at the shipped defaults,
then once per flag with that flag turned OFF, and time `run_stages` and
`plan_stitches` separately so a cost can be pinned to a stage.

It reads a corpus `prep_all` already wrote and re-digitizes `art.png` from
it — the pro side is not repeated, because none of these flags touch it.

    cd digitizer
    PRO_PARITY_OUT=<prepped corpus> .venv/Scripts/python -m tools.pro_parity.flagcost

Named slugs limit the designs; `--flags a,b` limits the flags (each still
turned off ONE at a time); `--together a,b` adds one arm with all of those
flags off at once.

**A flag that is inert on a design still costs what it costs.** The `same`
column says whether turning it off changed the stitches at all; a flag that
is both expensive AND inert on a design is the interesting case, because it
is paying for nothing there.

**The inert arms are also this harness's own error bar, and the first version
of it needed them.** Run naively — baseline first, then one arm per flag —
every arm looks ~1.5 s cheaper than the baseline on `hotel_fremont_hat`,
including three flags that provably changed nothing (`satin_house_fourfold`,
`merge_duplicate_cones`, `rehome_resnapped` all read +1.66 to +1.70 s while
returning a byte-identical plan). That is warm-up: the first `run_stages` in
a process pays import, cache and allocator costs no later one repeats. So
this now discards a warm-up pass before timing anything, re-measures the
baseline AFTER the arms, and prints the drift between the two baselines as
`+/-` next to every number. **A cost smaller than that drift is not a
measurement** — the report says so rather than ranking it.

**One flag off at a time measures a flag's cost GIVEN every other flag, not
its cost alone, and it cannot see an interaction.** It hit one on its first
real run: `curve_turn_deg` is byte-for-byte inert without `subpixel_edges`,
so turning `subpixel_edges` off also removed `curve_turn_deg`'s 28.8 s and
the report credited `subpixel_edges` with 44 s whose own share is 13.3 s. The
two rows summed to 73 s against a joint cost of 42 s. Never add rows. When two
flags touch the same geometry, add `--together a,b`: one extra arm with all
of them off at once (see docs/flag-runtime-bills-2026-09-12.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from digitizer_core.pipeline import plan_stitches, run_stages

from .prep_all import parity_config

OUT = Path(os.environ.get("PRO_PARITY_OUT", "pro_parity_out"))

# Every flag that is ON by default and landed from 2026-09-01, with the value
# that turns it off. Dates are the config.py line's, by `git log -S`.
FLAGS: dict[str, object] = {
    "enclosed_by_garment": False,       # 2026-09-10
    "subpixel_edges": False,            # 2026-09-09
    "design_ramp": False,               # 2026-09-04
    "fill_travel_under_cover": False,   # 2026-09-03
    "curve_turn_deg": None,             # 2026-09-03
    "satin_house_fourfold": False,      # 2026-09-02
    "merge_duplicate_cones": False,     # 2026-09-02
    "rehome_resnapped": False,          # 2026-09-01
    "edge_cap": "off",                  # 2026-09-01, flipped to "bean" 09-11
    "borders_last": False,              # 2026-08-31, just outside but cheap
}

# Chosen to span what the corpus actually contains rather than to be a
# sample of it: satin lettering that is nearly all columns, a fill-dominated
# flat logo, a gradient badge, and the largest fill in the corpus. A flag
# whose cost scales on crossings shows up on the first; one that scales on
# area shows up on the last.
DESIGNS = ["hotel_fremont_hat", "gaulke_roofing_lc", "precision_drone",
           "machine_hat"]


def _width_mm(meta: dict) -> float:
    """`prep_all` passes the pro bounds' width; `art_meta` records the padded
    raster instead, so the padding comes back off here."""
    return (meta["size_px"][0] - 2 * meta["pad_px"]) / meta["scale_px_per_mm"]


def verdict(saved_s: float, drift_s: float, same: bool) -> str:
    """What an arm's number is allowed to claim.

    The noise floor comes FIRST, deliberately. An arm that moved the clock by
    less than the baseline moved against itself has measured nothing, and
    saying "INERT here" about it would be claiming a result (this flag does
    nothing AND costs nothing) that the run does not support.
    """
    if abs(saved_s) <= drift_s:
        return "under the noise floor"
    return "INERT here" if same else "changes output"


def _digest(plan) -> str:
    h = hashlib.md5()
    for b in plan.blocks:
        for r in b.runs:
            h.update(str(r.kind).encode())
            for x, y in r.points:
                h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()[:12]


def one(art: Path, width_mm: float, off: tuple[str, ...] = ()):
    """One timed digitize with every flag in `off` set to its FLAGS value."""
    cfg = parity_config(width_mm, None)
    for flag in off:
        if flag not in type(cfg).__dataclass_fields__:
            raise SystemExit(f"{flag} is not a PipelineConfig field on this tree")
        if flag not in FLAGS:
            raise SystemExit(f"{flag} has no off value in FLAGS")
        setattr(cfg, flag, FLAGS[flag])
    t0 = time.time()
    res = run_stages(str(art), cfg)
    t1 = time.time()
    plan = plan_stitches(res, cfg)
    t2 = time.time()
    return {
        "stages_s": round(t1 - t0, 2),
        "plan_s": round(t2 - t1, 2),
        "total_s": round(t2 - t0, 2),
        "stitches": sum(len(r.points) for b in plan.blocks for r in b.runs),
        "digest": _digest(plan),
    }


def main():
    args = sys.argv[1:]
    flags = list(FLAGS)
    if "--flags" in args:
        i = args.index("--flags")
        flags = [f for f in args[i + 1].split(",") if f]
        del args[i:i + 2]
    together: tuple[str, ...] = ()
    if "--together" in args:
        i = args.index("--together")
        together = tuple(f for f in args[i + 1].split(",") if f)
        del args[i:i + 2]
    slugs = [a for a in args if not a.startswith("-")] or DESIGNS

    rows = []
    for slug in slugs:
        d = OUT / slug
        art, meta_p = d / "art.png", d / "art_meta.json"
        if not art.exists():
            print(f"[{slug}] SKIP - no art.png in {d}", flush=True)
            continue
        width = _width_mm(json.loads(meta_p.read_text()))
        one(art, width)                             # warm-up, discarded
        base = one(art, width)
        print(f"\n[{slug}] baseline {base['total_s']}s "
              f"(stages {base['stages_s']} + plan {base['plan_s']}), "
              f"{base['stitches']} st", flush=True)
        arms = [(f, one(art, width, (f,))) for f in flags]
        if together:
            arms.append(("+".join(together), one(art, width, together)))
        base2 = one(art, width)                     # the drift this run saw
        drift = abs(base2["total_s"] - base["total_s"])
        mid = (base["total_s"] + base2["total_s"]) / 2.0
        print(f"[{slug}] baseline again {base2['total_s']}s "
              f"-> drift +/-{drift:.2f}s; anything under that is noise",
              flush=True)
        rows.append({"slug": slug, "flag": None, **base, "saved_s": 0.0,
                     "share": 0.0, "same": True, "drift_s": round(drift, 2)})
        for f, r in arms:
            saved = mid - r["total_s"]
            share = saved / mid if mid else 0.0
            same = r["digest"] == base["digest"]
            rows.append({"slug": slug, "flag": f, **r,
                         "saved_s": round(saved, 2), "share": round(share, 4),
                         "same": same, "drift_s": round(drift, 2)})
            print(f"  off:{f:<26} {r['total_s']:7.2f}s "
                  f"(stages {r['stages_s']:6.2f} plan {r['plan_s']:6.2f})  "
                  f"costs {saved:+7.2f}s = {share*100:+6.1f}%  "
                  f"{verdict(saved, drift, same)}", flush=True)
        (OUT / "flagcost.json").write_text(json.dumps(rows, indent=1))

    print("\n=== flags by share of runtime, worst design "
          "(noise-floor arms excluded) ===", flush=True)
    worst: dict = {}
    for r in rows:
        if r["flag"] is None or abs(r["saved_s"]) <= r["drift_s"]:
            continue
        w = worst.get(r["flag"])
        if w is None or r["share"] > w["share"]:
            worst[r["flag"]] = r
    for f, r in sorted(worst.items(), key=lambda kv: -kv[1]["share"]):
        print(f"  {f:<26} {r['share']*100:+6.1f}% of {r['slug']} "
              f"({r['saved_s']:+.2f}s, noise +/-{r['drift_s']})"
              f"{'   INERT THERE' if r['same'] else ''}", flush=True)
    quiet = sorted({r["flag"] for r in rows
                    if r["flag"] and abs(r["saved_s"]) <= r["drift_s"]}
                   - set(worst))
    if quiet:
        print(f"  under the noise floor on every design measured: "
              f"{', '.join(quiet)}", flush=True)


if __name__ == "__main__":
    main()
