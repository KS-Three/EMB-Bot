"""tools/pro_intake: a job Kent drops in becomes a registered, measured pair.

Everything runs on a synthetic `Embroidery Files/` folder built in tmp: a job
with two garments, a zipped job, a job with no art. No client file is read.
OCR is switched off (`ocr=False`) so the census is the geometric reader's
alone and the suite needs no tesseract; the OCR gate is tested with
`read_line` stubbed.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                       # proloop_synth

import proloop_synth as synth                        # noqa: E402
from tools import pro_intake as pi                   # noqa: E402

H, W, STROKE = 3.0, 2.0, 0.8     # synthetic cap height, letter width, satin width (mm)


# ------------------------------------------------------------------ fixtures
def _stroke(x0, y0, x1, y1):
    import math
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return synth.satin_pass(x0, y0, math.hypot(x1 - x0, y1 - y0), STROKE, angle_deg=ang)


def _letter(ch, x, y=20.0, h=H, w=W):
    """A block capital of satin strokes, top-left at (x, y)."""
    v = [(x, y, x, y + h)]
    strokes = {"L": v + [(x, y + h, x + w, y + h)],
               "T": [(x, y, x + w, y), (x + w / 2, y, x + w / 2, y + h)],
               "E": v + [(x, y, x + w, y), (x, y + h / 2, x + w * 0.8, y + h / 2), (x, y + h, x + w, y + h)],
               "H": v + [(x + w, y, x + w, y + h), (x, y + h / 2, x + w, y + h / 2)]}[ch]
    return [p for s in strokes for p in _stroke(*s)]


def design(scale: float = 1.0):
    """Three colour blocks: a 30 x 15 mm fill (no lettering), the word LTEH
    at a 3 mm cap, and a row of four identical filled squares (a motif, not
    a word). Scaled about the origin: the LC cut, and each job its own
    bytes (one DST copied between jobs is its own test)."""
    fill = [[q for row in synth.fill_passes(0.0, 0.0, 30.0, 15.0) for q in row]]
    word = [_letter(ch, 2.0 + i * (W + 1.0)) for i, ch in enumerate("LTEH")]
    motif = [[q for row in synth.fill_passes(16.0 + i * 3.2, 19.5, 2.6, 2.6, row=0.3, stitch=0.8) for q in row]
             for i in range(4)]
    blocks = [((20, 20, 20), fill), ((200, 30, 30), word), ((30, 160, 60), motif)]
    return [(rgb, [[(x * scale, y * scale) for x, y in p] for p in passes]) for rgb, passes in blocks]


def art_png(path: Path, aspect: float = 30.0 / 24.0, px: int = 360):
    """One-panel artwork: a filled ellipse with a word cut out of it."""
    h = int(px / aspect)
    img = np.full((h + 40, px + 40, 3), 255, np.uint8)
    cv2.ellipse(img, (px // 2 + 20, h // 2 + 20), (px // 2, h // 2), 0, 0, 360, (40, 40, 160), -1)
    cv2.putText(img, "LTEH", (px // 3, h // 2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 6)
    cv2.imwrite(str(path), img)
    return path


def preview_jpg(path: Path):
    """A vendor preview: the same design twice, side by side."""
    tile = cv2.imread(str(art_png(path.with_suffix(".tmp.png"))))
    path.with_suffix(".tmp.png").unlink()
    gap = np.full((tile.shape[0], 80, 3), 255, np.uint8)
    cv2.imwrite(str(path), np.hstack([tile, gap, cv2.GaussianBlur(tile, (5, 5), 0)]))
    return path


def worksheet_pdf(path: Path, runs: int = 30):
    body = b"BT " + b" ".join(b"(Stitches %d) Tj" % i for i in range(runs)) + b" ET"
    path.write_bytes(b"%%PDF-1.4\n1 0 obj << /Length %d >>\nstream\n" % len(body) + body
                     + b"\nendstream\nendobj\ntrailer << >>\n%%EOF\n")
    return path


@pytest.fixture
def jobs(tmp_path):
    """root/ with three jobs; -> (root, registry, scratch)."""
    root = tmp_path / "Embroidery Files"
    acme = root / "Acme Co"
    acme.mkdir(parents=True)
    synth.write_pattern(acme / "acme logo hat.DST", design())
    synth.write_pattern(acme / "acme logo hat.PES", design())
    synth.write_pattern(acme / "acme logo LC.DST", design(0.85))
    art_png(acme / "Acme Art.png")
    preview_jpg(acme / "acme logo hat.JPG")
    worksheet_pdf(acme / "acme logo hat.pdf")
    (acme / ".DS_Store").write_bytes(b"\0junk")

    zipped = root / "Zip Co"
    zipped.mkdir()
    stage = tmp_path / "stage"
    stage.mkdir()
    synth.write_pattern(stage / "ZIPCO HAT.DST", design(1.05))
    synth.write_pattern(stage / "ZIPCO HAT.PES", design(1.05))
    art_png(stage / "zipco logo.png")
    with zipfile.ZipFile(zipped / "yourorderisready.zip", "w") as z:
        z.write(stage / "ZIPCO HAT.DST", "order/ZIPCO HAT.DST")
        z.write(stage / "ZIPCO HAT.PES", "order/ZIPCO HAT.PES")
        z.write(stage / "zipco logo.png", "order/zipco logo.png")
        z.writestr("__MACOSX/order/._ZIPCO HAT.DST", b"\0appledouble")

    noart = root / "No Art Job"
    noart.mkdir()
    synth.write_pattern(noart / "NOART BEANIE.DST", design(0.95))
    preview_jpg(noart / "NOART BEANIE.JPG")
    return root, tmp_path / "intake" / "registry.json", tmp_path / "intake" / "unzipped"


def _run(jobs, **kw):
    root, registry, scratch = jobs
    return pi.run(root, registry, scratch, ocr=False, log=lambda *_a: None, **kw)


# ------------------------------------------------------------------ the intake
def test_two_garments_pair_with_the_folder_art(jobs):
    _run(jobs)
    reg = pi.load_registry(jobs[1])
    job = reg["jobs"]["Acme Co"]
    pairs = {p["garment"]: p for p in job["pairs"]}
    assert set(pairs) == {"HAT", "LC"}
    assert pairs["HAT"]["garment_id"] == "hat_front" and pairs["LC"]["garment_id"] == "left_chest"
    assert pairs["HAT"]["slug"] == "acme_co_hat" and pairs["LC"]["slug"] == "acme_co_lc"
    for p in pairs.values():
        assert p["slug_from"] == "minted"
        assert p["art"] == "job:Acme Co/Acme Art.png" and p["art_how"] == "job folder"
    # the PES twin is found by content and brings thread colours; the LC has none
    assert pairs["HAT"]["pes"] == "job:Acme Co/acme logo hat.PES"
    assert pairs["HAT"]["census"]["threads"] == 3 and pairs["LC"]["pes"] is None
    kinds = {f["file"]: f["kind"] for f in job["files"]}
    assert kinds["acme logo hat.JPG"] == "preview"
    assert kinds["Acme Art.png"] == "art"
    assert kinds["acme logo hat.pdf"] == "worksheet"
    assert ".DS_Store" not in kinds
    assert any("acme logo hat.JPG" in f and "MANIFEST" in f for f in job["flags"])


def test_zipped_job_extracts_a_copy_never_in_place(jobs):
    root, registry, scratch = jobs
    before = sorted(p.name for p in (root / "Zip Co").rglob("*"))
    _run(jobs)
    assert sorted(p.name for p in (root / "Zip Co").rglob("*")) == before == ["yourorderisready.zip"]
    job = pi.load_registry(registry)["jobs"]["Zip Co"]
    (pair,) = job["pairs"]
    assert pair["dst"].startswith("scratch:zip_co/") and pair["garment"] == "HAT"
    assert pair["art"].startswith("scratch:zip_co/") and pair["art"].endswith("zipco logo.png")
    assert pair["census"]["threads"] == 3
    reg = pi.load_registry(registry)
    assert pi.resolve(pair["dst"], reg).is_file()
    assert not any("._" in f["file"] or "__MACOSX" in f["file"] for f in job["files"])


def test_job_with_no_art_is_flagged_and_not_handed_out(jobs):
    _run(jobs)
    job = pi.load_registry(jobs[1])["jobs"]["No Art Job"]
    (pair,) = job["pairs"]
    assert pair["garment"] == "BEANIE" and pair["art"] is None
    assert any(f.startswith("NO SOURCE ART") for f in job["flags"])
    assert {f["kind"] for f in job["files"]} == {"dst", "preview"}
    slugs = [r[0] for r in pi.registered_pairs(jobs[1])]
    assert "no_art_job_beanie" not in slugs
    assert "no_art_job_beanie" in [r[0] for r in pi.registered_pairs(jobs[1], with_art=False)]


def test_registered_pairs_are_border_census_rows(jobs):
    _run(jobs)
    rows = pi.registered_pairs(jobs[1])
    assert sorted(r[0] for r in rows) == ["acme_co_hat", "acme_co_lc", "zip_co_hat"]
    for slug, pro, art, gid in rows:
        assert Path(pro).is_file() and Path(art).is_file() and gid in ("hat_front", "left_chest")
    rec = pi.pair_record("acme_co_lc", jobs[1])
    assert rec["job"] == "Acme Co" and rec["dst"].name == "acme logo LC.DST"
    assert rec["width_mm"] == pytest.approx(30.0 * 0.85, abs=0.6)
    assert pi.pair_record("nope", jobs[1]) is None


def test_rerun_adds_only_new_jobs(jobs):
    root, registry, _scratch = jobs
    first = _run(jobs)
    assert sorted(first["new"]) == ["Acme Co", "No Art Job", "Zip Co"]
    stamp = registry.read_bytes()
    second = _run(jobs)
    assert second["new"] == [] and sorted(second["unchanged"]) == sorted(first["new"])
    assert registry.read_bytes() == stamp
    late = root / "Late Job"
    late.mkdir()
    synth.write_pattern(late / "late patch.DST", design(1.1))
    art_png(late / "late.png")
    third = _run(jobs)
    assert third["new"] == ["Late Job"]
    reg = pi.load_registry(registry)
    assert reg["jobs"]["Late Job"]["pairs"][0]["garment"] == "PATCH"
    assert {k: v for k, v in reg["jobs"].items() if k != "Late Job"} == json.loads(stamp)["jobs"]


def test_a_changed_job_is_reported_not_reread_until_rescan(jobs):
    root, registry, _scratch = jobs
    _run(jobs)
    old = pi.load_registry(registry)["jobs"]["No Art Job"]
    art_png(root / "No Art Job" / "noart logo.png")
    rep = _run(jobs)
    assert rep["changed"] == ["No Art Job"] and rep["new"] == []
    assert pi.load_registry(registry)["jobs"]["No Art Job"] == old
    rep = _run(jobs, rescan=["No Art Job"])
    assert rep["new"] == ["No Art Job"]
    (pair,) = pi.load_registry(registry)["jobs"]["No Art Job"]["pairs"]
    assert pair["art"] == "job:No Art Job/noart logo.png"
    assert pair["slug"] == "no_art_job_beanie"          # its own slug back, not a _2


def test_byte_identical_dst_in_two_jobs_is_counted_once(jobs):
    root, registry, _scratch = jobs
    other = root / "Acme Reorder"
    other.mkdir()
    (other / "acme logo hat.DST").write_bytes((root / "Acme Co" / "acme logo hat.DST").read_bytes())
    _run(jobs)
    (pair,) = pi.load_registry(registry)["jobs"]["Acme Reorder"]["pairs"]
    assert pair["same_as"] == "acme_co_hat"
    assert pair["art"] == "job:Acme Co/Acme Art.png" and pair["art_how"] == "same bytes as acme_co_hat"
    assert any("byte-identical to acme_co_hat" in f
               for f in pi.load_registry(registry)["jobs"]["Acme Reorder"]["flags"])


def test_cli_markdown_census(jobs, capsys):
    root, registry, scratch = jobs
    assert pi.main(["--root", str(root), "--registry", str(registry), "--scratch", str(scratch),
                    "--no-ocr"]) == 0
    capsys.readouterr()
    assert pi.main(["--registry", str(registry), "--all", "--markdown"]) == 0
    out = capsys.readouterr().out
    assert "| job | pair | garment |" in out
    assert "| Acme Co | acme_co_hat | HAT |" in out
    assert re.search(r"\| \d\.\d\? \|", out)                     # geometric only: marked '?'


# ------------------------------------------------------------------ the pieces
@pytest.mark.parametrize("rel, garment", [
    ("C GOLKE hat beanie.DST", "BEANIE"),
    ("PROSEALHAT BEANI.DST", "BEANIE"),
    ("PROSEALHAT.DST", "HAT"),
    ("Becker Hat & Polo Large/beckers logolc.DST", "LC"),
    ("Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.DST", "LC"),
    ("Hotel Patch/HOTEL FREMONT .DST", "PATCH"),
    ("Mfab Hat & Polo/mf4b logo hat.DST", "HAT"),
    ("Mfab Hat & Polo/mf4b logo.DST", None),        # a folder naming two garments says nothing
    ("GOLKE LOGO JB 1.DST", None),
    ("order.zip!x/TIRES HAT 3D.DST", "HAT"),
])
def test_garment_from_name(rel, garment):
    assert pi.garment_of(rel)[0] == garment


def test_preview_by_content_and_name(tmp_path):
    pre = preview_jpg(tmp_path / "logo hat.JPG")
    art = art_png(tmp_path / "logo.png")
    motif = tmp_path / "motif.png"                  # art that repeats itself side by side
    cv2.imwrite(str(motif), cv2.imread(str(pre)))
    one = art_png(tmp_path / "logo hat.png")        # one panel, named like the stitch file
    dst = synth.write_pattern(tmp_path / "logo hat.DST", design())
    rows = {r["rel"]: r for r in pi.classify_files([(p, p.name) for p in (pre, art, motif, one, dst)])}
    assert pi.is_preview(rows["logo hat.JPG"]["panel"])
    assert rows["logo hat.JPG"]["kind"] == "preview"
    assert rows["logo.png"]["kind"] == "art" and rows["logo.png"]["panel"]["panels"] == 1
    assert rows["motif.png"]["kind"] == "preview?"
    assert rows["logo hat.png"]["kind"] == "art?"
    assert rows["logo hat.DST"]["kind"] == "dst"


def test_pdf_worksheet_by_text_layer(tmp_path):
    rows = pi.classify_files([(worksheet_pdf(tmp_path / "proof.pdf"), "proof.pdf"),
                              (worksheet_pdf(tmp_path / "vector.pdf", runs=2), "vector.pdf")])
    assert [r["kind"] for r in rows] == ["worksheet", "pdf?"]


def test_zip_member_escaping_the_archive_is_refused(tmp_path):
    job = tmp_path / "Evil"
    job.mkdir()
    with zipfile.ZipFile(job / "x.zip", "w") as z:
        z.writestr("ok.DST", b"x")
        z.writestr("../../outside.DST", b"x")
    with zipfile.ZipFile(job / "mac.zip", "w") as z:
        z.writestr("To a T:Becker Beanies/beckers beanie.DST", b"y")    # a Mac name
    files, refused = pi.extract_zips(job, tmp_path / "scratch", "evil")
    assert refused == ["x.zip"]
    assert not (tmp_path / "outside.DST").exists()
    assert not list((tmp_path / "scratch").rglob("ok.DST"))           # refused whole
    (path, label), = files
    assert path.parent.name == "To a T-Becker Beanies"
    assert label == "mac.zip!To a T-Becker Beanies/beckers beanie.DST"


def test_copy_marks_and_prefixes_still_name_a_preview(tmp_path):
    dst = synth.write_pattern(tmp_path / "Machine beanie E (1).DST", design())
    pre = preview_jpg(tmp_path / "Machine beanie E.JPG")
    multi = preview_jpg(tmp_path / "multi Machine beanie E (1).JPG")
    art = art_png(tmp_path / "Machine logo.png")                    # contains no stitch stem
    rows = {r["rel"]: r["kind"] for r in pi.classify_files([(q, q.name) for q in (dst, pre, multi, art)])}
    assert rows == {dst.name: "dst", pre.name: "preview", multi.name: "preview", art.name: "art"}
    assert pi.stem_key("Machine beanie E-1 (1).PES") == "machine beanie e"


def test_lettering_census_reads_the_word_not_the_fill_or_the_motif(tmp_path):
    dst = synth.write_pattern(tmp_path / "x.DST", design())
    c = pi.census_of(dst, ocr=False)
    assert c["blocks"] == 3 and c["stitches"] > 0
    assert set(c["lettering"]) == {"block 2"}
    assert 3.0 <= c["lettering"]["block 2"] <= 4.0           # the word's cap, less the 0.4 mm thread
    assert c["fine_lettering"] is True
    assert c["ocr"].startswith("none")
    assert [ln["pieces"] for ln in c["lines"]] == [4]


def test_lettering_takes_the_smallest_line_tesseract_confirms(tmp_path, monkeypatch):
    two = design()
    # the same word again at twice the cap, in the same block, under it
    big = [_letter(ch, 2.0 + i * (2 * W + 2.0), y=26.0, h=2 * H, w=2 * W) for i, ch in enumerate("LTEH")]
    two[1] = (two[1][0], two[1][1] + big)
    dst = synth.write_pattern(tmp_path / "x.DST", two)
    calls = []

    def fake(g):
        calls.append(len(g))
        return {"text": "XYZ", "conf": 90.0, "ok": len(calls) == 2}   # the small line fails, the big reads
    monkeypatch.setattr(pi, "read_line", fake)
    c = pi.census_of(dst, ocr=True)
    assert len(calls) == 2
    small, large = sorted(ln["cap_mm"] for ln in c["lines"])
    assert c["lettering"] == {"block 2": large} and large > small * 1.5
    assert [ln["lettering"] for ln in c["lines"]] == [False, True]


def test_read_line_wants_a_word_not_a_confident_letter(monkeypatch):
    from digitizer_core import legibility
    reads = {}
    monkeypatch.setattr(legibility, "ocr", lambda img, psm, blur, thin: reads[img.shape])
    piece = {"ox": 0, "oy": 0, "mask": np.ones((40, 20), bool)}

    def line(n):
        return [dict(piece, ox=i * 30) for i in range(n)]

    def verdict(n, text, conf):
        img = pi.line_image(line(n))
        reads[img.shape] = (text, conf)
        return pi.read_line(line(n))["ok"]
    assert verdict(3, "THE", 96.0) is True
    assert verdict(3, "THE", 69.0) is False             # under OCR_CONF_MIN
    assert verdict(3, "TE", 96.0) is False              # under OCR_MIN_LETTERS
    assert verdict(9, "7AGS", 90.0) is False            # 4 letters off 9 pieces: not a word
    assert verdict(5, "EATSTAYPLAY", 95.0) is True      # joined letters read more, not fewer


def test_overlay_is_drawn(tmp_path):
    dst = synth.write_pattern(tmp_path / "x.DST", design())
    pi.census_of(dst, overlay=tmp_path / "ov.png", ocr=False)
    img = cv2.imread(str(tmp_path / "ov.png"))
    assert img is not None and img.shape[0] > 100


# ------------------------------------------------------------------ the consumers
@pytest.fixture
def kent(tmp_path, monkeypatch, jobs):
    """The synthetic jobs registered where the tools look by default
    (`EMB_SCRATCH_KENT/pro_intake/registry.json`)."""
    k = tmp_path / "scratch_kent"
    monkeypatch.setenv("EMB_SCRATCH_KENT", str(k))
    _root, registry, scratch = pi.default_paths()
    pi.run(jobs[0], registry, scratch, ocr=False, log=lambda *_a: None)
    return registry


def test_pro_pair_takes_a_registered_job(kent):
    from tools import pro_pair
    args = pro_pair.parse_args(["--job", "acme_co_lc", "--out", "x"])
    assert args.art.name == "Acme Art.png" and args.pro.name == "acme logo LC.DST"
    assert args.garment == "left_chest" and args.width == pytest.approx(25.5, abs=0.6)
    assert pro_pair.parse_args(["--job", "acme_co_lc", "--width", "70"]).width == 70.0
    with pytest.raises(SystemExit):
        pro_pair.parse_args(["--job", "no_art_job_beanie"])     # no art: says so, does not guess
    with pytest.raises(SystemExit):
        pro_pair.parse_args(["--job", "nope"])
    with pytest.raises(SystemExit):
        pro_pair.parse_args(["--art", "a.png"])                 # neither --job nor all three


def test_word_legibility_and_flip_sheet_find_a_registered_job(kent):
    from tools import flip_sheet_renders, word_legibility
    jobs = word_legibility.registered_jobs()
    assert jobs["acme_co_hat"]["pro"].endswith("acme logo hat.PES")      # the PES: thread colours
    assert word_legibility.resolve(jobs["acme_co_hat"]["art"]).name == "Acme Art.png"
    f = flip_sheet_renders.fixture_files("zip_co_hat")
    assert f["pro_dst"].name == "ZIPCO HAT.DST" and f["art"].name == "zipco logo.png"
    assert f["garment"] == "hat_front" and f["width_mm"] > 30


def test_no_registry_hands_out_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("EMB_SCRATCH_KENT", str(tmp_path / "absent"))
    assert pi.registered_pairs() == [] and pi.pair_record("acme_co_hat") is None
