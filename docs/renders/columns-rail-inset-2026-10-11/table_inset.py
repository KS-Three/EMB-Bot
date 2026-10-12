"""OUTDIR/*.jsonl from measure_inset.py -> markdown tables on stdout."""
import json
import sys
from pathlib import Path

rows = [json.loads(line) for p in sorted(Path(sys.argv[1]).glob("*.jsonl"))
        for line in p.read_text().splitlines() if line.strip()]
ORDER = {"shipped": 0, "lane0": 1, "lane": 2}
NAME = {"shipped": "shipped", "lane0": "lane before", "lane": "lane after"}
rows.sort(key=lambda r: (r["fixture"], r["width"], ORDER[r["arm"]]))

print("## lost_frac, three readings (grid = as the regression test reads it; "
      "matched = at the shipped design's physical alignment, the one for deltas)\n")
print("| logo | mm | arm | grid | one-pixel | matched | unsewn mm2 | wrong colour mm2 | overshoot mm2 "
      "| letters overshoot / unsewn mm2 | penetration median mm | stitches | trims |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    m = r["matched"]
    pen = r["penetration_median_mm"]
    print(f"| {r['fixture']} | {r['width']:g} | {NAME[r['arm']]} | {r['grid']['lost_frac']:.4f} "
          f"| {r['fine']['lost_frac']:.4f} | {m['lost_frac']:.4f} | {m['unsewn_mm2']} "
          f"| {m['wrong_colour_mm2']} | {m['overshoot_mm2']} "
          f"| {m['letters_overshoot_mm2']} / {m['letters_unsewn_mm2']} "
          f"| {'-' if pen is None else f'{pen:+.3f}'} | {r['stitches']:,} | {r['trims']} |")

print("\n## after minus before (lane), and after minus shipped\n")
print("| logo | mm | grid: after-before | one-pixel | matched | overshoot mm2 | unsewn mm2 "
      "| penetration: before / after / shipped | after-shipped matched |")
print("|---|---|---|---|---|---|---|---|---|")
by = {(r["fixture"], r["width"], r["arm"]): r for r in rows}
for (fx, w, arm), r in sorted(by.items()):
    if arm != "lane":
        continue
    b, s = by.get((fx, w, "lane0")), by.get((fx, w, "shipped"))
    if not b or not s:
        continue
    pen = [x["penetration_median_mm"] for x in (b, r, s)]
    print(f"| {fx} | {w:g} | {r['grid']['lost_frac'] - b['grid']['lost_frac']:+.4f} "
          f"| {r['fine']['lost_frac'] - b['fine']['lost_frac']:+.4f} "
          f"| {r['matched']['lost_frac'] - b['matched']['lost_frac']:+.4f} "
          f"| {r['matched']['overshoot_mm2'] - b['matched']['overshoot_mm2']:+.1f} "
          f"| {r['matched']['unsewn_mm2'] - b['matched']['unsewn_mm2']:+.1f} "
          f"| {' / '.join('-' if p is None else f'{p:+.3f}' for p in pen)} "
          f"| {r['matched']['lost_frac'] - s['matched']['lost_frac']:+.4f} |")
