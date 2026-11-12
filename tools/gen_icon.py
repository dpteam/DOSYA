"""Generate the README icon and banner from the game's own assets.

Nothing here is hand-drawn twice: Dosya, the chicken, the bus and the font all
come from the same generators the game uses. If a sprite changes, the icon
changes with it.

    python tools/gen_icon.py

Out:
    docs/icon.png    512x512, rounded, for the README header
    docs/banner.png  1280x360, the hero image
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pal  # noqa: E402
import pix  # noqa: E402
import art_all  # noqa: E402
import genfont  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

# Ordered 4x4 Bayer matrix. Gradients in a 256-colour palette band like a
# cheap VHS tape without this; with it they look like 1994 in the good way.
BAYER = [
    0, 8, 2, 10,
    12, 4, 14, 6,
    3, 11, 1, 9,
    15, 7, 13, 5,
]


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

def dither_v(c, y0, y1, ramp_base, n, v0, v1, x0=0, x1=None):
    """Vertical gradient inside one palette ramp, dithered between steps."""
    x1 = c.w - 1 if x1 is None else x1
    x0 = max(0, x0)
    x1 = min(c.w - 1, x1)
    for y in range(max(0, y0), min(c.h - 1, y1) + 1):
        t = 0.0 if y1 == y0 else (y - y0) / float(y1 - y0)
        v = v0 + (v1 - v0) * t
        i = int(math.floor(v))
        f = v - i
        i = max(0, min(n - 1, i))
        i2 = min(n - 1, i + 1)
        row = y * c.w
        for x in range(x0, x1 + 1):
            th = BAYER[(y & 3) * 4 + (x & 3)]
            c.px[row + x] = ramp_base + (i2 if f * 16.0 > th else i)


def disc(c, cx, cy, r, ramp_base, n, v_edge, v_centre):
    """Dithered circle. Used for the sun and for the glow behind the title."""
    for y in range(cy - r, cy + r + 1):
        if y < 0 or y >= c.h:
            continue
        dy = y - cy
        span = int(math.sqrt(max(0, r * r - dy * dy)))
        row = y * c.w
        for x in range(cx - span, cx + span + 1):
            if x < 0 or x >= c.w:
                continue
            d = math.hypot(x - cx, y - cy) / float(r)
            v = v_centre + (v_edge - v_centre) * d
            i = int(math.floor(v))
            f = v - i
            i = max(0, min(n - 1, i))
            i2 = min(n - 1, i + 1)
            th = BAYER[(y & 3) * 4 + (x & 3)]
            c.px[row + x] = ramp_base + (i2 if f * 16.0 > th else i)


def wave(x, period, seed):
    """Smooth 1D noise, same trick as the in-game parallax hills."""
    def noise(i):
        n = (i * 374761393 + seed * 1442695040) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return (n ^ (n >> 16)) & 0xFF
    i0 = x // period
    f = x % period
    a = noise(i0)
    b = noise(i0 + 1)
    return a + (b - a) * f // period


def hill(c, base_y, amp, period, seed, ramp_base, n, v_top, v_bottom, x_from=0, x_to=None):
    """One rolling ridge, dithered at the crest."""
    x_to = c.w - 1 if x_to is None else x_to
    for x in range(max(0, x_from), min(c.w - 1, x_to) + 1):
        h = wave(x, period, seed) * 2 + wave(x, period // 3 + 1, seed + 7)
        y = base_y - (h * amp) // 600
        for yy in range(max(0, y), c.h):
            t = (yy - y) / float(max(1, c.h - y))
            v = v_top + (v_bottom - v_top) * t
            i = int(math.floor(v))
            f = v - i
            i = max(0, min(n - 1, i))
            i2 = min(n - 1, i + 1)
            th = BAYER[(yy & 3) * 4 + (x & 3)]
            c.px[yy * c.w + x] = ramp_base + (i2 if f * 16.0 > th else i)


def sprite(name):
    """Build a sprite exactly the way the asset exporter does."""
    rows = art_all.build()[name]
    w = len(rows[0])
    h = len(rows)
    c = pal.Canvas(w + 2, h + 2)
    c.blit(pix.art(rows, art_all.L), 1, 1)
    pix.outline(c)
    return c


def blit_scaled(dst, src, dx, dy, scale):
    for y in range(src.h):
        for x in range(src.w):
            v = src.px[y * src.w + x]
            if not v:
                continue
            px0 = dx + x * scale
            py0 = dy + y * scale
            for sy in range(scale):
                row = (py0 + sy) * dst.w
                if py0 + sy < 0 or py0 + sy >= dst.h:
                    continue
                for sx in range(scale):
                    px1 = px0 + sx
                    if 0 <= px1 < dst.w:
                        dst.px[row + px1] = v


_FONT = None


def font():
    global _FONT
    if _FONT is None:
        _FONT, _ = genfont.build_table()
    return _FONT


def text(dst, x, y, s, scale, colour, shadow=None):
    """Draw CP866 text at an integer scale, with an optional drop shadow."""
    table = font()
    codes = list(s.encode("cp866"))

    def draw(ox, oy, col):
        cx = ox
        for code in codes:
            for gy in range(16):
                bits = table[code * 16 + gy]
                if not bits:
                    continue
                for gx in range(8):
                    if bits & (0x80 >> gx):
                        for sy in range(scale):
                            for sx in range(scale):
                                px = cx + gx * scale + sx
                                py = oy + gy * scale + sy
                                if 0 <= px < dst.w and 0 <= py < dst.h:
                                    dst.px[py * dst.w + px] = col
            cx += 8 * scale
        return cx

    if shadow is not None:
        draw(x + scale, y + scale, shadow)
    return draw(x, y, colour)


def text_width(s, scale):
    return len(s.encode("cp866")) * 8 * scale


def text_centered(dst, y, s, scale, colour, shadow=None, cx=None):
    cx = dst.w // 2 if cx is None else cx
    x = cx - text_width(s, scale) // 2
    return text(dst, x, y, s, scale, colour, shadow)


# --------------------------------------------------------------------------
# scenes
# --------------------------------------------------------------------------

def make_icon(size=512):
    c = pal.Canvas(size, size)
    sky = pal.PAL["sky0"]
    n_sky = pal.RAMPS["sky"][1]
    ground = int(size * 0.78)

    # sky, dithered so 12 ramp steps do not read as 12 stripes
    dither_v(c, 0, ground, sky, n_sky, n_sky - 1, 2)

    # sun, high and to the right
    disc(c, int(size * 0.80), int(size * 0.16), int(size * 0.10),
         pal.PAL["yellow0"], pal.RAMPS["yellow"][1], 2.4, 6.0)

    # clouds
    cl = sprite("cloud")
    blit_scaled(c, cl, int(size * 0.08), int(size * 0.10), 2)
    blit_scaled(c, cl, int(size * 0.52), int(size * 0.05), 2)

    # three ridges, back to front, each brighter and lower
    hill(c, int(size * 0.62), 34, 71, 11,
         pal.PAL["darkgreen0"], pal.RAMPS["darkgreen"][1], 1.6, 0.3)
    hill(c, int(size * 0.69), 28, 43, 29,
         pal.PAL["darkgreen2"], pal.RAMPS["darkgreen"][1], 2.2, 0.4)
    hill(c, int(size * 0.75), 22, 29, 53,
         pal.PAL["green1"], pal.RAMPS["green"][1], 3.0, 0.6)

    # ground
    dither_v(c, ground, size - 1, pal.PAL["dirt0"], pal.RAMPS["dirt"][1], 7.0, 3.0)
    # a grass lip where the dirt starts
    for x in range(size):
        h = 3 + (wave(x, 11, 3) * 3) // 255
        for yy in range(ground, min(size, ground + h)):
            v = 5.0 - (yy - ground) * 0.6
            c.px[yy * size + x] = pal.PAL["green%d" % max(1, int(v))]

    # Dosya, standing on the ground line. Scale 8 keeps her whole.
    ds = sprite("dosya_stand")
    scale = 8
    dx = (size - ds.w * scale) // 2
    dy = ground - ds.h * scale + 4
    blit_scaled(c, ds, dx, dy, scale)

    # one chicken, because the icon needs a witness
    ck = sprite("chicken0")
    blit_scaled(c, ck, int(size * 0.13), ground - ck.h * 4 + 2, 4)

    # a sunflower to the right, for colour balance
    sf = sprite("sunflower")
    blit_scaled(c, sf, int(size * 0.78), ground - sf.h * 4 + 2, 4)

    return c


def make_banner(w=1280, h=360):
    c = pal.Canvas(w, h)
    sky = pal.PAL["sky0"]
    n_sky = pal.RAMPS["sky"][1]
    horizon = int(h * 0.80)

    dither_v(c, 0, horizon, sky, n_sky, n_sky - 1, 2)

    # sun
    disc(c, int(w * 0.88), int(h * 0.19), 38,
         pal.PAL["yellow0"], pal.RAMPS["yellow"][1], 2.2, 6.0)

    # Clouds only in the corners, well clear of the title block in the middle.
    cl = sprite("cloud")
    for (cx, cy, s) in ((40, 22, 3), (150, 66, 2), (1150, 88, 2),
                        (1010, 26, 2), (300, 14, 2)):
        blit_scaled(c, cl, cx, cy, s)

    # ridges
    hill(c, int(h * 0.60), 22, 91, 5,
         pal.PAL["darkgreen0"], pal.RAMPS["darkgreen"][1], 1.2, 0.2)
    hill(c, int(h * 0.70), 18, 53, 17,
         pal.PAL["darkgreen1"], pal.RAMPS["darkgreen"][1], 1.6, 0.3)
    hill(c, int(h * 0.80), 14, 31, 41,
         pal.PAL["green0"], pal.RAMPS["green"][1], 2.4, 0.4)

    ground = int(h * 0.90)
    dither_v(c, ground, h - 1, pal.PAL["dirt0"], pal.RAMPS["dirt"][1], 7.0, 3.0)
    for x in range(w):
        hh = 3 + (wave(x, 11, 3) * 3) // 255
        for yy in range(ground, min(h, ground + hh)):
            v = 5.0 - (yy - ground) * 0.6
            c.px[yy * w + x] = pal.PAL["green%d" % max(1, int(v))]

    # Title block, centred, sitting in the sky above the ridges.
    text_centered(c, 34, "ДОСЯ", 7, pal.PAL["red9"], pal.PAL["void0"])
    text_centered(c, 158, "и автобус", 3, pal.PAL["yellow7"], pal.PAL["void0"])

    # subtitle sits in the sky, above the ridge line
    text_centered(c, 196, "село · навоз · разбитые мечты", 2,
                  pal.PAL["grey9"], pal.PAL["void0"])

    # Dosya on the left, bus on the right, both on the ground line
    ds = sprite("dosya_stand")
    blit_scaled(c, ds, 76, ground - ds.h * 5 + 8, 5)

    bus = sprite("bus")
    blit_scaled(c, bus, w - bus.w * 4 - 76, ground - bus.h * 4 + 10, 4)

    # a small parade of poultry
    ck = sprite("chicken0")
    ro = sprite("rooster0")
    blit_scaled(c, ck, 26, ground - ck.h * 3 + 2, 3)
    blit_scaled(c, ro, 214, ground - ro.h * 3 + 2, 3)
    blit_scaled(c, ck, 330, ground - ck.h * 3 + 2, 3)

    return c


def rounded(im, radius):
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1],
                        radius=radius, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def main():
    os.makedirs(DOCS, exist_ok=True)

    icon = make_icon(512)
    im = rounded(icon.to_image(), 84)
    im.save(os.path.join(DOCS, "icon.png"))
    print("wrote docs/icon.png", im.size)

    banner = make_banner()
    banner.to_image().save(os.path.join(DOCS, "banner.png"))
    print("wrote docs/banner.png", banner.w, "x", banner.h)


if __name__ == "__main__":
    main()
