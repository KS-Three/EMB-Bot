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
