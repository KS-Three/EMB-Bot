# merge_chroma_guard: every run it moves (2026-11-17)

Original | flag OFF | flag ON, same size and frame.

**Moved: 2 of 35 runs**, both pictured. The 9 prime-grader pro jobs at their
own sizes (1 moved; the other 8 stitch-identical) and the 26
`corpus_scorecard.FIXTURES` at 80 mm, left chest, Studio request (1 moved;
the other 25 identical by md5 of the stitches).

| picture | stitches OFF -> ON | read by eye |
|---|---|---|
| `precision_drone_hat_pair.png` (pro job, 62.6 mm hat) | 14,423 -> 15,433 | **Better.** The sky's upper-right quadrant sews blue and the water is a full blue band behind the trees, as in the art. |
| `drone_render_80mm_pair.png` | 18,610 -> 21,091 | **Better.** Blue sky and water where OFF had none; the ground reads black instead of a dark slate. |

Cost: 7% and 13% more stitches on the two Drone runs. Limit: 35 runs is what
was measured; the rule runs on every photo-style and gradient design.

Kent, 2026-11-17, shown both pictures: "Flip ON (Recommended)".

## The flip was withdrawn the same day

The sweep above is at ONE config (the Studio request). A targeted run of the
suite with the flag ON then failed 8 tests, and they are not only pins of the
Drone:

- stage-2 goldens moved for `photo_subject_stub` and `enthusiast_logo`
  (`test_photo_lane_byte_identical`, `test_stage2_photo_segment`);
- blocking THREAD_MATCH_POOR findings rose 1 -> 3 on `logo_golden_tee` and
  3 -> 4 on `drone_render` (`test_thread_match_area_in_message`);
- `drone_render` gained a forbid-gap finding of 5.27 mm2 (`test_forbid_gap`);
- two more on `drone_render` (`test_duplicate_cone_layers`, the shard test).

None of that was in front of Kent, so "2 of 35" understated the flag's reach
and the default stays OFF. Before it is asked again: run the fixtures at the
configs those tests use, picture every mover, and explain each finding that
got worse.
