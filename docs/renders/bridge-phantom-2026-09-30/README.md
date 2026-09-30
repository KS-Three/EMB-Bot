# bridge at 80 mm: the border that goes on and off, and the script

Kent's pick 2026-09-30, in his words on the envelope sitting: *"The lettering
on bridge is smooshed together and the satin border is jumpy, its on off on
off etc."* Rendered on the engine of that night (rail comp ON, the envelope
ON), `left_chest`, `max_colors=6`, 14 px/mm, lit.

- `bridge-80mm-shipped-vs-dissolve.jpg` — artwork | shipped | `dissolve_phantom_blends=True`.
- `ring-right-spoke-crop.jpg` — the ring at the right-hand spoke, shipped | dissolve, 2.5×.

**The border.** `logo_bridge_bar.jpg` is a JPEG and its black ring and spokes
carry a grey ringing halo; the gradient lane quantises that halo as a sixth
thread, `(153,153,153)`, and sews it as 57 shapes in 94 runs — 400 mm² of
thread of which 133 lies on grey artwork, 139 on other ink and 145 on white:
the light-grey satin fragments along every black edge, the "on off on off".
`dissolve_phantom_blends=True` (built 2026-09-04 for exactly this fixture,
OFF "waiting on Kent's look at a render") folds the halo into its sides:
grey 400 → 13 mm², regions 80 → 34, trims 98 → 59, jumps 32 → 20, stitches
15,432 → 11,613. Its own artefact is visible in the right panel: a few halo
labels adjacent to the teal text fold into teal, so the ring carries teal
specks at the right and bottom (teal on other ink 17.5 → 39.6 mm², on white
0 → 6.5). Corpus: fremont and drone byte-identical, golden_tee −50 stitches,
gaulke +84 and +2 trims, screenshot +23 and +5 trims; becker, tires and
enthusiast are not on that lane.

**The script.** "Bridge" is one 246 mm² satin shape with five counters, and
it is not classified as lettering (no `text_candidate`), so no lettering
rule touches it. Red thread on yellow artwork: 40.1 mm² shipped, 3.1 of it
inside the counters (the rail push's counter guard holds them) and 36.9
outside — the pull band around the whole outline and the inter-letter gaps.
With the pull in the polygon instead of on the rails it reads 17.9 (3.4 /
14.4): rail comp's outward push is 22 of the 40, the script's own sub-floor
gaps the rest. A notch guard on the rail push — the counter rule extended to
a probe that leaves the polygon and re-enters it within reach — moved that
40.1 to 38.3 and cost bare satin on every fixture (MARINE 6.28 → 6.60%,
ENTHUSIAST 6.98 → 7.63, golden_tee 7.20 → 8.35), so it is a measured
negative, not a fix. The teal "BAR & RESTAURANT" (1.6 mm cap height at
80 mm) sews as five blobs, below the lettering floor.
