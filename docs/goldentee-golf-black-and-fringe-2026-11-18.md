# Golden Tee GOLF: black over the gold, the grey fringe, the missing TM (2026-11-18)

Prime-grader job `L_goldentee_hat` (Bad, `ruins`): "black outline stitches pile over the
yellow/orange fills so the O counter and the L and F are barely readable; a grey shadow fringe
is sewn under the word that the art has only as a soft blur; the TM is missing."
Reproduced on main at 74.9 mm, hat_front, the Studio request. All three are REAL in the stitches
(read from the plan, not only the picture). Two get a flag (built OFF); the TM is a thread limit.

## 1. The black is sewn LAST, over the gold (flag `cap_merged_layer_home`)

The art's GOLF has a dark teal extrusion along the letters' lower-left edge. Stage 2 quantises
it as its own ink (spool 3344, quantize layer 6, the LAST layer). The colour cap (max 6) folds
it onto black and stamps `color_cap_merged_from`, but leaves `meta["layer"]` at 6. Black's spool
is declared by layer 1, so Golden Tee sews TWO black blocks: block 1 (layer 1, before any
colour) and block 6 (the teal's, after white, grey, gold, pumpkin and burnt orange).

The teal bands in block 6 (GOLF region, plan mm):

| shape | art width (2A/P) | sewn cross, median / p90 |
|---|---|---|
| Sf655cc83 (G) | 0.47 mm | 1.25 / 1.60 mm |
| S7d03ec7e (G/O) | 0.64 | 1.27 / 1.70 |
| S57307533 (O) | 0.41 | 1.02 / 1.34 |
| Sb6e5a319 (L, F) | 0.33 | 1.02 / 1.31 |
| Sc8434164 / Scfa8e58b (F) | 0.53 / 0.65 | 0.69 / 1.57 |

So the black sews 0.5 to 0.8 mm wider than the art's band. That excess is the satin cross floor
plus pull compensation (`stitch_width_pull_mm` 0.4): a physical constant, ROADMAP gate 1, NOT
touched. What is NOT a constant is the ORDER: because the band sews last, its excess lands on top
of the gold it borders and caps it. Sewn at its spool's layer, stage 5 plans against the order
actually sewn, the gold covers the excess, and the black shows at the width the art has.
`rehome_cap_merged_regions` is `rehome_resnapped_regions`' rule (earliest layer that DECLARES
the new cone; never a step region) keyed on the cap's own stamp.

## 2. The grey fringe is a quantised blur (flag `shadow_to_page`)

The art has a soft drop shadow under GOLF, blurred over about 1.3 mm. Stage 2's quantiser puts
its mid-greys into Fieldstone (0124, rgb 204,204,185), one 87 mm2 region, `S463dcb15`, 1.32 mm
wide (2A/P), bbox x -18.3..22.3, y 7.2..16.5: stage 2 has no notion of a blur, it sees a grey
ring. Stage 3 to 7 then sew it as a satin band at a median cross of 1.97 mm: a fuzzy halo.
It survived because nothing before stage 6 asks "is this the page showing through as a shadow"
except `bevel_fold` pass 1 (a band near the art's own page colour, >= 40% of its outline on the
page, >= 30% hugging the art, not wrapping it), and that pass runs only inside `bevel_ring_fold`.
`bevel_ring_fold` ON does remove it, but also folds the black and the bevel bands away, closes
the O's counter and leaves one flat gold (picture in the PR): the whole word is lost. `shadow_to_page`
is pass 1 alone, so the shadow goes and nothing else folds.

## 3. The TM is a thread limit

At 74.9 mm the art's TM is 1.72 x 0.94 mm with strokes 0.09 to 0.12 mm (`tm-mark-golden-tee-2026-10-26`).
A 40 wt thread lays 0.40 mm (`machine.thread_profile`), so the strokes are 0.23 to 0.30 of ONE thread
and the whole glyph is 2.3 thread widths tall. Nothing sews a 0.1 mm line; a single run is already
4x the stroke, and the 0.5 mm `bean_letter_max_stroke_mm` line is the thinnest stroke the engine
treats as a letter. The pro re-sets the mark at 4.3 x 2.0 mm (x2.5, a hand-drawn double run). Stage 2
also drops it (`thin_ink` 3 px floor, 2 px strokes). Kent ruled "no build" on 2026-10-26 and there is
still no second job carrying a TM, (R) or (C). Written up, not built.

## What was NOT changed

- Satin cross floor / pull (gate 1). Sewn black bands stay at the floor; only their order changed.
- `bevel_ring_fold`, `keyline_fragment_drop`, `merge_chroma_guard`: untouched.
