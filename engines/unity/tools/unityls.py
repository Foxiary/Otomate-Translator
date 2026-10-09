# -*- coding: utf-8 -*-
"""List the objects inside a Unity bundle or .assets file.

    python tools/unityls.py <file> [--type TextAsset] [--name "Scenario*"] [--summary]

Prints path id, type, size and name. `--summary` counts objects per type
instead, which is the quickest way to see where a game keeps its text: look
for TextAsset (JSON / scripts), MonoBehaviour (TextMeshPro components, tables)
and Font / Texture2D / Sprite.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityio import add_common, load, objects, utf8_stdout   # noqa: E402


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--type", help="only this object type, e.g. TextAsset")
    ap.add_argument("--name", help="only names matching this glob")
    ap.add_argument("--summary", action="store_true", help="count objects per type")
    add_common(ap)
    a = ap.parse_args()

    env = load(a.file, a.unity_version)
    print("%s: %s, %d objects" % (os.path.basename(a.file), type(env.file).__name__, len(env.objects)))
    if a.summary:
        count, size = collections.Counter(), collections.Counter()
        for o in env.objects:
            count[o.type.name] += 1
            size[o.type.name] += o.byte_size
        for t, n in count.most_common():
            print("  %-24s %6d objects  %12d bytes" % (t, n, size[t]))
        return
    rows = objects(env, a.type, a.name)
    for o, d in rows:
        name = getattr(d, "m_Name", "") if d is not None else ""
        print("  %20d  %-20s %10d  %s" % (o.path_id, o.type.name, o.byte_size, name))
    print("%d listed" % len(rows))


if __name__ == "__main__":
    main()
