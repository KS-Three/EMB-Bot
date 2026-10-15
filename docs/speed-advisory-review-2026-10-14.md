# Speed advisory review — 2026-10-14

Kent: *"Do we adjust embroidery speeds for more challenging stitches?"*

**No. Nothing EMB-Bot writes carries a speed, and the formats Kent sews (DST,
PES) cannot carry one.** The pro's files carry none either. The pro handles
hard passages with geometry and leaves speed to the operator. EMB-Bot prints a
*planning* run time at 650 spm, or at the operator's typed speed.
Measure-only review; no engine change; no flag.

**The census found something the question did not ask about (§5).** Our hard
stitches are short and stacked, not long. 33.8% of our stitches are under
1 mm, against the pro's 10.6%. In the median file, 31% of penetrations land
near an earlier hole, against the pro's 13%. That is a geometry lead, not a
speed one.

## 1. Formats: which can carry speed

| Format | Writer | Can carry speed? | Emitted today |
|---|---|---|---|
| DST | `src/dst.js` | No. The record holds stitch/jump/colour flags only (`dst.js:106-107`); `0xF3` ends the file (`:121-122`) | none |
| EXP | `src/exp.js` | No speed code in `exp.js` (colour `80 01`, jump `80 04`, trim `80 80`: `:71-86`), nor in pystitch's EXP reader or writer | none |
| PES/PEC | `src/pes.js` | No. The long form has jump `0x1000` and trim `0x2000` (`:157-158`), colour is `FE B0`, end is `FF` (`:186-194`) | none |
| `/export` dst, pes, jef, exp, pec, vp3, xxx | pystitch (`digitizer_service/formats.py:110-120`) | No. None of these writers sets `WRITES_SPEEDS` | none |
| `/export` u01 (Barudan) | pystitch `U01Writer` | **Yes**: `WRITES_SPEEDS = True` (`U01Writer.py:9`); it sets bit `0x04` (SLOW) or `0x02` (FAST) on the next stitch (`:47-67`) | **none**: `export.plan_to_pattern` adds only STITCH/JUMP/TRIM/COLOR_CHANGE (`export.py:56-66`), so there is nothing to encode (`EmbEncoder.py:286-289, 570-575`) |

Only pystitch's `U01Reader` and `DatReader` (both Barudan) read SLOW/FAST.
`tests/test_stitch_difficulty_census.py` pins U01 as the only `/export` format
that writes speeds. It also shows a U01 written WITH SLOW/FAST reads back
with both, so the census's zero could have been a one.

## 2. Pro practice

- **Worksheets.** There are 19 Wilcom ES-65 worksheet PDFs from Kent's
  commissioned jobs (`scratch_kent/`, gitignored). Decoded through their
  ToUnicode maps, they list stitches, colours, stops, machine ("Tajima"),
  trims, max/min stitch, max jump and thread. They have **no speed or time
  field**: zero hits for speed, spm, rpm, slow, time or minute. Max stitch
  runs 6.6-12.1 mm, and min stitch 0.2-0.5 mm.
- **Commands.** Zero SLOW/FAST across 90 file reads: 28 pro DSTs, 17
  machine test files, 36 `scratch_corpus/` DSTs, and the 9 committed Becker
  DST/PES. DST cannot carry speed, so the DSTs prove little. The informative
  pair is the two Barudan `.dsb` test files, from a family that can. Their
  raw control bytes carry no slow or fast bit in 18,006 records.
- **Stitch lengths** (§5): 82.75% of the pro's stitches are 1-4 mm, and
  0.25% are ≥7 mm. Only 10 of 28 files have any stitch ≥7 mm. Playbook law 36
  (`docs/machine-physics-playbook-2026-07-31.md:61`) says firmware slows by
  itself for stitches over 3-4 mm. That is trade-sourced, not measured here.

## 3. EMB-Bot today

- **Sew time.** `src/sewtime.js:24-28` sets `PLAN_SPM = 650`, and `:58-69`
  computes `stitches/spm + trims×120/650`. The Python twin is
  `machine.py:843-844`. It is printed on the worksheet PDF
  (`src/pdfsheet.js:216-226`) and in the Studio row (`estimate.js:118-123`).
  The operator's typed speed (`QuoteSettings.svelte:46`) is capped at the
  nameplate (`quote.js:65-67`). **One speed for the whole design.**
- **Appliqué has per-step speeds that reach nobody.** The constants are
  `machine.py:1212-1214` (700/650 spm), and they are attached to each `Step`
  (`stage6_applique.py:780, 800, 1012, 1030, 1049`). The step IR is "BUILT
  BUT ORPHANED" (`docs/scope-digest/craft-laws.md:98`). Re-checked today:
  neither `adapter.py` nor the service serialises `step`.
- **Sew-out cards** estimate at 650 spm (`README-v3.2.md:13, 411`). Their
  scoring sheet has a `Speed (spm): ______` blank (`scoring-sheet-v3.2.md:9`).
  *Nitpick:* the card charges 3 s per trim and 30 s per colour change, while
  `sewtime.js` charges ~11 s per stop.
- **Nothing classifies stitches as challenging.** The playbook asked for
  `spm = f(stitch length histogram)` (`playbook:84`). Backlog row 6 built
  the flat 650 instead (`docs/scope/machine-physics-backlog.md:60`).

## 4. Where speed advice could live

Kent ruled on 2026-10-02 that nothing new reaches the customer readout (memory
`no-warnings-reaches-readouts`). That leaves three operator surfaces:

| Surface | Exists? |
|---|---|
| Worksheet PDF (`pdfsheet.js`, exported beside the file) | **Yes.** It already prints run time and spm |
| Sew-out card README + scoring sheet | **Yes.** They already record the speed sewn |
| The stitch file itself | Only for U01 (§1). Not DST, not PES |

## 5. Census: ours vs the pro's

`python -m tools.stitch_difficulty_census corpus` digitizes each fixture at
80 mm, left chest; `file PATH` reads any stitch file. Both use one pystitch
stream. `near hole` is a penetration within 0.5 mm of the 3rd-20th before
it. `peak` is penetrations per mm² in the densest 2×2 mm window.

| design | stitches | <0.5 | 0.5-1 | 1-4 | 4-7 | ≥7 | p95 mm | max mm | near hole | peak /mm² |
|---|---|---|---|---|---|---|---|---|---|---|
| becker_marine_logo | 6123 | 6.2% | 6.5% | 83.5% | 3.8% | 0 | 3.69 | 4.94 | 30.7% | 9.5 |
| logo_script_tires | 2724 | 9.5% | 3.8% | 84.1% | 2.6% | 0 | 3.86 | 4.61 | 26.7% | 12.2 |
| logo_bridge_bar | 17533 | 13.3% | 23.5% | 62.0% | 1.2% | 0 | 3.38 | 5.09 | 37.6% | 21.5 |
| logo_gaulke_roofing | 4843 | 6.6% | 21.9% | 71.2% | 0.3% | 0 | 3.02 | 4.84 | 26.8% | 13.5 |
| logo_golden_tee | 8311 | 3.9% | 30.7% | 65.1% | 0.3% | 0 | 2.91 | 4.94 | 19.3% | 31.2 |
| logo_hotel_fremont | 14272 | 8.5% | 30.5% | 61.0% | 0.0% | 0 | 3.0 | 3.0 | 34.6% | 18.0 |
| screenshot_phone_ui_golke | 8310 | 13.2% | 42.9% | 43.8% | 0.1% | 0 | 3.0 | 4.51 | 44.6% | 25.8 |
| logo_alpha | 5837 | 10.7% | 23.1% | 66.2% | 0.0% | 0 | 3.0 | 3.0 | 29.4% | 17.5 |
| logo_whitebg | 5807 | 10.7% | 23.0% | 66.3% | 0.0% | 0 | 3.0 | 3.0 | 29.6% | 15.8 |
| enthusiast_logo | 2418 | 9.4% | 26.4% | 64.2% | 0.0% | 0 | 2.69 | 3.0 | 34.6% | 10.2 |
| owl_kent | 32966 | 12.0% | 18.4% | 69.6% | 0.1% | 0 | 3.05 | 4.88 | 31.3% | 51.5 |
| **ours, pooled / median** | 109,144 | **10.4%** | **23.4%** | 65.7% | 0.5% | **0** | 3.0 | 4.61 | **30.7%** | 17.5 |
| **pro (28 DST), pooled / median** | 324,020 | 2.4% | 8.2% | 82.8% | 6.4% | 0.25% | 4.0 | 6.2 | 12.7% | 11.6 |
| test files (17) | 576,905 | 6.0% | 14.7% | 67.8% | 11.2% | 0.32% | 4.5 | 8.9 | 17.7% | 13.0 |
| `scratch_corpus` (36) | 365,825 | 3.7% | 8.9% | 78.1% | 9.3% | 0.01% | 4.0 | 5.3 | 19.8% | 9.3 |

No EMB-Bot file has a long-satin swing (≥7 mm, reversing >150°) or any
stitch ≥7 mm. Every file has zero slow/fast. Sharp turns (60-150°) read
3.7-12.0% for ours and a 6.2% median for the pro, so they separate nothing.

**What it says about speed.** Firmware's length-based slow-down would barely
fire on our files, whose p95 is 3.0 mm. Our risk is at the other end. We have
stitches under law 18's 1.0 mm satin floor (`playbook:17`) and penetrations
inside law 17's 0.5 mm same-hole radius (`:15`), at 2.4-3.2× the pro's rate.
Law 35 names penetration clustering as the usual cause of lettering breaks
(`:59`). Slowing down treats the symptom; the pro avoids the cause in
geometry. *Caveat:* these are different designs at different sizes (ours
80 mm, the pro's 38-89 mm), so compare distributions, not files. This census
does not split the short stitches by source.

## 6. Options for Kent

**(a) An operator-sheet line from the census. Measure-only, no format
change.** The worksheet PDF gains one line, e.g. *"Hard passages: N stitches
≥7 mm, M near an earlier hole."* *Cost:* about one session, because the
census must be ported to JS (lettering never reaches the Python engine,
`machine.py:840-842`). *Catch:* any "max spm" figure is a physical constant
(gate 1), so until a sew-out the line prints counts only. Per §5, those
counts would mostly report our own short, stacked stitches, which treats a
geometry defect at the machine.

**(b) Format-native slow-down, default-OFF.** Insert SLOW/FAST around
challenging passages in `plan_to_pattern`, for U01 only. *Cost:* half a
session. *Catch:* only Barudan U01 can carry it. Kent's machines read DST,
nobody here owns a Barudan, and so the gate-1 sew-out cannot be run. It is
built for no user.

**(c) Nothing on speed. The pros leave it to the operator.** *Cost:* zero.
*Catch:* run time stays one flat planning rate. The evidence supports this:
§2's 28 pro files and 19 worksheets carry no speed at all. The real follow-up
is §5's geometry lead: split our sub-1 mm and near-hole stitches by source
(ties, underlay, fill row ends, small shapes) before proposing any change.
That is about half a session, measure-only, with the same tool.

**Candidate speeds: GATE-1 CANDIDATES, UNSEWN, sourced only from in-repo
trade docs.** None is a default.

| Passage | Candidate | Source |
|---|---|---|
| Whole design, planning | 650 spm | `sewtime.js:24-28` (Tajima TMEZ, HAPPY) |
| Appliqué cover / trim-heavy | 600-800 / 600-700 spm | `docs/specialty-techniques-2026-08-01.md:252` |
| Caps | ~900 spm **vs** 600 (500-750) | playbook law 34 (`:55`) **vs** `specialty-techniques:527`: the sources disagree |
| Puff / 3D | 500-600 spm | `specialty-techniques:629, 798` |
| Long satin, dense small lettering, sharp corners | **no source** | none in repo; a number here would be invented |

If Kent wants (a) with a speed in it, the settling sew-out is to sew one card
at two speeds and record them on the existing `Speed (spm)` blank.
