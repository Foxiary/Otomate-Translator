# -*- coding: utf-8 -*-
"""Dump, re-import and edit TextAssets in a Unity bundle or .assets file.

    python tools/textasset.py dump    <file> <out dir> [--name GLOB]
    python tools/textasset.py import  <file> <dir> --out <file> [--apply]
    python tools/textasset.py replace <file> <asset> <old> <new> --out <file> [--count N] [--apply]

`dump` writes each TextAsset to `<out dir>/<name>.txt` exactly as stored (BOM
and line endings included); a name used twice gets its path id appended.

`import` takes those files back: every `<name>.txt` that differs from the
asset replaces it. A file that was valid JSON must still be valid JSON.

`replace` swaps one string inside one asset, for a term fix across a table.
It edits the raw text, so nothing else in the file can move, and when the
asset is JSON it re-parses both versions and refuses any change that is not
that exact substitution inside a string value. `--count` makes it refuse
unless the string occurs exactly that many times.

All writes are dry runs until `--apply`, go to `--out` (which may be the input
file itself; a `.bak` copy is kept then), use the right packer for the file
type, and are verified: every other object must read back byte-identical.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import (add_common, backup, load, objects, raw_snapshot, save,   # noqa: E402
                     text_of, utf8_stdout, verify_untouched)

BOM = "﻿"


def as_json(text):
    try:
        return json.loads(text.lstrip(BOM))
    except ValueError:
        return None


def leaves(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, "%s/%s" % (path, k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, "%s[%d]" % (path, i))
    else:
        yield path, x


def file_names(rows):
    names, seen = {}, {}
    for o, d in rows:
        seen[d.m_Name] = seen.get(d.m_Name, 0) + 1
    for o, d in rows:
        base = d.m_Name if seen[d.m_Name] == 1 else "%s.%d" % (d.m_Name, o.path_id)
        names[o.path_id] = base + ".txt"
    return names


def write(env, a, changed):
    if not a.apply:
        print("\ndry run - add --apply to write %s" % a.out)
        return
    if os.path.abspath(a.out) == os.path.abspath(a.file):
        print("backup -> %s" % backup(a.file))
    size = save(env, a.out, a.packer)
    verify_untouched(a.before, a.out, changed, a.unity_version)
    print("wrote %s (%d bytes); %d objects changed, all others byte-identical"
          % (a.out, size, len(changed)))


def cmd_dump(a):
    env = load(a.file, a.unity_version)
    rows = objects(env, "TextAsset", a.name)
    names = file_names(rows)
    os.makedirs(a.out_dir, exist_ok=True)
    for o, d in rows:
        data = text_of(d).encode("utf-8", "surrogateescape")
        with open(os.path.join(a.out_dir, names[o.path_id]), "wb") as f:
            f.write(data)
        kind = "json" if as_json(text_of(d)) is not None else "text"
        print("  %-40s %10d bytes  %s" % (names[o.path_id], len(data), kind))
    print("%d TextAssets -> %s" % (len(rows), a.out_dir))


def cmd_import(a):
    env = load(a.file, a.unity_version)
    a.before = raw_snapshot(env)
    rows = objects(env, "TextAsset")
    names = file_names(rows)
    changed = set()
    for o, d in rows:
        p = os.path.join(a.dir, names[o.path_id])
        if not os.path.exists(p):
            continue
        new = open(p, "rb").read().decode("utf-8", "surrogateescape")
        old = text_of(d)
        if new == old:
            continue
        if as_json(old) is not None and as_json(new) is None:
            raise SystemExit("%s was JSON and no longer parses - fix it first" % names[o.path_id])
        d.m_Script = new
        d.save()
        changed.add(o.path_id)
        print("  %-40s %d -> %d bytes" % (names[o.path_id], len(old.encode("utf-8", "surrogateescape")),
                                         len(new.encode("utf-8", "surrogateescape"))))
    if not changed:
        print("nothing differs from the file - nothing to write")
        return
    write(env, a, changed)


def cmd_replace(a):
    env = load(a.file, a.unity_version)
    a.before = raw_snapshot(env)
    rows = objects(env, "TextAsset", a.asset)
    if len(rows) != 1:
        raise SystemExit("%d TextAssets match %r - name exactly one" % (len(rows), a.asset))
    o, d = rows[0]
    raw = text_of(d)
    n = raw.count(a.old)
    print("%s: %r occurs %d times" % (d.m_Name, a.old, n))
    if n == 0:
        raise SystemExit("nothing to replace")
    if a.count is not None and n != a.count:
        raise SystemExit("expected exactly %d occurrences" % a.count)
    out = raw.replace(a.old, a.new)
    before, after = as_json(raw), as_json(out)
    if before is not None:
        if after is None:
            raise SystemExit("the replacement breaks the JSON")
        b, c = dict(leaves(before)), dict(leaves(after))
        if b.keys() != c.keys():
            raise SystemExit("the replacement changes the JSON structure (a key or bracket)")
        diffs = [(k, b[k], c[k]) for k in b if b[k] != c[k]]
        for k, x, y in diffs:
            if not (isinstance(x, str) and x.replace(a.old, a.new) == y):
                raise SystemExit("unexpected change at %s" % k)
            print("  %s\n      %r\n   -> %r" % (k, x, y))
        print("%d JSON values changed" % len(diffs))
    d.m_Script = out
    d.save()
    write(env, a, {o.path_id})


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("dump")
    p.add_argument("file")
    p.add_argument("out_dir")
    p.add_argument("--name", help="only TextAssets whose name matches this glob")
    add_common(p)
    for name in ("import", "replace"):
        p = sub.add_parser(name)
        p.add_argument("file")
        if name == "import":
            p.add_argument("dir", help="folder written by `dump`")
        else:
            p.add_argument("asset", help="TextAsset name")
            p.add_argument("old")
            p.add_argument("new")
            p.add_argument("--count", type=int, help="required number of occurrences")
        p.add_argument("--out", required=True, help="output file (may be the input itself)")
        p.add_argument("--packer", default="auto", choices=["auto", "lz4", "lzma", "none", "original"])
        p.add_argument("--apply", action="store_true", help="write (default: dry run)")
        add_common(p)
    a = ap.parse_args()
    {"dump": cmd_dump, "import": cmd_import, "replace": cmd_replace}[a.cmd](a)


if __name__ == "__main__":
    main()
