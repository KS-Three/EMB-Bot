---
name: ember-feature-teardown
description: "Ember Design feature/pricing-level competitive teardown (manual, pricing, Bridge app) vs EMB-Bot — handoff doc + biggest gaps"
metadata: 
  node_type: memory
  type: project
  originSessionId: 98a32431-28fc-4b04-85d2-1eca952cdca9
  modified: 2026-08-09T19:05:32.781Z
---

Feature-level teardown done 2026-08-09 from an HTTrack mirror of emberdesign.net at
`C:\My Web Sites\Ember Design\emberdesign.net` (manual docs, pricing, fill-pattern list, convert
tool, bridge tool, ~4,300 explore-gallery pages, ~370 user profiles). Complements the
architecture-level [[ember-architecture]] teardown from 2026-08-08. Full handoff doc:
`<repo-root>\docs\ember-competitive-teardown-2026-08-09.md`.

Biggest gaps vs EMB-Bot: fill-pattern library (Ember ships 13-24 named patterns w/ unique params,
counted two different ways between the two teardowns — reconcile against the live editor before
picking a match target; EMB-Bot effectively ships 1 usable fill/tatami), 7 run types vs EMB-Bot's
~3, and "Ember Bridge" — a free desktop app that pushes designs straight to a Wi-Fi machine,
no EMB-Bot equivalent even conceptually.

EMB-Bot already leads on: font count (55 vs Ember's 25 built-in, post-2026-08-04 ShareAlike pull), CIEDE2000 perceptual thread
matching (ahead of any documented vendor practice, Ember included), and engineering transparency
(EMB-Bot's docs record real defects with severity; Ember's "AI Auto Digitize" is undocumented
outside vague privacy-policy boilerplate).

**Why:** feeds Kent's 2026-07-29 market-parity-vs-Ember launch roadmap ([[emb-bot-digitizer]]).
**How to apply:** the [[dst-codec-axis-discrepancy]] and [[fill-density-convention]] bugs are
launch blockers independent of Ember and should be fixed before the fill-pattern gap is worth
closing — a broken default DST export undermines any feature-parity work. Open decisions for Kent:
fill-pattern target count, whether Bridge-style machine transfer is ever in scope, whether to
revisit the parked community/gallery feature given Ember's growth-loop stats (25k users/40k designs).
