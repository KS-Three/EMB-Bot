# Letter-fault reader replication: sat, still no verdict (2026-11-12, scored 2026-11-13)

**Verdict, as registered: no verdict.** Kent sat the nine-item kit on
2026-11-13 (record: [`defect-marks-2026-11-12/SITTING.md`](defect-marks-2026-11-12/SITTING.md)).
The frozen pin rule selects letter pins on **2 of the 9 items**, one pin
each. The pass line needs at least 5 items, so it cannot be applied. The
letter-fault reader (PR #1389) has not been replicated, and it has not been
refuted either.

## Result of the sitting (2026-11-13)

Scored by `score_replication.py` exactly as registered: frozen reader, 3 mm,
`chance_area` null, item bootstrap. The reader ran from tree `ea13a362`; its
worker re-digitized each job and checked that the stitches matched.

| item | selected pin (his note) | reader flags | hit at 3 mm | chance |
|---|---|---|---|---|
| `C_lt_bukit_asam` | "No spacing between the rings" | 8 (3 bay closed, 4 join, 1 counter lost) | 1/1 (nearest flag 2.42 mm) | 0.195 |
| `C_lt_n_sync` | "#1-#2 have perpendicular thread angles which shouldn't be adjacent or touching eachother on an "S"" | 0 | 0/1 | 0.0 |

Pooled over the 2 pins: hit rate 0.50 against a chance rate of 0.098. The
chance-corrected figure is +0.446, CI95 [0.00, 0.81]. 2b (bare inherited pins
dropped) is the same, because no bare pins were selected. Leave-one-out:
dropping bukit_asam gives [0.00, 0.00], dropping n_sync gives [0.81, 0.81].
With two items the interval says almost nothing, which is why the pass line
does not look at it.

**This differs from what the pre-registration expected.** It planned for about
5 of the 9 items to carry letter pins, since 6 of 11 logos did on 11-10. Only
2 did. Kent left 60 pins across 8 items (one item was "Nothing wrong"), but
almost none of them are about closure, the faults this reader reads (a counter
filled, letters joined, a bay closed). They are about:

- **Flat or straight letter edges:** I, Z, E.
- **Smooth curves:** the 14 bare pins on `and_pizza`, and "all of the letters
  are jagged" on `dot_music`.
- **Letters out of line:** on `jakarta` and `bukit_asam`.
- **Stitch type or angle changing inside one shape.**

Of the two selected pins, the `n_sync` note is about thread angles meeting
on an "S", and the rule admits it on the word "touching". That is the rule as
frozen, so it stays in.

The power table below assumed 5 or more items with pins. The sitting reached
none of its rows, so a lack of verdict is the likely outcome for any
closure-only reader on these logos at 80 mm. That is not evidence about the
reader itself.

## Before the sitting (2026-11-12)

The letter-fault reader (PR #1389) cannot be replicated on pins Kent has
already made: outside the six logos it was fit on, the frozen pin rule finds
letter pins on ONE item. A nine-item sitting was built for that reason.

The pre-registration came first, in its own commit (`ea13a362`):
[`defect-marks-2026-11-12/letter-reader-replication-preregistration.md`](defect-marks-2026-11-12/letter-reader-replication-preregistration.md).
It freezes the reader (detection AST digest `b5211fb9…`, equal at `79fa7646`
and `bdae1860`; that is the Python 3.13+ `ast.dump` text, which CI's 3.12
dumps as `95841189…`, so the test pins both plus a version-stable
`ast.unparse` digest `035bf7dd…`), the pin rule, the 3 mm radius, the stitched-area chance null,
the item list and the pass line. Every figure here is an instrument reading,
not a quality claim (ROADMAP gate 4).

## What held-out data exists

| sitting | items | letter pins under the frozen rule | status |
|---|---|---|---|
| 2026-11-10 | 15 (11 pro logos, 4 photos) | 14 on 6 logos | the fit set: chose the rule, scored the first result |
| 2026-11-11 | 21 Commons logo rows | 30 on 1 item (`C_silhouette_logo`: one note + 29 bare pins it covers) | scored 11-11, no verdict |

No other `marks.json` exists in the repo or the primary checkout. Two 11-11
notes are about a letter but the frozen rule does not admit them
(`C_comic_halftone` "The N isn't an "N"", `C_outline_lineart_logo` "Hard to
decipher the dot on the "I""); they are not added, since picking pins after
the rule is what pre-registration forbids.

**Power of what exists:** one item. The harness bootstraps over items, so
one item gives a zero-width interval and the pass line (at least 5 items with
pins) cannot be applied. The 30 pins are one judgement.

## Power of a new sitting

Simulated from the first result's six items (table in the pre-registration):

| items carrying letter pins | P(shown) at the first effect | at half of it | with no effect | CI width |
|---|---|---|---|---|
| 5 | 0.51 | 0.28 | 0.04 | 0.58 |
| 9 | 0.76 | 0.43 | 0.04 | 0.44 |
| 12 | 0.88 | 0.55 | 0.04 | 0.39 |

The first result is likely an overestimate (its pins chose its rule), so the
half-effect column is the realistic one. Nine lettering logos is the whole
committed pool that has never been pinned. On the first sitting 6 of 11 logos
carried a letter pin under the rule; if 5 of the 9 do, a real half-size
effect is found about a quarter of the time, so a "not shown" from this
sitting is mostly a statement about power. A false "shown" runs 4-6%.

## The prepared sitting

Built after the pre-registration commit, by
[`defect-marks-2026-11-12/build_kit.py`](defect-marks-2026-11-12/build_kit.py),
on tree `ea13a362` (main `bdae1860` plus that commit, which touches docs
only): kit `defect-marks-1112`, `kit_sha256` `f824c55c20f7…`
([`kit.json`](defect-marks-2026-11-12/kit.json) committed; no pictures). All
nine digitized, none skipped, one process at a time, 18-244 s each. Each at
the Studio's request, 80 mm on left_chest:

| item | size |
|---|---|
| `C_lt_bukit_asam` | 80.4 x 21.3 mm |
| `C_lt_but_seriously` | 80.2 x 30.9 mm |
| `C_lt_hed_p_e` | 81.1 x 19.0 mm |
| `C_lt_jakarta` | 80.9 x 34.3 mm |
| `C_lt_k_line` | 80.5 x 16.9 mm |
| `C_lt_ahora` | 80.6 x 20.9 mm |
| `C_lt_dot_music` | 80.4 x 12.6 mm |
| `C_lt_n_sync` | 80.3 x 15.9 mm |
| `C_lt_and_pizza` | 79.6 x 27.9 mm |

On Kent's machine the kit, its art copies and the capture are in the primary
checkout's gitignored `digitizer/eye_pairs_out/defect-marks-1112/`,
`eye_pairs_out/defect-marks-1112-art/` and `corpus_runs/lettering-1112-ea13a362/`
(copied from the lane and checked file-by-file). Serve with launch.json
`defect-marks-1112` (port 8738); the page was checked to load all nine. The
page never receives the yardstick's reading or any reader's flags, and the
reader has not been run on any of the nine.

## What waited on Kent (sat 2026-11-13; see the result above)

A 9-item sitting on `defect-marks-1112` (launch.json, port 8738), the same
page as the last two. At the 11-11 pace (21 items in 1 h 46 min, about
5 minutes each) it takes about 45 minutes. It decides whether the letter
reader's 11-11 "shown" replicates on art neither the rule nor the reader has
seen: if it does, it is the first fault reader with a replicated result and
can be proposed as a preflight finding; if not, it joins the edge and in-fill
readers as a measured negative.

Scoring afterwards (by a session, not Kent), from a checkout at the kit's
tree: the reader on every item with a selected pin, then
`docs/defect-marks-2026-11-12/score_replication.py`, which applies the pass
line exactly as registered.
