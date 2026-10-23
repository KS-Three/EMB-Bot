# Our digitizing settings against the professional's files (2026-10-21)

Research only. No engine file changed, no default flipped, no constant touched.

**Why.** Kent, 2026-10-21: *"We should compare our settings against the pros,
anything that's off by 5% or more should get a secondary review."* This is that
comparison. Every setting that shapes stitches and that the pro's files can show
is listed with our effective default, the pro's value read from his DSTs, and the
delta. Every setting off by 5% or more, or outside the pro's range, got a second
reading by an independent reviewer (a fresh agent given only the setting, the two
numbers and the evidence paths, not the first reader's conclusion), who measured
again from scratch with its own script.

**ROADMAP gate 1.** Densities, pull and widths are physical constants. Nothing
here changes one. Where the table says "gate 1: yes", the recommendation is a
sew-out arm or a Kent flip, never a silent default change. DOCTRINE (2026-09-03)
settled `FILL_ROW_MM` on the pro's files read as rows **together with Kent's own
stitch-out**; the pro's files alone have not settled a constant.

## What was read

- **Pro.** All 28 DSTs in the repo-root `Embroidery Files.zip` (11 jobs; the
  `Test Files` sample corpus left out). DST only: the PES reader reports a TRIM at
  every jump. Every number is read in each file's own frame, never through a box
  mapped from the art.
- **Ours, through the same instruments.** Nine of those jobs digitized by `main`
  at `4fa4f302` with `tools/pro_pair.py` at the pro's own width and garment:
  Fremont hat 92.6 mm, Roofing hat 114.2 and LC 95.2, Drone 62.6, Becker hat small
  76.5, Becker beanie 79.8, MFab hat 104.9, Machine hat 89.5, Golden Tee 74.9. Our
  `ours.dst` went through exactly the scripts the pro's DST did, so a delta between
  them is not a difference of method.
- **Earlier measurements reused**, and named where used:
  `docs/pro-digitizer-rules-2026-10-21.md` (lettering, economy, knockdown),
  `docs/underlay-audit-2026-10-05.md`, `docs/corpus-laws-round3-2026-08-01.md`,
  `docs/beanie-knockdown-2026-10-21.md`, `docs/trim-economy-2026-10-21.md`.
- **Scripts** are throwaway, in the session scratchpad (first reader:
  `pro_settings.py`, `compare.py`; each reviewer its own). Methods are given per
  row, enough to reproduce.

### One correction to PR #1026 this found

**The pro's satin is 0.37 mm, not 0.40.** `pro-digitizer-rules` R7 reads "0.40
(same rail)" on every file. That is the DST grid: every penetration is stored on a
0.1 mm grid, so a true 0.37 mm advance is laid down as a mix of 0.3 and 0.4 steps
and the per-stitch median lands on 0.40. Averaging the advance over a straight run
of 8+ crosses gets under the grid; the same average reads our 0.40 setting back as
0.400, so the instrument is sound. Corpus law 21's 0.38 (2026-08-01) was the right
number.

### One stale note this found

**`.claude/memory/pro-trim-threshold.md`'s "pro floats up to 16.1 mm uncut" is
not about jumps.** Its "NOT CUT" class is `prep_all.decode`'s "hop": two
consecutive needle-DOWN stitches 7.5 mm or more apart (the 16.1 mm one is a stitch
in `beckers logo hat.PES`). In the DSTs the pro leaves **no** needle-up move uncut.
The note carries a correction from this PR; `docs/trim-economy-2026-10-21.md:108`
repeats the old phrasing.

## The table

Ours = the effective default on today's `main`, by garment profile where it
differs (Hat = `hat_front` → `structured_cap`; LC = `left_chest` → `pique_knit`;
beanie → `jersey_tee`; `digitizer_core/fabrics.py:61-76`, `GARMENT_FABRIC`
`:106`). Pro = median by job [range of job medians]. Delta = (ours − pro) / pro.
"1st / 2nd" = the first reading and the independent second reading.

| # | setting | ours (file:line) | pro median [range] | delta | flagged | 1st reading / 2nd review | gate 1? | recommendation |
|---|---|---|---|---|---|---|---|---|
| 1 | **Satin spacing, hat & LC** (same rail) | 0.40, outer rail (`machine.py:406`, `config.py:2332`); all garments | **0.37** [0.356-0.380], 9 jobs | **+8%** | yes | 1st: straight-run per-stitch median 0.35-0.39, ours 0.38-0.40. 2nd: run-averaged 0.356-0.380, ours 0.393-0.400 (control reads 0.400). **Agree: REAL, small.** Law 21 (2026-08-01) ruled "no change" on 0.38 vs 0.40. | yes | Sew-out arm 0.37 beside 0.40. ~8% more satin stitches. |
| 2 | **Satin spacing, beanie** | 0.40 (no beanie override) | **0.35** [0.335-0.375], 6 beanie files | **+14%** | yes | 2nd: 4 of 5 beanie/hat pairs denser by 0.014-0.033 mm; Roofing unchanged. Doc's "0.32-0.36" was per-stitch. **REAL; varies by job** (a variable, not a constant). | yes | Sew-out arm ~0.34 for beanie. |
| 3 | Border (edge satin) density | 0.40 (`machine.py:597`) | 0.40 law 41 (p10 0.36, p90 0.42), per-stitch reading | 0% as read | no | Same grid caveat as row 1 applies to law 41's reading; not re-read. | yes | Read again with run averaging when row 1 is sewn. |
| 4 | **Satin → fill width ceiling** | 5.0 (`machine.py:415`); 6.5 under `wide_columns` OFF (`machine.py:431`, `config.py:4132`) | widest satin, p99 by job: **4.39** [3.22-5.72], one roof peak aside; ours max 4.90-5.03 | ceiling +14% over the p99 median; the pro's range (5.72) is above ours | yes (outside range) | 1st: p99 3.3-11, Roofing 9-11 suspicious. 2nd: Roofing's long crosses are ONE tapering column (the roof peak, 2.5 → 11.4 mm, 44 mm long) at the DST record limit; other > 5 mm crosses are short taper wedges (Becker 5.7). **RULED**: DOCTRINE 2026-09-06 (don't raise the cap), `wide_columns` built OFF 2026-09-09. | yes | Leave 5.0. |
| 5a | **Satin underlay: zigzag threshold** | zigzag (1.45 pitch) above 2.5 mm, gated on artwork width + rail comp (`machine.py:445, 825`; `stage6_satin.py:6733`) | edge run + zigzag on columns ≥ ~3.5 mm (Becker hat edge 18/21, zigzag 14/21); zigzag on only ~15% of 2.0-3.5 mm columns | threshold **-29%** (2.5 vs 3.5) | yes | 1st: law 22 put the crossover at 2.0-2.5 (third-party corpus). 2nd: on these hats it is nearer 3.5; ours barely fires at 2.5-3.5 anyway (Machine 0/14, Golden Tee 1/22). **ARTEFACT of law 22's corpus**; don't apply law 22's 2.5 → 2.0. | yes | Edge run + zigzag at 3.5 mm as a sew-out arm. |
| 5b | **Satin underlay under small letters** | none under letters whose art extent < 5 mm (`machine.py:469`, law 50); `center_run` otherwise (`fabrics.py:61-76`) | a centre walk under ~93% of columns at every width, including < 1.5 mm (Fremont 77 of 78) | columns with NO underlay: ours 23% vs pro 5%; on columns < 5 mm long ours 46% vs pro 10% | yes | 2nd only. **RULED** (Kent, MASTER_SCOPE 2026-09-03) but the gap is REAL. Caveat: some of the pro's "centre walk" may be travel sewn under the column, which does the same job. | yes | Show Kent the 46% vs 10%; reversing it needs a sew-out. |
| 6 | **Small-text minimum height** | sews at the art's size (`small_text_cap_mm` None, `config.py:2731`) | **3.85** cap [3.65-4.25] (pro doc R2; 2nd: Fremont p10 3.38, p90 4.30) | ours ~1.7 on Fremont's EST: **-56%** | yes | 2nd: agrees with R2. **RULED in direction** (Kent 2026-10-21, "match the pro"); #1024/#1025 merged OFF, #1029 open. | cap: no (design); floors: yes | Let #1029 land; renders before any flip. |
| 7 | **Small-text column floor** | `SATIN_MIN_CROSS_MM` 0.5 (`machine.py:456`); candidate 0.85 OFF (`config.py:2750`) | **0.90** [p10 0.71-0.80] on raised text; 1.26 Drone/Proseal | **-44%** (0.5 vs 0.9) | yes | 2nd: Fremont 0.90 (p10 0.72, 446 crosses); ours sews that text as bean, so no like-for-like column. **In flight** (#1029). | yes | Sew-out card v6 (#1029) decides. |
| 8 | **Pull compensation, hat** | 0.4 mm per rail (`fabrics.py:61`), less `RAIL_REACH_INSET_MM` 0.11 (`columns.py:110`) ⇒ +0.58 mm on a column | sewn − art on wide strokes: +0.26 / +0.45 (Roofing), +0.56 (Machine) | ours − pro **+0.15 to +0.27 mm** on wide hat strokes (**+10 to +13%** of the column) | yes | 1st: whole-file median columns ours ≈ pro on several hats (inconclusive). 2nd: per letter line, ours +0.53/+0.60/+0.79 vs pro +0.26/+0.45/+0.56; thin strokes equal (−0.03). **Disagree on the first reading, which mixed populations; REAL, small.** Kent ruled where pull lands (rail comp, 2026-09-28), not the amount. | yes | Hat sew-out arm: −0.1 mm per rail (or a share of stroke width) against 0.4. |
| 9 | Pull compensation, LC | 0.3 per rail (`fabrics.py:71`) | ours − pro −0.05 to +0.06 mm (Roofing LC) | ±3% | no | 2nd confirms equal. | yes | none |
| 10 | **Fill row spacing** | 0.15 (`machine.py:75`), all garments (pile presets scale it) | **0.16** mean [0.147-0.173] | **-6%** | yes | 1st: doc's 0.15-0.19. 2nd: run-averaged means 0.147-0.173, ours 0.140-0.164. **DELIBERATE, RULED** by Kent 2026-09-03 (DOCTRINE; `fill-row-ruling-2026-09-03`). Nitpick. | yes | No change. |
| 11 | **Fill stitch length** | 3.0 (`machine.py:37`), even division per row | **3.49** [3.45-3.52] on rows ≥ 10 mm, 10 of 11 jobs; Fremont **hat** 2.97 (patch 3.47) | **-14%** | yes | 1st: p50 3.45-3.55. 2nd: 3.45-3.52, p10-p90 3.44-3.55; ours exactly 2.97-3.00; the pro uses a FIXED length with staggered remainders (0.6-3.3 mm), not even division. First reader's "ours p50 2.2" was split-satin rows. **Agree: REAL.** Law 20 (2026-08-01) proposed a 4.0 ceiling; never ruled or built. The `machine.py:33-37` comment still cites the older 2.6 median. | yes | Sew-out arm 3.5 fixed + stagger beside 3.0. |
| 12 | **Fill angle habit** | each fill picks its own angle; `design_angle` OFF (`config.py:1821`) | one angle per design on 5 of 7 fill jobs (78-99.9% of fill thread within ±10°); never horizontal (≤ 3% near 0°, Drone 14%) | categorical | yes | 1st: ours horizontal 96-97% on Fremont and Drone. 2nd: same; ours also spreads on MFab, Becker, beanie. **REAL but RULED**: Kent judged `design_angle` "no difference" on 8 of 9 logos and kept it OFF (`docs/kent-review-2026-09-18.md`). New: we sew horizontal rows where the pro never does. | no (design) | Not a re-flip; a fresh question with renders: why our fills pick 0°. |
| 13 | **Fill underlay, hat** | `edge_zigzag`, 2.0 mm pitch (`fabrics.py:61`, `machine.py:799`) | CROSS pass: 0.75-0.99 pitch, 3.05-4.02 stitch, 89-90°, 8-20% of the fill's thread, under every dense fill (7 jobs) | pitch +100%, thread ~6.6% vs 8-20% | yes | 1st: underlay audit 2026-10-05. 2nd: re-ran `pro_fill_underlay.py` on 4 hat files, agrees; ours Fremont reads CROSS at 2.0/2.2/6.6%. **REAL.** Partly ruled: MASTER_SCOPE item 27 (2026-10-07) makes `cross_tatami` a picker choice; presets are Kent's. **Defect found: our MFab main fill (2,521 mm², photo class) and the Becker beanie fills sew BARE.** | yes (preset) | Kent flip: `cross_tatami` into hat/LC/beanie presets. File the bare fills as a defect. |
| 14 | Fill underlay, LC & beanie | `edge_run` (`fabrics.py:71,74`) | CROSS as row 13 | categorical | yes | as row 13 | yes | as row 13 |
| 15 | Cross underlay constants | 1.0 row / 4.0 stitch (`machine.py:814-815`) | 0.98 / 3.99 (audit, 34 fills) | 2% / 0% | no | — | yes | none (it is in no preset; row 13) |
| 16 | **Fill-to-neighbour overlap** | `overlap_mm` 0.25 (`config.py:1538`) | law 37 +0.37 was a THIRD-PARTY corpus; pro seam strips 0.44-1.03 (rough raster, direction only); same doc read the pro at +1.6-1.9 | ≥ **-32%** | yes | 2nd: **in flight** — `overlap_by_angle` (1.0 mm on parallel seams, #700/#823) and `forbid_gap_mm` (#846) built OFF, card block 6 (MASTER_SCOPE item 47). | yes | Decide through card block 6, not the scalar. |
| 17 | Run (link) stitch length | 2.0 (`machine.py:997`) | not separable from travel in the DSTs | — | 1st: yes (+18%) | 1st: single runs 1.4-2.5 vs 2.0. 2nd: 94% of those "runs" sew under later stitching; visible runs are 20 stitches in 9 files. **ARTEFACT.** 2.0 is law 61's measurement. | — | Keep. |
| 18 | Travel stitch length | 2.5 (`machine.py:792`) | 2.38 [p10 1.28, p90 3.91] travel under later fill | +5% | borderline | 2nd: ours 2.34, inside the pro's range. **ARTEFACT / no gap.** | — | Keep. |
| 19 | **Bean stitch length** | 0.73 × 3 passes (`machine.py:732-733`) | **0.95** [0.80-1.04] by job | **-23%** | yes | 1st: 1.3-2.5 (detector caught only one bean style). 2nd: ABAB beans pro 0.80-1.04, ours 0.71-0.81; pro sews ~5x fewer bean stitches (3,100 vs 15,200 over 9 files). **REAL.** Already priced: `edge_cap_bean_pitch_mm` built OFF, candidates 1.0/1.2/1.5 (`config.py:4016`, MASTER_SCOPE 59(g)). | yes | Sew card block P (#970), then decide 1.0. |
| 20 | Tie-off leg length | 0.8 (`machine.py:829`) | 0.86 [0.70-1.00] | -7% | 1st: yes | 1st: 0.9 overall. 2nd: inside the pro's 0.70-1.00 band. **ARTEFACT.** | — | Keep. |
| 21 | Tie-off leg count | `TIE_STITCHES` 3 (`machine.py:830`), but `stitches.tie_run` (`:382`) adds a return leg: emits 4 | 4 (287 of 298 runs) | 0% | no | Both read 4. The comment is wrong, the output is not. | — | Fix the comment (doc-level). |
| 22 | **Tie-in** | every run locked (bounce, 4-5 legs at 0.8) | **none** on 296 of 298 runs; first stitches not shortened | categorical | yes | 1st: "13-43% retrace at 1.1-1.4". 2nd: those were satin/underlay starts; the pro does not lock a start. **Disagree on the first reading; REAL.** Not ruled (DOCTRINE 2026-10-20 turns browser `ties` ON, rules nothing on style). | yes (does a start hold?) | Sew-out card: "no tie-in" arm. The pro may rely on the machine's own lock or on covering stitches. |
| 23 | Tie-off style | bounce in one gap (A,B,A,B,A: 2 holes) | walk back two stations (A,B,C,B,A: 3 holes) | categorical | yes | 2nd only. **REAL, minor.** | yes | Same card as row 22. |
| 24 | **Minimum stitch length (output)** | declared `MIN_STITCH_MM` 1.0, `TINY_STITCH_MM` 0.5 (`machine.py:26,30`) | p1 **0.41** [0.36-0.64]; 0.1-5.8% of stitches < 0.5 | ours p1 0.10-0.32 (**-27 to -76%**); 4.2-13.8% < 0.5 | yes | 1st and 2nd agree on numbers. 2nd: 40-90% of our sub-0.5 stitches are **fill-row turns stepped straight across** (0.10-0.22 mm); the pro turns on a slant of ~0.7-0.85 mm (p10 0.40-0.42 in all seven fill jobs) at the SAME row spacing. Neither floor is enforced on output (`preflight._tiny_step_metrics` only counts). **REAL**, not caused by the 0.15 row ruling. | turn shape: no; a floor number: yes | Build an angled row turn, OFF. |
| 25 | **Trim threshold / jumps** | `TRIM_AT_MM` 3.0 (`machine.py:835`; `trim_at_mm` 3.0 hat/LC/beanie, `fabrics.py`) | every needle-up move cut, in all 28 files; shortest cut 1.4-4.6 mm | ours leaves **0-168 uncut jumps** of 0.5-3.0 mm per job (Fremont 168, Drone 55, Machine 33) | yes | 1st and 2nd agree (2nd decoded raw DST records: the pro always writes ≥ 3 jump records). **REAL.** DOCTRINE (2026-09-06) rules only against RAISING the threshold. | yes (trimmer wear vs floats) | Built-OFF candidate: cut, or sew needle-down, every needle-up move. |
| 26 | Max stitch length | 12.1, format limit (`machine.py:20`) | file max 4.4-12.1 | — | no | Not a setting difference. | — | none |
| 27 | Beanie knockdown rows / stitch / margin | 0.50 / 3.5 / 2.0 (`knockdown.py:49,51,55`) | 0.48-0.51 / 3.50 / 1.80-1.82 true (`docs/beanie-knockdown-2026-10-21.md`) | +2% / 0% / +3% on free-standing logos | no | Reused, not re-read. | yes | none |
| 28 | Edge border width | 1.70 (`machine.py:589`) | 1.70 law 41 (edge-covering borders) | 0% | no | Reused. | yes | none |
| 29 | **Colour-block ordering** | one block per thread, largest-weight first | threads repeated to keep fill-then-outline per element (5 jobs); biggest fills first (8 jobs) — pro doc R12/R13 | categorical | yes | Not re-read (architecture, not a constant). Corpus law 34: "emitting one thread more than once", not built. | no | Not a setting; listed for completeness. |

Satin underlay method (row 5): a satin top is a run of 6+ antiparallel stitches at
≤ 0.55 mm spacing; earlier same-colour stitches inside its footprint (0.15 mm
buffer) covering ≥ 50% of its length are its underlay, classed as centre run
(offset < 0.3 of the half-width), edge run, or zigzag (antiparallel, > 0.55 mm).

## Where the pro's own jobs disagree (variables, not constants)

- **Fill stitch length**: Fremont hat 2.97 against 3.45-3.52 on every other job
  (Fremont patch 3.47). One job, deliberate.
- **Beanie satin density**: 4 of 5 pairs denser than the hat, Roofing unchanged.
- **Fill angle**: one angle on five jobs, a mirrored pair ±20-25° on Drone and the
  Becker beanie.
- **Overlap**: 0.44 to 1.03 mm by job on a rough raster.

## Recommended changes, ranked by expected visible effect

Nothing here is flipped by this PR. "Needs sew-out" = gate 1, an arm on the next
card. "Safe to change" = no physical constant moves.

1. **Fill underlay under dense fills → `cross_tatami` in the hat/LC/beanie
   presets** (row 13-14). The pro does it on every dense fill on every job; ours
   is sparse, and two of our fills sew bare. Visible as fill that sinks and lets
   the cap show through. *Needs sew-out* (a preset is gate 1); Kent's flip. The
   bare MFab/Becker-beanie fills are a separate defect: *safe to fix*, no constant.
2. **Fill-row turns on a slant instead of straight across** (row 24). Removes
   40-90% of our sub-0.5 mm stitches, the ones that shred thread and pile at the
   fill edge. Construction, *safe to build OFF*; any floor number is *needs
   sew-out*.
3. **Cut every needle-up move, or sew it needle-down** (row 25). 168 uncut
   floats on Fremont alone, each one a thread someone snips by hand. *Needs
   sew-out* (trimmer wear vs floats); build OFF.
4. **Fill stitch length 3.0 → 3.5, fixed length with stagger** (row 11). Smoother,
   flatter fills with ~14% fewer penetrations. *Needs sew-out.*
5. **Satin spacing 0.40 → 0.37 (hat/LC), ~0.34 (beanie)** (rows 1-2). Fuller
   satin, less fabric showing between crosses, ~8% more satin stitches. *Needs
   sew-out.*
6. **Hat pull −0.1 mm per rail on wide strokes** (row 8). Columns 0.15-0.27 mm
   narrower, closer to the pro's letters. *Needs sew-out.*
7. **Satin underlay: a centre walk under small letters, edge run + zigzag from
   ~3.5 mm** (rows 5a-5b). 46% of our short columns sew bare where the pro's
   bare share is 10%; reverses a 2026-09-03 ruling, so Kent's call. Do NOT
   apply law 22's 2.5 → 2.0. *Needs sew-out.*
8. **Tie-in dropped, tie-off walked back** (rows 22-23). Small visible effect
   (no lock knot at run starts). *Needs sew-out* — a start that does not hold is
   worse than a knot.
9. **Bean pitch 0.73 → ~1.0** (row 19). Already on card block P. *Needs sew-out.*
10. **Why our fills sew horizontal rows** (row 12) — a question with renders, not
   a flip; `design_angle` stays as Kent ruled.
11. **Doc fixes, safe now:** the `machine.py:33-37` comment (law 7's 2.6 mm,
    superseded by law 20), `TIE_STITCHES`' "3" (emits 4), PR #1026's R7 "0.40"
    (is 0.37). The memory note's "16.1 mm floats" is corrected in this PR.
