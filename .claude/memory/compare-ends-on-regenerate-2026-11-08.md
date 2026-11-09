---
name: compare-ends-on-regenerate-2026-11-08
description: Kent 11-08 "Keep as is (Recommended)": the Studio's Compare view (PR #1345) still ends on a regeneration, like Original view; do not make it survive
metadata:
  type: feedback
---

Compare view (PR #1345) puts the artwork over its realistic stitches with a
draggable split. Underneath, it is Original view (`originalView` plus
`compareView`), so every Original rule applies, including this one: another
view, the simulator or a regeneration ends it. Asked whether Compare should
survive a regeneration, Kent ruled on 2026-11-08: "Keep as is (Recommended)".

**Why:** Kent's call. Compare stays a strict Original sub-mode, with no new
exception.

**How to apply:** do not build "Compare survives regenerate" unless Kent asks
for it. A bug report that Compare closes after Auto Digitize describes the
intended behaviour.
