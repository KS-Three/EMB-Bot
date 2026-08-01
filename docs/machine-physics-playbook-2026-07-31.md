# The machine-physics playbook — what the fabric and the machine demand of the digitizer

Continues the numbered laws. Laws 1–14 covered geometry and the pipeline; 15 onward are what the thread, the needle, the fabric, and the shop floor demand. Every law carries its numbers, its source tier, and an honest confidence tag: **[P]** primary (manufacturer/vendor/peer-reviewed), **[T]** named trade expert, **[B]** blog-corroborated, **[D]** our own derivation, **[U]** unverified.

---

## Part 1 — The laws

### Thread and needle

**Law 15 — The loop is the whole game.** Lockstitch works because a relaxed thread balloons into a loop as the needle rises and the hook catches it. Anything that makes the loop late or small — added tension, stretched polyester (17–20% elongation before break), fabric riding up with the needle — makes the hook strike the thread (break) or miss it (skip). Run minimum workable tension: 140–150 g upper for 40wt poly, 120–130 g rayon, satin underside showing 1/3 bobbin, 2/3 top. [P] A&E, Madeira. High confidence.

**Law 16 — 40wt thread is 0.4 mm wide, and that is the unit of everything.** Lines spaced at 0.40 mm sit edge to edge: exactly one full-coverage layer. Tighter forces threads to roll over each other — rippling, distortion, breaks. Hard floor 0.35 mm; coverage-critical ceiling 0.55 mm. [P] Coats, Madeira; [T] Campbell. High confidence.

**Law 17 — The needle saws its own prior work.** Needle blade is 0.75 mm (75/11). Two penetrations within ~0.5 mm land in the same hole; the second strike shreds the first thread. Melco's own software filters stitches under 0.5 mm. Tie-in/tie-off must never stack on one point. [P] Melco, A&E; the 1–1.5 mm lock-offset figure is [U]. High confidence on the 0.5 mm radius.

**Law 18 — Stitch length floors are needle-diameter physics, not taste.** Walk ≥1.5 mm, satin ≥1.0 mm, fill ≥2.0 mm, and every stitch longer than the needle blade (~0.75 mm). Post-scaling stitches under 1 mm damage fabric and break thread. [P] Melco, Wilcom. High confidence.

**Law 19 — Breaks caused by the file are deterministic.** A point of needle thread reciprocates through the eye 30+ times before settling into the stitch, so any geometric defect gets multiplied — and it gets multiplied at the same spot every run. Repeatable break at one design position = our fault. Random-interval breaks = thread path or needle, operator's fault. This is the triage rule shops actually use to decide whether to reject a file. [P] Coats; [T] Campbell. High confidence.

**Law 20 — Heat is a duty-cycle problem, mostly not ours.** PET melts at 252 °C; needle temps measured 80 °C @ 1000 rpm up to 187 °C @ 4000; polyester loses 35–50% strength at high rpm. Single-head Tajima at ~650–1000 spm sits at the low end. Our lever is density (contact time per area), but the effect at embroidery rpm is an [U] extrapolation. [P] A&E, PMC study. Medium confidence for our speeds.

**Law 21 — One needle assumption, declared.** DB×K5 75/11 is the standard for 40wt: sharp (RG) for wovens and caps, ballpoint (SES) for knits, escalate to 80/12–90/14 for metallic 40wt and heavy goods. Needle life ~8 hours. The engine assumes 75/11; anything requiring escalation must be flagged on the worksheet. [P] Tajima, Madeira, Groz-Beckert, A&E. High confidence.

### Distortion and registration

**Law 22 — Pull is axial, push is perpendicular, and neither is a uniform outline offset.** Thread tension pulls the two penetration points together, so a column sews narrower across its stitch direction: 0.17–0.25 mm loss per full-density 40wt column (a 5 mm satin can sew ~4.5 mm). Push shoves fabric out at column ends: 0.13–0.20 mm. No major package does isotropic dilation — comp is added at penetration ends, along the stitch axis. [P] Wilcom, Melco DS manual; [T] Campbell, Embroidery Legacy. High confidence on mechanism and magnitudes.

**Law 23 — Comp scales with fabric and with width.** Anchors: 0.20 mm stable wovens, 0.35 mm t-shirt knits, 0.40 mm pique/fleece, up to 1.0 mm worst-case stretch. Width matters: ~0.15 mm on a 2 mm column, ~0.30 mm on a 7 mm column. So comp = base_fabric + slope × column_width, clamped — not one scalar. Small text is its own regime: ~50% comp at 5 mm letter height. [P] mechanism Wilcom/Melco; the mm table itself is [T/B] industry folklore, no manufacturer publishes it. Medium confidence — sew-out calibration required.

**Law 24 — Push comp is an end cutback, and it is automatable.** Cut satin ends back ~0.4 mm (one stitch); ~0.8 mm where a border will cover the junction. Industry does this manually; we do it in code. [T] Embroidery Legacy. Medium-high confidence.

**Law 25 — Registration drift is cumulative displacement, so time-adjacency wins.** Every stitch moves the fabric slightly; outlines sewn long after their fills land on moved fabric. Border each element immediately after its fill — never batch all outlines as a final pass. Big before small. On caps: bottom-up, center-out, alternate over the seam, finish-as-you-go, lettering last. [P] Melco; [T] ASI, Campbell. High confidence.

**Law 26 — Objects sew narrower than drawn, so joins need overlap and gaps need width.** Parallel stitch directions meeting: overlap 1–2 mm. Near-perpendicular: ~0 (the top layer bridges). Engineered gaps under 2 stitch rows (~0.8 mm) close up. Fill + running outline is the worst registration case — overlap deeply or drop the outline. [T] digitizers' benchmark article, mySewnet, Impressions. Medium-high confidence.

### Density, layering, pucker

**Law 27 — The density budget is a per-region sum, not a per-object setting.** coverage_units = Σ(0.4 / spacing) over everything overlapping a region, underlay included. The safe classic stack is underlay + fill + satin detail ≈ 2.5 units. Never more than two full-density fills stacked; a third layer means cutting a hole in the base (1–2 mm boundary overlap, no holes under objects <5×5 mm) or opposing angles. Embrilliance's red line is 6 thread layers ≈ 3 lockstitch passes. [P] Embrilliance; [T] Campbell; thresholds 2.5/3.5 are [D]. Medium confidence on the exact warn/block numbers.

**Law 28 — Underlay is structurally cheap and criminally expensive to omit.** Costs 15–20% of an element's stitches but only ~0.1–0.2 coverage units (spacing 3–4 mm, inset ≥0.4 mm inside edges). It is the digitizer's *only* lever against flagging, drift, and sink. Good underlay lets top spacing relax one step at constant visual coverage. [P] A&E stitch matrix, Wilcom; [T] Campbell. High confidence.

**Law 29 — Pucker is buckling: thread compression vs fabric bending stiffness.** Stylios & Lloyd model the stitch as an Euler column; fabric buckles out of plane when thread load exceeds its bending stiffness. Pucker risk ∝ density × tension for fixed geometry, and the fabric term is stiffness, not weight class. Longer fill stitches = fewer penetrations = softer on light wovens. [P] peer-reviewed + Coats/Madeira. High confidence on mechanism.

**Law 30 — Lofty and flat fabrics fail in opposite directions.** Pile (fleece, terry, pique): stitches sink — density +10–20%, doubled underlay (double zigzag / double tatami), knockdown fill extending ~3 mm past the design, min satin column 1–1.5 mm, topper assumed. Light flat wovens: pucker first — less of everything, longer stitches. More total thread on lofty goods puckers *less* because loft absorbs it. [T] Impressions. Medium-high confidence.

**Law 31 — Satin width clamps.** Under 1 mm: convert to multi-ply run. Over 8 mm: split or fill — wide satins snag in wash and wear (A&E won't recommend >6–8 mm for childrenswear). [P] A&E. High confidence.

### Fabric, stabilizer, caps

**Law 32 — Flagging is the operator's failure that only the digitizer can insure against.** Fabric bouncing with the needle shrinks the loop (Law 15) → skips, breaks, misregistration. Causes are hooping, presser foot, backing — operator domain. Our insurance is underlay that tacks garment to backing, and density the declared backing class can actually support (cutaway > tearaway > washaway in stitch support; medium cutaway ≈ heavy tearaway). [P] A&E, OESD. High confidence.

**Law 33 — Every fabric preset silently assumes a stabilizer.** Knit preset presumes cutaway; towel presumes tearaway + topper; cap presumes buckram + stiff cap tearaway (structured 1 piece, unstructured 2). The industry-standard fabric preset changes exactly three things — pull comp, underlay, spacing (Wilcom Auto Fabric) — which validates the fabrics.py schema, but the preset is only valid if the assumed backing is on the machine. Declare it; don't hide it. [P] Wilcom, Melco, OESD. High confidence.

**Law 34 — Caps are a different physical regime with hard rules.** A curved, seamed, finished object that stretches during sewing, with a raised center seam that deflects needles and swallows small letters. Hard rules: bottom-up + center-out; never section a cap-front fill; never run stitching parallel to the seam at crossings; lettering last; safe height = bill-to-curve minus 1 in (rule of thumb ≤2.25 in / ~57 mm); no lettering <5 mm or thin outline across the centerline; extra pull comp on anything crossing the seam; fill direction parallel to the fill's narrowest dimension; ~900 spm, sharp 75/11. [P] Melco (two docs); [T] ASI. High confidence.

### The shop floor

**Law 35 — Small text is where files die.** 4 mm satin letter floor; counters/openings under 0.8–1.0 mm close up; doubled lines need ≥0.8 mm separation; no underlay under tiny letters (it peeks through counters); trims per word, never per letter. Breaks at lettering are usually penetration clustering (Law 17), not raw density. [T] Campbell; [P-ish] ColDesi; [B] corroborated. High confidence.

**Law 36 — Machine time is set by stitch length distribution and stops, not the nameplate.** Plan at ~650 spm, not the rated 1,000–1,200 — firmware slows for stitches over 3–4 mm and top speed spikes tension (Law 15). One trim ≈ 120 stitch-equivalents (~11 s @ 650). A color change ≈ trim + constant, and on DST every color stop is *manual operator needle-mapping* at setup because DST carries no color data. Shops bill per 1,000 stitches ($1–3 typical); trims and stops are unbilled margin loss — 10 avoidable trims on a 144-piece run ≈ 4.4 machine-hours. [P] Tajima TMEZ, HAPPY workbook; [T] Embroidery Legacy; economics arithmetic [D]. High confidence on mechanism, medium on constants.

**Law 37 — Jerky geometry causes phantom stops.** Tajima break sensors watch thread motion; erratic draw from dense direction changes and overlong stitches trips false thread-break detection. No numeric direction-change threshold exists anywhere in primary sources — score smoothness monotonically, don't invent a cutoff. [P] A&E. Medium confidence.

**Law 38 — Preflight numbers for cost, from primary tables.** A&E stitch matrix: fill 1,000 st/in² at 6 mm length (1,500 at 4 mm when carrying lettering); satin 100–200 st/running inch by width, +15–20% with underlay; 5 mm letter ≈ 100 st; regions <1 mm wide → running stitch. Thread budget 5 m top + 3 m bobbin per 1,000 stitches. Our geometric counts are exact for generated objects; reserve the /in² coefficients for pre-digitizing estimates from artwork — real files run ~2.5–3× naive single-layer fill geometry. [P] A&E, Madeira; reconciliation [D]. High confidence.

---

## Part 2 — ENGINE CHANGE LIST

| Law | Target | Change | Status |
|---|---|---|---|
| 16, 27 | fabrics.py | Per-fabric top spacing table: woven 0.40–0.45, knit 0.45–0.50, lightweight 0.45–0.55, denim/canvas 0.35–0.38, cap 0.35, fleece/terry 0.35–0.45 (+topper assumed), puff 0.28–0.32. Hard floor 0.35 mm engine-wide. **Note: our current knit presets are tighter than every published table — loosen them.** | Desk-safe (values are published); sew-out confirms on our Tajima |
| 23 | fabrics.py | Replace scalar pull_comp with `base + slope × column_width`, clamped: base 0.20 woven / 0.35 knit / 0.40 pique-fleece, slope ≈ 0.03 mm per mm width, cap 1.0 mm. Melco-style min-column-width and max-comp clamps. | Sew-out-gated (table is trade folklore) |
| 33 | fabrics.py | Add `assumed_backing` field per preset (cutaway / tearaway / cap-buckram / topper flags). Density budget ceiling keys off backing class, not fabric alone. | Desk-safe |
| 28, 30 | fabrics.py | Underlay ledger per preset: knit/pile get edge-run + double zigzag/tatami (spacing 3–4 mm, inset ≥0.4 mm), and top spacing relaxes one step when underlay upgrades. Knockdown fill on pile, extending ~3 mm past design. | Desk-safe |
| 17, 18 | machine.py | Constants: NEEDLE_D = 0.75 mm; SAME_HOLE_R = 0.5 mm; MIN_WALK 1.5 / MIN_SATIN 1.0 / MIN_FILL 2.0 mm; hard filter stitches < 0.5 mm. | Desk-safe |
| 36, 38 | machine.py | Effective-speed model: spm = f(stitch length histogram), plan-rate 650 spm, penalty above 3 mm; TRIM_COST = 120 stitch-equivalents; thread budget 5 m + 3 m per 1k st. | Desk-safe |
| 22 | stage 5 | Pull comp applied at penetration ends along each object's stitch angle — never uniform outline dilation. Fill objects: comp on the edges the fill angle penetrates. | Desk-safe (mechanism is primary-sourced) |
| 24 | stage 5 | Automatic push cutback: 0.4 mm at open satin ends, 0.8 mm where a border object covers the junction. | Sew-out-gated |
| 26 | stage 5 | cfg.overlap_mm becomes angle- and fabric-conditional: 1.0 mm parallel joins on wovens, 1.5–2.0 knits/fleece, ~0 near-perpendicular; forbid engineered gaps < 0.8 mm. | Desk-safe defaults; gate the knit value |
| 25 | stage 7 | Sequencer: fill→border adjacency per element (no global outline pass), big-before-small, caps bottom-up/center-out/alternate-over-seam/lettering-last, optional basting box on knits. | Desk-safe |
| 34 | stage 7 + preflight | Cap mode: block sectioned cap-front fills, block seam-parallel stitching at crossings, block top-down/edge-in sequences; warn height > 57 mm; warn <5 mm detail within seam zone. | Desk-safe |
| 27 | preflight | Per-region coverage map: Σ(0.4/spacing) incl. underlay; warn ≥ 2.5 units, block/auto-hole ≥ 3.5; auto-oppose stacked fill angles; holes only under objects ≥ 5×5 mm. | Warn thresholds desk-safe; block threshold sew-out-gated |
| 17, 35 | preflight | Needle-penetration proximity map (not just density): flag clusters with pairwise gaps < 0.5 mm; flag stacked ties. This is check #1 — deterministic breaks get files rejected. | Desk-safe |
| 35 | preflight | Small-text battery: satin letters < 4 mm → convert to run or refuse; counters < 0.8 mm flagged; underlay stripped below threshold; trims per word enforced. | Desk-safe |
| 31 | preflight | Satin width clamps: < 1 mm → multi-ply run; > 8 mm → auto-split/fill. | Desk-safe |
| 36, 38 | preflight | Cost card on every output: stitch count (geometric), est. runtime @ 650 spm incl. trim cost, thread meters, trim count, color-stop count (each stop = operator mapping work; warn if > needle count). | Desk-safe |
| 37 | preflight | Monotonic smoothness score (direction-change churn per mm); no hard cutoff — none exists to copy. | Desk-safe as a score, never a block |

---

## Part 3 — Separation of duties

The stitch file can only demand; the operator must supply. Mixing the two produces files that blame the operator for our physics and worksheets that lecture the operator about ours.

**The digitizer (EMB-Bot) owns:** sew order, underlay, pull/push comp, density vs declared backing class, penetration spacing, stitch length floors, overlap/gap geometry, trim and color-stop economy, cap geometry rules, small-text conversion. Every one of these is deterministic in the file — Law 19 means we get blamed by name when they're wrong.

**The operator owns:** stabilizer purchase and piece count, topper placement, hooping (smallest hoop, taut-not-stretched, backing fully hooped), presser-foot height, needle selection and freshness (~8 h life), tensions (gram targets, 1/3–2/3 check), speed, cap loading and strap tension.

**The worksheet PDF must start carrying the digitizer's assumptions, per job:** assumed backing class and weight (e.g. "knit preset: 2–3 oz cutaway presumed; this density is not supported on tearaway"); topper yes/no; needle spec (75/11 RG or SES; escalate to 80/12 for metallic); tension targets in grams with the satin-underside 1/3–2/3 check; recommended hoop = smallest that fits + trace reminder; color-stop → needle map (DST carries none); thread meters top + bobbin; estimated runtime at 650 spm; cap jobs: load orientation, ~900 spm, placement 0.5 in above bill. None of this belongs in the DST; all of it belongs on paper next to the machine.

---

## Part 4 — What we could not verify, and what one sew-out settles

Unverified, in priority order, each with its test patch:

1. **Per-fabric pull-comp mm table (Law 23).** Trade folklore, no manufacturer table. *Test:* 5 mm circles + 2/4/7 mm columns at comp 0.0/0.2/0.35/0.5 mm on twill, jersey, pique. Measure sewn vs digital width; fit base + slope.
2. **Coverage-unit block threshold (Law 27).** Our 3.5-unit line vs Embrilliance's 6-thread-layer red. *Test:* stacked-fill ladder 2.0 → 4.0 units in 0.5 steps on twill/tearaway; note first break and hand-feel.
3. **Same-hole tolerance (Law 17).** 0.5 mm radius is Melco's filter, not a measured shred point; lock offset 1–1.5 mm is blog-tier. *Test:* tie clusters at 0.3/0.5/0.8/1.2 mm offsets, 20 repeats each, count breaks.
4. **Push cutback values (Law 24).** 0.4/0.8 mm from one expert source. *Test:* bordered squares, cutback 0/0.4/0.8 mm, measure fill peeking past border.
5. **Trim/stop seconds on our Tajima (Law 36).** 120-stitch figure is trade, not spec. *Test:* stopwatch 10 trims and 5 color stops during any patch above; recalibrate TRIM_COST.
6. **Direction-change / phantom-stop threshold (Law 37).** No number exists. *Test:* zigzag-churn strip at increasing angle density; log false break stops.
7. **Needle temp at embroidery rpm (Law 20)** — extrapolated; only matters if we ever push long dense runs at top speed. No dedicated patch; note any hard-nodule thread ends during test 2.
8. **DST axis orientation (carried over from the codec worksheet).** Our JS bit table is transposed vs pyembroidery/Tajima standard — unresolved. *Test:* the asymmetric L-mark patch, first thing on the card; everything else on the sew-out is uninterpretable if X/Y are flipped.

One hooping of twill + one of jersey + one cap covers tests 1–6 and 8. That is the next revision of the sew-out card.