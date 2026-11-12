"""Procedural 16x16 tiles: dirt, grass, brick, wood, water, spikes, hay...

Hand-drawing 16x16 tiles as ASCII is painful and they need noise anyway, so
each tile type is a small function that stamps palette ramps plus a deterministic
dither pattern.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pix  # noqa: E402
import pal  # noqa: E402

W = H = 16


def h32(x, y, seed=0):
    """Deterministic pseudo-random 0..255."""
    n = (x * 374761393 + y * 668265263 + seed * 1442695040) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return (n ^ (n >> 16)) & 0xFF


def tile(fill=None):
    return pal.Canvas(W, H, fill if fill is not None else 0)


def C(name):
    return pal.PAL[name]


def ramp(name, n, t):
    """Sample ramp entry by t in 0..1."""
    i = max(0, min(n - 1, int(t * (n - 1) + 0.5)))
    return C("%s%d" % (name, i))


# ---------------------------------------------------------------- tiles ------

def t_dirt():
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 1)
            c.set(x, y, ramp("dirt", 10, 0.30 + n / 255.0 * 0.45))
    for (px, py) in ((3, 4), (11, 9), (7, 12), (13, 3), (5, 8)):
        c.set(px, py, ramp("dirt", 10, 0.78))
        c.set(px + 1, py, ramp("dirt", 10, 0.62))
        c.set(px, py + 1, ramp("dirt", 10, 0.55))
    return c


def t_grass_top():
    c = t_dirt()
    for x in range(W):
        n = h32(x, 0, 7)
        c.set(x, 0, ramp("green", 12, 0.62 + n / 255.0 * 0.30))
        c.set(x, 1, ramp("green", 12, 0.55 + n / 255.0 * 0.25))
        c.set(x, 2, ramp("green", 12, 0.38 + n / 255.0 * 0.22))
        if h32(x, 5, 3) > 170:
            c.set(x, 3, ramp("green", 12, 0.45))
        if h32(x, 9, 4) > 215:
            c.set(x, 4, ramp("green", 12, 0.35))
    return c


def t_grass():
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 2)
            c.set(x, y, ramp("green", 12, 0.22 + n / 255.0 * 0.40))
    for (px, py) in ((2, 3), (9, 6), (5, 11), (12, 13), (7, 2)):
        for k in range(3):
            c.set(px + k, py, ramp("green", 12, 0.72))
            c.set(px + k, py + 1, ramp("green", 12, 0.55))
    return c


def t_brick():
    """Red brick. Kept for the well and the stove."""
    c = tile()
    bh, bw = 4, 8
    for y in range(H):
        row = y // bh
        off = (row % 2) * (bw // 2)
        for x in range(W):
            bx = (x + off) % bw
            if y % bh == 0 or bx == 0:
                c.set(x, y, ramp("grey", 16, 0.30))
            else:
                n = h32(x, y, 11)
                base = 0.42 + n / 255.0 * 0.22
                if y % bh == 1:
                    base += 0.12
                c.set(x, y, ramp("red", 12, base))
    return c


def t_wood():
    """Log wall of an izba: horizontal logs with a dark seam."""
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 21)
            v = 0.40 + (n / 255.0) * 0.16
            if y % 8 == 7:
                v = 0.14                      # seam between logs
            elif y % 8 == 0:
                v = 0.60                      # lit top of a log
            c.set(x, y, ramp("wood", 10, v))
    # grain
    for y in (3, 4, 11, 12):
        for x in range(W):
            if h32(x, y, 22) > 110:
                c.set(x, y, ramp("wood", 10, 0.32))
    # the ends of the logs, poking out at the corner
    for y in range(H):
        if y % 8 in (2, 3, 4, 5):
            c.set(0, y, ramp("wood", 10, 0.55))
            c.set(1, y, ramp("wood", 10, 0.45))
    return c


def t_log_end():
    """End grain of a log, used for the corner posts of a house."""
    c = tile()
    for y in range(H):
        for x in range(W):
            dx, dy = x - 7.5, y - 7.5
            r = (dx * dx + dy * dy) ** 0.5
            if r > 7.5:
                c.set(x, y, ramp("wood", 10, 0.20))
            elif int(r) % 2:
                c.set(x, y, ramp("wood", 10, 0.55))
            else:
                c.set(x, y, ramp("wood", 10, 0.40))
    return c


def t_plaster():
    """Whitewashed wall with a timber frame -- the other half of an izba."""
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 91)
            v = 0.72 + n / 255.0 * 0.22
            c.set(x, y, ramp("white", 10, v))
    # timber frame
    for x in range(W):
        c.set(x, 0, ramp("wood", 10, 0.30))
        c.set(x, 15, ramp("wood", 10, 0.30))
    for y in range(H):
        c.set(0, y, ramp("wood", 10, 0.30))
        c.set(15, y, ramp("wood", 10, 0.30))
    for i in range(16):
        c.set(i, 7, ramp("wood", 10, 0.35))
        c.set(i, 8, ramp("wood", 10, 0.30))
    return c


def t_window():
    """A little window with a lit interior. Villages are dark inside."""
    c = t_plaster()
    for y in range(3, 13):
        for x in range(3, 13):
            edge = (y in (3, 12)) or (x in (3, 12))
            c.set(x, y, ramp("wood", 10, 0.22) if edge else ramp("orange", 10, 0.55))
    for i in range(3, 13):
        c.set(8, i, ramp("wood", 10, 0.25))
        c.set(i, 8, ramp("wood", 10, 0.25))
    # a bit of glow spilling out
    for i in range(4, 12):
        c.set(i, 13, ramp("orange", 10, 0.40))
    return c


def t_fence():
    c = tile()
    for y in (3, 4, 10, 11):
        for x in range(W):
            c.set(x, y, ramp("wood", 10, 0.55 + h32(x, y, 31) / 255.0 * 0.2))
    for x in (3, 4, 11, 12):
        for y in range(H):
            c.set(x, y, ramp("wood", 10, 0.40 + h32(x, y, 32) / 255.0 * 0.2))
    return c


def t_water():
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 41)
            c.set(x, y, ramp("teal", 8, 0.25 + n / 255.0 * 0.35))
    for y in (4, 5, 11, 12):
        for x in range(W):
            if h32(x, y, 42) > 110:
                c.set(x, y, ramp("teal", 8, 0.72))
    return c


def t_spikes():
    """Rake tines pointing up: the classic village hazard."""
    c = tile()
    for i in range(4):
        x0 = 1 + i * 4
        for k in range(3):
            hgt = 9 - k * 3
            for y in range(H - 1, H - 1 - hgt, -1):
                c.set(x0 + k, y, ramp("metal", 8, 0.45 + (H - y) / 16.0 * 0.4))
    for x in range(W):
        c.set(x, H - 1, ramp("metal", 8, 0.25))
        c.set(x, H - 2, ramp("metal", 8, 0.30))
    return c


def t_hay():
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 51)
            v = 0.35 + n / 255.0 * 0.40
            if (x * 3 + y * 7) % 11 < 3:
                v += 0.15
            c.set(x, y, ramp("hay", 7, v))
    return c


def t_roof():
    """Thatch. Overlapping straw, darker at the bottom of each course."""
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 61)
            row = y // 4
            if y % 4 == 3:
                c.set(x, y, ramp("hay", 7, 0.20))
            else:
                off = (row % 2) * 3
                if (x + off) % 6 == 0:
                    c.set(x, y, ramp("hay", 7, 0.24))
                else:
                    c.set(x, y, ramp("hay", 7, 0.45 + n / 255.0 * 0.35))
    return c


def t_stone():
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 71)
            c.set(x, y, ramp("grey", 16, 0.32 + n / 255.0 * 0.30))
    for (px, py) in ((4, 5), (10, 3), (7, 10), (12, 12)):
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                c.set(px + dx, py + dy, ramp("grey", 16, 0.62))
    return c


def t_plank_platform():
    c = tile()
    for y in range(H):
        for x in range(W):
            if y < 5:
                c.set(x, y, ramp("wood", 10, 0.50 + h32(x, y, 81) / 255.0 * 0.2))
            elif y == 5:
                c.set(x, y, ramp("wood", 10, 0.18))
    return c


def t_door():
    """A plank door with an iron ring. Drawn as background decoration."""
    c = tile()
    for y in range(H):
        for x in range(W):
            n = h32(x, y, 101)
            v = 0.44 + n / 255.0 * 0.16
            if x % 5 == 0:
                v = 0.26
            c.set(x, y, ramp("wood", 10, v))
    # frame
    for x in range(W):
        c.set(x, 0, ramp("wood", 10, 0.55))
        c.set(x, 1, ramp("wood", 10, 0.34))
        c.set(x, 15, ramp("wood", 10, 0.30))
    for y in range(H):
        c.set(0, y, ramp("wood", 10, 0.34))
        c.set(15, y, ramp("wood", 10, 0.34))
    # iron ring handle
    c.set(11, 8, ramp("metal", 8, 0.72))
    c.set(12, 8, ramp("metal", 8, 0.55))
    c.set(11, 9, ramp("metal", 8, 0.55))
    c.set(10, 9, ramp("metal", 8, 0.40))
    return c


TILES = [
    ("empty", lambda: tile()),
    ("dirt", t_dirt),
    ("grass_top", t_grass_top),
    ("grass", t_grass),
    ("brick", t_brick),
    ("wood", t_wood),
    ("fence", t_fence),
    ("water", t_water),
    ("spikes", t_spikes),
    ("hay", t_hay),
    ("roof", t_roof),
    ("stone", t_stone),
    ("platform", t_plank_platform),
    ("log_end", t_log_end),
    ("plaster", t_plaster),
    ("window", t_window),
    ("door", t_door),
]


if __name__ == "__main__":
    cs = [fn() for _, fn in TILES]
    pix.save_preview(cs, os.path.join(os.path.dirname(os.path.abspath(__file__)), "prev_tiles.png"),
                     scale=4, cols=6, bg=(0, 0, 0))
    print("ok", [n for n, _ in TILES])
