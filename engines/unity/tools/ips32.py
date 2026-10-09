# -*- coding: utf-8 -*-
"""Build an IPS32 code patch for an NSO, checked against the decompressed image.

    python tools/ips32.py <main> <out dir> --patch RVA:OLD:NEW [--patch ...] [--flat main.flat]

    --patch 0x1998AC0:40028052:00058052      (hex bytes, same length both sides)

The patch is named `<build id>.ips` and goes in the mod's `exefs/` folder, next
to `romfs/`. Ryujinx and Atmosphere both pick it up by that name, so it binds
to exactly one build of the game.

Conventions that are easy to get wrong:
  - IPS32, not IPS: plain IPS has 3-byte offsets (16 MB) and cannot reach most
    of `.text`. IPS32 is magic `IPS32`, 4-byte big-endian offset, `EEOF` end.
  - File offset = RVA + 0x100: the loader applies the patch to the
    decompressed NSO including its 0x100-byte header. Do not take the
    `Offset:` column from Il2CppDumper's dump.cs, which is RVA + 0x10D
    (relative to the compressed file).
  - Every patch's OLD bytes are compared with the flat image first. A mismatch
    means the wrong build or the wrong offset convention, and nothing is written.

`main.flat` comes from `switchfs.py exefs` (or `switchfs.py nso`).
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import utf8_stdout   # noqa: E402

NSO_HEADER = 0x100


def parse_patch(text):
    try:
        rva, old, new = text.split(":")
        rva = int(rva, 0)
        old, new = bytes.fromhex(old), bytes.fromhex(new)
    except ValueError:
        raise SystemExit("bad --patch %r, want RVA:OLDHEX:NEWHEX" % text)
    if len(old) != len(new) or not old:
        raise SystemExit("--patch %r: OLD and NEW must be the same, non-zero length" % text)
    return rva, old, new


def build_id(nso):
    d = open(nso, "rb").read(0x60)
    if d[:4] != b"NSO0":
        raise SystemExit("%s is not an NSO" % nso)
    return d[0x40:0x60].hex().upper().rstrip("0")


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("nso", help="the game's `main` NSO (for the build id)")
    ap.add_argument("out", help="output folder, e.g. <mod>/exefs")
    ap.add_argument("--patch", action="append", required=True, help="RVA:OLDHEX:NEWHEX")
    ap.add_argument("--flat", help="decompressed image to check OLD bytes against "
                                   "(default: main.flat beside the NSO)")
    ap.add_argument("--apply", action="store_true", help="write the .ips (default: dry run)")
    a = ap.parse_args()

    bid = build_id(a.nso)
    flat = a.flat or os.path.join(os.path.dirname(os.path.abspath(a.nso)), "main.flat")
    if not os.path.exists(flat):
        raise SystemExit("no flat image at %s - run switchfs.py nso first, or pass --flat" % flat)
    print("build id %s, checking against %s" % (bid, flat))
    blob = bytearray(b"IPS32")
    with open(flat, "rb") as f:
        for text in a.patch:
            rva, old, new = parse_patch(text)
            f.seek(rva)
            cur = f.read(len(old))
            if cur != old:
                raise SystemExit("RVA 0x%X holds %s, expected %s - wrong build or offset?"
                                 % (rva, cur.hex().upper(), old.hex().upper()))
            blob += struct.pack(">IH", rva + NSO_HEADER, len(new)) + new
            print("  RVA 0x%08X -> offset 0x%08X  %s -> %s"
                  % (rva, rva + NSO_HEADER, old.hex().upper(), new.hex().upper()))
    blob += b"EEOF"
    dest = os.path.join(a.out, bid + ".ips")
    if not a.apply:
        print("\nIPS32 %d bytes, %d patches. Dry run - add --apply to write %s"
              % (len(blob), len(a.patch), dest))
        return
    os.makedirs(a.out, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(blob)
    print("\nwrote %s (%d bytes). Remove that file to undo the patch." % (dest, len(blob)))


if __name__ == "__main__":
    main()
