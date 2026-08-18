---
name: windows-goldens-fail-locally
description: Golden divergence is per-fixture — Kent's Windows fails a different three than CI deselects; never a red main, and never re-capture a golden locally
metadata:
  type: reference
---

Three tests fail on a Windows checkout of EMB-Bot:
`test_flat_lane_byte_identical[photo/enthusiast_logo.png]`,
`test_stage2_photo_segment[photo/enthusiast_logo.png]` and
`test_pushcomp[logo_whitebg.png-towel]`. The two `enthusiast_logo` rows pass on
`ubuntu-latest`, where PR #159 captured their golden; the towel row is
deselected on CI (deselected tests never run there — its mismatch was last
actually observed in the 2026-08-03-era dev container, so current
ubuntu-latest behavior is inferred, not measured). CI's three deselects are a
DIFFERENT set (`logo_alpha` ×2 + the same towel) — the full per-fixture
Windows-vs-CI matrix is MASTER_SCOPE §Gotchas ("The golden divergence is
PER-FIXTURE, not per-platform").

**`main` is green.** Confirmed with `gh run list --branch main` — `842d3a1` is
`success`. CI is `ubuntu-latest` (`.github/workflows/python-package-conda.yml`).

The divergence is one contour, not logic: on `enthusiast_logo` all 31 `shape_ids`
match and 30 of 31 areas match exactly, with one region reading 0.3208 mm² against
the golden's 0.3784 (figures still valid today — PR #159's re-capture `2a5cd29`
changed stitch data only, all 31 areas identical). The tell, measured against the
then-current golden: its own capture commit (`e364122`, since superseded by
`f6458a2`, then by `2a5cd29`) failed locally too — nothing could be bisected to,
because no local commit ever produced those bytes; the same holds by construction
for today's golden, captured on the CI runner. Ruled out first: every
geometry-relevant pin (numpy, opencv-contrib-headless, scipy, shapely,
scikit-image, pillow) matches `requirements.txt` exactly.

**Two consequences.** Do not read a local golden failure as a regression — judge a
change by "same failure set before and after". And **never re-capture a golden from
a Windows run**: it would pass locally and break CI.

Expect **3 failed** (the goldens above) locally with `digitizer/.venv` including
the optional `.[service]` extra: since 2026-08-17 the 5 OCR tests that need the
`tesseract-ocr` system binary (a separate non-pip install) skip via the shared
`requires_tesseract` marker (`tests/conftest.py`) when the binary is off PATH —
never on CI, where a missing binary fails loud. Before the markers, the same
machine read **8 failed / 1172 passed** at `73f37da`.

I asserted "main is red" repeatedly on 2026-08-15 before checking CI. Don't repeat
that. Standing ruling also in MASTER_SCOPE. See [[real-artwork-parity]].
