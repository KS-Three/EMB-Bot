# Word tagger: why the third glyph is missed at 50 mm (2026-10-13)

Measured negative. Tool: `digitizer/tools/word_tagger_trace.py` (replays
`words.detect_words` step by step; `tests/test_word_tagger_trace.py` pins
parity with the shipped tagger). `cfg.lettering_words` stays OFF and nothing in
`digitizer_core/` changed. No new flag.

Reproduce: `python -m tools.word_tagger_trace <fixture> --widths 50 65 80 100 --census --json out.json`
(add `--rescue-census` for the pair-rescue rules, `--summarize a.json b.json` to pool).

## What is "expected"

- becker, enthusiast, tires, bridge, drone, screenshot, fremont: the hand
  labels in `testdata/lettering_truth.json`, carried from the corpus width to
  each size by position (coordinates are millimetres and scale with width).
- golden_tee (unlabelled) and gaulke (its labels belong to an older build, ids
  not in this generation): the words the tagger itself reads at 100 mm. For
  these "expected" means "what the tagger reads at 100 mm", not ground truth.

## Refusals, pooled over 9 fixtures (glyphs expected but in no word)

| rule | 50 mm | 65 mm | 80 mm | 100 mm |
|---|---|---|---|---|
| nested (admission: box inside a larger candidate's box) | 18 | 16 | 5 | 1 |
| no_region (size's segmentation has no region there) | 21 | 0 | 0 | 0 |
| height_ratio (link) | 5 | 4 | 3 | 3 |
| aspect (admission) | 4 | 3 | 3 | 3 |
| other_word (tagged, but into another word than its line's) | 3 | 7 | 0 | 3 |
| small_component (linked to a partner, component under 3) | 2 | 4 | 4 | 2 |
| stroke_cv (admission) | 3 | 5 | 1 | 0 |
| ink (link) | 1 | 2 | 2 | 1 |
| stroke_ratio (link) | 0 | 2 | 1 | 1 |
| distance (link) | 0 | 0 | 0 | 1 |
| merged>ink / merged>stroke_ratio (glyph fused into a region the rule refused) | 1 | 1 | 0 | 0 |
| **glyphs missing / expected** | 58 / 190 | 44 / 190 | 19 / 190 | 15 / 190 |

At 50 mm per fixture: becker none; enthusiast no_region 14 (the whole small
second line is gone from the segmentation); gaulke nested 5; drone
height_ratio 1 + stroke_cv 1; tires aspect 2 + height_ratio 2 (the whole-word
script region, structural); bridge nested 12 + aspect 1; screenshot
height_ratio 1; fremont no_region 7 + other_word 3 + nested 1 + stroke_cv 1;
golden_tee below.

## Answer: there is no dominant LINK rule

- 39 of the 58 missing glyphs at 50 mm (nested 18, no_region 21) are lost
  UPSTREAM of linking: the 50 mm segmentation fuses or drops the regions
  (bridge 76 -> 36 regions, enthusiast 31 -> 14). No tagger threshold reaches
  a region that does not exist or sits inside a larger one.
- Of the link rules, `height_ratio` is the largest (5 at 50 mm) and its
  measured values are far from the 0.8 line: golden_tee 0.458, drone 0.559,
  screenshot 0.616-0.656, tires 0.168 (script). The nearest miss is 0.656.
- The early probe (golden_tee at 50 mm: 15 candidates -> 7 singletons + 4
  pairs) is real, but "third glyph" there is four DIFFERENT rules in two words:

| golden_tee 50 mm | glyph | rule | measured vs threshold |
|---|---|---|---|
| word0 (3) | S2579d9c1 | aspect (admission) | 2.251 vs 2.000, the box fused with a neighbour |
| word0 | S3a67f74c | merged into S60b96a29 | stroke_ratio 0.206 vs 0.500 (also ink) |
| word0 | S5ed3cb4c | height_ratio | 0.458 vs 0.800 |
| word1 (4) | S5960875d, S6beeddaf | small_component | a pair, 2 vs 3 |
| word1 | S8ae343e5 | stroke_cv (admission) | 0.620 vs 0.600 |
| word1 | Saa9fc5c9 | ink | 39.3 vs 20.0 (bevel layer colour) |

At 65 mm word0 is down to a pair plus a glyph merged into a region refused on
ink (46.2 vs 20.0); at 80 mm it forms and only the ink-refused glyph
(70.9 vs 20.0) of word1 is out.

## Census of rule changes (every fixture x 4 sizes = 36 cells)

"gained" = expected glyphs newly in a word; "new stray" = regions that are not
expected glyphs (and not `ignore`d) newly in a word, i.e. false joins by the
strict definition; "new cross-line" = new words spanning two expected lines;
"lines completed" = change in expected lines held whole by one word.
Stray is conservative where the carry lost a real letter, and for
golden_tee/gaulke it means "not in the 100 mm reference words".

| variant | gained | lost | new stray | new cross-line | lines completed | zero false joins |
|---|---|---|---|---|---|---|
| aspect_max=2.3 | 0 | 3 | 0 | 0 | -1 | yes |
| aspect_max=2.6 | 0 | 18 | 6 | 0 | -4 | NO |
| aspect_max=3.0 | 2 | 18 | 14 | 0 | -4 | NO |
| height_ratio=0.7 | 9 | 0 | 29 | 0 | +4 | NO |
| height_ratio=0.6 | 9 | 0 | 63 | 0 | +4 | NO |
| height_ratio=0.5 | 11 | 0 | 90 | 0 | +4 | NO |
| stroke_ratio=0.4 | 0 | 0 | 8 | 0 | 0 | NO |
| stroke_ratio=0.3 | 2 | 0 | 8 | 0 | 0 | NO |
| ink_de=30 | 1 | 0 | 27 | 0 | +1 | NO |
| ink_de=45 | 6 | 0 | 39 | 0 | +2 | NO |
| ink_de=80 | 8 | 0 | 42 | 0 | +3 | NO |
| prox_mult=3.5 | 0 | 1 | 30 | 0 | 0 | NO |
| prox_mult=4 | 0 | 1 | 36 | 0 | 0 | NO |
| prox_mult=5 | 7 | 1 | 69 | 0 | 0 | NO |
| cv_max=0.65 | 6 | 0 | 16 | 0 | 0 | NO |
| cv_max=0.7 | 6 | 28 | 15 | 0 | -2 | NO |
| cv_max=0.8 | 8 | 129 | 5 | 0 | -9 | NO |
| min_height_mm=0.8 | 0 | 0 | 7 | 0 | 0 | NO |
| min_height_mm=0.6 | 0 | 0 | 12 | 0 | 0 | NO |
| min_members=2 | 15 | 0 | 119 | 0 | 0 | NO |
| rescue:cv_max=0.65 | 3 | 0 | 15 | 0 | 0 | NO |
| rescue:cv_max=0.7 | 3 | 0 | 10 | 0 | 0 | NO |
| rescue:cv_max=0.8 | 3 | 0 | 3 | 0 | 0 | NO |
| rescue:ink_de=30 / 45 / 80 | 0 / 0 / 1 | 0 | 24 / 30 / 32 | 0 | 0 | NO |
| rescue:height_ratio=0.7 / 0.6 / 0.5 | 0 | 0 | 18 / 27 / 28 | 0 | 0 | NO |
| rescue:stroke_ratio=0.4 / 0.3 | 0 | 0 | 6 / 6 | 0 | 0 | NO |
| rescue:prox_mult=4 / 5 | 0 | 0 | 16 / 25 | 0 | 0 | NO |
| rescue:aspect_max=2.6 | 0 | 0 | 0 | 0 | 0 | yes |
| rescue:cv_max=0.7,ink_de=45 | 2 | 0 | 41 | 0 | 0 | NO |
| rescue: all five relaxed together | 4 | 0 | 97 | 0 | 0 | NO |

`rescue:` is the smallest-by-construction rule tried for "the third glyph": two
glyphs that already link under the shipped rules are a presumptive pair, and a
third that fails ONE shipped rule but passes the relaxed one against either of
them completes the word. A relaxed glyph never seeds a component and never
extends a word that already holds three (`pair_rescue`). It is the only form
that can join a third glyph without letting a loosened rule form words out of
non-letters alone, and it still leaks: the false joins are strict pairs of
non-letters (counters, dots, icon parts) that the min-3 rule was keeping out,
completed by a third.

## Proposal and why it is not built

The two zero-false-join rows gain nothing (`aspect_max=2.3` loses 3;
`rescue:aspect_max=2.6` gains 0). The cheapest real gain is `rescue:cv_max`
(+3 glyphs, all in golden_tee at 50 mm: S8ae343e5 at 0.620 plus the pair),
at 3 new false joins even at 0.8 (pairs of non-letters in drone and
screenshot). ROADMAP gates forbid flipping a tier without its instrument and
the false-join bar here is zero, so no flag is shipped.

What the data points at instead:

1. Fix the 50 mm segmentation before the tagger: 39 of 58 missing glyphs are
   `nested` (a larger candidate's box swallows the glyph) or `no_region`.
   `nested` is the tagger's own admission rule (`textcluster._drop_nested`) and
   is the one place a tagger change could help: 18 glyphs, mostly bridge (12)
   and gaulke (5). That is a separate, measurable change: drop the swallowing
   candidate rather than the swallowed ones when it fails the glyph tests, and
   census it the same way (`Rules` would need a nested-policy field).
2. `height_ratio` is a size-policy question (L3), not a threshold one: the
   nearest miss is 0.656 and the median is far under 0.8.

No agreement statistic is reported here: this is a refusal census, and kappa
with a CI lives in `tools/word_tagger_eval.py`.

## Follow-up: the `nested` drop at small print (2026-10-13, later)

This one is also a measured negative, with no flag. The trace tool now names
the host of every `nested` drop and its containment values (`nest_info`: box
area ratio, height ratio, share of the glyph on the host's ink, and share
inside the host's outline with holes filled). It also censuses five nesting
policies (`--nest-census`, plus `--variant nested=ring`). `digitizer_core/`
is unchanged.

The 18 `nested` refusals at 50 mm are three different things:

| fixture | glyphs | host | host h vs glyph h | box area | on host ink | in host outline | host aspect / CV |
|---|---|---|---|---|---|---|---|
| bridge | 12 (all of BAR & RESTAURANT) | Sc050577e, the wheel's badge disc | 49.40 vs 2.04-4.66 mm | x149-458 | 0.00 | 1.00 | 1.00 / 0.33 |
| gaulke | 4 ("word2") | S474b1932, the house | 6.16 vs 1.96 mm | x23.2-23.9 | 0.00 | 0.00 | 1.77 / 0.45 |
| gaulke | 1 (Sff465103) | S5c5f2b6f | 2.72 vs 1.74 mm | x2.8 | 0.00 | 1.00 | 0.97 / 0.13 |
| fremont | 1 (Se137a45a) | S7569cf1c | 3.82 vs 2.94 mm | x1.7 | 0.00 | 1.00 | 0.99 / 0.06 |

- bridge: once the design is 50 mm wide the badge is 49.4 mm tall. That is
  under `WORD_MAX_HEIGHT_MM` (60), so the badge passes every glyph screen and
  its box swallows the whole line sitting in its hole. At 65 mm the hosts are
  other shapes (S2cb6c9d0, 18.4 mm; S86f3627b, 40.3 mm), and the letters sit in
  their BOX beside their ink (in outline 0.00). At 80 mm the badge is over
  60 mm and is not a candidate.
- gaulke "word2" is the house icon's four WINDOW PANES (2x2, 1.96 x 1.43 mm,
  in the house's own ink). They count as "expected" only because gaulke has no
  labels for this generation and the 100 mm tagger reads the panes as a word.
  Here the `nested` drop is RIGHT and the 100 mm reference is wrong.
- The last two are single glyphs inside a small ring-like host.

Census (36 fixture x size cells; a false join is a non-letter newly in a word):

| policy | gained | lost | new stray | zero false joins |
|---|---|---|---|---|
| ring: a host does not swallow a linked word (3+) inside its outline | 8 | 0 | 8 | NO |
| frame: a host whose BOX holds a linked word swallows nothing | 28 | 0 | 19 | NO |
| outline: a host swallows only what is inside its outline | 20 | 0 | 21 | NO |
| frame+outline | 28 | 0 | 29 | NO |
| nest_max_h=5 / 8 (no host over K x the glyph's height) | 8 / 8 | 0 | 16 / 12 | NO |

- `ring`'s 8 gains are bridge's BAR & RESTAURANT at 50 mm. The other four
  letters there fail ink or small_component, as they do at 80 and 100 mm.
- `ring`'s 8 strays are two 2x2 icon grids at 100 mm, each inside a shape's
  hole: on drone, four 1.4-1.9 mm panes in the 19.3 mm body (S2af623d5); on
  the phone screenshot, four 1.2-1.4 mm squares in a 9.0 mm icon (S618732e4).
  Four panes link like a word of four, because `_split_lines` only cuts
  components of 6 or more.
- `frame`'s 28 gains include gaulke's 12 window panes (4 each at 50, 65 and
  80 mm), so its real gain is 16 letters.
- `frame`'s strays are the wheel's spokes at 50 mm (0.18-0.21 inside the
  badge outline) and pieces of a host's own ink at 80 mm (outline 0.00).

What would separate the bridge line from the icon grids is the word's SHAPE
(one row of 8 against a 2x2 block), not containment. A rule tweaked to clear
these two grids would be fitted to the same census that scores it, so it is
left for the L3 / size-policy work rather than built here.

`no_region` is not a tagger rule; it comes from stage 0 / regions. It accounts
for 21 of the 58 glyphs missing at 50 mm (36%), all of them at 50 mm
(enthusiast 14, fremont 7), and 0 at 65, 80 and 100 mm. ROADMAP gate 2: not
touched.
