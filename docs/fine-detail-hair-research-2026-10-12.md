# Fine detail and hair in thin thread — 2026-10-12

**Question (Kent):** "Thread is extremely thin, we should be able to
embroider hair! (Fonts shouldn't be an issue at all.)" What is the physical
floor per thread weight, how do professionals sew hair and fur, what does
EMB-Bot assume today, and what would a hairline tier and its first sew-out
look like?

Research only; no code changed. **Every number in §4 is a candidate from a
source, not a setting** — ROADMAP gate 1 (no sew-out, no physical constants)
applies to all of it.

Marks: **[V]** read on the owner's page today. **[A]** read on the owner's
page today by a second research pass, not re-opened by the writer (the
Madeira PDFs would not extract here). **[R]** read today on AllStitch, a
Madeira reseller; the text is the reseller's own. **[S]** search summary
only, unconfirmed. **[2]** a practitioner, not a vendor (a mark; there is no source 2). **[calc]** my
arithmetic.

Not repeated: decorator minimums and the 300 DPI story
(`docs/low-res-industry-practice-2026-10-10.md`); Laws 45–58
(`docs/lettering-mastery-2026-08-01.md`).

## Answer

1. **Thin thread is a real product line, three steps deep.** Madeira
   Polyneon No. 40 / 60 / 75 is about 27 / 17 / 11 tex, on needles
   60/8–75/11, 60/8–65/9 and 60/8 only; Amann's Serafil fine is sold as
   60 / 75 / 100 wt on 65 / 60 / 55 needles. No vendor sells a "hair"
   thread; fine detail is what 60–100 wt is for.
2. **No vendor publishes a thread diameter.** Melco publishes the floors
   nobody else does: run ≥ 1.5 mm, satin stitch ≥ 1.0 mm, fill ≥ 2.0 mm,
   column ≥ 1.0 mm, because a needle is 0.7–0.8 mm across and a stitch
   shorter than the needle breaks thread. **Fine thread moves density and
   lettering size, not stitch length** — the needle sets that. Amann's satin
   spacing per weight: 0.30–0.35 mm (60), 0.20–0.25 (75), 0.10 (100).
3. **Professionals sew hair with LONG stitches, not short ones.** Fur is
   randomised tatami at 4–6 mm, layered narrow satins with feathered edges,
   or Pulse's Fur Stitch; dark first, underlay off, edges rough; single
   strands are single runs laid over that ground. Short stitches are the
   named failure.
4. **A single strand already IS a hairline.** One run of 40 wt lays about
   0.4 mm; 60 wt about 0.32. The limits are the shortest stitch a curl
   needs and how close two strands can sit before they merge.
5. **EMB-Bot does not know what thread it sews.** No code mentions a thread
   weight; every floor assumes 40 wt / 0.4 mm on a 75/11. It already owns
   both hair techniques in some form — `fill_technique = "streamline"`
   (directional runs, built, not default) and `detail_layer` (lines as bean
   runs over the fill, built OFF). The gap is a **thread-weight profile**,
   not a new algorithm.
6. **Fonts sit on the same floor.** The trade's lettering minimum moves
   from about 6 mm (40 wt) to 3–5 mm (60 wt) and about 3 mm (75 wt), for
   the same reason. Kent is right above ~6 mm cap in 40 wt; below that, the
   thread decides.

## 1. The physical floor, per thread weight

| Weight | Linear density | Needle | Smallest lettering | Satin spacing | Src |
|---|---|---|---|---|---|
| 40 | dtex 135×2 ≈ 27 tex [A]; Wilcom ~27 [V] | 60/8–75/11 [A]; Wilcom 75/11 [V] | block 6–7 mm [R]; ≥ 6 mm on a 75 [V] | 0.40 (repo) | [1][4][5][19] |
| 60 | dtex 84×2 ≈ 17 tex [A]; Wilcom ~17 [V] | 60/8–65/9 [A]; Amann 65 [V]; Madeira UK "65" [V]; **Wilcom 70/10–75/11** [V] | 3 mm [V]; 4–5 mm [V]; 4 mm [R] | 0.30–0.35 [V]; Wilcom "finer" −0.03 [A] | [1][3][6][19][20][21] |
| 70 | ~14 tex [V] | 65/9–70/10 [V] | — | Wilcom −0.06 [A] | [1][21] |
| 75 | dtex 55×2 ≈ 11 tex [A] | 60/8 only [A]; Amann 60 [V] | ~3 mm "and slightly smaller" [V] | 0.20–0.25 [V] | [19][20] |
| 100 | Amann Serafil fine 420; WonderFil InvisaFil | Amann 55 [V] | "micro" (unsized) [A]; "small embroideries" [V] | 0.10 [V] | [8][20] |
| hair | **none found** | | | | |

- **Weight is a count, not a size.** Amann's wiki defines tex, dtex,
  denier and Nm and gives no ticket formula [A][23]; the folk "tex ≈ 1000 /
  wt" [S][9] says 25 for 40 wt where data sheets say 27. Use the dtex.
- **Diameter.** Not published: Amann measures it optically and gives no
  value [A][23]; Wilcom gives needle diameter only (Nm 75 = 0.75 mm) [V][1].
  DRAWings treats 0.4 mm as a standard thread's width [A][24], as the
  repo's Law 16 does (a LAID width — edge-to-edge for full cover). Scaling
  with √dtex [calc]: 60 wt ≈ 0.32 mm, 75 wt ≈ 0.26 mm. A trade-press line,
  "No. 40 is 25% thicker than No. 60" [A][2][28], agrees.
- **Minimum stitch length is the needle's floor.** Melco: 10 points = 1 mm,
  needles 7–8 points; walk ≥ 15, satin ≥ 10, fill ≥ 20; input points ≥ 1 mm
  apart; stitches shorter than the needle break thread [V][25]. Wilcom:
  small stitches "can damage fabric and cause thread or needle breakage",
  no number [V][10]. Groz-Beckert names DB×1 Nm 55 for "very small
  lettering" [A][26]. A practitioner: 0.5 mm danger, 1.0 "yellow", 1.5
  target [2][11]. Ink/Stitch: a global 1 mm floor destroys small satin
  (repo Law 51).
- **Run length on curves.** Wilcom: about 1.8 mm for tight curves, 4.0 mm
  for a hand-made look [V][12].
- **Minimum satin width.** Melco: 1.0 mm ("Min. Col. Width"); satin under
  ~1 mm is a named break cause [V][25]. This **corrects**
  `docs/trade-knowledge-2026-09-13.md` §5, which found no published floor.
- **When a single strand is sewable.** DRAWings: a single run is the
  0.4 mm base; at a 0.8 mm line it doubles the pass, at 1.0 mm triples,
  above 1.0 mm goes to satin [A][24]. No source publishes a narrower floor:
  a one-thread line is sewable at any length above the run minimum.
- **Fabric.** Madeira's backing guide puts water-soluble topping over pique
  because stitches sink in the nap, and says topping keeps "thin letters
  and fine details" crisp [A][27]. AllStitch: a tone-on-tone fill behind
  60 wt detail on polos, and tell the digitizer which areas are 60 wt
  [R][4]. Madeira UK aims fine thread at lightweight goods for less
  distortion [V][3]. Groz-Beckert: puckering rises with density, thread
  thickness and tension; needle size "hardly influences" it [A][26].

## 2. How professionals sew hair and fur

| Technique | Settings | Source |
|---|---|---|
| Randomised tatami | short fur 4 mm, offset .5/0, random 50; long fur 4–6 mm, offset 1/0, random 70–90 | Jesse Elliott, *Impressions* [2][14] |
| Layered narrow satins | stacked long narrow satins, feathered edges; light tatami underlay at 0.80 mm, others off | Hatch [V][15] |
| Open fill layers | open tatami layers blended up to density; underlays off | Hatch [V][15] |
| Directional fill + strands | tatami angled with the fur, freehand single runs for detail, Florentine to follow the body | Hatch [V][15] |
| Automatic | Fur Stitch: layers of jagged satin repeated through a shape | Pulse [V][16] |

- **Dark first, light over** [2][14]; Hatch blends lighter colours upward [V][15].
- **Direction carries the read**: near-vertical looks raised, horizontal flat [2][14].
- **No clean edge**: drop the edge-run underlay, leave it jagged [2][14][15].
- **Sourced failures:** too many stitches in a small area break or fray
  thread and warp fabric [2][14]; small stitches break thread and needles
  [V][10][25]; trims add roughness, so jump along the fill direction
  [2][14]; finer needles deflect and break more [S][17].
- **Not found on any vendor page:** bird-nesting with fine thread,
  registration drift between fur layers, 60 wt puckering. Hypotheses for
  the card, not facts.

**Hair is a texture of long, directional, layered stitches, not a field of
tiny ones.** The thin-thread question is how close strands can sit and stay
separate, and how short a run can go on a curl.

## 3. What EMB-Bot does today (`origin/main` f92cfd52)

`60 wt`, `thread_wt`, `threadWeight`: zero hits in `src/`, `app/src/`,
`digitizer/digitizer_core/`. Brand is chosen (`cfg.thread_brand`); weight
is not.

Constants that encode the thread (would become weight-aware):

| Constant | Value | Where | Note |
|---|---|---|---|
| `COVERAGE_THREAD_W_MM` | 0.40 | `machine.py:826` | is the thread |
| `SATIN_SPACING_MM` | 0.40 | `machine.py` | "threads just touch at 0.4" |
| `FILL_ROW_MM` | 0.15 | `machine.py:75` | from pro files, thread unknown |
| `RUN_MIN_AREA_MM2` | 0.16 | `machine.py:731` | = 0.4² |
| `MIN_LETTER_EXTENT_MM`, JS `CAP_FLOOR_MM` | 4.0 | `preflight.py:219`, `satinfont.js:82` | Law 48 consumables line |
| `STREAMLINE_D_SEP_DARK_MM` | 0.8 | `stage6_streamline.py:147` | "two thread widths" |
| `Fabric.needle` | 75/11 | `fabrics.py` | Law 21, 40 wt |
| JS `THREAD_WIDTH_MM` | 0.4 | `render.js:120`, `svgexport.js:77` | preview |

Needle-set, so a thinner thread alone does not move them: `MIN_STITCH_MM`
/ `MIN_COLUMN_MM` / JS `COLUMN_FLOOR_MM` 1.0 (`machine.py:26`,
`preflight.py:222`, `satinfont.js:81`), `SATIN_MIN_CROSS_MM` 0.5,
`BEAN_STITCH_MM` 0.73 × 3 passes. Not thread at all: `RUN_MIN_LOOP_MM` 2.2,
`TINY_STITCH_MM` 0.5, `TRIM_AT_MM` / `trim_at_mm` 3–4, `MAX_STITCH_MM` 12.1
(DST), `min_detail_mm` 1.5, underlay-off below 5 mm. `pull_comp_mm`: no
source either way.

Two facts worth Kent's eye:

- **The engine already sews under its own 1.0 mm floor.** The bean tier
  runs at 0.73 mm (14 pro outlines, p10 0.67) — under Melco's needle floor
  too — and `keep_thin_strokes` (ON, Kent 2026-09-13) raised Fremont's
  sub-1 mm satin stitches from 66% to 72%. `config.py` records that as a
  gate-1 question. It is this card's question.
- **The pro sews under it too.** Fremont's tagline at 92.5 mm: 2.2–2.9 mm
  letters on 0.82–0.90 mm columns (memory `pro-files-refute-scale-limit`).
  A DST carries no thread weight; Madeira's 3 mm 60 wt figure would fit.

**Fine-detail machinery that exists:**

- `stage6_satin._hairline_stretches`: a stretch under `SATIN_MIN_CROSS_MM`,
  three bean stations or longer, sews as a bean along its spine (both engines).
- `small_shape_rescue` ON; `keep_thin_strokes` ON (0.3–0.5 mm strokes kept,
  sewn as hairline beans); `lettering_min_column_mm` OFF (measured not to
  change the tier, DOCTRINE 2026-09-09).
- `detail_layer` OFF: FDoG lines from the photo as bean runs in one block
  sewn LAST over every fill — "strands over a ground".
- `fill_technique = "streamline"` (default `tatami`): Jobard–Lefer
  streamlines along the ETF direction field, docstring "fur, hair, panel
  flow"; 3.0 mm stitches, spacing 0.8 mm dark to 3.2 mm light, nothing in
  highlights; `layered` sews dark shade first. The §2 recipe, near enough.
- **Faces**: `faces_route_flat` (engine OFF, Studio ON; Kent 2026-09-30)
  sews a detected face flat. It supersedes the 2026-08-25 "tabled" note.
- **Metrics, not warnings** (Kent 2026-10-02): `edge_wobble_*`, `curve_*`,
  `STITCHES_TOO_SHORT`, `LETTERING_TOO_SMALL`. `min_px_per_mm` 4,
  `work_px_per_mm` 8 (0.125 mm/px: a 0.3 mm strand is ~2.4 px).

## 4. Proposal — a thread-weight profile and a hairline rule (not a build)

**The profile.** `thread_wt` **per colour block**, not per design: Madeira
says one design can mix thread counts [V][18] and suggests one needle per
head converted to a fine needle with 60 wt kept on it [V][3]. A DST carries
no thread data, so the worksheet must say which block goes on which needle —
the channel `Fabric.needle` already uses.

| Field | 40 wt (today) | 60 wt | 75 wt | Basis |
|---|---|---|---|---|
| laid width | 0.40 | ~0.32 | ~0.26 | Law 16, √dtex [calc] |
| satin spacing | 0.40 | 0.30–0.35 | 0.20–0.25 | Amann [V][20]; Madeira Classic 60 0.35 (Law 49) |
| run-tier area floor | 0.16 mm² | ~0.10 | ~0.07 | width² [calc] |
| column floor, min stitch | 1.0 | 1.0 | 1.0 | Melco [V][25]: needle-set |
| cap-height note | 4.0 mm | 3 mm | ~3 mm | [V][3][20] |
| streamline dark spacing | 0.8 | ~0.64 | ~0.52 | two widths [calc] |
| needle advice | 75/11 | 65/9 | 60/8 | [A][19], [V][20]; Wilcom says 70/10–75/11 for 60 wt [V][1] |

**The hairline rule.** Today a sub-floor stroke sews as a **three-pass
bean**: three widths of mark for a one-width stroke. Proposed: skeleton
width at or under one laid width → **one pass** along the skeleton; one to
~2.5 widths → two or three passes (DRAWings' 0.8 / 1.0 mm switch points
[A][24] are the published analogue); wider → satin. Stitch 1.5–2.0 mm
(Melco's 1.5 walk floor; Wilcom's 1.8 on curves), 1.0 mm only on a curl,
never under the needle's 0.7–0.8 mm. No underlay (Law 50; Hatch for fur).
Sewn last, over the ground, as `detail_layer` does. Trims per `trim_at_mm`;
needle-down hops between strands capped as the streamline tier's 8 mm is.

**Where.** Stage 7 picks the tier (it already routes sub-floor shapes to
the run tier first); stage 6 emits — `stage6_satin._hairline_stretches`
for flat-art strokes, `stage6_detail` for photo lines; JS mirror in
`satinfont.js` / `satinplay.splitByCrossFloor`.

**First sew-out card (candidates only, gate 1).** Same file, two hoopings:
pique + cutaway + water-soluble topping (Madeira's pique recipe [A][27]),
and twill + tearaway. Two needles: 40 wt on 75/11, 60 wt on 65/9.

- **A — single strands.** 25 mm straights and a 3 mm-radius S-curve at
  0.73 (today's bean), 1.0, 1.5, 2.0 mm stitches; one pass and three; both
  weights. 32 lines.
- **B — strand combs.** Five parallel 20 mm runs at 0.4, 0.6, 0.8, 1.2 mm
  spacing, both weights: where do strands stop reading as separate? The
  hair question.
- **C — narrow satin.** 0.6, 0.8, 1.0, 1.2 mm columns at each weight's
  candidate spacing: does 60 wt move Melco's 1 mm?
- **D — small caps.** One word at 2.5, 3, 4 mm cap, both weights, beside
  the existing card's block 5.
- **E — strands over ground.** A 15 × 15 mm mid-tone tatami with A's
  1.5 mm runs over it, dark and light.

Score per line: breaks (machine counter), gaps along the line, read at
arm's length, macro photo. Settles: hairline stitch length, one pass vs
bean, the 60 wt column floor and cap note, and per-weight streamline
spacing.

## 5. Fonts

Small lettering is bounded by exactly the floor hair is. Our font bands
are computed from a 1.5 mm column (`minCap = 1.5 / w5`,
`docs/lettering-mastery-2026-08-01.md`: 7–45 mm over 22 fonts), a 40 wt
number. The 69-font library (`tools/build-embf.mjs`) carries only an
authored `sizeMm`, no published minimum, and the Studio's `sizeBand` is a
0.75×–2× guess (`app/src/lib/fontFilter.js`).

| Thread | Smallest lettering quoted | Source |
|---|---|---|
| 40 wt | 6–7 mm block; ≥ 6 mm on a 75; most Hatch satin fonts 6 mm, run-stitch block 4 mm | [R][4], [V][5], [A][22] |
| 60 wt | 3 mm; 4–5 mm "very narrow bars"; 4 mm | [V][3], [V][20], [R][6] |
| 75 wt | ~3 mm "and slightly smaller" | [V][20] |
| 100 wt | "micro", unsized | [A][20] |

Law 48 already calls 4 mm a needle/thread boundary, not a legibility limit;
lowercase runs ~70% of cap [A][22]. So fonts are no issue above ~6 mm cap
in 40 wt; 6 down to ~3 mm needs 60 or 75 wt on a 65/9 or 60/8; under 3 mm
no source says any thread does it. A 60 wt profile would lower our bands;
only a sew-out says how far. Script and serif hairlines are the same
question as a strand of hair.

## What could still be wrong

- 60 wt lettering floors disagree (3, 4–5, 4 mm); the 6–7 mm 40 wt figure
  is only on a reseller's page; all are block letters.
- Wilcom pairs 60 wt with 70/10–75/11, Madeira's sheet with 60/8–65/9.
  Both primary; the card should test the needle.
- The [A] sources (Madeira sheets, Groz-Beckert, DRAWings, Hatch fonts,
  backing guide) were read by the second pass only.
- Diameters are derived, not measured; a microscope on the cones would
  replace the √dtex guess.
- Melco's floors are one vendor's service page, written for 40 wt.
- Density for 60 wt conflicts: +25% (reseller-hosted article [R][6]) vs
  "little to no adjustment" (Madeira UK). `FILL_ROW_MM` 0.15 came from pro
  files of unknown thread.
- The fur recipe is one practitioner's, in trade press.
- Not reached: a Schmetz chart (404), a Groz-Beckert thread table (it
  publishes none — "as thin as possible"), Isacord 60, Sulky, Gunold,
  Floriani, Brother, Bernina, Janome, Wilcom Sketch/Photo Stitch.

## Sources

- [1] Wilcom, "Thread thickness and needle size" — https://wilcom.com/resources/blog/thread-thickness-and-needle-size [V]
- [3] Madeira UK, "Sharper Lettering, Finer Detail" — https://www.madeira.co.uk/trend-focus/benefits-of-working-with-fine-threads/ [V]
- [4] AllStitch, "Embroidering with 60 weight thread" — https://allstitch.com/pages/embroidering-with-60-weight-thread [R]
- [5] Amaya (Melco distributor), "How small can I make my lettering" — https://help.amayauk.com/melco-how-small-can-i-make-my-lettering [V]
- [6] "Madeira ThreadWorks: advantages of 60 weight thread" (AllStitch) — https://allstitch.com/pages/madeira-threadworks-advantages-of-60-weight-thread [R]
- [8] WonderFil EU, "9 ways to sew with fine 80–100wt threads" — https://wonderfil.eu/blogs/news/9-ways-to-sew-with-fine-80-100wt-threads [V]
- [9] Thread weight / tex — https://jukijunkies.com/blog/thread-guide-tex-vs-thread-weight/ [S]
- [10] Wilcom ES 26, "Optimizing Stitch Quality" — https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/quality/Optimizing_Stitch_Quality.htm [V]
- [11] John Deer, running-stitch guide, Embroidery Legacy — https://embroiderylegacy.com/?p=28838 [2]
- [12] Wilcom ES 26, "Stitch length settings" — https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Digitizing/stitches/Stitch_length_settings.htm [V]
- [14] Jesse Elliott, "Digitizing Realistic Designs, Part 3: Animals", *Impressions* — https://impressionsmagazine.com/process-technique/digitizing-realistic-designs-part-3-animals/16283/ [2]
- [15] Hatch, "Digitizing Animals with Hatch Embroidery" — https://hatchembroidery.com/resources/blog/digitizing-animals-with-hatch-embroidery-free-king-parrot-design [V]
- [16] Pulse DG/ML 13.1, What's new — https://dgml14.pulsemicro.com/pulse-products-13.1-whatsnew.htm [V]
- [17] Amaya needle guide — https://www.amayauk.com/?p=7705 [S]
- [18] Madeira India, Polyneon 60 — https://shopindia.madeira.com/en/threads/polyester-polyneon/polyneon-60-1500--mtrs.htm [V]
- [19] Madeira data sheets — https://www.madeira.com/fileadmin/user_upload/Downloads/Data_Sheets/Data_Sheet_POLYNEON_40__EN.pdf (also `_60__EN`, `_75__EN`, `Data_Sheet_Classic_40__EN.pdf`, `Datenblatt_Classic_60__DE.pdf`) [A]
- [20] Amann, "Small embroidery designs: precision starts with the right thread" — https://www.amann.com/knowledgehub/blog/small-embroidery-designs-precision-starts-with-the-right-thread/ [V]
- [21] Wilcom ES 28, thread thickness and auto-spacing — https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/stitches/stitches-10.htm [A]
- [22] Hatch, "Choosing the right size embroidery lettering" — https://hatchembroidery.com/resources/blog/choosing-the-right-size-embroidery-lettering-for-your-project [A]
- [23] Amann wiki, thread numbering — https://www.amann.com/knowledgehub/amann-wiki/sewing-thread-numbering-explained-tex-nm-denier-and-ticket-numbers/fine-grade-specifications-for-sewing-threads-and-embroidery-threads/ [A]
- [24] DRAWings, "The running outline type explained" — https://www.drawstitch.com/blog/knowledge-base/digitizing-basics-the-running-outline-type-explained/ [A]
- [25] Melco service, "Stitches Too Small" — https://melco-service.com/source1/Stitches_Too_Small.htm [V]
- [26] Groz-Beckert, "Machine needles for single and multihead embroidery" — https://www.groz-beckert.com/mm/media/en/web/pdf/Machine_needles_for_single_and_multihead_embroidery.pdf [A]
- [27] Madeira USA backing guide — https://www.madeirausa.com/_resources/common/userfiles/file/Backing%20Guide.pdf ; Aqua topping — https://www.madeirausa.com/embroidery-supplies-guide/backing-guide/aqua-topping.aspx [A]
- [28] Lee Caroselli-Barnes, "How to digitize small lettering", *Impressions* — https://impressionsmagazine.com/how-to-digitize-small-lettering/ [A][2]
