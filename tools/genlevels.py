"""Level builder -> build/gen/levels.c

Levels are authored here so columns always line up. Each level is a grid of
characters. Two layers exist:

  FOREGROUND (collides)
    ' ' empty      '#' dirt        '=' grass top    '%' grass
    'B' brick      'W' wood        'F' fence        '~' water
    '^' rakes      'H' hay         'R' roof         'S' stone
    '-' one-way platform
    'P' player start
    'c' chicken    'r' rooster     'o' goat         'd' ded
    't' tractor    'm' milk        'e' egg          'n' manure
    'v' samogon    'X' bus (goal)

  BACKGROUND (decor only, drawn dimmed, no collision)
    '1' house wall  '2' roof  '3' fence  '4' hay  '5' wood  '6' stone

Every level is 14 rows tall. Row 12 is the usual walking surface, row 13 is
the dirt under it.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_C = os.path.join(ROOT, "build", "gen", "levels.c")
OUT_H = os.path.join(ROOT, "build", "gen", "levels.h")

H = 14
GROUND = 12


class Grid:
    def __init__(self, w, h=H):
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def fill(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, ch)

    def ground(self, x0, x1, top=GROUND, dirt="#", grass="="):
        self.fill(x0, top, x1, self.h - 1, dirt)
        self.fill(x0, top, x1, top, grass)

    def platform(self, x0, x1, y):
        self.fill(x0, y, x1, y, "-")

    def house(self, x, w, h, roof=True, base=None):
        """Background izba: log walls, thatch roof, a window and a door.

        `base` is the row the house stands on. It defaults to GROUND, but a
        level with terraces must pass the real ground row, otherwise the house
        floats above the village like a rumour.
        """
        base = GROUND if base is None else base
        wall = "1" if (x // 4) % 2 == 0 else "5"
        self.fill(x, base - h, x + w - 1, base - 1, wall)
        self.fill(x, base - h, x, base - 1, "9")
        self.fill(x + w - 1, base - h, x + w - 1, base - 1, "9")
        if roof:
            self.fill(x - 1, base - h - 1, x + w, base - h - 1, "2")
            if h >= 4:
                self.fill(x, base - h - 2, x + w - 1, base - h - 2, "2")
        self.fill(x + 1, base - 3, x + 1, base - 1, "8")
        if w >= 4:
            self.fill(x + w - 3, base - h + 1, x + w - 3, base - h + 1, "7")

    def fence(self, x, n=1):
        for i in range(n):
            self.put(x + i, GROUND - 1, "3")

    def hay(self, x, y=GROUND - 1):
        self.put(x, y, "4")

    def endwall(self, h=7):
        """A cliff at the end of the level. Without it Dosya runs straight past
        the bus and off the edge of the world, which reads as a bug."""
        self.fill(self.w - 2, GROUND - h, self.w - 1, self.h - 1, "#")

    def rows(self):
        return ["".join(r) for r in self.g]


# ---------------------------------------------------------------------------
def level1():
    """ОГОРОД -- learn to run, jump and hate poultry."""
    W = 120
    g = Grid(W)
    g.ground(0, 14)
    g.ground(18, 30)
    g.ground(35, 52)
    g.ground(56, 72)
    g.ground(76, 96)
    g.ground(101, W - 1)

    g.fill(15, 13, 17, 13, "~")
    g.fill(31, 13, 33, 13, "~")
    g.fill(97, 13, 100, 13, "~")

    # background: a couple of village houses, fences and hay
    g.house(24, 5, 3)
    g.house(84, 6, 3)
    g.fence(4, 3)
    g.fence(46, 2)
    g.fence(66, 3)
    g.fence(107, 2)
    g.hay(9)
    g.hay(60)

    # platforms with loot
    g.platform(20, 23, 8)
    g.platform(24, 27, 6)
    g.platform(38, 42, 9)
    g.platform(60, 64, 6)
    g.platform(80, 85, 8)
    g.platform(88, 91, 6)

    g.put(21, 7, "m")
    g.put(25, 5, "e")
    g.put(40, 8, "m")
    g.put(62, 5, "v")
    g.put(82, 7, "e")
    g.put(89, 5, "m")

    # Enemies stay at least three tiles away from pit edges: a chicken right
    # next to a hole turns a jump into a funeral.
    for x in (8, 26, 44, 58, 64, 86, 90, 105):
        g.put(x, GROUND - 1, "c")
    g.put(48, GROUND - 1, "r")
    g.put(62, 9, "c")
    g.put(92, GROUND - 1, "o")

    g.put(7, GROUND - 1, "n")
    g.put(37, GROUND - 1, "n")
    g.put(79, GROUND - 1, "n")

    g.put(2, GROUND - 1, "P")
    g.put(115, GROUND - 1, "X")
    g.endwall()
    return g


# ---------------------------------------------------------------------------
def level2():
    """ДЕРЕВНЯ -- more houses, more chickens, more rakes."""
    W = 140
    g = Grid(W)
    g.ground(0, 12)
    g.ground(17, 26)
    g.ground(30, 46)
    g.ground(50, 58, 11)
    g.ground(62, 84)
    g.ground(88, 104, 9)
    g.ground(108, W - 1)

    g.fill(13, 13, 16, 13, "~")
    g.fill(27, 13, 29, 13, "~")
    g.fill(59, 13, 61, 13, "~")
    g.fill(105, 13, 107, 13, "~")
    g.fill(47, 13, 49, 13, "^")

    g.house(6, 5, 3)
    g.house(20, 5, 4)
    g.house(35, 6, 4)
    g.house(54, 5, 3, base=11)
    g.house(66, 6, 4)
    g.house(76, 5, 3)
    g.house(93, 6, 4, base=9)
    g.house(112, 5, 3)
    g.house(124, 6, 4)

    g.fence(3, 3)
    g.fence(31, 2)
    g.fence(52, 2)
    g.fence(80, 3)
    g.fence(99, 2)
    g.fence(120, 3)
    g.hay(10)
    g.hay(44)
    g.hay(70)
    g.hay(131)

    g.platform(20, 24, 8)
    g.platform(52, 56, 7)
    g.platform(72, 76, 8)
    g.platform(90, 95, 5)
    g.platform(97, 101, 6)

    g.put(22, 7, "e")
    g.put(54, 6, "m")
    g.put(74, 7, "e")
    g.put(92, 4, "m")
    g.put(99, 5, "v")

    for x in (5, 22, 38, 44, 55, 64, 76, 82, 92, 100, 118, 126):
        g.put(x, GROUND - 1, "c")
    for x in (24, 42, 70, 94, 120):
        g.put(x, GROUND - 1, "r")
    g.put(45, GROUND - 1, "o")
    g.put(80, GROUND - 1, "o")
    g.put(122, GROUND - 1, "o")
    for x in (32, 60, 90, 116):
        g.put(x, GROUND - 1, "d")

    g.put(9, GROUND - 1, "n")
    g.put(41, GROUND - 1, "n")
    g.put(87, GROUND - 1, "n")
    g.put(111, GROUND - 1, "n")

    g.put(2, GROUND - 1, "P")
    g.put(135, GROUND - 1, "X")
    g.endwall()
    return g


# ---------------------------------------------------------------------------
def level3():
    """ТРАКТОРНОЕ ПОЛЕ -- the finale. Everything is on fire, emotionally.

    Built on a strict 16-tile rhythm: 13 tiles of ground, 3 tiles of pit.
    Regularity is what makes a hard level fair -- the player can see the
    pattern and commit to a jump instead of guessing.
    """
    W = 160
    g = Grid(W)
    segs = []
    x = 0
    while x < W:
        segs.append((x, min(x + 12, W - 1)))
        x += 16

    for (a, b) in segs:
        g.ground(a, b)
    for (a, b) in segs[:-1]:
        g.fill(b + 1, 13, b + 3, 13, "~")

    # one platform per segment, dead centre, so it never sits on a landing zone
    for i, (a, b) in enumerate(segs):
        mid = (a + b) // 2
        g.platform(mid - 2, mid + 2, 7 if i % 2 == 0 else 5)

    # a barn every other segment
    for i, (a, b) in enumerate(segs):
        if i % 2 == 0:
            g.house(a + 7, 5, 4)
        else:
            g.fence(a + 2, 2)
    # rakes on the flat, never within 4 tiles of a pit
    for i, (a, b) in enumerate(segs):
        g.fill(a + 5, GROUND - 1, a + 6, GROUND - 1, "^")

    # loot on the platforms
    loot = ["m", "e", "v", "m", "e", "m", "v", "e", "m", "v"]
    for i, (a, b) in enumerate(segs):
        mid = (a + b) // 2
        y = (7 if i % 2 == 0 else 5) - 1
        g.put(mid, y, loot[i % len(loot)])

    # enemies: one of each flavour per few segments, well away from edges
    kinds = ["c", "c", "r", "o", "t", "d", "c", "r", "o", "t"]
    for i, (a, b) in enumerate(segs):
        g.put(a + 2, GROUND - 1, kinds[i % len(kinds)])
        if i >= 4:
            g.put(b - 2, GROUND - 1, kinds[(i + 3) % len(kinds)])

    for i, (a, b) in enumerate(segs):
        g.put(a + 9, GROUND - 1, "n")

    g.put(2, GROUND - 1, "P")
    g.put(W - 5, GROUND - 1, "X")
    g.endwall()
    return g


LEVELS = [
    ("ОГОРОД", level1),
    ("ДЕРЕВНЯ", level2),
    ("ТРАКТОРНОЕ ПОЛЕ", level3),
]

ENEMY_CHARS = "crod t"
SAFE_DIST = 4          # tiles between an enemy and the edge of a pit


def relocate(g):
    """Nudge enemies that are too close to a hole, or inside a wall.

    Level authors place enemies roughly; the generator makes sure no chicken
    is standing on the lip of a pit waiting to become a trap. Searching
    outward keeps the author's intent (which part of the level) while
    guaranteeing the level stays fair.
    """
    rows = g.rows()
    w, h = g.w, g.h

    def solid(x, y):
        if y >= h:
            return True
        if x < 0 or x >= w:
            return False
        return rows[y][x] in "#=%BWF^HRS-"

    holes = [x for x in range(w)
             if not solid(x, GROUND) and not solid(x, GROUND + 1)]

    def safe(x):
        if x < 1 or x >= w - 1:
            return False
        if solid(x, GROUND - 1):
            return False
        if not solid(x, GROUND):
            return False
        return all(abs(hx - x) >= SAFE_DIST for hx in holes)

    moved = 0
    for y in range(h):
        for x in range(w):
            ch = g.g[y][x]
            if ch not in "crodt":
                continue
            if safe(x):
                continue
            for d in range(1, w):
                for nx in (x + d, x - d):
                    if 0 <= nx < w and safe(nx) and g.g[y][nx] == " ":
                        g.g[y][x] = " "
                        g.g[y][nx] = ch
                        moved += 1
                        break
                else:
                    continue
                break
    return moved


def validate(name, g):
    """Reject levels that are impossible or unfair.

    Checks:
      * exactly one player start and one bus
      * every enemy at least SAFE_DIST tiles from a hole: a chicken next to a
        pit turns a jump into a funeral
      * no enemy inside a wall
    """
    rows = g.rows()
    errs = []
    starts = sum(r.count("P") for r in rows)
    buses = sum(r.count("X") for r in rows)
    if starts != 1:
        errs.append("player starts: %d" % starts)
    if buses != 1:
        errs.append("buses: %d" % buses)

    def solid(x, y):
        if y >= g.h:
            return True
        if x < 0 or x >= g.w:
            return False
        return rows[y][x] in "#=%BWF^HRS-"

    # columns that are holes at ground level
    holes = []
    for x in range(g.w):
        if not solid(x, GROUND) and not solid(x, GROUND + 1):
            holes.append(x)

    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "crodt":
                if solid(x, y):
                    errs.append("%s inside a wall at %d,%d" % (ch, x, y))
                for hx in holes:
                    if abs(hx - x) < SAFE_DIST:
                        errs.append("%s at %d is %d tiles from hole at %d"
                                    % (ch, x, abs(hx - x), hx))
    if errs:
        print("!! %s:" % name)
        for e in errs:
            print("   " + e)
    return errs


def c_escape(s):
    out = []
    for b in s.encode("cp866"):
        if b == 0x22:
            out.append('\\"')
        elif b == 0x5C:
            out.append("\\\\")
        elif 32 <= b < 127:
            out.append(chr(b))
        else:
            out.append("\\%03o" % b)
    return '"' + "".join(out) + '"'


def c_string(rows):
    return "\n".join("    " + c_escape(r) + "," for r in rows)


def main():
    os.makedirs(os.path.dirname(OUT_C), exist_ok=True)

    # Build each level exactly once: relocate, validate, remember the rows.
    built = []
    problems = 0
    for name, fn in LEVELS:
        g = fn()
        moved = relocate(g)
        rows = g.rows()
        assert all(len(r) == g.w for r in rows), name
        errs = validate(name, g)
        problems += len(errs)
        built.append((name, g, rows, moved))
        print("%-18s %dx%d  (%d enemies moved, %d problems)"
              % (name, g.w, g.h, moved, len(errs)))

    body = ["/* generated by tools/genlevels.py - do not edit */",
            '#include "levels.h"', ""]
    for i, (name, g, rows, _moved) in enumerate(built):
        body.append("static const char *lvl%d_rows[%d] = {" % (i + 1, len(rows)))
        body.append(c_string(rows))
        body.append("};")
        body.append("")

    body.append("const LevelDef g_levels[] = {")
    for i, (name, g, _rows, _moved) in enumerate(built):
        body.append("  { %s, %d, %d, lvl%d_rows }," % (c_escape(name), g.w, g.h, i + 1))
    body.append("};")
    body.append("")
    body.append("const int g_num_levels = %d;" % len(built))

    with open(OUT_C, "w", encoding="ascii") as f:
        f.write("\n".join(body) + "\n")

    with open(OUT_H, "w", encoding="ascii") as f:
        f.write("""/* generated by tools/genlevels.py - do not edit */
#ifndef DOSYA_LEVELS_H
#define DOSYA_LEVELS_H

typedef struct {
  const char *name;
  int w, h;
  const char **rows;
} LevelDef;

extern const LevelDef g_levels[];
extern const int g_num_levels;

#endif
""")

    print("wrote", OUT_C)
    if problems:
        print("%d level problem(s) - refusing to call this build good" % problems,
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
