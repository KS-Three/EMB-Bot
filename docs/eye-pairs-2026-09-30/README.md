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

**Ruling, given in chat right after (2026-09-30): flip the envelope ON.**
Shipped the same night: `satin_rails_follow_edge="envelope"` is the default
and `rail_envelope` left the arms table (`rails_follow_edge` stays, `True`
against it). The next work item he picked with it: bridge's satin border
that goes on and off, and its smooshed lettering.

**Follow-up on his becker note (2026-09-30, later that day):** the
"void-filling" was measured and is real — 78% of the envelope's new thread
on the letters lay on ground another stroke already sewed, because at a
junction the far ray runs along the meeting arm. The sibling rule refuses
those reaches; the strips and the census are in
`../renders/envelope-escapes-2026-09-30/`.

## Second sitting on the same URL — the dissolve after the fold fix (2026-09-30, Version 5)

Kent's pick after the bridge measurement: *fix the fold first, then flip*.
The fold's wrong turn — nine halo members folded into a detached black
cluster and came out as teal specks on bridge's ring (scope-history
2026-09-30; DOCTRINE "A fold's endpoint names a colour, not a place") — is
fixed on this branch, and the page was rebuilt at the same URL with one arm,
`phantom_dissolve` = `dissolve_phantom_blends=True`, shipped on the left and
the dissolve on the right, over the gradient lane's six logos. Four pairs:
bridge, gaulke, golden_tee, screenshot; drone and fremont are identical to
the stitch and not shown. tires (the photo lane, 2,646 → 2,643 stitches) is
in the table and not on the page: the arm is a gradient-lane flag and its
three stitches there are the palette re-read, not the fold.

The corpus under the arm (both sides through `digitize()` at each logo's own
width and garment, `max_colors=6`, on main after #559 and #563 with the
envelope ON; thread on white / on other ink from `tools/dropped_elements`'
colour fields), in `dissolve-corpus.json` with the page's caption:

| logo | lane | stitches | trims | jumps | regions | thread on white mm² | thread on other ink mm² |
|---|---|---|---|---|---|---|---|
| bridge | gradient | 16,179 → 11,385 | 101 → 43 | 32 → 17 | 80 → 20 | 179.3 → 105.8 | 599.3 → 600.6 |
| golden_tee | gradient | 8,659 → 8,554 | 45 → 47 | 4 | 39 | 343.1 → 341.9 | 337.4 → 337.6 |
| gaulke | gradient | 4,332 → 4,449 | 33 → 37 | 24 → 25 | 53 → 57 | 458.9 → 457.9 | 75.4 → 77.9 |
| screenshot | gradient | 8,171 → 8,170 | 73 → 76 | 45 → 43 | 158 | 645.0 | 227.1 → 227.0 |
| drone | gradient | identical |  |  |  |  |  |
| fremont | gradient | identical |  |  |  |  |  |
| becker | flat (not on the lane) | identical |  |  |  |  |  |
| enthusiast | flat (not on the lane) | identical |  |  |  |  |  |
| tires | photo | 2,646 → 2,643 | 8 | 0 | 6 | 179.4 → 176.0 | 40.5 → 40.3 |

**His verdicts on this arm from 09-28, BEFORE the fix** (`../eye-pairs-2026-09-28/kent-notes.json`):
bridge *after better*; gaulke, golden_tee, screenshot, tires *both bad*;
"did its job" can't tell on all five. Those documents are still in the
page's store under `phantom_dissolve__<fixture>` — the ids this page would
have taken, so they would have pre-filled the fold-fixed pairs and been
overwritten by his new clicks. This sitting is keyed
`phantom_dissolve__<fixture>__fold-fix` and its ruling
`phantom_dissolve__fold-fix` (the gallery's new `--sitting`, which the page
writes into every document it saves); the 09-28 record stays as it was.

### How it was built

```bash
cd digitizer
# two lanes, three logos each; every lane digitizes base + phantom_dissolve
.venv/bin/python -m tools.eye_pairs --render --out <laneA> --fixtures bridge,golden_tee,gaulke --arms phantom_dissolve
.venv/bin/python -m tools.eye_pairs --render --out <laneB> --fixtures screenshot,drone,fremont --arms phantom_dissolve
.venv/bin/python -m tools.eye_pairs.merge <out> <laneA> <laneB>
.venv/bin/python -m tools.eye_pairs_gallery --labelled --src <out> --out <out>/gallery \
    --tables ../docs/eye-pairs-2026-09-30/dissolve-corpus.json --sitting fold-fix
```

Then `<out>/gallery/index.html` and its `img/` republished to the artifact
above (12 images, 1.3 MB; Version 5). The envelope's seven pairs left the
page with this rebuild; their verdicts are the section above and the store.

### Kent's question

The flip. `dissolve_phantom_blends=False` is shipped — built 2026-09-04 for
this fixture, OFF since. With the fold fixed, does the dissolve read better
on the four logos it changes, and did it do the job on bridge's border that
goes on and off?

### Outcome

Pending his sitting. Read back with `ArtifactData`: `notes` under
`phantom_dissolve__<fixture>__fold-fix`, `rulings` under
`phantom_dissolve__fold-fix`.

## The evening sitting — the day's three lettering changes, before | after (2026-09-30)

Kent's pick after the teeth (#579): put the three changes the day made to
the lettering in front of his eye, on the page, with the thing the page
could not show until now. The same artifact URL, rebuilt under the tag
`evening-0930`:

- **Eight pairs against this morning's engine** — `ref_0930am`, `main` at
  1e5f8fe2 (the merge of #574): the envelope as it shipped that morning,
  before the sibling rule (#577), the split comb (#578) and the minimum
  stretch length (#579). BEFORE is that engine on the left, AFTER is today
  on the right. fremont is identical to the stitch and not shown; on
  enthusiast the stitch count is the same and the design is not.
- **Five dissolve pairs kept** — `phantom_dissolve` after the fold fix,
  still unjudged (bridge, gaulke, golden_tee, screenshot, tires; becker,
  enthusiast, fremont and drone identical). Their notes take the new tag;
  the 09-28 verdicts on the pre-fix dissolve stay under their own ids.
- **A needle-hole map beside every render**, the page's new *thread |
  needle holes* control at the top. `stitchviz.render_penetrations` draws
  the thread render faded to 35% over the cloth, on the same frame, with a
  dot at every stitch record and none at a jump; `--render` writes it as
  `renders/<fixture>__<arm>__holes.jpg` and the page swaps every view's
  source in place, so a zoom set on the thread stays on the holes. Built
  because the thread render cannot show a split column's mid-column
  penetration (`../renders/split-comb-2026-09-30/`): on the render the comb
  and the flicker look alike, on the map the comb is continuous staggered
  lines of holes down every wide column and the flicker is an interrupted
  one.
- **The locator marks becker (1 box) and tires (3).** On the other six ref
  pairs the change is under its 0.6 mm blur — a rail moved by under a
  millimetre, a comb that is texture — which is what the holes toggle is
  for. **The confound badge on tires' ref pair is right, and it matters**
  (found after the sitting, below): this checkout has the rembg venv, the
  ref engine's worktree does not, and tires is photo-class, so its BEFORE
  side ran without photo prep and its AFTER side with it.
- **The table** under the ref arm's head: `three-changes-corpus.json`,
  measured on the two engines that drew the pairs.

## The corpus, this morning's engine → today's

`tools/envelope_escapes.py` (a trace hook on `_rail_points` and a 20 px/mm
raster of the symmetric satin) and a per-leg split count, run in each
tree; stitches and trims are the same runs and agree with the page's
counts. *reached (escapes)*: the stations at which the envelope extends a
rail past the symmetric width, and how many of those extensions end on
ground another stroke of the same shape already sews. *changes
(lettering)*: how many times the split state changes between consecutive
legs along the satin runs, a cross and its return leg each split on their
own length.

| fixture | mm | stitches | trims | reached (escapes) | split on/off changes (lettering) |
|---|---|---|---|---|---|
| becker | 100 | 9,563 → 9,321 | 51 → 50 | 183 (113) → 72 (14) | 122 (59) → 37 (26) |
| golden_tee | 80 | 8,613 → 8,575 | 41 | 130 (75) → 36 (5) | 4 (0) |
| tires | 80 | 2,646 → 2,835 | 8 | 14 (13) → 1 (0) | 21 (0) → 5 (0) |
| enthusiast | 80 | 2,474 | 15 | 1 (1) → 0 (0) | 0 (0) |
| fremont | 92.5 patch | 20,012 | 56 | 0 (0) | 0 (0) |
| bridge | 80 | 16,157 → 16,175 | 101 | 85 (70) → 0 (0) | 20 (0) → 5 (0) |
| gaulke | 80 | 4,307 → 4,305 | 30 | 6 (5) → 0 (0) | 0 (0) |
| drone | 80 | 18,788 → 18,796 | 122 | 12 (10) → 0 (0) | 2 (2) |
| screenshot | 80 | 8,171 → 8,201 | 73 | 28 (26) → 1 (0) | 8 (0) → 3 (0) |
| **corpus** | | 90,731 → 90,694 | 496 | **459 (313) → 110 (19)** | **177 → 56** |

The tires row is measured with the photo-prep venv linked into the morning
engine's worktree (see *Measured after the sitting*); the first cut of
this table read tires from a worktree without it — 2,500 stitches, 22
(22) reached — which is the un-prepped lane, not the morning engine, and
put the corpus at 467 (322) and 173. Corrected, the before column is the
afternoon's escapes census to the station (459 / 313). What the three
changes did, in the corpus's own numbers: the envelope now reaches at a
quarter of the stations it did this morning and nineteen of those
extensions still land on a sibling's ground (Becker 14, golden_tee 5); the
split state changes a third as often along the runs; the stitch total
moves under a tenth of a percent, tires the exception (+7%: the comb on
its wide columns, 31 → 220 split legs).

## How it was built

```bash
cd digitizer
.venv/bin/python -m tools.eye_pairs --render --arms ref_0930am,phantom_dissolve --out <out>
.venv/bin/python -m tools.eye_pairs_gallery --labelled --src <out> --out <out>/gallery \
    --tables ../docs/eye-pairs-2026-09-30/three-changes-corpus.json --sitting evening-0930
```

One lane, the base and both arms on all nine logos (27 arm-runs, the ref
engine in a temp worktree), then `<out>/gallery/index.html` and its `img/`
republished to the artifact above (50 images, 7.5 MB; the previous
sittings' images removed from the version). The store was read before the
republish: no document newer than the export in `kent-notes.json`, no
rulings. The instrument runs are a scratch script over
`tools/envelope_escapes.census` in each tree; their output is the table.

## Kent's question

Two, on one page. On the eight ref pairs: does today's lettering read
better than this morning's — smoother, more flow, the void-filling gone —
and where the holes toggle shows the comb, does a continuous comb read
better than the flicker it replaced? On the five dissolve pairs: the flip
of `dissolve_phantom_blends`, still his to rule on. Verdicts pending at
the time of writing.

## Outcome — Kent's evening sitting (2026-09-30, all 13 judged)

**The eight ref pairs, this morning's engine | today** (a ref arm takes no
ruling; his note on its head: none):

| pair | verdict | note (verbatim) |
|---|---|---|
| becker | no difference | "the lettering does not flow, satin stitching is not smooth and structured pattern." |
| bridge | no difference | |
| drone | no difference | |
| enthusiast | no difference | |
| gaulke | both bad | |
| golden_tee | both bad | |
| screenshot | both bad | "dont use this image to judge" |
| tires | **before better** | "edges are nice, and clean the don't randomly break" |

4 no difference, 3 both bad, 1 before, 0 after. **The day's three changes
did not reach his eye.** The instruments moved (reached stations 467 → 110,
split changes 173 → 56) and the page reads *no difference* on the four
logos where they moved most; the one pair his eye separated went the
other way — tires, where the morning engine's edges are "nice and clean"
and today's "randomly break". Becker's note is the third time in a day
his eye has named the same thing about the lettering: the satin does not
flow, is not smooth, has no structured pattern — the sibling rule, the
comb and the teeth were all aimed at it and none of them changed the
verdict. screenshot's note says the fixture itself is not one to judge
digitizing by; that is a corpus note, recorded.

**The five dissolve pairs** (`dissolve_phantom_blends=True` after the fold
fix, shipped | dissolved):

| pair | verdict | did the flag do its job? | note (verbatim) |
|---|---|---|---|
| bridge | **after better** | yes | "random satin borders have been removed" |
| gaulke | **before better** | | "after ended up adding satin trim]" |
| golden_tee | **before better** | can't tell | |
| screenshot | both bad | | "disregard this photo to reference the digitizing judgement" |
| tires | no difference | can't tell | |

1 after, 2 before, 1 no difference, 1 both bad; no ruling on the page.
**The flag stays OFF.** It did on bridge exactly what it claims (the halo's
"random satin borders" gone), and on gaulke it added a satin trim that was
not there — a regression his eye caught and the corpus table had already
counted (regions 53 → 57, trims 33 → 37, stitches 4,305 → 4,441) without
reading it as one. His 09-28 verdicts on the pre-fix dissolve (bridge
after; gaulke, golden_tee, screenshot, tires both bad) stand beside these:
the fold fix moved gaulke, golden_tee and tires off *both bad*, and bridge
is the only logo where the dissolve is a gain both times.

The store, read back after he said he was done: `kent-notes.json`
(`third_sitting`), 13 notes and the ref arm's head note, no ruling document
with a value.

### What the verdicts send back to the bench

- **tires, "edges randomly break" today.** Measured below: the pair was
  the confound its badge named, and the edges his eye preferred are the
  un-prepped lane's. Today's engine and this morning's, both with photo
  prep, draw the same ragged tread edges; the day's changes add only the
  comb's penetrations.
- **gaulke, the dissolve's added satin trim.** Four regions and four trims
  appear under the flag; what they are is measured below.
- **becker, the lettering's flow.** Not one of the day's changes moved this
  verdict. The two levers not yet on the page are the pro's own Becker
  style — raw crosses to about 7 mm, no comb (`split_satin_above_mm=7.0`,
  8,292 stitches) — and the symmetric rails on the letters (the envelope
  OFF, whose reaches carry three times the symmetric rails' jitter). Both
  are one-line arms for a texture sitting, and gate 1 stands behind the
  first.

### Measured after the sitting

**tires: the pair compared lanes, not engines.** The primary checkout has
the rembg venv (`digitizer/rembg_isolated/venv`, gitignored); the ref
engine's worktree had none; tires is `photo_scene`. So the BEFORE side
skipped photo prep and the AFTER side ran it — the confound badge the
page put on that one pair. One engine per step of the day, all in
worktrees without the venv, draws clean tread edges at every step
(2,500 / 2,500 / 2,652 stitches) and the same commit as today's main in a
clean worktree reads 2,652 against this checkout's 2,835. With the venv
linked into a worktree of the morning engine: **2,646 → 2,835**, and the
locator's three boxes show the same ragged tread edges on both sides —
the notch where a tab meets its band, the jagged triangle, the messy
junction — with today's side adding the comb's mid-column penetrations
and nothing else (`tires_true_*.png` in the session scratch; the numbers
in the table above). What Kent preferred is the un-prepped lane's
segmentation of a cartoon tire: the rembg matte roughens its edges, and
his eye called that "edges randomly break". That is a finding about the
photo lane on tires (a logo classified `photo_scene` with
`detected_photographic=False`), not about the day's three changes, and it
is the one *before better* of the night.

**The yardstick now links the venv into every ref worktree**
(`refarm.link_photo_prep`; the row carries `photo_prep_env`, and the
page's confound badge reads it), so a future ref pair on a photo-class
fixture compares engines. The eight ref pairs on this page were rendered
before that; the seven non-photo fixtures are unaffected.

**gaulke: the dissolve's "satin trim" is four grey halo slivers.** Under
`dissolve_phantom_blends=True` gaulke gains four regions the shipped run
does not have — 0.19 to 0.28 mm² each, `rescued_small_shape`, thread 0108
(153, 153, 153), sewn as grey running stitches of 30 to 54 points (a
sliver along the letter's diagonal at (−6.0, −3.1)–(−2.5, 0.9) mm, two on a
bar at y ≈ 3.5, one at (−8.5, 0.9)); satin runs 91 → 95, trims 30 → 37,
stitches 4,305 → 4,441. The fold (`stage2_photo_segment.
dissolve_phantom_blends`) sends a halo member to the instance of its
endpoint colour that it borders, and these ended up as grey, disconnected
and rescued. Which branch of the fold made them — a member whose ramp was
grey-to-white, a member that touched no non-band label, or a band the
dissolve left standing — is the next measurement; the flag stays OFF
either way, on 2 before, 1 after.

**becker: nothing to add to the note.** The lettering's flow is the
open question the day did not answer; the two levers not yet on the page
are named above.

## The texture sitting — the lettering's two levers, before | after (2026-09-30, late)

Kent's pick after the evening verdicts: his becker note — *"the lettering
does not flow, satin stitching is not smooth and structured pattern"* —
had survived the day's three changes, and two levers had not yet been in
front of his eye. The same artifact URL, rebuilt under the tag
`texture-0930`, the needle-holes toggle on:

- **`split_7mm`** — `split_satin_above_mm=7.0`: raw satin crosses to about
  7 mm and no comb, the house style of the pro who sewed Becker's own files.
  Five pairs: becker (the letters: 85.8 → 35.1% of legs split, on/off
  changes 26 → 8, mid-column holes 114 → 59 per 100 legs, 9,321 → 8,281
  stitches), and tires, bridge, drone, screenshot where a non-lettering
  column crosses 5 mm; golden_tee, gaulke, fremont, enthusiast identical
  (no leg over the threshold).
- **`rails_symmetric`** — `satin_rails_follow_edge=False`: both rails at
  the nearer edge's distance, the envelope OFF. Three pairs: becker
  (9,321 → 9,248, the letters' legs 1,412 → 1,390), golden_tee (8,575 →
  8,573) and tires (the same count, a different design); six identical.
  After the sibling rule and the teeth, the envelope's reaches on the
  letters are few, and this is what they amount to.
- **The tables** under each arm's head: `texture-corpus.json`, one
  digitize per arm and logo on the engine that drew the pairs, on the
  satin runs of `text_candidate` shapes — legs, split share, on/off
  changes, holes per 100 legs, and two texture numbers described below.

## What the instruments say, and what they cannot

Two numbers were built for "smooth" and "flow": the share of consecutive
legs whose length differs by more than 0.15 mm (a rail step), and the
90th percentile of the turn between consecutive legs (the cross swinging).
On becker's letters they read 42.2% and 6.2° shipped, 42.2% and 6.2°
under the 7 mm split (the rails are the same rails), 40.4% and 6.6° under
the symmetric rails. **Then the same numbers on the pro's own Becker
files** (`testdata/reference/becker_*.dst`, 50 satin columns, 25,113 legs
by `tools/study_pro.classify`): 34.9% and 45.8°, and net of taper — the
second difference of leg length, roughness a straight taper does not
count — the pro is *rougher*: 54.4% of legs over 0.15 mm against our
45.2%, 35.3% over 0.30 mm against 21.0%, a median of 0.171 mm against
0.126. So **leg-length jitter is not what his eye calls smooth**, and
neither lever moves it more than four points. Whatever "flow" and
"structured pattern" are, they are not in this instrument; the page asks
him for the words.

## How it was built

```bash
cd digitizer
# the out dir seeded with the evening render's base (same engine, same config: a cache hit)
.venv/bin/python -m tools.eye_pairs --render --arms split_7mm,rails_symmetric --out <out>
.venv/bin/python -m tools.eye_pairs_gallery --labelled --src <out> --out <out>/gallery \
    --tables ../docs/eye-pairs-2026-09-30/texture-corpus.json --sitting texture-0930
```

Eighteen arm-runs (the base cached), 8 pairs, 10 identical and not shown,
33 images (5.8 MB) republished to the artifact above; the store read
before the republish (13 evening notes, one head note, nothing newer).
The table's instrument is a scratch script over `digitize()` with
`strip_ties` / `strip_splits` on each satin run; the pro numbers a second
one over `tools/study_pro`.

## Kent's question

On the five `split_7mm` pairs: does the pro's raw-cross style read as the
structure the comb lacks — and on the holes view, is a column with one
hole per rail station what "structured pattern" means? On the three
`rails_symmetric` pairs: do the letters read smoother without the reach,
at the coverage it costs? And in the note under either arm, his own words
for *flow*. The 7 mm threshold is a physical constant (a 6–7 mm float on
pique or a cap), so a verdict for it is a sew-out question under gate 1
before it is a flip. Verdicts pending at the time of writing.
