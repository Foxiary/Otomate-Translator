# -*- coding: utf-8 -*-
"""Package a mod folder as release zips for Ryujinx and Atmosphere.

    python tools/release.py --title-id 010068501FF9A000 --romfs mod/romfs [--exefs mod/exefs]
                            [--aoc 010068501FF9B001=dlc1/romfs ...] --name my-patch
                            --out-dir dist --version v1.0 [--build]

`--romfs` is a folder laid out like the game's RomFS holding only the files
the patch replaces. Layouts written:

  Ryujinx     <title id>/<name>/romfs/...      extract into mods/contents/
              <title id>/<name>/exefs/<build id>.ips
  Atmosphere  atmosphere/contents/<TITLE ID>/romfs/...
              atmosphere/exefs_patches/<name>/<build id>.ips
              atmosphere/contents/<TITLE ID>/exefs/...   (non-.ips exefs files)

A DLC is its own title: LayeredFS applies a mod per title id, so the game's
mod cannot reach DLC files. Each `--aoc TITLEID=DIR` becomes another root.

Never packed: `.resS` streams (LayeredFS falls back to the game's own, and a
patched asset keeps its offsets into them), UnityPy `CAB-*` scratch files,
`*.bak*` and `*.tmp`. Without `--build` it only prints the plan.
"""
import argparse
import hashlib
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import utf8_stdout   # noqa: E402

SKIP = re.compile(r"(\.resS$|(^|/)CAB-|\.bak\d*$|\.tmp$)", re.I)
TID = re.compile(r"^[0-9A-Fa-f]{16}$")


def files(root):
    out = []
    for base, _dirs, names in os.walk(root):
        for n in names:
            p = os.path.join(base, n)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if SKIP.search(rel):
                print("  skip %s" % rel)
                continue
            out.append((p, rel))
    return sorted(out, key=lambda x: x[1])


def plan(a):
    entries = {"ryujinx": [], "atmosphere": []}
    roots = [(a.title_id, a.romfs, a.exefs)] + [(t, d, None) for t, d in a.aoc]
    for tid, romfs, exefs in roots:
        for p, rel in files(romfs) if romfs else []:
            entries["ryujinx"].append((p, "%s/%s/romfs/%s" % (tid.lower(), a.name, rel)))
            entries["atmosphere"].append((p, "atmosphere/contents/%s/romfs/%s" % (tid.upper(), rel)))
        for p, rel in files(exefs) if exefs else []:
            entries["ryujinx"].append((p, "%s/%s/exefs/%s" % (tid.lower(), a.name, rel)))
            if rel.lower().endswith(".ips"):
                entries["atmosphere"].append((p, "atmosphere/exefs_patches/%s/%s" % (a.name, rel)))
            else:
                entries["atmosphere"].append((p, "atmosphere/contents/%s/exefs/%s" % (tid.upper(), rel)))
    return entries


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--title-id", required=True, help="the game's base title id (16 hex digits)")
    ap.add_argument("--romfs", required=True, help="mod RomFS folder")
    ap.add_argument("--exefs", help="mod ExeFS folder (.ips patches or replaced files)")
    ap.add_argument("--aoc", action="append", default=[], help="DLC as TITLEID=romfs folder; repeatable")
    ap.add_argument("--name", required=True, help="mod folder name, e.g. vn-translation")
    ap.add_argument("--version", required=True, help="release label used in the zip names")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--build", action="store_true", help="write the zips (default: print the plan)")
    a = ap.parse_args()

    if not TID.match(a.title_id):
        raise SystemExit("--title-id must be 16 hex digits")
    if not re.fullmatch(r"[\w.-]+", a.name):
        raise SystemExit("--name may use letters, digits, '.', '-' and '_' only")
    aoc = []
    for item in a.aoc:
        tid, sep, d = item.partition("=")
        if not sep or not TID.match(tid) or not os.path.isdir(d):
            raise SystemExit("bad --aoc %r, want TITLEID=existing folder" % item)
        aoc.append((tid, d))
    a.aoc = aoc
    for d in [a.romfs] + ([a.exefs] if a.exefs else []):
        if not os.path.isdir(d):
            raise SystemExit("not a folder: %s" % d)

    entries = plan(a)
    total = sum(os.path.getsize(p) for p, _ in entries["ryujinx"])
    print("%d files, %.1f MB" % (len(entries["ryujinx"]), total / 1e6))
    for _p, arc in entries["atmosphere"]:
        print("  %s" % arc)
    if not a.build:
        print("plan only - add --build to write the zips")
        return
    os.makedirs(a.out_dir, exist_ok=True)
    for layout, items in entries.items():
        out = os.path.join(a.out_dir, "%s-%s-%s.zip" % (a.name, a.version, layout))
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p, arc in items:
                z.write(p, arc)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            bad = z.testzip()
        if bad or len(names) != len(items):
            raise SystemExit("%s failed its read-back check" % out)
        print("%s  %.1f MB  sha256 %s" % (out, os.path.getsize(out) / 1e6, sha256(out)))


if __name__ == "__main__":
    main()
