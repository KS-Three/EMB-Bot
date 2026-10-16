---
name: bean-holds-on-2026-10-15
description: Kent flipped both bean-letter holds ON (counter hold 0.25, bay hold 0.2) as plain defaults, not switch values; None stays OFF so the three sew-out cards' OFF arms now pin it explicitly; the price is a few stitches per design and ~0.1 mm outward on held letters
metadata:
  type: project
---

Kent, 2026-10-15, after the 80 mm ink-link fix ([[the-80mm-ink-link-2026-10-15]])
and the choice "flip both holds ON": `bean_letter_counter_hold_mm` 0.25 (#952)
and `bean_letter_bay_hold` 0.2 (#967) are defaults now.

**Plain defaults, deliberately not `SMALL_TEXT_TRUE_SIZE` values.** The switch
refills a None, so a switch value cannot be turned OFF while the switch is ON
(a float 0.0 would have been the only way). The three sew-out card tools
(`sewout_card_lettering_arms`, `sewout_card_bayhold_edgecap`,
`sewout_card_passes`) expressed "hold OFF" as no override, i.e. the old
default; with plain defaults an explicit None is OFF, so each card's SWITCH
dict now pins both holds None and the cards' committed cuts keep their meaning
on a re-cut. `PRE_FLIP` pins None for both; `flagcost.FLAGS` lists them.

**Price (holds OFF vs ON, both set explicitly, lane cut from main 09c69f0b):**
Fremont Hat 81 mm 15,330 / 41 -> 15,340 / 41, 19 shapes (the 8 opens both
counters, the 9's tail and the 5's bay open; `docs/renders/bean-holds-on/`).
The rest of the corpus is in that folder's README. Two md5 pins moved in
`test_small_text_counter_guard` (the synthetic line's bean letters at 1.55 and
2.5 mm caps), re-pinned with the reason; the 3 mm line has nothing within a
hold's reach.

**Why:** a flip that changes what "no override" means breaks every tool that
relied on the old default silently; grep the card tools for the flag before
flipping anything bean-letter.
**How to apply:** when flipping a `float | None` flag, decide first whether
None must still mean OFF under the switch; if any committed artefact (a card,
a golden) was cut on the old default, pin the old value explicitly there.
Unsewn: the holds are gate-1 candidates and Kent's card (#959 / #967) is
what settles them on cloth.
