# Both bean-letter holds ON: the price (2026-10-15)

Kent's call after the 80 mm ink-link fix (#976): "flip both holds ON".
`bean_letter_counter_hold_mm` 0.25 (#952, needle points held off a small counter) and
`bean_letter_bay_hold` 0.2 (#967, stations held off an open bay) are plain defaults now;
an explicit None is OFF. Thread renders of EMB-Bot's own output (`digitizer_core.stitchviz`
through `tools/fremont_triage`'s panel helpers), not cloth. Nothing was sewn: both values
are gate-1 candidates and Kent's cards (#959 block A, #967 block B) settle them.

Every cell below was digitized twice with both holds set EXPLICITLY (OFF: None / None;
ON: 0.25 / 0.2), so the numbers do not depend on the config's defaults. The lane was cut
from `main` 09c69f0b; the 80 mm row was re-run after #976 merged (its OFF md5 is #976's
ON cell, `aed530f4`).

## Fremont, Hat, the Studio's request (`tools/fremont_triage.run_arm`)

| width | holds OFF | holds ON | changed shapes | renders |
|---|---|---|---|---|
| **80 mm (Kent's job, with #976)** | 14,812 st / 43 tr, `aed530f4` | **14,824 / 43**, `75f44f90` | 19 | `hat80_1895_pair.png`, `hat80_the_pair.png`, `hat80_tagline_pair.png` |
| 81 mm | 15,330 / 41, `1541421f` | 15,340 / 41, `a69f0719` | 19 | `hat81_1895_pair.png`, `hat81_tagline_pair.png` |
| 92.5 mm | 18,675 / 54, `e0d9323c` | 18,706 / 54, `12032076` | 18 | |

What the renders show: the 8 opens both counters (OFF: the upper one sewn shut), the 9's
tail bay and the 5's bay open, the tagline's A counters open; THE is unchanged but for a
slight peak on the T's bar where the bay hold lifts the stations between the two bays
under the bar (#967's "a stroke between two bays leans toward the wider one").

## The 17-design lettering corpus (`small_lettering_compare.corpus_designs`)

| design | holds OFF | holds ON | changed shapes |
|---|---|---|---|
| fremont (92.5 mm patch) | 20,832 / 48, `6d132b3e` | 20,863 / 48, `528e12a9` | 18 |
| fremont_hat81 | 15,330 / 41 | 15,340 / 41 | 19 |
| fremont_hat925 | 18,675 / 54 | 18,706 / 54 | 18 |
| enthusiast | 2,408 / 8, `1df648e7` | 2,414 / 8, `9944fec7` | 10 |
| screenshot | 8,511 / 63, `be7d0d38` | 8,514 / 63, `5e87da5a` | 4 |
| drone | 19,281 / 130 | identical | 0 |
| becker | 8,758 / 29 | identical | 0 |
| tires | 2,732 / 8 | identical | 0 |
| bridge | 18,923 / 99 | identical | 0 |
| golden_tee | 8,412 / 45 | identical | 0 |
| gaulke | 4,893 / 23 | identical | 0 |
| sp_synthetic_2.5 | 321 / 1, `a502e790` | 318 / 1, `42401291` | 3 |
| sp_synthetic_3 | 378 / 2, `88822294` | identical | 0 |
| sp_synthetic_4 | 547 / 4 | identical | 0 |
| sp_fremont_tagline_2.5 | 569 / 5, `a7d09ec9` | 590 / 5, `c57e1189` | 11 |
| sp_fremont_tagline_3 | 719 / 5, `4a197c3d` | 719 / 5, `af05900f` | 8 |
| sp_fremont_tagline_4 | 991 / 10, `23e0edc9` | 985 / 10, `35ff0da6` | 5 |

Only designs with bean letters move, and by a few stitches; no design gains or loses a
trim. The two moved md5 pins in `tests/test_small_text_counter_guard.py` are the
synthetic line's 1.55 and 2.5 mm cells (`00098415bf`, `42401291c4`), re-pinned with the
reason; the 3 mm line has nothing within a hold's reach.

## What changed besides the defaults

The three sew-out card tools (`sewout_card_lettering_arms`, `sewout_card_bayhold_edgecap`,
`sewout_card_passes`) expressed "hold OFF" as no override, i.e. the old default. Each now
pins both holds None in its SWITCH dict (block A's hold arm and block B's hold arms set
their own), so a re-cut sews what the committed cuts record. `PRE_FLIP` pins None for
both; `flagcost.FLAGS` lists them.
