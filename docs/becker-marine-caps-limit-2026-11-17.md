# Becker MARINE: the cap over each letter is the art, not our fault (2026-11-17)

Prime grader pin (`L_becker_hat_large`, 102 x 65 mm hat, scorecard
`docs/prime-grader/scorecard-2026-11-17.md`): "the top of the M is a separate cap
of vertical stitches over a horizontally stitched stem with a visible seam;
this repeats on the A, R, N and E tops." **Verdict: not a fault to fix. The
professional sews the same cap.** No engine change; nothing built.

Picture: `docs/renders/becker-marine-caps-2026-11-17/marine_original_ours_pro.png`
(original | ours at main `796123f2` | the professional's file, same frame).

## What the eye sees

- **The art.** Every MARINE letter has a sheared slab across its top quarter,
  a parallelogram leaning left with a small pointed notch on the left edge at
  22-30% of cap height. It is the font, not a rendering style.
- **The professional's file.** The slab sews as its own piece of near-vertical
  stitches over horizontal stems on M, A, I, N and E (and the R's bowl). The
  seam where it meets the stem shows. The earlier measurement agrees:
  `docs/big-letter-construction-2026-10-24.md` ("a sheared slab across the
  top of every letter that he sews as its own piece"; his top-20% crosses run
  at 99-118 deg, parallel to the slab's edge).
- **Ours.** Same construction: a vertical-stitch cap over horizontal stems. So
  the grader's pin reads a limit of how a block letter this size is threaded,
  one the professional shares.

## Where ours really is worse (a different mechanism, left alone)

Not the cap, and not what this lane was asked to fix, but visible in the same
picture: the M's left diagonal is a thin sliver with its own angle, the R's bowl
is several wedges, and the E's lower half is a fan from one point at about
(93, 59) mm where his is a plain bottom arm. The three OFF lettering flags
(`lettering_columns_apex_cut`, `_cover_handback`, `_connectors_buried`) plus
`satin_junction_square` were each run on this design: **0 pixels differ** from
the default, so none of them reaches these. A fix would need a new
mechanism at the junction of stem, diagonal and arm; it is a separate item.

Measured 2026-11-17, `tools.prime_grader capture` on main `796123f2`, 16,249
stitches in every arm.
