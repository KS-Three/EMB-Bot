# Flags built, measured, and waiting on a decision

Every one of these is **implemented, tested, byte-identical when off, and
default OFF.** None is waiting on more work from me; each is waiting on a
judgement that is Kent's. They are scattered across MASTER_SCOPE defects 5, 15,
27, 28 and 31 and a dozen scope-history entries, which is fine for a record and
poor for deciding four things in one sitting. This is the same evidence in one
place.

**Nothing here is new evidence** except where a row says so — two rows changed
on 2026-09-06 and both are marked. Assembled 2026-09-06; the defect entries
remain the source of truth, and this page is a reading aid, not a second
record. **If they ever disagree, MASTER_SCOPE wins.**

---

## The five that are genuinely decidable now

### 1. `cfg.satin_per_stroke` — do strokes sew as satin columns?

**Buys** decisiveness, not area. The satin/fill gate turns on `cv = 0.50`, so
distance FROM that edge is the thing: median |cv − 0.50| is **0.154 judged per
region against 0.221 judged per stroke** — further from the knife edge, i.e.
better — and the knife-edge share falls **40.9% → 24.7%**. On Becker @ 100 mm, ON:
**B 88 `DENSITY_EXTREME` → A 100 with no findings**, median column 0.29 → 0.64
mm, satin 75.2 → 154.0 mm² (3.5% → 7.2% of what actually sews).

**Costs** little at the corpus's own 80 mm — Becker is already 88.2% satin
there, so it adds 5.7 mm², and +143.8 mm² over 14 fixtures.

**The catch:** Becker's 17 regions sit ON the `cv = 0.50` gate — 11 within
±0.10 at 80 mm — so its satin share is a segmentation coin flip, not an
artwork property. The machine cap is a **veto** inside the rung, not a vote,
after a render caught the first cut leaving 28.0 mm² of bare cloth.

**Render:** `docs/renders/satin-per-stroke-2026-09-06/`. *(MASTER_SCOPE 5)*

### 2. `cfg.satin_patch_junctions` — sew the bare crotch of a K?

**Buys** the whole of one fixture's bare cloth: uncovered **23.8 → 0.0 mm² at
80 mm**, 44.5 → 0.0 at 90, **B 76 → B 88**, and it clears the corpus's only
other positive (`photo_scene_stub` 6.5 → 0.0). Corpus-wide that is
**30.3 → 0.0 mm², 100% of the bare cloth inside SATIN shapes.**

**Costs** +7–8% stitches on the fixture, +0.25% overall; 23 of 26 fixtures
byte-cost-identical, with one over-fire (`logo_bridge_bar` +59 st at 0.0
uncovered either way — the pass is deliberately stricter than the grader).

**The catch, and it is the whole question:** the patch sews **tatami inside a
satin letter**, so it is a *look* decision, not a number. Four cross-length
knobs were measured first and none reached it.

**Render:** `docs/renders/junction-bare-2026-09-06/`. *(MASTER_SCOPE 5)*

### 3. `cfg.revalidate_small_shapes` — re-snap shapes of 50–199 px?

**Buys** sewn colour the scorecard cannot see. `screenshot_phone_ui_golke`'s
worst thread error **33.0 → 21.2 ΔE00**; the headline shard `S43831dcd`
(177 px, and it *does* sew — 24 stitches) goes `0111 Whale` **32.7 → 0015
White 1.4**. 21 of 26 fixtures byte-identical.

**Costs** almost nothing measurable: **no grade and no block count moves
anywhere**, and one residual — `drone_render` 19 → 20 cones, because a shard
lands on `0674`, which the shipped pass otherwise vacates.

**CHANGED 2026-09-06 — this reframes the decision.** "Moves no grade" was
read as evidence the fix buys little. Half of that is the check aggregating
per THREAD on its worst patch; the other half is that **the design is 312
points under water** — `screenshot` must clear ~11 blocking findings before
`score` moves at all (`tools/floor_depth.py`). The invisibility is a property
of the scorecard's floor, not of this fix. `raw_score` now rides out as a
metric so the improvement is at least visible in a scorecard diff.

**Render:** `docs/renders/small-shape-resnap-2026-09-06/`. *(MASTER_SCOPE 28)*

### 4. `cfg.bind_resnap_all_classes` — bind the re-snap to the chosen palette?

**Buys** cones the operator does not have to load: **19 colour stops removed
across five designs** (drone 19→14, bridge_bar 18→14, screenshot 16→11,
golden_tee 16→13, gaulke 6→4), gaulke also −10.9% stitches.

**Costs** **+2 blocks net** — screenshot 10→8, golden_tee 2→5, bridge_bar 3→4
— and it is *not* a raw-yardstick artefact: forcing the excess yardstick still
gives golden_tee D 52→F 22 and drone D 40→F 28, the latter with no thread
block moving, so part of the price is the extra stitches.

**CHANGED 2026-09-06 — a benefit the price tag did not have.** Binding also
removes a **spool revisit on real customer artwork**: `screenshot` goes
17 blocks / 16 distinct with `3971` sewn twice, to **11 / 11 with no
duplicate**. An undeclared cone exists only because this escape put one there,
and nothing downstream rejoins the regions that land on it. That belongs on
the credit side.

**My reading, for what it is worth:** I said "I would not flip it on this
evidence — the value is the price tag." The revisit finding moves that
slightly toward flipping, not decisively. *(MASTER_SCOPE 15)*

---

### 5. `cfg.enforce_color_cap` — make "Colors (max N)" true? (added 2026-09-07)

**The only one of these five with a broken PROMISE behind it**, and the only
one found by driving the shipped app rather than by reading code.

**Buys** the slider meaning what it says. Thread count is the cost driver —
every distinct cone is a spool to buy and, on a single-needle machine, a
manual re-thread mid-job — and at the Studio's shipped default of 6,
**6 of 26 corpus designs sew more cones than promised, all six gradient**
(flat 0/6, photo_scene 0/7, photo_subject 0/2). `stage2_quantize` has always
capped the FLAT lane hard; the SLIC+RAG lane passes `max_k=max_colors` into
k-medoids, which is a clustering parameter and not a cap. **Stage 0 routes six
of seven real customer logos to gradient**, so the control was enforced on the
artwork type customers do not have.

| fixture | cones OFF | cones ON | stops OFF | stops ON |
|---|---:|---:|---:|---:|
| `drone_render` | **22** | 6 | 21 | 9 |
| `screenshot_phone_ui_golke` | 15 | 6 | 14 | 6 |
| `logo_golden_tee` | 14 | 6 | 13 | 6 |
| `logo_bridge_bar` | 13 | 6 | 12 | 5 |
| `summit_badge` | 12 | 6 | 11 | 5 |

**Costs** +1.1% stitches on `drone_render`, and colour merges a customer could
in principle see. On `logo_bridge_bar` **24 shapes move, every one between
0.38 and 7.21 mm²**, and the two renders read the same design — the `Bridge`
script, the black rim, the wheel and the yellow field are untouched. The 20
designs already inside their budget are byte-untouched.

**The residual is a different mechanism, named not hidden.** `region_blobs`
stays at 15 cones because it has only **4 REGION threads** — under the cap, so
the cap correctly does nothing — and **12 of its 15 sewn cones are built after
it, in stage 6 blend bands**. That is defect 16's open half, on a GENERATED
fixture no client artwork produces. A shade-band cap would have to run in
stage 6/7.

**My reading:** this is the one I would flip. The others trade quality for
quality; this one is the difference between a control that works and a
control that does not, and a quote built on 22 cones when the customer asked
for 6 is a refund conversation. The catch is that it merges colour, so it
wants your eye on `docs/renders/color-cap-2026-09-07/` first.

**Render:** `docs/renders/color-cap-2026-09-07/`. *(MASTER_SCOPE 31)*

---

## Already ruled — listed so it is not re-opened by accident

**`cfg.dissolve_phantom_blends`.** Kent saw the render and ruled **2026-09-04:
leave it OFF and bank it** — deliberately parked, not pending. A datum arrived
2026-09-06 (on `gaulke_roofing` the flag alone is **F 0 → C 64**, blocks 3 → 0,
worst ΔE 63.6 → 6.8, −15% stitches) and MASTER_SCOPE records it as exactly
that: *"Not a re-opening, a datum."*

**That datum is GONE — twice over.** PR #380 retracted the C 64 itself (measured on the cones, it is a design that DROPPED ITS LETTERING; the grade rewarded losing the ink), and re-measured 2026-09-07 the other half has moved too. `gaulke_roofing` grades
**B 76 with the flag OFF**, zero blocking `THREAD_MATCH_POOR`, worst ΔE00
**0.0**, at both `max_colors` 6 and 12. The flag now buys **4 cones → 3 and
−14.5% stitches** there, with no grade and no thread-match change — so the
one thing that might have re-opened the 2026-09-04 ruling no longer says
what it said. **His ruling stands more firmly, not less.** The cause of the
drift is not attributed: defect 28's enclosed-background exclusion accounts
for F 0 → F 4, not for the rest. His stated reasons on the day — two mild
negatives and the five-of-six residual — are unchanged.

## Not decidable yet, and why

- **`cfg.edge_cap`**, **`cfg.satin_rails_follow_edge`** — ROADMAP **gate 1**.
  A sew-out settles them; geometry cannot.
- **`cfg.chain_links`**, **`cfg.detail_layer`** — ROADMAP **gate 3** names
  chaining and contour explicitly: no default-OFF tier is flipped until its
  instrument is rebuilt. A green suite has already hidden needle-down thread
  on bare fabric here.
- The remaining default-OFF flags (`photo_segment_sam2`, `directional_comp`,
  `fill_density_boost`, `shade_palette_demand`, `shade_axis_normalize`,
  `applique`) are experiments or unfinished lanes, not decisions waiting.
