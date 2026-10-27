---
name: repin-tuples-2026-10-27
description: "2026-10-27 — W5-06a: tests/_hexrepr.py writes tuple/list/dict digests whole; tools.ci_repin re-pins them (digest by digest, or a changed count moves the whole source literal). Gain starts on a branch that has merged main."
metadata:
  type: project
---

# ci_repin: tuple, list and dict pins (W5-06a) — 2026-10-27

44 of PR #1112's 128 round-1 CI failures were tuple compares: `test_pushcomp` and
`test_shape_overrides` assert `(sha256(blob).hexdigest()[:20], stitches, bytes) ==
GOLDEN_FLAG_OFF[...]`, and pytest cut the headline to `('d26d5feef28..., 5380, 16733)`.
Extends [[ci-pin-hygiene-2026-10-25]]; tooling and tests only, no pin or engine change.

**What the pins really are** (the brief said "truncated md5"): the tuple's hash is a
**20-hex cut of a sha256**, 16 such literals, all in `test_pushcomp.py`. Every other
hex pin in the suite is 32 or 64. So a "digest" inside a container is a 20-64 hex
string; at top level it is still 32/64 only (a bare 16-hex string stays a string). The
flat-lane "dict" failure (`test_flat_lane_byte_identical`) is a JSON golden of stitch
coords, no md5 in it: a recapture, not a re-pin, and out of reach for this tool. Lists of
`S09c5bd0d` shape ids are not digests; both fall through to pytest's own diff.

**Plugin.** For `==` between two same-type tuple/list/dict holding a digest, `_hexrepr`
writes the headline with digests whole, a `hash mismatch inside a tuple, every changed
element in full:` block (`[0] left : '...'` / `right:` per changed leaf, path as
`['k'][1]`), then `whole left :` / `whole right:` when each side is under 800 chars and
reads back as the same literal. 40 changed leaves are listed, the rest counted. Any
exception returns None, so a bug here can never hide the failure it explains.

**Tool.** `read_nested` reads that block; `plan` routes each node:
- digest-only change: each digest to its literal in the tests, one ledger row per digest,
  all the old refusals (2+ occurrences, both/neither literal, one pin two values);
- a count changed too: refuse and print it, UNLESS one tuple/list/dict literal in
  `tests/**/*.py` (found by `ast`) equals the old side exactly. Then the leaves are
  rewritten in place by byte span (quote style, comment, layout kept) and the ledger says
  `whole literal moves, non-digest elements with it: [1] 5380 vs 4726; ...`;
- shape change (length/keys), pin built from parts, log cut by the plugin's limits: refuse.
`patch()` now builds every edit as a span on the original bytes and raises
`PatchConflict` (exit 1, nothing written) if two overlap, e.g. a digest swap and the
whole literal holding it.

**Evidence.** The values from #1112's saved log fed through the plugin's own explanation
and a dry run on the real `tests/test_pushcomp.py` printed exactly the two-tuple patch
(`("logo_whitebg.png", "left_chest")` and `"towel"`), nothing else. End to end: a real
inner pytest run writes the log, the tool patches the source, the same test then passes.

**Traps.** (1) The side pytest computed must not be a tuple LITERAL in the source: a
fixture that wrote `got = ("...", 5380, 16733)` made both sides literals and the tool
rightly refused, which cost one red test of mine. (2) New fixtures use synthetic
digests (`0123456789abcdef` * 2): a real pin pasted into `test_ci_repin.py` would make
every real run see two occurrences. (3) `clean_log` strips GitHub's raw-log timestamp but
NOT the `job<TAB>step<TAB>` prefix `gh run view --log` adds: the saved logs in
`Temp/embwt/plan5_logs/` need `sed -E 's/^[^\t]*\t[^\t]*\t//'` first.

**What it does NOT do.** Old logs carry only the cut headline for these pins, and the
gain starts on the first CI run of a flip branch that has merged main with this in it
(`addopts = "-p tests._hexrepr"` loads the branch's own plugin). But pytest's own
`Full diff:` block in those old logs DOES list a short tuple's elements whole
(`-     'e9daab81cc92f282e9eb',`); parsing it would make old logs usable, at the price of a
fragile reader (`?` hint lines, "Omitting N identical items"). Not built; Kent's call.
