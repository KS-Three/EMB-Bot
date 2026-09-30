# Eye pairs, 2026-09-30 — the envelope beside the corpus

Kent's pick after PR #563 (*the envelope on the eye-pairs page*). The labelled
page that decided `satin_rail_comp` — `https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp` —
rebuilt at the same URL with ONE arm, `rail_envelope` =
`satin_rails_follow_edge="envelope"`, against today's shipped base (rail comp
ON, the junction tuck, the seams closed: `main` at 08c46a54 plus #563), and
the corpus table under the arm's head, so his eye and the instruments sit on
one page. The 77 pairs of the 2026-09-28 sitting are no longer on the page;
their verdicts stay in its store and in `../eye-pairs-2026-09-28/kent-notes.json`
(re-read 2026-09-30 before the republish: 111 docs, none newer than the export,
no rulings).

## What is on the page

- **Seven pairs** — becker, bridge, drone, gaulke, golden_tee, screenshot,
  tires — BEFORE (symmetric rails, shipped) on the left, AFTER (the envelope)
  on the right, the change locator's boxes on both.
- **Two identical to the stitch and not shown:** enthusiast and fremont. The
  arm head says so; the envelope found no side short by 0.3 mm over seven
  stations on either.
- **The locator marks three:** becker (3 boxes), bridge (1), golden_tee (3).
  On drone, gaulke, screenshot and tires the design differs but the change is
  under the locator's 0.6 mm blur — under a third of a square millimetre of
  new thread on each (the table's last column). A pair with no box is a pair
  the envelope barely touched.
- **The table** under the head: `rail-envelope-corpus.json`, the gallery's
  `--tables` file, measured on the engine that drew the pairs.

## The corpus, symmetric → envelope (rail comp ON both sides)

| fixture | mm | stitches | trims | bare satin % | satin wobble std mm | unsewn outline mm | overshoot | new thread mm² (on ink / on white) |
|---|---|---|---|---|---|---|---|---|
| marine80 | 80.2 | 2,093 → 2,119 | 21 | 7.03 → 6.28 | 0.137 → 0.137 | 20.8 → 19.0 | 0.093 → 0.095 | — |
| becker | 100 | 8,297 → 8,900 | 48 → 49 | 8.14 → 7.35 | 0.099 → 0.109 | 46.3 → 28.0 | 0.016 → 0.015 | 22.9 (18.6 / 4.3) |
| tires | 80 | 2,515 | 7 | 4.55 → 4.52 | 0.083 → 0.084 | 3.2 → 2.8 | 0.078 | 0.2 (0.2 / 0.0) |
| enthusiast | 80 | 2,392 | 15 | 6.98 | 0.096 | 4.3 | 0.257 | 0.0 |
| fremont | 92.5 patch | 19,887 | 55 | 3.98 | 0.030 | 0.0 | 0.000 | 0.0 |
| bridge | 80 | 15,384 → 15,432 | 98 | 5.15 → 5.05 | 0.095 → 0.100 | 1.5 | 0.004 | 0.3 (0.2 / 0.1) |
| golden_tee | 80 | 7,966 → 8,072 | 47 → 46 | 10.35 → 7.20 | 0.070 → 0.075 | 7.3 → 3.3 | 0.215 → 0.231 | 45.3 (14.7 / 30.6) |
| gaulke | 80 | 4,189 | 32 | 6.89 → 6.86 | 0.077 → 0.077 | 0.0 | 0.047 | 0.2 (0.2 / 0.0) |
| drone | 80 | 18,540 | 123 | 4.88 → 4.86 | 0.074 → 0.073 | 4.3 | 0.048 | 0.1 (0.0 / 0.1) |
| screenshot | 80 | 7,885 | 71 | 8.97 → 8.96 | 0.063 → 0.063 | 0.8 | 0.762 | 0.2 (0.0 / 0.2) |

One figure where the two modes agree. `bare satin %` is the satin-only bare
instrument (`tools/rail_edge.bare_area`); wobble std and unsewn outline are
`tools/edge_wobble`; overshoot is `tools/dropped_elements`' `overshoot_frac`.
The last column classifies the thread the envelope adds by what the artwork
shows under it (`tools/dropped_elements`' colour fields at the instrument's
own registration): ink, of the right colour or another, or white. `thermal`
is drone's artwork byte for byte and is not repeated. MARINE is the suite's
fixture, not a page logo; its designs were not kept, so its last cell is
empty. Corpus trims 640 → 641 (becker's one).

## What golden_tee's numbers mean

The two fixtures with the defect carry the change, and they read differently:

- **becker** gains on every instrument: bare satin 8.14 → 7.35, unsewn
  outline 46 → 28 mm, artfid 88.9 → 89.2, lost elements 53 → 47, at +7%
  stitches and a tenth more rail roughness. Of the 22.9 mm² of new thread,
  17.0 is ink of the right colour and 4.3 is the edge halo.
- **golden_tee** reads two ways. Bare satin 10.35 → 7.20 and unsewn outline
  7.3 → 3.3 mm say coverage; artfid 77.4 → 76.8, lost elements 69 → 76 and
  overshoot 0.215 → 0.231 say the opposite. The thread classes settle it:
  **30.6 of the 45.3 mm² of new thread lands on the 3D lettering's white
  keylines** (30.2 within 0.5 mm of ink, 0.4 on open ground), 10.9 on ink of
  the right colour, 3.8 on another colour. Those keylines are sub-detail gaps
  (about 0.2 mm at 80 mm, against a 1.5 mm `min_detail_mm`) that the on-rails
  polygon spans; the symmetric width, taking the nearer side, never reached
  that far edge, and the envelope does. The satin-only instrument counts the
  same thread as its polygon covered; `dropped_elements` counts filled
  knockouts. *A bare-satin gain is not a coverage gain until the artwork
  under the new thread is read* — the page carries both readings so Kent's
  eye can say which one the cloth agrees with.

Everything else moves by 0.3 mm² or less — the envelope's design (a where
and a how-far), and the reason the page will read *no difference* on most
of its pairs.

## How it was built

```bash
cd digitizer
# three lanes, three logos each; every lane digitizes base + rail_envelope
.venv/bin/python -m tools.eye_pairs --render --out <lane> --fixtures becker,tires,enthusiast --arms rail_envelope
.venv/bin/python -m tools.eye_pairs.merge <out> <lane1> <lane2> <lane3>
.venv/bin/python -m tools.eye_pairs_gallery --labelled --src <out> --out <out>/gallery \
    --tables ../docs/eye-pairs-2026-09-30/rail-envelope-corpus.json
```

Then `<out>/gallery/index.html` and its `img/` republished to the artifact
above (21 images, 2.9 MB). The corpus columns are a scratch script's output
(symmetric against envelope through `digitize()` at each logo's own width and
garment, `max_colors=6`); the thread classes another's, over the lanes' design
files. Both are in `rail-envelope-corpus.json`.

## Kent's question

The flip. `satin_rails_follow_edge=False` is shipped; `True` was parked for
cloth on 2026-09-03; `"envelope"` has been OFF since #563 built it. Whether
the far rail's reach reads right is the sew-out question `True` was parked on;
the page is the eye's half of it, the table the instruments'.

## Outcome — Kent's sitting, 2026-09-30 (all seven judged, no ruling)

| pair | verdict | flag did its job? | note (verbatim) |
|---|---|---|---|
| becker | **after better** | can't tell | "It improved on filling in the empty space, but the lettering needs to be smooth and have flow to it, these stitches look like they are just trying to fill a void." |
| bridge | both bad | can't tell | "The defect it circled is nowhere close to what needs to be worked on here. The lettering on bridge is smooshed together and the satin border is jumpy, its on off on off etc." |
| drone | no difference | can't tell | |
| gaulke | both bad | can't tell | |
| golden_tee | **after better** | **yes** | "But satin rails typically are an accent point. so make sure whatever it's putting rails on is a significant feature that requires accenting or some type of "pop" to it." |
| screenshot | both bad | can't tell | |
| tires | no difference | can't tell | |

2 after, 0 before, 2 no difference, 3 both bad; the store: `kent-notes.json`.
The two *after* verdicts are the two fixtures with the defect, and one thing
they settle: **on golden_tee his eye preferred the keylines sewn over.** The
instrument's seven "filled knockouts" (the table's last column) are gaps the
eye does not want to see bare at 80 mm, so that column reads against the
eye there; becker's *after* came with a caveat that is not the envelope's
gain but its texture — the reached stretches read as void-filling rather
than flowing satin. The three *both bad* are the logos bad under every
setting since 09-18 (gaulke, screenshot) plus bridge, whose real defects he
named: lettering smooshed together and a satin border that goes on and off.
The flip was not ruled on the page.
