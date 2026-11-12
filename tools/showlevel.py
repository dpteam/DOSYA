"""Print generated levels as ASCII with a column ruler, for eyeballing."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import genlevels  # noqa: E402


def main():
    which = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    name, fn = genlevels.LEVELS[which - 1]
    g = fn()
    genlevels.relocate(g)
    rows = g.rows()
    print(name)
    for i in range(0, g.w, 100):
        chunk = range(i, min(i + 100, g.w))
        print("     " + "".join(str((x // 100) % 10) for x in chunk))
        print("     " + "".join(str((x // 10) % 10) for x in chunk))
        print("     " + "".join(str(x % 10) for x in chunk))
        for y, r in enumerate(rows):
            print("%3d |%s|" % (y, r[i:i + 100]))
        print()


if __name__ == "__main__":
    main()
