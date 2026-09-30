# The envelope's junction escapes — Becker's "void-filling" texture, measured and fixed (2026-09-30)

Kent's note on the envelope's labelled sitting (Becker at 100 mm, verdict
*after better*, `../../eye-pairs-2026-09-30/`): *"It improved on filling in
the empty space, but the lettering needs to be smooth and have flow to it,
these stitches look like they are just trying to fill a void."* His pick
after the resolution line: find out what the extended rails sew against
the symmetric stretch, and the texture lever.

Everything below is measured on the shipped engine (`main` at `d59ff556`,
`satin_rails_follow_edge="envelope"` ON since that night) with a trace hook
on `_rail_points` that reads every station's symmetric width and per-side
offset, then on the same tree with the rule. Numbers in `census.json`;
instrument `digitizer/tools/envelope_escapes.py`.

## What the extended rails were sewing

**Becker at 100 mm, the page's own render.** 70 satin strokes, 1,533 body
stations. The envelope extends 183 of them (11.9%), **159 on the six satin
letters of the top row** (M A R I N E — the bottom row sews as fill at this
size). Extension p50 0.67 mm, p90 2.37, max 3.73; 46 stretches, p50 3
stations long, 18 of them 1–2 stations; and the extended rail still sat a
median 0.67 mm short of the edge it reached for.

**The mechanism, read off the E's stem** (`becker100_E_rails_shipped.png`:
symmetric rails blue, envelope red, spines green). The stem's symmetric
half-width is 3.0–3.3 mm (a 6 mm stem) and its far side, toward the arms,
reads **7.4–9.6 mm at 30 of 44 stations**: the ray runs along an arm and
hits the arm's end 8.6 mm out. That escape lasts as long as the arm is
thick, about 13 stations at 100 mm, longer than
the width median (5) and the envelope's running-min window (7) put
together; and the corridor cap at the junction reads the merged footprint
(floor 3.66 mm → cap 6.05) and lets 2–2.8 mm of it through. The stem's
crosses then run into the arms, under and over the arms' own perpendicular
satin. That is the void-filling: thread laid on ground that was never bare.

**Where the thread landed** (20 px/mm raster, the six letters): the
envelope's new ground was 63.0 mm², **22% of it bare** under the symmetric
rails and **78% already sewn** by another stroke of the same letter; the
double-covered share of the letters rose 9.3 → 11.0% (True: 12.4%). The E
alone: 10.3 mm² of new ground, none of it bare.

**What it did to the texture** (final crosses whose nearest station the
envelope extended, against the same stations under the symmetric rails):
rail jitter over 0.15 mm at **31.5% of penetrations against 9.1%**, the
cross-length step p50 0.285 against 0.221 mm; and the letters' *unreached*
crosses roughened too, 8.3 → 20.0%, because the refinement fills the
notches at each stretch's ends with inserted stations. Cross angles were
untouched (p90 change under 2°): the flow Kent missed is the rails, not
the stitch direction.

**Nine logos, each at its own width.** 459 reached stations: **313 escapes
(68%)**, 146 genuine.

| logo | width | reached | escapes | genuine | stitches sym / envelope |
|---|---|---|---|---|---|
| becker | 100 | 183 | 113 | 70 | 8,827 / 9,563 |
| golden_tee | 80 | 130 | 75 | 55 | 8,573 / 8,613 |
| bridge | 80 | 85 | 70 | 15 | 16,085 / 16,157 |
| screenshot | 80 | 28 | 26 | 2 | 8,161 / 8,171 |
| tires | 80 | 14 | 13 | 1 | 2,646 / 2,646 |
| drone | 80 | 12 | 10 | 2 | 18,784 / 18,788 |
| gaulke | 80 | 6 | 5 | 1 | 4,305 / 4,307 |
| enthusiast | 80 | 1 | 1 | 0 | 2,474 / 2,474 |
| fremont | 92.5 | 0 | 0 | 0 | 20,012 / 20,012 |

## What separates an escape from a reach — and what does not

Every cap on the reach itself was screened on those 459 stations (kept
genuine / escapes let through): extension ≤ 1.0 mm **89% / 76%**; ≤ 1.5 mm
96% / 83%; offset ≤ 1.5× the symmetric width 60% / 50%; ≤ 1.3× 33% / 26%;
boundary distance at the end ≤ 0.5 mm 63% / 57%; ≤ 1.0 mm 81% / 80%. An
escape is not longer, not further from the edge, not a larger multiple of
the width than a genuine reach — golden_tee's escapes are short (p50 0.54
mm) and end near a boundary (0.19 mm). **Where the reach ENDS is the
only thing that separates them: inside another stroke's corridor, 89% /
5%** on the instrument's screen (nearest vertex, the sibling's symmetric
width at it); the shipped rule reads the sibling's median body width plus
the pull and realized 73% / 7%, below.

## The rule

`_in_sibling_ribbon` (`stage6_satin.py`, the envelope branch): a station
the envelope would extend is refused, and keeps the symmetric width, when
the extension's end lies within a sibling stroke's own half-width of that
stroke's spine. The siblings are the shape's other strokes (`satin_shape`
passes their spines) plus, inside a Goldman-joined stroke, the other
members (a stem's ray at a corner escapes along the foot exactly as at a
T). The half-width is the **median** of the width field along the
sibling's spine — its body — not the field's reading at the nearest point:
a sibling's spine starts at the junction node, where the field reads the
merged footprint (3.2 mm on a 5 mm stem meeting a 5 mm arm, 2.5 in the
body), and that radius round the node refused a genuine reach on the far
side of the very stem the sibling meets. `False` and `True` are
byte-identical; the envelope without siblings is byte-identical.

One subtlety the fixture test found: the far ray reaches four half-widths.
An arm longer than that gives no hit, the fallback puts the "edge" at the
nominal half-width, and there is no escape — Becker's arms are 9 mm long
against a 9.6 mm reach, which is why the E escaped and a 12.5 mm test arm
did not.

## After the rule

**Nine logos: 129 reached stations, 23 escapes, 106 genuine** — 93% of
the escapes gone, 73% of the genuine reaches kept. Stitches, symmetric /
envelope shipped / envelope with the rule: becker 8,827 / 9,563 / **8,932**;
golden_tee 8,573 / 8,613 / 8,581; bridge 16,085 / 16,157 / 16,085; the
other six within 2 of the symmetric count. The envelope now costs at most
1.2% of thread anywhere; on Becker it cost 8.3%.

**Becker at 100 mm.** Reached 78 stations (74 on the letters), extension
p90 1.03 mm (was 2.37), 23 stretches (8 of them 1–2 stations), the rail
now a median 0.33 mm short of the edge it reached for (was 0.67). New
ground 15.2 mm², **87% of it bare before**; double coverage 9.35% against
the symmetric 9.32%. Texture: rail jitter over 0.15 mm at the reached
stations 28.4% (the same stations symmetric: 9.3%) — the genuine reaches
that remain still roughen the rail where they sit; the letters' unreached
crosses are back to 11.3% (symmetric 8.3%, shipped 20.0%); all crosses
12.2% (symmetric 10.4, shipped 15.7, True 19.5).

**Becker at 80 mm** (the envelope test's fixture, tip caps off, False /
envelope / True): bare 10.222 / **9.550** / 7.235% (shipped envelope 9.484
— the reach is kept), satin wobble std 0.0914 / 0.0994 / 0.1281, stitches
5,691 / **5,697** / 6,079 (shipped 5,750): six stitches over the symmetric
rails where the shipped envelope spent 59, because the escapes were the
longest crosses on the design and carried the split points.

**MARINE at 80.2 mm** (the trims test): every arm cheaper — rail comp OFF
2,010 → 1,968, ON 2,461 → 2,372, the ratio 1.224 → 1.205; with tip caps
off 1,820 → 1,783 against 2,119 → 2,103, 1.164 → 1.179, a thousandth
under that pair's 1.18 ceiling, which moved to 1.19. The grown polygon's
rays escape at more stations than the rails' (275 against 238 under the
shipped envelope), so the OFF arm loses more.

## For Kent's eye

Each strip is the same window three ways: **symmetric rails (before
09-30) | envelope as shipped | envelope with the rule**, artwork outline in
red, thread renders at 20 px/mm.

- `becker100_E_Sf1c25fcd.jpg` — the E: the shipped middle tile lays the
  stem's horizontal crosses through the middle arm and along the top one;
  with the rule the arms keep their own satin.
- `becker100_R_Sa587cbf9.jpg` — the R: the bowl and the leg overlaid at a
  second angle in the shipped tile; gone with the rule.
- `becker100_A_S5a3cd301.jpg`, `becker100_M_Scc08b907.jpg` — the legs'
  crosses run into the diagonals in the shipped tile; not with the rule.
- `golden_tee80_T_Sa6d2719f.jpg` — the T whose keylines Kent preferred
  sewn over: **unchanged by the rule.** The yellow keyline is another
  shape, not a sibling stroke, so that reach was never an escape.
- `becker100_E_rails_shipped.png` — the diagnosis drawing: where the red
  envelope rails leave the blue symmetric ones and spike into the arms.

## What this does not fix

- **The genuine reaches are short and still read as teeth.** 8 of
  Becker's 23 remaining stretches are 1–2 stations (0.4–0.8 mm along the
  rail, stepping out by p50 0.37 mm), and the jitter share at reached
  stations is three times the symmetric rails'. A minimum stretch length
  or a ramp into the reach is the next lever, and it trades coverage for
  flow — Kent's call, not a measurement's.
- **Split satin flickers on the letters, under every rail mode.** At 100 mm
  the letters' columns straddle `SPLIT_SATIN_ABOVE_MM` (5.0): 71% of their
  crosses carry split points under the symmetric rails, 18 of 22 runs mix
  split and unsplit crosses, with 75 on/off transitions. The same "no
  flow" reading, and older than the envelope.
- **23 escapes remain** (Becker 15, golden_tee 6, bridge 1, drone 1):
  extensions that end outside every sibling's median ribbon yet on ground
  another stroke sews, where that stroke is wider than its median at the
  meeting.
