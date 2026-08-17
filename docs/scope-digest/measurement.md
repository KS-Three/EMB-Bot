# Scope digest — measurement: can EMB-Bot tell if a change helped?

Doc names are shortened to their prefix: `pro-parity-real-art` = `docs/pro-parity-real-art-2026-08-15.md`, `hardening-closeout` = `docs/hardening-closeout-2026-08-02.md`, and so on. Nothing re-measured here.

## What can be measured today, and how much to trust it

- **`tools/pro_parity/scorecard.py`** — 0-100 over coverage 20, direction 20, sttype 20, density 15, travel 15,
  underlay 10; registration-aligned, chance-corrected since `53e02ae`. Measures *similarity to this pro's
  stitches*, not embroidery quality (`pro-parity-real-art` §5). Blind to: bare fabric, since whole-design IoU
  barely moves for a 5 mm² hole (`pro-parity-measurements` §2); the satin starburst, which forced lane B to build
  its own cross-rotation metric; stitch-count blowups, since `density` normalises by solid area; sheen of a tatami
  patch beside satin (`pro-parity-lane-reports` §B, §D risks, §C risks).
- **Honest headline 42.5/100** — 15 designs, real artwork, chance-corrected, pinned worktree at `7298ac8`; every row above it in that table was invalidated mid-run (`pro-parity-real-art` §1).
- **`artfidelity.py`** (`art_iou`/`pro_extra`/`art_missed`) — how faithfully the PRO followed the customer art;
  pro-side only, immune to engine movement (`handoff-2026-08-16` §5). Its +/-4 mm shift search pins at the boundary
  on Gaulke, so a re-composed layout reads low by construction (`pro-parity-real-art` §3).
- **`selfconsistency.py`** — the scorecard's ceiling, pro vs pro; self-validated at 96.0/99.9 on
  one-job-saved-twice pairs. Three documented blind spots: PES-vs-DST pairs score the FORMAT (DST has no palette,
  so `decode()` substitutes a `GREYS` ramp), DST-vs-DST inflates `coverage`, several pairs are one file reused for
  two garments (`pro-parity-real-art` §11).
- **`bare.py`** — area not within 0.2 mm of a stitch at 10 px/mm; caught the FREMONT hole. Runs with
  `fill_density_boost=True`, gated OFF in shipped config, so absolute mm² are off-config
  (`pro-parity-measurements` §2, §3, §7).
- **`tools/corpus_scorecard.py`** — capture/diff of preflight's grade over 14 fixtures at two configs; reporting
  tool, not a CI gate, except a brand-new block-severity finding (`MASTER_SCOPE.md` § Evaluation corpus). Its
  preflight length predicate under-reports on 22/48 configs, median 1.50x, max 9.68x — larger than the margin its
  threshold rests on (`hardening-closeout` §2.4).
- **Byte-identical goldens** — signal in CI (`ubuntu-latest`), not locally: on Windows they fail from a single
  contour and the golden's own capture commit fails too, so judge by "same failure set before and after"
  (`pro-parity-real-art` §0b; `MASTER_SCOPE.md` § Gotchas).
- **Codec harnesses** (`crossval-stitch-formats.mjs` + `crossval_decode.py` vs pyembroidery) — self-validated by
  reproducing the known DST transposition at rms 0.0; prove standard-*reader* agreement, not machine behaviour, and
  EXP trim conventions vary by vendor (`pes-crossval-verdict` §1, §4, §5).

## What cannot be measured

- **Whether the output is good embroidery.** `gaulke_roofing_lc` scores 79.8 as an illegible smear and 52.9 when
  legible; needs `coverage` measured against the artwork, not the pro's stitches — open (`pro-parity-real-art` §5, §7.3).
- **Every physical question:** "Nothing was sewn... is geometry" (`hardening-closeout` § What I did not establish).
  Four hoopings settle nine (§5) — does a 0.640 mm bare core read on cloth; at what clearance a needle-down float
  shows on fleece (`LINK_COVER_TOL_MM` is a nominal thread spec, not a measurement); does a tie-in striking at
  0.000 mm grip better; is a 0.0355 mm 2A/P gap visible. Law 19's 0.19-0.20 vs 0.40 mm must not move on analysis (§6.6).
- **Pucker at single-direction 0.20 mm pitch** — unarbitrable from the corpus, since a pro letter carries outline,
  underlay and shadow over its fill so thread-per-area is not a row pitch (`pro-parity-lane-reports` §D risks).
- **Whether `f6458a2`+`08e39b5`'s trade is right** — +0.072 travel for -0.031 underlay, better on 6 designs and
  worse on 8; "needs a sew-out, not a scorecard" (`pro-parity-real-art` §1).
- **Whether the weights are defensible (n=2)**, and whether `hotel_fremont_patch`'s 115-degree fills are a defect
  or the pro's choice — both need more pairs (§11).
- **The +45% beanie solidity target:** "no solidity or minimum-sewable-feature control exists in the engine at
  all"; beanie underlay style is likewise sew-out territory (§5b). 10 art-less designs exist only in the flattered
  lane (§9); 3D foam is unimplemented, so `tires_hat_3d` `sttype` 0.00 is partly expected (§6.5).
- **Thread-run contiguity** — no test asserts it, so appliqué's 5-runs-to-6 fragmentation is invisible
  (`hardening-closeout` §2.6). The research partials are raw: "Do NOT wire any constant in here into the engine"
  (`research-partials` header).

## Instrument defects

- **`direction`, 20 points, measures a preference not a standard:** pro-vs-pro ceiling 0.11 on one pair and 0.85
  on another — one digitizer, one logo, 8x swing; an oracle rotation reaches 3.4 of its 20 points. "Least
  defensible weight in the scorecard." The 95 target is likewise above the metric's ceiling, since a pro scores
  75-84 against a pro (`pro-parity-real-art` §11; `MASTER_SCOPE.md` § Gotchas).
- **Wrong input:** every pre-2026-08-15 number was scored on artwork reconstructed from the pro's own stitches,
  flattering by 11.3 points; the recon lane is near-blind to art fidelity, r = -0.166 (`pro-parity-real-art` §3).
- **Wrong scale:** pre-2026-08-14 `direction`/`sttype` had a ~0.5 chance floor, so ~20 of their 40 points were paid
  for uncorrelated answers and older numbers read ~16 points high (`pro-parity-program` §2).
- **Wrong baseline flipped a verdict:** "+6.1% bare fabric, do not land" compared two unlanded commits;
  re-baselined against `main` the same work is -8.0% and +1.35 (`pro-parity-measurements` §2 vs §2b).
- **Metrics that could not see a verified fix:** the 5.41 mm² FREMONT hole was closed and confirmed by an
  independent healed-blob diff at the same coordinate while the scorecard read **-0.4** on that design
  (`pro-parity-measurements` §3, §1). Lane B cut cross rotation 7-17% and bare fabric on 3 of 4 designs for -0.18;
  lane C took an E's bar pivot from 75 to 1.4 degrees for +0.24 (`pro-parity-lane-reports` §B, §C).
- **The harness measured a config nobody ships, twice:** `garment_id` was never passed, so 12 hats and 7 beanies
  digitized as a polo left chest (`pro-parity-real-art` §5b); and `cfg.fill_density_boost = True` set a stray
  attribute nothing read once the field was removed (§8).
- **CRITICAL, 2026-08-02 — current status must be re-checked against code, do not assume still open:** chaining's
  own instruments are blind three ways — one-point links skipped (37% of the benchmark's links), first and last
  sewn segment never tested, cover computed from polygons rather than emitted thread (`hardening-closeout` §2.1).
- **CRITICAL, same caveat:** contour's `starved` gate is miscalibrated in both directions — 0 of 122 zoo shapes
  fire, silent on a 1.470 mm bare radius while firing on 0.51 mm spots (`hardening-closeout` §2.2).
- **CRITICAL, same caveat:** `test_every_stitch_stays_inside_the_shape` fails verbatim on a disc with a 0.3 mm
  hole; green only because no committed fixture has a hole under ~1 mm (`hardening-closeout` §2.3).
- **A test asserting nothing, and a wrong number driving the engine:** `assert X or True`
  (`tests/test_pushcomp.py:230`) is the line whose comment claims to guard the push-comp angle defect, while
  `principal_angle_deg` double-counts the closing duplicate vertex (`stage6_fill.py:52`) and now drives both fill
  rows and compensation direction, leaving a 20.93-degree residual (`hardening-closeout` §2.8).
- **Uncalibrated defect metrics:** lane A's 0.08 mm rail-stall threshold is its own invention, never validated
  against the corpus (`pro-parity-lane-reports` §A risks); the judge's pivot detector is meaningless on `mfab_lc`
  and `hotel_fremont_patch`, where the PRO scores higher (`pro-parity-judge-report` §2).
- **Four components calibrated on synthetics are wrong on real input** — stage 0 flat/gradient gate,
  `stage6_blend` ramp gate, the parity corpus, the `direction`/`sttype` weights (`handoff-2026-08-16` §3).

## Reproducibility gaps

- **The parity corpus does not exist in a fresh checkout:** `PRO_PARITY_ROOT` / `prep_all.py`'s `ROOT` default to
  `G:/My Drive/EMB-Bot/Embroidery Files`, and prepped designs live only as long as a scratch dir
  (`MASTER_SCOPE.md` § Evaluation corpus; `pro-parity-real-art` §8); `ROOT` was also hard-coded to a cloud sandbox
  path (`handoff-2026-08-16` §4). The 7 real artworks are on that same Drive (§6) and getting more is the
  highest-leverage non-code action (§3).
- **`scratch_corpus/`'s 37 files are gitignored and empty in every checkout** — no session has ever had them; blocks
  the DT-first classifier's M2/M3 (`MASTER_SCOPE.md` § Waiting on Kent 8; `handoff-2026-08-06` § Blocked on Kent 1).
- **MINOR but structural:** every chaining headline is measured on a PNG in Kent's Downloads folder, and preflight's
  "5 artworks" is 4 PNGs plus a gitignored `scratch_flat.png` carrying all 6 of its density-gate leaks — "no other
  machine can re-derive any of it" (`hardening-closeout` §2.9, §6.9).
- **One machine only:** 3 non-OCR Windows failures plus unusable local goldens, 4 tests needing the `tesseract-ocr`
  binary, a hand-created `digitizer/.venv` (`pro-parity-real-art` §0b, §8; `handoff-2026-08-16` §4).
- **Instrument artifacts sit in dead scratch dirs:** the lanes' renders and the judge's `fanmetric.py` /
  `jrender.py` under `/tmp/claude-0/...` (`pro-parity-lane-reports`; `pro-parity-judge-report` §5); the DST
  clean-room decoder and its PNGs (`dst-axis-verdict` § Artifacts); the transition census JSON and 46 overlays
  (`research-partials` § Corpus chaining laws). PES/EXP fixtures are the exception — regenerable from the
  committed harness (`pes-crossval-verdict` § Artifacts).
- **Parallel runs corrupt each other** without a per-agent `PRO_PARITY_OUT` (`pro-parity-program` §7); the instruments behind 42.5 are unmerged, in PR #157 (`handoff-2026-08-16` §0).

## Sequence claims

- **Fix the instrument before judging the fix:** "Rebuild the chaining coverage instrument, then re-run the
  acceptance test and expect it red... Nothing in this dossier should land on `feat/satin-rails` before item 1"
  (§6.1-6.2). Same for contour: build the widest-inscribed-bare-circle instrument as the *definition* of `starved`,
  then add a `room.covers` test to the transition chord, before that lane is trusted (`hardening-closeout` §6.3).
- **Reweighting is gated on scale-normalised registration in `scorecard.py`** — "the prerequisite for any defensible
  reweighting... a change to the measuring instrument, which makes it Kent's call": it registers by translation
  only, so `MAX_SIZE_DELTA` refuses every other same-logo pair (`pro-parity-real-art` §11).
- **Measure in a pinned worktree or the number is void** — three baselines died mid-run on 2026-08-15 (§1;
  `handoff-2026-08-16` §1) — and **re-baseline against the branch you propose to change** before quoting a delta
  (`pro-parity-measurements` §2b).
- **Validate on >=12 designs, not 5** — lane D was +1.76 tuned, -0.60 held-out, "the single most expensive lesson
  in the program" (`pro-parity-program` §7); stack B and D "only after D's rule is made discriminative"
  (`pro-parity-judge-report` §3).
- **Ordered work list** (`pro-parity-real-art` §7): solidity/enclosed background, garment (DONE),
  chance-correction (DONE), direction, "then row spacing" — §7.1 superseded and §7.4 retired the same day by §11.
- **Fix `principal_angle_deg` before landing push-comp**; add a fixture at exactly the cap and re-score at cap 3.0
  before shipping any dt-first arm; drop `LINK_UNCOVERED` from block to warn "today, before anything else"
  (`hardening-closeout` §6.7, §6.5, §6.4).
- **Codec fixes are hardware-gated after the code change:** one Brother or PE-Design load of a harness-clean PES
  before closing (`pes-crossval-verdict` §5); the 30-second panel check with the cap driver off before touching
  rotation settings, and "sequence the fix before any launch milestone that ships DST files externally"
  (`dst-axis-verdict` §3-4).
- **Stage 0 defect (a) is blocked on inputs, not effort** — siting the threshold needs more than one real gradient
  example, so the open question is artwork-first vs flat-lane-first (`handoff-2026-08-16` §2a, §7). **A sew-out
  unblocks the most at once** (`handoff-2026-08-06` §1, marked SUPERSEDED as a to-do list; `MASTER_SCOPE.md` § Waiting on Kent 3).

## Contradictions

- **`MASTER_SCOPE.md` live defect 4 says the pro "worked from richer artwork than we were given."**
  `handoff-2026-08-16` §0 corrects that exact sentence: same file, and the missing piece is 7,272 transparent
  pixels the pro sewed as a second colour. MASTER_SCOPE still carries the superseded reading.
- **"The starburst is largely a RENDER ARTIFACT" at real thread width** (`pro-parity-program` §3.1) vs all five
  lanes seeing fans and lane D eliminating them in thread-width renders — "the black E is an unreadable blowout"
  (`pro-parity-lane-reports` §D).
- **"Fill-vs-satin routing is worth ~40 of 100 points"** (`pro-parity-program` §3) does not survive the ceilings:
  `direction`'s 20 points are mostly unwinnable, `sttype` ceilings 0.73-0.80 (`pro-parity-real-art` §11).
- **Within one document, same day:** §6.3 calls stitch direction "the single largest recoverable deficit in the
  scorecard"; §11 explicitly retires that idea (`pro-parity-real-art`).
- **"True real-world parity is likely ~43-53 chance-corrected"** (`pro-parity-program` §2) — the measured 42.5
  falls below that floor (`pro-parity-real-art` §1).
- **CI status flipped twice:** `pro-parity-program` §1/§8.0 says `main` is red and golden re-capture is the only
  blocker; `pro-parity-real-art` §0b retracts its own "main is red" and confirms `842d3a1` succeeded.
- **Golden policy vs the golden's own docstring:** `test_flat_lane_byte_identical` says "if this test goes red, the
  change under review is wrong" (`pro-parity-lane-reports` §B); the standing ruling is never to re-capture from
  Windows nor read a local failure as a regression (`MASTER_SCOPE.md` § Gotchas).
- **Stage 0 misroute counts differ:** "six of the seven logos to the GRADIENT lane" (`MASTER_SCOPE.md` § Evaluation
  corpus) vs "10 of 15 real logos into the photo lane" (`handoff-2026-08-16` §2a) — reconcile before quoting either.
- **Judge vs lane on identical numbers:** lane C self-reported PARTIAL, fans "genuinely eliminated"; the judge
  re-measured it "WEAK / mostly noise", its own fan metric worse on 3 of 5 (`pro-parity-judge-report` §1).
