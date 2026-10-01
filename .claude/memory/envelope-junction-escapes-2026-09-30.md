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

**Teeth (same day, Kent's pick after the comb)**: 8 of Becker's 23 remaining
stretches were single-station (0.34–0.83 mm out and back); `_drop_short_reaches`
reverts stretches shorter than `_ENVELOPE_WINDOW` (3). Measured: 78 → 72
reached, 23 → 17 stretches, 9,333 → 9,321 st, reached-station jitter 28.4 →
26.3% (symmetric 9.3) — the teeth were two points of it; the rest is the
long reaches' plateaus/steps (1.8 mm max), the artwork's features. Slope
limit / ramp simulated: −24 to −49% extension area — Kent's trade, not
built. `docs/renders/envelope-teeth-2026-09-30/`.

**Evening sitting (same day, Kent's pick after the teeth)**: the labelled
page rebuilt as this morning's engine | today (`ref_0930am` = 1e5f8fe2,
main before #577/#578/#579) on the nine logos, tag `evening-0930`, the
dissolve pairs kept (still unjudged), and a needle-hole map beside every
render (`stitchviz.render_penetrations`, `--render`'s `__holes.jpg`, the
page's *thread | needle holes* toggle) because the thread render cannot
show the comb. The corpus table under the ref arm's head:
`docs/eye-pairs-2026-09-30/three-changes-corpus.json` (stitches, trims,
envelope reaches with escapes, split on/off changes, before → after per
logo). Verdicts: his, pending at the time of writing.

**Evening verdicts (same night)**: ref pairs 4 same, 3 both bad, 1 before
(tires), 0 after — the day's three changes did not reach the eye; becker
note: "the lettering does not flow, satin stitching is not smooth and
structured pattern" (third time). Dissolve: bridge after, gaulke/golden_tee
before, tires same, screenshot both bad → stays OFF; gaulke's "satin trim"
= four grey halo slivers (0.19–0.28 mm², thread 0108, rescued small
shapes as running stitches). **tires' "before better" was the confound**:
the rembg venv is gitignored, a ref worktree has none, tires is
photo_scene → BEFORE skipped prep (2,500 st) vs 2,646 with the venv linked;
both prepped sides show the same ragged matte edges. Fixed:
`refarm.link_photo_prep` + `photo_prep_env` on the row + the badge reads it.
Trap: the four "rembg-venv" local reds do NOT mean the venv is absent —
it runs here. Levers left for the lettering: split_satin_above_mm=7.0 (the
pro's Becker style) and the symmetric rails, as arms for a texture sitting.

**Texture sitting (late, Kent's pick)**: arms `split_7mm`
(split_satin_above_mm=7.0, the pro's Becker style) and `rails_symmetric`
(envelope OFF) on the page under tag `texture-0930`, 8 pairs, tables in
`docs/eye-pairs-2026-09-30/texture-corpus.json`. **Leg-length jitter is
NOT the eye's "smooth"**: becker's letters 42% of consecutive legs differ
by >0.15 mm under every arm; the pro's own Becker columns 35%, and net of
taper the pro is rougher (54% vs 45%). Do not build a rail smoother on
that number; get Kent's words for "flow" first. Verdicts pending.

**Texture verdicts (2026-10-01 01:21Z, 7 of 8)**: split_7mm — becker,
bridge, drone, tires *same* (screenshot: "please stop using this shitty
logo", now `EXCLUDED_FIXTURES`); rails_symmetric — golden_tee *before*
("very nice line following the outline" = the envelope), tires *same*,
becker unjudged. No rulings, no words for "flow". So 5.0 stays, no
sew-out pack; the envelope stays ON; becker's flow note still open —
next lever must come from his words or a sew-out, not rail-level changes.

**The pro beside ours (2026-10-01, Kent's pick)**: a `__file__` arm
(`tools/eye_pairs/filearm.py`, `pro_file` in ARMS: becker's 101.9 mm hat
PES) on the page under tag `pro-1001`, labels "OURS · today" | "THE PRO ·
the pro's file", no ruling. Table by `tools/satin_columns` on both designs'
stitch records: satin share 31.3 vs 42.6%, width p50 2.24 vs 2.66, legs
over 5 mm 0 vs 26.5%, jitter 32.5 vs 28.5%. Renders: the pro sews BECKER
(arch) as black FILL with grey satin keylines and MARINE as grey satin
columns, one direction per stroke, no mid-column holes. Kent's texture
head notes: "not sure what's being shown here" (both arms) — explain
LEFT/RIGHT in plain words on a page. Verdict pending.

**The pro verdict (2026-10-01 01:53Z)**: the pro's flows (`after`); Kent's
note names the BACK STITCHING ("supports the top threading so it has
structure and support"); in chat he also took fill-for-big-letters,
whole-stroke crosses, one direction per stroke. Built
`tools/underlay_cover.py` (covered-thread rule, both files). Findings on
MARINE: the interior-hole scatter IS the comb split (stems 5.5-6.9 mm >
5.0): 1,413 → 774 (7 mm) → 246 (off) vs the pro's 304; our stems already
carry centre run + ladder zigzag (18% of thread vs his crosshatch 28.9%,
support 20.7% both); 19.5% of our MARINE satin is stacked under later
satin (next lever). The arch letters: the 146-px fixture has OUTLINED
white-bodied letters; the pro's black fill is his source's. Trap: the
oversize-skip flag was a no-op (lettering ceiling = inf) — reverted.
Arm `split_off` on the `back-1001` page; rails_symmetric/becker corrected
to "same".
