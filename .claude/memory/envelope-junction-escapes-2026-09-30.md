# The envelope's junction escapes — Becker's "void-filling" (2026-09-30)

**Kent's note** on the envelope's labelled sitting (Becker 100 mm, *after
better*): "these stitches look like they are just trying to fill a void."
His pick after the resolution line: what the extended rails sew, and the
texture lever.

**Measured** (trace hook on `_rail_points`, scratch → `tools/envelope_escapes.py`):
- Becker 100 mm: 183 reached stations, 159 on the six satin letters (top
  row M A R I N E; the bottom row is fill). The E's stem reads its far side
  at 7.4–9.6 mm against its own 3.0–3.3 half-width (the ray runs along an
  arm to its end) for about 13 stations —
  longer than the median (5) + running-min (7) windows; the corridor cap at
  the junction is the merged footprint (3.66 → 6.05 mm). Crosses ran 2–2.8
  mm into the arms: 78% of the envelope's 63 mm² of new ground on the
  letters was already sewn; double coverage 9.3 → 11.0%; rail jitter >0.15
  at reached stations 31.5% vs 9.1% symmetric; unreached letters 8.3 → 20.0%.
- Nine logos: 459 reached, 313 escapes (68%). No cap on the reach separates
  (ext ≤ 1 mm: 89% genuine kept / 76% escapes through; ratio, boundary
  distance similar). The END inside a sibling stroke's corridor: 89% / 5%
  on the screen; the shipped rule realized 73% kept / 7% through.

**Shipped**: `_in_sibling_ribbon` in the envelope branch; `satin_shape`
passes the other strokes' spines (`siblings`), `_satin_joined` adds the
other members. Sibling half-width = MEDIAN of the field along its spine
(the field at the node is the merged footprint and refused a genuine
reach on the stem's far side — the first cut's bug; samples at tenths of
the arc length, plus the pull). After: 129 reached, 23 escapes, 106
genuine; Becker 100 mm 9,563 → 8,932 stitches (sym 8,827), new ground 15.2
mm² at 87% bare before; Becker 80 mm bare 9.550% (shipped envelope 9.484,
sym 10.222) at 5,697 stitches (sym 5,691, shipped 5,750: the escapes were
the longest crosses and carried the split points).
golden_tee's keyline reach (another shape, not a sibling) untouched.

**Test pins moved**: MARINE trims-test ceiling 1.18 → 1.19 (1.179 read;
every arm cheaper, OFF 2,010 → 1,968 / ON 2,461 → 2,372 = 1.205: the grown
polygon's rays escape at more stations, 275 vs 238); the envelope test's
stitch assertion now "within 2% of symmetric, under True". New fixture test: a 5 mm stem with a 5 × 6 mm
arm at `max_width_mm=inf`; rule neutered → 6.5 mm half-length vs 4.0.

**Traps**: the far ray reaches 4 half-widths — an arm longer than that
gives the fallback (nominal half-width), no escape; a 12.5 mm test arm
showed nothing. `pgrep -f "<literal>"` matched my own shell again (exit
144) — build the pattern with a bracket (`capt[u]re`).

**Left (Kent's picks)**: short genuine reaches still read as teeth (8 of 23
stretches 1–2 stations; jitter 3× locally) — minimum stretch length / ramp,
coverage vs flow; split satin flicker on the letters (71% split, 18/22
runs mixed, 75 transitions) under every rail mode; 23 escapes remain
(Becker 15, golden_tee 6, bridge 1, drone 1).

Records: `docs/renders/envelope-escapes-2026-09-30/` (README, census.json,
E/R/A/M strips + golden_tee T), scope-history, DOCTRINE ("A rail that
reaches for its far edge must first know whose edge it found").
