# -*- coding: utf-8 -*-
"""Find and adjust TextMeshPro text boxes: size, auto-size, wrapping, spacing.

    python tools/tmp.py list <file> [--text REGEX] [--object GLOB] [--nodes-from BUNDLE]
    python tools/tmp.py set  <file> <path id> [--width W] [--height H] [--font-size S]
                             [--x X] [--y Y] [--auto-size on|off] [--size-min S] [--size-max S]
                             [--wrap on|off] [--overflow MODE] [--char-spacing N]
                             [--line-spacing N] [--margin L,T,R,B] --out <file> [--apply]

A translation that runs longer than the original either overflows its box or
is clipped by a mask. The usual fixes are a wider box, letting TextMeshPro wrap,
or auto-sizing between a minimum and the original size. `list` prints every
TextMeshPro component with its box and settings (search by the text it shows,
`--text`, or by GameObject name, `--object`); `set` changes one of them by the
path id `list` printed.

Things that do not behave the way their names suggest (Unity 6, TMP 3.2):
  - Wrapping is `m_TextWrappingMode` (0 off, 1 normal) in recent TMP and the
    bool `m_enableWordWrapping` in older ones; `--wrap` writes whichever the
    component has.
  - A size range does nothing unless `m_enableAutoSizing` is on, and
    `m_fontSizeMax` should stay at the original size, or short lines grow.
  - The box size lives on the GameObject's RectTransform (`m_SizeDelta`), not on
    the text component; `--width`/`--height` write it there.
  - Some games wrap text in code before TMP sees it. If wrapping changes
    nothing on screen, look for a fixed line length in the game's code.

`.assets` and `level*` files usually carry no type tree for MonoBehaviours, so
the fields cannot be named. `--nodes-from` borrows the TextMeshPro type tree
from a bundle of the same game that does have one (any UI bundle).
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import (add_common, backup, load, raw_snapshot, save,   # noqa: E402
                     utf8_stdout, verify_untouched)

WRAP_KEYS = ("m_TextWrappingMode", "m_enableWordWrapping")


def borrowed_nodes(path, unity_version):
    for o in load(path, unity_version).objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:
            continue
        if isinstance(t, dict) and "m_text" in t and "m_fontSize" in t:
            return o.serialized_type.node
    raise SystemExit("no TextMeshPro type tree found in %s" % path)


def read_tmp(o, nodes):
    try:
        t = o.read_typetree(nodes) if nodes is not None else o.read_typetree()
    except Exception:
        return None
    if isinstance(t, dict) and "m_text" in t and "m_fontSize" in t:
        return t
    return None


def rect_of(env, objs, t):
    """(RectTransform object, GameObject name) of a TMP component."""
    go_id = t["m_GameObject"]["m_PathID"]
    go = objs.get(go_id)
    if go is None:
        return None, "?"
    g = go.read()
    for c in getattr(g, "m_Components", None) or getattr(g, "m_Component", []):
        ptr = c.component if hasattr(c, "component") else c
        if getattr(ptr, "m_FileID", 0) == 0 and ptr.m_PathID in objs \
                and objs[ptr.m_PathID].type.name == "RectTransform":
            return objs[ptr.m_PathID], g.m_Name
    return None, g.m_Name


def wrap_state(t):
    for k in WRAP_KEYS:
        if k in t:
            return "%s=%s" % ("wrap" if k == WRAP_KEYS[0] else "wordwrap", t[k])
    return "wrap=?"


def describe(t, rt):
    size = ("%gx%g @%g,%g" % (rt["m_SizeDelta"]["x"], rt["m_SizeDelta"]["y"],
                              rt["m_AnchoredPosition"]["x"], rt["m_AnchoredPosition"]["y"])) if rt else "?"
    auto = ("auto %g..%g" % (t["m_fontSizeMin"], t["m_fontSizeMax"])) if t.get("m_enableAutoSizing") else "fixed"
    m = t.get("m_margin", {})
    return ("box %s  size %g (%s)  %s  overflow=%s  charSp %g  lineSp %g  margin %g,%g,%g,%g"
            % (size, t["m_fontSize"], auto, wrap_state(t), t.get("m_overflowMode"),
               t.get("m_characterSpacing", 0), t.get("m_lineSpacing", 0),
               m.get("x", 0), m.get("y", 0), m.get("z", 0), m.get("w", 0)))


def cmd_list(a):
    env = load(a.file, a.unity_version)
    nodes = borrowed_nodes(a.nodes_from, a.unity_version) if a.nodes_from else None
    objs = {o.path_id: o for o in env.objects}
    text_rx = re.compile(a.text) if a.text else None
    import fnmatch
    n = 0
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        t = read_tmp(o, nodes)
        if t is None:
            continue
        if text_rx and not text_rx.search(t["m_text"] or ""):
            continue
        rect, go_name = rect_of(env, objs, t)
        if a.object and not fnmatch.fnmatchcase(go_name, a.object):
            continue
        rt = rect.read_typetree() if rect else None
        n += 1
        print("%20d  %s" % (o.path_id, go_name))
        print("      %s" % describe(t, rt))
        print("      text: %r" % (t["m_text"] or "")[:100])
    if n == 0 and nodes is None:
        print("no TextMeshPro component found. If this is an .assets / level file, "
              "pass --nodes-from <a UI bundle of the same game>")
    print("%d components" % n)


def on_off(v):
    if v not in ("on", "off"):
        raise argparse.ArgumentTypeError("on or off")
    return v == "on"


def cmd_set(a):
    env = load(a.file, a.unity_version)
    before = raw_snapshot(env)
    nodes = borrowed_nodes(a.nodes_from, a.unity_version) if a.nodes_from else None
    objs = {o.path_id: o for o in env.objects}
    o = objs.get(a.pid)
    if o is None:
        raise SystemExit("no object with path id %d" % a.pid)
    t = read_tmp(o, nodes)
    if t is None:
        raise SystemExit("%d is not a TextMeshPro component (or needs --nodes-from)" % a.pid)
    rect, go_name = rect_of(env, objs, t)
    rt = rect.read_typetree() if rect else None
    print("%d %s\n   before: %s" % (a.pid, go_name, describe(t, rt)))

    changed = set()
    box = {("m_SizeDelta", "x"): a.width, ("m_SizeDelta", "y"): a.height,
           ("m_AnchoredPosition", "x"): a.x, ("m_AnchoredPosition", "y"): a.y}
    if any(v is not None for v in box.values()):
        if rt is None:
            raise SystemExit("no RectTransform found for this component")
        for (field, axis), v in box.items():
            if v is not None:
                rt[field][axis] = v
        rect.save_typetree(rt)
        changed.add(rect.path_id)
    fields = {"m_fontSize": a.font_size, "m_fontSizeMin": a.size_min, "m_fontSizeMax": a.size_max,
              "m_characterSpacing": a.char_spacing, "m_lineSpacing": a.line_spacing,
              "m_overflowMode": a.overflow}
    # TMP's own fontSize setter moves m_fontSizeBase only while auto-size is off;
    # with auto-size on the base is what switching it off again restores.
    auto_after = a.auto_size if a.auto_size is not None else bool(t.get("m_enableAutoSizing"))
    if a.font_size is not None and "m_fontSizeBase" in t and not auto_after:
        fields["m_fontSizeBase"] = a.font_size
    if a.auto_size is not None:
        fields["m_enableAutoSizing"] = int(a.auto_size)
    if a.wrap is not None:
        key = next((k for k in WRAP_KEYS if k in t), None)
        if key is None:
            raise SystemExit("this component has no wrapping field")
        fields[key] = int(a.wrap)
    if a.margin is not None:
        try:
            l, top, r, b = (float(x) for x in a.margin.split(","))
        except ValueError:
            raise SystemExit("--margin wants four numbers: left,top,right,bottom")
        t["m_margin"] = {"x": l, "y": top, "z": r, "w": b}
    for k, v in fields.items():
        if v is not None:
            t[k] = v
    if any(v is not None for v in fields.values()) or a.margin is not None:
        o.save_typetree(t, nodes) if nodes is not None else o.save_typetree(t)
        changed.add(o.path_id)
    if not changed:
        raise SystemExit("nothing to change - pass at least one setting")
    print("   after:  %s" % describe(t, rt))
    if t.get("m_fontSizeMin", 0) > t.get("m_fontSizeMax", 0):
        raise SystemExit("size min is above size max")
    if not a.apply:
        print("dry run - add --apply to write %s" % a.out)
        return
    if os.path.abspath(a.out) == os.path.abspath(a.file):
        print("backup -> %s" % backup(a.file))
    size = save(env, a.out, a.packer)
    chk = verify_untouched(before, a.out, changed, a.unity_version)
    back = {x.path_id: x for x in chk.objects}
    t2 = read_tmp(back[a.pid], nodes)
    for k, v in fields.items():
        if v is not None and abs(float(t2[k]) - float(v)) > 1e-4:
            raise SystemExit("%s read back as %s, wrote %s" % (k, t2[k], v))
    print("wrote %s (%d bytes); %d objects changed, all others byte-identical"
          % (a.out, size, len(changed)))


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("file")
    p.add_argument("--text", help="only components whose text matches this regex")
    p.add_argument("--object", help="only GameObjects whose name matches this glob")
    p.add_argument("--nodes-from", help="bundle to borrow the TextMeshPro type tree from")
    add_common(p)
    p = sub.add_parser("set")
    p.add_argument("file")
    p.add_argument("pid", type=int, help="path id of the TextMeshPro component (from list)")
    p.add_argument("--width", type=float, help="box width (RectTransform m_SizeDelta.x)")
    p.add_argument("--height", type=float, help="box height (m_SizeDelta.y)")
    p.add_argument("--x", type=float, help="box position (RectTransform m_AnchoredPosition.x)")
    p.add_argument("--y", type=float, help="box position (m_AnchoredPosition.y)")
    p.add_argument("--font-size", type=float)
    p.add_argument("--auto-size", type=on_off, help="on or off")
    p.add_argument("--size-min", type=float, help="smallest size auto-size may use")
    p.add_argument("--size-max", type=float, help="largest size auto-size may use")
    p.add_argument("--wrap", type=on_off, help="on or off")
    p.add_argument("--overflow", type=int, help="0 overflow, 1 ellipsis, 2 masking, 3 truncate, "
                                                "4 scroll rect, 5 page, 6 linked")
    p.add_argument("--char-spacing", type=float)
    p.add_argument("--line-spacing", type=float)
    p.add_argument("--margin", help="left,top,right,bottom")
    p.add_argument("--nodes-from", help="bundle to borrow the TextMeshPro type tree from")
    p.add_argument("--out", required=True, help="output file (may be the input itself)")
    p.add_argument("--packer", default="auto", choices=["auto", "lz4", "lzma", "none", "original"])
    p.add_argument("--apply", action="store_true", help="write (default: dry run)")
    add_common(p)
    a = ap.parse_args()
    (cmd_list if a.cmd == "list" else cmd_set)(a)


if __name__ == "__main__":
    main()
