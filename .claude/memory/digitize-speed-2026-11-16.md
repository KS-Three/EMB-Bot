---
name: digitize-speed-2026-11-16
description: Kent's bar for digitize time (15-25 s understandable, over a minute not); the over-a-minute numbers were a laptop slowed to 1.4 GHz, idle it is 6-38 s; exact cuts taken 11-16; more cores measured 7%, not built
metadata:
  type: project
---

**Kent, 2026-11-16:** "Why does it take so long to digitize an image? I could
understand 15-25 seconds, but over a minute is insane, noone will want to wait
that long." He then said "Yes, speed pass", and after it picked "More cores".
The bar is his words; the reading that 15-25 s is the target to plan against
is mine.

**The trap that cost half a day: the laptop's clock.** The first table (nine
hat jobs 15-103 s, four over a minute) was timed while a full test suite and
other sessions held the clock at 1.4 GHz. Idle, one core runs at 3.7 GHz and
the same code is 2.7x faster: nine jobs 6-38 s, none over a minute, four over
25 s (MFab 28, Fremont 31, Drone 36, Golden Tee 38). Becker, same code: 13.0 s
idle, 19.5 s with seven other cores busy two minutes, 37.4 s during the suite.
Kent's laptop usually has sessions running, so over a minute is what he sees.
A customer's machine is not measured.

**Where the time goes.** One core of Python and GEOS (only OCR threads). No
stage is the hog. Three of the four jobs over 25 s spend half their time in
generation, before any stitch is planned.

**Taken (exact, plan md5 the same on nine jobs), #1604:** 229 -> 197 s idle.
Keyline crosses no edge touches, a letter's rails pushed once, the knot count,
rail samples, the pairing table, the band reader, the distinct-colour count,
neck-split halos. Doc: `docs/speed-pass-2026-11-16.md`.

**More cores: measured, not built.** The letter cut is 2.3 of Becker's 13 s
and 6.3 of MFab's 28 s, and one letter is 1.4 / 4.5 s of that, so a pool saves
at most 0.9 / 1.8 s (7%). It also needs `lettering_columns_judge_entry_free`,
which #1603 left OFF. Fewer passes (a cheaper judge, a candidate cap) is a
quality trade, Kent's call.

**Why:** he read over a minute as a reason customers leave.

**How to apply:** before quoting digitize seconds, read
`% Processor Performance` (about 185 idle on this laptop; 70 means 1.4 GHz)
and stop other suites first. Seconds from a loaded laptop are not the
product's number. A flag that adds seconds says so in its PR. Prove sameness
by md5. Related: [[digitize-speed-2026-10-26]], [[big-size-speed-2026-11-11]],
[[second-digitize-timing-2026-11-13]], [[launch-not-near-rulings-2026-11-12]].
