"""`.claude/memory/MEMORY.md` has a hard ceiling the loader enforces SILENTLY.

Past ~24.4 KiB the memory system loads the file only in part and drops entries
from the BOTTOM, mentioning it in a `<system-reminder>` and nowhere else. The
index does not get worse; the tail of it stops existing.

**A budget nothing checks is a preference**, which is the ruling
`test_scope_budget.py` already applies to MASTER_SCOPE. This one is worse in
one specific way and that is why it exists separately: MASTER_SCOPE over budget
is visible in the file, while MEMORY.md over budget is invisible everywhere
except a reminder in a session that is already mis-informed.

Measured 2026-09-15: at 48,421 chars the loader cut **16 of 57 entries**,
every one written after 2026-09-03 — the DST axis fix, the fill-row ruling,
the wide-column census. Rebuilt to 12,201.

Split 2026-10-23 (Kent's call): the index sat at its ceiling again and every PR
that added a note conflicted with every other. Lines for notes dated before
2026-09-15 live in `MEMORY-archive.md`, which is NOT auto-loaded, so it carries
only the per-line cap. The live ceiling is unchanged; every note file must be
indexed in exactly ONE of the two files.

The unit is CHARACTERS, calibrated against the loader's own report, not
assumed — see `char_count`. Bytes read ~0.5 KiB high on a file this full of
em-dashes; lines cannot see it at all (57 lines, one hook over 3,400 chars).
"""
from __future__ import annotations

import pytest

from tools.memory_budget import (ARCHIVE, BUDGET, INDEX, LINE_CAP, char_count,
                                 double_registered, entries, unregistered,
                                 unresolved)


@pytest.fixture(scope="module")
def text() -> str:
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def archive() -> str:
    return ARCHIVE.read_text(encoding="utf-8")


def test_the_counter_is_characters_not_bytes_or_lines(text):
    """The unit is the whole ballgame, so pin it against the calibration.

    On 2026-09-15 the loader called a 48,421-character file "47.3KB" — chars,
    KiB-based. The same file is 48,929 BYTES (47.8 KiB), so a byte budget would
    have reported half a KiB of headroom that does not exist, and a LINE budget
    would have read 57 and seen nothing at all.
    """
    assert char_count("abc") == 3
    assert char_count("") == 0
    # A multi-byte character is ONE character, which is the whole distinction.
    assert char_count("a—b") == 3
    assert char_count("a—b") < len("a—b".encode("utf-8"))
    assert char_count(text) == len(text)


def test_memory_index_is_within_its_budget(text):
    n = char_count(text)
    if n <= BUDGET:
        return
    worst = sorted(entries(text), key=lambda r: -r[3])[:3]
    pytest.fail(
        f"MEMORY.md is {n:,} chars ({n / 1024:.1f} KiB) against a {BUDGET:,} "
        f"ceiling ({BUDGET / 1024:.1f} KiB).\n"
        f"The loader will silently drop entries from the BOTTOM — the newest "
        f"memories — and say so only in a system-reminder.\n"
        f"Longest hooks: "
        + ", ".join(f"{t[:40]!r} {ln}" for t, _r, _h, ln in worst) + ".\n"
        f"The reclaim is the HOOK text: move detail into the note, which has no "
        f"budget. Deleting an entry is NOT the reclaim — every note needs its "
        f"line, the line just does not need the note's contents.")


def test_every_registry_line_resolves(text, archive):
    """A hook pointing at nothing is worse than no hook: it reads as a real
    memory and costs a session the open before it finds out."""
    bad = unresolved(text) + unresolved(archive)
    assert not bad, f"registry lines with no file behind them: {bad}"


def test_every_note_on_disk_is_registered(text, archive):
    """An unregistered note is written, committed, and unreachable by recall.

    A line in `MEMORY-archive.md` counts: the archive is not auto-loaded but the
    live index carries a pointer to it, so a note there is reachable.
    """
    orphans = unregistered(text, archive)
    assert not orphans, (
        "note files no registry line (MEMORY.md or MEMORY-archive.md) points "
        f"at, so nothing will ever open them: {orphans}")


def test_no_note_is_indexed_twice(text, archive):
    """Exactly ONE index per note. A line copied rather than moved leaves the
    two files disagreeing about the hook, and the live copy keeps costing
    characters the archive was created to give back."""
    dupes = double_registered(text, archive)
    assert not dupes, f"notes indexed more than once across the two files: {dupes}"


def test_the_live_index_points_at_the_archive(text):
    """The archive is not auto-loaded. Without a live line naming it, a session
    never learns the pre-09-15 history and the standing rulings exist."""
    assert any(rel == ARCHIVE.name for _t, rel, _h, _n in entries(text)), (
        f"MEMORY.md has no registry line pointing at {ARCHIVE.name}")


def test_archive_entries_stay_under_the_line_cap(archive):
    """The archive has no character ceiling (it is not loaded), but its lines
    follow the same per-line rule so a line moved in keeps passing."""
    over = [(t, ln) for t, _r, _h, ln in entries(archive) if ln > LINE_CAP]
    assert not over, (
        f"archive lines over the {LINE_CAP}-char cap: "
        + ", ".join(f"{t[:40]!r} {ln}" for t, ln in over))


def test_entries_stay_under_the_line_cap(text):
    """The index states this rule in its own header. Nothing enforced it, which
    is how one hook reached 3,409 characters — longer than most of the notes it
    was summarising, and the single biggest contributor to the overflow."""
    over = [(t, ln) for t, _r, _h, ln in entries(text) if ln > LINE_CAP]
    assert not over, (
        f"registry lines over the {LINE_CAP}-char cap the index states in its "
        f"own header: " + ", ".join(f"{t[:40]!r} {ln}" for t, ln in over))


def test_the_parser_is_not_vacuous(text, archive):
    """Every assertion above passes trivially if `entries()` returns nothing.

    This is the shape of failure `test_code_wires.py` records from 2026-09-07:
    a suite of "not in" checks that a parser finding nothing passes completely.
    """
    rows = entries(text)
    assert len(rows) >= 50, len(rows)
    assert len(entries(archive)) >= 30, len(entries(archive))
    assert all(hook.strip() for _t, _r, hook, _n in rows), (
        "entries with an empty hook, which the registry format exists to carry")
    both = rows + entries(archive)
    titles = [t for t, _r, _h, _n in both]
    assert len(set(titles)) == len(titles), "duplicate titles in the registry"
    paths = [r for _t, r, _h, _n in both]
    assert len(set(paths)) == len(paths), "the same note registered twice"
