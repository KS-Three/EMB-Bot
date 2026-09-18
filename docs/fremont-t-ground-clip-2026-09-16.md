# Fremont's T: the ground takes the pull back, and what `satin_rail_comp` does about it

Kent, 2026-09-16, on the `satin_polygon_axis` renders: *"Hotel Fremont the T
still needs a lot of work, but it improved."* The T is THE's, the 3 mm word
above HOTEL FREMONT (`docs/renders/polygon-axis-2026-09-16/fremont_fold3_60.jpg`):
shipped, it sews as two salmon bean runs; under the flag its bar becomes a
satin fan and its stem stays a bean run.

The answer is not in the T, and not in the axis. **Stage 5 grows every shape
by the fabric's pull and then cuts it back to the hole it sits in whenever a
colour was sewn before it — so on a design with a ground, the pull
compensation is almost entirely switched off, and a 0.41 mm stroke sews at
0.48 mm, under the satin floor.** Every number below is from Fremont at
92.5 mm on pique (pull 0.3 mm). The Fremont stitch probes ran on `5b28edb`,
the tool and the other designs on `3bf8dab`; #503 between them is default
OFF, so the shipped arm is the same engine.

## 1. The chain, measured

**The artwork.** In the source (`logo_hotel_fremont.webp`, 26.8 px/mm at this
size) THE's T stem is 12 px, the H's stems 12 and 13 px, the E's 12 px — one
weight. Traced, the T's stem is **0.41 mm**.

**Stage 5.** `resolve_overlaps` grows it (`poly.buffer(0.3)`, both sides) and
then applies *"never grow back over a color that is already down"*
(`grown.difference(earlier[L])`, there since `2abb876`, the first stitch
planner). THE sits in a hole of the patch fill, which sews first (shape
`S78e6cd01`, runs 121–128; the T's first run is 220). The hole is the
letter's own artwork, so the clip takes back nearly all of the growth:

| stroke (horizontal chord, mm) | artwork | grown by the pull | planned |
|---|---|---|---|
| THE — T stem | 0.41 | 1.01 | **0.48** |
| THE — H stems | 0.44–0.48 | 1.06–1.10 | 0.56–0.69 |
| THE — E stem / arm | 0.34–0.43 | 0.94–1.03 | 0.38–0.47 |
| FREMONT — T stem | 0.79 | 1.39 | **0.84** |
| FREMONT — N stems / diagonal | 0.78–1.01 | 1.38–1.77 | 0.81–1.08 |

**Stage 6.** `satin_stroke` reads the T stem's crosses at **0.47 mm, all six
under `SATIN_MIN_CROSS_MM` (0.5)**, so the whole stem is a hairline stretch
and sews as a bean run (defect 24's fallback, working as built). The H's
stems clear the floor only because its traced outline came out wider — the
same weight in the art, a different stitch type on the cloth. That is the
"mixed" look.

**The professional** (`Embroidery Files.zip`, Hotel Patch DST, same 92.5 mm):
the FREMONT T stem sews **1.40 mm** (23 crosses, p25–p75 1.40–1.44; y
flipped, aligned on the bounding-box centre, the stem inside the window in
the crop), which is artwork + 0.61 — the full pull on each side. THE was not
read cleanly this way (at 3 mm the pro's layout sits about 3 mm off ours);
the 2026-09-03 reading of the block that sews it is a 0.90 mm MEDIAN STITCH
(`pro-files-refute-scale-limit` memory), a stitch length, not a stem width.

## 2. How much of the pull survives — `tools/ground_clip.py`

Per planned shape: the share of its pull band `A.buffer(pull) − A` still in
the polygon stage 5 hands on (`kept`), and the share lost where an EARLIER
layer's artwork lies (`to_ground`).

| design (shipped) | shapes | lost ≥ half their band to an earlier colour |
|---|---|---|
| Fremont @ 92.5 mm | 164 | **157** |
| drone_render @ 80 mm | 102 | **45** |
| ENTHUSIAST @ 93 mm left chest | 27 | 0 |
| Becker @ 95.7 mm left chest | 11 | 0 |

Fremont's lettering rows read `kept 0.00–0.02`. ENTHUSIAST and Becker sew
their lettering on bare cloth, which is why every earlier pull measurement
on those two never saw this.

## 3. Two cures refuted the same session

Both put the pull back into the POLYGON and let the skeleton re-read it
(`docs/renders/fremont-t-2026-09-16/THE_refuted_cures.jpg`):

- **Exempt lettering from the clip** (hypothesis test: letter-sized shapes in
  the THE / HOTEL FREMONT rows only). THE's T sews satin at **1.01 mm** — the
  mechanism confirmed — but at a 3 mm cap height the 0.3 mm growth closes the
  E's arm slots and the H's crotches, and the word reads "TNR".
- **Exempt it, and hold the glyph's own narrow gaps open** (grow, minus the
  closing-at-pull of the artwork). Worse: the grown-then-carved outline is
  jagged and the skeleton shreds every letter.

That is the third time a widening of small lettering has been built on the
polygon and failed on the glyph's own gaps (the first:
`lettering_min_column_mm`, DOCTRINE 2026-09-09).

## 4. `satin_rail_comp` — the width, without the gaps

`cfg.satin_rail_comp` (built 2026-09-09, OFF) keeps a satin shape's ARTWORK
polygon in stage 5 — so the clip has nothing to take — and pushes each rail
out by the pull in stage 6, from a skeleton read off the artwork.

| stroke | shipped | rail comp | pro |
|---|---|---|---|
| THE — T | bean run | **satin, cross p50 0.97** | (median stitch 0.90) |
| THE — H | satin 0.64 + bean crossbar | satin 1.05 | |
| THE — E | bean run | satin 0.93 | |
| FREMONT — T | satin 0.78 | **satin 1.35** | 1.40 |

Renders (black satin, salmon bean, grey fill, blue artwork):
`THE_shipped_vs_rail_comp.jpg`, `FREMONT_T_shipped_vs_rail_comp.jpg`,
`enthusiast_shipped_vs_rail_comp.jpg`, `drone_shipped_vs_rail_comp.jpg`.

- **Fremont:** THE reads as THE in satin; the T's bar ends still fan and the
  FREMONT T's foot serif is still a scramble — a decomposition defect of slab
  serifs that is present under every arm here and is not this finding.
- **ENTHUSIAST:** the A's apex and the S's spine are cleaner; one new long
  diagonal at the E's top-left corner.
- **drone:** the rounded shape `Sc579466d` (9.6 × 7.6 mm, one hole) goes from criss-crossed stubs
  (9 strokes, six of them 0.17 mm) to one clean column. **Two small shapes
  get WORSE — clean zigzags become scribbles** (`S2492f28b`: 1 stroke → 17;
  `Secb59b4d`: 1 → 12).

**Why drone scribbles — a defect in the flag, found here.** The polygon rail
comp hands `satin_shape` is not the artwork on those shapes: stage 5 still
adds its underlap TONGUE (`poly.buffer(pull + overlap) ∩ later`). Under the
default the tongue disappears inside the isotropic growth; on the bare
artwork it is a one-sided bulge, and the skeleton branches into it. **6 of
drone's 58 satin shapes** carry polygon outside their artwork, every square
millimetre of it inside the tongue band (worst: `S2492f28b`, tongue 3.8 mm²
on 3.1 mm² of artwork, 5 vertices → 74). Fremont and ENTHUSIAST: 0.

## 5. The corpus — 26 fixtures @ 80 mm / left chest

`tools/flip_sheet.py run --arm off --arm rail_comp`, every row on `3bf8dab`,
no errors. **20 move, 6 byte-identical; net +3,241 stitches, +59 trims,
+1 sew block, 0 cones, +1 colour change.**

| | |
|---|---|
| grade **up** | `logo_script_tires` **B → A** (raw 88 → 100, −5 trims); `logo_gaulke_roofing` **C → B** (64 → 76, −4 trims) |
| raw up, no letter | `logo_bridge_bar` −38 → −26 (F floor), `photo_owl_pale` 46 → 58, `photo_sunset_backlit` 76 → 88 |
| grade **down** | none |

| fixture | stitches | trims | blocks |
|---|---:|---:|---:|
| `logo_golden_tee` | **+3,158** | **+51** | +1 |
| `photo_scene_stub` | +2,327 | +25 | 0 |
| `repro_gradient_white_icon` | −1,430 | +10 | 0 |
| `becker_marine_logo` | −1,004 | −3 | 0 |
| `logo_bridge_bar` | −778 | **−19** | 0 |
| `photo_dof_meadow` | +334 | +3 | 0 |
| `photo_owl_pale` | +309 | +2 | 0 |
| `logo_script_tires` | +265 | −5 | −1 |
| `photo_chrome_specular` | +243 | +2 | 0 |
| `logo_hotel_fremont` | +83 | +2 | 0 |
| `enthusiast_logo` | −44 | **−9** | 0 |

Findings: `script_tires` loses `TRIM_HEAVY:warn`, `gaulke` and `bridge_bar`
lose `STITCHES_TOO_SHORT:warn`, `owl` loses `DENSITY_EXTREME`,
`sunset` and `grass_macro` lose `LETTERING_TOO_SMALL`; Fremont and
`grass_macro` gain `TRIM_HEAVY:warn`.

**The cost is the tongue defect.** Golden Tee probed at the same 80 mm /
left chest: **17 of its 31 satin shapes** trace an underlap tongue under
the flag, and those 17 carry **+50 of the design's +51 trims** and 3,065 of
its 3,172 added needle points; their strokes balloon (4 → 28, 12 → 61,
8 → 45). The flag's own gain and its price live on different shapes.

## 6. What this does and does not settle

- **Gate 1 is untouched.** The AMOUNT of pull is the preset's; this is where
  it lands. The flag's own plan (§7) puts flipping it after a sew-out.
- **Evidence for the plan's open 2× question** (Python applies `pull_comp_mm`
  per rail, the browser engine as the column total): the pro's FREMONT T
  stem is artwork + 0.61 mm against pique's 0.3 — the Python reading. One
  stem in a pro FILE is not cloth; it is evidence, not a settlement.
- **Fills on a ground lose their pull too**, and rail comp does not touch
  fills. Whether that matters is not measured here.
- **The flag is not ready as built.** Its lettering gain is real on the
  designs this was about, and its corpus price is one mechanism on other
  shapes. The obvious next step is to keep the tongue out of what the
  skeleton reads under the flag (the tongue still sews coverage; it just is
  not a stroke), then re-run this A/B and the drone / Golden Tee renders.
  Not built here.
