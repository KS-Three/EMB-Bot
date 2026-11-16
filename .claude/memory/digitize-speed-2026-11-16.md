---
name: digitize-speed-2026-11-16
description: Kent's bar for digitize time (15-25 s understandable, over a minute not), where the time goes, the exact cuts taken 11-16, and the two levers left
metadata:
  type: project
---

**Kent, 2026-11-16:** "Why does it take so long to digitize an image? I could
understand 15-25 seconds, but over a minute is insane, noone will want to wait
that long." He then said "Yes, speed pass". The bar is his words; the reading
that 15-25 s is the target to plan against is mine.

**Where the time goes.** One core of Python and GEOS; seven of eight idle (only
OCR threads). CPU seconds equal wall seconds. No stage is the hog: the top three
check labels are 37-44% of a run. The Column lane re-sews a letter once per cut
the fold judge tries and once per walk `_edge_walk` tries. Nine hat jobs:
15-103 s on main `91e3fc42`, four over a minute.

**Taken (exact, plan md5 the same on nine jobs):** 592 -> 530 s total. Keyline
crosses no edge touches (`_cross_unobstructed`), a letter's rails pushed once
(`columns._RAILS_MEMO`), the knot count, rail samples, the pairing table, the
band reader as one array, the distinct-colour count, neck-split halos. Becker
54.5 -> 37.4 s; jobs with no lettering or keyline did not move.
Doc: `docs/speed-pass-2026-11-16.md`. Test: `tests/test_speed_exact_1116.py`.

**Left.** No exact cut over about 3 s. Two levers, both Kent's call:

- more cores: with `lettering_columns_judge_entry_free` the letter cut no longer
  depends on the needle's entry, so cuts can be computed ahead in a process pool
- fewer passes (a cheaper judge, a candidate cap): a quality trade

**Why:** he read over a minute as a reason customers leave.

**How to apply:** treat digitize seconds as a product number, not an engineering
nicety. A flag that adds seconds says so in its PR. Time trees back to back on
this laptop (one GEOS call read 3.25 and 4.27 s in the same hour; under 10% is
noise) and prove sameness by md5. Related: [[digitize-speed-2026-10-26]],
[[big-size-speed-2026-11-11]],
[[second-digitize-timing-2026-11-13]], [[launch-not-near-rulings-2026-11-12]].
