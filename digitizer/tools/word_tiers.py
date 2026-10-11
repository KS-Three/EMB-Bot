"""Does each WORD sew on one tier, or do its letters split?

L3 of `docs/lettering-architecture-rd-2026-10-07.md`: the tier a letter
sews on is decided per SHAPE today -- the run tier by the shape's own area
(`stage7_sequence.routes_to_run`), satin against fill by its own width
(`classify_ribbon`), the bean letter by its own ink -- so one word's letters
can land on different techniques, and a letter can change tier when the
design is resized by a millimetre (the 87 -> 88 mm cliff,
`classifier-cliff-is-input-resolution-2026-09-16`). L3 decides once per
word. This counts what today's engine does.

Per labelled line (`testdata/lettering_truth.json`), each member's tier is
read off the runs it sewed: `satin` (any satin run), else `fill`, else
`run` (the run tier's outline), `bean` (a bean letter), or `unsewn`. A line
is MIXED when its sewn members are not all on one tier. Counts, not
agreement rates: no raw agreement figure is quoted (ROADMAP gate 4).

    .venv/bin/python -m tools.word_tiers                     # corpus sizes
    .venv/bin/python -m tools.word_tiers --words --widths 70,80,90   # a size sweep
    .venv/bin/python -m tools.word_tiers --flag lettering_words --flag lettering_word_tiers
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TIERS = ("satin", "fill", "run", "bean", "unsewn")


def member_tiers(plan) -> dict[str, str]:
    """shape_id -> the tier it sewed on, from the plan's runs."""
    from digitizer_core import stitches
    kinds: dict[str, set] = collections.defaultdict(set)
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id:
                kinds[r.shape_id].add(r.kind)
    out = {}
    for sid, k in kinds.items():
        if stitches.SATIN in k:
            out[sid] = "satin"
        elif stitches.FILL in k:
            out[sid] = "fill"
        elif stitches.BEAN in k:
            out[sid] = "bean"
        elif stitches.RUN in k:
            out[sid] = "run"
    return out


def measure(name: str, path: Path, width: float, garment: str, lines: dict,
            flags: dict) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tools.thin_strokes import STUDIO_MAX_COLORS
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                         max_colors=STUDIO_MAX_COLORS, **flags)
    gen = build_generation(str(path), cfg)
    if lines is None:
        # Shape ids move with the design's size, so a sweep reads L1's
        # words (`words.detect_words`) as the lines instead of the labels.
        from digitizer_core.threads import chart_for
        from digitizer_core.words import detect_words
        lines = {f"word{i}:{len(w.members)}@{w.cap_mm:.1f}mm": [r.shape_id for r in w.members]
                 for i, w in enumerate(detect_words(gen.regions, chart=chart_for(cfg)))}
    have = {r.shape_id for r in gen.regions}
    if any(s not in have for ids in lines.values() for s in ids):
        return {"stale": True}
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    tiers = member_tiers(plan)
    rows = []
    for line, ids in lines.items():
        got = collections.Counter(tiers.get(s, "unsewn") for s in ids)
        sewn = {t for t in got if t != "unsewn"}
        rows.append({"line": line, "members": len(ids), "tiers": dict(got),
                     "mixed": len(sewn) > 1})
    return {"fixture": name, "width_mm": width, "lines": rows,
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims}


def main(argv=None) -> int:
    from tools.thin_strokes import corpus_cases, parse_flags
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*")
    ap.add_argument("--widths", help="comma-separated design widths in mm (default: corpus size)")
    ap.add_argument("--flag", action="append", help="NAME or NAME=VALUE, repeatable")
    ap.add_argument("--words", action="store_true",
                    help="lines are L1's detected words, not the labels (any size)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    flags = parse_flags(args.flag)
    truth = json.loads((ROOT / "testdata" / "lettering_truth.json").read_text())["fixtures"]
    widths = [float(w) for w in args.widths.split(",")] if args.widths else None
    out = []
    for name, path, w, g in corpus_cases():
        if name not in truth or (args.fixtures and name not in args.fixtures):
            continue
        for width in widths or [w]:
            res = measure(name, path, width, g,
                          None if args.words else truth[name]["lines"], flags)
            if res.get("stale"):
                print(f"{name} @ {width:g} mm: STALE labels at this size, not measured")
                continue
            out.append(res)
            mixed = sum(r["mixed"] for r in res["lines"])
            print(f"{name} @ {width:g} mm: {mixed}/{len(res['lines'])} lines mixed, "
                  f"{res['stitches']:,} stitches / {res['trims']} trims")
            for r in res["lines"]:
                mark = "MIXED" if r["mixed"] else "     "
                print(f"   {mark} {r['line']:24s} {r['tiers']}")
    total = sum(len(r["lines"]) for r in out)
    mixed = sum(x["mixed"] for r in out for x in r["lines"])
    print(f"\n{mixed} of {total} labelled lines mixed across tiers")
    if args.json:
        args.json.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
