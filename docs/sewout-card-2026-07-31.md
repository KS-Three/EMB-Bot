# Sew-Out Gate Card — 2026-07-31

**One hooping. Six questions. Print this page and take it to the machine.**

*(A seventh — block 7, FLOAT CLEARANCE — is drafted at the bottom but is
NOT in the built file. It is the one measurement `chain_links` waits on.
Read it before the next machine session; do not expect to sew it from the
current `.dst`.)*

File: `EMBBOT_SEWOUT_CARD.dst` (built by `digitizer/tools/sewout_card.py` +
`tools/sewout_bridge.mjs`, written by the browser encoder — the codec with sew
evidence on this machine). Design **66.0 mm wide x 96.0 mm tall**, **5,048
stitches**, **7 color blocks / 6 color changes**, ~32 trims (rebuilt
2026-09-03 with block 6 and `FILL_ROW_MM` 0.15; the 2026-07-31 build was
66.0 x 87.8 mm, 3,326 stitches, 5 blocks).

Fabric: the constants under test are tuned for the default preset
(pique knit). Sew on a polo blank or similar mid-weight knit, cutaway backing.
40 wt thread. Any colors — position identifies the blocks, color is a bonus.

## Before pressing start: the 30-second panel check

Load the file, cap driver OFF, rotation untouched, and read the panel
**before sewing**:

| Panel reading | Meaning |
|---|---|
| ~**66 x 88 mm**, preview upright like the diagram below | Machine reads EMB-Bot's convention — *surprising, report back* |
| ~**88 x 66 mm**, preview sideways | Transposition confirmed on hardware (expected). Hoop sideways or rotate 90 on the panel and note which way |
| Color count **6** | Machine honors EMB-Bot's color-change byte (0x43) |
| Color count **0** | Standard reading confirmed — the card will sew straight through with **no color stops**. Fine: run it all in one dark thread, blocks identified by position |

(Cross-check already done in software: pyembroidery, a standards reader,
decodes this exact file as 87.8 x 66.0 with 0 color changes — the known axis
dispute, `docs/dst-axis-verdict-2026-07-31.md`. Not a defect in the card.)

## The card, as EMB-Bot previews it (sew order top to bottom)

```
+--------------------------- 66 mm ---------------------------+
| 1 LOCK (red)                                                |
|   [=====A=====]      [=====B=====]      two 14 x 2.2 satin  |
|    tie 0.8 mm         tie 0.45 mm       bars, no underlay   |
|                                                             |
| 2 FILL (blue)         three 15 x 15 squares                 |
|   [ A ]    [ B ]    [ C ]                                   |
|   0.40     0.20     0.40 x2 passes,                         |
|   single   single   2nd offset 0.20                         |
|                                                             |
| 3 WIDE SATIN (green)  25 mm bars, current emitter           |
|   [====== 3 mm ======]                                      |
|   [====== 4 mm ======]     zigzag underlay auto             |
|   [====== 5 mm ======]     above 2.5 mm width               |
|                                                             |
| 4 TRAVEL (black)                                            |
|   ----straight A 2.5----      ~~~~ curve A 2.5 ~~~~         |
|   ----straight B 2.0----      ~~~~ curve B 2.0 ~~~~         |
|                                                             |
| 5 TEXT (purple)       cap heights, same baseline            |
|   SEW      OUT      EMB      inc                            |
|   4 mm     5 mm     6 mm     2.5 mm (run tier)              |
+-------------------------------------------------------------+
```

If the machine sewed it sideways, rotate this page 90 the same way.

---

## 1 — LOCK LENGTH (red, sews first)

Two identical naked satin bars; **only the lock stitch differs**. Thread is
cut before and after each bar, so every bar end carries a 3-leg tie.

- **A (left): `TIE_STITCH_MM 0.8`** — ours today.
- **B (right): `TIE_STITCH_MM 0.45`** — pro corpus median.

**Look at the four bar ends, then tug each bar's tail thread.** A good lock
holds under a firm tug and does not read as a lump or a dark knot at the end
of the column.

> **Decision: if B holds without a visible lump -> change `TIE_STITCH_MM` to
> 0.45 in `digitizer/digitizer_core/machine.py`. If B pulls out, 0.8 stands.
> If both hold and neither lumps, take 0.45 (less thread in the lock).**

## 2 — FILL DENSITY / INTERLEAVE (blue)

Three 15 x 15 mm tatami squares, rows horizontal, stitch length 3.0,
edge-lattice underlay under each (square C's second pass is fill only).

- **A: `FILL_ROW_MM 0.40`, single pass** — ours today.
- **B: `FILL_ROW_MM 0.20`, single pass** — brute density, ~2x stitches.
- **C: two 0.40 passes, second offset 0.20** — the corpus's suspected
  interleave; reads ~0.20 effective. (Offset verified in the file: measured
  0.20 exactly.)

**Hold each up to the light for coverage; pinch for stiffness; look at the
corners for puckering.** B and C should cover alike — the question is whether
C gets there softer, and whether A was already enough on fabric.

> **Decision: if A covers -> keep 0.40. If B covers but C is softer or
> flatter -> build the two-pass interleave into stage 6 (planned work, no
> constant). If B and C look the same -> `FILL_ROW_MM` to 0.20 is the cheap
> answer. Stiff/puckered B with good C = interleave confirmed as the pro
> trick.**

## 3 — WIDE SATIN (green)

Three 25 mm columns at **3 / 4 / 5 mm width**, today's emitter untouched
(zigzag underlay kicks in automatically above 2.5 mm — all three have it).
`SATIN_MAX_WIDTH_MM` is currently 5.0; these are the baseline eyes for the
split-satin lane running in parallel.

**Look for floating/snagging crosses (drag a fingernail across), gaps at the
edges, and fabric pull along the bar.**

> **Decision: widest bar that sews clean = the real `SATIN_MAX_WIDTH_MM`
> (in `digitizer/digitizer_core/machine.py`). If 5 floats but 4 is clean ->
> 4.0, and the split-satin lane takes everything wider. If even 5 is clean,
> 5.0 stands and split-satin is for wider-than-5 only.**

## 4 — TRAVEL / RUNNING LENGTH (black)

Running-stitch paths, thread trimmed between each: straights (left) and
S-curves (right).

- **A: 2.5 mm steps** (`TRAVEL_STITCH_MM`, ours) — top straight, top curve.
- **B: 2.0 mm steps** (corpus 2.02) — bottom straight, bottom curve.

**Judge the curves: faceting (chords visible as straight segments) and how
smoothly the line follows the S.** Straights should look identical — they are
the control.

> **Decision: if the B curve is visibly smoother -> `TRAVEL_STITCH_MM` to
> 2.0. If you cannot tell them apart at arm's length, 2.5 stands (fewer
> penetrations).**

## 5 — SMALL TEXT TIERS (purple, sews last)

Four words through the full pipeline, same baseline, Arial regular. What each
size routed to (nothing forced):

- **SEW — 4 mm cap** -> thin satin columns
- **OUT — 5 mm cap** -> satin
- **EMB — 6 mm cap** -> satin
- **inc — 2.5 mm cap** -> **run tier** (bean run on the outline — the rescue)

Probed while building: the rescue tier engages below ~3 mm cap at this
weight; 3.0 mm is the mixed boundary. So 4/5/6 judge the satin floor, and INC
shows what the rescue looks like on fabric.

**Read each word at arm's length. Then close up: are SEW's columns solid or
shredded? Is INC a crisp monoline or lint?**

> **Decision: smallest legible satin word = the satin floor; Studio warns
> below it. If SEW (4 mm) is shredded but INC is a clean monoline -> raise
> the run-tier threshold (`min_detail_mm` routing in stage 7) so lettering
> under ~4 mm rescues to run instead of satin. If INC reads as lint, the
> rescue floor (`RUN_MIN_LOOP_MM` / `RUN_MIN_AREA_MM2`) needs raising
> instead.**

---

## 6 — SEAM / UNDERLAP (orange then blue, sews last)

Four pairs of abutting 7.5 x 6 mm tatami fills along the bottom edge, rows
horizontal so they run ACROSS each seam — the case where pull draws the row
ends back and opens a line of fabric. The orange half of every pair sews
first and reaches under its blue partner by the pair's rung; the blue half
sews after, to its exact edge, exactly as stage 5 sequences two colours.

- **Pair 1 (left): 0 mm** — a butt joint, the failure the other reader
  named on the 2026-09-01 sew-out.
- **Pair 2: 0.25 mm** — `PipelineConfig.overlap_mm`, what ships (stage 5
  adds the fabric's pull on top: 0.55 mm on pique).
- **Pair 3: 0.5 mm.**
- **Pair 4 (right): 1.0 mm.**

**Hold each seam up to the light, then stretch the fabric gently along the
row direction. Which is the first pair that shows no fabric at the seam?
Then look at the orange side of pair 4 for a ridge or a colour step where
the tongue sits under the blue.**

> **Decision: the first pair with no line is the underlap; `overlap_mm`
> moves to it. If pair 2 already closes -> 0.25 stands. If pair 4 shows a
> ridge, the answer is between pairs 3 and 4 and a second card narrows it.
> `tools/seam_underlap.py` reads what any design actually carries against
> the number chosen.**

## 7 — FLOAT CLEARANCE / CHAINING (yellow, sews last) — **PROPOSED, NOT YET IN THE BUILT FILE**

**Status: a spec, not geometry.** `sewout_card.py` does not emit this block
yet, so the current `EMBBOT_SEWOUT_CARD.dst` has six. Adding it changes the
card's stitch count, extents and block count — the header figures above stay
correct only until it is built. Drafted 2026-09-13; clearances below are
proposed and want Kent's eye before anyone cuts thread.

**The question, and why it is the only one left.** `chain_links` routes a
needle-down connection between shapes instead of cutting it, and all three of
its structural preconditions closed in August (`c8ab7ad` 08-03, `11ceecc`
08-04, `f8e8968` 08-11 — the `PipelineConfig.chain_links` docstring carries
the full trail). Re-measured with chaining ON over four acceptance fixtures:
**chaining-added bare thread 0.00 mm on every one**, while the benchmark goes
**9.82 -> 4.06 trims/1k** and full_back **7.35 -> 4.73**. Against defect 4 —
we trim 3.1x the professional — that is the largest measured lever in the
codebase, and it is parked behind one line in that docstring:

> A sew-out that says at what clearance a needle-down float actually shows —
> `LINK_COVER_TOL_MM` is still a thread spec, not a measurement.

`LINK_COVER_TOL_MM = 0.2` is simply half of `COVERAGE_THREAD_W_MM` (0.40). It
asserts that a float within 0.2 mm of thread is invisible. Nothing has ever
checked that on fabric. The measured hairline gaps between fanned satin
crosses run to **0.127 mm inscribed radius / 0.121 mm beyond the thread
edge** and persist at any inset — so the tolerance sits barely above a gap the
geometry cannot avoid. Whether that is comfortable or reckless is a cloth
question, and only a cloth question: no reference implementation, format spec
or corpus can answer where a human eye catches a float.

Five cases, one colour throughout, no trims inside the block. Each is a pair
of 8 x 6 mm tatami patches with a needle-down float crossing between them —
the exact geometry chaining creates.

- **A: 0.2 mm gap** — `LINK_COVER_TOL_MM` itself. The case the constant
  claims is invisible.
- **B: 0.5 mm gap.**
- **C: 1.0 mm gap.**
- **D: 2.0 mm gap** — below every fabric's `trim_at_mm`, so today's preflight
  would pass it silently.
- **E: ride-on-top** — the float crosses the middle of one solid 10 x 6 mm
  patch instead of a gap. This is law 60's OTHER cover mechanism (a link
  riding on work its own colour already laid) and it has never been tested on
  fabric at all. The thread here is not hidden; the claim is that same-colour
  thread on same-colour thread does not read as a line.

**Hold the block up to the light at arm's length first and just look: does
any float read as a stray line? Then close up under good light, gap by gap.
Then drag a fingernail across each gap the way block 3 tests floating
crosses — a float that catches is one that will snag in wear even if it
hides.** For E, look across the patch at a low angle for a ridge.

> **Decision: the smallest gap that shows a line is the exposure
> `LINK_COVER_TOL_MM` must stay under. If A (0.2 mm) shows, the shipped
> tolerance is too generous — chaining stays OFF until the cover is
> tightened, and this card has earned its keep. If A and B are both clean,
> the tolerance has real headroom and `chain_links` can flip ON with the
> measurement behind it. If D is the first to show, set the tolerance
> between C and D and a second card narrows it. Independently: if E shows a
> ridge or a colour step, law 60's own-thread half is NOT free, and
> `_link_cover` needs a width or count floor on the already-laid cover
> rather than crediting any centreline. `tools/chain_probe.py` and
> `preflight._link_coverage` read what any design actually carries against
> whatever number this settles.**

**Build note for whoever adds it:** the float must be a genuine needle-down
transport segment, not a run-tier stitch path — `preflight._transport_and_content`
only counts a connection as transport when it crosses a shape boundary with
`jump` False, and its raster cell is `_LINK_CELL_MM = 0.1`, so a gap under
0.1 mm cannot be resolved by the software instrument either way.

## File verification (done in software, for the record)

- Browser round-trip (`tools/sewout_bridge.mjs`): 3,326 stitches encoded =
  3,326 decoded; 4 color changes; 66.0 x 87.8 mm extents both directions;
  preview rendered from the actual DST bytes and inspected.
- pyembroidery cross-read: 87.8 x 66.0 (axes swapped) and 0 color changes —
  expected transposition + 0x43 color byte, per the DST verdict memo. Left
  as-is deliberately; this card is also the hardware test of that dispute.
- Lock-bar tie legs measured in the emitted points: 0.800 / 0.450 mm.
- Interleave offset measured between square C's passes: 0.20 mm.

Regenerate: `PYTHONPATH=. .venv/Scripts/python tools/sewout_card.py` (from
`digitizer/`), then `node tools/sewout_bridge.mjs` (repo root). Outputs land
in `digitizer/debug_out/sewout/`.
