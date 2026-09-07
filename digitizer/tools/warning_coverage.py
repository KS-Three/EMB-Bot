#!/usr/bin/env python
"""Which engine warnings reach a customer, and in whose voice?

`app/src/lib/digitizer.js`'s `WARNING_TEXT` translates engine warning codes
into customer language. Its own comment says why it exists: untranslated codes
*"reached the panel as the engine's own build-status prose"*, and the four
`CLASSIFIED_*` codes were rescued from exactly that after Kent's 2026-08-30
note — *"the photo upload is very confusing ... IDK what ANY of that even
[means]"*.

Nothing checks the rest. This does. It changes nothing and decides nothing;
it counts, and it quotes.

## The delivery chain, confirmed end to end 2026-09-07

    plan.warnings (Python)
      -> digitizer_service/app.py   "warnings": plan.warnings
      -> job.warnings
      -> DigitizePanel.runDigitize  warnings: job.warnings || []
      -> describeWarnings()         WARNING_TEXT[code] or String(w.message)
      -> otherWarningLines          filters out BACKGROUND_ENCLOSED ONLY
      -> <ul class="dgp-warnings"><li>{w.text}</li>

**There is no severity filter and no disclosure.** Every warning the engine
emits is rendered verbatim, as a plain list item, to whoever digitized.

## What the corpus emits, measured 2026-09-07

26 fixtures at 80 mm / left_chest: **27 distinct codes, 11 of them
untranslated.** Untranslated is not automatically wrong -- the engine writes
English by default, and `SMALL_SHAPES_AS_RUN` (13/26) reads *"1 shape was too
small to hold a fill or satin ... and sewed as a light outline run instead"*,
which needs no help. Four of the eleven are like that (`SMALL_SHAPES_AS_RUN`,
`BACKGROUND_ABSENT`, `TONAL_REGIONS_SPLIT`, `DUPLICATE_CONE_LAYERS_MERGED`),
and two more sit in between: `BORDER_SEAM_SHARED` (1/26, *"both circuits still
ride the same line"*) and `SHAPES_LEFT_UNSEWN` -- see the shadow below. The
remaining FIVE split into three kinds, and only the third is unambiguous:

**Engine telemetry a customer cannot act on** -- and the two most frequent
codes in the whole corpus:

  PHOTO_SEGMENT_REGION_COUNT   20/26   "...produced 58 regions (982
                                        superpixels, 32 after merging),
                                        consolidated to 14 thread colors."
  PHOTO_PALETTE_SELECTED       20/26   "...(chart-restricted weighted
                                        k-medoids)."

**A real event, reported in a unit nobody outside this repo reads:**

  THREAD_RESNAPPED_AFTER_DRIFT 13/26   "16 shape(s) had moved off the colour
                                        their thread was chosen from ...
                                        (worst dE00 37.3)"
  PALETTE_THREAD_MISMATCH       6/26   "5 shapes sew in a thread the color
                                        list does not name for their layer"

**And one that leaks the SERVER's filesystem into the panel:**

  PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE  9/26

    "Background removal was skipped -- isolated rembg venv not found at
     /home/user/EMB-Bot/digitizer/rembg_isolated/venv/bin/python -- see
     digitizer/rembg_isolated/README.md to build it. Tone, texture and face
     prep were skipped with it..."

`cfg.photo_prep_background_removal` defaults **True**, so this is not a
corpus artefact: it is what every photographic design shows on any machine
where the optional isolated venv was never built. Six more `bg_reason`
strings can reach the same sentence, including `f"rembg worker exited
{proc.returncode}: {detail}"`, where `detail` is the last line of the
worker's STDERR. `pipeline.run_stages` already passes the same string as a
separate `reason=` payload field, so the diagnostic is not what is at stake
-- only the copy of it inside the human sentence.

## The one shadow: the panel says it twice, once in each voice

`otherWarningLines` hand-filters exactly ONE code out of the plain list --
`BACKGROUND_ENCLOSED`, because it owns a dedicated banner and would otherwise
appear twice. **`SHAPES_LEFT_UNSEWN` carries the same news and is not
filtered:** *"1 shape (156.5 mm2, largest 156.5 mm2) in thread 0020 was
planned but not sewn -- enclosed background, showing the garment through."*
It fires on **10 fixtures, and all 10 of them also emit
`BACKGROUND_ENCLOSED`** -- a total containment, not a correlation. So the
dedup works and the duplicate arrives anyway, immediately under the banner,
in the engine's own words.

**The co-occurrence report that found it produced FIVE candidates and only
this one survived reading**, which is why it prints the caveat it does. The
other four are two codes that merely both fire on photographs
(`PHOTO_SEGMENT_REGION_COUNT` and `PHOTO_PALETTE_SELECTED` "travel with"
`LONG_JUMPS_TRIMMED`; `THREAD_RESNAPPED_AFTER_DRIFT` and
`SMALL_SHAPES_AS_RUN` with `SAME_THREAD_SHAPES_MERGED`) and share no subject
at all. The mutual >=80% test kills the crude base-rate matches; it does not
kill this one. **Read the two messages.**

**No fix is proposed here, deliberately, and the kinds are not one
decision.** Suppressing or translating telemetry is a product call about
voice; so is finding customer words for a drift event. The path leak is the
one with no product question in it, and it is written up as its own item
rather than fixed in the same breath as a measurement -- changing what a
customer reads is a change, not an observation.

    .venv/bin/python -m tools.warning_coverage
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

_PANEL = pathlib.Path(__file__).resolve().parents[2] / "app/src/lib/digitizer.js"


def translated_codes() -> set[str]:
    """The keys of `WARNING_TEXT`, read off the Studio source.

    Case-sensitive on purpose. `PHOTO_AUTO_TIER`'s wire value is the only
    lowercase one in the engine (`warnings_codes.PHOTO_AUTO_TIER =
    "photo_auto_tier"`, against `NAME = "NAME"` for the other 56), the panel
    keys it in lowercase to match, and an uppercase-only reader reports it as
    untranslated when it is not. That mistake was made writing this tool.
    """
    if not _PANEL.is_file():                              # pragma: no cover
        return set()
    src = _PANEL.read_text(encoding="utf-8")
    start = src.index("const WARNING_TEXT")
    return set(re.findall(r"^\s{2}([A-Za-z_][A-Za-z_0-9]*)\s*:",
                          src[start:src.index("\n};", start)], re.M))


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    known = translated_codes()
    if not known:                                         # pragma: no cover
        print(f"could not read {_PANEL} — is the Studio checked out?")
        return 1

    seen: collections.Counter = collections.Counter()
    sample: dict[str, str] = {}
    where: dict[str, set[str]] = collections.defaultdict(set)
    for fx in FIXTURES:
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
        try:
            _result, plan = digitize(TESTDATA / fx, cfg)
        except Exception as exc:                          # pragma: no cover
            print(f"SKIP {fx}: {exc}")
            continue
        for w in getattr(plan, "warnings", None) or []:
            code = w.get("code", "?")
            seen[code] += 1
            where[code].add(fx)
            sample.setdefault(code, str(w.get("message", "")))

    hdr = f"{'code':38} {'fixtures':>8}  {'translated':>10}"
    print(hdr)
    print("-" * len(hdr))
    for code, n in seen.most_common():
        print(f"{code:38} {n:8}  {'yes' if code in known else 'NO':>10}")

    untranslated = [c for c in seen if c not in known]
    print(f"\n{len(seen)} distinct codes over {len(FIXTURES)} fixtures; "
          f"{len(untranslated)} untranslated and shown in the engine's own "
          f"words:")
    for c in sorted(untranslated, key=lambda c: -seen[c]):
        print(f"\n  {c}  ({seen[c]}/{len(FIXTURES)} fixtures)")
        print(f"    {sample.get(c, '')[:150]}")
    # An untranslated code that rides along with a TRANSLATED one is the
    # worst case in this file and the least visible: the panel has already
    # said the thing in customer words, and then says it again in the
    # engine's. `otherWarningLines` dedupes exactly one code by hand
    # (BACKGROUND_ENCLOSED, which owns a banner) and cannot know about a
    # second code carrying the same news.
    # The overlap is required in BOTH directions. A one-way test is a base-rate
    # generator, not a finding: LONG_JUMPS_TRIMMED fires on 20 of 26 fixtures,
    # so almost any code covers >=80% of its own fixtures with it and reads as
    # a "shadow" while sharing no subject at all. Mutual >=80% means the two
    # codes travel together rather than one being merely common.
    shadows = []
    for c in untranslated:
        for t in seen:
            if t not in known or not where[c] or not where[t]:
                continue
            both = len(where[c] & where[t])
            if both / len(where[c]) >= 0.8 and both / len(where[t]) >= 0.8:
                shadows.append((c, t, both, len(where[c]), len(where[t])))
    if shadows:
        print("\nUntranslated codes that travel with a TRANSLATED one (mutual "
              ">=80% of fixtures) — a candidate for the panel saying the same "
              "thing twice, once in each voice. Co-occurrence is not meaning: "
              "read both messages before believing it.")
        for c, t, n, a, b in sorted(shadows, key=lambda r: -r[2]):
            print(f"  {c:36} {n}/{a}  travels with  {t:26} {n}/{b}")
    else:
        print("\nNo untranslated code travels with a translated one at mutual "
              ">=80%.")

    print("\nRead the MESSAGES, not the count — the engine writes English by "
          "default, so untranslated is only a problem where the sentence "
          "names superpixels, k-medoids or dE00.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
