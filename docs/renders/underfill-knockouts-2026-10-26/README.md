# Under-fill knock-outs: Fremont's star and Becker's white edge (2026-10-26)

`silhouette_underfill`'s ON path (`digitizer/digitizer_core/silhouette_underfill.py`,
`plan`).

- **Before:** origin/main.
- **After:** this PR.
- **Pro:** the professional's file, at the same fraction of its own box. No registration between files, so his window is approximate.
- **Plans:** both of ours come from one generation per job, under the MFab recipe (`silhouette_underfill`, `sew_enclosed_white`, `enclosed_white_keyline`, `silhouette_underfill_panels`, `outline_loop_mitre`).
- **Drawing:** needle paths in thread colour, on grey.

| sheet | what to look at |
|---|---|
| `becker_hat_large_band_before_after_pro.png` | Two windows at 25 px/mm on the lower black band. **Top:** before, the white letter's fill runs past the band's black loops and the edge cap there sews in white; after, the white stops under the black and the cap is dark again. **Bottom:** before, the white bean cap is visible along the outer edge; after, it is dark. |
| `fremont_hat_star_before_after_pro.png` | 40 px/mm on the black state. Before, the star is gone: it was merged into the white ground under the state's black fill. After, it sews as a white run on top, as the pro's does. |
| `gaulke_lc_before_after_pro.png` | The whole design. Before and after are byte-identical, because the under-fill never fires on Gaulke. The buried roof line and window cross come from `sew_enclosed_white` alone, which reproduces the recipe's Gaulke LC file byte for byte. The pro leaves them as open garment gaps. |
