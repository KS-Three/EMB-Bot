# Does anyone cap a silhouette? The pro's files say yes — and the bill is twice what our docs say (2026-09-11)

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

## 1. The instrument

`digitizer/tools/pro_silhouette.py`, pinned by `tests/test_pro_silhouette.py`
(3). One statistic, defined once and applied to both sides:

- the design's outline = the outer boundary of (area fills ∪ satin columns ∪
  non-fill runs);
- the cover = **linear elements only** — satin columns at their own width and
  non-fill runs at thread width. **A fill's own rows are never cover**, because
  a row ending on the boundary is the defect rather than a cap;
- the answer = the share of outline length with no cover within 1.0 mm, which
  is defect 19's own tolerance.

`--ours FIXTURE` digitizes one of our fixtures, exports it to DST and reads it
back through the same function, so our number and the pro's are never two
different instruments.

## 2. The answer: he caps, comprehensively

| | silhouette | uncovered @1.0 mm |
|---|---|---|
| **Pro** — 5 Becker files | 3,488 mm | **0.5 – 2.2%** (median 1.6%) |
| **Us, `edge_cap="none"`** — 5 fixtures | 2,954 mm | **0.0 – 79.2%** (median 15.2%) |
| Us, `"bean"` | 2,339 mm | 0.0% on every fixture |
| Us, `"satin"` | 2,810 mm | 0.0% on every fixture |

Ours, per fixture, OFF: Hotel Fremont **0.0%** (its own satin border already
closes it), drone 7.3%, Becker 15.2%, `logo_whitebg` 76.3%, gaulke **79.2%**.

So the defect is real, it is wildly uneven, and **both cap styles close it
completely.**

## 3. The bill is much larger than defect 19 records

Defect 19 quotes **bean +12.6%, satin +15.3%** — true for Kent's icon, and not
representative. Across six fixtures at 80 mm:

| fixture | none | bean | satin |
|---|---|---|---|
| becker | 5,592 st / 36 trims | 10,663 / 51 (**+90.7%**) | 11,127 / 48 (**+99.0%**) |
| enthusiast | 2,353 / 24 | 4,716 / 35 (**+100.4%**) | 3,733 / 33 (+58.6%) |
| whitebg | 4,550 / 6 | 6,000 / 11 (+31.9%) | 6,182 / 10 (+35.9%) |
| drone | 16,337 / 87 | 21,593 / 119 (+32.2%) | 19,724 / 104 (+20.7%) |
| gaulke | 9,078 / 23 | 11,653 / 39 (+28.4%) | 11,481 / 31 (+26.5%) |
| fremont | 9,893 / 46 | 10,745 / 47 (+8.6%) | 10,930 / 47 (+10.5%) |

**Two fixtures pay for nothing.** Fremont is already 0.0% uncovered and still
buys +8.6%/+10.5%. `enthusiast_logo` has no recoverable area fill at all — it
is satin lettering — so the instrument cannot even say it has a silhouette
defect, and it pays **+100.4%/+58.6%**, the largest bill on the sheet.

## 4. The measurement reversed itself once — and the reason is worth keeping

The first version read the pro as **76.7–100% uncovered**, i.e. exactly the
opposite. It built the cover from whole runs and skipped any run that was an
area fill. In this corpus a run is routinely BOTH: `border_pro`'s own report
shows run#6 of the chest file as a 542.7 mm² fill hosting eleven columns, three
of them tracking a fill edge. Skipping those runs deleted precisely the caps
being looked for.

**A measurement that agrees with the conclusion you were already heading toward
is the one to re-derive.** The first reading would have argued against a flag
the pro's own work supports, and it printed a clean table while doing it.
`tests/test_pro_silhouette.py` pins all three halves: the pro reads capped, a
fill's rows never count as cover, and columns inside fill runs do.

## 5. `satin_rails_follow_edge` — the pro's files CANNOT settle it

The question is how far a rail sits from the artwork edge. A stitch file
contains the rails and not the artwork: the columns the pro sewed *define* the
shape he intended, so asking whether they reach its edge is circular. The
reference `.jpg` scans exist, but registering a scan to a stitch file to
sub-millimetre precision is its own project and it would still measure the
scan, not the intent. **Either artwork registration or a sew-out settles this
one; item 14's cheap route reaches `edge_cap` only.**

## 6. What is Kent's

`edge_cap` has a precedent now — the trade's own practice — and a bill that is
2–8× what the docs said on four of six designs. The options, with what each
costs, are in the session's question. Nothing here flips a default.
