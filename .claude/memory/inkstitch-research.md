---
name: inkstitch-research
description: "Ink/Stitch (Inkscape embroidery extension) research pass vs EMB-Bot — gaps, corroborations, licensing; doc at EMB-Bot/docs/inkstitch-research-2026-08-10.md"
metadata: 
  node_type: memory
  type: project
  originSessionId: c9d6332d-215d-41bb-875f-187263e5c45e
  modified: 2026-08-10T21:13:38.749Z
---

Research done 2026-08-10 against live Ink/Stitch source (tag v3.3.0, github.com/inkstitch/inkstitch)
and inkstitch.org docs, not training memory. Full report: `C:\Users\EE-LT-11030\Personal\EMB-Bot\docs\inkstitch-research-2026-08-10.md`.

**Highest-value finding:** Ink/Stitch runs its own MIT-licensed pyembroidery fork, `pystitch`
(github.com/inkstitch/pystitch), not upstream pyembroidery. Its DST codec is a 5th independent
source confirming EMB-Bot's own axis bug — see [[dst-codec-axis-discrepancy]]. `pystitch` is also
a live, license-compatible swap candidate for EMB-Bot's Python digitizer's pyembroidery dependency.

**Corroboration:** Ink/Stitch's `fill.py` row_spacing is the plain consecutive-row pitch (no ×2
factor) — matches EMB-Bot's own Law 19 convention, see [[fill-density-convention]].

**Genuine gaps found (concept-level, not code — see licensing below):** meander/stipple fill,
tartan/plaid fill, ripple stitch, circular fill, e-stitch/s-stitch satin variants — EMB-Bot has
none of these; Ink/Stitch has all of them in `lib/stitches/`.

**Non-findings worth knowing:** Ink/Stitch's Auto-Satin has no raster shape-classifier comparable
to EMB-Bot's `is_satin_candidate`; its trim/travel routing is simpler than EMB-Bot's own
corpus-derived chaining laws (59-62) — EMB-Bot is ahead there, not behind. EMB-Bot's own prior fill
research already scoped guided/gradient fill accurately and in places (gradient scheduler) is more
rigorous than Ink/Stitch's shipped code.

**Why:** Kent asked for a full "I want it all" sweep of Ink/Stitch for anything usable in EMB-Bot,
feeding the same market-parity effort as [[ember-feature-teardown]] and [[emb-bot-digitizer]].

**How to apply:** Ink/Stitch is GPL-3.0 — literal code/algorithm-implementation porting into
EMB-Bot needs a clean-room reimplementation from the geometric concept, not a copy, unless EMB-Bot
accepts GPL terms for that portion. `pystitch` itself is MIT and copy-safe. Fonts carry their own
per-font licenses (mirrors EMB-Bot's existing font-license landmine) — check before importing any.
The full doc has a tiered prioritized recommendation list; read it before starting any port.
