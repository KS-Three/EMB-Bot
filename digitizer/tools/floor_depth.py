#!/usr/bin/env python
"""How far BELOW zero do the floored designs sit?

`run_preflight` scores `max(0, 100 - 30*blocks - 12*warns)`. The clamp is
deliberate — a negative grade means nothing to an operator — but it means the
metric SATURATES, and a saturated metric cannot rank the designs sitting on it
or register any improvement to them.

Measured 2026-09-06 over the scorecard corpus: **12 of 52 design/garment
combos land on exactly 0**, with unclamped scores from **-272 to -38** — a
234-point spread behind one printed value. `screenshot_phone_ui_golke` would
have to clear **312 points, about eleven blocking findings**, before its grade
moved a single letter.

That is the mechanism under disagreement 1 in
`docs/yardstick-disagreements-2026-09-06.md`: a real fix to a floored design
is invisible not only because `THREAD_MATCH_POOR` aggregates per thread, but
because the design is hundreds of points under water. It also explains the
exception — `dissolve_phantom_blends` moves `gaulke_roofing` F 0 -> C 64
because gaulke is the SHALLOW one (F 4), not floored.

    .venv/bin/python -m tools.floor_depth
"""
from __future__ import annotations

import sys

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

# Kept in step with preflight rather than re-derived: if the deduction table
# or the bands move, this reads the new ones.
BLOCK = pf._DEDUCT["block"]
WARN = pf._DEDUCT["warn"]
D_GRADE = 40                       # the first band above F


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES, MATRIX

    rows = []
    for fx in FIXTURES:
        for m in MATRIX:
            art = TESTDATA / fx
            cfg = PipelineConfig(**m)
            try:
                result, plan = digitize(art, cfg)
                rep = pf.run_preflight(result, plan, cfg, image=art)
            except Exception as exc:                    # pragma: no cover
                print(f"SKIP {fx} {m['garment_id']}: {exc}")
                continue
            blocks = sum(1 for f in rep["findings"]
                         if f["severity"] == "block")
            warns = sum(1 for f in rep["findings"] if f["severity"] == "warn")
            rows.append((fx, m["garment_id"], rep["score"], rep["grade"],
                         100 - BLOCK * blocks - WARN * warns, blocks, warns))

    print(f"\n{'fixture':42} {'garment':12} {'score':>5} {'raw':>6} blk warn")
    for fx, g, s, _gr, raw, b, w in sorted(rows, key=lambda r: r[4]):
        print(f"{fx:42} {g:12} {s:5} {raw:6} {b:3} {w:4}"
              f"{'  <-- FLOORED' if s == 0 else ''}")

    floored = [r for r in rows if r[2] == 0]
    print(f"\n{len(rows)} combos, {len(floored)} floored at 0")
    if not floored:
        return 0
    raws = [r[4] for r in floored]
    print(f"  unclamped scores run {min(raws)} to {max(raws)} — a spread of "
          f"{max(raws) - min(raws)} points behind ONE printed value")
    print(f"  points to clear before F -> D ({D_GRADE}) shows anything:")
    for fx, g, _s, _gr, raw, _b, _w in sorted(floored, key=lambda r: r[4]):
        need = D_GRADE - raw
        print(f"     {fx} [{g}]: {need} pts "
              f"(~{(need + BLOCK - 1) // BLOCK} blocking findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
