# Does ARTFID's ranking agree with an eye? — 2026-09-11

**Result: on the pre-registered primary, no — but the test was underpowered by
construction, so read this as "no evidence of agreement", not "proven
independent".** The more useful findings are the ones the disagreements point
at, and one of them reverses the obvious reading of the table.

Instrument: `digitizer/tools/artfid_eye_rank.py`. Linux, python3.12,
CI-pinned `requirements.txt`, `tesseract-ocr` present. Fourteen tracked
fixtures, one digitize each.

The ranking was made from blind pairs — opaque labels, no scores, no
fixture names — and **committed to git before the scores were read**
(`docs/artfid-eye-ranking-2026-09-11.json`, commit `18aa55b`). `--reveal`
refuses to run until that file exists. The git timestamp is the audit trail;
that is the whole point of splitting the two commands.

**The eye here is Claude's, not Kent's.** This instrument is a cheap proxy
that says *where* to spend the expensive human pass, not a substitute for it.
Every number below inherits that.

---

## 1. The pre-registered result

| | n | Kendall tau-b | p |
|---|---|---|---|
| **PRIMARY** — non-refused, non-contaminated | 7 | **+0.048** | 1.000 |
| SECONDARY — all rows | 14 | +0.275 | 0.193 |

tau-b is chance-corrected by construction (0 = the agreement of unrelated
rankings), which is how ROADMAP **gate 4** is satisfied here — by the
statistic, not by a caveat. No "% agreement" appears in this document.

**The primary is underpowered, and that is a defect in my own instrument.**
Six of fourteen fixtures are refused by `score_image` and one more is the
contaminated control, leaving n=7. A seven-point tau cannot detect even a
moderate correlation. The honest statement is that the pre-registered test
came back null *and could not have come back much else*. Anyone re-running
this should widen the fixture set first.

## 2. The full table, in eye order

| lbl | fixture | eye | fid | Δ | ARTFID | cov | col | str | stitches | route | grade | refusal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| K | bg_uncertain | 1 | 2 | −1 | 95.6 | .963 | 1.00 | .916 | 10,384 | flat | B | |
| F | ribbon_curve | 2 | 8 | −6 | 87.5 | .753 | 1.00 | .925 | 991 | flat | A | |
| G | logo_script_tires | 3 | 9 | −6 | 85.8 | .794 | 1.00 | .828 | 2,345 | **photo_scene** | B | |
| H | logo_whitebg | 4 | 6 | −2 | 90.2 | .886 | 1.00 | .851 | 5,745 | flat | A | |
| I | logo_alpha | 5 | 5 | 0 | 90.4 | .888 | 1.00 | .855 | 5,774 | flat | A | |
| L | becker_marine | 6 | 7 | −1 | 87.7 | .839 | 1.00 | .832 | 6,603 | flat | B | *contaminated* |
| M | logo_hotel_fremont | 7 | **1** | **+6** | **95.9** | .962 | 1.00 | .926 | 13,231 | gradient | C | ink ambiguous |
| A | enthusiast_logo | 8 | 13 | −5 | 78.5 | .653 | 1.00 | .783 | 2,492 | flat | B | |
| N | logo_golden_tee | 9 | 12 | −3 | 81.9 | .700 | 1.00 | .826 | 6,795 | gradient | F | ink ambiguous |
| C | region_blobs | 10 | 3 | **+7** | 92.8 | .935 | .976 | .887 | 18,884 | gradient | F | |
| B | logo_bridge_bar | 11 | 4 | **+7** | 92.4 | .957 | .840 | .946 | 14,386 | gradient | F | ink ambiguous |
| J | summit_badge | 12 | 11 | +1 | 82.3 | .785 | 1.00 | .740 | 19,253 | gradient | F | ink saturates 100% |
| D | drone_render | 13 | 10 | +3 | 85.5 | .874 | .830 | .850 | 17,376 | gradient | F | ink ambiguous |
| E | logo_gaulke_roofing | 14 | 14 | 0 | 32.2 | .065 | 1.00 | .132 | 11,131 | gradient | B | subject mismatch 4.3× |

## 3. The finding that reverses on inspection

The table invites an obvious conclusion, and it is wrong. Recorded here
because the next person will reach for it too.

**The naive reading.** Preflight grade appears to beat ARTFID badly at
matching the eye — tau **+0.559** (p=0.011) against ARTFID's **+0.275**
(p=0.193). Tempting headline: *the repo already has a better instrument and
it is free.*

**The confound.** `route == flat` **alone** predicts the eye at tau
**+0.575** (p=0.014) — better than preflight grade does. Grade F is almost
exactly the set of gradient-route fixtures. Preflight grade was proxying the
route, not out-measuring ARTFID.

**Holding route constant reverses it.** Within each stratum ARTFID is the
*better* of the two, in both directions:

| stratum | n | preflight vs eye | ARTFID vs eye |
|---|---|---|---|
| non-flat routes | 8 | +0.229 (p=0.469) | **+0.429** (p=0.179) |
| flat routes | 6 | +0.258 (p=0.513) | **+0.467** (p=0.272) |

So the real shape of the problem is **not that ARTFID is a poor metric. It is
that ARTFID is not comparable ACROSS routes.** Within a route it tracks the
eye moderately; pooled, it fails, because gradient-route designs score
systematically higher than they look. That is a Simpson's-paradox pattern and
it changes what to fix: normalise or stratify per route, rather than
re-weighting components.

**Alternative explanation, not excluded.** The flat fixtures are also the
*easier artwork* (a slotted rectangle, a single curve, synthetic shape
sheets). "Flat routes look better" may be "flat fixtures are easier", not
"the flat lane is better engineered". The fourteen-fixture set confounds
route with difficulty and cannot separate them. Doing so needs hard artwork
digitized down both lanes.

## 4. What the disagreements actually name

**Three top-quartile ARTFID scores the eye does not endorse**, all gradient
route, all sewing ground they should have dropped:

- **M — 95.9, the highest score in the set.** Lost the rope border, `EST
  1895`, and `EAT | STAY | PLAY` entirely; sewed the badge interior in white
  thread. Its hero wordmark is genuinely the best text in the set, and the
  metric appears to be scoring that plus the sewn ground.
- **C — 92.8 (3rd).** Subject faithful, but the blank ground becomes a
  full-frame thread mass, plus an invented cyan wedge.
- **B — 92.4 (4th).** `BAR & RESTAURANT` destroyed to a featureless swoosh; a
  teal invented that exists nowhere in the artwork.

**Two clean reproductions the metric ranks mid-table:** F (991 stitches, a
faithful satin curve) at 8th, G (a fully legible script wordmark) at 9th.

**The refusal classes are load-bearing and working.** M, B, D, N, J and E all
carry a refusal, so `score_image` already says *do not read this row as an
engine result*. ARTFID-plus-refusals is honest; ARTFID's ranking taken alone
is not a usable quality ordering. The cost is that refusals cover six of
fourteen, so the metric can only speak to half its own fixture set.

### Component behaviour

| component | weight | min | max | spread | at exactly 1.000 | tau vs eye |
|---|---|---|---|---|---|---|
| coverage | 0.40 | .065 | .963 | .898 | 0/14 | +0.165 (p=0.451) |
| colour | 0.25 | .830 | 1.000 | .170 | **11/14** | +0.454 (p=0.045) |
| structure | 0.35 | .132 | .946 | .814 | 0/14 | +0.275 (p=0.193) |

- **`colour` is constant on eleven of fourteen fixtures** while carrying a
  quarter of the composite. It reads 0.976 on C and 0.840 on B — both of
  which *invented a colour that is not in the artwork*. That is by design, not
  a bug: `colour_score` measures excess over the **best available spool per
  region** — thread-choice quality — so an invented colour is invisible to it
  as long as the invention is itself close to some spool. It is a sparse
  signal that happens to fire correctly when it fires.
- **The heaviest component tracks the eye least.** With n=14 these three tau
  values are not statistically distinguishable from each other, so this is a
  lead, not a verdict.

### A stage-0 misroute, found in passing

**`logo_script_tires.png` — flat black script on white — routes as
`photo_scene`.** It still produced one of the better results, so nothing is
on fire, but a flat two-colour wordmark taking the photo lane is worth a
look on its own.

## 5. Scoring my own pre-registered predictions

Recorded in `18aa55b` before unblinding. Two right, one wrong, one half.

1. **"Lexically-damaged fixtures will score better than the eye ranks them."**
   ✅ 4 of 5 (M +6, B +7, D +3, J +1; N −3 against).
2. **"D will be the single largest disagreement."** ❌ **Wrong.** D is +3. The
   largest are C and B at +7.
3. **"Metric and eye will agree E is terrible."** ✅ Strongly — ARTFID 32.2,
   both rank it 14th, Δ=0. Coverage .065 catches the polarity inversion
   exactly as predicted.
4. **"K and F should top the metric."** ⚠️ Half. K is 2nd; **F is 8th.**

## 6. Statistical honesty

**About twenty correlations were computed here, and only the first two were
pre-registered.** A Bonferroni threshold for twenty tests is p ≈ 0.0025.
**Nothing in this document survives that**, including the route finding
(p=0.014) and the preflight confound. The closest is stitch count against the
eye at **tau = −0.560, p = 0.005** — the eye penalises stitch count strongly,
which is the most robust single relationship found and the one worth
replicating first.

Note that **ARTFID itself is uncorrelated with stitch count** (tau=+0.121,
p=0.591), so my own "the metric just rewards more thread" hypothesis was
**wrong**. What is true is narrower and more interesting: stitch count
predicts *visual* quality strongly and negatively, and ARTFID is blind to a
cheap signal that is already computed on every design.

Everything in sections 3, 4 and 6 is **exploratory and needs replication on a
wider fixture set.** Section 1 is the only confirmatory test, and it is null.

## 7. What this does and does not license

- **Does not** settle any physical constant (gate 1), and is not a sew-out.
- **Does not** license moving a threshold. `artfidelity_tune.py` already
  carries the warning about optimising the metric you are handed, and a
  metric this session just showed to be route-incomparable is exactly the
  wrong thing to optimise against.
- **Does** give ROADMAP phase 1's exit condition an instrument where it had
  none, and a reproducible protocol for re-running it.
- **Does** name three concrete leads, in priority order: cross-route
  comparability (§3), the `colour` component's 11/14 saturation (§4), and
  the `logo_script_tires` misroute (§4).

## 8. Follow-up, same day: the letterbox fix, and what it proved

Kent picked the worst finding in §4 to act on — `logo_gaulke_roofing`, the
phone screenshot whose black bars read as ink and inverted the whole design.
`digitizer_core/letterbox.py` strips letterbox bars in both
`stage0_classify._load` and `stage1_prep._load` (both, deliberately: stage 0
owns its own decode, and if only one stripped, classification and prep would
see different pictures).

**The fix works, and only a render could show it.** Before: white thread on
white cloth, the logo as negative space, unusable. After: both text lines
fully legible in black, the mark solid and correctly polarised. Blast radius
is one fixture — 13 of 14 come back byte-identical on route and stitch count,
and black letterboxing round-trips byte-for-byte on both axes across five
fixtures and three bar sizes.

### It ships behind `cfg.strip_letterbox`, DEFAULT OFF

Not caution about the fix — **the fixture's pathology is load-bearing.**
Turning the strip on broke 11 existing tests, every one of them naming
`gaulke_roofing`, and the most important of them says why this cannot be
resolved by editing expectations:

> `test_preflight.test_a_full_bleed_design_does_not_report_its_own_border`
> is a regression guard for a real `cv2.erode` `borderValue` bug measured
> 2026-08-20. It uses this fixture **because the black bars make the artwork
> touch the frame edge** — it is the corpus's only full-bleed design, and only
> by accident of the letterboxing. Cropping the bars removes its fixture.
> Re-pointing it at the new number would silently retire a guard for a
> genuine defect.

Seven more (`test_resnap_mask_matches_grader`, `test_thread_match_*`) pin
spool IDs that legitimately move once the design changes, and two
(`test_enclosed_by_garment`) need a fixture that still *has* enclosed
background regions — this one's went to zero.

So the flag is the honest state: mechanism landed, reviewed, tested, and
**byte-identical off — verified exactly, 11,131 stitches off against the
pre-change baseline, 12,811 on.** Flipping it on is a separate change whose
real work is re-pointing those 11 tests at fixtures that still carry the
property each is testing — never at whatever the engine now happens to emit.

### Known, and NOT fixed by this

With the bars gone, the band's own **soft shadow edges** — a ~12 px gradient
running 235 → 216 → 255 down each side, measured — drop border agreement to
**0.693**, so `stage1_prep` reports `BACKGROUND_ABSENT` and the white ground
is still sewn. That is the border flood's business, not letterboxing, and it
is why the "after" render still shows a stitched background. The bar/band
boundary itself is clean (row 1115 pure black, row 1116 at 254.6), so the
crop is exact; this is a separate defect that happened to be hidden behind a
worse one.

### The number that matters

| | before | after |
|---|---|---|
| the actual file | **unusable** (invisible on cloth) | **legible** |
| ARTFID | 32.2 | **32.7** |
| coverage | .065 | .070 |
| structure | .132 | .138 |
| preflight grade | B | **C** (worse) |

**ARTFID moved +0.5 points for a fix that turned an unusable file into a
usable one — and preflight grade moved the wrong way.** Neither instrument in
this repo could see the single largest quality improvement measured all day.

The cause is not subtle and was predicted before the fix was written:
`art_ink_field` reads the **original file**, so the bars are still counted as
ink (`ink_saturation` 0.847). The engine now correctly sews only the logo
band, which *shrinks* its overlap with that bogus ink field, so coverage stays
at ~0.07 and the `subject mismatch` refusal persists at 4.2×. **The metric
punishes the fix, very slightly, for being right.**

That asymmetry is left in place on purpose. Changing `art_ink_field` in the
same commit would have hidden the cleanest evidence this repo has that a
metric can be confidently, quietly wrong — and it is the same failure §3
describes, caught in the act rather than inferred from a rank correlation.
Fix the metric deliberately, on its own evidence, in its own change.

**The operational lesson is DOCTRINE's, re-earned:** the only instrument that
caught this was rendering it and looking. A claim about polarity needs a
picture, and a green metric is not one.

### Still open on that fixture

The band's white background is **still being sewn** — visible as pale fill
texture across the whole rectangle. That is the gradient-route ground-sewing
defect from §4, untouched here: it runs at ROADMAP **gate 2** (no stage-0
recalibration without real tonal artwork) and is not this change's business.

## Reproducing

```bash
cd digitizer && .venv/bin/python -m tools.artfid_eye_rank --verify   # drift control
cd digitizer && .venv/bin/python -m tools.artfid_eye_rank --render   # ~9 min, 14 digitizes
# rank the pairs, write artfid_eye_out/ranking.json, THEN:
cd digitizer && .venv/bin/python -m tools.artfid_eye_rank --reveal
```

`artfid_eye_out/` is gitignored and rebuilds from a fixed seed. Note that
`--verify` prints one fixture's score and so contaminates that fixture for
whoever runs it; `CONTAMINATED` in the tool must match.
