---
name: dark-ink-bean-by-width-2026-11-16
description: dark_ink_bean_by_width ON 2026-11-16 (Kent "Flip ON (Recommended)"): dark-ink strokes bean or sew satin by their group's median width (0.75 mm), not by thread contrast 50; NOAA +21 trims, 8 of 16 designs move
metadata:
  type: project
---

**Fault.** `bean_dark_ink` decided bean vs satin by thread contrast to the
ground (`BEAN_MAX_GROUND_DE00` 50.0), a stand-in for "pen line vs designed
lettering" that got real lettering backwards. NOAA ring text (90 mm): strokes
0.46 mm, contrast 66.8, so satin; the Column lane drops crosses under its 0.5
mm floor and 7 of 52 letters lost strokes. EPA ring text (90 mm): strokes
0.91 mm, contrast 44.9, so thin bean lines for bold lettering; all 22 measured
letters had under 0.8 of their area sewn.

**Rule.** `bean_dark_ink(regions, by_width=True)` groups strokes by (ground
shape, stroke thread); group median mean width (2 x area / perimeter) under
`thin_ink.DARK_INK_BEAN_MAX_WIDTH_MM` = 1.5 x `SATIN_MIN_CROSS_MM` = 0.75 mm
beans every member, at or over it none, whatever the contrast. No ground, no
bean. Census of 550 strokes over 53 designs: thin groups 0.26-0.65 mm, bold
0.80-1.39 mm, nothing between. A layout threshold judged from renders.

**Result (16 designs with dark-ink strokes).** 8 change (stitches / trims off
to on): NOAA 33436->33137 / 28->49; EPA 25291->26511 / 42->35; FEMA
9009->8962 / 47->46; NASA 23325->23386 / 29->34; USAID 10095->12175 / 39->47;
hed_p_e 3813->3778 / 15->17; Bridge hat 7912->7930 / 15->17; Bridge left chest
10190->10231 / 16->14. 8 byte-identical: Forest Service, NPS, Energy Star,
Ford, Pooh, both Hotel Fremont jobs, Precision Drone.

**Kent, 2026-11-16**, shown the EPA, NOAA, USAID and Bridge hat sheets and
asked "Flip dark_ink_bean_by_width ON?": "Flip ON (Recommended)". Earlier,
on the EPA ring close-up with the bean off: "the United States is a huge
improvement."

**Costs.** NOAA +21 trims (each bean letter stroke is its own run); USAID +2,080
stitches; FEMA seal text and Bridge hat small text stay rough either way. False
restores the engine as it was (conftest `BEAN_BY_WIDTH_2026_11_16_OFF`).
