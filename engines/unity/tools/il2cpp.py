# -*- coding: utf-8 -*-
"""Find and replace string literals in an IL2CPP `global-metadata.dat`.

    python tools/il2cpp.py find  <global-metadata.dat> <text> [--contains]
    python tools/il2cpp.py patch <global-metadata.dat> <old> <new> --out <file> [--apply]

Some interface text is not in any asset: it is a string constant in the game's
C# code (a default protagonist name, an alert, a button label). In an IL2CPP
build those constants live in the string-literal table of
`Data/Managed/Metadata/global-metadata.dat`, and grepping the assets finds
nothing.

Layout (checked on metadata v24-v31): the header's (offset, size) pairs at 0x08
and 0x10 locate the literal table and the literal data. Each table entry is
`{uint32 length; uint32 dataIndex}` and the data is packed with no padding.

So a patch is made in place and the new text must be no longer than the old
one in UTF-8 bytes: it overwrites the old bytes, pads with NUL, and lowers the
entry's `length`. File size and every other offset stay as they are. Growing a
literal means relocating the data block and rewriting the header, which this
tool refuses rather than attempts.

`patch` requires exactly one literal equal to <old>. After writing it reads the
file back and checks that only that literal's bytes and its length changed.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import backup, utf8_stdout   # noqa: E402

SANITY = 0xFAB11BAF


def header(blob):
    sanity, version = struct.unpack_from("<Ii", blob, 0)
    if sanity != SANITY:
        raise SystemExit("not a global-metadata.dat (sanity %08X)" % sanity)
    lit_off, lit_size, data_off, data_size = struct.unpack_from("<IIII", blob, 8)
    return version, lit_off, lit_size, data_off, data_size


def literals(blob):
    """[(index, length, dataIndex)] in data order."""
    _, lit_off, lit_size, _, _ = header(blob)
    out = [(i,) + struct.unpack_from("<II", blob, lit_off + i * 8) for i in range(lit_size // 8)]
    return sorted(out, key=lambda e: e[2])


def text_at(blob, data_off, di, length):
    return bytes(blob[data_off + di:data_off + di + length]).decode("utf-8", "replace")


def cmd_find(a):
    blob = open(a.file, "rb").read()
    version, _, lit_size, data_off, _ = header(blob)
    print("metadata v%d, %d literals" % (version, lit_size // 8))
    n = 0
    for i, length, di in literals(blob):
        s = text_at(blob, data_off, di, length)
        if (a.text in s) if a.contains else (s == a.text):
            n += 1
            print("  literal %6d  %4d bytes  %r" % (i, length, s))
    print("%d found" % n)


def cmd_patch(a):
    blob = bytearray(open(a.file, "rb").read())
    version, lit_off, lit_size, data_off, data_size = header(blob)
    want = a.old.encode("utf-8")
    ents = literals(blob)
    hits = [(i, length, di) for i, length, di in ents
            if bytes(blob[data_off + di:data_off + di + length]) == want]
    if not hits:
        raise SystemExit("no literal equals %r (try `find --contains`)" % a.old)
    if len(hits) > 1:
        raise SystemExit("%r matches %d literals - not guessing which" % (a.old, len(hits)))
    idx, length, di = hits[0]
    new = a.new.encode("utf-8")
    print("metadata v%d: literal %d at data index %d, %d bytes" % (version, idx, di, length))
    print("   old %3d bytes  %r" % (length, a.old))
    print("   new %3d bytes  %r" % (len(new), a.new))
    if len(new) > length:
        raise SystemExit("%d bytes longer than the original - in-place patching cannot grow a "
                         "literal; shorten the text" % (len(new) - length))
    at = data_off + di
    blob[at:at + length] = new + b"\x00" * (length - len(new))
    struct.pack_into("<I", blob, lit_off + idx * 8, len(new))
    if not a.apply:
        print("dry run - add --apply to write %s" % a.out)
        return
    if os.path.abspath(a.out) == os.path.abspath(a.file):
        print("backup -> %s" % backup(a.file))
    orig = open(a.file, "rb").read()
    with open(a.out, "wb") as f:
        f.write(blob)
    back = open(a.out, "rb").read()
    if header(back) != (version, lit_off, lit_size, data_off, data_size) or len(back) != len(orig):
        raise SystemExit("header or size changed - restore the backup")
    diff = [i for i in range(len(orig)) if orig[i] != back[i]]
    entry = range(lit_off + idx * 8, lit_off + idx * 8 + 4)
    if any(not (at <= i < at + length or i in entry) for i in diff):
        raise SystemExit("bytes outside the literal changed - restore the backup")
    L, D = struct.unpack_from("<II", back, lit_off + idx * 8)
    if (L, D, text_at(back, data_off, D, L)) != (len(new), di, a.new):
        raise SystemExit("read-back does not match")
    print("wrote %s; %d bytes changed, all inside the literal and its length" % (a.out, len(diff)))


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find")
    p.add_argument("file")
    p.add_argument("text")
    p.add_argument("--contains", action="store_true", help="substring match instead of equality")
    p = sub.add_parser("patch")
    p.add_argument("file")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--out", required=True, help="output file (may be the input itself)")
    p.add_argument("--apply", action="store_true", help="write (default: dry run)")
    a = ap.parse_args()
    (cmd_find if a.cmd == "find" else cmd_patch)(a)


if __name__ == "__main__":
    main()
