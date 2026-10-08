# A held hole with a colour in it — the seam that gets no tongue (2026-10-08)

**Flag:** `cfg.held_hole_bare_only`, built **OFF**. **Defect:** MASTER_SCOPE 6,
"Seams" — *"a hole held open at the detail floor gets no tongue"* (found
2026-09-03, `.claude/memory/seams-2026-09-03.md`, which named this cure as the
open design option: grow the tongue without closing the hole). **Instrument:**
`digitizer/tools/held_hole_tongue.py`. **Tests:**
`digitizer/tests/test_held_hole_bare_only.py`. **Renders:**
[`renders/held-hole-tongue-2026-10-08/`](renders/held-hole-tongue-2026-10-08/).

## The mechanism

`stage5_overlap.resolve_overlaps` grows every shape by the fabric's pull and
reaches the earlier colour `pull + overlap_mm` under whatever sews later. Growing
the shell shrinks its holes, so a hole that would fall under `min_detail_mm²`
(2.25 mm²) is **held open at its original size** — subtracted whole from the
grown shape. That is right for a counter. It is wrong for a hole a LATER
stitched colour sews in: subtracting the whole hole also subtracts the ground's
pull growth and its underlap tongue under the piece, so the piece sits in a
hole in the ground fill with nothing beneath its edges — a butt joint, plus
the vectoriser's anti-alias sliver of bare fabric round it. That is Kent's
second sew-out finding (*"a visible line of fabric on the seams"*) at its
most literal.

Who it hits: small pieces (2–13 mm²) inside a large ground. On Hotel Fremont
they are the patch's lettering (the pro's file lays those columns ON the
fill); on drone and Bridge Bar they are ordinary non-letter shapes.

## The cure

ON, a held hole holds open only its **bare** part — what no later STITCHED
shape covers — and only the bare pieces at or over the same `min_detail_mm²`
floor the hole was judged by (`stage5_overlap._bare_part`). The slivers
between a piece and its hole's edge are under the floor stage 3 drops detail
at; the ground grows into them and reaches its tongue under the piece, as on
every seam that was never held. A hole with no later stitched shape in it is
held exactly as before (same polygon, byte for byte); an unstitched later
shape is bare fabric by design and covers nothing. **No new constant** — the
floor and the tongue are the engine's own (gate 1 clean; the tongue's DEPTH,
`overlap_mm`, is still card block 6's to settle on cloth).

## Measured, 80 mm, left chest, OFF → ON

`held_hole_tongue.py --all`. *Pieces*: later stitched shapes in a hole the OFF
engine holds. *Tongue sewn*: of points `pull + overlap/2` inside each piece's
edge, the share the GROUND's own thread passes within one fill row of — read
off the stitches, per DOCTRINE ("prove a seam on the stitches"). *Ring bare*:
the 0.2 mm band either side of each piece's edge, inside its hole, that no
thread of any colour comes within a fill row of.

| fixture | pieces | holes held | depth-0 seam mm | tongue sewn | ring bare mm² | stitches | trims |
|---|---|---|---|---|---|---|---|
| `art/logo_hotel_fremont_patch.png` | 10 | 10 → 0 | 123.5 → 0 | 0% → 100% | 1.564 → 0.0 | 16,810 → 16,118 | 59 → 52 |
| `photo/logo_hotel_fremont.webp` | 9 | 9 → 0 | 158.2 → 0 | 0% → 100% | 0.653 → 0.0 | 13,745 → 13,196 | 35 → 33 |
| `photo/drone_render.png` | 7 | 9 → 4 | 25.6 → 1.5 | 0% → 100% | 0.804 → 0.001 | 19,026 → 19,023 | 142 → 142 |
| `photo/logo_bridge_bar.jpg` | 2 | 9 → 7 | 7.9 → 0 | 0% → 100% | 0.25 → 0.0 | 16,850 → 16,907 | 92 → 89 |
| `art/logo_golke_roofing.png` | 0 | 2 → 2 | — | — | — | plan md5-identical | |
| `photo/enthusiast_logo.png` | 0 | 0 | — | — | — | plan md5-identical | |
| `becker_marine_logo.png` | 0 | 0 | — | — | — | plan md5-identical | |
| `logo_whitebg.png` | 0 | 0 | — | — | — | plan md5-identical | |

Golke's two held holes each hold an UNSTITCHED piece (a garment-coloured
body), so they stay held — the case the stitched-only rule exists for.
Drone keeps four: two real bare openings (2.26 and 2.97 mm² of fabric beside
their pieces) and two holes with nothing stitched in them.

**Why Fremont gets CHEAPER.** Every stitch that moves is the ground fill's
(6,962 → 6,303 fill points, travel 96 → 64); every letter sews byte-identical
stitch counts. Ten holes broke the fill's rows into short spans with their
own ends and connectors (`LONG_JUMPS_TRIMMED` 31 → 9); without them the rows
run through. Cover was checked, not assumed: the ground's own fill covers
100.00% of its artwork both ways, and stitched artwork with NO thread within
0.2 mm falls **0.806 → 0.000 mm²**.

**The one column that reads worse, and why it is the instrument.**
`seam_underlap`'s seam length under 0.25 mm rises on drone (374 → 456 mm).
Every pair that moved is a released piece: OFF, its seam had no sewn overlap,
so the instrument fell back to the ARTWORK contact (0.65–2.3 mm each) at depth
0; ON, it measures the whole 7–23 mm seam, at a depth of about half the
piece's width (0.12–0.28 mm) — because these pieces are 0.27–0.67 mm wide and
the ground's 0.55 mm tongue now runs under ALL of them. A seam the instrument
could not see is now a seam it measures as fully underlaid. On Fremont and
the webp, where pieces are wider, the same column falls (387.6 → 303.2,
815.9 → 701.3).

## The renders

`renders/held-hole-tongue-2026-10-08/{drone_render,logo_hotel_fremont_patch,logo_bridge_bar}.png`
— OFF | ON close-ups drawn from the actual thread path at ~40-weight width,
the piece's own thread at 35% opacity so what is UNDER it shows, its artwork
edge in red. OFF: pale fabric under every piece, and bare specks at Fremont's
serif tips. ON: the ground's thread runs beneath. A remaining pale patch
inside the widest drone piece is its own interior beyond the tongue's reach,
covered by the piece's own satin — not a seam.

## Not done, and why

- **Not flipped.** OFF is the shipped engine; the flip is Kent's.
- **Not sewn.** Whether the ground's thread under a thin satin piece reads as
  bulk on cloth is a sew-out question (card block 6 also sets the depth).
- **The other cost:** a released piece now sews over the ground's fill
  (two layers where there was one). Preflight, OFF → ON, image passed so the
  thread check runs: score and grade unchanged on all four (Fremont patch
  88 B, webp 88 B, drone 0 F, Bridge Bar 0 F — the same findings list both
  ways), `DENSITY_STACKED` fires on none; `coverage_max` drone 8.32 → 8.83,
  webp 7.41 → 7.42, Bridge Bar 8.56 both, Fremont patch 6.80 → **6.47**.
  The stack is real on drone, and the sew-out is what prices it.
