---
name: cap-order-and-the-pair-experiment-2026-09-19
description: Cap sew order built and parked OFF; the corpus holds a natural cap-vs-flat experiment on identical artwork, and the pro's trim rate is what makes most of it unreadable
metadata:
  type: project
---

Started from Kent's question "have we overlooked anything this digitizing tool
needs?" The gap hunt found eight; he picked the first.

**The gap.** `cfg.garment_id` reached `fabrics.py` for pull compensation,
underlay, density and trim distance and stopped. `stage7_sequence.py` said
"garment" twice, both in prose. Meanwhile `src/digitize.js`'s `capMode` has
ordered cap garments centre-out and bottom-up all along, unconditionally. So
one lane gave a hat cap physics and the other gave it no cap order — and the
browser lane's version is UNGATED, so while `cap_center_out` stays OFF the
two lanes still disagree. That is deliberate, not an oversight.

**The reusable instrument nobody had used.** `tools/pro_parity/prep_both.py`
records which pro file is a cap and which is a left chest, from the pro's own
filename convention — and for four clients he digitized THE SAME ARTWORK both
ways. That is a natural controlled experiment: artwork held constant, garment
varied, so any bias from the design itself cancels in the paired difference.
Reach for it for any "does the pro treat garment X differently" question, not
just this one. `tools/cap_order_pro.py` is the first use.

**And why it mostly did not work — worth knowing before the next attempt.**
A run ends at a needle lift and this pro barely lifts, which is defect 4's
3.1x trim gap seen from the other side. Seven of eight files decode to 9-13
runs across 4-5 blocks, so there is no order in them to read; only `gaulke`
(42 runs, one block) scored. n = 1. To do it properly, assign runs to REGIONS
first — `tools/pro_parity/diff` on `claude/pro-overlay-diff` already does,
pushed 2026-09-18 and still without a PR.

**The measurement reversed my own recommendation**, which is the part worth
carrying. I designed the flag expecting to recommend flipping it. Centre-out
costs +111.2% needle-up and +8 trims on gaulke; the one readable pro pair
backs bottom-up and contradicts centre-out — the expensive half is the
unsupported half. Numbers in scope-history 09-19, rulings in DOCTRINE.

**Two process notes.** The first A/B I ran showed a flat zero and I briefly
read it as "the flag does nothing" — wrong fixtures, every cone holding one
shape (see [[six-flags-invisible-at-viewing-size-2026-09-18]] for the same
shape of error: a null that is really a question about the input). And a
static before/after render cannot show an ordering change at all, because the
thread lands in the same places; a sew-progression map can. Related:
[[worktree-session-harness-guard-2026-09-17]] for driving this from a
worktree, [[first-physical-sewout-2026-09-01]] for the cloth that would
settle the flip.
