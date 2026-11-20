## Summary

<!-- What changed and why. -->

## Flip PRs (a default goes OFF -> ON, or a value changes)

Attach the output of `python -m tools.flip_guard OUT_DIR field=value --evidence <design> ...`
(run from `digitizer/`; summary table first, then the OFF | ON sheets). Look at every design
flagged OUTSIDE EVIDENCE, every trims rise of 2 or more, and every bare-thread rise.

Never raise a quality ceiling (bare thread, chaining, coverage) to pass a flip. If a guard goes
red, the flip regressed something: fix the flip or narrow it.
