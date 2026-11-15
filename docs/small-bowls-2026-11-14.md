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

Seven configs, OFF -> ON with the flag alone, one digitize at a time. The base is main 5a647125, before tonight's #1533 flips. The metrics cover lettering shapes under 5 mm that have a counter: satin cover (`columns.satin_cover`), bowls under 0.85 cover, and satin needles more than 0.05 mm inside a counter.

| design | size | small letters with a counter | open bowls (cover < 0.85) OFF -> ON | mean satin cover OFF -> ON | stitches | trims | satin needles in counters |
|---|---|---|---|---|---|---|---|
| bukit_hat_85.1 | hat_front 85.1 | 6 | 3 -> 0 | 0.801 -> 0.98 | 2271 -> 2362 | 8 -> 8 | 2 -> 4 |
| bukit_lc_80.4 | left_chest 80.4 | 6 | 2 -> 0 | 0.825 -> 0.979 | 1974 -> 2054 | 9 -> 9 | 7 -> 5 |
| jakarta_lc_80 | left_chest 80.0 | 5 | 0 -> 0 | 0.996 -> 0.997 | 3166 -> 3174 | 22 -> 22 | 0 -> 0 |
| proseal_hat | hat_front 85.9 | 7 | 0 -> 0 | 0.972 -> 0.974 | 5707 -> 5709 | 36 -> 36 | 1 -> 1 |
| fremont_hat (byte-identical) | hat_front 92.6 | 8 | 8 -> 8 | 0.0 -> 0.0 | 16106 -> 16106 | 28 -> 28 | 0 -> 0 |
| mfab_hat (byte-identical) | hat_front 104.9 | 0 | 0 -> 0 | None -> None | 20954 -> 20954 | 26 -> 26 | 0 -> 0 |
| bukit_hat_113.5 | hat_front 113.5 | 3 | 0 -> 0 | 0.989 -> 0.996 | 4695 -> 4699 | 17 -> 17 | 0 -> 0 |

- **Bukit, the fault:**
  - Every open bowl closes at hat 85.1 and at Kent's LC 80.4. 85.1 reads "beyondcoal" ON.
  - At 80.4 the o's close, but coal's a reads closer to an o ("cool"): its stem barely shows. That is a separate fault, below.
  - At 113.5 (already read), the change is too small to see.
- **No design moves for the worse:**
  - Jakarta, ProSeal and Bukit 113.5 move by a handful of stitches, invisible on the zoomed sheets.
  - Fremont hat and MFab hat are byte-identical. Fremont's small lettered shapes are not Column-lane satin, so its cover reads 0; MFab has none under 5 mm with a counter.
- **Counter needles** go 2 -> 4 and 7 -> 5 on Bukit. On the 85.1 lane read none sits deeper than 0.07 mm; the 80.4 needles were not read one by one. The counters stay open on both sheets.
- **Trims are unchanged everywhere.**

## Not done

- The e's cut. The fold judge still chooses curved pieces over the ring cut
  it also tried. The flag closes the bowl but does not change which cut is
  chosen.
- **coal's a at LC 80.4** sews a closed bowl ON (it read as a "z" OFF), but
  its right stem barely shows, so the word reads closer to "cool". The stem
  is a separate fault; the flag does not reach it.
- A walk or underlay line still crosses some counters (the o's centre line
  on the sheets), with the flag OFF and ON alike. That is the lane's
  connector rule, not this build.
