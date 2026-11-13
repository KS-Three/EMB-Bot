# Monarch orange stripe: not drift, a width mistake (2026-11-12)

[`starter-pack-weak-spots-2026-11-12.md`](starter-pack-weak-spots-2026-11-12.md) reported that re-digitizing the
monarch on main loses the lower butterfly's first orange stripe, and called it main's drift since the pack's
`ac3d77fa`. Kent held the monarch re-digitize on that claim ("Baseball only now", 2026-11-12). **The claim was
wrong.** Main did not change the monarch. The re-digitize ran at the wrong target width.

## What happened

The pack (PR #1382) digitized the monarch with `target_width_mm` **90.0**. The DST that comes out is 90.5 mm wide,
because the stitched outline sits slightly outside the traced art. The manifest records that 90.5. The 11-12
re-digitize took the manifest's 90.5 as the target, so it ran 0.56% larger, and at that size the stripe is lost.

## Evidence

All runs use the 1920 px Commons render whose sha256 the manifest records. "Orange" counts pixels drawn from the DST at
10 px/mm, each block in its own thread colour (`r > 200, 90 < g < 170, b < 90`). The two `borders_last: false` rows
are drawn from the run's design rather than from the Studio's starter thread list, because that setting can change the
block order. On the rows both methods can draw, they agree to within 15 px.

| Code | Target mm | Setting | Stitches | Trims (DST) | Size mm | Orange px |
|---|---|---|---|---|---|---|
| shipped file (11-10) | — | — | 16,819 | 86 | 90.5 × 85.7 | 111,617 |
| `ac3d77fa` | 90.0 | defaults | 16,819 | 86 | 90.5 × 85.7 | 111,617 |
| `ac3d77fa` | 90.5 | defaults | 16,129 | 85 | 91.0 × 86.1 | 104,058 |
| main `8bd56ff7` | 90.0 | defaults | 16,819 | 86 | 90.5 × 85.7 | 111,617 |
| main `8bd56ff7` | 90.0 | `borders_last: false` | 16,743 | 67 | 90.5 × 85.7 | 111,268 |
| main `7ad81351` (the 11-12 run) | 90.5 | `borders_last: false` | 16,035 | 63 | 91.0 × 86.1 | 103,952 |

- **`ac3d77fa` at 90.0 is the shipped file.** Every byte after the 512-byte DST header matches. The header differs in
  one field: the pack's label is `monarch` and this run's is `EMBBOT`.
- **`ac3d77fa` at 90.5 loses the stripe** exactly as main did on 11-12. So the loss comes from the size, not from a
  commit.
- **Main at 90.0 writes the same DST bytes as `ac3d77fa`** (sha256 `858758ef…`), so nothing on main has changed the
  monarch. No commit to name, no flag, no default. Nothing else in the pack or in the tripwire set needs checking for
  this loss, because there is no change for them to share.
- **The candidate Kent ruled for,** `borders_last: false` at the right width, keeps the stripe (−0.3% orange) and
  takes the trims from 86 to 67. The hops that land on finished work drop from 68 to 51. Preflight goes from B 76 to
  B 88, and the service read-back verifies. The 86 → 63 reported on 11-12 came from the wrong width.
  One catch: the white and orange blocks swap sew order, so `starterThreads.js` must be regenerated with the DST.
- **Trims** above are the `tools/trim_classes` count, which is what the manifest holds.

## The other two "before" runs had the same mistake

The baseball and turtle "before" runs in the weak-spots doc also took the manifest's file width as the target:

- baseball: 75.5 instead of 75.0;
- turtle: 92.5 instead of 92.0.

That doc put their small stitch and trim differences down to drift. At the pack's targets, `ac3d77fa` reproduces
both shipped files, byte for byte past the DST header:
- baseball at 75.0 mm: 20,812 stitches, 75.5 × 74.1 mm;
- turtle at 92.0 mm: 17,398 stitches, 92.5 × 61.8 mm.

The diagnoses do not change, because each cause shows at both sizes:
- the baseball's radial ramp bands;
- the turtle's RAG merge;
- the monarch's `borders_last` hops.

The shipped flat baseball (PR #1417) is a new design made at 75.5 and checked from its own file, so it stands. It sews
0.8% wider than the 11-10 file.

## Size sensitivity

The stripe exists at 90.0 and is gone at 90.5. A 0.5 mm change in requested width turning a whole orange cell black is
a fragility in its own right. The cell is a thin wedge where the black vein lines nearly meet, and at some sizes the
traced orange there falls under the minimum. This was not traced to a stage. It is recorded here because a customer
who resizes the monarch can hit it.

## Rule for the next re-digitize

Take the target width from the run that made the file, not from the manifest's `width_mm`. The manifest now records
`digitize_config` for re-digitized rows, but not the original target. Until it does, recover the target by matching
the shipped DST's bytes.
