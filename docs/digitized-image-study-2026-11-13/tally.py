"""Tally the digitized-image study: counts, dupes, kinds, stitch types, rules dump."""
import collections
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
notes = sorted((root / "notes").glob("*.json"))
rows, bad = [], []
for n in notes:
    try:
        data = json.loads(n.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        bad.append(f"{n.name}: {e}")
        continue
    for r in data:
        r["_set"] = n.stem
        rows.append(r)

print("note files:", [n.name for n in notes], "unparseable:", bad)
print("entries:", len(rows), dict(collections.Counter(r["_set"] for r in rows)))

hashes, missing, small = collections.defaultdict(list), [], []
try:
    from PIL import Image
except Exception:  # noqa: BLE001
    Image = None
for r in rows:
    p = root / "images" / r.get("file", "")
    if not p.is_file():
        missing.append(r.get("id"))
        continue
    hashes[hashlib.md5(p.read_bytes()).hexdigest()].append(r["id"])
    if Image:
        try:
            with Image.open(p) as im:
                if max(im.size) < 500:
                    small.append((r["id"], im.size))
        except Exception as e:  # noqa: BLE001
            missing.append(f"{r['id']} unreadable {e}")
print("missing/unreadable:", missing)
print("byte-identical dupes:", [v for v in hashes.values() if len(v) > 1])
print("under 500 px:", small)
urls = collections.Counter(r.get("image_url") for r in rows if r.get("image_url"))
print("same image_url twice:", [u for u, c in urls.items() if c > 1])
print("kinds:", dict(collections.Counter((r.get("kind") or "?").split("|")[0].strip() for r in rows)))

stitch = collections.Counter()
edge = collections.Counter()
for r in rows:
    for s in r.get("shapes") or []:
        stitch[(s.get("stitch") or "?").lower()[:40]] += 1
        edge[(s.get("edge") or "?").lower()[:40]] += 1
print("\nshape stitch types (top 25):")
for k, v in stitch.most_common(25):
    print(f"  {v:4d}  {k}")
print("\nedges (top 20):")
for k, v in edge.most_common(20):
    print(f"  {v:4d}  {k}")

if len(sys.argv) > 2:
    out = pathlib.Path(sys.argv[2])
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(f"## {r['id']} [{r.get('kind')}] {r.get('subject')}\n")
            if r.get("vs_artwork"):
                f.write(f"VS ART: {r['vs_artwork']}\n")
            for t in r.get("techniques") or []:
                f.write(f"T: {t}\n")
            for t in r.get("rules") or []:
                f.write(f"R: {t}\n")
            f.write("\n")
    print("rules dump:", out, out.stat().st_size, "bytes")
