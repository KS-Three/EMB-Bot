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

import pathlib

import pytest

from tools.memory_budget import (ARCHIVE, BUDGET, INDEX, LINE_CAP, char_count,
                                 double_registered, entries, order_problems,
                                 read_stored, sorted_text, unregistered,
                                 unresolved)

#: The repo's `.gitattributes`, which pins the memory notes to LF.
GITATTRIBUTES = pathlib.Path(__file__).resolve().parents[2] / ".gitattributes"


@pytest.fixture(scope="module")
def text() -> str:
    # AS STORED (CRLF kept): the loader does not translate newlines either.
    return read_stored(INDEX)


@pytest.fixture(scope="module")
def archive() -> str:
    return read_stored(ARCHIVE)


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
    # ...but the loader counts JavaScript string length, UTF-16 units: a
    # character outside the BMP is TWO (found in the CLI binary, 2026-10-26).
    assert char_count("a\U0001F600b") == 4
    # It counts the text AFTER `trim()`, so the file's trailing newline is free,
    # a BOM is stripped, and inner characters are not.
    assert char_count("abc\n") == char_count("abc\r\n") == char_count(chr(0xFEFF) + "abc") == 3
    assert char_count("a b") == 3
    assert char_count(text) >= len(text.strip())      # never fewer than code points


def _crlf(lf_text: str) -> str:
    return lf_text.replace("\n", "\r\n")


def test_a_crlf_copy_is_counted_at_its_on_disk_length(tmp_path):
    """The loader does not translate newlines, so a CRLF working copy costs one
    extra character per line, and the budget has to see it.

    Found 2026-10-26: `Path.read_text` translated CRLF to LF, so on Kent's
    Windows box this test read ~146 characters fewer than the loader (one CR
    per line) and could pass on a copy the loader would cut. Build an index that
    fits as LF and does not as CRLF, write it to disk both ways, and read it
    back through the function the real check uses.
    """
    n_lines = 120
    letters = BUDGET - 10 - (n_lines - 1)                # LF total: exactly 10 under
    base, extra = divmod(letters, n_lines)
    lf_text = "\n".join("x" * (base + (i < extra)) for i in range(n_lines)) + "\n"
    lf_path, crlf_path = tmp_path / "lf.md", tmp_path / "crlf.md"
    lf_path.write_bytes(lf_text.encode("utf-8"))
    crlf_path.write_bytes(_crlf(lf_text).encode("utf-8"))

    on_lf, on_crlf = read_stored(lf_path), read_stored(crlf_path)
    assert "\r" not in on_lf and on_crlf.count("\r\n") == n_lines, "read_stored translated newlines"
    assert char_count(on_lf) == BUDGET - 10
    assert char_count(on_crlf) == BUDGET - 10 + (n_lines - 1)   # the last CR is trimmed with its LF
    assert char_count(on_lf) <= BUDGET < char_count(on_crlf), (
        "a CRLF copy of an index that just fits must be OVER budget, as the loader sees it")
    # and the translating read is what would have hidden it
    assert char_count(crlf_path.read_text(encoding="utf-8")) == char_count(on_lf)


def test_read_stored_keeps_every_carriage_return(tmp_path):
    """The same on every platform: `read_stored` decodes the bytes, so a CRLF
    file comes back with its CRs and is counted with them."""
    p = tmp_path / "MEMORY.md"
    p.write_bytes(b"- [a](a.md) \xe2\x80\x94 hook\r\n- [b](b.md) \xe2\x80\x94 hook\r\n")
    got = read_stored(p)
    assert got.count("\r\n") == 2
    assert char_count(got) == len("- [a](a.md) — hook\r\n- [b](b.md) — hook")


def test_gitattributes_pins_the_memory_notes_to_lf():
    """Without this a Windows `core.autocrlf=true` checkout writes CRLF into
    the working copy the loader reads, and the index silently loses ~1 character
    per line of headroom (146 of its 24,986 on 2026-10-26)."""
    rules = [ln.split() for ln in GITATTRIBUTES.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    hit = [r for r in rules if r[0] == ".claude/memory/*.md"]
    assert hit, ".gitattributes has no rule for .claude/memory/*.md"
    assert "eol=lf" in hit[0] and "text" in hit[0], hit[0]


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


def test_entries_are_alphabetical_by_link_filename(text):
    """Every PR appended its index line at the BOTTOM, so any two open PRs
    conflicted on the same last line of this file. An entry goes at its
    alphabetical place instead (by link filename; the archive pointer stays
    first), which collides only when two notes sort side by side."""
    problems = order_problems(text)
    assert not problems, (
        "MEMORY.md entries are not in order. Put your line at its ALPHABETICAL "
        "place by link filename (not at the bottom), or run "
        "`cd digitizer && .venv/bin/python -m tools.memory_budget --sort`.\n"
        + "\n".join(problems))
    assert sorted_text(text) == text      # the sorter and the check agree


def test_the_order_check_says_where_a_misplaced_line_goes():
    """The check is only worth its failure message: pin that it names the
    neighbours, and that the archive pointer must come first."""
    def line(name):
        return f"- [{name}]({name}.md) — hook\n"
    ordered = ("# idx\n\n" + f"- [a]({ARCHIVE.name}) — arc\n"
               + line("alpha") + line("bravo") + line("delta"))
    assert order_problems(ordered) == []
    appended = ordered + line("charlie")          # the old habit: append at the bottom
    msg = order_problems(appended)
    assert len(msg) == 1 and "'charlie.md'" in msg[0]
    assert "after 'bravo.md'" in msg[0] and "before 'delta.md'" in msg[0]
    assert sorted_text(appended).splitlines()[-1].startswith("- [delta]")
    assert order_problems(f"- [a](bravo.md) — x\n- [b]({ARCHIVE.name}) — y\n")   # pointer not first
    # the one `../../docs/` entry sorts by its filename, not its directory
    assert order_problems(ordered + "- [d](../../docs/zulu.md) — x\n") == []
    assert order_problems("- [d](../../docs/alpha.md) — x\n" + ordered)
