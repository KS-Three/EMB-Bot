# `text_cluster_mixed_caps` — before | after, 2026-11-17

**Fault** (prime grader scorecard 2026-11-17, `toat_machine_hat` and `toat_beanie`): the small capital A of
"To A T" sews as a clump of mixed-direction patches with stray crossing stitches and its counter shut.

**Cause**, traced by eye and by number: the row's letters are T and T (11.9 mm tall), o (7.2 mm) and A (7.7 mm).
The letter door links two glyphs only within 0.8 of each other's height, so the T's pair, the o and A pair, no
pair reaches the 3-member minimum, nothing is tagged as lettering, and the column lane never sees the row. The A
falls to the generic satin: a left leg that folds over the top into a fan, a crossbar piece that runs into the leg.
The professional's A (read stitch by stitch from his hat file) is two level-crossed leg columns with a narrow open
gap and a short crossbar between them: not a thread limit, the counter is open in his file.

**Flag** `text_cluster_mixed_caps` (default OFF; byte-identical OFF): glyphs no cluster took are clustered once more
at a 0.6 height ratio (the existing `HEIGHT_BAND_MIN`), every other link unchanged; groups of 3+ tag.

**Population:** the 9 committed pro jobs, flag OFF vs ON. **2 designs moved, 7 are byte-identical** (Becker hat
large, Gaulke roofing hat, Fremont hat, MFab hat, Precision Drone, Tires hat 3D, Golden Tee hat).
**Both movers are pictured, every changed region of each (10 images).** Stitches / trims: hat 17,430 / 21 ->
17,319 / 19; beanie 17,357 / 24 -> 17,267 / 23.
Original is placed by fitting its ink box to the design box (approximate, not the kit's registration).
The professional's renders are not committed (public repo, `tests/pro_renders_allowlist.txt`).

| Design | Picture | What moved | By eye |
|---|---|---|---|
| hat | `toat_machine_hat__zoom2.jpg` | the small A | **better**: two legs, flat top, open triangle counter, short crossbar; the fan over the apex and crossing patches are gone |
| hat | `toat_machine_hat__zoom1.jpg` | first T and the o | T **better** (clean level bar, no diagonal patch over it); o no visible change |
| hat | `toat_machine_hat__zoom3.jpg` | second T | **better**: flat bar, no fanned crossing stitches |
| hat | `toat_machine_hat__zoom4.jpg` | second T's bar, left end | **better**: square end, no lumpy bulge |
| hat | `toat_machine_hat__whole.jpg` | whole design | the rest of the badge unchanged |
| beanie | `toat_beanie__zoom3.jpg` | the small A | **better**: legs and flat top read as the art; counter open; the crossbar patch is still a little lumpy |
| beanie | `toat_beanie__zoom1.jpg` | first T and the o | T **better**; o no visible change (inner edge slightly more faceted, not worse by eye) |
| beanie | `toat_beanie__zoom2.jpg` | second T | **better** |
| beanie | `toat_beanie__zoom4.jpg` | the i-dot of Machine | **neutral to better**: the dot now leans like the art's instead of a flat stack |
| beanie | `toat_beanie__whole.jpg` | whole design | the rest of the badge unchanged |

**Worse: none seen.** The remaining TOAT faults (script "Machine" pen flow, speed-line weight) are other
faults and do not move.
