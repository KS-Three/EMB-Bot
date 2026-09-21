# Stale diagnostics, two flips, and a bill that oscillates (2026-09-12/13)

A parallel session (nine agents, six merged PRs: `c37c4c6`, `d8b9973`,
`624deed`, `339de3a`, `82e1ae1`, `9c26222`). Read this before trusting a
diagnostic's output or quoting a flag's cost.

## The theme: documentation that had stopped being true, and was executable

The session was pointed at open defects and spent most of its value on
**instructions that were confidently wrong**. Three examples, because the shape
recurs:

- **`tools/crossval-stitch-formats.mjs`** told its reader that if the DST
  control shows `identity`, *"the harness is broken — not the codec
  vindicated."* Backwards since the 2026-09-08 axis fix, and the repair it
  points at is putting X back in the high nibble. A session following it would
  have un-fixed the codec.
- **`tools/spool_remedy.py --masks`** built its config on today's defaults,
  where the fix it diagnoses is already ON, so it compared a hypothetical raw
  footprint against regions the FIXED engine produced — and printed that under
  the label "stage 4 today".
- **MASTER_SCOPE defect 30** had the wrong count (6 of 26 / 34 shapes against a
  measured 3 of 26 / 24), the wrong direction ("on all six … no review layer at
  all" against 0 of 3) and the wrong mechanism (a re-snap; it is
  `enforce_color_cap`). It went stale at the 09-10 colour-bundle flip, which
  updated defects 15, 28 and 31 and left this one.

**The lesson that generalises: a diagnostic that builds its own config from
today's defaults stops being a diagnostic the moment the thing it diagnoses
ships.** Pin such a tool to `conftest.PRE_FLIP` and say so in its docstring.

## The edge cap's bill oscillates with design size

`cfg.edge_cap="bean"` shipped ON 2026-09-11 on `+5.9–26.3%, median +13.4%` —
**one width** (`pro_silhouette.py` defaults to 80 mm). Becker bills **+58.7% at
88 mm**, worse than the `drone_render` figure DOCTRINE calls a whisker off the
blanket-border negative, and a **0.3 mm larger design is 34% cheaper**.

Both first guesses were wrong and **only the render separated them**: the
silhouette is topologically identical at every width, and the cracks are worth
0.8% of the bill. The cause is the `omit` gate losing its input, because one
shape carrying ~94% of the design's linear cover flips satin/fill on
`_PROMOTE_EXPLAINED_MIN` (0.80) from a scalar **not monotone in design size**.

That threshold's own comment calls 0.80 "a plateau rather than a knife edge" —
but that plateau is about **corpus cell counts**, not stability **per shape
across size**. Becker refutes the latter. `classify_ribbon`'s stability is the
open project; Kent chose to cap the cost and leave it alone.

**Two instruments were lying about it.** `TRIM_HEAVY` is a rate, so the cap's
own stitches inflated the denominator that would have flagged its trims —
preflight caught the cheap case and missed both expensive ones. And the `edges`
field counted arcs-or-rings depending on whether the gate split a ring, so it
FELL (18 → 25 → 16) as the bill rose (+18% → +26% → +57%).

## Two flags flipped, both after a corpus pass Kent asked for first

- **`cfg.layer_palette_from_regions`** — mislabelled review layers 7 → 0 at
  `max_colors=12` and 13 → 0 at the Studio's shipped 6, with plans
  byte-identical 26/26 at both settings. **Accepted price: duplicate review
  rows** (0 → 13 at 6), because `merge_duplicate_cone_layers` folds on the
  DECLARED cone upstream of the election. No half-flip exists.
- **`cfg.keep_thin_strokes`** — drone's `AND DRONE` goes unsewn → sewn; Fremont
  103 → 76 trims at +8.5% stitches, C 64 → B 76. **Accepted price: gaulke's
  2 → 4 cones for ZERO recall change and becker's second cone on a one-cone
  design.**

**Every published figure for defect 30 had been taken at `max_colors=12`, the
engine default — at the Studio's shipped 6 the defect was five times larger.**
When a flag's cost depends on a setting, measure it at the setting customers
get, not the one the harness defaults to.

## The flip mechanics worth reusing

- **Attribute test fallout against a pre-change worktree rather than triaging
  it.** `keep_thin_strokes`' first full suite was 33 failed against an expected
  three; the same 33 node IDs run against a worktree at the pre-change commit
  returned 3 failed / 30 passed, proving all 30 belonged to the flip. One run,
  not thirty investigations.
- **`recapture_flat_lane_key.py`'s refusal is a feature.** It passed
  `logo_whitebg` and `logo_alpha` on pre-change-tree proof and correctly blocked
  `test_pushcomp`'s `towel` tuple, which this container does not reproduce. The
  value was recorded for whoever can write it. Never `--force`; `--control`
  alone only vouches for a target sharing its code path.
- **CI deselects exactly three node IDs.** Every other golden runs there, so a
  bad recapture does not fail locally — it fails for everyone else.
- **`conftest.PRE_FLIP` is the mechanism that keeps one flag out of another
  flag's measurement.** `keep_thin_strokes` joining it fixed twelve of the
  thirty moved tests in one line.

## Read the render before repeating the claim

`keep_thin_strokes` is sold on Kent's "whole elements missing". The render
narrows that to **one fixture**: drone. On Fremont and gaulke the taglines
**already read with the flag OFF**. And the scorecard cannot see the fixture
that improved — drone is F 0 / raw −68 both ways.

## Open leads this left

- **`classify_ribbon`'s stability** — the cause behind the oscillation. Moves
  the artwork and every golden; a project, not cleanup.
- **Manual mode does not reproduce auto's sew order** once a tiny region exists
  in an early layer (auto orders by palette layer, manual by area). The flip
  exposed it, did not create it. MASTER_SCOPE open item 16.
- **`EDGE_CAP_OVER_BUDGET` has no `WARNING_TEXT` entry** in
  `app/src/lib/digitizer.js`, so the panel ships the engine's own sentence.
- **`dissolve_phantom_blends` stays banked**, but bridge_bar's thin-stroke cost
  falls from +29 regions/+28 trims to +1/+1 with it on — new evidence on a
  ruling Kent made before anyone knew that. Named, not re-litigated.
