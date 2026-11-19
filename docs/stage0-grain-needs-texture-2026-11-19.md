# Stage 0's photo gate, scale half — `cfg.stage0_grain_needs_texture` (built OFF 2026-11-19)

ROADMAP phase 2 (framing). Every number here is an instrument reading, not a
quality claim (gate 4). No constant moves (gate 2): the flag changes which
route may decide, not where any gate sits. The real tonal artwork gate 2 asks
for is the 39-row Commons corpus plus `owl_kent`, the set the texture gate
was sited on (spec 2026-10-28). Nothing was sewn (gate 1).

## 1. The defect

`unique_color_mass` (the grain gate, `UCM_PHOTO_MIN` 0.28) counts pixels
that differ from their 3x3 neighbourhood's mode. The window is in pixels, so
the smaller a logo is exported, the larger the share of its foreground that
sits on an anti-aliased edge, and the more "grain" it reads. Since
2026-10-28 an opaque file enters photo territory when grain OR texture fires;
grain alone sends small real logos to `photo_scene`:
`art/logo_mfab_hat.png` at its native 418 px (ucm 0.298, texture 0.063), and
MFab LC and TOAT machine once downscaled to 146–320 px. This is limit 3 of
`docs/stage0-scale-relative-grad-2026-11-06.md`.

## 2. Why the grain route can be demoted

On opaque files every real photograph read here clears the texture gate at
every export width — min 0.169 (`watercolor` at 250 px; spec 2026-10-28 §4)
— so grain-alone adds no photograph at the sizes the texture gate was
measured on. What it adds is small logos, `fur_ramp` (synthetic), and the
two corpus code images.

## 3. The rule

```
ON, opaque file, texture gate ON:
    two_tone veto      -> not photo        (unchanged, decides first)
    grain and not texture -> not photo     (route `grain_held`, new)
    otherwise          -> unchanged
cut-out file or texture gate OFF -> the grain gate alone (`legacy`), unchanged
```

A held verdict's confidence is the texture gate's. OFF is byte-identical to
today on every input (`tests/test_stage0_grain_needs_texture.py`).
`tools/classify_lens.py` restates it.

## 4. What moves — stage 0 class, OFF -> ON

72 files (the repo fixtures `tools/stage0_photo_gate.py` lists and the 39
Commons rows), each at native and at every ladder width below native (146,
200, 250, 320, 400, 640, 900, 1200, 1600 px; PIL LANCZOS, the scale test's
resampler): **577 readings, 21 move**, every one photo -> non-photo, every one
on route `grain`.

| file | kind | widths that move | OFF -> ON |
|---|---|---|---|
| `art/logo_mfab_hat.png` | real logo | native, 146, 250, 320 | photo_scene -> flat |
| `art/logo_mfab_lc.png` | real logo | 146, 200, 320 | photo_scene -> flat |
| `art/logo_toat_machine.png` | real logo | 146, 250 | photo_scene -> flat |
| corpus `qr_code` | designed graphic | 146, 200, 250 | photo_scene -> flat |
| corpus `barcode` | designed graphic | 400, 640 | photo_scene -> gradient |
| `photo/fur_ramp.png` | synthetic | native, 146, 250, 400, 640 | photo_scene -> flat |
| corpus `stained_glass` | **photograph** | **146** | photo_scene -> flat |
| corpus `vintage_engraved_badge` | photographed graphic | 146 | photo_scene -> flat |

Nothing else moves: the 18 other corpus photographs, `owl_kent`, every
cut-out (drone, enthusiast, Fremont webp), and every opaque logo at every
width.

**Not reproduced:** the 11-06 doc listed Gaulke and Fremont reaching
`photo_scene` at 146–250 px. On today's main neither does under either arm
(`photo/logo_gaulke_roofing.png`, `art/logo_golke_roofing.png`,
`art/logo_hotel_fremont_patch.png`: no move at any width).

## 5. Stated limits

1. **A photograph exported at 146 px loses photo territory** (`stained_glass`;
   the texture gate's 512-px raster reads a 146-px file as it is, and its
   texture falls under 0.13 there). The ladder the texture gate was sited on
   starts at 250, where no photograph moves. The Studio sends up to 1200 px
   and never upscales, so this is a customer who uploads a thumbnail.
2. Cut-outs are untouched, so a small logo on a transparent background still
   reads the grain gate alone.
3. Stage-0 class only. What the moved designs SEW is the flag sweep below.

## 6. Flag sweep (stitches)

`python -m tools.flag_sweep --flag stage0_grain_needs_texture --pictures`
(18 tripwire placements + 26 corpus fixtures, main `1089931d` + this
change): **2 of 44 moved, 0 errored.**

| run | stitches | jumps | needle-up mm | colours |
|---|---|---|---|---|
| `mfab_hat` | 20564 -> 20540 | 80 -> 66 | 741.9 -> 560.4 | 3 |
| `fur_ramp` (synthetic) | 7240 -> 7073 | 17 -> 23 | 153.9 -> 251.5 | 5 -> 6 |

`mfab_lc` does not move: as placed by the tripwire and the corpus it already
reads flat (its misroute is a downscale). Trims unchanged on both. The
renders (ORIGINAL | BEFORE | AFTER) were shown to Kent with the flip
question; on `mfab_hat` the visible change is small — the M's inner notch
and the dash read cleaner ON — and the needle-up saving is the larger effect.
