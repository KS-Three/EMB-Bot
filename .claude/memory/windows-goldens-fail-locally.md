---
name: windows-goldens-fail-locally
description: The byte-identical goldens fail on Kent's Windows checkout and pass in CI — that is platform divergence, never a red main, and never re-capture them locally
metadata:
  type: reference
---

Three tests fail on a Windows checkout of EMB-Bot and pass on `ubuntu-latest`:
`test_flat_lane_byte_identical[photo/enthusiast_logo.png]`,
`test_stage2_photo_segment[photo/enthusiast_logo.png]` and
`test_pushcomp[logo_whitebg.png-towel]`.

**`main` is green.** Confirmed with `gh run list --branch main` — `842d3a1` is
`success`. CI is `ubuntu-latest` (`.github/workflows/python-package-conda.yml`) and
the goldens were captured there.

The divergence is one contour, not logic: on `enthusiast_logo` all 31 `shape_ids`
match and 30 of 31 areas match exactly, with one region reading 0.3208 mm² against
the golden's 0.3784. The tell is that the golden's OWN capture commit (`e364122`)
fails locally too — nothing can be bisected to, because no local commit ever
produced it. Ruled out first: every geometry-relevant pin (numpy,
opencv-contrib-headless, scipy, shapely, scikit-image, pillow) matches
`requirements.txt` exactly.

**Two consequences.** Do not read a local golden failure as a regression — judge a
change by "same failure set before and after". And **never re-capture a golden from
a Windows run**: it would pass locally and break CI.

Expect **8 failed / 1148 passed** locally with `digitizer/.venv` including the
optional `.[service]` extra — 5 OCR tests needing the `tesseract-ocr` system binary
(a separate non-pip install) plus these 3.

I asserted "main is red" repeatedly on 2026-08-15 before checking CI. Don't repeat
that. Standing ruling also in MASTER_SCOPE. See [[real-artwork-parity]].
