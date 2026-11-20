Moved: 0 of 44 runs; pictured: 0.

# `cfg.extra["dark_ink_bean_by_core"]`: flip-readiness evidence, 2026-11-20

**What it does.** This flag works with `dark_ink_bean_by_width` (ON), which
sews thin dark-ink strokes as bean runs. With the flag ON, a group of at least
`DARK_INK_CORE_MIN_STROKES` (24) strokes beans only when the median CORE width
of its strokes is under `DARK_INK_BEAN_MAX_CORE_MM` (1.0 mm, two minimum satin
crosses). The core width is the inscribed-circle diameter. Without the flag
the test uses the mean width, and the mean reads a serif letter by its serifs:
the Nevada seal's bold ring letters read 0.51 mm and sewed as one-line runs,
while their core reads 1.18 mm. Built OFF 2026-11-19 (`thin_ink.py`; memory
`logo-batch-9-2026-11-19`).

**The sweep.** `python -m tools.flag_sweep --flag extra.dark_ink_bean_by_core
--pictures` ran all 44 runs (18 tripwire placements and 26 corpus fixtures)
with 0 errors. Every run's stitch md5 is identical OFF and ON. The full table
is in `sweep.md`.

**No visible change**, so there is no before | after pair to show. The two
arms sew the same stitches byte for byte on every design in the sweep.

**Why nothing moved.** The memory note's 101-design batch moved 36 designs,
29 of them visibly. Its gains were ring text of 36 to 65 strokes on
government seals (Nevada, SEC, Florida, Court of Federal Claims,
Agriculture). Its losses were small groups (Hotel Fremont patch EAT | STAY |
PLAY to blobs, House, OPM, Energy Star, Fish & Wildlife), which the later
group-size floor was meant to exclude. None of those seal logos is in the
tripwire or corpus population. This sweep therefore shows that the flag is
inert on the designs the nightly checks guard. It does not show what the flag
does where it acts. Pictures of the seal designs would need that batch's
artwork, which is not committed here, so this run did not render it.
