# White-keyline art gate: the MFab recipe, for MFab-type art only (2026-10-26)

Kent's ruling, 2026-10-26: *"Gate to MFab art first (Recommended)"*. The
recipe turns on by default only where a dark shape carries white outlines round
letters, and only MFab changes now. Workers then fix the recipe's defects so
the other art can follow.

The recipe is six switches:

- `silhouette_underfill`
- `sew_enclosed_white`
- `enclosed_white_keyline`
- `silhouette_underfill_panels`
- `outline_loop_mitre`
- `silhouette_underfill_rim`

Made a default for all art, it changed 19 of the 20 other paired jobs and
damaged four (bystander report, 2026-10-26):

- **Gaulke:** the roof line is buried.
- **Tires:** the e counters are sewn white.
- **ProSeal:** the slot and the counters are sewn white.
- **Becker:** a white edge shows past the band.

## The read

The code is `digitizer_core/white_keyline_art.py`, behind
`cfg.white_keyline_art_recipe` (built OFF; the flip is its own PR). It reads
the stage-4 regions in `finish_generation`, before `sew_enclosed_white`, the
recipe's first switch, acts. It uses `art_outline.find_art_outlines`, the
pass `border_from_outline` already runs. The art reads as white-keyline art
when some art outline is:

1. background the art encloses (`enclosed_background`, the white field);
2. round at least one text-tagged body that is not background (a letter);
3. held by a host: a non-background shape of at least `RING_MIN_AREA_MM2`
   whose outline covers `INSIDE_MIN` of the field.

There is no new constant. The verdict rides `PipelineResult.white_keyline_art`
and is folded into `plan_stitches`' config, as the photo verdict is. One read
comes before the verdict exists: `build_generation`'s colour-cap ranking. On
MFab it changes nothing.

## Proof

Each job runs at the pro's width through the Studio's request, using the
bystander report's own art, width and garment.

| job | route | verdict |
|---|---|---|
| mfab_hat | photo_scene, background removed | **true** |
| mfab_lc | gradient | **true** |
| becker_hat_large, becker_lc_large, becker_hat_small, becker_chest_small, becker_beanie | flat | false |
| bridge_hat, bridge_lc | gradient | false |
| gaulke_roofing_hat, gaulke_roofing_lc, gaulke_roofing_beanie | gradient | false |
| hotel_fremont_hat, hotel_fremont_patch | gradient | false |
| precision_drone | gradient | false |
| proseal_hat, proseal_beanie | gradient | false |
| tires_hat_3d | photo_scene, background removed | false |
| goldentee_hat | gradient | false |
| toat_machine_hat, toat_machine_beanie, toat_beanie | gradient | false |

**MFab: the gate's file is the explicit recipe's file.**

| job | gate DST md5 | explicit recipe DST md5 | stitches / trims |
|---|---|---|---|
| mfab_hat | `a4841a68` | `a4841a68` | 21,765 / 41 |
| mfab_lc | `f41029f4` | `f41029f4` | 20,849 / 54 |

These differ from #1094's `7b1e20a8` / `85ac48f5` because main moved after
that PR: #1057's ruled defaults, and the rim. Both arms here run on the same
code.

**Off the gate nothing moves.** When the verdict is false, `apply` returns the
very same config object (tested), so those plans are the defaults' by
construction. Spot checks, gate ON vs OFF, full digitize:

| job | gate OFF DST md5 | gate ON DST md5 | verdict |
|---|---|---|---|
| becker_hat_large | `5772f690` | `5772f690` | false |
| toat_machine_hat | `f05c8a95` | `f05c8a95` | false |
| hotel_fremont_hat | `9b7590ff` | `9b7590ff` | false |

The bystander report's defaults md5s (taken at d18c36f7) are not reused here.
#1057 has since changed main's defaults, so they no longer pin today's main.

**Why the read stays narrow:**

- Becker's art outline is its black band, and its white letter faces are
  background, not letters.
- To a T's and Drone's outlines hold no letter.
- No other job has a background outline at all.
