# Eye pairs, 2026-11-08: the fill-slant blind sitting (`fill-slant-1108`)

**Sat 2026-11-09: ON 0, OFF 7, tie 9 on 16 live pairs, so the sitting favours
OFF. Kent ruled "Keep OFF, record". Full reading: `SITTING.md`.**

Built for Kent; **the sitting and its timing are Kent's.** Nothing here is
judged or flipped. Read `PRE-REGISTRATION.md` first (committed before any
render); `spec.json` is what the builder read; `manifest.json` is the public
description (sealed key hash, no pair-to-arm mapping).

**24 pairs: 16 live, 4 identical, 4 repeat.** Manipulation check passed
(`fill_slant_on` changes the stitch stream on 16 of 22 logos).

**Byte-identical (not a pair), 6 logos:** `gaulke_roofing_hat`,
`precision_drone`, `proseal_hat`, `hotel_fremont_patch`, `toat_machine_hat`,
`toat_beanie`. The other 16 each give one live pair.

## To sit it

```
cd "C:\Users\EE-LT-11030\Claude Personal\EMB-Bot\digitizer"
.venv\Scripts\python -m tools.eye_pairs --serve --out eye_pairs_out\fill-slant-1108
```

(or the `fill-slant-picker` launch config, port 8735). LEFT, RIGHT or tie per
pair (left / right / space, `u` undoes). Do not open `arms.json`,
`features.json`, `manipulation.json` or `designs/` in that folder before the
sitting is over. Afterwards: `python -m tools.eye_pairs.sitting analyse
..\docs\eye-pairs-2026-11-08\fill-slant\spec.json --out eye_pairs_out\fill-slant-1108`
(set `EMB_BRIDGE_PRO` and `EMB_SCRATCH_KENT` for the pro-distance table).
