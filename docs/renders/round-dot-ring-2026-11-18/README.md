# round_dot_ring (built OFF): the Tires i dot, flag OFF vs ON

Prime grader pin on `tires_hat_3d` (44.5, 18.0 mm): the i's dot is faceted, with flat spots top and bottom
and a jutting last stitch. Pictures are our renders and the committed Tires art only (no professional's file).

- `tires_dot_closeup.png`: ORIGINAL | BEFORE (flag OFF) | AFTER (ON), 30 px/mm.
- `tires_whole_before_after.png`: the whole wordmark, before above after.

**Moved: 1 of 35 runs; pictured: 1 of 1.** The 9 committed pro jobs at their own size and the 26
`corpus_scorecard.FIXTURES` at the Studio request (80 mm, left_chest) were run flag OFF vs ON, md5 of
`design["stitches"]`: only `tires_hat_3d` changes. The other 34 are byte-identical, including
`logo_script_tires.png` at 80 mm (its dot is under 4 mm there). Nothing is worse by eye.

**What changed in the plan (read from `plan.iter_runs()`, not the picture).** The dot (`S91cf86bf`)
keeps its tatami fill (145 -> 141 points) and gains a 111-point `border` ring (the pro's 1.5 mm band
width) plus one travel. Sew order moves: the T's bar (`S667dbd3b`) now sews last instead of second, its
satin points unchanged (955) but its run chain re-linked; the big word (`S396ab4ae`) is 4 satin points
more and 7 travel points fewer. Whole design 4554 -> 4660 stitches, trims 7 -> 7, jumps 7 -> 7.

**Tests with the flag forced ON (default flipped locally, not committed):** 874 tests across the
border-by-size family, edge cap, prediction-matches-emitter, flag ledger, pushcomp, chaining, tripwire,
pro_baseline, corpus_scorecard, word_legibility, lettering and the rest of the files that mention Tires
or the size ring: all pass (4 skips, environmental).

**Not cured here:** the i's entry-stroke end at (21.5, 37.0). Its polygon end is within 0.25 mm of a true
circle (rms 0.08 mm) and the thread already covers all of the art there; the flat slant is the last
column cross. Three attempts (parallel cap crosses, crosses square to the end's axis, a circle-fit
polygon cap) gave no change, a small gap, and a worse straight cut; all reverted.

Limits: the ring is the pro's layout habit (29% of 4-6 mm fills at the census), a preview call, and
whether a 1.5 mm ring on a 5.7 mm dot holds on cloth is a sew-out question (ROADMAP gate 1).
