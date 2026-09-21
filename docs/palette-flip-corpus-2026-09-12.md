# The corpus pass Kent asked for before the flip — defect 30 (2026-09-12)

**What this is.** `cfg.layer_palette_from_regions` shipped DEFAULT OFF in #465
(`stage3_segment.layer_palette_threads`, the §6 fix in
`docs/palette-mismatch-2026-09-12.md`). Kent was offered "flip it now" and
ruled **corpus pass first**. This is that pass, and nothing else: the flag is
still OFF in the tree, no engine file was edited, and the recommendation at the
end is a recommendation.

> **OUTCOME, added after the fact: Kent flipped it 2026-09-12.** He was shown
> §3's duplicate-row cost alongside the recommendation and took it knowingly —
> the duplicates are the truth the colour cap produced and there is no
> half-flip. `cfg.layer_palette_from_regions` now defaults True. Everything
> below was measured with the flag OFF in the tree and is unchanged by the
> flip; read it as the evidence behind the decision, not as an open question.
> The one thing still open is folding the duplicate rows, which means
> `merge_duplicate_cone_layers` on the DERIVED cone — it moves sew order and
> goldens, and stays out of scope.

**Measured on the tree at `352240b`.** HEAD moved to `bf64a05` while the arms
ran (a `CLAUDE.md` prose commit and the #469 merge), and
`git diff 352240b..bf64a05 -- digitizer/digitizer_core digitizer/tools` is
**empty** — so every number below is also the engine at HEAD. Python 3.12.3,
`digitizer/.venv/bin/python`, Linux.

**Four full-corpus arms**, 26 fixtures each, run in parallel 18:38–19:52 UTC:
OFF and ON at the engine default `max_colors=12` **and** at the Studio's
shipped `max_colors=6` (`app/src/lib/project.js:87` — a new digitized element
is created with 6, and every published number for this defect was taken at 12).
Config is the shipped instrument's own:
`PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=N,
layer_palette_from_regions=ARM)`.

The probe is a scratchpad script (not committed — it is a throwaway reading of
shipped code) that digitizes each fixture and dumps the whole per-layer picture:
the review palette, every region's cone/stitched/area/mover-stamp by layer, the
block list, the warning payload, a digest over every stitch coordinate, and the
phantom split taken **from `tools/palette_mismatch.py`'s own `_phantoms` and
`_operator_list_is_consistent`**, imported rather than reimplemented. Its OFF
numbers at 12 reproduce the published ones exactly (24 diverged regions on 3 of
26, 14 phantom cone entries on 9 of 26), which is the check that the harness
and the instrument agree.

---

## 0. The answer, in one table

| | `max_colors=12` OFF | ON | `max_colors=6` OFF | ON |
|---|---:|---:|---:|---:|
| fixtures whose review cone list moves | — | **3 of 26** | — | **5 of 26** |
| layers whose cone changes | — | **7** | — | **13** |
| **layers naming a cone no region in them carries** (the invariant) | **7** on 3 fixtures | **0** | **13** on 5 fixtures | **0** |
| `PALETTE_THREAD_MISMATCH` fires | 3 of 26 | **0 of 26** | 5 of 26 | **0 of 26** |
| diverged regions | 24 (6 sew, largest sewn 7.2 mm²) | **0** | **122** (34 sew, largest sewn **101.3 mm²**) | **0** |
| phantom cone entries, `set(review) − set(blocks)` | 14 on 9 fixtures | **7 on 6** | 20 on 11 fixtures | **7 on 6** |
| — of those, MISLABELLED (the defect) | 7 | **0** | 13 | **0** |
| — of those, legitimately unsewn (keep) | 7 | 7 | 7 | 7 |
| review rows, corpus-wide | 132 | 132 | 109 | 109 |
| duplicate rows (two layers, one cone) | 0 | **7** | 0 | **13** |
| cones dropped from a review list that a block SEWS | — | **0** | — | **0** |
| grey-swatch population (`reviewFromJob` → `#888`) | 0 | 0 | 0 | 0 |
| plan digest / `design.colors` / stats identical OFF↔ON | — | **26 of 26** | — | **26 of 26** |
| operator list (`plan.palette` vs `plan.blocks`) consistent | 26/26 | 26/26 | 26/26 | 26/26 |

**Recommendation: FLIP IT.** Reasons and the one cost are in §5.

---

## 1. Which review cone lists change, and how

Per the standing rule — *on a fixture where a change removes a cone, read the
cone list, not the grade* (DOCTRINE) — this is the list, layer by layer. "sewn
by its own layer" is the stronger property beyond the invariant: the elected
cone is not merely carried by a region in that layer, some region in that layer
sews it.

### 1.1 At the engine default, `max_colors=12` — 3 of 26 fixtures, 7 layers

| fixture | layer | before | after | that layer's regions | new cone sewn by its own layer |
|---|---:|---|---|---|---|
| `photo/drone_render.png` | 5 | `2564` | `0111` | 2 regions, both sewn, largest 3.2 mm², both cap-merged | yes |
| | 6 | `1565` | `0111` | 5 regions, none sewn, largest 3.7 mm², all cap-merged | no (layer sews nothing) |
| | 14 | `0015` | `0145` | 3 regions, all sewn, largest **7.2 mm²**, 3 cap + 1 re-snap | yes |
| | 15 | `0931` | `1310` | 2 regions, none sewn, largest 7.8 mm² | no (layer sews nothing) |
| `photo/summit_badge.png` | 12 | `0134` | `4174` | 7 regions, none sewn, largest 1.2 mm², all cap-merged | no (layer sews nothing) |
| `photo/logo_golden_tee.jpg` | 0 | `0015` | `3971` | 4 regions, none sewn, largest **304.7 mm²**, all cap-merged | no (layer sews nothing) |
| | 13 | `0230` | `0532` | 1 region, sewn, 2.9 mm² | yes |

**New cone carried by its own layer: 7 of 7. Sewn by its own layer: 3 of 7.**
The other four are layers whose every region is unstitched — the
enclosed-background default. They are real review rows, they keep a real
colour, and the colour they keep is now the one their own shapes carry instead
of the one stage 2 remembered. That is exactly what the docstring promises and
the boundary it draws.

Whole lists, so the diff is legible rather than described:

```
photo/drone_render.png
  OFF  1776 3335 1102 0108 1310 2564 1565 3971 0145 1305 0111 1304 0142 0700 0015 0931
  ON   1776 3335 1102 0108 1310 0111 0111 3971 0145 1305 0111 1304 0142 0700 0145 1310
  sewn 1776 3335 1102 0108 1310 0111 3971 0145 1305 1304 0142 0700 3971   (13 blocks)

photo/summit_badge.png
  OFF  4174 3574 2732 1342 2920 3130 0142 0020 3641 2762 0145 1114 0134
  ON   4174 3574 2732 1342 2920 3130 0142 0020 3641 2762 0145 1114 4174
  sewn 4174 3574 2732 1342 2920 3130 0142 0020 3641 2762 0145 1114 4174   (13 blocks)

photo/logo_golden_tee.jpg
  OFF  0015 0020 0703 3971 1102 0811 3344 1904 0532 0142 1115 1300 0270 0230
  ON   3971 0020 0703 3971 1102 0811 3344 1904 0532 0142 1115 1300 0270 0532
  sewn      0020 0703 3971 1102 0811 3344 1904 0532 0142 1115 1300 0270   (12 blocks)
```

`summit_badge` ON is now character-for-character the block list. That is a
coincidence of this fixture, not the contract (§4), but it is the cleanest
picture of what the election does.

### 1.2 At the setting customers actually get, `max_colors=6` — 5 of 26, 13 layers

The colour cap is the producer, so the shipped setting is where this lives.
**Three of these five had never been measured at 6**: the published §1.2 table
is an eight-fixture read (the seven real-customer logos plus `logo_whitebg`),
so `drone_render`, `photo_chrome_specular` and `summit_badge` at 6 appear here
for the first time. `photo_chrome_specular` diverges at 6 and not at 12 at all.

| fixture | layer | before | after | that layer's regions | sewn by its own layer |
|---|---:|---|---|---|---|
| `photo/drone_render.png` | 3 | `0108` | `3971` | 7 regions, **all 7 sewn**, largest **101.3 mm²**, 7 cap + 1 re-snap | yes |
| | 4 | `1310` | `1305` | 1 region, sewn, 20.4 mm² | yes |
| | 5 | `3770` | `3971` | 3 regions, 1 sewn, largest 11.3 mm² | yes |
| | 6 | `1565` | `1776` | 6 regions, 1 sewn, largest 3.7 mm² | yes |
| | 10 | `0111` | `3971` | 11 regions, **all 11 sewn**, largest 6.8 mm² | yes |
| | 11 | `0142` | `3971` | 4 regions, all 4 sewn, largest 8.4 mm² | yes |
| | 12 | `1300` | `1305` | 2 regions, none sewn, largest 3.4 mm² | no (layer sews nothing) |
| | 13 | `0931` | `1305` | 3 regions, 2 sewn, largest 1.6 mm² | yes |
| | 14 | `1321` | `1305` | 1 region, sewn, 3.0 mm² | yes |
| `photo/photo_chrome_specular.png` | 6 | `0015` | `0131` | 1 region, sewn, **42.8 mm²** | yes |
| `photo/summit_badge.png` | 6 | `0134` | `4174` | 7 regions, none sewn, largest 1.2 mm² | no (layer sews nothing) |
| `photo/logo_golden_tee.jpg` | 6 | `0015` | `3971` | 5 regions, 1 sewn, largest **304.7 mm²** | yes |
| `photo/screenshot_phone_ui_golke.jpg` | 6 | `0015` | `3971` | **71 regions**, 4 sewn, largest 7.3 mm² | yes |

**Carried by its own layer: 13 of 13. Sewn by its own layer: 11 of 13** — the
opposite balance from 12, because at 6 the cap moves whole populations of sewn
shapes, not a handful of shards.

```
photo/drone_render.png            (15 review rows, 9 blocks)
  OFF  1776 3335 1102 0108 1310 3770 1565 3971 1305 0145 0111 0142 1300 0931 1321
  ON   1776 3335 1102 3971 1305 3971 1776 3971 1305 0145 3971 3971 1305 1305 1305
  sewn 1776 3335 1102 3971 1305 1776 0145 3971 3971

photo/photo_chrome_specular.png   photo/logo_golden_tee.jpg
  OFF  3574 3666 4174 0111 0108 0131 0015     OFF  0703 0020 3971 1102 3344 1902 0015
  ON   3574 3666 4174 0111 0108 0131 0131     ON   0703 0020 3971 1102 3344 1902 3971
  sewn 3574 3666 4174 0111 0108 0131 3574     sewn 0703 0020 3971 1102 3344 1902 3971 0020

photo/screenshot_phone_ui_golke.jpg          photo/summit_badge.png
  OFF  1776 0111 0108 3971 0020 3630 0015     OFF  4174 3574 3130 2732 1342 0142 0134
  ON   1776 0111 0108 3971 0020 3630 3971     ON   4174 3574 3130 2732 1342 0142 4174
  sewn 1776 0111 0108 3971 0020 3630 0020     sewn 4174 3574 3130 2732 1342 0142 4174
```

**The OFF population at 6 is five times the published corpus number at 12**:
122 diverged regions on 5 fixtures against 24 on 3 — `drone_render` 38,
`screenshot_phone_ui_golke` 71, `summit_badge` 7, `logo_golden_tee` 5,
`photo_chrome_specular` 1. (The published "76 on two real-customer fixtures" is
`golden_tee` 5 + `screenshot` 71, reproduced exactly; it was an eight-fixture
read, and the other three only show up in a full-corpus pass at 6.) **34 of the
122 SEW**, and the largest sewn one is **101.3 mm²** on `drone_render` layer 3 —
fourteen times the largest sewn mislabel at 12, and not a sub-millimetre shard
in the sense the earlier measurement made this defect sound.

---

## 2. The invariant

> `palette[i]["number"] ∈ {r.thread_number for r in layer i}` for every layer
> on every fixture.

**ON: it holds on 26 of 26 fixtures at `max_colors=12` and on 26 of 26 at
`max_colors=6`. Zero violations, zero exceptions, nothing to report loudly.**
Every one of the 20 changed layers (7 + 13) names a cone its own regions carry.

OFF, for contrast, it is violated on **7 layers across 3 fixtures at 12** and
**13 layers across 5 fixtures at 6** — the lists in §1, read the other way.

Two things checked so the "0" is not an artifact of how it was counted:

- **No layer anywhere in any of the four arms holds two distinct cones** (0 of
  every layer on every fixture). So today's defect is entirely "the whole layer
  moved and the label stayed", never "the layer split". That is also why the
  warning goes to 0 under ON rather than to a smaller number.
- **No layer is empty**, so no fixture reaches the "keeps `thread_indices[i]`"
  fallback and passes the invariant vacuously. Every palette row was elected.

One consequence worth stating plainly: **flipping does not make
`PALETTE_THREAD_MISMATCH` structurally dead.** With the flag ON it still fires
whenever a layer holds a cone its elected representative does not — i.e. the
mixed-layer case, which is the case that would actually be worth a warning.
Its population is 0 today. The detector for the wholesale case becomes
`tests/test_layer_palette.py` and `test_pipeline.py::test_palette_has_one_entry_per_layer`,
which already assert the invariant.

---

## 3. Does anything get worse?

Asked as four separate questions, because "no" to one of them is not "no" to
the others.

**(a) Does any review list lose a row?** No. Rows are unchanged on every
fixture: **132 → 132** review rows corpus-wide at 12, **109 → 109** at 6. The
election renames rows; it never deletes one. `len(result.palette)` is identical
per fixture in all 26 pairs at both settings.

**(b) Does any review list lose a cone a customer needs?** No. **Cones dropped
from a review list that a block actually sews: 0** — at 12 and at 6. Every cone
that disappears from a list (`0015`, `0931`, `1565`, `2564`, `0134`, `0230`,
`0108`, `1300`, `1321`, `3770`, `1310`, `0111`, `0142`) is a cone **no block on
that fixture sews**: stage 2's memory of a layer that has since been cap-merged
away. Nothing was added either (`cones added that a block sews: 0`) — the
election picks from cones already present in the design.

The other direction is unchanged too: cones a block sews that appear on **no**
review layer are **24 cones on 4 fixtures in all four arms** — the two gradient
ramps, `region_blobs` and `repro_gradient_white_icon`, i.e. the blend tier's
`shade_thread_index` shades, which are by design (§4).

**(c) Can a customer see a wrong swatch?** No, and the population that could
produce one is unchanged at zero. `reviewFromJob` resolves a shape's colour
`byNumber.get(thread_number)` against the review palette, then
`stats.blocks[sew_block].rgb`, then grey `#888`. The shapes at risk are those
whose own cone is absent from the review list **and** which produced no block:
**0 regions in all four arms.** If anything the ON list is a better lookup
table — every entry is now a cone some region in that layer really carries — but
the measured population is 0 → 0, so this is a non-event either way.

**(d) Can anything a customer is charged for, or a machine sews, move?** No,
and this is the load-bearing check: **the plan digest is identical OFF vs ON on
26 of 26 fixtures at both settings.** The digest covers every block's thread
index, number, rgb, step metadata and stitch count, plus every stitch
coordinate of every run. `design.colors` (the Download step's list, via
`plan_to_design`) is identical 26/26; `stats.thread_mm_by_color` and the
stitch/trim/colour-change counts are identical 26/26; `plan.palette` — the
operator's list — is consistent with `plan.blocks` on 26/26 in every arm. The
"review-only" claim in the docstring and in `test_the_layer_palette_is_review_only`
(two fixtures) now holds corpus-wide, measured rather than reasoned.

**The one thing that genuinely does get worse — and it is cosmetic and
predicted.** `merge_duplicate_cone_layers` folds layers on the DECLARED cone,
and it runs before this election, so two layers can now carry the same DERIVED
cone and not fold. Measured: **duplicate rows 0 → 7 at `max_colors=12`** (4 on
`drone_render`, 2 on `golden_tee`, 1 on `summit_badge`) and **0 → 13 at
`max_colors=6`** (9 on `drone_render`, 1 each on the other four). `drone_render`
at 6 is the extreme: **15 review rows naming 6 distinct cones**.

That is the review screen telling the truth — those nine layers really do sew
`3971`/`1305`/`1776` after the cap merged them, and the Studio's sequencer rows
already label themselves from each shape's OWN `threadNumber`, so they are
*already* showing the duplicate today while the palette row above says
otherwise. But it is a visible change in the list, and folding those layers is
explicitly out of scope (it moves sew order and goldens —
`docs/palette-mismatch-2026-09-12.md` §6, and the docstring's own closing
paragraph). Worth Kent knowing before, not after.

Two smaller notes in the same direction:

- The `.length` trap (§4.3 of the measurement doc) is untouched:
  `drone_render` at 12 still reports 16 rows against 13 blocks. What improves
  is the DEDUPED count — `new Set(palette.map(p => p.number)).size` goes 16 → 12
  at 12 and 15 → 6 at 6, which is now exactly the "Colors (max N)" promise
  instead of contradicting it.
- `reviewFromJob`'s `brandId = palette[0].brand_id` is unaffected: brand is
  uniform across the list, and the election only ever swaps which chart entry a
  row names, never the chart.

---

## 4. Phantom cones — the direction that costs money

Defined as the shipped tool defines it: `set(review) − set(blocks)`, a cone the
review list names that no block sews, split by `_phantoms` into MISLABELLED (no
region in that layer carries it — the defect) and unsewn-legitimate (the layer
really carries it; nothing sews it).

| | 12 OFF | 12 ON | 6 OFF | 6 ON |
|---|---:|---:|---:|---:|
| phantom cone entries | **14** | **7** | **20** | **7** |
| fixtures carrying one | 9 | 6 | 11 | 6 |
| MISLABELLED layers | 7 | **0** | 13 | **0** |
| legitimate unsewn rows | 7 | 7 | 7 | 7 |
| fixtures silent (phantom, no warning) | 6 | 6 | 6 | 6 |

**The published "before" figure — 9 of 26 fixtures, 14 cones — halves to 7
cones on 6 fixtures, and every survivor is one of the two legitimate kinds**,
identical in both arms and at both settings:

```
logo_alpha.png                  layer 4  lists 0020   unstitched layer
logo_whitebg.png                layer 4  lists 0015   unstitched layer (the ring hole)
photo/enthusiast_logo.png       layer 2  lists 0015   unstitched layer
logo_script_tires.png           layer 0  lists 0015   unstitched layer
photo/logo_gaulke_roofing.png   layer 2  lists 0020   unstitched layer
photo/region_blobs.png          layer 1  lists 2153   blend tier: base cone, blocks are shades
photo/region_blobs.png          layer 2  lists 3630   blend tier: base cone, blocks are shades
```

These are the rows the fix deliberately does not touch, and they are byte-for-byte
the same rows before and after. `logo_whitebg` still lists `0015 White` for an
enclosed ring hole the machine never threads, and still loads five spools — the
walkthrough in §3 of the measurement doc is unchanged by the flip, which is the
point: **the invariant is about the layer's own regions, never `palette ⊆ block
cones`.**

At `max_colors=6` the before figure is larger still (20 cones on 11 fixtures)
and lands on the same 7.

---

## 5. Recommendation: flip it

**The evidence supports flipping.** Specifically:

1. **It does what it says on every fixture, at both colour settings.** The
   invariant holds 26/26 and 26/26; the defect's whole measured population —
   7 mislabelled layers at 12, 13 at 6, 24 and 122 diverged regions, 7 and 13
   phantom cone entries — goes to **zero**, with no exceptions to report.
2. **Nothing a customer or a machine sees can move, and that is now measured
   rather than argued**: identical plan digest, `design.colors`,
   `thread_mm_by_color` and stitch counts on 26 of 26 fixtures at both
   settings. The blast radius really is `_review_payload["palette"]`.
3. **It cannot lose a row or a cone.** 0 rows dropped; 0 cones dropped that any
   block sews; the blend tier's 24 legitimately-absent cones and the 7
   legitimately-unsewn rows are untouched.
4. **It is worth most at the setting customers actually get.** At the Studio's
   shipped `max_colors=6` the OFF defect is five times bigger than the number
   this repo has always quoted, it touches a **101.3 mm² sewn shape**, and it
   sits on five fixtures — two of them real customer artwork
   (`logo_golden_tee`, `screenshot_phone_ui_golke`), plus `drone_render`,
   `summit_badge` and `photo_chrome_specular`.
5. **The risk of flipping is smaller than the risk of leaving it.** OFF, the
   list is wrong on 5 of 26 designs at the shipped setting and the only thing
   keeping that harmless is that no consumer reads it positionally — one new
   chip row, legend or `.length` ends that, which is the trap the measurement
   doc spends §4 on. ON, the list is true and the same trap is inert.

**The one cost to say out loud before flipping**, not buried: the review list
grows duplicate rows where the cap merged whole layers — 7 rows at 12, 13 at 6,
worst `drone_render` at 6 with 15 rows and 6 distinct cones. They are honest
duplicates (those layers do sew the same cone, and the sequencer already shows
that per shape), but a reviewer scanning the layer list will see repeated
colours where they used to see distinct ones. Folding them is
`merge_duplicate_cone_layers` on the DERIVED cone, which moves sew order and
goldens: a separate, measured decision, deliberately not bundled here.

**If Kent would rather not take the duplicate rows**, the honest alternative is
to leave the flag OFF and keep defect 30 open as-is — not to half-flip it.
There is no configuration where the list gets truer without the duplicates
appearing, because the duplicates *are* the truth the cap produced.

---

## 6. Reproducing this

The shipped instrument, one flag apart, is the fast read (10–25 min per arm
uncontended):

```bash
cd digitizer
.venv/bin/python -m tools.palette_mismatch                       # OFF, max_colors=12
.venv/bin/python -m tools.palette_mismatch --on                  # ON
.venv/bin/python -m tools.palette_mismatch --max-colors 6        # OFF, the shipped setting
.venv/bin/python -m tools.palette_mismatch --on --max-colors 6   # ON
```

**All four of those CLI forms were run and are verified working** — `--on` and
`--max-colors` had never been exercised end to end before, since both landed in
#465. Run over two fixtures (`logo_whitebg`, `photo/summit_badge`) they agree
with the corpus arms fixture for fixture:

```
### tools.palette_mismatch                (max_colors=12  layer_palette_from_regions=False)
logo_whitebg.png            —   phantom (unsewn, legitimate): layer 4 lists 0015
photo/summit_badge.png      7  [12]  the layer lists ['0134'], the shapes sew ['4174']
                                PHANTOM (mislabelled): layer 12 lists 0134, its regions sew ['4174']
MISLABELLED LAYERS … : 1 layers on 1 of 2 fixtures

### tools.palette_mismatch --on           (max_colors=12  layer_palette_from_regions=True)
logo_whitebg.png            —   phantom (unsewn, legitimate): layer 4 lists 0015
0 of 2 fixtures fire PALETTE_THREAD_MISMATCH
MISLABELLED LAYERS … : 0 layers on 0 of 2 fixtures
```

`--max-colors 6` shows the same thing with `summit_badge`'s mislabelled layer
at index 6 instead of 12, and `--on --max-colors 6` clears it the same way.

**The numbers in §0–§5 are from the four full-corpus arms, not from that
instrument's `main()`.** Two full-corpus `--on` arms were launched alongside
and died silently after ~14 minutes with empty output on a box already running
three `pytest -n auto` suites; nothing from them is quoted here. The per-layer
detail in §1 and the four "does anything get worse" checks in §3 are outside
the tool's output anyway: they came from a scratchpad probe that digitizes each
fixture once per arm and dumps the per-layer regions, a stitch-coordinate
digest and `_phantoms`' own verdict as JSON — the tool's own splitter and
operator check imported, not reimplemented. The probe is deliberately not
committed (`docs/palette-mismatch-2026-09-12.md` §7 makes the same call about
its own scripts); the instrument that should carry this permanently — the
phantom column — already landed in #465.

*(measured 2026-09-12 — four full-corpus arms, `digitizer/.venv/bin/python`,
engine at `bf64a05`)*
