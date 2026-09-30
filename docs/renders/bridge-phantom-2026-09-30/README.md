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

## The script as lettering, measured (2026-09-30, Kent's pick)

*Why "Bridge" is not `text_candidate`, and whether classifying it as
lettering would open its gaps.* Numbers in `script-as-lettering.json`.

**The classifier cannot see a connected word.** `detect_text_clusters`
admits a region through the letter door on three gates — height 1.5–60 mm,
stroke cv ≤ 0.55, bbox aspect 0.05–1.4 — and then tags only a CLUSTER of
three or more linked members (one ink, heights within 0.8, near each other).
"Bridge" (`S71ddac97`, 245.7 mm², five counters, 37.7 × 14.4 mm, sewn as
satin) passes height (14.4) and stroke cv (0.328) and fails **aspect: 2.616
against a ceiling of 1.4** — the ceiling was calibrated on single glyphs
(the benchmark's 14 letters read 0.107–0.964, its fragments 1.778–2.125), and
a six-letter script word is 2.6 times wider than tall. Past that gate it
would still tag nothing: a cluster needs three members and the word IS the
cluster — bridge has 26 letter candidates in 80 regions, none in the
script's red. The house-angle grouping uses the same aspect gate, so a
script word takes its own angle too. tires' "TIRES" (441 mm², 65.1 × 17.2 mm,
aspect 3.78, stroke cv 0.166) fails the same gate: four candidates, no cluster.

**Tagging it opens nothing.** With the script force-tagged as a text
cluster and every shipped lettering flag ON, shipped → tagged: 16,179 →
16,388 stitches, 101 → 103 trims, bare satin 4.31 → 4.07 %, **red on yellow
39.9 → 40.6 mm²** (red artwork bare 0.2 → 0.6); the script's runs satin
12 → 11, underlay 18 → 22, travel 8 → 6. On tires the tag reads the same
way: 2,646 → 2,897 stitches (underlay 15 → 20), trims 8, bare 4.44 → 4.01 %.
The rules that read the tag are `satin_lettering_split` (no width ceiling,
per-stroke rung, fold guard), `edge_cap_skip_lettering` (no silhouette cap
over the letter's outline), the per-cluster shared stitch width and
preflight's legibility OCR. None reads the rails, the pull or a gap.

**The gaps are closed in the artwork.** At the design's scale (the ink's
279 px across 80 mm, 3.49 px/mm; measured 4× upsampled) the open gaps
between the script's strokes — 85 mm of channel — read p10 / p25 / p50 /
p75 / p90 = 0.57 / 1.06 / 1.58 / 2.29 / 2.72 mm: 9 % of the gap length is
under 0.5 mm, 17 % under 0.8, **22 % under 1.0**, 45 % under 1.5. The
counters are tighter (p50 0.80 mm, half under 0.8); the strokes themselves
p50 1.89 mm. Two facing rails on pique knit push out `pull_comp_mm` 0.3
each and a thread covers 0.40, so any gap under 1.0 mm is closed before a
rule runs; the pull band is 22 of the 40 mm² (above) and the general notch
guard recovered 2 (above). What could still open daylight is the 1.0–1.5 mm
quarter of the gap length, and only by holding the push where two strokes
face each other — the guard that costs bare on every other fixture unless
it is scoped to script, which the classifier cannot name.
