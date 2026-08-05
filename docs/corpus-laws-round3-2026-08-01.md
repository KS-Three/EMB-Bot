## Corpus laws, round 3 (2026-08-01)

Six dimensions the first two rounds could not reach: fill ANGLE, density vs
SIZE, colour SEQUENCING, entry/exit POSITION, underlay RECIPE per element
class, and what happens where two regions MEET. Six purpose-built instruments,
each validated against synthetic fixtures of known geometry **before** it was
pointed at the corpus, each reporting its own blind spots.

Corpus: the same 36 `scratch_corpus` DSTs plus Kent's commissioned
PRECISION DRON HAT, beckers logo hat, and the two distinct HOTEL FREMONT cuts —
**40 files, 425,621 stitches**. (`HOTEL FREMONT .DST` and
`HOTEL FREMONT  (1).DST` are byte-identical, md5 `3da32f23…`; `(2)` is a
genuinely different cut. Instruments reporting 39 files dropped one duplicate.)

Round 3 closes two things the playbook has been carrying open — **the interleave
question under law 7** and **the unmeasured `BORDER_SEAM_OFFSET_MM`** — and it
refutes one rule the engine ships and one conclusion a round-3 instrument
reached about itself. Both refutations are below, in the open, with the
evidence.

---

### Fill angle (the light tier only — read the scope note first)

**Scope note, stated before the laws that depend on it.** The angle instrument
accepts a run as tatami only when its row gap falls in **[0.55, 2.0] mm**.
The corpus's real top-fill density is **0.19–0.25 mm** (law 19). The window
therefore *structurally excludes* every dense fill in the corpus — those runs
land in the instrument's "satin-density reject" pile, which is exactly what it
reports for all 30 of its fill-free files. Two consequences, both load-bearing:

1. **Its headline "Kent's commissioned files contain ZERO tatami — the pro
   answer for cap logos is satin everything" is false, and two other round-3
   instruments measuring the same bytes say so.** The density census finds a
   **1,373 mm² region in `HOTEL FREMONT  (2)` sewing at 0.177 mm row gap**, a
   1,913 mm² region carrying a sparse pass at 2.93, and **1,084 mm² in
   `PRECISION DRON HAT` at 2.32**; the seam census independently renders
   `PRECISION DRON` block 4 as *the full circular badge fill* with block 8 laid
   over it. Kent's files fill, and fill large. Do not build a "cap logos are
   all satin" rule.
2. **Laws 15–17 describe the LIGHT/sketch fill tier and nothing else.** The
   angle of a dense branded fill is, as of today, **unmeasured**.

The measured population: 64 regions, ~116k fill stitches, 10 of 40 files —
bunny-star, cat-and-girl, corgi, teddy-bear, snowman, chamomile, rose-hand,
summer-umbrella, christmas-sleigh, hello-spring. Row gap med 0.83 mm
(p10 0.62, p90 1.13), stitch med 2.20, coherence med 0.90. Angles are in the
pyembroidery y-up frame mod 180; screen renders mirror θ → 180−θ, so absolute
angles carry that ambiguity and every comparative number below does not.

**15. There is no design-wide fill angle.** **0 of 8** multi-fill designs share
one angle at a 10° tolerance. The dominant angle cluster carries a median
**0.46** of a design's fill stitches (p10 0.37, max 0.93). Folding
perpendicular mates into one axis family still leaves **2–4 families per
design** (dominant family share med 0.55). The two designs that *are*
effectively single-angle are the cleanest solid-fill pieces:
`rose-hand` (68°, 93% of fill stitches, per-element wobble 61–86°) and
`summer-umbrella` (117°, 93%, wobble 114–117° plus small 28/92° accents).
*Confidence: high for the light tier (synthetic tatami at 0/30/45/72/117.5°
recovered to ≤0.1° through perimeter-underlay contamination; split satin at
0 and 60° correctly rejected). Cross-check against `study_pro.fill_stats`
agrees within 5.7° on all 4 comparable regions — but only 4 were comparable.*

**16. 45° is not a default, and canonical angles are rare.** Region angle within
±7° of canonical: **0° 6%, 45° 6%, 90° 17%, 135° 0%, other 70%** (76%
stitch-weighted). Big regions (n ≥ 1000 st, n=28) cluster loosely near-vertical
tilted (88–119°) and shallow-near-horizontal (147–174°) — a 10–30° tilt off
canonical is the norm. **The angle tracks the region's long axis, or runs
square across it, and almost never sits at an unrelated oblique**: at aspect
ratio > 2.5 (n=9) the delta to the long axis is med 28°, **67% with-axis,
33% across, 0% oblique**, and only 1 of 9 elongated regions uses a canonical
angle at all. At AR 1–1.5: med 30°, 55% with-axis. At AR 1.5–2.5: med 29°,
51% with / 31% across.
*Confidence: high on "not 45", medium on the with/across split (n=9 at the
informative aspect ratio). Limit: a region is a needle-down run, so a fill
sewn in N sections counts N times.*

**17. Crosshatch — a second pass laid perpendicular over the first — is the
sketch tier's fill signature.** Of 153 overlapping same-design region pairs,
**~46 differ by 60–90°**, and the pattern appears in **7 of 8** multi-fill
designs. This is not angle noise; it is two deliberate passes over one area.
*Confidence: medium. Limit: the detector is coarse centroid/extent overlap,
so "same area" is approximate. Nothing here says whether crosshatch belongs
outside the sketch tier.*

**Where the corpus disagrees with itself on angle:** adjacent same-colour
fills share an angle in the solid-fill designs and deliberately do not in the
sketch designs. Same-block non-overlapping pairs: n=21, med difference
**22.8°**, only 24% within 10°. Nearby pairs (<15 mm apart, n=7) split cleanly
by house style — `teddy-bear` 2.1° and `bunny-star` 3.0° (shared) against
`corgi` 16.0/18.5/49.7° and `cat-and-girl` 25.4/29.0° (varied on purpose).
**Sharing an angle across neighbouring same-colour elements is a law for solid
work and an anti-pattern for sketch work.** No corpus evidence at all on fill
LETTERING angle: pro lettering in these 40 files is always satin, so the
"one shared angle across lettering rows" rule from the wordmark lesson stands
unrefuted and unconfirmed.

---

### Density vs size

Definitions used throughout: **fill gap** = perpendicular row spacing between
traverses consecutive *in sew order* inside one needle-down run. **satin
advance** = spine advance per cross; same-rail spacing = 2×. Both are trimmed
means, never medians — DST quantises to 0.1 mm and a median snaps to the grid
(fixture `satin_w18_split3_a0.42`: true 0.42, median reads 0.40, trimmed mean
recovers 0.419). 3,661 bands → 1,165 satin columns, 490 dense fill bands,
282 sparse zigzag underlay bands.

**18. Density does not grade with size. Pros hold it FLAT.** Fill row spacing
by region area, across three orders of magnitude:

| area mm² | n | med gap |
|---|---|---|
| 0–10 | 79 | 0.185 |
| 10–25 | 90 | 0.200 |
| 25–50 | 82 | 0.196 |
| 50–100 | 87 | 0.186 |
| 100–200 | 75 | 0.189 |
| 200–400 | 50 | 0.189 |
| 400–800 | 22 | 0.189 |
| 800+ | 5 | 0.188 |

Pooled Spearman ρ(area, gap) = **−0.057**; within-file median ρ = **+0.015**
across 19 files with signs both ways (`hello-fall` −0.543 … `cat-and-girl`
+0.794 — noise, not policy). Satin advance vs column LENGTH is equally flat:
0.180 / 0.196 / 0.194 / 0.196 / 0.191 / 0.190 / 0.190 / 0.183 mm from <3 mm to
70 mm+, within-file median ρ **−0.090**. A 1,373 mm² region in
`HOTEL FREMONT  (2)` sews at 0.177; a 0.8 mm² region in `bunny-star` sews at
0.073–0.19. **The file-to-file spread (per-file medians 0.178 `gather` to 0.290)
is far larger than any size effect** — house style, not geometry.
*Confidence: high. Backed by within-file ρ and per-file medians, not the pooled
n (39 files over-count). Limit: trims fragment regions into multiple bands, so
`area` understates fragmented shapes — but that biases toward the null, and the
flat result spans 0–10 to 800+ mm².*

**19. Fill row spacing is ~0.19–0.20 mm, in ONE pass. The interleave question
is closed.** Corpus fill gap med **0.194** (per-file p10 0.184, med 0.194,
p90 0.266). Law 7 hedged this as "0.20 effective, but that may be two
interleaved 0.40 passes"; `machine.py:39-40` carries the same hedge. **It is
not two passes.** The spacing is measured between traverses consecutive in sew
order inside one needle-down run, which an interleaved second pass cannot
produce, and the raw coordinates confirm it — `beckers logo hat.DST`, rails at
y=13.50/18.70, one stitch per cross, same-rail x-steps 0.30/0.40/0.40/0.30,
monotone single pass:

```
 -9.20 13.50    -8.90 13.50    -8.50 13.50    -8.10 13.50    -7.80 13.50
 -9.30 18.70    -8.90 18.70    -8.60 18.70    -8.30 18.70    -7.90 18.70
```

Three independent instruments converge: the density census at **0.194**, the
underlay census's top-fill row gap at **0.25** (p10 0.20, p90 0.50), and round
one's `study_pro` at "~0.20 effective in dense branded fills".
`FILL_ROW_MM = 0.40` is **2× sparser than the corpus**.
*Confidence: high on the number and on the refutation. Limit: single-stitch-
per-row fills are structurally absent from the population (`nsub>=2` required)
and count as satin, which biases small-region stitch stats downward.*

**20. Fill stitch length is a ~4.0 mm CEILING with even division per row, not a
target length.** The raw correlation looks overwhelming — pooled ρ(row length,
stitch) = **+0.904**, within-file median +0.847, 19/19 files |ρ|>0.4 — and it
dissolves the moment you restrict to rows long enough to reach the cap:
all rows ρ +0.904 → rows ≥8 mm ρ +0.647 → **rows ≥12 mm ρ +0.240**, with
stitch p10 3.20 / med 3.49 / **p90 4.00**. Per-file maxima in rows ≥8 mm cluster
hard against the ceiling: `hello-fall` 4.04, `miss` 4.03, `i-love-pets` 4.05,
`bunny-star` 4.30, `chamomile-love` 4.70. Short rows get short stitches as a
*consequence of dividing the row into a whole number of stitches*, not because
anyone graded them. This supersedes law 7's "2.0–3.4, median ~2.6" — that
median was short rows dragging the average down.
*Confidence: high. Limit: none material; the effect is arithmetic and visible
in every file.*

**21. Satin rail density is ~0.40 mm same-rail and tightens ~15% only past
4.5 mm of column width.** Corpus satin advance med **0.190** → same-rail
**0.38**. Independently, the underlay census measures same-rail penetration
spacing at **0.40–0.45 mm in every width bucket**, and the seam census measures
covering-border rail advance at **0.40** (p10 0.36, p90 0.42). Round one's
law 4 said 0.40–0.51 on the rails. **Four instruments, one number.** The one
real grade is by column WIDTH, and it is mild:

| width mm | n | med advance | same-rail |
|---|---|---|---|
| 0.8–1.5 | 258 | 0.181 | 0.362 |
| 1.5–2.5 | 401 | 0.197 | 0.393 |
| 2.5–3.5 | 211 | 0.190 | 0.379 |
| 3.5–4.5 | 109 | 0.179 | 0.357 |
| 4.5–6.0 | 61 | 0.167 | 0.334 |
| 6.0–20 | 23 | 0.160 | 0.320 |

Flat 0.18–0.20 up to 3.5 mm (74% of all columns), then ~15% tighter. Of the
10 files holding columns on both sides of 3.5 mm, **9/10 are denser when wide**,
median delta −0.016 mm. Robust to excluding `hope-christmas-inscription.dst`
(ρ −0.127 → −0.094) and to restricting to unsplit crosses (ρ −0.125).

**Correction to the density lane's own conclusion.** That lane reported the
engine sewing 0.80 mm same-rail and being "2× sparser than the corpus" in
satin. A code read refutes it: `stage6_satin` resamples the spine into stations
**`ceil(length / SATIN_SPACING_MM)`** — stations 0.40 mm apart — and the rail
order is **constant A, B, A, B** (the comment at `stage6_satin.py:1156` says so
explicitly, and explains that flipping alternate crosses would turn the return
leg into a hop *along* a rail). One penetration per rail per station means
**same-rail = 0.40 mm**, which is exactly what law 4's shipped fingerprint
measures (outer rail p95 0.47). `test_satin.py:231`'s `2 * SATIN_SPACING_MM`
samples `pts[0::4]` — every *other* A-rail penetration — so it asserts two
stations, not one. **Engine satin density already matches the corpus. The 2×
gap is real for FILL and imaginary for SATIN.**
*Confidence: high on the corpus numbers; high on the correction (direct code
read plus the existing fingerprint). Limit: 330 bands (9.0%) are ambiguous
satin/fill — a 2-stitch fill row and a half-split satin cross are the same
geometry, separated only by split-point stagger. That is a deliberate
selftest FAIL (`BLINDSPOT_fill_nostagger`), not a bug. 45 bean/triple-run
bands were stripped at advance <0.06 (`breathe-feathers` worst, p10 0.02
before stripping).*

---

### Underlay recipes, per element class

Instrument: stroke-based phase segmentation, where a *stroke* is the polyline
between apexes (turn ≥55°), so a split satin cross reads as ONE stroke of full
width — the trap that blinds `study_pro.classify`. 19/19 synthetic fixtures
pass at 0% geometry error. 1,684 satin columns, 507 fills.

**22. Zigzag underlay is gated on width at 2.0 mm AND on column LENGTH at
~6 mm.** Share of columns carrying a zigzag phase, by width:

| width mm | n | none | centre run | zigzag | edge run |
|---|---|---|---|---|---|
| <1.2 | 219 | 17% | 39% | 6% | 30% |
| 1.2–2.0 | 510 | 11% | 29% | 18% | 26% |
| 2.0–3.0 | 443 | 9% | 17% | **56%** | 14% |
| 3.0–4.5 | 284 | 6% | 9% | **70%** | 12% |
| 4.5–7.0 | 157 | 4% | 6% | **75%** | 12% |

The switch throws between 1.2–2.0 and 2.0–3.0: 18% → 56%. But width alone is
not the gate — **at any width, a column shorter than 6 mm gets an edge walk
(19–38%) and zigzag is rare**. The full recipe for a real column ≥2 mm wide and
≥15 mm long is **walk → zigzag → walk** (`Rc.Z.Rc` 17–22%) or walk → zigzag
(`Rc.Z` 14–21%). `SATIN_ZIGZAG_ABOVE_MM = 2.5` sits half a bucket high, and
the length gate does not exist in the engine at all.
*Confidence: high on the width crossover (law 2 independently put it at
2.0–2.5 from a different instrument); high on the length gate. Limit: the
>7.0 mm bucket is junk — 82% of its "columns" are shorter than 2× their own
width (median length 2.85 mm), i.e. sketch-zigzag lobes and fill fragments.
Only its len>15 sub-cell (n=13) is real.*

**23. Zigzag geometry is a constant, not a function of the column.** Pitch —
spine advance per cross — is **width-independent at 1.37–1.47 mm** (2.0–3.0 mm
columns 1.47, 3.0–4.5 mm 1.45, 4.5–7.0 mm 1.37; p10–p90 roughly 0.92–1.70).
Zigzag width is **0.80–0.85 × the column**, i.e. an inset of **0.25–0.40 mm per
side**. Underlay stitch length 2.46 / 3.22 / 2.90 mm by bucket. Centre-run
stitch length scales with width then caps at ~2.2 mm (1.22 / 1.60 / 2.10 / 2.14
/ 2.30 / 2.06), offset from the spine 0.05–0.11 mm — genuinely centred. Edge
run: stitch 0.89 → 1.97 mm, inset from the rail −0.02 mm on narrow columns
(it walks *on* the rail) rising to 0.62–1.08 mm on wide ones.

The engine's zigzag is **half as wide as practice and a third too sparse**:
`_stroke_underlay` narrows each rail point 0.3 of the way toward its partner,
giving **0.4 × column width** against the corpus's 0.82; and
`UNDERLAY_ZIGZAG_MM = 2.0` against a measured 1.45.
*Confidence: high (pitch and inset both stable across three width buckets and
robust to the lookback window — BACK 12→30 moves every cell ≤5 pp).*

**24. A zigzag almost never sews alone, and nobody double-zigzags.**
Zigzag-with-a-walk vs zigzag-alone runs **69/31, 85/15, 86/14, 85/15, 90/10,
83/17** across the width buckets — 85–90% in the buckets that matter.
Double-Z is **<1% of satin and 1% of fills**. The engine's existing
center_run + zigzag pairing already gets this right and should keep it.
*Confidence: high.*

**25. Small lettering gets one walk and nothing else.** Elements with a
min-dimension ≤8 mm (n=382, width med 1.40 mm, rail 0.40 mm): edge run 27%,
centre run 21%, mid run 13%, **none 12%**, Re.Rm 7%, zigzag 2.6%, Rc.Z 2.4%,
Re.Z 1.6%. **Walk-only ≈68%, any zigzag ≈7%, bare 12%.**
*Confidence: high on "a walk is there"; LOW on which walk. Halving the
footprint tolerance (0.8 → 0.4 mm) moves edge-run 30%→16% and centre-run
39%→47% in the <1.2 mm bucket. Trust the presence, not the position. Buckets
≥2 mm move ≤3 pp and are safe.*

**26. Under a fill, the underlay is a running line — an edge run or an interior
walk. A lattice is 7 cases in 507.** Fill underlay recipes: interior walk
21.7%, edge run 17.6%, **none 14.2%**, Rg.Z 8.9%, Z 6.9%, then Rg.Re / Re.Z.Re
/ Re.Rg / Re.Z / Z.Re at 3.4 / 3.0 / 2.8 / 2.6 / 2.2%. ~62% carry a running
underlay, ~27% a zigzag, 14% are bare. Edge run under fill: stitch **2.06 mm**
(1.08–3.47); interior walk 1.84 mm. **Sparse-grid tatami underlay: n=7 total.**
The shipped `edge_lattice` default is not what this corpus does.
Where a zigzag *is* used under a fill its angle against the top stitching is
**bimodal** — median 15° but p10 1.1° / p90 86°: digitizers pick parallel or
perpendicular, never a fixed 45°.
*Confidence: high on the ranking. Limit: an early containment-based attribution
scored a clean case at 25% and read 42% of columns as bare, because one
letter-long walk serves several short columns; switching to spine COVERAGE
moved "none" 42%→17%. Anything quoting 42% is wrong.*

**House styles disagree on underlay, loudly.** `enjoy-moment-script.dst` is
54 columns, **54% bare, 0% zigzag** — the only file in the corpus with no
zigzag underlay anywhere. Against it: `sweet-heart` 91% zigzag, `best-friend`
90%, `gather` 90%, `i-love-pumpkin` 84%, `miss` 81%, `beckers logo hat` 78%,
`little-romeo` 77%. Kent's own three disagree with each other:
**PRECISION DRON HAT** (154 cols, w 1.58) 16% none / 39% Rc / 14% Z / 29% Re;
**HOTEL FREMONT** (110–117 cols, w 1.39) 8% / 22% / 14% / 38%;
**beckers logo hat** (74 cols, w **2.70**) 7% / 1% / **78% Z** / 11%. Beckers is
not a different philosophy — it is the same law 22 gate applied to a file whose
columns are simply wider.

---

### Entry and exit position

**27. Pros do not enter where it is nearest. They enter at the FREE END of the
stroke and sew INTO the junction.** Scored on an identical decision subset:

| rule, against what the digitiser actually did | n=291 | accuracy (95% Wilson) |
|---|---|---|
| structural — "enter at the free cap" | 248/291 | **85.2% [81–89]** |
| stage 7 — "enter at the cap nearer the previous exit" | 123/291 | **42.3% [37–48]** |

Agreement matrix: structural-hit/greedy-hit 29.2%, **structural-hit/greedy-miss
56.0%**, structural-miss/greedy-hit 13.1%, both-miss 1.7%. **In 56% of
decisions the digitiser walked past the near end of the column to start at its
free cap.** On the fair-coin form — columns with exactly one free cap, so the
mix of available ends cancels — the start lands on the free cap
**289/335 = 86.3% [82–90]**. Cap ends are **2.5× more likely to be the start
than the finish** (34.9% of starts vs 13.9% of finishes, against 24.4% of all
ends). Cleanest render for eyeball confirmation: `think-positive.dst` — every
leaf enters at its outer tip and exits into the stem junction, every letter
stroke enters at its bottom free cap.
*Confidence: high, and falsification-tested. Same corpus, three modes,
identical 1,039 columns detected in each: forward cap-start **87.9%**, reversed
**12.1%** (exact complement), coin-flip **48.3%** (lands on the null). The
classifier is direction-agnostic; the 86% is reading real sew direction, not
its own detector. 20/20 fixture claims pass.*

**28. The end-class preference order is cap > tee > corner ≈ butt.** Each cell
below has a clean 50% null:

```
cap    vs butt    n=125  cap    90.4%
cap    vs corner  n=100  cap    88.0%
cap    vs tee     n=110  cap    80.0%
tee    vs butt    n=124  tee    71.8%
tee    vs corner  n=192  tee    64.6%
corner vs butt    n=108  corner 51.9%   <- no preference
```

Corollary for exits: `butt` and `corner` ends are **~2.2× more likely to be the
exit than the entry** (butt ×0.72 start-enrichment, corner ×0.78). At element
level (multi-column glyphs, n=88) the entry sits at extremity score med **0.71**
against a random-landing null of 0.50, med **0.20 of the element diameter** from
its nearest tip, and the first column of a glyph starts at **cap 64%**, tee 16%,
butt 10%, corner 10%.
*Confidence: high on cap-vs-anything; high on the corner≈butt tie being a real
null rather than thin data (n=108).*

**29. A structural entry is worth up to ~10 mm of extra travel, and no more.**
Extra travel paid to reach the structural cap instead of the near one (n=163):
med **5.7 mm**, p10 2.2, p25 3.7, p75 12.0, p90 22.5, max 100. **39.3% ≤5 mm,
71.8% ≤10 mm, 87.7% ≤20 mm.** Beyond ~20 mm they mostly stop paying.
*Confidence: medium on the absolute millimetres. Limit: "previous exit" is the
previous DETECTED column's exit, not the true needle position — fills and
running work between columns are invisible to this instrument. The head-to-head
in law 27 only needs the ordering of two distances and is robust to it; these
mm figures are an upper bound.*

**30. To enter a stroke's interior, pros CUT the stroke at the crossing.** A
satin column cannot start mid-column, so the real finding is the workaround:
**194 of 884 logical strokes (21.9%) are splits** — two collinear columns
butting end to end, split-point gap med 0.85 mm, collinearity |cos| med 0.967.
Of 275 butt pairs, **79.3% sit at a crossing with another column** (geometry
forced the cut) and 20.7% are pure sew-order cuts in open space. The cut lands
at **0.30 of the merged stroke's length** (p10 0.09, p90 0.47) — at
intersections, not at midpoints. Topology: chained through the split 46.2%,
**both halves sewn INTO the split 38.9%**, both halves out of it 14.9%. That
38.9% is law 27 re-expressed: given a stroke crossed in the middle, the pro
sews cap→centre, leaves, comes back, and sews the other cap→centre.
*Confidence: high. This is also the trap `study_pro.classify` falls into — it
reads these as two unrelated columns.*

**31. Underlay hand-off has NO law. Report it as a null; do not implement it.**
Of 1,157 columns: underlay enters at the far cap and the satin sews back over
it **45.5%**; underlay enters at the same cap the satin starts from
(out-and-back) **42.5%**; no lead-in 7.6%; plain travel-in 4.3%. A coin flip.
What *is* consistent: the lead-in path lying on the column measures **1.81× the
column length** (p10 0.82, p90 2.02) — there are essentially always ~2 passes
of underlay before a column, but which end hands off is free.
*Confidence: high that this is a null, which is a finding.*

**Where the corpus disagrees on entry.** Stock corpus **89.1% [85–92]**
structural against Kent's commissioned files **62.8% [48–76]** — CIs do not
overlap. Treat it as suggestive, not settled: `HOTEL FREMONT` and
`PRECISION DRON HAT` are the two densest files in the corpus (2.49 and 2.80
columns/cm² against a corpus median ~0.25), and Fremont has only **7.3%
free-cap ends** because in a packed badge lockup nearly every column end has an
unrelated neighbour inside the classifier's `max(2.0 mm, 1.1 × width)` radius
and gets labelled `tee`. Their fair-coin subsets are n=8–14. Named extremes —
highest (n≥5): `enjoy-coffee` 100% (15), `welcome` 100% (8), `breathe-feathers`
100% (8), `miss` 100% (7), `little-romeo` 100% (6), `jolly-af` 100% (5),
`think-positive` 95.5% (22), `autumn-time` 92.9% (14), `hope-christmas-
inscription` 90.9% (22). Lowest: `HOTEL FREMONT  (2)` 30.0% (10),
`HOTEL FREMONT ` 37.5% (8), `future-mrs` 50.0% (6), **`be-joy` 62.5% (16) — the
only stock-corpus counterexample with usable n**, `PRECISION DRON HAT` 76.9%
(13).

---

### Colour sequencing

Only **2 of 39 files carry thread identity** (PES companions). Every colour
claim below rests on n=2 or on geometry that does not need colour. Said once,
plainly, so no number here gets quoted without it.

**32. Sew order is background-to-foreground. It is not largest-first and it is
not centre-out.** Of 139 overlapping ordered block pairs, **107 (77%) put the
smaller block later** — background field down first, detail on top. Against
that, Spearman ρ against sew index across 17 designs with ≥3 blocks:
ink area med **−0.14** (8 large-first / 4 small-first / 5 flat), stitch count
med −0.14, radial distance from centre med **−0.50** (**10 outside-in / 2
centre-out**). Large-to-small is not a law; centre-out is actively backwards.
*Confidence: high on layering (77% of 139 pairs, and it needs no colour data);
high on the refutation of centre-out. Limit: "ink" is a 1 mm raster footprint —
a hull-based version made a wreath read as a solid disc and had to be replaced.*

**33. A design sweeps once, in one direction — but the direction belongs to the
design, not to the craft.** Directional sweep ρ med **0.83** (p10 0.60, p90
1.00), **15 of 17** designs ≥0.60. The directions: leftward 3, rightward 3,
upward 3, down-left 2, downward 2, and so on. **A sweep is a law. A particular
sweep is not.**
*Confidence: high.*

**34. Threads repeat, and the engine cannot express it.** Both files with
thread identity return to threads already used:
- **beckers logo hat** — 5 blocks, **2 distinct threads**, 3 returns:
  `gray black gray black gray`, luminance ρ **0.00**.
- **HOTEL FREMONT** — 9 blocks, **4 distinct threads**, 5 returns:
  `white black brown white pink black white black brown`, luminance ρ
  **−0.225** (mildly *dark*-to-light).

**~56–60% of colour stops are returns to a thread already in the design**, for
two visible reasons. *Registration* (beckers): black shadow then grey face, and
the arched word deliberately split into "BEC" then "KER" so each shadow+face
pair sews while the fabric is still aligned — that split bought 2 extra colour
changes on purpose. *Layer stack* (Fremont): white returns 3× (badge field →
centre mark → banner fill), black 3× (border → banner outline → lettering),
each at a different z-level, with return gaps of 1–5 blocks. The seam census
confirms the thread accounting independently from the PES sibling: Fremont's
9 blocks are 4 threads (White ×3, Black ×3, Light Brown ×2, Flesh Pink),
beckers' 5 are 2 (Gray ×3, Black ×2).

**Any global lightness sort is contradicted where it can be measured, and more
importantly it CANNOT EXPRESS a returning thread** — it would collapse
Fremont's 9 blocks into 4 and destroy the stack. The engine's one-block-per-
thread architecture (`stage5_overlap.PlannedRegion.sew_index`, one index per
thread, order inherited from stage 2's descending pixel weight) has the same
limitation for the same reason. **The missing capability is emitting the same
thread more than once.**
*Confidence: LOW as a statistical claim (n=2). HIGH as a structural claim — the
inability to return to a thread is a property of the engine, not of the sample.*

**35. Lettering is not last. It goes wherever the layer order puts it.**
Detected in 7 designs: **0/7 in the last block; 3/7 in the FIRST**. Relative
position med **0.05**, p90 0.67. The renders explain it: `PRECISION DRON HAT`
is a cap and sews **bottom-to-top**, so its three text lines are blocks **1–3
of 23** — they sit below the badge, which is built after. `HOTEL FREMONT`
builds a badge stack outward, so text lands at **7–8 of 9**. `little-romeo`
reads top-to-bottom, so "LITTLE" is block 0. `chamomile-love` puts "LOVE" at
4 of 7 with detail passes after. **This is the one existing engine sequencing
rule the corpus supports.**
*Confidence: medium-high on the finding, LOW on the count. Lettering detection
needs ≥4 separate glyphs on a common baseline, so connected script is invisible
— it missed "Romeo" in little-romeo, and most of the 13 single-block corpus
designs are script wordmarks. Read "7/39 have lettering" as BLOCK lettering
only. FP rate 2.5% (1/40 randomised negative controls).*

**36. Inside one colour: one sweep, one clean pass, travel-optimal.** Of 139
blocks, 122 measurable: sweep |ρ| med **0.84** (47% strong ≥0.85, 38% loose,
16% none); revisit med **0.09** — **51% are a clean single pass** (<0.10), 34%
some return, 16% heavily interleaved (worst `hello-fall` 0.75,
`breathe-feathers` 0.64, `rose-hand` 0.61). Of the 47 blocks with ≥3
trim-separated elements: travel efficiency med **1.00**, 55% travel-optimal
(≥0.90), 21% near-optimal, 23% loose — with four blocks deliberately *worse
than random* (`bunny-star`, `i-love-pumpkin`, `welcome`, `hello-spring` at
−1.25) that sacrifice travel for something else.

**Largest-first inside a colour is NOT a law**: size ρ med **−0.20** (p10 −0.80,
p90 +0.66) — 47% large-first, 23% small-first, 30% flat. A weak tendency. The
engine's current within-colour behaviour (nearest-neighbour on the geometry,
starting from an extreme of the group so the sweep never doubles back) is what
the corpus does; do not add a size rule on top of it.
*Confidence: high on sweep and single-pass; explicit null on largest-first.
Limit: only 47/139 blocks split into ≥3 objects — these files travel by running
stitch rather than trimming, so the object-level travel and size stats are a
biased subsample of the more separated designs. The travel baseline is a 2-opt
tour, not an exact optimum, so efficiency can exceed 1.*

---

### Seams, overlaps, and outlines over fills

Method: rasterise each colour block's needle-down coverage at 0.10 mm/px
(travel >6 mm dropped, morph-close 0.8 mm), then walk each region's contour
against the other. **Overlap positive, gap negative.** Validated on 48
rectangle pairs at known laps −1.0…+2.0 mm × row spacing 0.20/0.40/0.65 ×
rotation 0°/37°: |err| med **0.05**, max 0.07 mm.

**37. Two fills meet by OVERLAPPING, ~0.4–0.8 mm — and the allowance wanders.**
Purest set (both regions ≥150 mm², frontier ≥20 mm, no satin column on the
seam; n=9 over 6 files): offset per seam med **+0.37 mm** (p10 −0.15,
p90 +1.13); per sample over 1,956 pooled frontier samples med **+0.45**
(p10 −0.75, p90 +2.05). Verdicts **8 OVERLAP / 0 BUTT / 1 GAP**; pooled samples
65% lap / 15% butt / 20% gap. Relaxing to all fill-fill frontiers ≥20 mm
(n=19, includes border-covered ones): med **+0.81**, pooled 3,601 samples
76/12/11. Sorted: summer-umbrella 0-3 −0.15 · chamomile-love 3-6 +0.15 ·
snowman 0-2 +0.17 · teddy-bear 0-3 +0.25 · bunny-star 1-2 +0.37 · snowman 0-1
+0.55 · **snowman 1-2 +0.81 over a 395 mm frontier** · chamomile-love 3-5 +0.97
· **corgi 1-2 +1.13 over 222 mm**. Biggest overall: PRECISION DRON blk4-8
**+1.63** over 184 mm, beckers blk1-3 +1.85. Visually confirmed —
`snowman-christmas-colors` blk1-2 is a striped scarf and every stripe boundary
shows a distinct overlap band.

**The spread is as much the story as the median: within ONE seam the offset
varies by 2.60 mm p90−p10** (p10 0.88, p90 3.58). Pros do not hold a constant
seam allowance. They overlap generously and let it wander.
*Confidence: high on the sign and the scale; medium on the exact median.
Limit: instrument noise on real files is ~0.2 mm, not the 0.05 of fixtures
(|A→B − B→A| med 0.18, p90 0.84 across 143 frontiers; 0.32 on the pure subset).
Region TYPING is parameter-sensitive and region VALUES are not — across
RES 0.05/0.10, close 0.5/0.8/1.2, travel 4/6, the fill-fill median ranged
+0.80…+1.05 mm while the fill-fill COUNT ranged 23–40. Trust the numbers, not
the counts.*

**38. There is no evidence of a deliberate bare-fabric sliver.** Of the 9 clean
fill-to-fill boundaries, **1 reads as a gap** — `summer-umbrella` blk0-3 at
−0.15 mm — and the mask render shows an *incidental* adjacency (a flower petal
grazing the umbrella canopy), not a designed edge. 21 of 97 abut frontiers
≥20 mm read as gaps, but **17 of those 21 are stroke/lettering pairs**:
`autumn-time` 0-1 (2.67 mm), `hello-spring` 0-1 (2.33), `PRECISION DRON` 2-3
(1.89) and 1-2 (1.55), `breathe-feathers` 0-1 (0.59 over 295 mm),
`summer-umbrella` 2-3 (1.37 over 241 mm) — ordinary negative space between
separate elements.
*Confidence: this is a NULL, and a limited one. The instrument cannot
distinguish "designed sliver" from "two elements that simply do not touch." No
case in the corpus demands the former reading, which is the most that can
honestly be said.*

**39. A seam is usually NOT outlined.** Fill-fill frontiers ≥20 mm with ≥50%
outline coverage: **6/19 (32%)**, median coverage 0.03. Any length: 11/31 (35%),
median 0.14. All abut frontiers ≥20 mm: 40/97 (41%), median 0.02. When an
outline IS present its true width is med **1.70 mm** (p10 1.29, p90 3.21), and
in **63/78** cases it belongs to one of the two colours rather than a third.
Zooming out: of 67 area-fill regions across 39 files, only **11 (16%)** carry a
covering satin column and 12 (18%) have any column tracking their edge.
**This supports keeping `cfg.border` off by default** — the round-2 reasoning
was right, and now it has a second, independent instrument behind it.
*Confidence: high.*

**40. A covering border sits CENTRED on the fill edge. `BORDER_SEAM_OFFSET_MM
= 0.0` is now MEASURED, not a boundary condition.** Round two's `border_pro`
over-a-fill detector fired zero times because it required a `classify()`-
labelled fill run earlier in the same colour block. Region-level masks with no
`classify()`, no run ordering and no same-block rule find **70 tracking columns
of 633, of which 41 actually cover an edge**. Covering subset (n=41, 7 files):
centreline offset vs the fill edge (inward positive) med **+0.05 mm**
(p10 −0.45, p90 +0.20); offset/half-width +0.04; share of the column lying on
the fill 0.59. Restricted to columns ≥20 mm long (n=25, the trustworthy
subset): offset med **+0.00** (p10 −0.47, p90 +0.20). Per file: PRECISION DRON
+0.15 (n=20) · beckers +0.10 (5) · i-love-pets +0.05 (5) · christmas-sleigh
−0.15 (7) · HOTEL FREMONT −0.15 (2) · creative +0.40 · hello-summer +0.75.
And the ordering is unanimous: **41/41 sewn AFTER the fill they cover, 0/41
before.**
*Confidence: high on the number, high on the ordering. Limit: when the covering
border belongs to one of the two blocks, a raw measure reads +0.75 against a
truth of 0.00 (half the border body) — the numbers above are the "core"
re-measure with the border cut out of its own block's mask, which only works
when the column is detected at ≥30% frontier coverage.*

**41. Amendment to laws 11 and 12: an edge-covering border is WIDER than a
lettering column, and it sews at the SAME density.** Law 11 put border width at
1.40 mm — but that population was **closed loops, mostly round letters**, as
`border_pro`'s own header admits. Real edge-covering borders measure
**1.66 mm med** (p90 3.83), and **2.39 mm** over the trustworthy ≥20 mm subset,
and they are file-dependent (christmas-sleigh 1.55 → i-love-pets 4.53). Law 12
put border density at 0.45 mm, "looser than lettering because it rides over
coverage." Measured on real covering borders: **0.40 mm** (p10 0.36, p90 0.42)
— **identical to lettering columns. There is no density relaxation.**
*Confidence: medium-high on width (n=41 / n=25, file-dependent, so a single
value is a compromise); high on density (tight p10–p90, and it agrees with
law 4, law 21, and the underlay census's same-rail figure).*

A separate population of **29 tracking-but-not-covering columns** is decorative
concentric striping, not edge covering: 19 sit wholly outside the fill (offset
med −1.42 mm, width 1.38) and 10 wholly inside (+1.21 mm, width 1.59) —
Fremont's four concentric badge rings, christmas-sleigh, PRECISION DRON. Do not
let a future detector merge these two populations.

**42. The base colour runs CONTINUOUS under the top colour. Pros do not knock
out.** Across 49 stacked pairs, the share of the upper region backed by the
lower is med **0.77** (fill-fill 0.71, fill-lettering 0.82, lettering-lettering
0.71). Genuine partial cases are three: `chamomile-love` blk5-6 (0.11) and
blk2-6 (0.13), `creative` blk0-1 (0.22).
*Confidence: high. Note the interaction with the coverage budget: a continuous
base plus a top layer is exactly the "two full-density fills stacked" case
`COVERAGE_WARN_UNITS` reasons about, and law 19's density change moves both.*

---

### Where the corpus does NOT vote together

A law is only a law when the corpus votes together. These did not, and are
recorded as splits rather than promoted:

- **Angle sharing between neighbouring same-colour fills** — solid-fill designs
  hold ±3–10° (`rose-hand`, `summer-umbrella`, `teddy-bear` 2.1°,
  `bunny-star` 3.0°); sketch designs vary on purpose (`corgi` up to 49.7°,
  `cat-and-girl` 25–29°). Overall med difference 22.8°, only 24% within 10°.
- **Sweep direction** — 15/17 designs sweep, in six different directions.
- **Largest-first within a colour** — 47% / 23% / 30%. Real, weak, not a law.
- **Underlay hand-off end** — 45.5% / 42.5%. A coin.
- **Corner vs butt as an entry** — 51.9% over n=108. No preference.
- **Zigzag underlay as a house style** — `enjoy-moment-script` 0%, `sweet-heart`
  91%. (Partly explained by law 22's width gate; not fully.)
- **Per-file fill density** — 0.178 to 0.290 mm across 26 files, a spread far
  wider than any within-file effect.
- **Zigzag-under-fill angle** — bimodal, p10 1.1° and p90 86°. Parallel or
  perpendicular, never a compromise.
- **Kent vs stock on structural entry** — 62.8% vs 89.1%, CIs disjoint, but
  confounded by column density and the classifier's end-radius. Suggestive.

---

## Engine mapping (round 3)

**Gate key.** *desk-safe* — verifiable from the emitted file and renders; no
thread-on-fabric question. *sew-out-gated* — changes the thread laid down
(density, coverage, count) and needs Kent's sew-out. *not built* — no
mechanism exists.

| Law | Stage / constant | Change | Gate |
|---|---|---|---|
| 15 | `stage6_fill.principal_angle_deg` | keep per-region PCA; the literal `45.0` is only a degenerate-polygon fallback and stays | desk-safe, no change |
| 16 | `stage6_fill` angle selection | retire any notion of a canonical default; PCA long-axis already matches the dominant tendency (67% on elongated regions) | desk-safe, no change |
| 15/16 | new: same-colour angle snap | snap neighbouring same-colour regions to a shared angle for solid-fill work; leave sketch work per-region | desk-safe |
| 17 | crosshatch second pass | perpendicular second pass for a sketch/decorative tier | not built |
| 18 | `FILL_ROW_MM`, `SATIN_SPACING_MM` being flat | **flat is correct — confirmed, do not add size grading** | no change |
| 19 | `machine.FILL_ROW_MM` 0.40 → **0.20** | doubles fill stitch count; also doubles the preflight reading — at `COVERAGE_THREAD_W_MM = 0.40` a single 0.20 mm fill measures **2.00 coverage units**, so any second layer crosses `COVERAGE_WARN_UNITS` 2.5 and a third hits `COVERAGE_BLOCK_UNITS`. Land the two together. | **sew-out-gated** |
| 19 | `machine.py:39-40` comment | delete the interleave hedge; it is refuted | desk-safe |
| 20 | `FILL_STITCH_MM` 3.0 → ceiling **4.0** + even division per row in `_row_points` | changes the model, not just the number; even division is itself a stagger source, so re-check against `FILL_STAGGERS` | desk-safe (confirm on sew-out) |
| 21 | `SATIN_SPACING_MM` 0.4 | **no change.** Engine same-rail is 0.40 (stations at 0.40, constant A/B rail order); corpus is 0.38. The "engine satin is 2× sparse" claim is wrong. | no change |
| 21 | satin advance above 4.5 mm | ~15% tighter past 4.5 mm; `SATIN_MAX_WIDTH_MM` is 5.0, so the effect is ~0 inside our range | no change |
| 22 | `SATIN_ZIGZAG_ABOVE_MM` 2.5 → **2.0** | half a bucket; law 2's own crossover was "between 2.0 and 2.5" | desk-safe |
| 22 | new: length gate in `stage6_satin` | columns shorter than ~6 mm take an edge walk, never a zigzag, at any width | desk-safe |
| 23 | `machine.SATIN_ZIGZAG_PITCH_MM` (new constant, 1.45) wired into `stage6_satin._stroke_underlay` in place of `UNDERLAY_ZIGZAG_MM` (left at 2.0 for fill's own lattice underlay, which still reads it) | pitch is width-independent in the corpus | **shipped 2026-08-05** |
| 23 | `_stroke_underlay` narrowing 0.3 → **0.09** | gives 0.82 × column width (inset 0.25–0.40/side) instead of today's 0.40 × | **shipped 2026-08-05** |
| 24 | walk-under-zigzag pairing | **already correct** — `_stroke_underlay` always emits the spine walk and adds the zigzag on top | built, confirmed |
| 25 | small lettering | falls out of law 22's gates: at 1.40 mm median width nothing reaches the zigzag threshold | desk-safe, via 22 |
| 26 | `fabrics.fill_underlay` `edge_lattice` → **`edge_run`** | affects pique_knit, jersey_tee; leave the pile presets' heavier styles for their own sew-out | **shipped 2026-08-05** |
| 27–29 | `stage7_sequence` entry choice + `stage6` `start_near` | replace nearest-point with: score each candidate end **cap 3, tee 2, corner 1, butt 1**; proximity is the TIEBREAKER, never the driver; let the higher class win while extra travel ≤ **10 mm**, fall back to proximity past **20 mm** | desk-safe, highest value |
| 27 | exits | finish INTO the junction — prefer butt/corner as the exit | desk-safe |
| 30 | split at crossings | `SPLIT_SATIN_ABOVE_MM` splits by cross WIDTH; the corpus also splits by TOPOLOGY, at crossings, at ~0.30 of stroke length | not built |
| 31 | underlay hand-off | **do not implement.** 45.5/42.5 | null |
| 32 | `stage2_quantize` order + `stage5_overlap.sew_index` | today's descending-pixel-weight order approximates background-first; make it overlap-aware — smaller-of-an-overlapping-pair sews later (77%) | partial |
| 33 | `stage7_sequence` start-at-an-extreme sweep | **already correct** — a single sweep is the law, its direction is not | built, confirmed |
| 34 | `PlannedRegion.sew_index`, one per thread | **the missing capability: emitting one thread more than once.** ~57% of colour stops in Kent's own files are returns. Architectural, not a constant. | not built |
| 35 | absence of a lettering-last rule | **already correct** — lettering goes where the layer order puts it | built, confirmed |
| 36 | `stage7` nearest-neighbour + extreme start | **already correct**; do NOT add largest-first (47/23/30) | built, confirmed |
| 37 | `config.overlap_mm` 0.25 → **0.40** | corpus pure-set median +0.37; today's 0.25 is inside p10–p90 but low | desk-safe (sew-out to confirm) |
| 38 | bare-fabric sliver | nothing to build | null |
| 39 | `cfg.border` default OFF | **confirmed by a second instrument** — 16% of area fills carry a covering column | no change |
| 40 | `BORDER_SEAM_OFFSET_MM` 0.0 | **promote the comment from "UNMEASURED, boundary condition" to measured: +0.00 (n=25) / +0.05 (n=41)**, and record that 41/41 sew after the fill | desk-safe, doc-only |
| 41 | `BORDER_WIDTH_MM` 1.40 → **1.70** for edge-covering borders (2.39 for long ones); keep 1.40 for closed-loop letter outlines | two populations, two numbers | desk-safe |
| 41 | `BORDER_DENSITY_MM` 0.45 → **0.40** | no relaxation; agrees with laws 4 and 21 | desk-safe |
| 42 | `stage5_overlap` knock-out | **already correct** — the engine does not knock out; keep it that way | built, confirmed |

Six laws confirm what is already shipped (18, 21, 24, 33, 35, 36, 39, 42), which
is the cheapest kind of result and worth saying out loud. Two are architectural
(34 thread reuse, 30 topological splits). One — law 19 — is the single largest
change in the round and the one that must not ship without a sew-out.

---

## Known limits of the round-3 instruments

Add to the round-1/2 list; the **parity trap** still applies to every one of
these.

- **The fill-angle window excludes the corpus's real fill density.** The
  `[0.55, 2.0] mm` row-gap gate cannot see a 0.19 mm fill. Laws 15–17 are the
  LIGHT tier. Dense-fill angle is unmeasured, and the lane's "Kent's files
  contain zero tatami" conclusion is refuted by two other lanes on the same
  bytes. Narrow fills are underrepresented for a second reason: the split-satin
  guard rejects rows with ≤2 penetrations under 8 mm along-row, by design.
  Contour/spiral fills would fail the coherence gate; none appeared, so no
  claim is made about them.
- **DST carries no thread colour.** 37 of 39 files. Every colour claim rests on
  the two PES companions; 180 of 202 frontiers in the seam census are
  `thread unknown`, and 5 confirmed same-thread pairs (med −0.53) were excluded
  from the headline seam numbers — the unknown ones may hide more of the same.
- **Satin/fill is ambiguous in 9.0% of bands** (330 of 3,661). A 2-stitch fill
  row and a half-split satin cross are the same geometry. Separated by
  split-point stagger; an unstaggered narrow fill reads as satin. Deliberate
  selftest FAIL (`BLINDSPOT_fill_nostagger`).
- **Entry/exit coverage is 25.8%** — 109,915 of 425,621 stitches lie inside a
  detected satin column. Fills, running-stitch art and underlay are outside
  that instrument entirely, and **5 files yield zero columns** (`best-friend`,
  `birthday-squad`, `cat-and-girl-sketch`, `chamomile-love`, `rose-hand` — the
  sketch/redwork tier). **Nothing in laws 27–31 applies to fill entry.**
  Detection floor: columns under 0.7 mm wide or shorter than 8 zigzag segments
  are invisible. 9 files have a fair-coin subset under 5 columns and their
  per-file percentages are noise.
- **Underlay walk POSITION is tolerance-sensitive under narrow columns.**
  Halving the footprint tolerance moves edge-run 30%→16% and centre-run
  39%→47% in the <1.2 mm bucket. Walk *presence* is robust (none 17%→21%).
  Buckets ≥2 mm move ≤3 pp.
- **Region typing in the seam census is parameter-sensitive; region values are
  not.** Counts ranged 23–40 across parameter sweeps while medians moved
  ≤0.25 mm. Needle-down travel under 6 mm rasterises as coverage (visible as
  hairline spurs in the summer-umbrella render). A wide satin border can type
  as an area fill (`i-love-pets` blk2, a 4.5 mm satin ring). Morphological
  closing rounds concave detail finer than 0.8 mm.
- **Sequencing window resolution** is `W = clamp(n/60, 6, 40)`; interleaving
  finer than ~n/40 stitches is invisible, and this actually hid an interleave on
  a fixture until the fixture was made denser.
- **2 of Kent's 3 commissioned designs are caps**, which carry their own
  bottom-to-top constraint. They are not independent samples of general
  strategy.
- **The probes live in scratchpad, not in the repo.** Unlike `study_pro.py`,
  `census_pro.py` and `border_pro.py`, nothing from round 3 was written into
  `tools/`. Before any of these numbers is argued with, the instrument has to be
  brought into the repo and re-run. Scratchpad root:
  `C:\Users\EE-LT-~1\AppData\Local\Temp\claude\C--Users-EE-LT-11030\b845a108-6467-4184-b54f-1f888a276bca\scratchpad\`
  — `fill_angle_probe.py` + `fill_angle_agg.py` / `fill_angle_deep.py` /
  `xval.py` (angle); `dens_size.py` + `dsz_*.py` (density, `--selftest`);
  `colorseq_run2\probe.py` (sequencing, `--selftest`); `entryexit\geo.py` +
  `fixtures.py` / `validate.py` / `reverse_test.py` / `probe2-4.py` /
  `final.py` (entry/exit, plus renders under `entryexit\render\`);
  `embphase.py` + `fixture_test.py` / `underlay_census.py` (underlay);
  `seam\seam_pro.py` + `dig2.py` / `overlay.py` / `blocks.py` / `recon.py`
  (seams, `--validate`).

---

## Action note (2026-08-01, main session) — the fill-density claim is NOT yet acted on

Law 19 measures professional fill row spacing at **~0.19–0.20 mm in a single
pass**. Our `machine.FILL_ROW_MM` is **0.40**. Taken at face value that says
every fill we sew is half the professional density, and correcting it would
roughly double the stitch count of every filled design in the product.

A change that large does not ship on a document, however well instrumented.
Three things must line up first, and two of them are already in motion:

1. **The definition must be ours.** The instrument defines fill gap as the
   perpendicular spacing between traverses consecutive *in sew order within one
   needle-down run*. Our `FILL_ROW_MM` is the spacing between adjacent rows as
   generated. Those are the same number only if the corpus fills are simple
   boustrophedon. If a pro fill interleaves — sews every other row and returns
   — the instrument reads half the true row pitch, and 0.19 is really 0.38,
   which is our 0.40 to within house-style spread. Law 19 asserts single-pass
   and closes the interleave question; that assertion is exactly what must be
   re-derived independently before the constant moves.
2. **The coverage instrument already disagrees, usefully.** Preflight's Law 27
   map reads a 0.40 mm fill as **1.000 coverage units** — one full covering
   layer, derived from thread width alone. A 0.19 mm fill reads ~2.1 units.
   Sustained 2.1-unit coverage over a large area is what the physics playbook
   calls a board (law 27's own warn line is 2.5, block 3.5). Either pro fills
   genuinely sit near the top of the density budget, or the two instruments
   are measuring different things. Reconciling them is the work.
3. **The sew-out card already tests this exact question.** Block 2 of
   `EMBBOT_SEWOUT_CARD.dst` sews three 15×15 mm squares: 0.40 single pass,
   0.20 single pass, and 0.40 two-pass interleaved at a 0.20 offset. That card
   was built before this law existed and it happens to be the decisive
   experiment for it. Kent's eye on those three squares settles in one hooping
   what no amount of DST parsing can.

Until then `FILL_ROW_MM` stays at 0.40 and this law is recorded, not applied.
