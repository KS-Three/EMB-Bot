# Letter-fault reader replication: no held-out data yet, sitting prepared (2026-11-12)

**Verdict: no verdict.** The letter-fault reader (PR #1389) cannot be
replicated on pins Kent has already made: outside the six logos it was fit on,
the frozen pin rule finds letter pins on ONE item. A nine-item sitting is built
and ready; it is the only thing that can decide the question.

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

## What waits on Kent

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
