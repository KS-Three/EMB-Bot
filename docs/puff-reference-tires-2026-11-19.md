# Puff reference: TIRES HAT 3D (measurement pending)

**Status: unmeasured.** `TIRES HAT 3D.PES` (a third-party file, gitignored under
`scratch_kent/`) was not available on the machine this was built on, so no number
below is measured from it. The tool exists and is tested on a synthetic pattern
(`digitizer/tests/test_puff_reference.py`); it has not yet run on the real file.

## Measure it (Kent, on the laptop that has the file)

```
cd digitizer
.venv/Scripts/python -m tools.puff_reference "../scratch_kent/Embroidery Files/TIRES/fwdyourdigitizingorderisreadytireslogo (1)/TIRES HAT 3D.PES"
```

Expect two blocks of about 279 and 5,359 stitches (worksheet,
`docs/stage0-tires-photo-scene-2026-09-11.md` section 10). Paste the JSON into this file
with a `(measured DATE - tools/puff_reference.py)` pointer, then replace the
`# unmeasured` constants in the puff code.

## Values in use meanwhile (design spec section 3, all unmeasured)

| Constant | Value |
|---|---|
| Satin spacing | 0.18 mm |
| Underlay | none |
| Tie stitches at run starts | 5 |
| Column width | 3 to 11 mm |
| Foam thickness | 3 mm (fixed) |

## What the tool reports

`blocks` (stitches, trims per colour block), `satin_spacing_mm`, `underlay`,
`tie_stitches`, `cap_rows`, `column_width_mm`. Definitions are in the
`tools/puff_reference.py` docstring; `cap_rows` and `underlay` are heuristics
and should be eyeballed against a render of the real file before being trusted.
