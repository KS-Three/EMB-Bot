# How a satin column's width changes when the design is resized — the pro's files, and what the vendors say (2026-10-01)

Question (Kent, for the manual lane's spine-plus-width column, spec
`2026-09-30-manual-digitizing-gaps-design.md` §6 and rulings 2, 5, 9): when a
design is resized, how should a hand-authored satin column's width change? His
hypothesis: *not proportionally — "just because size doubles doesn't necessarily
mean width doubles."* This note measures what one professional digitizer actually
did with the same artwork at several sizes, reads what the digitizing software
and the trade publish, and lays the candidate models out against both. It
recommends nothing; the stored model is the reader's call.

**Summary, five lines.**

1. **Measured, in the pro's own files, the sewn width follows the design size but
   under-shoots it:** a 1.251× design carries 1.195× columns (median over 341
   matched locations, 3,050 / 3,778 crosses), a 1.332× design 1.265×, and the
   lettering of a 1.97× jacket back 1.778× — an effective exponent **k ≈ 0.80–0.85**
   in width ∝ size^k, with an inter-quartile spread of about ±0.10.
2. **The best single reading is not a power law: the rails scale 1:1 and a fixed
   ≈0.3–0.55 mm rides on top unchanged.** k rises with column width (0.73 → 0.77 →
   0.91 across width terciles) and the non-scaling part is constant in millimetres
   (regression slope 0.05 mm/mm, intercept 0.38), which is what a millimetre
   pull-compensation setting — Wilcom publishes 0.20–0.40 mm by fabric — does to an
   object that is otherwise scaled. "Width never changes" is refuted on every pair
   (bias +0.57 to +1.04 mm, RMS about 3× worse than either scaling model); "width
   scales 1:1" is wrong by only 0.12–0.22 mm.
3. **Strength:** one digitizer; two artworks with size-only pairs (Becker ×1.25 and
   ×1.33, a Gaulke lettering block ×1.97) and seven more cap/flat/knit pairs that
   agree in direction; three same-size controls read 1.000 exactly and the fourth
   (partly re-digitized) 1.000 at the median. Everything in Part 2 is documentation,
   not cloth — and nothing here clears ROADMAP gate 1.
4. **No clamp was observed anywhere between 0.67 and 11.8 mm.** In eleven pairs not
   one location changed stitch type (satin → split / fill / run) at the other size;
   raw unsplit crosses reach 9.1 mm (Becker hat, 101.9 mm) and 11.8 mm (roofing hat,
   against DST's 12.1 mm record limit). The vendors' answer to a column that grows
   too wide is Auto Split (more penetrations), not a narrower column; only Melco
   documents a min/max column-width clamp as a property.
5. **The one number:** at 1.25× the columns are 1.195× — equivalently, about half a
   millimetre of every column's sewn width does not scale with the design.

Verification legend, as `docs/paired-ground-truth-sourcing-2026-09-28.md` uses it:
**[M]** measured this session by script · **[V]** read this session from the cited
primary source (raw HTML fetched and quoted) · **[S]** read through a summarising
fetch, not the raw page · **[I]** inferred · **[U]** not verified; what would settle
it is named.

---

## Part 1 — Measured: one professional's files of one artwork at several sizes

### 1.1 What exists to compare

`Embroidery Files.zip` at the repo root (committed, public) holds the commercial
digitizer's DST/PES/EMB deliveries; `digitizer/testdata/reference/` holds the four
Becker variants under lower-case names, **byte-identical** (md5) to the zip members
[M]. The same files also sit, gitignored, in the main checkout's `scratch_kent/`;
nothing there was needed. `scratch_corpus/` (37 third-party DSTs) has no
same-artwork pairs and was not used. The Bridge Bar hat/LC pair that
`tools/pro_parity/prep_both.py` indexes lives on the Drive only and is not in the
zip; not measured.

Same-artwork sets, sizes read off the needle-down bounding box [M]:

| artwork (zip folder) | file | W × H mm | stitches | satin spacing p50 |
|---|---|---:|---:|---:|
| Becker Marine | `beckers logo LC 2 A.DST` (= `becker_chest_small_…_lc_2_a.dst`) | 76.5 × 46.8 | 8,694 | 0.361 |
| | `beckers logo hat 2 A.DST` (= `becker_hat_small_…_hat_2_a.dst`) | 76.5 × 46.8 | 8,694 | 0.361 |
| | `beckers logolc.DST` (= `becker_hat_polo_large_…_logolc.dst`) | 95.7 × 58.3 | 11,274 | 0.361 |
| | `beckers logo hat.DST` (= `becker_hat_polo_large_…_logo_hat.dst`) | 101.9 × 62.1 | 12,356 | 0.361 |
| | `beckers logo hat Smaller.DST` (= `…_hat_smaller.dst`) | 101.9 × 62.1 | 12,562 | 0.400 |
| | `To a T:Becker Beanies/beckers beanie.DST` | 79.8 × 50.1 | 11,411 | 0.361 |
| C Gaulke Plowing | `C GOLKE LC.DST` | 89.4 × 47.8 | 9,255 | 0.400 |
| | `C GOLKE hat.DST` | 108.0 × 52.3 | 11,271 | 0.400 |
| | `C GOLKE hat beanie.DST` | 110.5 × 54.9 | 14,576 | 0.400 |
| | `GOLKE LOGO JB 1.DST` (jacket back) | 178.5 × 95.9 | 32,665 | 0.400 |
| Gaulke Roofing | `c golke logo LC.DST` | 95.2 × 42.1 | 5,151 | 0.400 |
| | `c golke logo hat.DST` | 114.2 × 48.5 | 6,138 | 0.400 |
| | `c golke logo HAT BEANI.DST` | 93.8 × 43.4 | 7,051 | 0.400 |
| MFAB | `mf4b logo lc.DST` / `mf4b logo hat.DST` | 96.7 × 36.9 / 104.9 × 40.2 | 15,786 / 17,568 | 0.400 |
| Proseal | `PROSEALHAT BEANI.DST` / `PROSEALHAT.DST` | 75.0 × 55.4 / 85.9 × 63.3 | 7,117 / 5,894 | 0.400 |
| To a T Machine | `Machine beanie E (1).DST` / `Machine LC.DST` / `Machine HAT.DST` | 81.0 × 55.8 / 89.5 × 61.6 / 89.5 × 61.6 | 14,817 / 13,875 / 13,886 | 0.316 / 0.400 / 0.400 |
| Hotel Fremont | `HOTEL FREMONT .DST` (patch) / `HOTEL FREMONT HAT.DST` | 92.5 × 50.8 / 92.6 × 50.9 | 15,458 / 17,067 | 0.400 |

Three things the table alone settles [M]:

- **`beckers logo hat Smaller.DST` is not smaller.** It is the 101.9 mm hat with
  spacing 0.40 instead of 0.361 — a density variant, usable as a same-size control.
- **The Becker small LC and small hat are the same stitches** (identical cross
  statistics; they differ in colour sequence). The Fremont patch and hat are the
  same size, and so are Machine LC and HAT. These are the controls.
- **Satin spacing is a per-object constant at every size** (0.361 or 0.400, not
  graded by width — checked by width bin: 0.36–0.40 in every bin from 1 mm up with
  n ≥ 100; only the 0.5–1 mm bin, which is end and corner crosses, reads 0.45–0.67),
  and the stitch count grows with size (Becker 8,694 → 11,274 → 12,356). Stitches were
  regenerated from objects, not scaled as a stitch file. The deliveries include
  `.EMB` (Wilcom's native object format), so Wilcom's documentation in Part 2 is the
  directly relevant vendor.

Every layout was rendered and looked at before anything was matched
(`.superpowers/research-satin-width/out/sheet_*.jpg`, scratch): Becker is the same
layout in all five files (the beanie adds a knockdown ground); the two Gaulke logos
keep their lettering layout across LC/hat/beanie; **the jacket back's picture was
re-digitized** (the truck is redrawn with far more detail — colour changes 6 → 20,
trims 50 → 89), so only its lettering block is a size pair; Proseal's hat was
re-digitized with a different construction of the word. Beanies carry a tatami
knockdown under everything, which is why registration below is done on satin
centrelines rather than on the bounding box.

### 1.2 Instrument

Widths are read with the repo's existing definition, `tools/satin_columns._crosses`
— the one that produced *"the pro's MARINE p99 6.2"* (`machine.py`,
`SATIN_WIDE_COLUMN_MAX_MM`; `docs/scope-history.md` 2026-09-09): three consecutive
penetrations are a cross when the apex sits ≥ 0.1 mm off the chord of its
neighbours, both legs are 0.4–12 mm, and the offsets alternate side for ≥ 3 crosses.
**The apex offset IS the rail-to-rail width** (not the stitch length). A thin
wrapper returns, per kept cross, the width, the chord (= same-rail advance = the
satin spacing), the cross centre and its direction; its widths were asserted equal
to `_crosses`' output on every synthetic case. Zigzag underlay is excluded by
keeping only crosses whose chord is ≤ 1.0 mm (top satin advances 0.36–0.40; zigzag
underlay advances more) [M].

Validation [M]: synthetic raw zigzags of 0.8, 2.0, 3.0, 5.0, 6.5 mm read 0.800,
2.000, 3.000, 5.000, 6.500 at chord 0.400; a curved running stitch reads 0 crosses;
a split column (k = 3, staggered) reads **0** crosses on the repo instrument and the
true width in a merged mode that first removes pass-through penetrations (turn
< 25°) — that mode is used only to look for split satin / tatami rows, never for
the width numbers. Against the repo's own records: `tools/satin_columns.py --file`
on `becker_hat_polo_large_beckers_logolc.dst` prints median 2.52 (its docstring's
number) and the small LC 2.09; the top-only p99 of that file is 6.22 against the
recorded "p99 6.2"; design 95.7 × 58.3 as recorded.

**Matching.** Two files are registered on their satin **centrelines** (cross
centres — a width-free quantity): an anisotropic scale + translation fitted by
trimmed ICP from the cross-cloud bounding boxes. The registration scale `s` is the
design-size ratio used throughout (it agrees with the stitch bounding box to 0.3 %
wherever no knockdown ground is present). Then, in the larger file's frame, 2 mm
cells: a cell matches when both files have ≥ 4 top crosses in it and their median
cross directions agree within 20°, and the cell's width is the median of its
crosses. Independently, **column runs** (one sustained alternation inside one
needle-down pass, ≥ 10 crosses) are matched one-to-one on centroid (≤ 1.5 mm or 15 %
of length), length (within 0.7–1.43×) and direction (≤ 15°); a run's width is its
median. Where registration is anisotropic (sx ≠ sy by > 2 %) k and c are also
computed with each cell's own scale along its cross direction.

**Models scored per matched location** (A = smaller file, B = larger, s = size
ratio): proportional wB = s·wA; constant wB = wA; outline-scales-plus-fixed
wB = s·(wA − c) + c with c the median of (s·wA − wB)/(s − 1); power wB = wA·s^k with
k = ln(wB/wA)/ln s.

**Limits.** DST coordinates sit on a 0.1 mm grid, so a run's median width is
quantised to 0.1 mm wherever its rails are axis-aligned; at s ≈ 1.1 a 1.3 mm column
is expected to move by one quantum, so the small-step pairs cannot separate
"unchanged" from "scaled with a fixed part" (§1.5). Cells can mix two columns; the
direction test and the run-level check both guard that. Only raw (unsplit) satin
is in the width statistics; a column the pro had split would be invisible to them —
§1.6 looks for those separately and finds none in the size pairs.

### 1.3 Same garment, two sizes — the clean pairs

| pair (A → B) | s (reg.) | reg. residual | cells (crosses A / B) | **width ratio** p25 / **p50** / p75 | **k** p25 / **p50** / p75 | k by width tercile (thin / mid / wide) | fixed part c (mm) p25 / p50 / p75 | RMS mm: proportional / constant / outline+fixed | runs matched; run ratio p50 (IQR) |
|---|---:|---:|---:|---|---|---|---|---|---|
| Becker LC 76.5 → LC 95.7 | 1.251 | 0.06 mm, 99.5 % < 1 mm | 341 (3,050 / 3,778) | 1.169 / **1.195** / 1.225 | 0.70 / **0.80** / 0.91 | 0.73 (0.75–2.0 mm) / 0.77 (2.0–3.3) / 0.91 (3.4–5.7) | 0.31 / 0.51 / 0.80 | 0.267 / 0.662 / **0.240** | 39 of 45; 1.206 (1.187–1.236), k 0.84 |
| Becker hat 76.5 → hat 101.9 | 1.332 | 0.06 mm, 99.5 % | 369 (3,045 / 3,958) | 1.226 / **1.265** / 1.297 | 0.71 / **0.82** / 0.91 | 0.72 / 0.76 / 0.90 | 0.39 / 0.54 / 0.70 | 0.281 / 0.846 / **0.230** | 35 of 45; 1.278 (1.254–1.300), k 0.85 |
| Gaulke-plowing LC 89.4 → jacket back 178.5, **lettering block only** | 1.974 | 0.21 mm, 88 % | 242 (1,434 / 2,979) | 1.720 / **1.778** / 1.846 | 0.80 / **0.85** / 0.90 | 0.90 (0.5–1.2 mm) / 0.84 (1.2–1.33) / 0.85 (1.34–2.4) | 0.17 / 0.27 / 0.37 | 0.434 / 1.108 / **0.376** | 50 of 61; 1.778 (1.755–1.833), k 0.85 |

Mean bias of the proportional model (wB − s·wA): −0.118, −0.162, −0.222 mm; of the
constant model: +0.567, +0.745, +1.041 mm [M].

Per-column rows, Becker LC small → LC large (run medians, DST grid 0.1 mm; n = crosses) [M]:

| column (run) | 76.5 mm | 95.7 mm | ratio | n |
|---|---:|---:|---:|---:|
| the BECKER outline border, longest run | 1.90 | 2.21 | 1.163 | 480 / 600 |
| border, next run | 1.97 | 2.34 | 1.188 | 230 / 285 |
| letter detail | 2.50 | 3.00 | 1.200 | 104 / 130 |
| letter detail | 3.07 | 3.61 | 1.176 | 102 / 127 |
| letter detail | 3.40 | 4.53 | 1.332 | 119 / 141 |
| MARINE stems (ten runs) | 4.00–4.14 | 4.80–5.04 | 1.19–1.25 | 42–84 each |
| widest run | 5.23 | 6.16 | 1.178 | 14 / 18 |

The same stems in the hat pair (s 1.332): 4.00 → 5.10–5.24, ×1.28–1.31. Under
"outline scales + fixed c", the stems' c reads 0.25–0.4 mm; under a power law their
k is 0.9. The thin border's k is 0.68–0.77 either way.

**Three sizes at once** (76.5, 95.7, 101.9; 358 locations present in all three;
w fitted linearly in relative size, w = g·size + c) [M]: the intercept c — the
part that does not scale — is **0.56 mm** (IQR 0.39–0.71) and does **not** grow with
the column: regressing c on the small-file width gives c = 0.051·w + 0.375 (a power
law k = 0.8 would put the slope near 0.2 and the intercept near 0; a fixed-mm
addition puts the slope at 0). Predicting the 101.9 mm widths from the 76.5 → 95.7
step alone: proportional bias −0.170, RMS 0.273; power k = 0.80 bias +0.036, RMS
0.224; outline + fixed 0.55 mm bias +0.012, RMS 0.214; constant bias +0.733, RMS
0.832. Over a 1.25–1.33× range the two sub-proportional readings are
indistinguishable; the three-size intercept and the width-tercile trend both point
at the fixed-millimetre one.

### 1.4 Cap vs flat, and knit — same artwork, different garment AND size

These pairs mix two causes. The cap and beanie versions carry the same construction
as the flat ones here, but the digitizer visibly edits per garment (Machine beanie:
spacing 0.316 against 0.400 on LC, a knockdown ground, and the hexagon border is
**2.31 mm on the 81 mm beanie against 2.10 mm on the 89.5 mm LC** — narrower on the
larger design, ×0.909 over 1,355 / 1,269 crosses). Read them as corroboration of
direction, not as the law [M]:

| pair (A → B) | s | sx / sy | cells | width ratio p50 (IQR) | k p50 (IQR) | c mm p50 | note |
|---|---:|---|---:|---|---|---:|---|
| Becker LC 95.7 → hat 101.9 | 1.065 | 1.064 / 1.066 | 379 | 1.055 (1.040–1.062) | 0.86 (0.62–0.96) | 0.47 | 83 % of cells within 4 % of s; no cap-specific width change detectable |
| Becker beanie 79.8 → LC 95.7 | 1.252 | 1.255 / 1.248 | 344 | 1.195 (1.164–1.225) | 0.79 (0.68–0.90) | 0.56 | the beanie's artwork is the 76.5 mm one under a knockdown |
| Gaulke-plowing LC 89.4 → hat 108.0 | 1.210 | 1.208 / 1.212 | 284 | 1.182 (1.146–1.231) | 0.88 (0.72–1.09) | 0.19 | |
| Gaulke-roofing LC 95.2 → hat 114.2 | 1.167 | 1.197 / **1.137** | 312 | 1.153 (1.096–1.186) | direction-aware 0.91 (0.62–1.16) | 0.17 | the hat was squashed 5 % in height |
| Gaulke-roofing beanie 93.8 → hat 114.2 | 1.227 | 1.259 / 1.196 | 311 | 1.111 (1.058–1.172) | direction-aware 0.53 (0.28–0.82) | 0.77 | knit columns relatively wider — a garment edit, not size |
| MFAB LC 96.7 → hat 104.9 | 1.089 | 1.087 / 1.091 | 531 | 1.056 (1.020–1.077) | 0.63 (0.23–0.87) | 0.68 | step within one DST quantum for thin columns (§1.5) |
| Proseal beanie 75.0 → hat 85.9 | 1.212 | 1.198 / 1.227 | 250 | 1.151 (1.071–1.182) | direction-aware 0.72 (0.34–0.89) | 0.71 | the hat's word was re-digitized |
| Machine beanie 81.0 → LC 89.5 | 1.112 | 1.112 / 1.112 | 454 | 1.045 (0.914–1.094) | 0.41 (−0.84–0.84) | — | border narrowed on the larger design (above); thin lines §1.5 |

**Controls** — same size, so every ratio must read 1 [M]: Becker LC vs hat at 76.5:
cell ratio p10–p90 1.000–1.000, 295 cells; Machine LC vs HAT 89.5: 1.000–1.000, 460
cells, RMS 0.013 mm; Becker hat 0.361 vs 0.400 spacing: 1.000–1.000, 396 cells;
Fremont patch vs hat (92.5 / 92.6, partly re-digitized): p50 1.000, p75 1.071. The
instrument sees "unchanged" when it is there.

### 1.5 Is there a population whose width does NOT change? Not resolvable at these steps

In the two pairs with a ~1.1× step, some runs read the same width in both files:
MFAB 10 of 52 matched runs move ≤ 0.03 mm in **mean** width (pooled 1.336 →
1.342 mm, 387 crosses), Machine 8 of 49 (0.936 → 0.959 mm, 235 crosses) — thin
decorative lines of 0.85–1.5 mm. But outline-scales-plus-fixed (each pair's own c,
0.47 and 0.55 mm) predicts 1.41 and 0.98 mm for them, proportional 1.45 and 1.04,
and the DST grid is 0.1 mm: MFAB's reading is 0.07 mm under the fixed-part model
and Machine's 0.02 mm under it — both inside one quantum, both on the "unchanged"
side. **A second, width-fixed population is neither established nor excluded by
these two pairs.** In the pairs with a
big enough step to tell there is none: Becker ×1.25, 2 of 341 cells within 3 % of
unchanged; Becker ×1.33, 1 of 369; the jacket-back lettering ×1.97, 1 of 242 [M].
What would settle it: a pair with a ≥ 1.3× step that contains thin outline
objects, or the digitizer's `.EMB` opened in Wilcom to read which objects are
Column C / outline-satin.

### 1.6 The extremes — what the pro does when a column gets wide or thin

- **No stitch-type change in any pair.** For every 2 mm cell holding raw satin in
  one file, the same place in the other file holds raw satin — 11 pairs, 100 % in
  both directions (e.g. Becker LC: 345 / 345 and 356 / 356 cells; jacket back
  lettering 313 / 313 and 392 / 392). Nothing became split satin, tatami, or a run
  because the size changed [M].
- **The wide end scales raw, past every threshold this repo discusses.** Share of
  top crosses over 5.0 / 6.5 / 8.0 mm and the widest raw cross [M]:
  Becker 76.5: 1.2 % / 0.1 % / 0 %, max 7.0 · Becker LC 95.7: 8.6 / 0.8 / 0.1 %, max
  8.5 · Becker hat 101.9: **26.9 / 1.1 / 0.1 %, max 9.1** · roofing LC 95.2: 3.1 /
  2.1 / 1.2 %, max 9.7 · **roofing hat 114.2: 4.2 / 2.5 / 1.8 %, max 11.8** (the
  sun's rays, 9.7 → 11.8 at sx 1.197). Mid-cross penetrations in the 5–12 mm band of
  the roofing files: 1–9 rows against 110–180 raw crosses — the pro did not split
  them, and 11.8 mm is 0.3 mm under the DST record limit (12.1 mm, `machine.py`
  `MAX_STITCH_MM`). This is the "raw crosses to ~7 mm, no comb" house style the
  split-comb note records (`split-comb-2026-09-30.md`), seen to continue to 12.
- **The thin end never approaches a floor in these pairs.** Thinnest sustained
  column (run mean, ≥ 10 crosses) per file: Fremont 0.67–0.69, Proseal 0.79–0.90,
  jacket back 0.83, Machine 0.83–0.86, MFAB 0.90, Gaulke 0.92–1.18, Becker 1.46–1.79
  mm — i.e. this digitizer's thinnest columns sit at 0.7–0.9 mm whatever the design
  size, and Becker's thinnest scaled (1.48 → 1.69 → 1.76) rather than sitting on a
  floor, because nothing in these designs would have fallen under one [M]. What a
  column that *would* drop under ~0.7 mm becomes (held at a width, or a run) is not
  in this evidence.
- **Doubling the size did not mean doubling the picture.** The jacket back's
  lettering scaled (×1.78 on widths at ×1.97); its truck was redrawn — more
  elements, satin where the LC had tatami, 3.5× the stitches. The pro's answer to a
  2× resize of a detailed picture was re-digitizing, not scaling.

### 1.7 What this evidence can and cannot support

It is **one digitizer** (the `.EMB`s and the file-naming convention are one
studio's), **two artworks** with size-only pairs, and widths between 0.67 and
11.8 mm. The clean pairs span 1.25–1.97×; a left-chest → jacket-back ×3 on a bold
logo is extrapolation. The cap/beanie pairs carry garment edits that move widths
on their own (§1.4), so they corroborate direction only. The fixed ~0.3–0.55 mm is
*consistent with* a millimetre pull-compensation setting — Wilcom's published table
is 0.20–0.40 mm (§2) — but nothing here reads the setting; the `.EMB` would, or the
digitizer would. Nothing here says what the cloth does with a 7–12 mm raw cross on
pique or a cap (gate 1).

---

## Part 2 — What the software and the trade say

Every row below was read this session from the URL given; **[V]** rows were fetched
raw and are quoted verbatim, **[S]** rows were read through a summarising fetch.
Three distinctions the question needs: **(a)** resizing an *object* (outline) file,
where stitches are regenerated; **(b)** resizing a *stitch* (machine) file; **(c)** a
*line with a width property* versus a two-rail column.

| source | what it says about width on resize | quote (short) | URL | kind |
|---|---|---|---|---|
| Wilcom EmbroideryStudio help — Stitch Types | (a) Stitches come from outlines + properties; scaling regenerates them. Width = outline geometry, so it scales; properties do not. | "The software uses object outlines and the associated stitch type to generate stitches. Whenever you reshape, transform or scale an object, stitches are regenerated according to current settings." | https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Digitizing/stitches/Stitch_Types.htm | first-party [V] |
| Wilcom ES — Scaling objects | (a) Spacing (density) is held; count changes. Only EMB scales perfectly. | "As an object is scaled, the stitch count changes to preserve the current spacing." · "Note: Only EMB designs contain the complete set of design information for 100% perfect scaling and transformation." | https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Modifying/transform/Scaling_objects.htm | first-party [V] |
| Hatch help — Scale objects / Edit stitches | (a) same, for Hatch. | "Stitches are regenerated and original stitch density preserved." · "stitches are automatically generated from design outlines and properties. This means you can scale, transform and reshape designs without affecting stitch density or quality." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Editing/edit_objects/Scale_objects.htm · …/Editing/edit_advanced/Edit_stitches.htm | first-party [V] |
| Hatch help — Machine file recognition | (b) Stitch files are not for scaling; recognised objects scale, un-recognised blocks change density; ±10 % limit. | "While machine files are generally not suited to scaling, Hatch Embroidery can derive object outlines, stitch types and spacing from raw stitch data with some success." · "Even after recognition, the density of manual objects increases or decreases with design size. Thus you should not scale these designs by more than ±10% or some areas may be too thickly or too thinly covered." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Setup/assets/Machine_file_recognition.htm | first-party [V] |
| Wilcom ES 2025 — Apply satin stitch with auto spacing | Sewable band stated qualitatively, both ends; density may follow width. (c) "Outlines > Satin" is the even-thickness line object. | "If a Satin shape is too wide, stitches may be loose or fail to cover the fabric properly. Conversely, in narrow columns, stitch density may be too great and needle penetrations damage the fabric. You can adjust stitch density by setting a fixed spacing or allowing Auto Spacing to calculate spacings wherever column width changes." · "Use Outlines > Satin to create thicker borders or columns of even thickness." | https://docs.wilcom.com/embroiderystudio/27/en/OnlineHelp/Digitizing/stitches/stitches-8.htm | first-party [V] |
| Wilcom ES — Column C (Set angles & orientation) | (c) A fixed-width column tool exists; width is a property. Whether that width scales with the object is **not stated** on the pages read [U]. | "Use Traditional Digitizing > Column C to digitize columns or borders of fixed width." | https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/input/input-18.htm | first-party [V] |
| Hatch help — Satin outlines | (c) same object in Hatch. | "Use Object Properties > Outline > Satin to create thicker borders or columns of even thickness." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Satin_outlines.htm | first-party [V] |
| Wilcom ES — Split satin stitches | Upper end: a column that grows past a length is **split**, not narrowed; 7 mm is the tip; a minimum split length exists. | "While Auto Split is used primarily to prevent long stitches in wide columns…" · "Enter a maximum satin stitch length to allow before Auto Split is applied. Stitches that exceed this value will be split into smaller stitches." · "Tip: Use a length of 7.00 mm to preserve the satin effect." | https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Split_satin_stitches.htm | first-party [V] |
| Hatch help — Satin fills | The hard ceiling is the machine's frame movement, 12.1 / 12.7 mm; over it the stitch is broken, or kept as jumps (Auto Jump). | "embroidery machines have a maximum possible stitch length which is determined by the physical frame movement. If a stitch exceeds this, it is generally broken into smaller stitches of equal length." · "Usually 12.1 or 12.7 mm, this maximum value varies with the selected machine type." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Stitches/stitch_basics/Satin_fills.htm | first-party [V] |
| Wilcom blog — Mastering Satin Stitch and Tatami Stitch | Stated maximum width (already in DOCTRINE 2026-09-02). | "Maximum Width: The ideal maximum width for a Satin Stitch is around 12mm. Wilcom suggests staying within 10 mm width. Going up to 15mm is possible, though there is a high risk of snagging." · "Tip: Use 7 mm Auto Split to maintain the satin effect." | https://wilcom.com/resources/blog/mastering-basic-stitch-types-satin-stitch-and-tatami-stitch | first-party blog [V] |
| Wilcom ES — Apply automatic pull compensation | Pull comp is an **absolute millimetre** property, varied by fabric *and by column width* — the fixed part §1.3 measures is this class of setting. | "Enter an overstitch allowance (in millimeters)." · "Appropriate settings vary with the type of fabric – stretchy, pile, etc – hooping method – tight or loosely hooped – and size of embroidery object – wide or narrow columns." Table: drills/cotton 0.20, T-shirt 0.35, fleece/jumper 0.40, lettering 0.2–0.3 mm. | https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/underlays/Apply_automatic_pull_compensation.htm | first-party [V] |
| Hatch help — Pull compensation | Same mechanism, "overstitching" outlines. | "Automatic pull compensation, however, counters the pull effect by ‘overstitching’ outlines of filled shapes on the sides where the needle penetrates." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Digitizing/digitize_objects/Pull_compensation.htm | first-party [V] |
| Hatch help — Lettering underlay | Typical lettering column width; a fancy font's size band; Auto Split mandatory at the band's bottom. | "Most embroidery lettering is 15 mm high or less … At normal sizes, columns are less than 3 mm wide for normal – not heavy or block – fonts." · "With fancy fonts such as ‘Charcuterie’, the minimum height is 20mm, the maximum 65mm. Even at 20mm, Auto Split should be turned on otherwise stitch length will be too long for domestic machines." | https://hatch.embroideryhelp.net/v3/en/OnlineHelp/Lettering/lettering/Lettering_underlay.htm | first-party [V] |
| Hatch blog — Choosing the right size embroidery lettering | Object-based lettering scales 1:1, and the vendor publishes the **size band** within which that is acceptable per font; under ~5 mm you change stitch type (run-stitch font), not width. | "All fonts will have specific parameters that need to be observed." · "Run Stitch (Block) Minimum: .2in/4mm Maximum: .25in/6mm" · "Tahoma … Minimum: .25in/6mm Maximum: 1.6in/40mm" | https://hatchembroidery.com/resources/blog/choosing-the-right-size-embroidery-lettering-for-your-project | first-party blog [V] |
| Melco DesignShop v9 help — Top Stitching tab | **The only vendor read that clamps width as a property.** Pull comp as a **percentage** of stitch line (scales with width), plus a fixed **Pull Offset** in points, a **Max Pull Comp**, extra comp for small columns, and **Min / Max Column Width** clamps. Also the density-vs-size rule of thumb. | "Because the adjustment is based on a percentage, the longer the stitch line, the more compensation is added. For example, if the pull compensation is set to 105% for an object, each individual stitch line will be increased in length by 5%…" · "if a pull offset value of 2 pts was added to a single-line column with a width of 12 pts, the stitch lines of the column would be extended to equal 16 pts." · "Max Pull Comp: This value will limit how far the pull compensation is allowed to extend the stitch lines." · "Enable Small Column Pull Comp Scale: If this is checked, the pull compensation will increase for small columns based on the values specified." · "Min Col Width: The Minimum Column Width will keep stitch lines in a column from falling shorter than the value entered in the Min Col Width field. Max Col Width: The Maximum Column Width will keep stitch lines in a column from being longer than the value entered in the Max Col Width field." · "As design size increases, density value should decrease." (Melco's point is 0.1 mm — [I], not read on this page.) | http://www.melco-service.com/docs/DS_V9_090309/Top_Stitching.htm | first-party [V] |
| Ink/Stitch docs — Satin Column | (c)/(a) Width is the rail distance (geometry, scales with the SVG). Pull comp exists in **both** forms — % of width (scales) and mm (does not). Too wide → split at a maximum stitch length. | "A satin column is defined by a shape made of two mostly-parallel lines … The thickness of the column will be based on the distance between the two lines." · "Pull compensation (%): Additional pull compensation which varies as a percentage of stitch width." · "Pull compensation (mm): … This setting expands each pair of needle penetrations outward from the center of the satin column by a fixed length." · "Maximum stitch length: Stitches wider than this will be split up (split stitches)." | https://inkstitch.org/docs/stitches/satin-column/ | first-party (project docs) [V] |
| Ink/Stitch docs — Preferences / Zig-Zag stitch | Lower end: under a stroke-width threshold the object is **re-typed to a running stitch**, not held at a width; ≥ 1 mm recommended. (c) A stroke's width is the zigzag width. | "The stroke width has to be wider than the preference setting, otherwise this element will be treated as a running stitch." · "To not produce hard stitches, it is recommended to only use satins wider than 1mm." · "Ink/Stitch will create stitches along the path using the stroke width you specified as the zigzag width." | https://inkstitch.org/docs/preferences/ · https://inkstitch.org/docs/stitches/zigzag-stitch/ | first-party (project docs) [V] |
| Inkscape manual (Tavmjong Bah) — Transformations | (c) For stroke-based widths, whether the width scales with the object is a user toggle, default on. | "When scaling objects, scale the stroke width by the same proportion." | http://tavmjong.free.fr/INKSCAPE/MANUAL/html/Transforms.html | secondary (semi-official manual) [V] |
| Embrilliance help — Resizing; Sizing of Design Files (Advanced) | (b) A stitch-file resizer: width scales with the design and **density is rebuilt**; satin gets special handling, with a split-satin look appearing at a size. 50–250 %. | "Essentials has a technology known as a stitch processor which lets you resize existing stitch files from upward to 250% to downward of 50%." · "The sizing engine will preserve the look of the fill while keeping the density the same as it was when the design was at its original size." · "the handling of satin stitches is special and you may want to achieve a split-satin look at a certain size." | https://embrilliance.com/Help/Platform%20Mac%201159/resizing.htm · http://embrilliance.com/Help/Essentials%201103/sizingofdesignfilesa.htm | first-party [V] |
| Embird tutorial / FAQ — Resizing with density adjustment | (b) same class: density re-set to a column-stitch and fill-stitch value on resize. | "Embroidery resizing with density adjustment is the process of changing the size of an embroidery design and modifying the stitch density to maintain the design's quality…" · "Embird will adjust the density of stitches to the values specified in Column Stitches Density and Fill Stitches Density boxes." | https://www.embird.net/sw/embird/tutorial/resize/resize.htm · https://www.embird.net/manual/0200faq.htm | first-party [V] |
| Brother — PE-Design 11 Line sewing attributes; machine STB help | (c) "Zigzag width" is a line attribute (Narrow/Wide shown; no mm range on the page). Machine-side resize keeps density by recalculating; no % limit given. | "You can change the pattern size while maintaining the desired thread density. The machine recalculates the stitch density automatically." | https://support.brother.com/g/s/hf/htmldoc/ped/im/ped11/en/PED11_EN/pages/16_1293378.html · https://help.brother-usa.com/app/answers/detail/a_id/80155 | first-party [S] — raw fetch refused (403/401); read via summarising fetch |
| Embroidery Legacy — Satin stitch | Trade band: 1.5–10 mm; machine limits 10 (home) / 12 (commercial). | "It is not recommended to go below 1.5 mm and not over 10 mm." · "Most home machines have a limit of 10 mm. Many commercial machines can stitch up to 12 mm." | https://embroiderylegacy.com/satin-stitch-embroidery-digitizing/ | secondary (education) [V] |

**Not reached / not found [U]:** Tajima DG by Pulse help on satin width or resize
(search returned product pages only); Barudan and Madeira guidance on satin width
(Madeira's downloadable guides were not opened); the Wilcom ES page that states a
scaling limit for *un-recognised* stitch files (Hatch's ±10 % is the same company's
statement and is cited instead); whether a Wilcom Column C / outline-satin width
scales when the object is scaled (no page read says so either way).

**Reading the vendors together.** (a) In every object-based package the rails are
geometry and the stitch *properties* are not: spacing/density is held (Wilcom,
Hatch), pull compensation is a millimetre allowance (Wilcom, Hatch, Ink/Stitch's
mm form) or a percentage (Melco, Ink/Stitch's % form) — and only the millimetre
form produces the sub-proportional widths §1.3 measures. (b) Stitch-file resizers
scale the width with everything else and rebuild density; the vendor warnings
(±10 % Hatch; "not more than 20 %" is a secondary Embrilliance recommendation seen
in search, not read on a first-party page [U]) are about density and detail, not
about width per se. (c) Fixed-width line objects exist in Wilcom/Hatch (Column C,
Outline Satin), Ink/Stitch (stroke width) and Brother (zigzag width); none of the
first-party pages read says what happens to that width on resize. The ends of the
band are handled by **changing the stitch** — Auto Split / maximum stitch length
above (7 mm tip, 12.1 hard), a run stitch below (Ink/Stitch's threshold, Hatch's
run-stitch fonts under ~5 mm) — except Melco, which also offers hard Min / Max
Column Width and Max Pull Comp clamps as properties.

---

## Part 3 — What it means for the decision (analysis, separated from the findings)

Four candidate models for the stored width of a hand-authored column, each against
the pro's data (§1), the vendors (§2), and a left-chest → jacket-back resize. The
worked example uses Becker's 95.7 mm left chest to a 300 mm back (×3.13): MARINE
stems 4.9 mm, the BECKER border 2.2 mm, the thinnest detail 1.7 mm.

**A. Width is geometry — scales 1:1 with the design.**
*Pro:* the closest simple model to the data, and the one the pro's software
applies to the rails; wrong by 0.12–0.22 mm (5 % at 1.25×, 11 % at 1.97×), always on
the high side, with the error growing with the step. *Vendors:* this is what every
object-based package does to the outline (Wilcom, Hatch, Ink/Stitch rails), and
what every stitch-file resizer does to everything. *Jacket back:* stems 15.3 mm,
border 6.9, detail 5.3. The stems pass the 12.1 mm record limit and the pro's 7 mm
Auto Split tip; the vendor answer at that point is a split, not a narrower column.
*Catch:* a column drawn at the pro's width at left-chest size (which already
includes his fixed part) over-shoots his jacket-back width by ~0.5 × (s − 1) mm.

**B. Width is a physical property — never changes on resize.**
*Pro:* refuted on every size pair — bias +0.57 / +0.75 / +1.04 mm, RMS 0.66 / 0.85 /
1.11 against 0.23–0.38 for either scaling model; same-size controls prove the
instrument would have seen it. The only places that *read* unchanged are thin
lines at a ~1.1× step, where the DST grid cannot tell "unchanged" from "scaled with
a fixed part" (§1.5). *Vendors:* B is what the packages do to the *properties* —
spacing, pull comp in mm, min/max width, split length — never to the width of a
two-rail column; for a fixed-width *line* object (Column C, stroke, zigzag line) no
page read says. *Jacket back:* stems stay 4.9 mm on letters three times taller —
the letterform changes weight; counters and gaps open; the pro's own files never
do this. *Catch:* it is the model the pro's data most clearly contradicts.

**C. Proportional but clamped to a sewable band.**
*Pro:* within 0.67–11.8 mm nothing was ever clamped — the thin end sits at
0.7–0.9 mm at every size without a pair that would test a floor, and the wide end
goes raw to 9.1 and 11.8 mm with no split and no fill; the only ceiling the data
touches is the DST record (12.1). A clamp at 5.0 would have narrowed or split 27 %
of the hat's crosses, one at 6.5 1.1 % of them; the pro did neither. *Vendors:* the band is real
in every source (Wilcom 10–12 mm ideal max, 7 mm split tip, 12.1 machine; trade
1.5–10; Ink/Stitch ≥ 1 mm) — but the upper end is enforced by **adding
penetrations**, not by narrowing, and the lower end by **re-typing to a run**;
Melco alone documents min/max width as hard property clamps. The repo's own
ruling 5 (warn above 6.5, never block, offer fill or split) is this model's warn
form. *Jacket back:* stems 15.3 → split (Wilcom), or warn + split/fill offer
(ruling 5), or clamp to a max (Melco). *Catch:* the pro's data gives no number for
the clamp; the repo's 5.0 / 6.5 / 7 and the vendors' 7 / 10 / 12 all live inside
gate 1 (`DOCTRINE.md` 2026-09-02: a web citation is not fabric), and a lower clamp
has no data at all.

**D. A sub-linear law, width ∝ size^k.**
*Pro:* k = 0.80 (IQR 0.70–0.91) at 1.25×, 0.82 (0.71–0.91) at 1.33×, 0.85
(0.80–0.90) at 1.97×, run-level 0.84–0.85 — a tight, repeatable number. But it
drifts with width (0.73 → 0.91 across terciles) and the three-size fit says the
non-scaling part is a constant in millimetres, not a fraction of the width: the
power law is a serviceable *fit* over 1.25–2× for 1–5 mm columns, not the
mechanism. Its twin, **"rails scale 1:1, plus a fixed c ≈ 0.3–0.55 mm that does
not"**, predicts the third size as well (bias +0.01 vs +0.04 mm), explains the
tercile drift, and matches the kind of setting the pro's software exposes
(pull compensation 0.20–0.40 mm by fabric). *Vendors:* none implements a power law
on width; the fixed-mm form falls out of (a) automatically. *Jacket back:* k = 0.8
gives stems 12.2, border 5.5, detail 4.2; fixed 0.5 gives 14.3 / 5.8 / 4.3 — both
still over the split tip and the power law still over 12.1 at the stems. *Catch:*
k measured on 1–5 mm columns at ≤ 2× is being asked about 5 mm columns at 3×; the
two readings diverge there (12.2 vs 14.3 mm), and only the EMB or a pair with a
bigger step decides which.

**Where the evidence leans.** Against B, strongly (three independent pairs,
controls clean). Toward "the drawn geometry scales and a fixed millimetre part does
not" (D's second form, or equally A applied to the rails with the compensation held
in mm — which is what the pro's own software does), moderately: one studio, two
artworks, k ≈ 0.8–0.85 with c ≈ 0.3–0.55 mm, and the mechanism is the one the
vendors document. On C, the band is universally asserted and never once reached in
the data; its *numbers* are gate-1 constants and its *form* (warn / split /
re-type vs hard clamp) differs by vendor. Trade-offs the reader is left with: a
1:1 width is simplest and over-shoots the pro by ~0.5 mm per unit of scale; a
fixed-part model needs a c that is either read from the EMB or taken from the
fabric table (and then it is pull comp wearing another name — ruling 2 already
keeps `widthMm` as the drawn width with pull comp applied by `satin.js`, so the
fixed part may already exist in the engine and double-counting is the risk); a
power law needs no second constant but is a fit, not a law; a clamp needs a cloth
number.

---

## What this does not settle

- **Whether the fixed 0.3–0.55 mm is pull compensation.** Consistent with Wilcom's
  published 0.20–0.40 mm (and with ±0.25 mm per side), but the setting was not
  read. The `.EMB` files in the zip hold it; opening one in Wilcom (or asking the
  digitizer) settles it in minutes.
- **What this pro does above ~9 mm.** No pair reaches a column he had to split or
  fill: the 2× jacket back's picture was redrawn rather than scaled. A Becker-sized
  logo at 250–300 mm from the same studio would answer it.
- **What the cloth does with 7–12 mm raw crosses on pique and on a cap** — gate 1.
  The files show he ships them; they do not show how they wear.
- **Behaviour under ~0.7 mm.** No pair contains a column that would fall below the
  thinnest sustained width seen (0.67 mm); whether he holds a width, re-types to a
  run, or drops it is not in this evidence.
- **Whether fixed-width line objects (Wilcom Column C / Outline Satin, Hatch,
  Brother zigzag) keep their width when the object is scaled.** No first-party page
  read says; a 30-second test in Hatch's free trial would.
- **The thin-line population in MFAB and Machine (§1.5)** — resolvable only with a
  ≥ 1.3× step or the EMB.
- **Density follows width or not.** This pro holds spacing fixed per object; Wilcom
  Auto Spacing and Melco Auto-Density grade it by width. Which the manual lane
  should do is a separate question this note did not measure beyond §1.1.

## Method record

Measurement code is scratch under `.superpowers/research-satin-width/` (git-ignored):
`swlib.py` (the wrapper around `tools/satin_columns._crosses`, the collinear merge
for split rows), `s1_inventory.py` (sizes, validation), `s2_render.py` (layout
sheets), `s3_pairs.py` (registration, cell and run matching, model scoring, overlay
renders), `s4_modes.py` (ratio histograms, run tables), `s5_checks.py` (three-size
fit, quantisation check, wide end), `s6_floor_and_fixed.py` (thinnest columns,
fixed-run renders). Outputs in its `out/` (`inventory.json`, `pairs.json`, logs,
sheets, overlays). Python: the main checkout's `digitizer/.venv` (3.14, pystitch,
numpy, scipy, cv2), run with cwd = this worktree's `digitizer/`. Vendor pages were
fetched with curl to `web/` and stripped to text; quotes above are from those
files. Nothing in `digitizer/`, `src/` or `app/` was changed.
