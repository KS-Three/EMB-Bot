# Specialty techniques — the revenue map

**Scope.** Eleven candidate techniques, scored for Fritsch's Stitches: one operator, one Tajima single-head lockstitch, DST out. Every number below is carried from the four research lenses with its source tier intact — `[V]` vendor doc, `[S]` supplier tech sheet, `[P]` production/trade writeup, `[D]` derived. Nothing here is invented.

**Engine baseline assumed.** Satin with width control, bean/run tier, border circuits, tatami fill, seven fabric presets, color-block sequencing (`stage7_sequence.py`), DST via pyembroidery (`export.py`), worksheet PDF (`src/pdfsheet.js`).

---

## 0. The prerequisite that isn't a technique

Five of the eleven candidates — appliqué, puff, ITH patch, ITH dimensional, and any multi-material job — need the same missing thing, and none of them can ship without it:

**An ordered `steps[]` container in the IR where each step boundary is a machine function plus an operator-action string.**

Today EMB-Bot emits *one artwork rendering*: N color blocks, each carrying a thread. A specialty design is a **program with operator interrupts**. The invariant the whole discipline runs on:

> **One color stop = one human action.**

Three consequences that are code, not doctrine:

1. **DST has no STOP opcode.** Color change and stop are the same record — `0xC3`. Jump is `0x83`, end is `0xF3`. Wilcom is explicit that the frame-out command "must be specified as a Stop function or Color Change respectively" — **Stop for multi-head, Color Change for single-head** `[V]`. We are single-head. **Every inter-layer break is a color change.** Ink/Stitch says the same from the other side: appliqué components "should be separate colors so the machine stops between steps" `[V]`.

2. **The DST writer must never merge adjacent same-color blocks.** Appliqué layers are frequently all one thread. `export.py:51` currently emits `pattern.color_change()` unconditionally for `bi > 0`, which is correct — but pyembroidery's encoder normalizes the command list before writing, and a block that produces zero stitches (a suppressed cover arc, an empty tackdown) can collapse its adjacent color change. **Sew-out gate: write a two-block same-thread DST, confirm the Tajima halts at the boundary.** Melco's manual states this as a warning — insert a Color Change between locator and tackdown to "force the stop," and **disable auto-merge** or the software silently welds the layers `[P]`. This is the number-one reported appliqué failure in software terms.

3. **Step granularity is a design decision, not a rendering detail.** Merging two objects to save a stop destroys an operator instruction. The nearest-neighbour resequencer in `stage7_sequence.py` must be forbidden from crossing a step boundary.

Build this once. It is the difference between four features and zero.

---

## 1. Ranked build table

Scores 1–5. **Rev** = revenue to a small shop. **Eff** = engine effort (5 = trivial, 1 = brutal). **Mach** = feasibility on our Tajima single-head with no new hardware.

| # | Technique | Rev | Eff | Mach | What it needs that we lack | Verdict |
|---|---|---|---|---|---|---|
| **1** | **Appliqué** — 4-layer, trim-in-place + pre-cut, satin/zigzag/E cover | **5** | 3 | **5** | Step/stop IR (§0). Signed-normal offset chain. Tolerance solver for cover width. Partial-cover arc suppression. Boundary→SVG cut export. | **Build now** |
| **2** | **3D puff / foam** | **5** | 3 | **5** | Step/stop IR. Perpendicular tapered end-caps at every open column terminus. Density-normalized column math. Underlay suppression + 2 mm inset walk. 5-stitch tie mode. | **Build now** |
| **3** | **Knockdown fill** | 3 | **5** | **5** | Polygon dilate + angle-pair tatami + "sequence first" rule. All of it is one new call over the existing fill tier. | **Build now** |
| **4** | **Bean / run variants** (5-, 7-ply, per-segment repeat list, backstitch, stem) | 2 | **5** | **5** | An odd-repeat parameter and a per-segment list. Nearly free. | **Build now** |
| **5** | **ITH flat patch** (dieline → tackdown → decorative → edge finish) | 4 | 3 | **5** | Everything appliqué needs, plus the patch underlay stack, a concavity gate on faux-merrow, and the sidecar emitter (color-change sheet + dieline SVG). | **Build after #1** |
| **6** | **Motif run / candlewicking** | 3 | 4 | **5** | Arc-length parameterization, per-placement local frame, motif library as *data*. The library grows without touching the engine. | **Build** |
| **7** | **Stipple / sketch / hand-stitch effect** | 3 | 2 | **5** | New space-filling meander path generator; randomization as a post-pass over existing tiers, not a new tier. Unlocks **faux chenille** with Burmilana wool-blend `[V]`. | **Build later** |
| **8** | **ITH dimensional** (fobs, zip bags, stuffies) | 2 | 1 | 4 | Turning-gap suppression spans, flip events with mirror transform, hardware voids, bobbin-matches-top rule. | **Defer** |
| **9** | **Cross-stitch fill** | 1 | 2 | **5** | Crosses align to an **invisible global grid, not the object**, with fractional crosses at boundaries `[V]`. Our fill engine is object-local — this is an architectural exception, not a fill pattern. | **Skip unless asked** |
| **10** | **Sequin** | 2 | 1 | 2 | Tajima **Sequin Device IV** (~$, one needle consumed). Plus the densest spec of the eight: drop-stitch direction, fixing patterns, mode-toggle state tracking. DST *does* carry sequins natively (`0x43`) — that isn't the blocker, the hardware and the geometry are. | **Skip until a customer funds the device** |
| **11** | **Moss / chenille** | 3 | 1 | **1** | A **different machine**. Hooked needle + looper, no bobbin. Tajima's chenille line is the TCMX; a lockstitch single-head cannot be converted. | **Do not build** — take the work as faux-chenille via #7 |

**Why appliqué is #1 and not puff.** Twill numbers and names on a hoodie are a $25–40 decoration that sews in a few thousand stitches. The same coverage as solid fill is 40k stitches and forty minutes of machine time. Appliqué is the highest margin-per-minute product a small shop has, and it's also the substrate for #5.

**Why knockdown is #3 despite adding no new SKU.** `GARMENT_FABRIC` already maps `"towel" → terry_towel` and `"blanket" → fleece_sweatshirt`. We are already quoting pile work the engine cannot do well (see §5.1 — the density multiplier runs backwards on exactly those two presets). Knockdown is the cheapest fix in the list and it stops refunds rather than starting revenue.

---

## 2. Appliqué — complete parametric spec

### 2.1 The canonical sequence: four layers, not three

Every major package models appliqué as up to four generated layers `[V]`:

| # | Layer | Purpose |
|---|---|---|
| 1 | **Guide run / placement** | Marks where the fabric goes. Disappears under the fabric. |
| 2 | **Cutting line** | Stitched *on top of* the laid fabric; the operator cuts against it. Trim-in-place only. |
| 3 | **Tackdown** | Holds fabric flat while trimming. |
| 4 | **Cover** | Buries the raw edge. |

Layer 2 exists *because* layer 1 disappears. Wilcom's guide-run panel has an explicit **Pre-cut** (no cutting line) vs **Trim-in-place** (generates the cutting line) switch `[V]`. **That switch is the single biggest branch in the feature.**

**Where the machine stops — trim-in-place:**

```
guide run → [CC, lay fabric] → cutting line → tackdown
          → [CC, trim] → cover
```

Note the trim happens **after** the tack, not between cutting line and tack. Cutting line and tackdown run back-to-back in one block. Wilcom: "Set a Frame Out after the tack stitching in order to trim the appliqué patch" `[V]`. Most hobby writeups get this wrong.

**Pre-cut collapses to one stop:**

```
guide run → [CC, lay pre-cut piece] → tackdown → cover
```

Melco makes this an explicit checkbox — *"Enable Color Change After Tackdown"* — which you leave off for pre-cut `[V]`.

### 2.2 Reference frame and the offset chain

Let **B** = the digitized boundary = the intended finished location of the raw fabric edge. Signed normal offset **s**: `s < 0` inward, `s > 0` outward onto ground fabric.

Vendors **chain** the offsets rather than referencing them all to B. Match this or the published numbers won't transfer:

- Guide-run offset is relative to the outline `[V]`
- Tack offset is relative to the **guide run** `[V]` — and is a **run-stitch-only** parameter; zigzag and E tacks are positioned by column width, centered on the line
- Cover offset is relative to the **tackdown**, not the outline `[V]`

Hatch: offsets range **±10 mm**, there is **one** cover offset value (not per cover type) `[V]`.

**Unit note:** 1 DST coordinate unit = 1 Melco point = **0.1 mm**. Quantize every offset to 0.1 mm *before* rail generation so the two cover rails don't accumulate a half-unit drift.

### 2.3 The governing constraint — cover width is a tolerance budget, not an aesthetic

No source states this as an equation. It falls out of the tolerance stack `[D]` and then validates against four independent published number sets.

Let `o_tack` = tackdown offset (negative), `[t_lo, t_hi]` = trim clearance band, `m_bury` = margin to hide the tackdown thread, `m_edge` = margin to overshoot the raw edge, `c_in`/`c_out` = cover rails, `W = c_out − c_in`.

```
c_out ≥ o_tack + t_hi + m_edge
c_in  ≤ min( o_tack − m_bury ,  o_tack + t_lo − m_edge )
W_req = c_out − c_in ≥ t_hi + m_bury + m_edge
```

with `m_bury = m_edge = 0.5 mm`.

**Distribute surplus width inward.** With trim-in-place the error is asymmetric: an operator can under-trim (fabric hangs outward) but the tackdown thread hard-stops over-trimming inward. The production floor calls this the **65/35 rule** `[P]`.

**Validation:**

| Workflow | `t_hi` | `W_req` from equation | Published | Source |
|---|---|---|---|---|
| Tight trim, duckbill scissors | 1.5 | **2.5 mm** | "absolute minimum: 2.5 mm (risky)" | `[P]` |
| Normal trim-in-place | 2.0 | **3.0 mm** | "beginner safe zone 3.0–3.8"; Hatch baseline 3.00 | `[P]` |
| Loose trim discipline | 3.0 | **4.0 mm** | Melco DS11 practice: cover 40 pt = 4.0 mm | `[P]` |
| Pre-cut, hand-placed (ε ≈ 0.75) | n/a | **2.5 mm** = 2(ε + m_edge) | satin offset default 0.00, centered | `[V]` |
| Laser-cut + heat-tacked (ε ≈ 0.4) | n/a | **1.8 mm** | Stahls' Poly-Twill **2 mm** for 1″–3″ letters | `[S]` |

The last row is the strongest confirmation available. Stahls' — the largest tackle-twill supplier — publishes stitch width by size for **heat-sealed, pre-cut** twill, and it is dramatically narrower than every embroidery-appliqué recommendation:

| Letter / logo height | Stitch width | Stitches per inch |
|---|---|---|
| 1″–3″ | **2 mm** | 15 (≈1.69 mm spacing) |
| 4″–9″ | **3 mm** | 15 |
| 10″ and up | **4 mm** | 15 |

Narrower *because there is no trim step and no placement error to absorb* — `t_hi` is zero. Width still scales with piece size because large pieces drift under the presser foot.

**Implementation corollary: expose `trim_discipline` as a shop-level preset and derive `W_cover`. Do not expose cover width as a free number the user guesses at.**

### 2.4 Worked default — trim-in-place, "normal"

```
B                    s =  0.00
guide run            s =  0.00     run,        L = 2.5 mm
cutting line         s =  0.00     run,        L = 2.0 mm   (trim-in-place only)
tackdown             s = -1.00     double run, L = 2.5 mm
raw edge lands       s ∈ [-0.70, +1.00]
cover satin inner    c_in  = -1.95
cover satin outer    c_out = +1.05
                     W = 3.00 mm, split 65/35 inside/outside
```

Check: tackdown at −1.00 sits 0.95 mm inside `c_in` ✓. Innermost raw edge −0.70 sits 1.25 mm inside `c_in` ✓. Outermost raw edge +1.00 sits 0.05 mm inside `c_out` — **marginal**, which is exactly why the field says 3.5–4.0 mm is the safe zone when you can afford the stitches.

### 2.5 Layer 1 — placement / guide run

| Param | Default | Range | Source |
|---|---|---|---|
| Type | single run | bean only if base is dark/napped | `[V]` |
| Stitch length | **2.50 mm** | 2.0–3.0 | `[P]`; Melco outline/detail 15–25 pt `[V]` |
| Offset | **0.00 mm** | −0.5 … +0.5 | `[V]` |
| Curve handling | shorten to ≥1.5 mm where local radius < 3 mm | | `[V]` Melco Curve Compensation |
| Passes | 1 | 2 if base dark or textured | `[P]` |
| Terminate | tie-off + **color change** | | `[V]` |

**Do not bean the placement run.** Longer visible dashes help the operator, but a bean triples the perforations that will later sit *outside* the cover satin on any shape you shrink.

### 2.6 Layer 2 — cutting line

| Param | Default | Source |
|---|---|---|
| Type | single run | `[V]` |
| Stitch length | **2.00 mm** — shorter than placement; you cut against it | `[D]` |
| Offset | **0.00 mm**, coincident with B | `[V]` |
| Emit when | `mode == trim_in_place` **and** min inscribed diameter ≥ 12 mm | `[D]` — below 12 mm scissors don't fit |

### 2.7 Layer 3 — tackdown

Stitch-type choice is driven by workflow, not taste. This is a genuine conflict in the literature and it resolves cleanly:

| Workflow | Tackdown type | Why |
|---|---|---|
| Trim-in-place | **Run or double run** | Zigzag tacks get clipped by scissors and leave fabric "whiskers" `[P]` |
| Pre-cut / laser-cut | **Zigzag or E-stitch** | Nothing to trim, so a column can straddle the edge and compress it |
| Heat-sealed twill | May be **omitted** | `[V]` Melco: tackdown is optional |

| Param | Run/double-run | Zigzag (pre-cut) | E / blanket (felt) |
|---|---|---|---|
| Offset `o_tack` | **−1.00 mm** | centered on B | **−1.00 mm** spine |
| Stitch length | **2.50 mm** | — | 2.0–2.5 mm |
| Column width | — | **2.00 mm** (80 in / 20 out → −1.6 … +0.4) | 2.0–2.5 mm |
| Spacing | — | **2.00–3.00 mm** | 2.0–3.0 mm |
| Passes | 2 | 1 | 1 |

**Hard vendor constraint:** `W_tack ≤ W_cover − 2·m_bury`. Hatch enforces this itself — "Width is constrained by width of cover stitch, if used" `[V]`. At `W_cover = 3.0`, `W_tack ≤ 2.0 mm` — exactly the published default. Not a coincidence; that's Hatch's clamp showing through.

**Why −1 mm inward, stated properly:** the tackdown must compress the *appliqué* against the stabilizer, not the ground fabric. Outside stitches compress background fabric and cause peeling; inside stitches compress the appliqué `[P]`.

**Terminate:** tie-off + color change if `mode == trim_in_place`; otherwise run straight into the cover with **no stop**.

### 2.8 Layer 4 — cover

| Param | Default | Rule | Source |
|---|---|---|---|
| Type | **satin** | satin / zigzag / E / raised satin | `[V]` |
| Width `W` | **3.00 mm** | solved from §2.3; hard floor 2.5 | `[P][S][D]` |
| Inside/outside split | **65/35** trim-in-place; **50/50** pre-cut | surplus goes inward | `[P][V]` |
| Spacing | **0.40 mm** | 0.35 dense · 0.45 loose | `[P]`; Melco 4.2 pt `[V]` |
| Spacing hard bounds | **0.30 / 0.60 mm** | below 0.30 cuts fabric; above 0.60 exposes raw edge | `[P]` |
| Spacing vs width | ≤3 mm → 0.35–0.40 · 3–5 → 0.40–0.45 · >5 → 0.45+ | | `[V]` |
| Pull comp | **+0.20 mm** | up to 0.30 on knits | `[P]` |
| Underlay | **none separate** — the tackdown *is* the underlay | if enabled, sequence **after** tackdown | `[P]` |
| Corners | miter on convex >45°, overlap on concave | | `[V]` |
| Closure overlap | **4–8 stitches past the start point** | | `[S]` Stahls' |
| Restart after break | overlap **6.4 mm (¼″)** into previous stitching | | `[S]` |

**Zigzag cover (tackle-twill look):** width per §2.3, spacing **1.69 mm** (= 15 SPI) `[S]`, or **3.0 mm** — Melco's ZigZag-appliqué preset defaults to 30 pt with *no* underlay `[V]`. This is the correct recipe for athletic twill and a genuinely different aesthetic, not a cheap satin.

**E-stitch cover** — build on the same two-rail column, change stitch *order* to a comb and **enlarge the zigzag spacing substantially** (Ink/Stitch warns explicitly) `[V]`. Blanket cover offset default is **−1.0 mm**, not 0, because a blanket's spine must sit inside the edge so its legs reach across it `[V]`. This is the soft-hand option for baby goods.

### 2.9 Pre-cut vs trim-in-place, side by side

| | **Pre-cut / laser-cut** | **Trim-in-place** |
|---|---|---|
| Layers emitted | 3 | 4 |
| Machine stops per piece | **1** | **2** |
| Cut path | **= B exactly**; feed the same contour to the cutter | fabric blob = B dilated **5–10 mm** (1–2″ for large patches) |
| Governing tolerance | placement error ε: 0.75 hand, 0.40 heat-tacked | trim clearance `t_hi`: 1.5–3.0 |
| Cover width | **2.0–2.5 mm** | **3.0–4.0 mm** |
| Cover split | **50/50, offset 0** | **65/35 inward** |
| Tackdown | zigzag/E straddling B, or omitted if heat-sealed | run/double-run at −1.0 |
| Best for | repeat orders, twill, vinyl, shapes with holes, anything under 20 mm | one-offs, sampling, no cutter |

**Laser cutting adds no geometry — it removes tolerance.** Every benefit shows up as a smaller ε, which buys back cover width and therefore stitch count. A 100 mm perimeter at 0.40 mm spacing costs ~500 stitches per mm of cover width; 4.0 → 2.0 mm saves roughly a thousand stitches on one edge.

**Adhesive changes the recipe more than the cutter does.** Stahls' Poly-Twill heat-applies at **330 °F / 165 °C, 8–10 s, medium pressure** with a pillow inside the garment; a **2–3 s tack** lets you realign before committing `[S]`. Once heat-sealed, ε collapses to ~0.4 mm and the tackdown becomes optional — which is why their table can specify 2 mm.

**Do not offset the cut path.** Export the boundary polygon as SVG/DXF at 1:1 and offset the *stitches* instead, so a re-cut with different stitch settings still fits.

### 2.10 Material matrix

| Material | Frays | Tackdown | Cover | Spacing | Min stitch len | Stabilizer | Needle |
|---|---|---|---|---|---|---|---|
| **Tackle twill (coated poly)** | Yes | optional if heat-sealed | zigzag 2/3/4 mm by size, or satin | 1.69 zigzag / 0.40 satin | 2.0 | med tearaway | 75/11 sharp |
| **Cotton / quilting woven** | Heavily | double run −1.0 | satin 3.0–3.5 | 0.40 | 2.5 | med tearaway | 75/11 sharp |
| **Felt / fleece** | No | run or E, light | **blanket/E at −1.0**, or satin ≥3.0 | 0.45 | 2.5 | med tearaway | 75/11 |
| **Knit / jersey** | Rolls | **zigzag or E required** — a run lets the knit roll `[D]` | satin 3.0–3.5, pull comp **0.30** | 0.45 | 2.5 | **2.5 oz cutaway min** + WS topping | 75/11 ballpoint |
| **Vinyl / faux leather** | No | **omit** — every hole permanent | satin, loosened | 0.45–0.50 | **3.0–4.0** | tearaway | wedge point |
| **Denim / canvas** | Yes | higher density, heavier needle | satin 3.5 | 0.40 | 2.5 | tearaway | 80/12 |

Stabilizer escalation `[P]`: standard = 1 layer medium tearaway; soft base = 1 cutaway + 1 tearaway; **>15,000 stitches = 2 layers tearaway crossed**.

Machine speed `[P]`: **600–800 SPM** on the cover; **600–700** on trim-heavy multi-piece. Put this in the worksheet — the Tajima won't infer it.

**Vinyl is pre-cut only.** Never trim in hoop; the cutting-line perforations stay visible forever.

### 2.11 Multi-piece

**Overlap allowance — the one hard vendor number:**

```
overlap_allowance = W_cover / 2
```

Wilcom states it directly: "Set the cutting overlap to half the width of the cover stitching – e.g. 2mm" `[V]`. Hatch's Partial Appliqué tool is documented as accurate to **±½ the cover width** `[V]`. For the 3.0 mm default, the lower piece's boundary is dilated **1.5 mm** into the hidden region.

**Suppress the doubled border, don't stack it.** Two satins on the same 3 mm band at 0.40 mm spacing is 0.20 mm effective — below the 0.30 mm floor, i.e. guaranteed fabric damage and needle deflection.

Implementation: for each pair `(lower, upper)`, compute the arc of `lower.boundary` lying inside `upper.boundary ⊖ (W_cover/2)`, and emit the lower piece's cover **only on the complement**.

> **The lower piece's tackdown still runs on the full closed contour.** It's invisible under the overlapping fabric and it is the only thing holding that hidden edge down. Get this wrong and the feature is worthless.

**Ordering — two legitimate modes:**

- **Mode A, per-piece:** `P₁T₁C₁ · P₂T₂C₂ · …` Required whenever a later piece overlaps an earlier one, because piece 2 must be trimmed against *already-secured* piece 1. Bottom-to-top in the artwork. Cost: **2 stops per piece**.
- **Mode B, batched** (Wilcom "Combine Appliqué Components"): `P₁P₂P₃ · T₁T₂T₃ · C₁C₂C₃`, with frame-outs once after the guide-run block and once after the tack block `[V]`. Cost: **2 stops total**, any piece count. Only valid when no piece overlaps another.

**Selection rule `[D]`:** run overlap detection. Zero overlaps → Mode B. Any overlap → Mode A, or partition into overlap-free groups and batch within each group. On a single head, a six-piece design is 4 operator interventions vs 12.

### 2.12 Gates (all `[D]`, all must be enforced)

```
min_feature_width      ≥ 2·|c_in| + 1.0 mm     # ≈ 5.9 mm at the 3.0 mm default
                                               # below this no fabric shows — emit plain satin and SAY SO
min_inscribed_diameter ≥ 8 mm  (pre-cut)
                       ≥ 12 mm (trim-in-place) # scissors must fit
min_concave_radius     ≥ |c_in| + 0.3 mm       # else fillet before rail generation
min_hole_diameter      ≥ 15 mm trim-in-place;  otherwise force pre-cut
max_cover_width        ≤ 5.0 mm                # beyond this, snag risk
```

`min_feature_width` interacts with the existing small-shape run tier: a shape that fails it falls through to plain satin, and the engine must **say** it did rather than silently emitting an appliqué with no visible fabric. Wilcom hits the same wall from the vector side — "cover stitches that are too thick may be ignored" `[V]`.

### 2.13 Parameter block and solver

```jsonc
{
  "mode": "trim_in_place",          // | "pre_cut"
  "trim_discipline": "normal",      // tight(t_hi=1.5) | normal(2.0) | loose(3.0)
  "placement_error_mm": 0.75,       // pre_cut only: 0.75 hand, 0.40 heat-tacked
  "margins": { "bury_mm": 0.5, "edge_mm": 0.5 },

  "placement":    { "type": "run", "length_mm": 2.50, "offset_mm": 0.00, "passes": 1 },
  "cutting_line": { "emit": true, "type": "run", "length_mm": 2.00, "offset_mm": 0.00 },
  "tackdown": {
    "type": "double_run",           // run|double_run|zigzag|e_stitch|none
    "offset_mm": -1.00, "length_mm": 2.50,
    "width_mm": 2.00,               // zigzag/e only; clamped to W_cover - 2*bury
    "spacing_mm": 2.00
  },
  "cover": {
    "type": "satin",                // satin|zigzag|e_stitch
    "width_mm": null,               // null = solve from tolerance stack
    "inside_share": 0.65,           // 0.50 when mode == pre_cut
    "spacing_mm": 0.40,             // clamp [0.30, 0.60]
    "pull_comp_mm": 0.20,
    "closure_overlap_stitches": 6
  },
  "multi_piece": { "overlap_allowance_mm": null, "sequencing": "auto" }
}
```

```
solve_cover(o_tack, t_lo, t_hi, m_bury, m_edge, W_floor_material, inside_share):
    c_out   = o_tack + t_hi + m_edge
    c_in    = min(o_tack - m_bury, o_tack + t_lo - m_edge)
    W_req   = c_out - c_in
    W       = clamp(max(W_req, W_floor_material), 2.5, 5.0)
    surplus = W - W_req
    c_in   -= surplus * inside_share
    c_out  += surplus * (1 - inside_share)
    return quantize(c_in, 0.1), quantize(c_out, 0.1)
```

`W_floor_material`: twill 2.0 · felt 2.5 · woven 3.0 · knit 3.0 · loose weave 3.5.

### 2.14 Emission order

```
for piece in bottom_to_top_order:
    emit placement_run
    emit COLOR_CHANGE                        # 0xC3
    if trim_in_place: emit cutting_line
    emit tackdown                            # FULL closed contour, always
    if trim_in_place: emit COLOR_CHANGE
    emit cover on (contour \ suppressed_arcs)
```

Batched mode hoists the three blocks across all pieces with exactly two color changes total.

**Do not synthesize frame-out jumps in DST for v1.** Emit the color change only and let the operator use the machine's frame-forward key. A synthetic frame-out is a large jump-out/jump-back pair that some machines trim through, and it interacts badly with hoop-limit checking. Note the frame-out in the worksheet instead.

**Ties:** tie-in and tie-off at the start and end of every layer (3 stitches ≈ 0.7 mm). No trims *within* a layer.

### 2.15 Failure modes → parameter fix

| Symptom | Mechanism | Response |
|---|---|---|
| Fabric peeking outside the satin | raw edge landed beyond `c_out`; under-trim | widen `W` / shift split outward. **Re-derive from `t_hi`** — this is the tolerance stack failing, not a density problem |
| Gap at inner edge | over-trim, or `c_in` too shallow | move `c_in` inward; raise inside share toward 70/30 |
| Fraying after wash | cover too narrow or too open | spacing → 0.35; pull comp +0.2; widen `W`; fuse the appliqué back |
| Whiskers **at the trim** | zigzag tackdown + in-hoop trimming | switch tackdown to run/double run |
| Fabric shifted during trim | tackdown too light / too far from edge | double run; `\|o_tack\|` → 0.8; raise tack density |
| Border puckers | cover density too high or stabilizer under-spec | spacing → 0.45; 2.5 oz cutaway; add pull comp |
| Needle punching through | spacing below 0.30 — usually two stacked covers | apply partial-cover suppression |
| Misaligned appliqué | placement line skipped | **never suppress layer 1**, even for pre-cut |
| Permanent holes (vinyl) | stitch length too short; tackdown used | length ≥3.0 mm; drop tackdown; pre-cut only |
| Satin breaks on tight concave corner | inner rail self-intersects when concave radius < `\|c_in\|` | fillet to `r ≥ \|c_in\| + 0.3` before rail generation |

**Renderable assertion worth adding to preview:** professionals verify at **400–600% zoom** that cover stitches actually *cross* the edge line rather than running beside it `[P]`. We can check that automatically instead of asking a human to squint.

---

## 3. 3D puff / foam — complete parametric spec

### 3.1 The physical model, because it drives every number

Two mechanisms must both succeed:

1. **Coverage** — thread must hide a 2–4 mm slab now sitting *between* fabric and thread, so the satin bridges a much longer arc than it does flat. This is the density requirement.
2. **Perforation** — needle penetrations act as a perf line so waste foam tears away at the boundary. Melco: "The needle penetrations perforate the foam and allow for the excess to be pulled away upon completion" `[A/V]`.

Satin only penetrates along its **two long sides**. **A column's ends have no penetrations**, so foam does not release there. That single geometric fact is the entire reason end-caps exist.

> **Design rule: every puff region must be enclosed by a closed loop of needle penetrations.** Sides come free from the satin; ends must be manufactured.

This is the #1 engine change, because our medial-axis satin generator emits exactly the open-ended ribbons that fail here.

### 3.2 Foam

| Thickness | Verdict |
|---|---|
| 2 mm | Supported; lowest loft; common on caps |
| **3 mm** | **Default.** Strongest consensus — Madeira/E-Zee Bodybuilder ships at 3 mm; "the standard for most puff embroidery" |
| 4 mm | Practical ceiling — "usually don't recommend foam over 4 mm" `[V]` |
| 5 mm | Melco's stated hard limit |
| 6 mm | **Avoid.** "the shank is actually in the foam which traps the thread from being pulled up" — a *stitch formation* failure, not cosmetic |

**Single layer only.** Madeira sells 2-piece stacking for extra loft; Wilcom and Ignition forbid it ("the second layer can shift during sewing, causing deflection"). For an auto-digitizer, forbid it.

**Hardness matters as much as thickness.** Hard/dense Bodybuilder at 3 mm gives "a stiffer, sharper cornered profile" — better end behavior. Assume hard 3 mm as the engine default.

**Foam color matches thread. Never contrasting.** This is the hedge against the #1 failure.

Cut foam **≥ 0.5 in (12.7 mm) larger** than the finished embroidery. Multi-color puff: leave **≈ ¼ in (6.35 mm)** between puff colors; never overlap foam pieces.

### 3.3 Density — the best-documented parameter

| Value | Source |
|---|---|
| 0.15–0.17 mm | Melco Overview (snippet only) |
| **0.18 mm** | Melco PDF p.4 — **fetched, verified** |
| **0.18 mm** | Wilcom Q&A ("I use .18mm density and no underlay") |
| 0.16 mm | Hatch (vs. Hatch flat default 0.36) |
| 0.20 mm | Tajima (stated for end-face cutting stitches) |
| 0.20 mm | Madeira ("0.4mm to 0.2mm improves coverage of the foam") |

Relative: **2.0×** flat (Madeira, Ignition), **1.75–2.0×** (Jagger), **~2.25×** (Hatch).

**Converged spec:**

```
spacing_puff = spacing_flat / 2.0, clamped to [0.15, 0.20], target 0.18
```

Our `SATIN_SPACING_MM = 0.4` → **0.20**; nudge the target to 0.18. Density is thread-dependent (brands differ in weight) — expose as a per-thread trim, not a global constant. It is also the primary knob for the tear-away failure: "if you do not have a clean finished edge on your foam, increase your density." Upper bound ~0.15 — past that you get thread breaks and needle deflection.

**Discard `[C]` sources claiming 0.40–0.50 mm.** That is *looser* than normal flat satin, physically backwards, and contradicts all five tier-A sources.

### 3.4 Satin width limits

| | Value | Source |
|---|---|---|
| Hard min | **3.0 mm** | Melco PDF p.1 (verified), Melco Overview, Wilcom |
| Marginal | 2 mm — "can work, but may compress the foam too much" | `[V]` |
| Hard max | **11.0 mm** | Melco PDF p.1 (verified) |
| Machine ceiling | 12 mm (Tajima can reach 21 mm, but that's capability, not recommendation) | `[V]` |
| **Design-time ceiling** | **8.0 mm** — "by the time you add pull compensation you are over the machine limit" | `[B]` Jagger |

**Why too narrow fails:** below 3 mm the two rows of penetrations perforate the foam into a strip that shreds rather than tears, and the column crushes the foam flat.

**Why too wide fails:** the satin arcs over the foam so effective thread path >> nominal width; past 11–12 mm it snags, and auto-split kicks in and puts penetrations *in the middle of the shape*, crushing the foam down the centerline.

**Gate on stroke width, not glyph height.** Wilcom explicitly rejects the height premise: "the size of the text isn't going to dictate the possibility of applying 3D puff." A 0.5 in block letter with 3.5 mm stems is legal; a 1.5 in script with 2 mm hairlines is not.

### 3.5 End-caps — the highest-value section

Three published methods. Build **#3 as baseline plus #1 at termini**; Melco's worked example uses capping, Jagger uses both. Belt and braces is standard practice.

**Method 1 — Capping.** "A smaller satin stitch perpendicular to the ends under the final top satin stitch" `[V]`.

| Param | Value | Source |
|---|---|---|
| Spacing | **0.30 mm** ("3 points") | Melco PDF p.3 |
| Overhang past column end | **0.7 mm** (0.5 Wilcom → 0.9 Jagger) | `[V][B]` |
| Geometry | trapezoid, **wide outboard, narrow inboard**, feathered edge pointing in | `[B][V]` |
| Pull comp | **0.9 mm** | `[B]` |
| Order | **before** the top satin — caps sew *under* it | `[V][B]` |
| Connection | walk stitch between the two caps in the thread path | `[V]` |

Note the cap is **4× less dense than the top satin** (0.30 vs 0.18). Correct: the cap is buried, so it only needs **perforation**, not **coverage**. Do not inherit top-satin density into the cap.

Overhang fails in both directions: "if your cap is too far inside the end of the segment you will have loose stitches hanging over the edge of the letter."

**Method 2 — Pinching.** Rotate the angle field of the top satin "so that there are needle penetrations completely around the entire shape" `[V]`. Cheapest for an auto-digitizer — an angle-field modification on an existing column rather than a new object. Later optimization.

**Method 3 — Bean perimeter ("knife").** Maps directly onto our existing bean tier and is the cheapest high-value addition we have.

| Param | Value | Source |
|---|---|---|
| Path | element outline / wireframe | `[B]` |
| Stitch length | **1.5 mm** | `[B]` Jagger |
| Repeats | **3** (triple run: 1 forward, 2 back) | `[B]` |
| Offset | **0.0 mm** (John Deer variant: +0.2 mm outside, 1 mm length) | `[B]` |
| Start lock | yes | `[B]` |
| Start point | **bottom of the element** (cap orientation) | `[B]` |

### 3.6 What can go over foam

- **Satin only.** "Only satin stitches will give the raised puff look" `[V]`. "You cannot do puff embroidery with complex fill stitches" `[B]`.
- **Tatami/fill: verified NO**, with one qualified exception — Wilcom: "Tatami fills can be used for 3D puff, but you will want to use a satin stitch around the edge to cut the foam." That is not "tatami puffs"; it is "tatami will sit on foam and won't shred, provided a satin border does the cutting." Low textured raise, not a puff column. **Manual/advanced mode only, never auto-digitizer output.**
- **Column type: density-normalized.** Melco specifies "Column 2… keeps the density even throughout the shape." Translation: measure density along the **true stitch arc**, not the naive centerline, or curves thin out on the outside and the foam shows. This is a code-level requirement, not a setting.
- **Auto-split OFF.** Melco raises the fill threshold to **200 points = 20 mm**, far above any legal puff width so it never triggers.
- **Short stitches OFF.** "It will dig into the foam."

### 3.7 Underlay — none, replaced by a tackdown walk

Consensus: **no conventional underlay.** It compresses the foam before the top satin arrives and can shred it.

What replaces it, with hard numbers `[V]` Melco PDF p.2:

```
tackdown_walk:
  stitch_length_mm: 2.0        # "20 point walk stitch element"
  inset_mm:         0.2        # inside the puff boundary
  passes:           2          # "twice around the inside of the shape"
```

Cross-checks: Melco Overview 20–25 pt = 2.0–2.5 mm. Hatch is looser at 4 mm, single pass. Jagger is the outlier and permits a **wide zigzag underlay at 0.2 mm inset** — defensible, not contradictory: a *wide* zigzag rides the column shoulders rather than crushing the center. Ship the walk; expose the zigzag as a variant.

### 3.8 Compensation — a genuine convention split

**Convention A (Jagger):** pull compensation, large. Widen stitches **≥25%**; **0.60–0.70 mm**; caps get **0.9 mm**.
**Convention B (Wilcom):** push only, **0.3–0.4 mm**, "I don't use pull compensation." Rationale: foam pushes outward against the column.

**Recommendation:** start at **+0.3–0.4 mm over flat-satin compensation** (the two mid-range sources agree), and expose 0.6–0.7 mm as a "high loft / thick foam" preset. **This is sew-out-gated — it depends on how the host software defines the terms and cannot be resolved from documents.**

**Critical coupling, enforce as an invariant:**

```
width_designed + 2 * comp ≤ 12.0 mm
```

That invariant *is* Jagger's 8 mm design ceiling vs. 12 mm machine ceiling.

**Overlap at junctions.** Our medial-axis satin almost certainly butts segments end-to-end at branch points. **On puff, butt joints leak foam.** Force an overlap of **0.4 mm** at every junction.

### 3.9 Sequencing and machine

**Puff goes last. Universal.** "The portion of the design that will be puffed must be the last section to sew" `[V]` — all flat sections first, because you are laying a physical slab.

**Stop before the puff color — mandatory.** Melco: "Insert the Hold command in the color sequence just before the puff color." Tajima: "Insert a stop code that stops the machine after the contour is sewn… If you forget to put the stop code in digitizing, you will miss the timing to place the urethane."

| Setting | Value | Source |
|---|---|---|
| Tie-in / tie-off | **5 stitches each** — "due to the increased thickness of the foam" | `[V]` Melco PDF p.2 |
| Presser foot | **highest setting, puff color only** | `[V]` |
| Speed | **600 SPM** for caps (range 500–750; drop to 500 on breaks) | `[A/B]` |
| Needle | **80/12 sharp** — deliberately *bigger* so holes tear better | `[B]` |
| Thread | **100% polyester, 40 wt**; loosen top tension slightly | `[V][B]` |
| Bobbin detection | **OFF** for the puff color (foam dust false-trips it) | `[V]` |
| Minimum/preset | raise to 25 pt during the puff color | `[V]` |
| Backing | heavy non-woven tearaway (structured caps) | `[A]` |

**Element order on caps:** start point at the **bottom** of the element; sew **bottom-up** (brim → crown) and **center-out**.

**Reject if the element crosses the cap front seam.** A puff column over a seam sees a step change in substrate thickness on top of 3 mm of foam — hard reject for auto-placement.

**Finishing:** tear foam away only after the puff color completes. Tweezers for small areas; heat gun on **lowest** setting or a hot hair dryer for remnants. Poly thread survives this; rayon may not.

### 3.10 Full config block

```yaml
puff:
  enabled_when:
    min_stroke_width_mm: 3.0           # HARD reject below
    max_stroke_width_mm: 11.0          # HARD reject above
    design_width_ceiling_mm: 8.0       # soft: leaves comp headroom
    max_element_height_mm: 57.0        # ~2.25 in cap field
    reject_if_crosses_cap_seam: true
    reject_shapes: [holes, thin_appendages, script_hairlines]

  foam:
    thickness_mm: 3.0
    max_thickness_mm: 4.0
    hard_limit_mm: 5.0                 # needle-shank cutoff
    layers: 1                          # never stack
    hardness: hard
    color: match_thread
    oversize_mm: 12.7
    multi_color_gap_mm: 6.35

  satin:
    spacing_mm: 0.18
    spacing_range_mm: [0.16, 0.20]
    spacing_rule: flat_spacing / 2.0
    density_normalized_columns: true    # Melco "Column 2"
    short_stitches: OFF
    auto_split: OFF
    auto_split_threshold_mm: 20.0
    overlap_at_junctions_mm: 0.4
    compensation:
      mode: push
      value_mm: 0.35                    # 0.3-0.4
      alt_pull_mm: 0.65                 # Jagger convention preset
      invariant: width + 2*comp <= 12.0

  underlay:
    standard_underlay: OFF
    tackdown_walk: { stitch_len_mm: 2.0, inset_mm: 0.2, passes: 2 }

  perforation:                          # reuse the bean tier
    perimeter_bean:
      stitch_len_mm: 1.5
      repeats: 3
      offset_mm: 0.0
      start_lock: true
      start_point: bottom_of_element

  end_caps:
    method: capping                     # alt: pinching
    geometry: trapezoid_taper_inward
    overhang_mm: 0.7                    # 0.5 - 0.9
    spacing_mm: 0.30                    # perforate, not cover
    pull_comp_mm: 0.9
    order: before_top_satin
    connect_caps_with: walk_in_thread_path

  sequencing:
    puff_block: LAST
    stop_code_before_puff: true
    separate_needle_color: true
    element_order: [bottom_up, center_out]
    tie_in_stitches: 5
    tie_off_stitches: 5

  machine:
    speed_spm: 600
    presser_foot: max_height
    needle: 80/12_sharp
    thread: polyester_40wt
    bobbin_detection: OFF
    backing: heavy_nonwoven_tearaway

  forbidden:
    [tatami_over_foam, complex_fill_over_foam, underlay_over_foam,
     short_stitches, stitch_penetrations_inside_shape, stacked_foam]
```

### 3.11 Failure modes → fix

| Failure | Mechanism | Fix |
|---|---|---|
| Foam showing through the satin | density too low for the arc; or uneven density on curves | 0.16–0.18; **density-normalized column**; match foam color |
| Foam showing **at column ends** | no penetrations at the ends — the core geometric failure | caps (0.30 spacing, 0.7 mm overhang, tapered) or pinch the angle field |
| Foam at corners/junctions | butt joints leak | overlap 0.4 mm at junctions; tune cap protrusion + push comp |
| Won't tear away cleanly | perforation line incomplete or sparse | bean perimeter 1.5 mm × 3; increase density; 80/12 sharp; heat gun the remnants |
| Loft flat / crushed | penetrations inside the shape | kill underlay, auto-split, short stitches; satin only |
| Loose stitches over the letter edge | end cap set too far inboard | push overhang to 0.8–0.9 mm |
| Thread/needle breaks, "punching" | foam too thick, density too high, speed too high, foot too low | ≤4 mm single layer; 500–600 SPM; foot fully up; loosen top tension; don't cross seams |
| Thread won't pull up | needle **shank** buried in foam | foam ≤5 mm |
| False bobbin-break stops | foam dust | disable bobbin detection for the puff color |
| Foam in the wrong place | missing stop code | Stop/Hold immediately before the puff block |

### 3.12 Pricing note that belongs in the worksheet

**"Your stitch counts for puff are generally very low so absolutely do not go by the stitch count."** Puff costs **~2 extra minutes per cap** in handling alone (laying foam, tearing, finishing), excluding cutting. If EMB-Bot ever quotes, puff must be time-priced, not stitch-priced.

---

## 4. Knockdown fill — complete spec

The cheapest tier in the list. We already have tatami; the new machinery is a polygon dilate, an angle pair, and a sequencing rule.

**What it is:** a low-density fill laid *before* the design that mats down nap on towels, fleece, fur, sweaters and high-pile knits so the real stitching does not sink. It **is** the underlay — turn conventional underlay off inside it.

**Recipes, best → weakest source:**

| Recipe | Spacing | Stitch length | Angles | Passes | Cost |
|---|---|---|---|---|---|
| **Light mesh fill — recommended default** | **2–3 mm** ("3 mm handles almost everything") | **3–4 mm** | **45° / 135°** | 2 stacked | **~370 sts/in²** |
| Automatic support stitching | 0.6 mm | ~3.5 mm | 45° | 1 | ~725 sts/in² |
| **Beanie / knit hat** | **2 mm** | **4 mm** | **15° / 135°** | 2 stacked, shape larger than design | — |
| Manual cross-hatch (Embird workflow) | 2.5–4.0 mm | — | — | — | underlay OFF |

Note the two Erich Campbell recipes differ by **2×** in stitch cost for the same job — on a single head that is real cycle time. **Sew-out gate: is 3 mm × 2 passes enough on our actual towel stock?**

**Margin:** extend past the design **3.0–4.0 mm** — "about one-eighth inch or more, if the pile is extra-long" (≈3.2 mm); SewWhat-Pro ships a 4 mm border default.

**Thread:** matte (Madeira Frosted Matt or cotton blend), matched to the garment, so the knockdown doesn't read as a shiny halo.

**Sequencing:** first block in the design, on its own color stop so the operator can thread the matte/matching cone. This is an operator instruction, not a rendering detail — see §6.

**What it buys:** Campbell demonstrates holding **4 mm letters on towel** with it. Without it, the derived floor is **9–12 mm cap height on terry** `[D]`. That is the whole argument for the feature.

**Also required, per fabric:** water-soluble topping. Knockdown mats the *bottom*; only a topping stops loops blurring the *top* edge.

---

## 5. `fabrics.py` audit

File: `<user-home>\EMB-Bot\digitizer\digitizer_core\fabrics.py`

**Repo constraint first.** The file's own docstring: *"Same ids, same values, deliberately… When a sew-out moves a number, move it in both places."* Every change below must land in `src/fabrics.js` too, or a design digitized in the browser and one built in Python need different tuning on the same garment.

### 5.1 The bug-class finding: `density_adjust` runs backwards on pile

`stage7_sequence.py:72`:

```python
row_mm = (cfg.fill_row_mm or FILL_ROW_MM) * max(0.1, fabric.density_adjust)
```

`density_adjust` **multiplies row spacing**. So `terry_towel = 1.1` produces **0.44 mm rows — 10% *less* dense than baseline** — and `fleece_sweatshirt = 1.05` → 0.42 mm. Published practice for both is the opposite direction: **+10–20% density on terry**, **+10–15% on sweatshirt fleece**. To express "+15% density" the multiplier must be **≈0.87**, not 1.05/1.1.

Either the values are inverted or the field name means the opposite of what its author intended. Either way, **the two pile fabrics currently get the thinnest coverage on the substrates that need the most.**

One caveat that keeps this honest: 0.44 mm sits just under the published terry ceiling of "no more than 0.45 mm." If the intent was "cap the sparse side," the field is doing something defensible by accident. It still cannot express the +10–20% that three other sources ask for.

### 5.2 `density_adjust` never reaches satin

It multiplies `FILL_ROW_MM` only. `SATIN_SPACING_MM = 0.4` (`machine.py:52`) is global. **On terry and fleece, satin is the thing that sinks** — monogram strokes, letters, borders — and every pile source spends its ink on satin. Needs a `satin_spacing_mm` per fabric, or one multiplier applied to both.

### 5.3 Per-preset verdict

| Preset | Field | Current | Published | Verdict | Gate |
|---|---|---|---|---|---|
| `woven_dress`, `canvas_tote` | `pull_comp_mm` | **0.2** | 0.17–0.20 wovens | ✅ correct | — |
| `jersey_tee` | `pull_comp_mm` | **0.35** | 0.35–0.40 knits | ✅ correct | — |
| `pique_knit` | `pull_comp_mm` | **0.3** | **"no less than 0.40"**; Hatch ≈0.40 | ❌ low → **0.40** | **Desk-fixable** |
| `structured_cap` | `pull_comp_mm` | **0.4** | 0.40–0.45 | ⚠️ → **0.45** | **Desk-fixable** |
| `fleece_sweatshirt` | `pull_comp_mm` | **0.5** | 0.22–0.26 absolute (sweatshirt), or 10% of column width | ❌ high → **0.25** + proportional | **Desk-fixable** |
| `terry_towel` | `pull_comp_mm` | **0.6** | +10% satin width, or 20–30% proportional | ⚠️ plausible absolute; should be proportional | Desk-fixable (add field), value **sew-out-gated** |
| `terry_towel` | `density_adjust` | **1.1** (0.44 mm) | +10–20% density → **0.85–0.90** (0.34–0.36) | ❌ **inverted** (§5.1) | **Sew-out-gated** — test 0.34 / 0.40 / 0.45 over the same knockdown |
| `fleece_sweatshirt` | `density_adjust` | **1.05** (0.42) | +10–15% → 0.87–0.90, *or* hold ~1.0 and spend on knockdown | ❌ **inverted**, direction genuinely disputed | **Sew-out-gated** |
| `structured_cap` | `density_adjust` | **1.0** (0.40) | 0.35–0.40 satin / 3.5 SPI | ⚠️ → **0.9** | Desk-fixable |
| `pique_knit` | `density_adjust` | **1.0** (0.40) | 0.40–0.45 | ⚠️ → **1.05–1.1** (knits go genuinely lighter) | Desk-fixable |
| `jersey_tee` | `density_adjust` | **1.0** (0.40) | 0.45 / 4.2 SPI | ⚠️ → **1.1** | Desk-fixable |
| all | `satin_underlay` | `center_run` on 5 of 7 | center run is the *small-text* underlay; textured goods want **zigzag / double zigzag + edge run** | ❌ under-built for pique, jersey, cap | Desk-fixable |
| `structured_cap` | `fill_underlay` | `edge_zigzag` | fine, but **avoid dense fill underlay** — needle deflection at the buckram seam | ⚠️ keep lattice light | Desk-fixable |
| all | `trim_at_mm` | 3.0 / 3.5 / 4.0 | no published mm anywhere | see below | Judgement, not sourced |

**Trim distance.** Nothing in the literature gives a per-fabric mm threshold. Engineering judgement built on cited constraints: **leather/vinyl 8–10 mm** (each trim is a tie cluster = perforations; "keep trims to a minimum"); **terry/fleece 5–6 mm** (loops bury short connectors, and every trim leaves a nub to pick out of pile); **mesh/performance/thin knit 3.0 mm** (floats are visible and snag). Note `MAX_STITCH_MM = 12.1` (`machine.py:20`) is the DST record limit and is unrelated to trim policy — the engine is right to keep them separate.

### 5.4 Missing fields, each backed by a number

| Proposed field | Why | Sourced values |
|---|---|---|
| `min_satin_width_mm` | `SATIN_MIN_CROSS_MM = 0.5` is a degeneracy guard, not a legibility floor | 1.0 standard · **1.5–2.0 terry/sherpa/fleece** · 1.8 thick knit · 1.0 leather |
| `max_satin_width_mm` | `SATIN_MAX_WIDTH_MM = 3.0` sends every column >3 mm to tatami — but terry wants **satin up to 8 mm**, the 3D-buildup trick needs **≥4 mm**, and puff needs **3–11 mm**. Tatami on pile sinks. | 7–8 mm knit · 8 mm terry · **11 mm puff** · split above |
| `min_text_height_mm` | Nothing enforces legibility floors | 5.08 flat · 6.35 cap · 6.0 mesh · 3.0 leather · **9–12 terry w/o knockdown** `[D]` |
| `knockdown` (enum + params) | Whole tier absent | §4 table |
| `underlay_inset_mm` | `UNDERLAY_INSET_MM = 1.0` is global; pique explicitly needs underlay "moved further away from the edges than on an ordinary fabric" | 0.5 flat → 1.2–1.5 textured |
| `pull_comp_pct_of_width` | Three of the most specific sources give *proportional* comp, which an absolute-mm field cannot express | terry 20–30% · thick knit 20–30% · fleece 10% of column width |
| `push_comp_pct` | Performance sources pair column thickening with **shortening column ends by the same 10–15%** — pull and push on perpendicular axes of the same object | 10–15% |
| `fill_angle_avoid` | "Avoid… a 45-degree stitch angle" on performancewear (45° aligns with the knit's diagonal and telegraphs distortion) | exclude 45° ±5 |
| `max_stitches` | The backing decision is stitch-count-driven | **7,000** on single mesh no-show |
| `density_floor_mm` | Leather/vinyl is the only class where density has a **maximum**; nothing in the engine can express "never denser than X" | satin ≥0.45, fill ≥0.60 |
| `tie_policy` | `TIE_STITCH_MM = 0.8` (`machine.py:85`) is **below** the engine's own `MIN_STITCH_MM = 1.0`. On leather each tie is 3 legs in <1 mm — a perforation cluster. | leather: ≥1.5–2.0 mm legs, fewer ties |
| `specialty_allowed` | Which techniques are legal on this substrate (appliqué / puff / knockdown) | see §2.10, §3.1 |

### 5.5 Missing presets and two wrong garment mappings

Add: `performance_knit`, `leather`, `vinyl`, `mesh`, `sherpa_highpile` (distinct from fleece), `waffle_thermal`, `beanie_rib`, `tackle_twill` (as an appliqué *material*, not a ground fabric).

Two mappings in `GARMENT_FABRIC` are wrong today:

- `"beanie" → "jersey_tee"` — contradicted directly by the published beanie knockdown recipe (2 stacked fills, 2 mm, 4 mm length, 15°/135°). Should be `beanie_rib`.
- `"blanket" → "fleece_sweatshirt"` — should point at `sherpa_highpile` once it exists.

### 5.6 Two engine constants that block all specialty work

- **`SATIN_MAX_WIDTH_MM = 3.0`** — correct for flat goods, wrong for pile, and **fatal for puff**, whose legal range starts where this constant stops. Must become per-fabric and per-technique.
- **`TIE_STITCH_MM = 0.8` vs `MIN_STITCH_MM = 1.0`** — internal contradiction. `TINY_STITCH_MM = 0.5` matches published practice exactly ("in most cases .5mm is the absolute minimum before the machine starts creating hard stitches"); the tie legs don't. Puff additionally needs a **5-stitch tie mode** and appliqué a 3-stitch one, so this wants to be policy, not a constant.

### 5.7 Sew-out list (things the literature does not settle)

1. **Terry top density direction** — "+10–20% density" vs "no more than 0.45 mm ceiling." Test 0.34 / 0.40 / 0.45 mm rows over the same knockdown.
2. **Fleece density direction** — "+10–15%" vs "slightly lower than ordinary fabrics." Both credible; the difference is probably knockdown-present vs absent.
3. **Minimum text height on terry** — no published mm. Verify 6 / 9 / 12 mm cap heights with and without knockdown.
4. **Knockdown cost/benefit point** — 370 vs 725 sts/in² for the same job.
5. **Puff compensation convention** — push 0.3–0.4 vs pull 0.6–0.7 + 25% width. Not resolvable from documents.
6. **Whether the Tajima halts on a same-needle color change in DST.** Gates appliqué, ITH and puff simultaneously. **Do this one first.**
7. **Whether `density_adjust` should split** into `fill_density_adjust` + `satin_density_adjust` — every difficult substrate treats them independently.

---

## 6. Operator-facing metadata — the worksheet is now half the deliverable

### 6.1 What we ship today

`src/pdfsheet.js` emits: title, placement label, a rendered stitch image, dimensions / stitch count / color count, and a **Thread Sequence** list of `swatch + (color.name || "Color N")`.

That is a thread list. For a specialty design it is **not a worksheet**, because the operator's job at each stop is not "change thread" — it is "lay the twill," "trim," "place the foam," "turn the hoop over." A thread list actively misleads: it implies a color change where there is a material change, and on an all-one-color appliqué it implies nothing is happening at all.

### 6.2 What each stop must carry

Replace the color row with a **step row**:

| Field | Example | Why |
|---|---|---|
| `index` | `3` | matches the machine's color counter |
| `needle` | `5` | single-head: often the *same* needle across steps |
| `thread` | `Madeira Poly 1800 White` | may be identical to the previous step |
| **`action`** | `TRIM — cut fabric close to the tackdown, just outside the stitch line` | **the load-bearing field** |
| `stitches` | `412` | so the operator knows how long the block runs |
| `dwell` | `frame out, ~40 s` | sets expectations for a stop that isn't a thread change |
| `material` | `Poly-Twill, pre-cut #7` | which physical thing goes down |
| `flags` | `FRAME OUT · SAME NEEDLE` | warns that the machine will stop with no color to change |

### 6.3 Naming — the stop name IS the instruction

Kill `"Color 3"`. Name blocks by the operator verb, following Embroidery Library's fixed vocabulary:

```
1  PLACE     Sew placement outline for shield         [white]      412 st
2  LAY       Stop · lay twill over the outline        [white]        —
3  CUT+TACK  Cutting line, then tackdown              [white]      688 st
4  TRIM      Stop · frame out · trim to the tackdown  [white]        —
5  COVER     3.0 mm satin cover, 0.40 mm spacing      [gold]      3,140 st
```

For puff:

```
7  FLAT DONE All flat elements complete
8  FOAM      Stop · lay 3 mm hard foam, color-matched to thread
9  TACK      2.0 mm walk, 2 passes, 0.2 mm inset
10 PUFF      Satin 0.18 mm · foot MAX · 600 SPM · bobbin detect OFF
11 TEAR      Remove excess foam · heat gun lowest setting
```

### 6.4 Sidecars — a file bundle, not a file

DST carries none of this. Emit alongside the `.dst`:

1. **Color-change sheet** (the PDF above) — the primary human-facing artifact and the reason ITH/appliqué files work at all.
2. **Dieline / cut file** — the boundary polygon as **SVG or PDF at 1:1**. We already have the geometry; exporting it is nearly free and it is table stakes. Print it, adhere it to the fabric-plus-stabilizer sandwich, cut, hoop. **Do not offset the cut path** (§2.9).
3. **Material bill per step** — fabric, stabilizer type and weight, adhesive, foam thickness and hardness, hardware size, needle size.
4. **Hoop target and safe field** — a design sold for a 4×4 hoop is built at **≤3.93″** square. Specialty edges sit at the extreme perimeter, so the safe field, not the nominal hoop, is the constraint.
5. **"DO NOT RESIZE" flag** — hard requirement. Edge overhang (0.5 mm), tackdown inset (0.4–1.0 mm), cover width and cap overhang (0.7 mm) are **absolute, not proportional**. Scaling silently breaks all four.
6. **Machine-settings block** — the settings the Tajima will not infer and the DST cannot carry: speed, presser-foot height, bobbin-detection state, needle, tension note.
7. **Finishing spec** — heat-seal product, temperature, dwell, pressure (Stahls' Poly-Twill: 330 °F / 8–10 s / medium; heat-seal film: 320–392 °F, 15–20 s, 40–60 psi).
8. **Frame-out note** — since v1 emits the color change only and leaves the frame move to the operator's frame-forward key, the worksheet must say so at each frame-out stop.
9. **Time-based cost line, not stitch-based** — puff adds ~2 min/cap of pure handling; trim-in-place appliqué adds a stop-and-trim per piece. The stitch count lies about both.

### 6.5 Engine invariants the worksheet depends on

- The step boundary in the IR and the color-change record in the DST must be **the same object**. If the resequencer can reorder across a boundary, or the writer can drop a boundary, the sheet and the file disagree and the operator does the wrong thing at the right time.
- `stage7_sequence.py`'s nearest-neighbour ordering must be **scoped within a step**, never across one.
- Every step must carry a non-empty `action` string or the emitter should refuse to build the file. A stop with no instruction is worse than no stop.

---

## 7. What not to build, and why

**Moss / chenille — do not build.** It is a different machine, not an attachment: hooked needle and looper, **no bobbin**, pulling one loop of yarn at a time. Tajima's chenille line is the TCMX (750 rpm chenille, 6 needles/head, automatic needle-height adjustment). **A lockstitch single-head cannot be converted.** Loop height is set by needle height, not stitch length, and there is no bobbin thread to lock moss — chain borders are mandatory as tie-in/tie-off. Take letterman-jacket demand as **faux chenille**: Stipple Stemstitch plus a wool-blend thread such as Madeira Burmilana on the machine we already own `[V]`. That converts an unbuildable feature into a variant of #7.

**Sequins — skip until a customer funds the device.** Not because DST can't carry them — it carries them natively (`c0=0, c1=1` → `0x43`; confirmed three ways including pyembroidery's `SEQUIN_MODE = 0b01000011`). The blockers are (a) the **Tajima Sequin Device IV** option, which also consumes a needle, and (b) the geometry, which is the densest spec of the eight: center-to-center spacing with auto-minimum, Exact/Expand/Contract fit modes, fixing-stitch size 2.50–30.00 mm from the sequin center or auto-match with a 0.20–2.00 mm margin, and a **drop-stitch direction opposite the feed direction** with a default 90° max angle — get that wrong and the needle misses the hole and damages fabric, needle and needle plate. Plus a real engine hazard: **sequin ejects are written as jumps**, and DST infers trims from N consecutive jumps (often 3, sometimes 6 on Tajima controllers). The `0x43` mode flag is the only thing stopping the controller reading a sequin run as a trim. It is a fashion/dance-costume product, not a workwear/logo product.

**Cross-stitch fill — skip unless asked.** Crosses align to an **invisible global grid, not to the object**, so they match across adjacent objects; fractional crosses are generated at boundaries; stitch angle has no effect; auto underlay and pull compensation are automatically deactivated `[V]`. Our fill engine is object-local. That is an architectural exception, not a new fill pattern, and demand from a Tajima production shop is thin.

**ITH dimensional (fobs, zip bags, stuffies) — defer, don't kill.** The blocking primitives are the four nobody documents: **turning gaps** (a suppression span on an edge run — 8–10 cm left open in a bag lining), **flip events** (mid-design hoop inversion, mirroring all subsequent geometry and requiring the **bobbin to be wound with matching top thread** because the back becomes a finished face), **hardware voids** (3/16″ eyelet clearance, size 20 KAM snaps), and the **material stack**. Flat patches are achievable now via #1 and #5; dimensional goods are a different project.

**Multi-layer foam — forbid in the auto-digitizer.** Madeira sells 2-piece stacking; Wilcom and Ignition forbid it because the second layer shifts and causes deflection and needle breaks. Single layer only.

**Tatami over foam — forbid as auto output.** The one documented exception (tatami on foam *with a satin border doing the cutting*) yields a low textured raise, not a puff column. Manual mode only.

**Synthetic frame-out jumps in DST — not in v1.** A synthetic frame-out is a large jump-out/jump-back pair that some machines will trim through, and it interacts badly with hoop-limit checking. Emit the color change; put the frame-out in the worksheet.

**Puff on frequently washed or dry-cleaned goods — refuse the job, don't engineer around it.** The foam crumbles. Caps and outerwear only.

**Real merrow edges — don't fake them on concave shapes.** A true merrow border is always **1/8″ (3.18 mm)** and the overlock head can only follow simple convex outlines: square, rectangle, triangle, circle, oval, basic shield. A faux-merrow primitive must **refuse concave boundaries above a curvature threshold** and fall back to plain satin rather than produce something that reads as a failed merrow.

---

## 8. Build order, one line each

0. **Step/stop IR + guaranteed color-change emission + the same-needle-stop sew-out.** Everything depends on it.
1. **Appliqué**: signed offset chain → tolerance solver → four-layer emitter → partial-cover suppression → boundary SVG export.
2. **Puff**: width gate (3/11 mm) → density-normalized column → end-caps → bean perimeter → underlay suppression + 2 mm inset walk → 5-stitch ties → last-block ordering.
3. **Knockdown**: dilate + angle-pair tatami + first-block sequencing.
4. **`fabrics.py`**: fix the inverted `density_adjust` on terry and fleece, correct the four pull-comp values, split satin from fill density, add `max_satin_width_mm` (puff needs 11 mm), remap `beanie` and `blanket` — **and mirror every change into `src/fabrics.js`.**
5. **Worksheet**: step rows with action strings, machine-settings block, material bill, DO-NOT-RESIZE flag, dieline SVG sidecar.
6. Bean variants, motif runs, ITH flat patch, stipple — in that order, whenever there's room.