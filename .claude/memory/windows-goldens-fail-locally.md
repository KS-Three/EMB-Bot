---
name: windows-goldens-fail-locally
description: Golden divergence is per-fixture and MOVES — corrected 2026-08-22, Linux now fails the set this file calls the Windows one; never a red main, never re-capture a golden locally
metadata:
  type: reference
---

> **CORRECTED 2026-08-22 — the set below is no longer the Linux picture, and
> the headline claim inverted.** Measured on a Linux container with the pinned
> requirements, on BOTH Python 3.12 (CI's version) and 3.13:
>
> | fixture | measured on Linux |
> |---|---|
> | `test_flat_lane_byte_identical[logo_alpha.png]` | **PASS** |
> | `test_stage2_photo_segment[logo_alpha.png]` | **PASS** |
> | `test_flat_lane_byte_identical[photo/enthusiast_logo.png]` | FAIL |
> | `test_stage2_photo_segment[photo/enthusiast_logo.png]` | FAIL |
> | `test_pushcomp[logo_whitebg.png-towel]` | FAIL |
>
> That is the *Windows* failure set, on Linux — the exact inverse of the claim
> below that "the two `enthusiast_logo` rows pass on `ubuntu-latest`". Two
> independent things corroborate the new reading: CI's deselect list had grown
> from three to FIVE, adding precisely the two `enthusiast_logo` rows, which
> only happens if they began failing there; and removing both `logo_alpha`
> deselects and pushing produced a GREEN CI run (`db0e642`), so those two pass
> on the real `ubuntu-latest` runner, not just in a container.
>
> The original claim was explicitly an inference from where PR #159 captured the
> golden, not a measurement — and COOKBOOK warns the set moves whenever a golden
> is re-captured. It moved. CI now deselects three.
>
> Everything below is kept as the WINDOWS record, which is what the file is
> named for and which nothing here re-measured.

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
