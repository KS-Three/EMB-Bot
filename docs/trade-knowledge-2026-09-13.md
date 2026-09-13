# Published digitizing trade knowledge — what the vendors actually say

A verified research pass (106 agents, 24 primary sources, 108 claims extracted,
25 taken to 3-vote adversarial review, **6 confirmed / 19 refuted**) against five
questions EMB-Bot has been answering from its own corpus alone.

**Read the refutation rate as the headline.** Thirteen of nineteen voted claims
died, and they died overwhelmingly on *inferential overreach* — reading a trim
threshold as a visibility threshold, reading a max-jump format setting as a trim
trigger — not on quote fidelity. **Treat any number in this domain that is not a
verbatim vendor sentence as suspect.** That includes numbers in this file that
are not in quotation marks.

Every surviving finding rests on **category (a)** primary vendor documentation:
Wilcom (Hatch v3, EmbroideryStudio e4 and 26) and Embird (Studio manual, Studio
NEXT). No trade-press or named-practitioner source produced a surviving claim;
no blog or forum material is relied on for any number here.

---

## 1. Trim vs jump — the vendors agree with our measurement

**We were treating "no single distance threshold reproduces this professional"
as a puzzle. It is the expected shape of the published model.**

Three independent vendor doc families decline to reduce the decision to a
distance:

- **Hatch v3**, verbatim: *"if the connecting run is hidden beneath another
  object, it is more efficient to use a connecting run rather than a trim and
  tie-off"*. Independently corroborated in a different Wilcom tree (ES e4,
  `Types_of_connectors`): *"If objects are adjacent and connectors will be
  hidden, they can be used as run connectors rather than trimmed connectors."*
  Two separate documentation sets, so not a one-off sentence.
- **A three-state per-object override** (Hatch v3, structurally corroborated at
  Wilcom ES26): *"Off – No trims are inserted; Always trim – Trims are inserted
  after the object; Trim if next connector > – Trims are inserted if connectors
  exceed the specified length."* **Two of the three states bypass the millimetre
  value entirely**, which is what establishes that the mode sits ABOVE the
  distance rather than modifying it.
- **Embird publishes no distance threshold at all**: *"You should always select
  such sewing order of objects in design that there is a minimum number of trims
  required."* Driven by object sew ORDER plus same-colour and visibility. The
  verifier checked Embird's other relevant pages for a hidden length rule and
  found none, so the negative is not a one-page artefact.

**Bearing on us:** published vendor support for hypotheses (i) covered-by-later-
stitching and (ii) colour-block boundaries. `chain_links`' whole architecture —
route for cover, not for distance — is what three vendor doc families describe.
Defect 4's overlapping 542-cut / 368-float distributions are the signature of
this model, not an anomaly to be explained away.

**One figure is in the record but NOT citable.** Hatch documents a 3 mm default
for *"On, if next connector >="*, and the quote appears inside the verifier
evidence for the confirmed three-state finding — yet the standalone claim
asserting 3 mm as a citable vendor trim default was **refuted 0-3**, most likely
because it was wrapped in an over-strong contradiction framing. Re-read it at
the primary page before using it as a prior. Do not cite it from here.

## 2. Float visibility — NO PUBLISHED VALUE, and one number that contradicts us

### 2a. The contradiction: Embird 2–3 mm vs our 0.75 mm

**Embird Studio manual**, verified verbatim against the live page's raw HTML:

> *"Shape of connection was chosen so that connection runs mostly deep inside of
> the yellow object which will be sewn on the top. This helps to prevent showing
> of connection on the sew-out in case of little displacement of yellow stitches,
> which often happens as result of loose hooping of fabric or pull effect of the
> thread. If upper object is large enough, place connection at least 2~3 mm
> inside of the upper object. If it is small, place connection into the middle."*

Commensurability was checked at the code level: Embird defines a connection as
*"a series of running stitches whose only purpose is to draw thread from one
spot to another"*, routed under a later object to avoid a trim — the same
construct as our buried link. `LINK_COVER_INSET_MM = 0.75`
(`machine.py:950`, applied as `c.buffer(-0.75)` at `stage7_sequence.py:478`) is
literally the distance a link must sit inside the covering polygon. **Same
axis.** Ratio: 2.7x to 4.0x tighter.

**Why this is sharper than the ratio.** Our derivation (`machine.py`, 2026-08-04)
is a pure THREAD-REACH model — fill 0.223 mm, satin 0.501 mm, run-tier inradius
0.539 mm, plus `LINK_COVER_TOL_MM` 0.2, binding at 0.539 + 0.2 = 0.739 → 0.75.
Every term asks *where does the thread stop relative to its polygon*. **Nothing
budgets for the stitches or fabric MOVING after they are sewn.** Embird's 2–3 mm
is sized explicitly against loose hooping and thread pull — a failure mode our
number does not model at all. Confirmed by reading the derivation comment: its
own "what an inset cannot fix" list names only the fanned-satin hairline gaps.

Our comment also states the policy: *"erring big turns a buriable link into a
jump (a needle-up move, invisible); erring small sews a float on bare fabric.
Round up, never down."* By that policy, a published number 3x larger against an
unmodelled failure mode is a reason to look again.

**Three qualifiers, none of them dismissals.** Embird's figure is a routing
TARGET where ours is a permissive FLOOR, so they are not perfectly like-for-like.
The Embird page carries no date or version stamp (the same rule is restated in
the current Studio NEXT rewrite, the best available currency check). And **no
second published figure corroborates 2–3 mm anywhere** — counter-evidence search
found Wilcom publishing travel-run lengths and underlay settings but no inset
distance for hiding a connection. **Strong enough to reopen the question, not
strong enough to settle the constant.**

### 2b. The null: nobody publishes a visibility tolerance

**No vendor states, in millimetres, the clearance at which a needle-down float
over or beside existing stitching becomes visible.** Two attempts to extract one
from Wilcom's trim-settings page were voted down (1-2, then 0-3) — that page
documents a trim THRESHOLD and reading it as a VISIBILITY threshold was not
sustained.

The closest published statement is Embird's, and it is **binary, not a
tolerance**: connections belong where they are *"either hidden or do not
significantly impact the visual appearance"*, and Embird trims when *"there is
no way of how to make connections between them so that they would be not
visible"*.

On same-colour thread riding on its own already-sewn work — law 60's second
mechanism — the only published touch is Embird treating same-colour as a
PRECONDITION for an acceptable connection, never as a licence for a visible
float.

**This is the strongest available justification for sew-out card block 7.** The
number does not exist in the literature; it has to be measured on cloth.

## 3. Underlay — essentially unsourced

Wilcom ES26's run-stitch underlay page publishes **no default stitch length and
no inset from the finished edge**. The page was fetched twice with different
extraction prompts; both passes returned exactly two rows: *"Length – Sets the
maximum length of each stitch"* and *"Vary run length"* (minimum stitch length +
chord gap). Explicit negatives: no defaults column, no recommended ranges.

**The trap this closes:** `chord gap` is the natural misread — a millimetre
distance sitting on an underlay settings page — but it measures deviation of a
polyline chord from the true curve ALONG the path, **not a perpendicular inset
from a finished edge**. Laundering it into a prior for our 0.75 mm would be an
unforced error.

Everything else attempted here was refuted: a 2–3 mm "narrow column" band for
centre-run (0-3), an edge-run combination rule (0-3), Wilcom's Underlay margins
topic (0-3). **Self-limit:** this is a page-scoped negative, not proof that
Wilcom publishes no underlay inset anywhere.

Mildly informative by itself: Wilcom parameterises run length as a **cap with no
number attached** — the same shape as our 5 mm satin cap — and declines to
publish where inside that cap a design should sit.

## 4. Pull compensation — a published table, and a convention we cannot resolve

**Wilcom EmbroideryStudio 26**, verified by two independent fetches, verbatim and
in millimetres:

| Fabric | Wilcom (mm) |
|---|---|
| drills, cotton | 0.20 |
| T-shirt | 0.35 |
| fleece, jumper | 0.40 |
| lettering | 0.2 – 0.3 |

Against `fabrics.py`:

| Ours | Value | Wilcom row | |
|---|---|---|---|
| `canvas_tote` / `woven_dress` | 0.2 | drills, cotton 0.20 | **exact** |
| `jersey_tee` | 0.35 | T-shirt 0.35 | **exact** |
| `fleece_sweatshirt` | 0.5 | fleece, jumper 0.40 | **25% above** |
| `pique_knit` 0.3 · `structured_cap` 0.4 · `terry_towel` 0.6 | | no Wilcom row | — |

**Do not celebrate the two exact matches yet.** Wilcom's page **does not state
whether the millimetre value is per side or total added width**, and the
verifier confirmed that negative rather than assuming it. If the two conventions
differ, an apparent exact match is really a 2x disagreement, and the fleece row
is not 25% off but 2.5x off. **Settling per-side-vs-total is a prerequisite to
reading this table as corroboration at all.**

Two further limits, both from the page itself: Wilcom frames the table as *"Use
the following table as a guideline"* — recommended starting values, **not shipped
defaults**. And it publishes **no satin-versus-fill split**; Wilcom's own
qualifier names three variables (fabric, hooping tightness, object size) and
stitch type is not among them.

**Not found:** no fill/tatami row-spacing default, no satin density default, no
table of how either changes for knits, pique, twill, caps, performance/stretch or
towelling. The fleece row is the single fabric-specific datum recovered.

**Explicitly not inferred:** a tempting reading — that a 0.35 mm T-shirt
allowance is a third of our 1.0 mm satin floor and therefore bears on it — is
NOT made by the page and must not be attributed to it.

## 5. Satin column limits and small lettering — nothing survived

**No published minimum or maximum satin column width. No narrow floor below
which a column should become a run/bean. No wide ceiling. No minimum legible
lettering cap height. No maximum stitch length before a column must split.**

The only candidate that reached a vote — Wilcom specifying centre-run for narrow
columns with 2–3 mm as the narrow band — was **refuted 0-3**.

**Our 1.0 mm satin width floor has no published value to be validated against or
contradicted by.** Nor does the satin run-length comparison (our median 3.82 mm /
p90 4.93 against the professional's 2.52 / 5.00) have any vendor default to be
judged against.

Two numbers surfaced in passing and are recorded as **unverified leads only**:
Embird Studio NEXT's global parameters page reportedly carries a 12.7 mm maximum
stitch length and a 1.2 cm column-width exception for tie-up stitches. Neither
was fetched for this purpose or voted on. 12.7 mm is very likely a format/machine
ceiling rather than a satin-splitting rule — it is exactly 0.5 inch.

## 6. The machine layer is unsourced — and this qualifies defect 4

**All ten machine-side claims were refuted**, most unanimously: Brother PR1050X
jump-count trimming (0-3, twice), Melco's consecutive-jump-count threshold and
default (0-3, three claims), Wilcom's "Maximum Jump" as a machine-format setting
(0-3, three claims). No Tajima, Barudan or SWF documentation was reached at all.

So hypothesis (iv) — trim behaviour configured per-job on the machine rather than
per-design in the file — **has no confirmed published support**, however
plausible it is mechanically.

**Why this is decision-relevant rather than merely absent.** Our 910-move corpus
was decoded from the professional's machine FILES. It records what the file says.
**Whether it also records what the machine did is unestablished by any source
reached**, and should be treated as an open assumption when reasoning about the
3.1x trim-rate gap. One piece of corroborating text survived inside another
claim's verification — that a machine will only trim connectors longer than the
length set on the machine itself, regardless of what the file requests — but it
was never itself voted on and carries no named source here.

---

## The scope mismatch that governs how to use all of this

**The vendor coverage rule and the 2–3 mm inset both govern needle-DOWN
connecting runs. Our 910-move corpus measures needle-UP moves.** These findings
constrain how EMB-Bot should route a buried connection — which is exactly
`chain_links` and `LINK_COVER_INSET_MM`. They do **not** license leaving a
needle-up jump uncut, and applying them as if they did would be a category error.

## Coverage limits

Only two vendor families were reached. Pulse/Tajima DG, Melco DesignShop, Brother
PE-Design and Embrilliance yielded nothing citable. Two verifiers hit the
session's WebSearch budget (200/200) before hunting third-party contradiction and
compensated by reading primary pages directly — the stronger check for "vendor
document X says Y", but it means the underlay negative and the pull-compensation
table were tested only against the documents they cite.

**None of this is a sew-out.** All pages fetched live 2026-09-13.
