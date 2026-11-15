# Small bowls: a ring column keeps its thin crosses (2026-11-14)

The eye sweep's fault 5 (`digitizer/eye_pairs_out/eye-sweep-1114/REPORT.md`,
"Trace 3"): Bukit Asam's tagline "beyondcoal" sewed "b-y-n-d cual" at hat
85.1 mm and at Kent's 80.4 mm, and read at 113.5. Stages 4 and 5 kept every
bowl. Stage 6 lost about 40% of each round letter.

## Which step opens the ring

The Column lane, on the lane's own input for the small o (`Se3d3c24a`, 2.4 mm
wide, counter 1.6 mm²), one number per step:

| step | what the o has after it |
|---|---|
| the cut (`outline_cut.letter_columns`, `small_bold`) | one RING column round the counter, 21 crosses of 0.47-0.63 mm: the ring is whole |
| text lean | no change (a ring is not a straight column) |
| rail inset (0.11 mm a side) and `small_bold`'s pull (0.15 x W = 0.08 mm) | crosses 0.33-0.49 mm on the thin top and bottom; the inner rail cannot push into the counter (`_push_rails` holds it to the counter floor) |
| the cross floor (`SATIN_MIN_CROSS_MM` 0.5) in `column_runs` | **9 of 21 crosses dropped**; 12 kept, on the thick sides |
| `thin_floor` (`small_bold`) | does nothing: it widens a column's thin crosses only when fewer than 3 remain |

Satin cover of the o: 1.00 at the cut, **0.70 sewn**. A ring has no ends, so
every dropped cross is a gap in the bowl. The o sewed as two brackets ("u"),
and the a's bowl the same way.

The ablation agrees: with `small_bold` off, or with pull 0, the o sews at
cover 1.00. Turning off text lean, `fold_cuts`, `corner_fold`,
`inside_stagger` or `square_ends` changes nothing. It is not a min-length
prune, not the hole keep-out, and not the spine.

**The e is a second path to the same drop.** The fold judge picks a cut that
splits its bowl into curved columns rather than one ring. Each of those
columns then drops its thin crosses: 10 of them, cover 0.66.

## The build: `cfg.extra["lettering_columns_ring_floor"]` (built OFF)

The flag acts under `thin_floor` (a letter under 5 mm) when a column is a
bowl's wall:
- a RING column;
- or a column whose piece runs along one of the letter's counters for at
  least a stroke width (the e's curved pieces).

On such a column the crosses under the floor are WIDENED to it about their
own middles (`_floor_crosses`, `thin_floor`'s own construction) instead of
dropped.
- **A ring column:** every cross.
- **An open wall piece:** its two end crosses still drop, as `thin_floor`
  already ruled (a fan's converging tip, widened, crosses itself).

**What it does not change:**
- The floor stays 0.5 mm and the pull stays as it is (gate 1).
- A letter with no counter is untouched.
- So is a letter over 5 mm.

**The counter stays open.** A cross widened about its middle reaches up to
0.07 mm past the counter's edge on this tagline. The e's eye had one needle
at 0.066 mm with the flag OFF already. The tagline's counters are about 1 mm
across. A counter under a needle width is not a counter by the time it gets
here: `letter_columns` drops holes under 0.05 W² as trace.

**The sewn plan** (Bukit hat 85.1, the six small letters with a counter,
satin cover = `columns.satin_cover`):

| letter | satin cover OFF -> ON |
|---|---|
| o (yond) | 0.70 -> 1.00 |
| o (coal) | 0.69 -> 1.00 |
| a | 0.85 -> 0.98 |
| e | 0.66 -> 0.91 |
| d | 0.93 -> 0.99 |
| b | 0.98 -> 0.99 |

## Corpus

PENDING

## Not done

- The e's cut. The fold judge still chooses curved pieces over the ring cut
  it also tried. The flag closes the bowl but does not change which cut is
  chosen.
