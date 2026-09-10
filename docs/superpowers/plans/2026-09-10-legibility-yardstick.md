# A yardstick that can see what Kent sees: legibility on the render, the un-clamped score, and the thread-match floor (2026-09-10)

**Status: PLANNED — Kent's pick 2026-09-10 ~20:00Z ("Item 11 and 1", in that
order), after the region-colour flip (#448).** Quality review 2026-09-08
item 11. Phase 1's exit is that the metric's ranking agrees with Kent's eye;
this plan closes the three measured ways it cannot, before item 1 (the
real-logo lane) moves every gradient fixture and needs a grade that moves
with it.

## 0. What already governs this — read before changing the plan

- **The score is `100 − 30·blocks − 12·warns`, clamped at 0**, and the grade
  letter is read off the clamped number (`preflight.run_preflight`).
  `metrics["raw_score"]` has carried the unclamped value since 2026-09-06
  (yardstick-disagreements row 6) — INERT until the scorecard baseline is
  recaptured, because `corpus_scorecard._metric_deltas` intersects key sets
  and the stored baseline (`captured_at_commit 6180cca`, 2026-09-04)
  predates the key. 12 of the corpus's 52 design/garment combos sit on
  exactly 0 with true scores from −272 to −38 (`tools/floor_depth.py`).
- **`THREAD_MATCH_POOR` has no area floor** (row 3): per thread, judged on
  the thread's WORST graded patch; the worst shape behind a blocking finding
  runs 0.58–1,648 mm² across the seven F fixtures, 12 of 23 under 5 mm².
  Every sibling floors: `_UNCOVERED_MIN_PATCH_MM2` 5.0 mm²,
  `_COVERAGE_MIN_PATCH_MM2` 25.0, lettering 4.0 mm. The finding already
  carries `worst_shape_area_mm2`; its own comment records the floor as "a
  product call that re-bases the scorecard for at least four fixtures
  (recorded, not proposed)". Item 11 proposes it and Kent picked item 11.
- **The gradient lane is JUDGED on raw distance; the photo route on excess
  over the best loaded spool** (row 4, 2026-08-24). Excess is REPORTED on
  every route since 2026-09-06; only the scoring differs. Four of the seven
  F fixtures clear every block under excess. Whether the gradient lane
  should be judged on excess is a product call (a logo's palette can be
  changed, a photograph's cannot) — recorded, never taken. It stays Kent's;
  §5 puts it to him with today's numbers.
- **Sewn-but-illegible counts as covered.** `tools/dropped_elements.py`
  reads 0.2% on Hotel Fremont, whose tagline Kent calls "completely lost"
  (kent-review 08-27, 09-03). `tools/legibility.py` (PR 1 of the thin-stroke
  plan, 2026-09-08) is the instrument that reads what the thread SAYS: per
  text cluster, the same millimetres cropped from the prepped artwork and
  from `stitchviz.render_design`'s thread render, tesseract on both, the
  normalised edit similarity between the readings. It lives in `tools/`,
  runs only by hand, and nothing in preflight, the scorecard or the flip
  sheet reads it. Its measured limits stand and are not re-litigated here:
  OCR is a LOWER bound on lettering loss (Fremont's THE reads 1.00 on a
  render showing T H C — tesseract's word model fills the arm in;
  `thin_strokes.py` sees that arm at 74% recall); a cluster the art side
  cannot read (Becker at 1.46 px/mm) contributes nothing rather than a
  false zero; a tagline that is not a text cluster is invisible to it.
- **Gate 4** — no quality claim on a raw agreement number. Edit similarity
  is a distance with no chance floor claimed for it; the grade's raw score
  is a sum of deductions. Neither is an agreement rate; neither is reported
  as one.
- **Determinism.** Legibility needs the `tesseract` binary. CI installs it
  (`python-package-conda.yml`), this container has 5.3.4, Kent's box has it
  for the Studio's Convert-to-text pass; the OCR tests skip without it
  (`conftest.requires_tesseract`). A finding whose presence depends on a
  binary must never move a test that pins another finding, and must never
  be silently absent: the report says `legibility_checked`.
- **Kent's eye, on the record** (kent-review-2026-08-27.md, the fourteen
  stitch-outs; kent-review-2026-09-03.md): Fremont "EAT | STAY | PLAY was
  completely lost. EST on top was dropped out. THE is incomplete"; Bridge
  Bar "Resturant was dropped completely … BRIDGE text should be cleaner";
  drone "the left side trees were lost … the E on drone"; summit "Text on
  the bottom was dropped out"; Becker "the C infill was completely lost";
  ENTHUSIAST "the red arm … was lost" (the lettering itself reads). These
  are the calibration rows for §4.2.

## 1. The gap, in one sentence each

1. A design 312 points under water cannot register a fix (row 6 → row 1).
2. A 0.58 mm² shard and a 1,648 mm² field get the same "do not sew" (row 3).
3. Lettering the thread no longer says scores as covered (kent-review 09-03).

## 2. The design

Three changes to the yardstick, each measured on the corpus before it is
made, none of them a stitch:

- **(a) `THREAD_MATCH_POOR` gets the sibling floor.** A graded row whose
  footprint is under `_THREAD_MATCH_MIN_PATCH_MM2` — one constant, equal to
  `_UNCOVERED_MIN_PATCH_MM2` (5.0 mm²), the floor the uncovered check
  already uses for "a patch worth a finding" — cannot set a thread's
  severity. The thread is judged on its worst patch AT OR ABOVE the floor;
  sub-floor offenders are still listed in `extra.regions` (a review screen
  can point at them) under `sub_floor: true` and counted in
  `extra.sub_floor_count`, and a thread whose only offenders are sub-floor
  emits no finding, exactly as `_uncovered_findings` drops a sub-floor
  patch. The footprint is the row's own graded pixel count over
  `px_per_mm²` — the eroded, aligned mask the grader scored, so a shade band
  is floored on its own area and not its parent region's. Ships ON: it is
  the item's explicit deliverable and a scoring rule, not a physical
  constant (gate 1 does not apply); the movers are named in §4.1 and the
  scorecard recaptured with them attributed.
- **(b) The un-clamped score is READ, not just carried.** `flip_sheet.py`
  rows record `raw_score` beside `score`, the report prints both and reads
  its grade-up / grade-down verdicts off `raw_score` (a floored design
  moving −272 → −180 is "better", which is what row 1 asked for);
  `corpus_scorecard.diff` prints `raw_score` on its score line; the
  baseline is recaptured so the key is live. The operator's number in the
  Studio stays clamped — a negative grade means nothing at the machine —
  and the letter is unchanged. MASTER_SCOPE's convention becomes "F 0
  (raw −272)" wherever a floored grade is quoted.
- **(c) Legibility as a preflight check, `cfg.legibility_check`, DEFAULT
  OFF until Kent rules on §4.2's table.** The measurement moves from
  `tools/legibility.py` into `digitizer_core/legibility.py` (the tool
  becomes a thin CLI over it; its tests keep passing); `run_preflight`
  runs it when the flag is on, the artwork is given (`image=` — the same
  contract the thread-match check has) and tesseract is present, and
  writes `metrics["legibility_checked"]`, `legibility` (the design-level
  figure, weighted by the art reading's length), `legibility_worst` and
  `legibility_clusters`. One finding per design, `LETTERING_ILLEGIBLE`,
  aggregated like the lettering and thread checks: the worst readable
  cluster judges, every cluster rides in `extra.clusters` with both
  readings and confidences, and the message says which words the thread
  does not say. Severity thresholds are §4.2's — proposed from the
  corpus against Kent's words, ruled by him. When the flag is off, or
  tesseract is absent, or `image` is None (the re-score path), nothing is
  emitted and `legibility_checked` is False, so no pinned test moves and
  a missing check is never mistaken for a clean one.

Not in this plan: making `dropped_elements` itself legibility-aware (it
measures colour disagreement per pixel; legibility is a different question
and gets its own number beside it), and the yardstick swap (§5, Kent's).

## 3. Instruments first

- **`tools/thread_match_floor.py`** — every `THREAD_MATCH_POOR` row across
  the scorecard matrix (26 fixtures × 2 garments at 80 mm, the engine's 12
  colours) with the worst offender's graded footprint, then the same
  findings under the floor: which severities move, which findings vanish,
  which grades and raw scores move. The number 5.0 is the sibling's; the
  sweep also reads 2.0 and 10.0 so the choice is seen, not assumed.
- **`tools/legibility.py --corpus`** re-run on today's engine at the
  Studio's 6 and the engine's 12, per cluster, against Kent's words
  (§0), with the cost of the read measured separately from the digitize
  (an in-service check is paid on every generate).
- **`tools/floor_depth.py`** re-run for the raw-score table on today's
  engine (the 2026-09-06 numbers predate eleven flips).

## 4. Measured

### 4.1 The thread-match floor

`tools/thread_match_floor.py`, the scorecard matrix (26 fixtures × 2
garments at 80 mm, the engine's 12 colours), one digitize per pair and
preflight once per floor. **The old check (floor 0) carried 40 blocking
`THREAD_MATCH_POOR` findings over the 52 pairs; the patch that judged them
runs 0.21–1,564 mm², p50 8.74, and 16 of the 40 sit under 5 mm²** (8 under
2, 24 under 10). The sixteen: gaulke's `4174` on a 0.21 mm² patch (the
0.58 mm² shard of row 3), the screenshot's `1776` 0.92, `0108` 1.03, `0142`
2.13 and `3900` 4.32, drone's `3335` 1.92 and `0111` 2.52, Golden Tee's
`0532` 2.41 — each on both garments. Nothing else in the report changes:
warns 70 → 70 (a thread whose blocking patch was sub-floor is judged on its
next patch, and two of them land as warns), the other checks untouched.

| floor | tm blocks | tm warns | all blocks | pairs on the 0 floor | grade moves | raw sum |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (the old check) | 40 | 70 | 40 | 10 | — | 2,164 |
| 2 | 34 | 70 | 34 | 10 | 2 | 2,344 |
| **5 (shipped)** | **26** | **70** | **26** | **10** | **2** | **2,584** |
| 10 | 18 | 68 | 18 | 8 | 4 | 2,848 |

**At the shipped 5.0 mm²: 14 blocking findings gone, no design leaves the
0 floor, two grades move** — gaulke D 46 → **B 76** on both garments (its
one thread block rode the 0.21 mm² patch; nothing above the floor offends),
and the floored designs rise where the letter cannot show it: drone raw
−140 → **−80** (4 → 2 blocks: `1102` on 201 mm² and `1776` on 1,564 mm²
stay), the screenshot −116 → **−38** (6 → 3), Golden Tee −92/−104 →
−50/−62 (2 → 1: `0703` on 81 mm² stays). Bridge Bar is unmoved at 5 (its
two blocks, `4423` and `1375`, judge on 9.5 and 9.8 mm² patches — the
shards the region-colour PR named); at 10 they would go and it would read
C 64 / D 52, which is why the sweep reads 10 too and why 5 is the number:
a 10 mm² shard of a wordmark is a shard someone sees, and the sibling that
already floors at 5 has never been argued up. The synthetic photo stub,
the blobs, the repro and summit keep every block (patches 15–1,237 mm²).

### 4.2 Legibility on today's engine, against Kent's eye

`tools/legibility.py --corpus` on this engine (the ten real-art fixtures
at their review sizes; `logo_drone_thermal_badge` is byte-identical to
`drone_render` and runs once), at the Studio's 6 and the engine's 12, with
the read now floored at three letters of ART truth (`ART_MIN_LETTERS`).
Per cluster, `art (confidence) → render (confidence) | similarity`;
`unsewn` is a cluster none of whose shapes sews and is the unsewn warnings'
business, never this check's.

| fixture | at 6 | at 12 | what Kent said (08-27, 09-03) |
|---|---|---|---|
| `enthusiast_logo` | ENTHUSIAST 95 → 93 **1.00**; ENTERPRISES INC 96 → 91 **0.93** (1.6 mm) | same | the lettering reads; "the red arm was lost" is not lettering |
| `logo_hotel_fremont` @ 92.5 | THE 96 → 83 **1.00**; HOTEL FREMONT 80 → 66 **0.74** (the ART reads "HOTELFREMOWWEAA" — banner noise; the render "HOTELFREMOTR") | same | "THE is incomplete" (the E's arm — invisible to OCR, `thin_strokes` sees it); HOTEL FREMONT's letters sew at 99–100% stroke recall — **0.74 is art-side noise, not loss** |
| `logo_bridge_bar` | one 49 mm cluster; art reads "X" — no truth (floored) | no cluster; whole design "GRIDGE4RESINS" 72 → "EY" 60 **0.13** | "Resturant was dropped completely … BRIDGE text should be cleaner" |
| `logo_golden_tee` | one 51 mm cluster; art reads "TL" — no truth (floored) | same | — |
| `logo_gaulke_roofing` | C GOLKE INDUSTRIES STEEL… 94 → 46 0.21, **unsewn** (enclosed holes; item 9 sews them on a light garment) | same | the lettering is the unsewn population's, not this check's |
| `drone_render` | DRONE 80 → 58 **0.22** (3.1 mm; "DROM" → "VR74A"); two clusters unreadable on the art | 80 → 70 **0.36** ("NOORONK") | "the E on drone … minor details were omitted" |
| `screenshot_phone_ui_golke` | NVISK 88 → 17 **0.00** (3.4 mm); 5G4 81 → 72 **0.00** (2.8); SPOTIFY 92 → 52 **0.50** (2.0); C GOLKE INDUSTRIES SNOW PLOWING 94 → 58 **0.59** (9.1); "I" floored | 0.00 / 0.00 / **0.50** / **0.56** | (not on his list — 2–3 mm UI text at 80 mm) |
| `becker_marine_logo` @ 100 | art unreadable at 1.46 px/mm; the render reads BECKER 96, MARINE 95 | same | — |
| `logo_script_tires` | script, neither side reads | same | — |

**The cost, measured beside the digitize on this box under load** (the read
alone, `legibility.measure`, at the Studio's 6): Fremont 8.3 s for 48
tesseract calls (2 clusters), ENTHUSIAST 6.8 s / 48, gaulke 7.4 s / 48,
Bridge Bar 3.7 s / 24, drone 12.6 s / 72, the screenshot 16.8 s / 120 (5
clusters) — about 24 calls and 3.5 s per cluster, against digitizes of 11 s
(ENTHUSIAST) to 135 s (Fremont). Paid on every generate once the flag is
on; the art side (18 of the 24 calls) could be cached per artwork if that
matters.

**Looked at — `docs/renders/legibility-2026-09-10/`, the OCR crops
themselves (the binarised, upscaled input tesseract read; thread drawn as
filaments).** The number is trustworthy at its ends and noisy in the
middle, and that is the finding that sets the thresholds:

- **Fremont's HOTEL FREMONT, 0.74**: the render reads HOTEL FREMON(T)
  cleanly — bold, every letter whole. The art crop carries the banner tail
  under the wordmark, which is where "WWEAA" on the ART reading comes from.
  Art-side noise; not loss.
- **The screenshot's 9 mm GOLKE line, 0.59**: "C GOLKE INDUSTRIES / SNOW
  PLOWING DIVISION" reads to a person, a little blobby. OCR gets half of it.
- **drone's DRONE, 0.22 at 6 / 0.36 at 12** (3.1 mm): a person reads
  "DRON" and an E that has lost its arms — Kent's "the E on drone". Damaged,
  not lost.
- **The screenshot's SPOTIFY, 0.50** (2.0 mm): blobs. Tesseract's "SETHY"
  shares three letters by luck. Lost — and `LETTERING_TOO_SMALL`'s row.
- **NVISK, 0.00** (3.4 mm): three blobs. Lost.
- **Bridge Bar, whole design at 12, 0.13**: the render shows "Bridge" in
  script, readable, and BAR & RESTAURANT gone — "Resturant was dropped
  completely". Real loss, on a design whose script the OCR cannot parse
  either way.

So DRONE at 0.22 reads and SPOTIFY at 0.50 does not: **no similarity band
separates lost lettering from damaged lettering**, and a block/warn split by
this number would block a design a person can read (drone under the first
provisional 0.5) and warn on one whose letters are clean (Fremont under
0.75). What the number can carry honestly is ONE band: under 0.5 the thread
does not say what the art says, on every row Kent named or no eye reads
(Bridge Bar 0.13, DRONE 0.22 / 0.36, NVISK and 5G4 0.00), and it is silent
on every row that reads (GOLKE 0.59, HOTEL FREMONT 0.74, ENTHUSIAST, THE).
SPOTIFY at exactly 0.50 is the one miss, and it is 2 mm lettering the size
check already names. **The provisional constants are therefore
`LEGIBILITY_WARN` = 0.5 and `LEGIBILITY_BLOCK` = 0.0 — a warn, never a
block — and the two-band alternatives are put to Kent in §5 with what each
one gets wrong.**

### 4.3 The floor depth today

From the same sweep, on this engine (the 2026-09-06 figures predate
eleven flips): **10 of the 52 pairs sit on the clamped 0 under the old
check, with raw scores from −140 to −26** (2026-09-06: 12 of 52, −272 to
−38 — the colour bundle and the region colour took two pairs off the floor
and lifted the rest). Under the floor the same ten stay on it — drone −80,
the screenshot −38, Golden Tee −50/−62, the blobs −56, summit −26 — which
is the row-1 mechanism in one table: **three of the ten just gained 42–78
points and the printed grade shows none of it.** `raw_score` now rides on
the flip sheet's rows and verdicts and on the scorecard's score line, so
the next such fix reads as one.

### 4.4 The recapture, and what the diff attributed

`tools/corpus_scorecard.py diff` against the 2026-09-04 baseline (lane
commit `6180cca`, not on main): **46 of 52 pairs moved.** This PR's floor
accounts for the `THREAD_MATCH_POOR` count moves on drone (block ×4 → ×2),
gaulke (F 0 → B 76 — `4174` went with the enclosed-background rule on
09-06, `1375` with the subpixel re-pin on 09-09, `3971` with the floor),
Golden Tee (×2 → ×1) and the screenshot (×10 → ×3, the rest of that fall
the colour bundle's) — exact, because the sweep reads the same pairs at
floor 0. Everything else is the engine since 09-04: the colour bundle and
the region colour (Bridge Bar F 0 → F 4 / 16, meadow D 52 → C 64, summit's
warn, the scene stub's trims, the repro at hat_front 46 → 58), the satin
work of 09-08/09 (script_tires at hat_front B 88 → A 100, the owl's
stabilizer info), and metric-only drift on the rest (the subpixel flip
moved every polygon by a pixel). **Two grade drops were bisected on
main's first-parent history rather than attributed by class:**
`photo_grass_macro` B 76 → D 40 at **#432** (the subpixel flip; D 52 since
#437 — `LETTERING_TOO_SMALL` and `STITCHES_TOO_SHORT` appeared on a photo
fixture with no lettering), and `becker_marine_logo` at hat_front B 88 →
B 76 at **#433** (junction clustering — `ARTWORK_UNCOVERED` appeared on
the cap's density only; that PR measured Becker's bare area on left_chest).
Neither is this PR's; both are named in the recapture commit and left as
a follow-up. Captured 2026-09-10 at `9f3d09c`.

## 5. Decisions — Kent's

1. **`LETTERING_ILLEGIBLE`'s severity rule, and the flip of
   `cfg.legibility_check`.** Built warn-only under 0.5 (§4.2). The options,
   each with what it gets wrong on the crops:
   - **(A) warn under 0.5, never block** — as built. Misses SPOTIFY (0.50,
     blobs at 2 mm; the size check has it). Blocks nothing, so a design
     whose lettering is entirely gone still says "warn".
   - **(B) block under 0.2, warn under 0.7** — blocks Bridge Bar (0.13:
     "Bridge" reads, RESTAURANT is gone), NVISK and 5G4; warns the GOLKE
     line (0.59) that reads cleanly.
   - **(C) block under 0.5, warn under 0.75** (the first provisional) —
     blocks DRONE, which a person reads with one letter lost; warns
     Fremont, whose letters are clean.
   - **(D) keep the check OFF** as an instrument, and read `legibility` in
     the scorecard only.
   The flip: (A) or (B) ON in the Studio's preflight costs about 3.5 s per
   text cluster per generate today (§4.2); the report says
   `legibility_checked` either way.
2. **Whether the gradient lane is JUDGED on excess like the photo route**
   (yardstick-disagreements row 4). Under the floor `THREAD_MATCH_POOR`
   still blocks 26 times over the matrix, all on the gradient lane's raw
   yardstick, and four of the seven F fixtures cleared every block under
   excess on 2026-09-06. A logo's palette can be changed, a photograph's
   cannot — which is why this stayed a product call. Not taken here.
