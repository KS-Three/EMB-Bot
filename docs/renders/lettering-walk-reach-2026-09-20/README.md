# Sew-out arm — `satin_walk_cursor_reach_mm` (2026-09-20)

Kent's ruling the day it was built: **the flag stays OFF until cloth
settles it.** Both sides of the trade are things the eye judges —
a trim leaves tails to clip and a tie-off bump; a rescued walk leaves
a short run of thread lying on the fabric between letters.

Sew each case's three arms in one hooping, same thread, same
stabiliser. Then answer **question D** below.

**The files are not in the repo** — regenerate them on the machine that will
sew them, which also re-reads them back through pystitch:

    cd digitizer
    .venv/Scripts/python -m tools.sewout_walk_reach      # Windows
    .venv/bin/python -m tools.sewout_walk_reach          # Linux

Nine arms, `.dst` and `.pes` each, into `digitizer/.cache/sewout-walk-reach/`
beside a copy of this sheet. The table below is what that run wrote on
2026-09-20; the tool prints it again each time, so a mismatch means the
engine moved under the sheet.

| case | arm | stitches | trims | exposed travel mm | worst leg mm |
|---|---|---|---|---|---|
| becker100 | off | 8,440 | 54 | 0.4 | 0.4 |
| becker100 | reach4 | 8,433 | 51 | 3.4 | 3.0 |
| becker100 | reach5 | 8,433 | 51 | 3.4 | 3.0 |
| gaulke | off | 4,406 | 34 | 1.8 | 0.5 |
| gaulke | reach4 | 4,394 | 31 | 10.3 | 3.1 |
| gaulke | reach5 | 4,385 | 29 | 16.5 | 3.3 |
| marine127 | off | 7,289 | 43 | 8.8 | 3.3 |
| marine127 | reach4 | 7,286 | 42 | 9.2 | 3.3 |
| marine127 | reach5 | 7,289 | 41 | 9.2 | 3.3 |

Why these three cases:

- **becker100** — best ratio: 3.0 mm of exposed thread for three trims
- **gaulke** — worst ratio: 14.7 mm for five trims — look hardest here
- **marine127** — nearly free: 0.4 mm for two trims, and the plan's yardstick

## Question D — does the rescued walk read better than the trim it saves?

Look between the letters, where `off` has a trim and `reach4` /
`reach5` have a short run instead.

1. **Can you see the run at all** on the fabric, at arm's length? At
   reading distance?
2. **Against the trim it replaced:** which looks worse — the run, or
   the tails and tie-off bump where the trim was?
3. **Does the worst case change the answer?** gaulke pays the most
   exposed thread; becker the least. If gaulke reads badly and becker
   reads fine, the flag wants a per-design rule, not one number.
4. **4 vs 5 mm:** is there any visible difference? The measurement
   found no knee, so if the eye finds none either, the cheaper radius
   wins by default.

What each answer flips:

- The run is invisible or clearly better than the trim → flip ON at
  the radius that reads the same, and re-price the sheet's other
  trim questions against it.
- The run shows and the trim does not → the flag stays OFF for good,
  and the refused-walk bucket is closed: the census already showed
  three quarters of it is a web that does not reach, where a trim is
  correct.
- It depends on the design → the flag needs a gate (density,
  letter spacing, or thread colour against fabric), and that gate is
  the next measurement.

**What the numbers already say, before cloth.** The worst single exposed leg
is 3.0-3.3 mm in every ON arm, on all three cases — that is the length the
eye has to judge, and it does not grow with the radius. becker reads
identically at 4 and 5 mm (51 trims, 3.4 mm exposed either way), so on that
case the cheaper radius is free; gaulke is where the two radii differ most
(31 trims at 10.3 mm against 29 at 16.5).

*(files written by `digitizer/tools/sewout_walk_reach.py`, pinned by
`tests/test_sewout_walk_reach.py`; every file read back through pystitch and
required to match the plan's stitch count before it is offered to the
machine. Numbers and the full census: scope-history 2026-09-20; the flag is
`cfg.satin_walk_cursor_reach_mm`.)*
