# -*- coding: utf-8 -*-
"""Read a Switch NSP without hactool: ExeFS, RomFS, and NSO decompression.

    python tools/switchfs.py exefs <game.nsp> <out dir> [--keys prod.keys]
    python tools/switchfs.py romfs <game.nsp> <out dir> [--keys prod.keys] [--list]
    python tools/switchfs.py nso   <main> <main.flat>

Pure Python on pycryptodome + lz4:

    NSP (PFS0) -+- *.tik  -> encrypted title key, opened with titlekek_XX
                +- *.nca  -> header AES-XTS(header_key), sections AES-CTR(title key)
    ExeFS = PFS0 section holding `main`; RomFS = IVFC section, last level = data
    main (NSO0) -> three LZ4-block segments laid out at their memory offsets

Keys come from `prod.keys` (Ryujinx keeps it in `system/`). Only the regions
needed are decrypted, never the whole NCA.

Two traps, both of which produce plausible garbage rather than an error:
  - The XTS tweak is the sector number BIG-endian (Nintendo's variant).
  - The CTR counter counts from the offset inside the NCA, while the read
    position is the offset inside the NSP file.

Update NCAs (BKTR patch RomFS) are not supported: `romfs` on an update NSP
lists its sections and skips them. Extract the base game instead.

`exefs` also writes `main.flat`, the decompressed image `ips32.py` checks
patches against.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import utf8_stdout   # noqa: E402

CONTENT = {0: "Program", 1: "Meta", 2: "Control", 3: "Manual", 4: "Data", 5: "PublicData"}


def default_keys():
    for base in (os.environ.get("APPDATA", ""), os.path.expanduser("~/.config")):
        p = os.path.join(base, "Ryujinx", "system", "prod.keys")
        if base and os.path.exists(p):
            return p
    p = os.path.expanduser("~/.switch/prod.keys")
    return p if os.path.exists(p) else None


def load_keys(path):
    if not path or not os.path.exists(path):
        raise SystemExit("prod.keys not found - pass --keys <path to prod.keys>")
    keys = {}
    for line in open(path, encoding="utf-8"):
        k, sep, v = line.partition("=")
        if not sep:
            continue
        try:
            keys[k.strip().lower()] = bytes.fromhex(v.strip())
        except ValueError:
            pass
    if "header_key" not in keys:
        raise SystemExit("%s has no header_key" % path)
    return keys


def _mul_alpha(t):
    carry = 0
    for i in range(16):
        b = t[i]
        t[i] = ((b << 1) & 0xFF) | carry
        carry = b >> 7
    if carry:
        t[0] ^= 0x87


def xts_decrypt(key, data, sector_size=0x200, sector=0):
    from Crypto.Cipher import AES
    crypt = AES.new(key[:16], AES.MODE_ECB)
    tweaker = AES.new(key[16:], AES.MODE_ECB)
    out = bytearray()
    for s in range(len(data) // sector_size):
        tweak = bytearray(tweaker.encrypt((sector + s).to_bytes(16, "big")))
        chunk = data[s * sector_size:(s + 1) * sector_size]
        for b in range(0, sector_size, 16):
            blk = bytes(x ^ y for x, y in zip(chunk[b:b + 16], tweak))
            dec = crypt.decrypt(blk)
            out += bytes(x ^ y for x, y in zip(dec, tweak))
            _mul_alpha(tweak)
    return bytes(out)


def ctr_read(f, file_base, nca_base, ctr8, offset, size, key):
    """`size` bytes at `offset` (relative to the section) of an AES-CTR section."""
    from Crypto.Cipher import AES
    aligned = offset & ~0xF
    pad = offset - aligned
    total = (pad + size + 0xF) & ~0xF
    counter = bytearray(16)
    counter[0:8] = ctr8[::-1]
    counter[8:16] = ((nca_base + aligned) >> 4).to_bytes(8, "big")
    f.seek(file_base + aligned)
    raw = f.read(total)
    cipher = AES.new(key, AES.MODE_CTR, nonce=b"", initial_value=bytes(counter))
    return cipher.decrypt(raw)[pad:pad + size]


def parse_pfs0(blob):
    magic, n, str_size, _ = struct.unpack_from("<4sIII", blob, 0)
    if magic != b"PFS0":
        raise SystemExit("not a PFS0 container (%r)" % magic)
    strtab = blob[16 + n * 24:16 + n * 24 + str_size]
    data_off = 16 + n * 24 + str_size
    out = []
    for i in range(n):
        off, size, name_off, _ = struct.unpack_from("<QQII", blob, 16 + i * 24)
        name = strtab[name_off:strtab.index(b"\0", name_off)].decode()
        out.append((name, data_off + off, size))
    return out


def ticket_titlekey(tik, keys):
    sig_type = struct.unpack_from("<I", tik, 0)[0]
    head = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0xC0,
            0x10003: 0x240, 0x10004: 0x140, 0x10005: 0xC0}[sig_type]
    enc_key = tik[head + 0x40:head + 0x50]
    rights_id = tik[head + 0x160:head + 0x170]
    rev = rights_id[15]
    idx = rev - 1 if rev > 0 else 0
    kek = keys.get("titlekek_%02x" % idx)
    if kek is None:
        raise SystemExit("prod.keys lacks titlekek_%02x" % idx)
    from Crypto.Cipher import AES
    return rights_id, rev, AES.new(kek, AES.MODE_ECB).decrypt(enc_key)


class NSP:
    def __init__(self, path, keys):
        if not os.path.isfile(path):
            raise SystemExit("not a file: %s" % path)
        self.f = open(path, "rb")
        head = self.f.read(0x10)
        n, st = struct.unpack_from("<II", head, 4)
        self.f.seek(0)
        self.entries = parse_pfs0(self.f.read(0x10 + n * 24 + st))
        self.keys = keys
        self.title_key = None
        tik = next((e for e in self.entries if e[0].endswith(".tik")), None)
        if tik:
            self.f.seek(tik[1])
            rights_id, rev, self.title_key = ticket_titlekey(self.f.read(tik[2]), keys)
            print("rights id %s, master key rev %d" % (rights_id.hex(), rev))

    def ncas(self):
        """Yield (name, offset, size, decrypted header) for every NCA."""
        for name, off, size in sorted(self.entries, key=lambda e: -e[2]):
            if not name.endswith(".nca"):
                continue
            self.f.seek(off)
            hdr = xts_decrypt(self.keys["header_key"], self.f.read(0xC00))
            if hdr[0x200:0x204] not in (b"NCA3", b"NCA2"):
                print("%s: header does not decrypt (%r) - wrong keys?" % (name, hdr[0x200:0x204]))
                continue
            yield name, off, size, hdr

    def sections(self, off, hdr):
        """Yield (index, fs header, nca_base, file_base, key or None)."""
        for i in range(4):
            start, end = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
            if start == end == 0:
                continue
            fsh = hdr[0x400 + i * 0x200:0x400 + (i + 1) * 0x200]
            enc = fsh[0x04]
            key = None if enc == 1 else self.title_key if enc == 3 else False
            yield i, fsh, start * 0x200, off + start * 0x200, key

    def reader(self, file_base, nca_base, ctr8, key, base):
        def read(o, s):
            if key is None:
                self.f.seek(file_base + base + o)
                return self.f.read(s)
            return ctr_read(self.f, file_base, nca_base, ctr8, base + o, s, key)
        return read


def cmd_exefs(a):
    nsp = NSP(a.nsp, load_keys(a.keys))
    os.makedirs(a.out, exist_ok=True)
    for name, off, size, hdr in nsp.ncas():
        print("\n%s  %.1f MB  %s" % (name, size / 1e6, CONTENT.get(hdr[0x205], hdr[0x205])))
        if hdr[0x205] != 0:
            continue
        for i, fsh, nca_base, file_base, key in nsp.sections(off, hdr):
            if fsh[0x02] != 1 or not key:
                continue
            layers = struct.unpack_from("<I", fsh, 0x08 + 0x24)[0]
            l_off, _ = struct.unpack_from("<QQ", fsh, 0x08 + 0x28 + (layers - 1) * 0x10)
            read = nsp.reader(file_base, nca_base, fsh[0x140:0x148], key, l_off)
            head = read(0, 0x1000)
            if head[:4] != b"PFS0":
                continue
            cnt, st = struct.unpack_from("<II", head, 4)
            items = parse_pfs0(read(0, (0x10 + cnt * 24 + st + 0xFFF) & ~0xFFF))
            print("   section %d: PFS0 %s" % (i, ", ".join(x[0] for x in items)))
            if not any(x[0] == "main" for x in items):
                continue
            for nm, foff, fsize in items:
                with open(os.path.join(a.out, nm), "wb") as w:
                    w.write(read(foff, fsize))
                print("      -> %-14s %10d B" % (nm, fsize))
            decompress_nso(os.path.join(a.out, "main"), os.path.join(a.out, "main.flat"))
            return
    raise SystemExit("no ExeFS found - is this the base game or update NSP?")


def romfs_walk(read, out_root, list_only):
    hdr = read(0, 0x50)
    vals = struct.unpack_from("<10Q", hdr, 0)
    if vals[0] != 0x50:
        raise ValueError("not a RomFS (header size %d)" % vals[0])
    _, _, _, dm_off, dm_size, _, _, fm_off, fm_size, data_off = vals
    dirs, files = read(dm_off, dm_size), read(fm_off, fm_size)
    out = []

    def walk(doff, path):
        _p, _s, child, first, _h, nlen = struct.unpack_from("<6I", dirs, doff)
        here = path + ("/" + dirs[doff + 0x18:doff + 0x18 + nlen].decode("utf-8", "replace") if nlen else "")
        foff = first
        while foff != 0xFFFFFFFF:
            _fp, sib, d_off, d_size, _fh, fnlen = struct.unpack_from("<IIQQII", files, foff)
            rel = (here + "/" + files[foff + 0x20:foff + 0x20 + fnlen].decode("utf-8", "replace")).lstrip("/")
            out.append((rel, d_size))
            if not list_only:
                p = os.path.join(out_root, *rel.split("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as w:
                    pos = 0
                    while pos < d_size:
                        n = min(1 << 22, d_size - pos)
                        w.write(read(data_off + d_off + pos, n))
                        pos += n
            foff = sib
        c = child
        while c != 0xFFFFFFFF:
            walk(c, here)
            c = struct.unpack_from("<I", dirs, c + 4)[0]

    walk(0, "")
    return out


def cmd_romfs(a):
    nsp = NSP(a.nsp, load_keys(a.keys))
    found = 0
    for name, off, size, hdr in nsp.ncas():
        title_id = struct.unpack_from("<Q", hdr, 0x210)[0]
        print("\n%s  %.2f MB  %s  title %016X" % (name, size / 1e6, CONTENT.get(hdr[0x205], hdr[0x205]), title_id))
        for i, fsh, nca_base, file_base, key in nsp.sections(off, hdr):
            if fsh[0x02] != 0:
                continue
            if key is False:
                print("   section %d: encryption type %d not supported (update/BKTR?)" % (i, fsh[0x04]))
                continue
            levels = [struct.unpack_from("<QQ", fsh, 0x18 + k * 0x18) for k in range(6)]
            data_lvl = [lv for lv in levels if lv[1] > 0][-1]
            read = nsp.reader(file_base, nca_base, fsh[0x140:0x148], key, data_lvl[0])
            try:
                dest = os.path.join(a.out, "%016X" % title_id, "romfs")
                listing = romfs_walk(read, dest, a.list)
            except ValueError as e:
                print("   section %d: %s" % (i, e))
                continue
            found += 1
            print("   section %d: RomFS, %d files, %.2f MB%s" % (
                i, len(listing), sum(s for _, s in listing) / 1e6,
                "" if a.list else " -> " + dest))
            for rel, s in listing[:a.show]:
                print("      %12d  %s" % (s, rel))
            if len(listing) > a.show:
                print("      ... %d more" % (len(listing) - a.show))
    if not found:
        raise SystemExit("no readable RomFS in this NSP")


def decompress_nso(path, out_path):
    import lz4.block
    d = open(path, "rb").read()
    if d[:4] != b"NSO0":
        raise SystemExit("%s is not an NSO (%r)" % (path, d[:4]))
    flags = struct.unpack_from("<I", d, 0x0C)[0]
    segs = []
    for i in range(3):
        f_off, m_off, size = struct.unpack_from("<III", d, 0x10 + i * 0x10)
        comp = struct.unpack_from("<I", d, 0x60 + i * 4)[0]
        raw = d[f_off:f_off + comp]
        if flags & (1 << i):
            raw = lz4.block.decompress(raw, uncompressed_size=size)
        if len(raw) != size:
            raise SystemExit("segment %d decompressed to %d bytes, expected %d" % (i, len(raw), size))
        segs.append((m_off, raw))
    img = bytearray(max(m + len(r) for m, r in segs))
    for m, r in segs:
        img[m:m + len(r)] = r
    with open(out_path, "wb") as w:
        w.write(img)
    print("\nNSO build id : %s" % d[0x40:0x60].hex().upper().rstrip("0"))
    print("flat image   : %s (%d B)" % (out_path, len(img)))


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("exefs", "romfs"):
        p = sub.add_parser(name)
        p.add_argument("nsp")
        p.add_argument("out")
        p.add_argument("--keys", default=default_keys(), help="prod.keys (default: Ryujinx's)")
        if name == "romfs":
            p.add_argument("--list", action="store_true", help="only list the files")
            p.add_argument("--show", type=int, default=40, help="how many file names to print")
    p = sub.add_parser("nso")
    p.add_argument("nso")
    p.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "exefs":
        cmd_exefs(a)
    elif a.cmd == "romfs":
        cmd_romfs(a)
    else:
        decompress_nso(a.nso, a.out)


if __name__ == "__main__":
    main()
