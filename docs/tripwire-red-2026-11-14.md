# Nightly tripwire red, 2026-11-14: an instrument change, not a regression

*(measured 2026-11-14 — nightly run 43600877165, compared with the two green nights before it; CI artifacts only, nothing re-digitized. Ledger untouched.)*

**Verdict: (b) instrument change.** PR #1482 (merged 2026-11-14 07:54Z, six hours before the nightly) recentred the lit bands in `digitizer_core/stitchviz.py`, the thread renderer the word-cc reader draws its OCR crops with. Every word-cc figure moved; no stitch did. The ledger's word-cc rows need a CI re-capture, not a code revert.

## The red row

Run 43600877165 (head `d15a6831`), summary: `0 wrong-way, 0 missing, 1 reader moved, 2 right-way, 108 within tolerance -> FAIL`.

| job | figure | ledger baseline | now | tolerance | verdict |
|---|---|---|---|---|---|
| **mfab_hat** | word cc, native | ours 0.27, **pro 0.20** | ours 0.12, **pro 0.49** | 0.00 | **reader_moved (the only red row)** |
| becker_hat_large | word cc, native | 0.84 (pro 1.00) | 1.00 | 0.00 | better (right-way) |
| hotel_fremont_hat | word cc, native | 0.90 (pro 1.00) | 1.00 | 0.00 | better (right-way) |

**What `reader_moved` means** (`digitizer/tools/tripwire.py`, `compare()`): the PRO's own file, which is committed and never changes, reads differently from the value the ledger stored (pro word cc 0.204 -> 0.495). A pro-side figure can only move if the READER changed, so the tool refuses to judge ours against the old baseline and fails the night. It is a different class from `WORSE` (ours moved the wrong way past tolerance: 0 rows) and from `better` (ours moved the right way past tolerance: listed, exit 0). The two right-way rows are only right-way by accident of the same shift.

## Evidence it is the reader

All from the artifacts of runs 43445411546 (11-13, green), 43247766672 (11-12, green) and 43600877165 (11-14, red):

- **Ours did not change on the failing rows.** `mfab_hat/ours.dst` and `becker_hat_large/ours.dst` are byte-identical (md5 `647c03c0...` and `4a5679f0...`) between the 11-13 and 11-14 runs. Stitches, trims, hops, needle-up mm, stitch-type and direction kappa for those jobs are equal figure for figure.
- **The pro's DST is a committed file.** Its figure still moved, 0.204 -> 0.495.
- **The OCR stack is identical**: all three runs record `tesseract v5.5.3 (tesserocr 2.12.0, in-process)`, same `cv2 5.0.0`, pystitch 1.0.1, python 3.12.16, same runner image.
- **Only three rows moved at all, and they are exactly the three rows that carry a word cc** (`words`: becker_hat_large 2, hotel_fremont_hat 8, mfab_hat 4). The other 15 jobs have no word reading and none of their word-independent figures moved past tolerance.
- **The one reader-path file that changed is `stitchviz.py`** (`git diff 2decffb2 d15a6831`; `word_legibility.py`, `ocr.py`, `tripwire.py`, `pro_baseline.py`, `requirements.txt` and the workflow are all unchanged). `word_legibility` renders every OCR crop through `stitchviz.render_design` (`lit=True`). #1482 sets the `_BANDS` highlight offsets from 0.14/0.26 to 0, so tone no longer follows which way a fill's rows advance. PR #1482's body says `coverage (lit=False)` is bit-identical, which is why the kappa figures, measured on coverage, did not move while the OCR crops, which are lit, did.
- #1482 is in the 11-14 tree and not in the 11-13 tree (`git merge-base --is-ancestor`), and it is the only commit in the 65 between them that touches `stitchviz.py` or `legibility.py` (the other, #1469, adds a `deadline.check`).

Not reproduced locally: no local OCR run was made. The case rests on the byte-identical DSTs, the identical environment and the single changed file in the reader path; a local number would be indicative only (CLAUDE.md: never capture or compare numerics from this laptop).

## It is not the owed `enclosed_white_skip_transparent` capture

MASTER_SCOPE item 75 still says a CI capture is owed. It is not: the current ledger was captured 2026-11-12, run 43147117899 at engine `2f3e782e`, AFTER the 11-11 flip. Drone's ledger row (`sttype_kappa` 0.374, tolerance 0) matches tonight's 0.374 exactly. Item 75's "owed" clause is stale (that file is Kent's to edit; not touched here).

## Side note, not a finding

Four rows moved a few stitches with the tolerance still holding: becker_hat_small 10547 -> 10541, becker_chest_small 10310 -> 10307, mfab_lc 17853 -> 17848, toat_machine_hat 18917 -> 18921 (+0.1 mm needle-up). All inside the ledger's tolerance, so no flag. They show the engine moved slightly between the two nights, from the 11-13/11-14 engine PRs; nothing here ties them to the red row.

## What happens next

The nightly will stay red every night, `mfab_hat word cc reader moved`, until the ledger is re-captured under the new renderer, because the ledger still stores the old pro reading (0.204). The re-capture is Kent's call: the `Nightly tripwire` workflow's `capture` mode (three passes on three runners), then commit `tripwire-ledger-<run id>`. `preview.js` was NOT brought in step with this change (stitchviz.py says so), so any further renderer edit before the capture re-opens the same row.
