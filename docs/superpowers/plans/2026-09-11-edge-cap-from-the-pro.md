# How much of an edge has thread laid along it — his and ours — and the gate that makes a cap affordable (2026-09-11)

**Status: MEASURED. `edge_cap` is Kent's call and §5 puts it to him.
`satin_rails_follow_edge` is NOT answerable from these files and that is the
finding for it.** Quality review 2026-09-08 item 14.

## 0. What already governs this

- **`cfg.edge_cap`** is built in two styles (`"bean"`, `"satin"`) and default
  OFF, one design-level block after all artwork in a thread already loaded.
  MASTER_SCOPE defect 19 carries the reason: on Kent's icon **100% of the
  293.2 mm outer silhouette is uncovered at 1.0 mm**, against 0.0% on the glyph
  edge he rated flawless. Its recorded position has been *"a sew-out settles
  which cap, if either"* (ROADMAP gate 1).
- **The gate's own test says to ask which kind of question this is.** Reading
  whether a digitizer who owns a machine caps his silhouettes is reading a
  decision already made on cloth, not inventing a physical constant — the same
  route that settled fill row spacing. That is what this does. It does not
  settle which style sews better; that still needs thread.
- **`tools/border_pro.py`** already recovers area fills from penetration
  geometry and satin columns as phases inside a run. This reuses both.

## 1. Two instruments, deliberately — and the two that pretended to be one

**`digitizer/tools/pro_silhouette.py` reads the two sides differently, because
they are knowable to different depths.** Two earlier versions of this tool
denied that and both were wrong.

- **Ours is EXACT.** We own the plan, so every run carries the kind that made
  it. The reading unions every satin, border, bean and run-tier polyline at one
  thread width through `stage7_sequence._sewn_linear_cover` — *the same
  function the edge cap's own gate uses*, so instrument and engine cannot
  drift — and measures how much of the sewn regions' outer boundary it covers.
  A fill's rows are never cover: a row ENDING on the boundary is the defect.
- **His is a LOWER BOUND.** A stitch file has no kinds, and separating a
  border from a big tatami's row-turn phases is exactly the ambiguity
  `border_pro`'s B1 and B4 warnings are about. So this counts only the columns
  `border_pro` already certifies as fill-edge borders — a spine tracking a
  fill's boundary for ≥`EDGE_FRAC` of its samples within `EDGE_NEAR_MM` — and
  credits each with the length it actually tracks. Border satin the test misses
  reads as absent, so the figure can only understate him.

### The two wrong versions, kept because the failure mode repeats

**Version 1** built cover from whole runs and skipped any run that was an area
fill. In this corpus a run is routinely both a fill and the host of the columns
bordering it (`border_pro`: run#6 of the chest file, a 542.7 mm² fill with
eleven columns, three tracking a fill edge). It read the pro **76.7–100%
uncovered** — that he does not cap at all.

**Version 2** added every column phase back, including a tatami's own row
turns, and read him **0.5–2.2% uncovered** — that he caps almost everything.
Applied to OUR side it called Hotel Fremont **0.0% uncovered**; the engine says
0.0 mm of Fremont's 203.7 mm outer boundary carries any linear stitch at all.

**What caught it was not a review — it was the gate disagreeing.** The gate
reads real run kinds, and it saved Fremont exactly nothing while the tool
claimed Fremont needed nothing. **Two instruments disagreeing is the finding.**
Neither number should have been published, and one of them was, in an earlier
commit on this branch.

## 2. What each side actually says

**Ours, exact, `edge_cap="none"`, 80 mm** — the share of the sewn silhouette
with no linear stitching on it:

| fixture | silhouette | uncovered |
|---|---|---|
| enthusiast | 556.4 mm | 5.9% |
| drone | 1,205.2 mm | 20.2% |
| becker | 659.4 mm | 24.5% |
| gaulke | 333.9 mm | 76.7% |
| whitebg | 308.0 mm | 82.6% |
| **fremont** | 203.7 mm | **100.0%** |

3,266 mm of silhouette, median **76.7%** open. Fremont is the clean case: a
badge whose satin is all interior lettering, so its outer edge is entirely
tatami row-ends.

**His, a floor:** across the five Becker files, 7,063 mm of fill edge, **at
least 19.1–26.1% of it carries a certified fill-edge border** (median 23.8%),
none of them in the same colour block as the fill they border. He does lay
thread along fill edges as a matter of course. Whether that adds up to capping
a whole design silhouette is **not knowable from a stitch file** — say the
floor, not a coverage figure.

## 3. The gate, and what it is worth

Capping the WHOLE outline whether or not anything already covers it is what
made `edge_cap` expensive. `silhouette_cap` now takes `omit` — everything
linear this design has already sewn — and both emitters drop the samples
standing on it, sewing only the stretches genuinely ending in open air. No new
constant: the arc floor is `_ARC_MIN_MM` (the column's own width) and the
tolerance `_OMIT_TOL_MM`, both already there. `run_outline` gained the arc
machinery `border_runs` already had.

| fixture | OFF | bean UNGATED | **bean GATED** | satin GATED |
|---|---|---|---|---|
| becker | 5,592 st | 10,663 (+90.7%) | **6,603 (+18.1%)** | 6,664 (+19.2%) |
| enthusiast | 2,353 | 4,716 (+100.4%) | **2,492 (+5.9%)** | 2,413 (+2.6%) |
| drone | 16,337 | 21,593 (+32.2%) | **17,376 (+6.4%)** | 17,472 (+6.9%) |
| gaulke | 9,078 | 11,653 (+28.4%) | **11,131 (+22.6%)** | 11,294 (+24.4%) |
| whitebg | 4,550 | 6,000 (+31.9%) | **5,745 (+26.3%)** | 6,002 (+31.9%) |
| fremont | 9,893 | 10,745 (+8.6%) | **10,745 (+8.6%)** | 10,930 (+10.5%) |

The gate turns a +8.6–100.4% bill into **+5.9–26.3%** (median +13.4%), and the
edge still closes: uncovered falls to **0.1–6.2%** (bean) and 0.0–6.4% (satin).
Fremont does not move, and that is the gate being right rather than failing —
its outer edge has nothing on it, so there was nothing to skip.

## 4. Which style is NOT settled here

Bean is cheaper in stitches on five of six (median +13.4% against +14.9%) and
closes the two worst fixtures better (gaulke 0.1% against 6.4%, fremont 0.9%
against 0.0% — a wash). Satin costs fewer trims (becker 50 against 54, gaulke
32 against 40, drone 88 against 92). **Neither dominates, which is exactly the
question ROADMAP gate 1 reserves for a sew-out.** The flip that follows this
picks bean and says why; one config value changes it.

## 5. `satin_rails_follow_edge` — the pro's files CANNOT settle it

The question is how far a rail sits from the artwork edge. A stitch file
contains the rails and not the artwork: the columns the pro sewed *define* the
shape he intended, so asking whether they reach its edge is circular. The
reference `.jpg` scans exist, but registering a scan to a stitch file to
sub-millimetre precision is its own project and it would still measure the
scan, not the intent. **Either artwork registration or a sew-out settles this
one; item 14's cheap route reaches `edge_cap` only.**

## 6. Kent's ruling, 2026-09-11 — and the flip

Asked with the (then uncorrected) table, he picked **"gate it, then flip"**.
The gate shipped first and changed nothing by default; this section is the
flip.

### The default is `"bean"`

Bean rather than satin because it is cheaper in stitches on five of six
fixtures (median +13.4% against +14.9%) and closes the two worst-open designs
at least as well (gaulke 0.1% uncovered against satin's 6.4%). **It is not a
dominant win and the style stays a sew-out's** (gate 1): satin costs FEWER
TRIMS on five of six — becker 50 against 54, gaulke 32 against 40, drone 88
against 92 — and priced at Kent's own `_TRIM_STITCH_EQUIVALENT` of 25 the two
are within 4% of each other overall, with satin ahead on four fixtures and
bean ahead by more on the other two. One config value changes it.

### What it costs, honestly

Trims go up, and the trim RATE moves both ways because stitches go up too
(per 1,000 stitches, at 80 mm, cap off → bean → satin):

| fixture | off | bean | satin |
|---|---|---|---|
| becker | 6.26 | **8.03** | 7.35 |
| whitebg | 1.10 | 1.39 | 1.33 |
| fremont | 4.55 | **4.28** | 4.21 |
| drone | 5.26 | 5.24 | **4.98** |
| gaulke | 2.42 | **3.50** | 2.74 |
| enthusiast | 9.77 | 9.63 | 9.95 |

Worse on becker and gaulke, better on fremont and drone, flat elsewhere.
**Four of the six are already over the 4.1 professional ceiling with the cap
OFF**, so this is not the flip breaking a band it was inside. The one place it
does cross is `test_chaining`'s 93 mm fixture (2.43 → 5.1), and that test now
pins `edge_cap="none"` on both arms rather than re-base a professional
benchmark to admit our own cost.

### The cone re-load, and Kent's second ruling

The cap sews as its own block in whichever cone owns most of the silhouette —
so on **all six fixtures** it re-loads a cone the job already ran, a stop the
`merge_duplicate_cone_layers` fold exists to remove. Measured alternative:
always reusing the last-loaded cone removes the stop and puts a badly matched
colour on the edge — on gaulke the best-match cone owns **95.0%** of the
silhouette against the last-sewn cone's **5.4%**, on enthusiast 77.8% against
22.2%. **Kent's call: keep the best match, accept the stop.**
`test_duplicate_cone_layers` and `test_rehome_resnapped` carry the carve-out by
name; every artwork revisit still fails them.

### What moved, and what deliberately did not

45 tests moved. Most are synthetic-fixture tests whose subject is artwork
sequencing, and those now pass `edge_cap="none"` explicitly — the cap is a
design-level pass with nothing to say about depth sorting or layer overrides,
and `tests/test_edge_cap.py` owns it. The byte-identity goldens
(`test_flat_lane_byte_identical`, `test_stage2_photo_segment`,
`test_pushcomp`'s isotropic hash) pin `"none"` for a stronger reason: their job
is "this OTHER change did not move the lane", and recapturing them would retire
a pre-change baseline to record a change they were never about — the posture
`conftest.PRE_FLIP` already documents. **No golden was recaptured.**

The service now flags the cap's block `design_edge: true`: it is the one block
with no review shape behind it (it outlines the union of several), so without
the flag the Sequencer would show a nameless row the user cannot map to
anything on the canvas.
