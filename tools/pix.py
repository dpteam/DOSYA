"""Tiny helper: ASCII grids -> indexed canvases."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pal  # noqa: E402


def art(rows, legend, w=None, h=None):
    """Build a canvas from an ASCII grid.

    legend maps a char to a palette key ("skin5") or a raw index.
    """
    rows = [r for r in rows if r.strip("\n") != ""]
    w = w or max(len(r) for r in rows)
    h = h or len(rows)
    c = pal.Canvas(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in ". ":
                continue
            v = legend.get(ch)
            if v is None:
                raise KeyError("no legend entry for %r" % ch)
            c.set(x, y, pal.PAL[v] if isinstance(v, str) else v)
    return c


def outline(c, colour="void1", diagonal=False):
    """Add a 1px outline around all non-transparent pixels."""
    src = bytes(c.px)
    col = pal.PAL[colour] if isinstance(colour, str) else colour
    offs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        offs += [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    for y in range(c.h):
        for x in range(c.w):
            if src[y * c.w + x]:
                continue
            for dx, dy in offs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < c.w and 0 <= ny < c.h and src[ny * c.w + nx]:
                    c.px[y * c.w + x] = col
                    break
    return c


def shade(c, key_from, key_to, y0, y1, x0=0, x1=None):
    """Recolour a band, used for cheap lighting."""
    a = pal.PAL[key_from] if isinstance(key_from, str) else key_from
    b = pal.PAL[key_to] if isinstance(key_to, str) else key_to
    x1 = c.w if x1 is None else x1
    for y in range(y0, min(y1, c.h)):
        for x in range(x0, min(x1, c.w)):
            if c.px[y * c.w + x] == a:
                c.px[y * c.w + x] = b
    return c


def save_preview(canvases, path, scale=6, cols=8, bg=(26, 24, 32)):
    pal.sheet(canvases, scale=scale, cols=cols, bg=bg).save(path)
