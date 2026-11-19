# To a T hat: the A of "To A T" and the C of "LLC" (2026-11-19)

**Verdict: no flag built. The counter and width faults are thread-width limits (ROADMAP gate 1). The two
real faults left are column END faces (A's left foot, C's top terminal), the same family as the Tires
stroke end, and they need the professional's end-face numbers, which this session could not get.**

Reproduced on main (tree `e4b0428`, `text_cluster_mixed_caps` ON) with
`tools.pro_pair.digitize('testdata/art/logo_toat_machine.png', 89.5, 'hat_front')`; plan read from
`result.regions` (meta) and a 40 px/mm render. Art only, no professional's file. Pictures (art | ours):
`docs/renders/toat-a-c-2026-11-19/`. Scorecard source: `docs/prime-grader/scorecard-2026-11-18.md`,
`L_toat_machine_hat` at (47.5, 18.0) and (68.0, 47.0) mm.

## What the reader saw, after the 11-18 flip

| fault (reader) | measured | class |
|---|---|---|
| A: "crossbar and counter have filled in" | The A counter is OPEN and the crossbar is present. Counter 2.26 mm2 in the art (1.25 mm wide), 1.11 mm2 sewn (1.03 mm wide). The A's polygon keeps its interior ring (24.0 mm2, stroke 1.5 mm, `text_cluster_mixed_caps`). | counter half-closed by the pull: **thread-width limit (gate 1)**; "filled in" is a **grader misread** of a 1 mm slit at print size |
| A: "apex is square" | The art's apex is a flat top too, and ours is flat. | **grader misread** |
| A: "ragged leg bottom" | The left foot ends in a stair: two overlapping bars at the base, one sticking out left of the leg (`A_left_foot_ours.png`). The art's foot is one slanted cut. | **real**: column end face, same family as `docs/tires-script-counters-2026-11-18.md` "stroke ends" |
| C: "crowded against the L" | Stems are 1.23 mm in the art and 2.0-2.1 mm sewn (+0.8 mm = the 0.4 mm/side pull). L-to-C gap 3.8 mm in the art, 2.9 mm sewn at y 50.5. The C's stroke is 1.0 mm. | **thread-width limit (gate 1)** |
| C: "broken into several stitch blocks, notch at the top terminal" | One polygon (12.7 mm2, no hole), `lettering_group`. The stem's horizontal crosses meet a separate fan-shaped terminal column at the corner and stack over each other, leaving a notch on the outside (`C_top_terminal_ours.png`). `lettering_columns_corner_fold` (ON) folds L corners, not a stem turning into a terminal arc. | **real**: a column end/join |
| C: "ragged lower hook" | Same construction at the bottom of the C; not separately measured. | real, same family |

At print size the C is 5 mm tall and the A 7.6 mm; the two real faults are small (the reader's own grades
are noticeable and nitpick).

## Why nothing was built

A fix for A's foot and C's terminal is an end face, the thing three earlier attempts on Tires did not find
(`.claude/memory/round-dot-ring-2026-11-18.md`). Without the professional's end-face numbers a fourth
guess is the same experiment. The pro's TIRES and To a T files live in the gitignored `scratch_kent/`, not
in a cloud checkout (`tools/pro_parity/prep_all.py` names them); the director was told on 2026-11-19. The
counter and the width are the pull constant: row 16 of `docs/sew-out-list-2026-11-18.md`.
