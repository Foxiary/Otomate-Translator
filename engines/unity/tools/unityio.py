# -*- coding: utf-8 -*-
"""Shared UnityPy helpers: load a bundle or .assets file, save it back the way
the game expects, and prove that nothing but the intended objects changed.

Not a command. Every tool in this folder goes through `load()` and `save()`.

Saving rules, all measured on UNLOGICAL (Unity 6000.0, Switch):

  - A bundle (UnityFS) must be saved with `packer="lz4"`. UnityPy's default is
    uncompressed: a 4.1 MB bundle came out at 23.7 MB.
  - A serialized `.assets` / `level*` file has no packer at all.
  - UnityPy re-packs objects at 8-byte alignment where Unity used 16, so a
    re-save is never byte-identical. What must hold is that every object the
    tool did not mean to touch reads back with the same raw bytes;
    `verify_untouched()` checks exactly that after every write.
"""
import fnmatch
import io
import os
import shutil
import sys


def utf8_stdout():
    """The app reads output as UTF-8; Windows consoles default to a code page."""
    if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def load(path, unity_version=None):
    import UnityPy
    if unity_version:
        # Files stripped of their version string (common in .assets without a
        # type tree) need one to parse; 2021.3.0f1 is what UNLOGICAL used.
        UnityPy.config.FALLBACK_UNITY_VERSION = unity_version
    if not os.path.isfile(path):
        raise SystemExit("not a file: %s" % path)
    return UnityPy.load(path)


def is_bundle(env):
    return type(env.file).__name__ == "BundleFile"


def objects(env, type_name=None, name_glob=None):
    """[(obj, data)] filtered by type and by m_Name glob (case-sensitive)."""
    out = []
    for o in env.objects:
        if type_name and o.type.name != type_name:
            continue
        try:
            d = o.read()
        except Exception:
            if name_glob:
                continue
            d = None
        name = getattr(d, "m_Name", "") if d is not None else ""
        if name_glob and not fnmatch.fnmatchcase(name or "", name_glob):
            continue
        out.append((o, d))
    return out


def raw_snapshot(env):
    return {o.path_id: o.get_raw_data() for o in env.objects}


def save(env, out_path, packer="auto"):
    """Write `env` to `out_path`. packer: auto | lz4 | lzma | none | original."""
    if packer == "auto":
        packer = "lz4" if is_bundle(env) else "none"
    if is_bundle(env):
        blob = env.file.save(packer=None if packer == "none" else packer)
    else:
        if packer not in ("none", "original"):
            raise SystemExit("a serialized .assets file takes no packer (got %s)" % packer)
        blob = env.file.save()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, out_path)
    return len(blob)


def verify_untouched(before, out_path, changed, unity_version=None):
    """Reload `out_path`; every object outside `changed` must be byte-identical."""
    chk = load(out_path, unity_version)
    after = {o.path_id: o for o in chk.objects}
    missing = [pid for pid in before if pid not in after]
    if missing:
        raise SystemExit("objects lost on save: %s" % missing[:20])
    bad = [pid for pid, raw in before.items()
           if pid not in changed and after[pid].get_raw_data() != raw]
    if bad:
        raise SystemExit("save changed %d objects it should not have: %s" % (len(bad), bad[:20]))
    return chk


def backup(path):
    """Copy `path` to `path.bak`, `path.bak2`, ... - never overwrite an older one."""
    dest, i = path + ".bak", 2
    while os.path.exists(dest):
        dest, i = "%s.bak%d" % (path, i), i + 1
    shutil.copy2(path, dest)
    return dest


def text_of(data):
    """TextAsset content as str, whatever UnityPy handed back."""
    raw = data.m_Script
    if isinstance(raw, str):
        return raw
    return bytes(raw).decode("utf-8", "surrogateescape")


def add_common(ap):
    ap.add_argument("--unity-version", default=None,
                    help="fallback Unity version for files that do not carry one, "
                         "e.g. 2021.3.0f1")
