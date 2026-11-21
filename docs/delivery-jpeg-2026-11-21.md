# Same logo, the file the customer actually has — 2026-11-21

**Question.** Every fixture here is scored as committed: the master PNG, or
whatever JPEG Kent was handed. A customer uploads whatever their email,
website or social page gave them, which is nearly always a JPEG, often
re-saved, often a shrunk thumbnail. Nothing measured whether that changes
what sews. Stage 0's *resolution* invariance is Phase 2's exit and has its
own work (MASTER_SCOPE, "Phase 2 (framing)"); *compression* invariance had
no instrument.

**Instrument.** `digitizer/tools/delivery_jpeg.py` makes the deliveries
from each logo's committed file (alpha flattened on white, as a JPEG export
does) and scores each digitize against the logo digitized from the file as
committed, with `tools/lowres_detail.score` (`agree` = share of the
reference's sewn area sewn in the same colour; `fine` = the same over its
sub-1.5 mm ink). Deliveries: `flat_white` (alpha flattened, lossless — it
separates "lost its transparency" from "got compressed"), `q95`, `q75`,
`q50`, `q30`, `q75x2` (saved twice), `thumb` (60 %, q70). `--set
FIELD=VALUE` prices any config flag on every arm.

Nine logos, 80 mm, left chest, main `69b658c`. Full table:
[`renders/delivery-jpeg-2026-11-21/sweep-main-69b658c.txt`](renders/delivery-jpeg-2026-11-21/sweep-main-69b658c.txt).
Pictures (master, its sew, the delivery, its sew):
[`renders/delivery-jpeg-2026-11-21/`](renders/delivery-jpeg-2026-11-21/).

## What moved

| logo | delivery | what happened | stitches ref → arm | agree |
|---|---|---|---|---|
| becker | flat_white (no compression) | the white page is sewn as a white rectangle round the logo | 10,474 → 18,499 | 0.977 |
| becker | every JPEG | same | → 17,703–18,707 | 0.94–0.98 |
| gaulke (phone screenshot) | q30, thumb | the white card behind the lettering is sewn; master sews only the ink | 4,534 → 12,774 / 11,893 | 0.47 / 0.59 |
| whitebg | q95 | purple square sews blue: one cone lost to a near-lossless save | 6,607 → 6,667 | 0.927 (fine 0.42) |
| bridge | q50 | compression-halo cones return through the teal lettering; trims 15 → 43 — and q30 is BETTER than q50 | 10,684 → 13,025 | 0.974 (fine 0.78) |
| drone | flat_white | routing flips gradient → flat on losing alpha | 18,083 → 23,284 | 0.80 |
| fremont | flat_white | a white element on transparency vanishes on white — information genuinely lost, not the engine's | 11,772 → 4,727 | 0.31 |
| tires, golden_tee, enthusiast | all | stable (agree ≥ 0.94; enthusiast's q30 adds two cones) | | |

Agreement here is a raw overlap against the engine's own reading of the
master, not a quality claim (gate 4): it says the delivery CHANGED the
design, and the pictures say which way.

## Causes found

**1. Becker: `BACKGROUND_ABSENT` on a tightly-cropped logo — and the warning
that should catch it is silent.** The 146 × 91 px file is cropped so tight
that the dark outline touches 29 % of the 2-px border ring; agreement 0.711
against `bg_border_agreement_min` 0.75, so stage 1 decides the art runs edge
to edge and the page sews. The master escapes only because its alpha says
where the page is. `GROUND_SEWN` (the download-confirm block for exactly
this) does not fire: the letters touching the edge cut the sewn page into
pieces, the biggest spans 1.00 × 0.65 of the design against
`_GROUND_SPAN_MIN` 0.90, and it is 29 % of the stitching. **Not fixed.**
Same family as DOCTRINE 2026-09-14's "soft shadow edges drop border
agreement to 0.693"; `bg_structural` ("Waiting on Kent" 39) is being priced
on these deliveries.

**2. Gaulke q30: JPEG ringing voided the letterbox bars — FIXED here.** A
q30 save rings one line (mean 9.8 on a black bar) just above the top bar's
hard edge. `letterbox._run_length` required the step on the very line the
uniform run broke on, so the top bar was refused; with only the bottom bar
left, the interior's border read black and the bottom bar was refused as a
margin. Now the step may lie up to `JPEG_RING_LINES` = 7 lines past the run
(JPEG codes 8 × 8 blocks; ringing stays in the block holding the edge), the
transition lines go WITH the bar, and past line n the step must be HARD
against the previous line (a ramp drifts, never jumps) across lines uniform
in themselves (a ragged silhouette is not a bar). **Verdict changes: 0 of
53 committed images; 1 of 371 deliveries (9 deliveries × every testdata
image) — gaulke q30, now (1116, 1116, 0, 0) like every other quality.** The
first cut without the two guards caught a sunset photo's silhouette as a
55-line bar and the ramp test; both are pinned
(`tests/test_letterbox.py`, four new tests).

**3. Gaulke q30 / thumb still sew the card: the edge-strip trimmer.** With
the bars found, `detect_edge_strips` must trim the card's 9-px shadow strips
or the border ring reads 0.69 and stage 1 says `BACKGROUND_ABSENT`. It
trims them at q50 and better, but at q30 the outermost shadow columns have
drifted within 6 ΔE of the white ground (5.6, 5.9), so the strip "ends"
before it starts; on the thumbnail every column carries the resize-blended
line where the bar was cut (column std 12–14 everywhere), so no column is
uniform. **Not fixed** — a naive widening of the scan reads into artwork.

**4. whitebg q95 and bridge q50** are colour/segmentation fragility, causes
not isolated.

## What a fix is worth

Gaulke is the corpus's phone screenshot and Becker its tightly-cropped
master — both are what a customer without a designer sends. In both, the
failure is the worst one a customer can get: a block of thread the colour
of the cloth across the whole design, and in Becker's case no warning.
